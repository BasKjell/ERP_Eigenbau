"""Agentenregister und Ablauf laden und fail-closed validieren (KI-U-02, Teil 01/09)."""

from __future__ import annotations

import hashlib
import json
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
# Zusätzliche Entscheidungspunkte nach dem V-Modell (Teil 02): EP1 „Projekt definiert“ vor G1.
EXTRA_GATES = ("EP1",)
PROJECT_CLASSES = ("S", "M", "L")
CRITICALITIES = ("K1", "K2", "K3")
# Werkzeuge, die keine Agentenrolle besitzen darf (Teil 09).
FORBIDDEN_TOOL = re.compile(r"(approve|freigabe|merge|delete|loesch|deploy|admin|release)", re.I)
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}")
DATA_CLASSES = ("oeffentlich", "intern", "vertraulich")
# Felder, die ein Administrator in der Agentenzentrale übersteuern darf. Kennung, Rolle, Nummer und Art
# (Ersteller/Prüfer) bleiben fest, weil der Ablauf darauf aufbaut. Jede Übersteuerung läuft durch
# dieselbe Prüfung wie das Register und ändert den Registerstand (Digest).
EDITABLE_FIELDS = {
    "name": "text", "owner": "text", "deputy": "text", "status": "choice", "autonomy": "choice",
    "approved_until": "date", "model_profile": "choice", "mission": "longtext", "tools": "list",
    "reads": "list", "data_classes": "list", "limits": "limits", "escalation": "longtext",
    "evidence": "longtext", "prompt_text": "prompt",
}


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
    data_classes: tuple[str, ...] = ()
    deputy: str = ""

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
            "deputy": self.deputy,
            "reads": list(self.reads),
            "data_classes": list(self.data_classes),
            "limits": dict(self.limits),
            "prompt_file": self.prompt_file.name,
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
    when: dict[str, tuple[str, ...]] = field(default_factory=dict)
    ep: str = ""
    completes_for: tuple[str, ...] = ()

    def applies(self, auftrag: dict[str, Any]) -> bool:
        """Gilt dieser Schritt für den Zuschnitt des Auftrags (Projektklasse)?"""
        allowed = self.when.get("project_class")
        if any(auftrag.get(flag) for flag in self.when.get("flag", ())):
            return True  # z. B. Integrationspaket eines L-Projekts: Integrationstests trotz Kurzweg
        return not allowed or str(auftrag.get("project_class") or "S") in allowed


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
    # Geprüfte Übersteuerungen aus der Agentenzentrale (Rolle -> Feld -> Wert), Rollenanweisung als Text.
    overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

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
        return common + "\n\n" + self.role_prompt(role)

    def role_prompt(self, role: str) -> str:
        """Rollenanweisung: übersteuerter Text oder die Datei aus dem Register."""
        text = (self.overrides.get(role) or {}).get("prompt_text")
        return str(text) if text else self.agent(role).prompt_file.read_text(encoding="utf-8")

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
                    "ep": step.ep,
                    "when": {k: list(v) for k, v in step.when.items()},
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


def check_override(field_name: str, value: Any) -> Any:
    """Form eines übersteuerten Feldes prüfen; Inhalte prüft danach das Laden des Registers."""
    _require(field_name in EDITABLE_FIELDS, f"Feld {field_name} ist nicht änderbar")
    kind = EDITABLE_FIELDS[field_name]
    if kind == "text":
        _require(isinstance(value, str) and len(value.strip()) <= 80, f"{field_name}: Text bis 80 Zeichen")
        _require(field_name == "deputy" or len(value.strip()) >= 2, f"{field_name}: Text fehlt")
        return value.strip()
    if kind in {"choice", "date"}:
        _require(isinstance(value, str) and 1 <= len(value) <= 40, f"{field_name}: Auswahl fehlt")
        return value
    if kind == "longtext":
        _require(isinstance(value, str) and 3 <= len(value.strip()) <= 1500, f"{field_name}: 3 bis 1500 Zeichen")
        return " ".join(value.split())
    if kind == "list":
        _require(isinstance(value, list) and all(isinstance(v, str) and SAFE_ID.fullmatch(v) for v in value),
                 f"{field_name}: Liste von Kennungen erwartet")
        return sorted(set(value), key=value.index)
    if kind == "limits":
        _require(isinstance(value, dict) and all(
            isinstance(k, str) and re.fullmatch(r"max_[a-z_]{2,40}", k) and isinstance(v, int)
            and not isinstance(v, bool) and 0 <= v <= 1000 for k, v in value.items()),
            "limits: Name max_… und ganze Zahl 0 bis 1000")
        return dict(value)
    _require(isinstance(value, str) and 20 <= len(value) <= 20000, "Rollenanweisung: 20 bis 20000 Zeichen")
    return value


def load(directory: Path, overrides: dict[str, dict[str, Any]] | None = None) -> Registry:
    """Lädt ``registry.yaml`` und ``workflow.yaml`` aus *directory* und prüft beide vollständig.

    *overrides* sind Übersteuerungen aus der Agentenzentrale. Sie werden vor der Prüfung eingemischt;
    ein Register, das mit ihnen ungültig wäre, wird abgewiesen.
    """
    overrides = {str(role): dict(values) for role, values in (overrides or {}).items() if values}
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

    known_roles = {str(e.get("role")) for e in data.get("agents") or [] if isinstance(e, dict)}
    unknown_roles = set(overrides) - known_roles
    _require(not unknown_roles, f"Übersteuerung für unbekannte Rollen {sorted(unknown_roles)}")
    agents: dict[str, Agent] = {}
    seen_ids: set[str] = set()
    for entry in data.get("agents") or []:
        _require(isinstance(entry, dict), "Agenteneintrag muss ein Objekt sein")
        changes = overrides.get(str(entry.get("role")), {})
        if changes:
            entry = {**entry, **{k: check_override(k, v) for k, v in changes.items() if k != "prompt_text"}}
            if "prompt_text" in changes:
                check_override("prompt_text", changes["prompt_text"])
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
            data_classes=tuple(str(c) for c in entry.get("data_classes") or ()),
            deputy=str(entry.get("deputy") or ""),
        )
        _require(set(agents[role].data_classes) <= set(DATA_CLASSES), f"Agent {agent_id}: unbekannte Datenklasse")
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
        _require(gates <= set(GATES) | set(EXTRA_GATES), f"Klasse {name}: unbekanntes Gate")
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
            when={str(k): tuple(str(x) for x in v) for k, v in dict(raw.get("when") or {}).items()},
            ep=str(raw.get("ep") or ""),
            completes_for=tuple(str(x) for x in raw.get("completes_for") or ()),
        )
        _require(set(step.when) <= {"project_class", "flag"}, f"Schritt {step.id}: unbekannte Bedingung")
        _require(set(step.when.get("flag", ())) <= {"integration_required"}, f"Schritt {step.id}: unbekannte Kennzeichnung")
        _require(set(step.when.get("project_class", ())) <= set(PROJECT_CLASSES),
                 f"Schritt {step.id}: unbekannte Projektklasse")
        _require(set(step.completes_for) <= set(PROJECT_CLASSES) and (not step.completes_for or step.kind == "gate"),
                 f"Schritt {step.id}: completes_for nur an Gates mit Projektklassen")
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
            _require(step.id in GATES or step.id in EXTRA_GATES, f"Gate {step.id} unbekannt")
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
    _require([s.id for s in steps if s.kind == "gate" and s.id in GATES] == list(GATES),
             "Gates G1 bis G5 müssen in Reihenfolge folgen")
    gate_order = [s.id for s in steps if s.kind == "gate"]
    if "EP1" in gate_order:
        _require(gate_order.index("EP1") < gate_order.index("G1"), "EP1 muss vor G1 liegen")
        _require(all("EP1" in spec.get("human_gates", ()) for spec in classes.values()),
                 "EP1 „Projekt definiert“ entscheidet in jeder Klasse ein Mensch")
    for agent in agents.values():
        _require(set(agent.reads) <= produced, f"Agent {agent.id}: liest Artefakte, die nie entstehen")
    # Akzeptanztests bleiben unabhängig von der Implementierung (Teil 04, Test 08/19).
    for name in ("akzeptanztest", "integrationstest"):
        tester = agents.get(name)
        if tester:
            _require("implementierung" not in tester.reads, f"{tester.name} darf keine Implementierung lesen")

    budget = dict(flow.get("budget") or {})
    _require(all(isinstance(budget.get(key), int) and budget[key] > 0
                 for key in ("max_model_calls", "max_output_tokens")), "Laufbudget fehlt")
    rounds = flow.get("max_correction_rounds")
    _require(isinstance(rounds, int) and 1 <= rounds <= 5, "max_correction_rounds muss 1 bis 5 sein")

    # Rollenanweisungen gehören zum Rollenvertrag (KI-U-05): jede Änderung ändert den Registerstand.
    prompt_bytes = b"".join(path.name.encode() + b"\0" + path.read_bytes() for path in sorted(prompts_dir.glob("*.md")))
    material = raw_registry + b"\0" + raw_workflow + b"\0" + prompt_bytes
    if overrides:  # ohne Übersteuerung bleibt der Digest des Registers unverändert
        material += b"\0" + json.dumps(overrides, sort_keys=True, ensure_ascii=False).encode()
    digest = hashlib.sha256(material).hexdigest()
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
        overrides=overrides,
    )


def independent(author: Agent, reviewer: Agent) -> bool:
    """Prüfer gehören zu einer anderen Modellfamilie und einer anderen Identität (Teil 01)."""
    return author.role != reviewer.role and author.family.casefold() != reviewer.family.casefold()
