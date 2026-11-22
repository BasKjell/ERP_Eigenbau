"""Agentenregister und Ablauf laden und fail-closed validieren (KI-U-02, Teil 01/09)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ACTIVE_STATUSES = frozenset({"testbetrieb", "befristet_produktiv"})
STATUSES = frozenset({"idee", "bewertet", "pausiert", "stillgelegt"}) | ACTIVE_STATUSES
AGENT_AUTONOMY = frozenset({"A0", "A1", "A2", "A3"})
KINDS = frozenset({"create", "review"})
STEP_KINDS = frozenset({"create", "review", "check", "gate"})
GATES = ("G1", "G2", "G3", "G4", "G5")
# Werkzeuge, die keine Agentenrolle besitzen darf (Teil 09).
FORBIDDEN_TOOL = re.compile(r"(approve|freigabe|merge|delete|loesch|deploy|admin|release)", re.I)
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}")


class RegistryError(ValueError):
    """Register oder Ablauf sind unvollständig oder widersprüchlich."""


@dataclass(frozen=True)
class Agent:
    id: str
    role: str
    number: int
    name: str
    owner: str
    status: str
    autonomy: str
    approved_until: date
    model_profile: str
    family: str
    gateway_alias: str
    kind: str
    mission: str
    tools: tuple[str, ...]
    reads: tuple[str, ...]
    prompt_file: Path
    reviewed_by: str | None
    escalation: str
    evidence: str
    limits: dict[str, Any] = field(default_factory=dict)
    umbrella: str = ""

    def active(self, today: date | None = None) -> bool:
        return self.status in ACTIVE_STATUSES and (today or date.today()) <= self.approved_until

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "number": self.number,
            "name": self.name,
            "owner": self.owner,
            "status": self.status,
            "autonomy": self.autonomy,
            "approved_until": self.approved_until.isoformat(),
            "model_profile": self.model_profile,
            "family": self.family,
            "kind": self.kind,
            "mission": self.mission,
            "tools": list(self.tools),
            "reviewed_by": self.reviewed_by,
            "escalation": self.escalation,
            "evidence": self.evidence,
            "umbrella": self.umbrella,
        }


@dataclass(frozen=True)
class Step:
    id: str
    label: str
    kind: str
    role: str | None = None
    subject: str | None = None
    produces: str | None = None
    decider: str | None = None
    requires: tuple[str, ...] = ()
    freeze_baseline: bool = False
    bind_digest: str | None = None
    on_rework: dict[str, str] = field(default_factory=dict)
    on_failure: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Registry:
    version: int
    register_id: str
    policy_version: str
    agents: dict[str, Agent]
    human_roles: dict[str, dict[str, Any]]
    tools: dict[str, str]
    artifact_kinds: tuple[str, ...]
    productive_agents: tuple[dict[str, Any], ...]
    steps: tuple[Step, ...]
    classes: dict[str, dict[str, Any]]
    max_correction_rounds: int
    budget: dict[str, int]
    prompts_dir: Path
    digest: str

    def agent(self, role: str) -> Agent:
        try:
            return self.agents[role]
        except KeyError:
            raise RegistryError(f"Rolle {role} steht nicht im Agentenregister") from None

    def step_index(self, step_id: str) -> int:
        for index, step in enumerate(self.steps):
            if step.id == step_id:
                return index
        raise RegistryError(f"Unbekannter Schritt {step_id}")

    def producer(self, kind: str) -> Step | None:
        return next((step for step in self.steps if step.produces == kind), None)

    def human_gate(self, gate: str, change_class: str) -> bool:
        return gate in self.classes[change_class]["human_gates"]

    def prompt(self, role: str) -> str:
        common = (self.prompts_dir / "_gemeinsam.md").read_text(encoding="utf-8")
        return common + "\n\n" + self.agent(role).prompt_file.read_text(encoding="utf-8")

    def public(self) -> dict[str, Any]:
        return {
            "register_id": self.register_id,
            "version": self.version,
            "policy_version": self.policy_version,
            "digest": self.digest,
            "agents": [agent.public() for agent in sorted(self.agents.values(), key=lambda a: a.number)],
            "productive_agents": list(self.productive_agents),
            "human_roles": self.human_roles,
            "classes": self.classes,
            "steps": [
                {
                    "id": step.id,
                    "label": step.label,
                    "kind": step.kind,
                    "role": step.role,
                    "decider": step.decider,
                    "produces": step.produces,
                    "subject": step.subject,
                }
                for step in self.steps
            ],
        }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RegistryError(message)


def _as_date(value: Any, label: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise RegistryError(f"{label}: ungültiges Datum") from None


def load(directory: Path) -> Registry:
    """Lädt ``registry.yaml`` und ``workflow.yaml`` aus *directory* und prüft beide vollständig."""
    registry_path, workflow_path = directory / "registry.yaml", directory / "workflow.yaml"
    try:
        raw_registry = registry_path.read_bytes()
        raw_workflow = workflow_path.read_bytes()
        data = yaml.safe_load(raw_registry)
        flow = yaml.safe_load(raw_workflow)
    except (OSError, yaml.YAMLError) as exc:
        raise RegistryError(f"Register oder Ablauf nicht lesbar: {type(exc).__name__}") from exc
    _require(isinstance(data, dict) and isinstance(flow, dict), "Register und Ablauf müssen Objekte sein")
    prompts_dir = directory / "prompts"
    _require((prompts_dir / "_gemeinsam.md").is_file(), "gemeinsame Systemanweisung fehlt")

    profiles = data.get("model_profiles") or {}
    tools = data.get("tools") or {}
    kinds = tuple(data.get("artifact_kinds") or ())
    human_roles = data.get("human_roles") or {}
    _require(bool(profiles) and bool(tools) and bool(kinds), "Profile, Werkzeuge und Artefaktarten fehlen")
    for name in tools:
        _require(not FORBIDDEN_TOOL.search(name), f"Werkzeug {name} darf keiner Agentenrolle gehören")
    for name, role in human_roles.items():
        _require(
            isinstance(role, dict) and isinstance(role.get("keycloak_roles"), list) and role["keycloak_roles"],
            f"Entscheidungsrolle {name} braucht Keycloak-Rollen",
        )

    agents: dict[str, Agent] = {}
    seen_ids: set[str] = set()
    for entry in data.get("agents") or []:
        _require(isinstance(entry, dict), "Agenteneintrag muss ein Objekt sein")
        required = {"id", "role", "number", "name", "owner", "status", "autonomy", "approved_until",
                    "model_profile", "kind", "mission", "tools", "reads", "prompt", "escalation", "evidence"}
        missing = required - entry.keys()
        _require(not missing, f"Agent {entry.get('id')}: Pflichtfelder fehlen: {sorted(missing)}")
        agent_id, role = str(entry["id"]), str(entry["role"])
        _require(bool(SAFE_ID.fullmatch(agent_id)) and bool(SAFE_ID.fullmatch(role)), "ungültige Agenten-ID")
        _require(agent_id not in seen_ids and role not in agents, f"Agent {agent_id} doppelt")
        _require(entry["status"] in STATUSES, f"Agent {agent_id}: unbekannter Status")
        _require(entry["autonomy"] in AGENT_AUTONOMY, f"Agent {agent_id}: Stufe A4 oder unbekannt")
        _require(entry["kind"] in KINDS, f"Agent {agent_id}: unbekannte Art")
        profile = profiles.get(entry["model_profile"])
        _require(isinstance(profile, dict), f"Agent {agent_id}: unbekanntes Modellprofil")
        unknown_tools = set(entry["tools"]) - set(tools)
        _require(not unknown_tools, f"Agent {agent_id}: unbekannte Werkzeuge {sorted(unknown_tools)}")
        unknown_kinds = set(entry["reads"]) - set(kinds)
        _require(not unknown_kinds, f"Agent {agent_id}: unbekannte Artefaktarten {sorted(unknown_kinds)}")
        prompt_file = (directory / str(entry["prompt"])).resolve()
        _require(prompt_file.is_relative_to(prompts_dir.resolve()) and prompt_file.is_file(),
                 f"Agent {agent_id}: Rollenanweisung fehlt")
        seen_ids.add(agent_id)
        agents[role] = Agent(
            id=agent_id,
            role=role,
            number=int(entry["number"]),
            name=str(entry["name"]),
            owner=str(entry["owner"]),
            status=str(entry["status"]),
            autonomy=str(entry["autonomy"]),
            approved_until=_as_date(entry["approved_until"], agent_id),
            model_profile=str(entry["model_profile"]),
            family=str(profile["family"]),
            gateway_alias=str(profile["gateway_alias"]),
            kind=str(entry["kind"]),
            mission=" ".join(str(entry["mission"]).split()),
            tools=tuple(entry["tools"]),
            reads=tuple(entry["reads"]),
            prompt_file=prompt_file,
            reviewed_by=entry.get("reviewed_by"),
            escalation=str(entry["escalation"]),
            evidence=str(entry["evidence"]),
            limits=dict(entry.get("limits") or {}),
            umbrella=str(entry.get("umbrella") or ""),
        )
    _require(bool(agents), "Register enthält keine Agenten")
    for agent in agents.values():
        if agent.reviewed_by:
            reviewer = agents.get(agent.reviewed_by)
            _require(reviewer is not None, f"Agent {agent.id}: Prüfrolle fehlt")
            _require(independent(agent, reviewer), f"Agent {agent.id}: Prüfer nicht unabhängig")

    classes = flow.get("classes") or {}
    _require({"standard", "neue_funktion", "kritisch"} <= set(classes), "Änderungsklassen unvollständig")
    for name, spec in classes.items():
        gates = set(spec.get("human_gates") or ())
        _require(gates <= set(GATES), f"Klasse {name}: unbekanntes Gate")
        _require({"G4", "G5"} <= gates, f"Klasse {name}: Fachabnahme und Produktion bleiben menschlich")

    steps: list[Step] = []
    produced: set[str] = {"auftrag"}  # Eingang des Laufs, kein Agentenergebnis
    for raw in flow.get("steps") or []:
        _require(isinstance(raw, dict) and raw.get("kind") in STEP_KINDS, "ungültiger Ablaufschritt")
        step = Step(
            id=str(raw["id"]),
            label=str(raw.get("label") or raw["id"]),
            kind=str(raw["kind"]),
            role=raw.get("role"),
            subject=raw.get("subject"),
            produces=raw.get("produces"),
            decider=raw.get("decider"),
            requires=tuple(raw.get("requires") or ()),
            freeze_baseline=bool(raw.get("freeze_baseline", False)),
            bind_digest=raw.get("bind_digest"),
            on_rework=dict(raw.get("on_rework") or {}),
            on_failure=dict(raw.get("on_failure") or {}),
        )
        _require(all(s.id != step.id for s in steps), f"Schritt {step.id} doppelt")
        if step.kind in {"create", "review"}:
            agent = agents.get(step.role or "")
            _require(agent is not None, f"Schritt {step.id}: Rolle fehlt im Register")
            _require(agent.kind == step.kind, f"Schritt {step.id}: Art passt nicht zur Rolle")
            _require(step.produces in kinds, f"Schritt {step.id}: unbekanntes Ergebnis")
        if step.kind == "review":
            _require(step.subject in produced, f"Schritt {step.id}: Prüfgegenstand entsteht nicht vorher")
            creator = next((s for s in steps if s.produces == step.subject), None)
            if creator is not None and creator.role:
                _require(
                    independent(agents[creator.role], agents[step.role or ""]),
                    f"Schritt {step.id}: Prüfer und Ersteller gehören zur selben Modellfamilie",
                )
        if step.kind == "gate":
            _require(step.id in GATES, f"Gate {step.id} unbekannt")
            _require(step.decider in human_roles, f"Gate {step.id}: Entscheider fehlt")
            _require(set(step.requires) <= produced, f"Gate {step.id}: Voraussetzung entsteht nicht vorher")
        for target in (step.on_rework.get("back_to"), step.on_failure.get("back_to")):
            if target:
                _require(any(s.id == target for s in steps), f"Schritt {step.id}: Rücksprungziel fehlt")
        decision = step.on_rework.get("decision")
        if decision:
            _require(decision in human_roles, f"Schritt {step.id}: Entscheidungsrolle fehlt")
        if step.produces:
            produced.add(step.produces)
        if step.kind == "gate" and step.freeze_baseline:
            produced.add("baseline")
        steps.append(step)
    _require([s.id for s in steps if s.kind == "gate"] == list(GATES), "Gates G1 bis G5 müssen in Reihenfolge folgen")
    for agent in agents.values():
        _require(set(agent.reads) <= produced, f"Agent {agent.id}: liest Artefakte, die nie entstehen")
    # Akzeptanztests bleiben unabhängig von der Implementierung (Teil 04, Test 08/19).
    tester = agents.get("akzeptanztest")
    if tester:
        _require("implementierung" not in tester.reads, "Akzeptanztest-Agent darf keine Implementierung lesen")

    budget = dict(flow.get("budget") or {})
    _require(all(isinstance(budget.get(key), int) and budget[key] > 0
                 for key in ("max_model_calls", "max_output_tokens")), "Laufbudget fehlt")
    rounds = flow.get("max_correction_rounds")
    _require(isinstance(rounds, int) and 1 <= rounds <= 5, "max_correction_rounds muss 1 bis 5 sein")

    digest = hashlib.sha256(raw_registry + b"\0" + raw_workflow).hexdigest()
    return Registry(
        version=int(data.get("version", 0)),
        register_id=str(data.get("register_id", "")),
        policy_version=str(data.get("policy_version", "")),
        agents=agents,
        human_roles=human_roles,
        tools=tools,
        artifact_kinds=kinds,
        productive_agents=tuple(data.get("productive_agents") or ()),
        steps=tuple(steps),
        classes=classes,
        max_correction_rounds=rounds,
        budget=budget,
        prompts_dir=prompts_dir,
        digest=digest,
    )


def independent(author: Agent, reviewer: Agent) -> bool:
    """Prüfer gehören zu einer anderen Modellfamilie und einer anderen Identität (Teil 01)."""
    return author.role != reviewer.role and author.family.casefold() != reviewer.family.casefold()
