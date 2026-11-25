"""Ablaufsteuerung: Fachauftrag -> Rollen -> Gates -> Fachabnahme (KI-Entwicklungskonzept Teil 02/03).

Die Engine ist deterministisch. Sie entscheidet anhand von ``agents/workflow.yaml`` und dem
gespeicherten Zustand, welche Rolle als Nächstes arbeitet. Modelle liefern nur Text; die Engine
prüft den Ergebnisvertrag, führt erlaubte Werkzeugaufrufe mit der Rollenidentität aus, bindet
Prüfungen und Abnahmen an Version und Digest und legt menschliche Entscheidungen in die
Entscheidungs-Inbox.
"""

from __future__ import annotations

import difflib
import fnmatch
import json
import re
import subprocess
import threading
import time
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from . import fachagenten as fa
from . import registry as registry_module
from .adoption import Adoption, Preview
from .contract import ARTIFACTS, REVIEW_ONLY, ContractError, Handoff, extract_json, validate
from .providers import AgentReply, AgentRequest, Provider, ProviderError
from .registry import (
    AGENT_AUTONOMY,
    CRITICALITIES,
    DATA_CLASSES,
    EDITABLE_FIELDS,
    PROJECT_CLASSES,
    STATUSES,
    Agent,
    Registry,
    RegistryError,
    Step,
    check_override,
)
from .rm import RM, RMConflict, RMError
from .sandbox import Sandbox, SandboxError, validate_path
from .store import OPEN_RUN_STATES, Store, digest_of, iso
from .uicheck import UiCheckError, UiRunner, scenarios_from

ORCHESTRATOR = ("orchestrator", "FLOW-ORCHESTRATOR")
# Laufsteuerung (Pause, Fortsetzen, Abbrechen): Plattformbetrieb und Tech Lead (KI-EK Teil 02).
CONTROL_ROLES = frozenset({"platform-admin", "it-user", "work-admin", "flow-techlead"})
# Aufsicht sieht alle Projekte, entscheidet aber nur in ihrer eigenen Rolle (Projektkatalog, agents/projects.json).
OVERSIGHT_ROLES = frozenset({"platform-admin", "flow-isb", "flow-gf"})
CATALOG_OWNER = {"username": "projektkatalog", "name": "Projektkatalog"}
# Agenteneigenschaften ändern nur Administratoren; alle anderen sehen sie nur an.
CONFIG_ADMIN_ROLES = frozenset({"platform-admin"})
# Projektübergreifende Betriebsbefugnis (Laufabbruch ohne Projektrecht): nur Plattformbetrieb.
CROSS_PROJECT_OPERATIONS = frozenset({"platform-admin"})
# V-Ebenen, deren Arbeitspaket den projektweiten Integrationsnachweis eines L-Projekts liefert.
INTEGRATION_LEVELS = frozenset({"software_integration", "systemintegration"})
# Abschlussarten eines Laufs (nur „produktion“ ist eine Auslieferung nach G5).
COMPLETIONS = ("produktion", "projektplanung", "katalog", "ende")
GATE_BACK_TO = {"EP1": "projektplanung", "G1": "anforderungen", "G2": "architektur", "G3": "entwicklung", "G4": "entwicklung"}
# Domänenprofile (KI-Softwareentwicklung Teil 07).
DOMAINS = ("it", "produkt", "pruefsoftware", "werkzeug")
CLASS_ORDER = ("standard", "neue_funktion", "kritisch")
GATE_IDS = frozenset({"EP1", "G1", "G2", "G3", "G4", "G5"})
MAX_INVALID_ATTEMPTS = 2


class EngineError(RuntimeError):
    """Fachlich unzulässige Aktion (z. B. fehlende Befugnis, falscher Zustand)."""


class Engine:
    def __init__(
        self,
        registry: Registry,
        store: Store,
        providers: dict[str, Provider],
        profile_providers: dict[str, str],
        rm: RM,
        sandbox: Sandbox | None = None,
        *,
        scopes: dict[str, dict[str, Any]] | None = None,
        demo_mode: bool = False,
        adoption: Adoption | None = None,
        preview: Preview | None = None,
        budgets: dict[str, dict[str, int]] | None = None,
        escalation: dict[str, Any] | None = None,
        ui_runner: UiRunner | None = None,
        projects: dict[str, dict[str, Any]] | None = None,
        opencode_roles: tuple[str, ...] = ("entwicklung",),
    ) -> None:
        missing = {profile for profile in {a.model_profile for a in registry.agents.values()}
                   if profile_providers.get(profile) not in providers}
        if missing:
            raise EngineError(f"kein Provider für Modellprofile {sorted(missing)}")
        self.registry, self.store, self.providers = registry, store, providers
        self.profile_providers, self.rm, self.sandbox = profile_providers, rm, sandbox
        self.demo_mode = demo_mode
        self.scopes = scopes or {}
        self.adoption, self.preview, self.budgets = adoption, preview, budgets or {}
        self.escalation = escalation or {}
        self.ui_runner = ui_runner
        # Umsetzung „opencode“: diese Rollen arbeiten über den lokalen OpenCode-Worker (opencode.py).
        self.opencode_roles = tuple(opencode_roles)
        # Gespeicherte Übersteuerungen der Agenteneigenschaften einmischen (geprüft wie das Register).
        self.override_error = ""
        stored = self.store.agent_overrides()
        if stored:
            try:
                self.registry = registry_module.load(self.registry.prompts_dir.parent, stored)
            except RegistryError as exc:
                self.override_error = f"Übersteuerungen nicht angewendet: {exc}"
        # Projektkatalog mit Projektrechten. Ohne Katalog gilt der bisherige Ablauf ohne Projektprüfung.
        self.projects = dict(projects or {})
        for code, spec in self.projects.items():
            if not re.fullmatch(r"[A-Z][A-Z0-9-]{2,30}", code):
                raise EngineError(f"Projektkürzel {code} ungültig")
            if spec.get("criticality", "K1") not in CRITICALITIES or spec.get("domain", "it") not in DOMAINS:
                raise EngineError(f"Projekt {code}: Kritikalität oder Domäne ungültig")
            unknown = [s for s in self.project_scopes(code) if s not in self.scopes]
            if not self.project_scopes(code) or unknown:
                raise EngineError(f"Projekt {code}: Änderungsbereiche fehlen oder sind unbekannt {unknown}")
        if self.sandbox is not None:
            for scope in self.scopes.values():
                for path in [*scope.get("paths", []), *scope.get("reads", [])]:
                    validate_path(path, self.sandbox.allowed_prefixes)  # fail closed beim Start
        self.lock = threading.RLock()
        self._migrate_step_ids()

    def _migrate_step_ids(self) -> None:
        """Altaufträge ohne stabile Schritt-ID: aus Index (gleicher Registerstand) oder offenem Gate ableiten."""
        for run in self.store.runs(limit=10_000):
            if run.get("step_id") or run["status"] not in OPEN_RUN_STATES:
                continue
            step_id = ""
            if run["registry_digest"] == self.registry.digest:
                step_id = self.registry.steps[run["step_index"]].id if run["step_index"] < len(self.registry.steps) \
                    else "fertig"
            else:
                gate = next((d for d in self.store.decisions(status="offen", run_id=run["id"]) if d["gate"] in GATE_IDS),
                            None)
                step_id = gate["step_id"] if gate else ""
            if step_id:
                self.store.update_run(run["id"], step_id=step_id)

    def _update_run(self, run_id: str, **fields: Any) -> None:
        """Lauf ändern; ein neuer Schrittindex bekommt immer die stabile Schritt-ID dazu."""
        if "step_index" in fields and "step_id" not in fields:
            index = int(fields["step_index"])
            fields["step_id"] = self.registry.steps[index].id if index < len(self.registry.steps) else "fertig"
        if fields.get("status") == "abgeschlossen" and "completion" not in fields:
            fields["completion"] = "ende"
        self.store.update_run(run_id, **fields)

    def _open_decision(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("registry_digest", self.registry.digest)
        return self.store.open_decision(*args, **kwargs)

    def _current_step_id(self, run: dict[str, Any]) -> str:
        """Stabile Schritt-ID eines Laufs. Leer, wenn sie sich nach einer Registeränderung nicht mehr ableiten lässt."""
        if run.get("step_id"):
            return str(run["step_id"])
        if run["registry_digest"] == self.registry.digest:
            return self.registry.steps[run["step_index"]].id if run["step_index"] < len(self.registry.steps) else "fertig"
        return ""

    def _step_by_id(self, step_id: str) -> Step | None:
        return next((s for s in self.registry.steps if s.id == step_id), None)
    # =================================================================================
    # Aufträge
    # =================================================================================
    def submit(self, values: dict[str, Any], user: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        self._authorize(user, "product-owner")
        auftrag = self._validated_auftrag(values, user)
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{8,80}", idempotency_key):
            raise EngineError("Idempotenzschlüssel fehlt oder ist ungültig")
        with self.lock:
            try:
                return self.store.create_run(
                    title=auftrag["title"],
                    change_class=auftrag["change_class"],
                    auftrag=auftrag,
                    requested_by=_person(user),
                    registry_digest=self.registry.digest,
                    idempotency_key=idempotency_key,
                    step_id=self.registry.steps[0].id,
                )
            except ValueError as exc:
                raise EngineError(str(exc)) from None

    def _validated_auftrag(self, values: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        allowed = {"title", "goal", "user_group", "behavior", "exclusions", "success_example", "data_class",
                   "change_class", "scope", "project", "execution", "project_class", "criticality", "domain"}
        unknown = set(values) - allowed
        if unknown:
            raise EngineError(f"unbekannte Auftragsfelder {sorted(unknown)}")

        def text(name: str, low: int, high: int, required: bool = True) -> str:
            value = str(values.get(name) or "").strip()
            if (required and len(value) < low) or len(value) > high:
                raise EngineError(f"{name}: {low} bis {high} Zeichen erforderlich")
            return value

        project = str(values.get("project") or "FLOW-PLATFORM")
        if not re.fullmatch(r"[A-Z][A-Z0-9-]{2,30}", project):
            raise EngineError("Projektkürzel ungültig")
        catalog = self.projects.get(project)
        if self.projects:
            if catalog is None:
                raise EngineError(f"Projekt {project} steht nicht im Projektkatalog")
            self._require_project(user, project, "aendern")
            values = dict(values)
            if not values.get("domain"):
                values["domain"] = catalog.get("domain", "it")
            floor = str(catalog.get("criticality", "K1"))
            given = str(values.get("criticality") or "")
            if floor != "K1" and (not given or (given in CRITICALITIES and
                                                CRITICALITIES.index(given) < CRITICALITIES.index(floor))):
                values["criticality"] = floor  # das Projekt gibt die Mindest-Kritikalität vor
        project_class, criticality, change_class = self._classify(values)
        domain = str(values.get("domain") or "it")
        if domain not in DOMAINS:
            raise EngineError(f"Domäne muss einer von {', '.join(DOMAINS)} sein")
        data_class = str(values.get("data_class") or "intern")
        if data_class not in DATA_CLASSES:
            raise EngineError("Datenklasse muss oeffentlich, intern oder vertraulich sein")
        if data_class == "vertraulich" and change_class == "standard":
            raise EngineError("vertrauliche Daten sind keine Standardänderung")
        scope_id = str(values.get("scope") or "")
        scope = self.scopes.get(scope_id)
        if scope is None:
            raise EngineError("Änderungsbereich (scope) fehlt oder ist nicht freigegeben")
        if catalog is not None and scope_id not in self.project_scopes(project):
            raise EngineError(f"Änderungsbereich {scope_id} gehört nicht zum Projekt {project}")
        checked = list(scope.get("paths", []))
        reads = [path for path in scope.get("reads", []) if path not in checked]
        if self.sandbox is not None and checked:
            try:
                size = sum(len(text or "") for text in
                           self.sandbox.originals(self.sandbox.base_commit(), [*checked, *reads]).values())
            except SandboxError as exc:
                raise EngineError(f"Änderungsbereich nicht lesbar: {exc}") from None
            limit = self._scope_limit(scope, str(values.get("execution") or "automatisch"), data_class)
            if size > limit:
                raise EngineError("Änderungsbereich ist zu groß für die lokalen Modelle; bitte einen kleineren "
                                  "Bereich wählen oder die Umsetzung durch Codex/Claude zulassen")
        execution = str(values.get("execution") or "automatisch")
        if execution not in {"automatisch", "lokal", "abo", "opencode"}:
            raise EngineError("Umsetzung muss automatisch, lokal, abo oder opencode sein")
        if execution == "opencode" and "opencode" not in self.providers:
            raise EngineError("Der OpenCode-Worker ist nicht eingerichtet (opencode.enabled)")
        if execution == "abo" and data_class == "vertraulich":
            raise EngineError("vertrauliche Daten werden nur lokal verarbeitet")
        return {
            "title": text("title", 5, 160),
            "goal": text("goal", 10, 2000),
            "user_group": text("user_group", 2, 160),
            "behavior": text("behavior", 10, 3000),
            "exclusions": text("exclusions", 0, 1500, required=False),
            "success_example": text("success_example", 5, 1500),
            "data_class": data_class,
            "change_class": change_class,
            "project_class": project_class,
            "criticality": criticality,
            "domain": domain,
            "scope": scope_id,
            "scope_label": str(scope.get("label", scope_id)),
            "paths": sorted(set(checked)),
            "reference_paths": sorted(set(reads)),
            "project": project,
            "execution": execution,
            "owner": _person(user)["name"],
            # Ausdrücklich verlangte Änderungsklasse: wird an Arbeitspakete vererbt (nur Verschärfung).
            "change_class_explicit": str(values.get("change_class") or ""),
            # Bindung an den Projektkatalog bleibt erhalten, auch wenn Katalog oder Projekt später fehlen.
            "catalog_bound": bool(self.projects),
        }

    def _classify(self, values: dict[str, Any]) -> tuple[str, str, str]:
        """Einstufung nach Teil 01: Projektklasse und Kritikalität bestimmen die Änderungsklasse.

        K2/K3 -> kritisch, sonst S -> standard und M/L -> neue_funktion. Eine ausdrücklich genannte
        Änderungsklasse darf den Weg nur verschärfen. Ohne Einstufung gilt der bisherige Kurzweg (S).
        """
        explicit = values.get("change_class")
        if explicit is not None and str(explicit) not in self.registry.classes:
            raise EngineError("unbekannte Änderungsklasse")
        if not values.get("project_class"):
            # Ohne Projektklasse bleibt der bisherige Standard „neue_funktion“ (menschliches G1); eine
            # Kritikalität allein darf den Weg nur verschärfen, nie zur Standardänderung abschwächen.
            criticality = str(values.get("criticality") or ("K2" if explicit == "kritisch" else "K1"))
            if criticality not in CRITICALITIES:
                raise EngineError("Kritikalität muss K1, K2 oder K3 sein")
            change_class = "kritisch" if criticality in {"K2", "K3"} else str(explicit or "neue_funktion")
            return "S", criticality, change_class
        project_class = str(values.get("project_class") or "S")
        criticality = str(values.get("criticality") or "K1")
        if project_class not in PROJECT_CLASSES:
            raise EngineError("Projektklasse muss S, M oder L sein")
        if criticality not in CRITICALITIES:
            raise EngineError("Kritikalität muss K1, K2 oder K3 sein")
        derived = "kritisch" if criticality in {"K2", "K3"} else "standard" if project_class == "S" else "neue_funktion"
        if explicit and CLASS_ORDER.index(str(explicit)) > CLASS_ORDER.index(derived):
            derived = str(explicit)
        return project_class, criticality, derived

    # =================================================================================
    # Ein Arbeitsschritt
    # =================================================================================
    def recover(self) -> None:
        """Nach Neustart: unterbrochene Schritte markieren; idempotente Schritte laufen erneut.

        Wartet ein Lauf ohne offene Entscheidung (Absturz zwischen Entscheidung und Folgeschritt),
        wird derselbe Schritt erneut eingeplant; ein Gate öffnet dann eine neue Entscheidung.
        """
        for step in self.store.running_steps():
            self.store.finish_step(step["id"], "unterbrochen", error="Dienst wurde während des Schritts beendet")
            self.store.event(step["run_id"], "wiederanlauf", "orchestrator", step["role"] or step["step_id"],
                             f"Schritt {step['step_id']} nach Neustart erneut eingeplant")
        for run in self.store.runs(limit=10_000):
            if run["status"] in {"wartet", "blockiert"} and not self.store.decisions(status="offen", run_id=run["id"]):
                self._update_run(run["id"], status="aktiv", reason="")
                self.store.event(run["id"], "wiederanlauf", "orchestrator", "orchestrator",
                                 "Lauf wartete ohne offene Entscheidung; Schritt erneut eingeplant")

    def cycle(self) -> bool:
        """Bearbeitet höchstens einen Schritt. Liefert True, wenn Arbeit erledigt wurde."""
        if self.store.control("global", "bereit") != "bereit":
            return False
        if self.process_business_job():
            return True
        with self.lock:
            run = self.store.next_active()
            if run is None:
                return False
            if run["registry_digest"] != self.registry.digest:
                self._block(run, "Agentenregister oder Ablauf wurden geändert; Lauf neu bewerten",
                            "blockade", step_id=self._current_step_id(run))
                return True
            if run["step_index"] >= len(self.registry.steps):
                self._update_run(run["id"], status="abgeschlossen")
                return True
            step = self._step(run)
            if not step.applies(run["auftrag"]):
                self._skip(run)
                return True
        if step.kind in {"create", "review"}:
            self._agent_step(run, step)
        elif step.kind == "check":
            self._check_step(run, step)
        else:
            with self.lock:
                self._gate_step(run, step)
        return True

    def _step(self, run: dict[str, Any]) -> Step:
        return self.registry.steps[run["step_index"]]

    def _next_applicable(self, run: dict[str, Any], index: int) -> int:
        steps = self.registry.steps
        while index < len(steps) and not steps[index].applies(run["auftrag"]):
            index += 1
        return index

    def _skip(self, run: dict[str, Any]) -> None:
        """Schritte, die für die Projektklasse nicht gelten, ohne Arbeit überspringen."""
        step = self._step(run)
        index = self._next_applicable(run, run["step_index"])
        if index >= len(self.registry.steps):
            self._update_run(run["id"], status="abgeschlossen", step_index=index, reason="")
            return
        self._update_run(run["id"], step_index=index)
        self.store.event(run["id"], "uebersprungen", "orchestrator", step.role or step.id,
                         f"{step.label} entfällt für Projektklasse {run['auftrag'].get('project_class', 'S')}",
                         {"step": step.id})

    # -- Agentenschritt ------------------------------------------------------------------
    def _agent_step(self, run: dict[str, Any], step: Step) -> None:
        agent = self.registry.agent(step.role or "")
        if not agent.active():
            self._block(run, f"{agent.name} ist im Register nicht aktiv oder die Freigabe ist abgelaufen",
                        "blockade", step_id=step.id)
            return
        if self.store.control(f"agent:{agent.role}") == "pausiert":
            self._update_run(run["id"], status="pausiert", reason=f"{agent.name} ist pausiert")
            self.store.event(run["id"], "pausiert", "orchestrator", agent.role, f"{agent.name} ist pausiert; Lauf hält an")
            return
        budget = self._budget(run)
        if run["model_calls"] >= budget["max_model_calls"] or run["output_tokens"] >= budget["max_output_tokens"]:
            self._block(run, "Laufbudget erschöpft", "blockade", step_id=step.id)
            return
        local = self.providers[self.profile_providers[agent.model_profile]]
        provider, why = self._provider_for(run, step, agent)
        if provider is not local:
            self.store.event(run["id"], "eskalation", "orchestrator", agent.role,
                             f"{agent.name} arbeitet mit {provider.name}: {why}", {"provider": provider.name})
        try:
            context = self._context(run, step, agent)
        except (SandboxError, OSError) as exc:
            self._block(run, f"Kontext nicht herstellbar: {exc}", "blockade", step_id=step.id)
            return
        system = self.registry.prompt(agent.role)
        user = self._render(run, step, agent, context)
        row = self.store.start_step(run["id"], step.id, agent.role, provider.name, agent.gateway_alias)
        self.store.event(run["id"], "start", agent.role, agent.role, f"{agent.name}: {step.label}",
                         {"step": step.id, "provider": provider.name})
        handoff: Handoff | None = None
        error = ""
        for attempt in range(1, MAX_INVALID_ATTEMPTS + 1):
            request = AgentRequest(run["id"], step.id, agent, system, user, self._max_tokens(agent), context)
            try:
                reply: AgentReply = provider.generate(request)
            except ProviderError as exc:
                if provider is local or not self.escalation.get("fallback_local", True):
                    error = str(exc)
                    break
                self.store.event(run["id"], "eskalation", "orchestrator", agent.role,
                                 f"{provider.name} nicht verfügbar ({exc}); weiter mit dem lokalen Modell",
                                 {"provider": local.name})
                provider = local
                try:
                    reply = provider.generate(request)
                except ProviderError as again:
                    error = str(again)
                    break
            run = self._count(run, reply)
            self.store.record_usage(run["id"], step.id, agent.role, reply.provider, reply.model,
                                    reply.input_tokens, reply.output_tokens, reply.seconds)
            try:
                candidate = validate(extract_json(reply.text), role=agent.role, kind=step.kind,
                                     limit=_limit(agent))
                _require_real_change(agent.role, candidate, context.get("files"))
                handoff = candidate
                break
            except ContractError as exc:
                error = f"Ergebnisvertrag verletzt: {exc}"
                user += ("\n\nDeine letzte Antwort verletzte den Ergebnisvertrag: "
                         f"{exc}. Antworte erneut ausschließlich mit einem gültigen JSON-Objekt.")
                self.store.event(run["id"], "vertrag", "orchestrator", agent.role, f"Übergabe ungültig ({attempt})",
                                 {"error": str(exc)[:300]})
        with self.lock:
            current = self.store.run(run["id"])
            if current["status"] != "aktiv" or current["step_index"] != run["step_index"]:
                self.store.finish_step(row, "verworfen", error="Lauf wurde während des Schritts geändert")
                return
            if handoff is None:
                self.store.finish_step(row, "abgebrochen", error=error)
                self._block(current, f"{agent.name}: {error}", "blockade", step_id=step.id)
                return
            try:
                refs = self._apply_tools(current, step, agent, handoff)
            except (RMError, SandboxError) as exc:
                self.store.finish_step(row, "abgebrochen", summary=handoff.summary, error=str(exc))
                self._block(current, f"{agent.name}: {exc}", "blockade", step_id=step.id)
                return
            content = self._artifact_content(current, step, handoff, refs)
            stored = self.store.add_artifact(current["id"], step.produces or "", agent.role, step.id, content, refs)
            self.store.finish_step(row, handoff.status, summary=handoff.summary, findings=handoff.findings,
                                   questions=handoff.questions)
            self.store.event(current["id"], "ergebnis", agent.role, agent.role,
                             f"{agent.name}: {handoff.summary}",
                             {"status": handoff.status, "artifact": stored["kind"], "version": stored["version"],
                              "findings": len(handoff.findings)})
            self._route(current, step, agent, handoff)

    def _agent_rights(self, agent: Agent) -> dict[str, Any]:
        """Welche Rechte ein Agent über welche technische Rolle hat und wer sein Ergebnis freigibt.

        Rein aus Register und Konfiguration abgeleitet – dieselben Quellen, die Orchestrator,
        FLOWWORK-RM-Adapter und FLOWGATE bei jedem Aufruf durchsetzen.
        """
        tools = [{"name": name, "label": self.registry.tools.get(name, name), "enforced_by": TOOL_ENFORCER.get(
                  name.split(".", 1)[0], "Orchestrator")} for name in agent.tools]
        steps = self.registry.steps
        decided: list[dict[str, str]] = []
        # relation „freigabe“ nur, wenn das Gate das Ergebnis des Schritts ausdrücklich voraussetzt
        # (gate.requires enthält step.produces); sonst ist es nur der nächste menschliche Entscheidungspunkt.
        for index, step in enumerate(steps):
            if step.role != agent.role:
                continue
            gates = [s for s in steps[index + 1:] if s.kind == "gate"]
            approving = next((g for g in gates if step.produces and step.produces in g.requires), None)
            following = gates[0] if gates else None
            candidates = [
                (approving.decider, approving.id, approving.label,
                 f"{approving.id} setzt das Ergebnis „{step.produces}“ voraus", "freigabe") if approving else (None,) * 5,
                (following.decider, following.id, following.label,
                 "nächster menschlicher Entscheidungspunkt im Ablauf; setzt dieses Ergebnis nicht unmittelbar voraus",
                 "naechste") if following and following is not approving else (None,) * 5,
                (step.on_rework.get("decision"), step.id, step.label, "bei Bedenken des Agenten", "bedenken"),
            ]
            for decider, gate_id, gate_label, why, relation in candidates:
                if decider and not any(d["gate"] == gate_id and d["role"] == decider and d["relation"] == relation
                                       for d in decided):
                    spec = self.registry.human_roles.get(decider, {})
                    decided.append({"gate": gate_id, "gate_label": gate_label, "role": decider,
                                    "label": spec.get("label", decider), "why": why, "relation": relation,
                                    "keycloak_roles": list(spec.get("keycloak_roles", []))})
        approved = {(d["gate"], d["role"]) for d in decided if d["relation"] == "freigabe"}
        decided = [d for d in decided if d["relation"] != "naechste" or (d["gate"], d["role"]) not in approved]
        escalation = (self.escalation.get("roles") or {}).get(agent.role) if self.escalation.get("enabled") else None
        reviewer = self.registry.agents.get(agent.reviewed_by or "") if agent.reviewed_by else None
        repository = []
        if agent.role == "entwicklung":
            repository.append("schreibt nur die freigegebenen Pfade des Auftrags, in einer Sandbox ohne Netz und "
                              "ohne Zugangsdaten; übernommen wird erst nach Fachabnahme als lokaler Branch")
        if agent.role in REFERENCE_READERS:
            repository.append("liest Referenzdateien des Änderungsbereichs (nur lesen)")
        return {
            "identity": {"role": agent.role,
                         "rm_token": f"Kurzzeit-Token für FLOWWORK mit Rolle „{agent.role}“ je Lauf",
                         "gateway_key": f"eigener FLOWGATE-Schlüssel der Rolle „{agent.role}“"},
            "tools": tools,
            "model": {"alias": agent.gateway_alias, "family": agent.family, "profile": agent.model_profile,
                      "escalation": escalation},
            "reads": list(agent.reads),
            "repository": repository,
            "data_classes": list(agent.data_classes),
            "limits": dict(agent.limits),
            "reviewed_by": reviewer.name if reviewer else "",
            "decided_by": decided,
            "never": ["fachlich freigeben", "Gates entscheiden", "mergen oder pushen", "löschen",
                      "ausliefern", "Rechte oder Register ändern"],
            "valid_until": agent.approved_until.isoformat(),
        }

    def _scope_limit(self, scope: dict[str, Any], execution: str, data_class: str) -> int:
        """70k Zeichen für lokale Modelle; komplexe Bereiche mit Abo-Worker dürfen größer sein."""
        esc = self.escalation
        external = (esc.get("enabled") and data_class != "vertraulich" and execution != "lokal"
                    and (execution == "abo" or scope.get("complexity") == "hoch"))
        return int(esc.get("max_scope_chars", 200_000)) if external else 70_000

    def _provider_for(self, run: dict[str, Any], step: Step, agent: Agent) -> tuple[Provider, str]:
        """Komplexe Aufträge an Codex/Claude (Abo-Worker), sonst lokal.

        Komplex heißt: Klasse in ``complex_classes``, Änderungsbereich mit ``complexity: hoch``,
        ausdrücklich „abo“ im Auftrag oder ``after_local_failures`` gescheiterte lokale Versuche
        dieses Schritts. Vertrauliche Daten verlassen den Rechner nie; „lokal“ im Auftrag
        schließt die Eskalation aus.
        """
        local = self.providers[self.profile_providers[agent.model_profile]]
        auftrag = run["auftrag"]
        if auftrag.get("execution") == "opencode" and agent.role in self.opencode_roles and "opencode" in self.providers:
            # Lokal und agentisch: gleiche Modelle und Schlüssel wie FLOWGATE, auch für vertrauliche Daten.
            return self.providers["opencode"], "Umsetzung durch OpenCode (lokal) im Auftrag festgelegt"
        esc = self.escalation
        target = (esc.get("roles") or {}).get(agent.role)
        if not esc.get("enabled") or not target or target not in self.providers:
            return local, ""
        if auftrag.get("data_class") == "vertraulich" or auftrag.get("execution") in {"lokal", "opencode"}:
            return local, ""
        reasons = []
        if auftrag.get("execution") == "abo":
            reasons.append("im Auftrag so festgelegt")
        if run["change_class"] in (esc.get("complex_classes") or []):
            reasons.append(f"Änderungsklasse {run['change_class']}")
        if (self.scopes.get(str(auftrag.get("scope", ""))) or {}).get("complexity") == "hoch":
            reasons.append(f"Änderungsbereich {auftrag.get('scope')} ist als komplex eingestuft")
        limit = int(esc.get("after_local_failures", 0) or 0)
        if limit and self.store.failed_attempts(run["id"], step.id, local.name) >= limit:
            reasons.append(f"{limit} lokale Versuche gescheitert")
        return (self.providers[target], "; ".join(reasons)) if reasons else (local, "")

    def _budget(self, run: dict[str, Any]) -> dict[str, int]:
        """Laufbudget: Ablauf, ggf. je Klasse überschrieben, plus vom Tech Lead gewährte Nachschläge."""
        base = {**self.registry.budget, **self.budgets.get(run["change_class"], {})}
        bonus = run["corrections"].get("budget_bonus", {})
        return {key: int(base[key]) + int(bonus.get(key, 0)) for key in ("max_model_calls", "max_output_tokens")}

    def _count(self, run: dict[str, Any], reply: AgentReply) -> dict[str, Any]:
        calls, tokens = run["model_calls"] + 1, run["output_tokens"] + reply.output_tokens
        self._update_run(run["id"], model_calls=calls, output_tokens=tokens)
        return {**run, "model_calls": calls, "output_tokens": tokens}

    @staticmethod
    def _max_tokens(agent: Agent) -> int:
        return 16000 if agent.role == "entwicklung" else 4096

    def _route(self, run: dict[str, Any], step: Step, agent: Agent, handoff: Handoff) -> None:
        if handoff.status == "fertig":
            self._clear_pending(run, step.id)
            self._advance(run, step, f"{agent.name} übergibt")
            return
        if handoff.status == "entscheidung_offen":
            question = handoff.questions[0]
            decider = question["to"] if question["to"] in self.registry.human_roles else "product-owner"
            self._update_run(run["id"], status="wartet", reason=f"Frage an {decider}")
            self._open_decision(
                run["id"], step.id, "frage", decider, f"Rückfrage von {agent.name}",
                "\n".join(f"- {q['question']}" + (f" ({q['impact']})" if q.get("impact") else "")
                          for q in handoff.questions),
                {"agent": agent.id, "summary": handoff.summary}, actor=agent.role,
            )
            return
        if step.kind == "review" and handoff.status == "nacharbeit":
            back_to = step.on_rework.get("back_to")
            if back_to:
                counts = dict(run["corrections"].get("counts", {}))
                counts[step.id] = counts.get(step.id, 0) + 1
                if counts[step.id] > self.registry.max_correction_rounds:
                    self._set_corrections(run, counts=counts)
                    self._update_run(run["id"], status="wartet", reason="Korrekturlimit erreicht")
                    self._open_decision(
                        run["id"], step.id, "korrekturlimit", "tech-lead",
                        f"{self.registry.max_correction_rounds} Korrekturrunden ohne Erfolg",
                        "Befunde bestehen weiter. Weitere Runde zulassen oder Lauf abbrechen?",
                        {"findings": handoff.blocking_findings(), "back_to": back_to}, actor=agent.role,
                    )
                    return
                self._set_corrections(run, counts=counts, pending={back_to: handoff.blocking_findings()})
                target = self.registry.step_index(back_to)
                creator = self.registry.steps[target].role or back_to
                self._update_run(run["id"], step_index=target, reason="")
                self.store.event(run["id"], "ruecklauf", agent.role, creator,
                                 f"{agent.name} gibt {len(handoff.blocking_findings())} Befund(e) zurück",
                                 {"round": counts[step.id]})
                return
            decider = step.on_rework.get("decision", "tech-lead")
            self._update_run(run["id"], status="wartet", reason=f"Eskalation an {decider}")
            self._open_decision(
                run["id"], step.id, "eskalation", decider, step.on_rework.get("reason", f"Bedenken von {agent.name}"),
                handoff.summary + "\n" + "\n".join(f"- {f['impact']}" for f in handoff.blocking_findings()),
                {"agent": agent.id, "findings": handoff.findings}, actor=agent.role,
            )
            return
        self._block(run, f"{agent.name} meldet {handoff.status}: {handoff.summary}", "blockade", step_id=step.id)

    # -- Kontext und Werkzeuge -----------------------------------------------------------
    def _context(self, run: dict[str, Any], step: Step, agent: Agent) -> dict[str, Any]:
        visible = {kind: self.store.latest_artifact(run["id"], kind) for kind in ("auftrag", *agent.reads)}
        context: dict[str, Any] = {
            "run_id": run["id"],
            "step": step.id,
            "change_class": run["change_class"],
            "auftrag": run["auftrag"],
            "artifacts": {kind: item["content"] for kind, item in visible.items() if item and kind != "auftrag"},
            "digests": {kind: {"version": item["version"], "digest": item["digest"]}
                        for kind, item in visible.items() if item},
            # Nur Antworten auf eigene Rückfragen dieses Schritts. Erledigte Gate-Ablehnungen kommen als
            # findings_to_fix beim Ersteller an; Prüfer sollen den aktuellen Stand prüfen, nicht die Historie.
            "decisions": [
                {"title": d["title"], "outcome": d["outcome"], "comment": d["comment"], "by": d["decided_by"].get("name")}
                for d in self.store.decisions(run_id=run["id"])
                if d["status"] == "angenommen" and d["step_id"] == step.id and d["gate"] in {"frage", "eskalation"}
            ],
        }
        if agent.role == "nachweise":
            # Rolle 10 erhält Metadaten (Version, Digest) aller Belege, Inhalte nur laut Register.
            for kind in self.registry.artifact_kinds:
                item = self.store.latest_artifact(run["id"], kind)
                if item:
                    context["digests"][kind] = {"version": item["version"], "digest": item["digest"]}
        if step.kind == "review":
            context["subject_kind"] = step.subject
        if agent.role == "projektplanung":
            context["scopes"] = {key: str(spec.get("label", key)) for key, spec in self.scopes.items()}
        pending = (run["corrections"].get("pending") or {}).get(step.id)
        if pending:
            context["findings_to_fix"] = pending
        references = list(run["auftrag"].get("reference_paths") or [])
        if references and self.sandbox is not None and agent.role in REFERENCE_READERS:
            # Nur lesen: fachlicher Hintergrund (z. B. Prozessbeschreibungen), nie Änderungsziel.
            context["reference_files"] = self.sandbox.originals(self.sandbox.base_commit(), references)
        if agent.role == "entwicklung":
            paths = list(run["auftrag"].get("paths") or [])
            context["allowed_paths"] = paths
            if self.sandbox is not None and paths:
                base = self.sandbox.base_commit()
                context["base_commit"] = base
                context["files"] = self.sandbox.originals(base, paths)
                # ~20k Token Eingabe plus 16k Token Ausgabe passen in das 40k-Kontextfenster der lokalen Modelle.
                auftrag = run["auftrag"]
                limit = self._scope_limit(self.scopes.get(str(auftrag.get("scope", ""))) or {},
                                          str(auftrag.get("execution") or "automatisch"),
                                          str(auftrag.get("data_class") or "intern"))
                if sum(len(text or "") for text in [*context["files"].values(),
                                                     *(context.get("reference_files") or {}).values()]) > limit:
                    raise SandboxError("freigegebene Dateien sind zu groß für den Modellkontext")
        return context

    def _render(self, run: dict[str, Any], step: Step, agent: Agent, context: dict[str, Any]) -> str:
        data = json.dumps(context, ensure_ascii=False, indent=1)
        if len(data) > 110_000:
            data = data[:110_000] + "\n… (gekürzt)"
        lines = [
            f"Lauf: {run['id']} · Auftrag: {run['auftrag_id']} · Schritt: {step.id} ({step.label})",
            f"Rolle: {agent.id} {agent.name} · Stufe {agent.autonomy} · Klasse: {run['change_class']}",
            "Zuschnitt: Projektklasse {project_class} · Kritikalität {criticality} · Domäne {domain}".format(
                project_class=run["auftrag"].get("project_class", "S"), criticality=run["auftrag"].get("criticality", "K1"),
                domain=run["auftrag"].get("domain", "it")),
        ]
        if run["auftrag"].get("criticality") == "K3":
            lines.append("Kritikalität K3: Du lieferst nur Entwürfe und Prüfhinweise; jedes Ergebnis prüft eine "
                         "qualifizierte Person nach Norm. Kennzeichne es als „KI-Entwurf, menschliche Prüfung nach "
                         "Norm erforderlich“.")
        if agent.role == "entwicklung":
            lines.append("Freigegebene Pfade: " + (", ".join(context.get("allowed_paths") or []) or "keine"))
        if agent.role == "akzeptanztest" and _has_ui(run["auftrag"].get("paths") or []):
            lines.append(UI_HINT)
        if agent.role == "entwicklung" and (context.get("artifacts") or {}).get("integrationstests"):
            lines.append("Für jeden Integrationstestfall (integrationstests) legst du einen automatisierten Test an, "
                         "dessen Name die Fall-ID enthält (z. B. test_IT_1_rechte für IT-1). Nur so zählt das "
                         "Ergebnis an G3; ein grüner Gesamtlauf allein genügt nicht.")
        if agent.role in {"entwicklung", "planung", "architektur"}:
            lines.append("Braucht die Änderung Dateien außerhalb der freigegebenen Pfade, setze status "
                         "entscheidung_offen und nenne in questions genau diese Dateien – liefere keine Teillösung.")
        if context.get("findings_to_fix"):
            lines.append("Es liegen Befunde vor, die du in dieser Runde beheben musst (siehe findings_to_fix).")
        lines.append(_schema_hint(agent.role, step.kind))
        lines += ["<<<ARBEITSDATEN", data, "ARBEITSDATEN>>>",
                  "Liefere jetzt deine Übergabe als ein JSON-Objekt gemäß Ergebnisvertrag."]
        return "\n".join(lines)

    def _tool(self, agent: Agent | None, run: dict[str, Any], operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        if agent is None:
            role, agent_id = ORCHESTRATOR
        else:
            if operation not in agent.tools:
                raise RMError(f"{agent.name} besitzt das Werkzeug {operation} nicht")
            role, agent_id = agent.role, agent.id
        result = self.rm.call(role, agent_id, run["id"], operation, payload)
        self.store.event(run["id"], "werkzeug", role, "flowwork", f"{operation} ausgeführt",
                         {"operation": operation, "object": str(result.get("id", ""))[:60]})
        return result

    def _apply_tools(self, run: dict[str, Any], step: Step, agent: Agent, handoff: Handoff) -> dict[str, Any]:
        project = run["auftrag"]["project"]
        refs: dict[str, Any] = {}
        if agent.role == "anforderungen" and handoff.artifacts:
            previous = self.store.latest_artifact(run["id"], "anforderungen")
            mapping = dict((previous or {}).get("refs", {}).get("rm", {}))
            for item in handoff.artifacts:
                values = {k: item.get(k) for k in ("title", "text", "priority", "rationale", "negative_case")}
                values["acceptance_criteria"] = item["acceptance_criteria"]
                values["source"] = run["auftrag_id"]
                known = mapping.get(item["key"])
                if known:
                    payload = {"id": known["id"], "expected_version": known["version"], "values": values}
                    try:
                        result = self._tool(agent, run, "rm.update_draft", payload)
                    except RMConflict as conflict:
                        # Wiederanlauf: Ein unterbrochener Versuch dieses Laufs hat bereits geschrieben.
                        # Der Adapter erlaubt Änderungen nur am Entwurf desselben Laufs; also mit dem
                        # bestätigten Stand genau einmal erneut schreiben.
                        payload["expected_version"] = int(conflict.current.get("version", 0))
                        result = self._tool(agent, run, "rm.update_draft", payload)
                else:
                    result = self._tool(agent, run, "rm.create_draft", {
                        "idempotency_key": f"{run['id']}:{item['key']}", "project": project,
                        "auftrag_id": run["auftrag_id"], "key": item["key"], "values": values})
                mapping[item["key"]] = {"id": result["id"], "version": int(result.get("version", 1))}
            refs["rm"] = mapping
            for question in handoff.questions:
                self._tool(agent, run, "rm.ask_owner", {"auftrag_id": run["auftrag_id"], **question})
        elif agent.role == "anforderungspruefung":
            mapping = (self.store.latest_artifact(run["id"], "anforderungen") or {}).get("refs", {}).get("rm", {})
            for finding in handoff.findings:
                target = mapping.get(finding["location"])
                if target:
                    self._tool(agent, run, "rm.comment", {"id": target["id"], "version": target["version"],
                                                          "text": f"[{finding['severity']}] {finding['impact']}"})
        elif agent.role == "akzeptanztest" and handoff.artifacts:
            baseline = self.store.latest_artifact(run["id"], "baseline")
            mapping = (baseline or {}).get("content", {}).get("rm", {})
            tests = {}
            for item in handoff.artifacts:
                result = self._tool(agent, run, "rm.create_test", {
                    "idempotency_key": f"{run['id']}:{item['key']}:{baseline['version'] if baseline else 0}",
                    "project": project, "key": item["key"], "title": item["title"],
                    "criterion": item["criterion"], "preconditions": item.get("preconditions", ""),
                    "steps": item["steps"], "negative": bool(item.get("negative"))})
                tests[item["key"]] = result.get("id")
                requirement = mapping.get(item["criterion"].split("/")[0])
                if requirement and result.get("id"):
                    self._tool(agent, run, "rm.link_trace", {"requirement_id": requirement["id"], "item_id": result["id"],
                                                             "relationship": "verifies"})
            refs["tests"] = tests
        elif agent.role == "planung" and handoff.artifacts:
            tasks = {}
            for item in handoff.artifacts:
                result = self._tool(agent, run, "ticket.create", {
                    "idempotency_key": f"{run['id']}:{item['key']}", "project": project,
                    "subject": f"[{run['auftrag_id']}] {item['title']}", "covers": item.get("covers", [])})
                tasks[item["key"]] = result.get("id")
            refs["tasks"] = tasks
        elif agent.role == "entwicklung" and handoff.status == "fertig":
            if self.sandbox is None:
                raise SandboxError("keine Sandbox konfiguriert")
            paths = list(run["auftrag"].get("paths") or [])
            changes = {item["key"]: item["content"] for item in handoff.artifacts}
            base = self.sandbox.base_commit()
            originals = self.sandbox.originals(base, paths)
            diff = _diff(originals, changes)
            if not diff.strip():
                # Zweite Sperre hinter dem Vertrag: ein leerer Stand darf nie in Prüfung und Abnahme gehen.
                raise SandboxError("Implementierung ändert nichts gegenüber dem Ausgangsstand")
            refs = self.sandbox.apply(run["id"], base, paths, changes)
            refs["diff"] = diff[:100_000]
        return refs

    def _artifact_content(
        self, run: dict[str, Any], step: Step, handoff: Handoff, refs: dict[str, Any]
    ) -> dict[str, Any]:
        content: dict[str, Any] = {"status": handoff.status, "summary": handoff.summary}
        if step.kind == "review":
            subject = self.store.latest_artifact(run["id"], step.subject or "")
            content["subject"] = {"kind": step.subject, "version": subject["version"] if subject else 0,
                                  "digest": (subject["refs"].get("digest") if subject and step.subject == "implementierung"
                                             else subject["digest"] if subject else "")}
            content["findings"] = handoff.findings
        if handoff.artifacts and step.produces != "implementierung":
            content["items"] = handoff.artifacts
        if step.produces == "implementierung":
            content.update({"files": refs.get("files", {}), "digest": refs.get("digest"), "base": refs.get("base"),
                            "diff": refs.get("diff", "")})
        if handoff.questions:
            content["questions"] = handoff.questions
        return content

    # -- Prüfschritt -----------------------------------------------------------------------
    def _check_step(self, run: dict[str, Any], step: Step) -> None:
        implementation = self.store.latest_artifact(run["id"], "implementierung")
        if implementation is None:
            with self.lock:
                self._block(run, "Keine Implementierung zum Prüfen", "blockade", step_id=step.id)
            return
        row = self.store.start_step(run["id"], step.id, None, "sandbox")
        self.store.event(run["id"], "start", "integration", "integration",
                         f"Integrationsprüfung am Digest {implementation['refs'].get('digest', '')[:19]}")
        if self.sandbox is None:
            passed, summary, seconds, command = False, "Sandbox nicht konfiguriert", 0.0, ""
        else:
            try:
                result = self.sandbox.check(str(implementation["refs"].get("workspace", "")))
                passed, summary, seconds, command = result.passed, result.summary, result.seconds, result.command
                output = result.output or result.summary
            except SandboxError as exc:
                passed, summary, seconds, command, output = False, str(exc), 0.0, "", ""
        cases: dict[str, str] = {}
        if self._requires_kind(run, "integrationstests"):
            specified = (self.store.latest_artifact(run["id"], "integrationstests") or {}).get("content", {}).get("items", [])
            cases = _case_results(output, [str(c.get("key", "")) for c in specified if c.get("key")])
            open_cases = sorted(k for k, v in cases.items() if v != "bestanden")
            if passed and open_cases:
                passed = False
                summary = (f"Integrationstests ohne bestandenes Ergebnis am Kandidaten: {', '.join(open_cases)}. "
                           "Je Fall einen automatisierten Test mit der Fall-ID im Namen anlegen (z. B. test_IT_1_…).")
        with self.lock:
            content = {"passed": passed, "digest": implementation["refs"].get("digest"),
                       "implementation_version": implementation["version"], "summary": summary,
                       "seconds": round(seconds, 1), "command": command, "cases": cases}
            self.store.add_artifact(run["id"], "integration", "integration", step.id, content)
            self.store.finish_step(row, "fertig" if passed else "nacharbeit", summary=summary[-500:])
            if passed:
                self._advance(run, step, "Integrationsprüfung bestanden")
                return
            if self.sandbox is None:
                self._block(run, "Integrationsprüfung nicht möglich: Sandbox fehlt", "blockade", step_id=step.id)
                return
            counts = dict(run["corrections"].get("counts", {}))
            counts[step.id] = counts.get(step.id, 0) + 1
            finding = [{"severity": "hoch", "location": "integration", "impact": summary[-1500:],
                        "recommendation": "Fehlschlagende Prüfung beheben"}]
            back_to = step.on_failure.get("back_to", "entwicklung")
            if counts[step.id] > self.registry.max_correction_rounds:
                self._set_corrections(run, counts=counts)
                self._update_run(run["id"], status="wartet", reason="Korrekturlimit erreicht")
                self._open_decision(run["id"], step.id, "korrekturlimit", "tech-lead",
                                         "Integrationsprüfung wiederholt rot",
                                         "Weitere Runde zulassen oder Lauf abbrechen?",
                                         {"findings": finding, "back_to": back_to}, actor="integration")
                return
            self._set_corrections(run, counts=counts, pending={back_to: finding})
            self._update_run(run["id"], step_index=self.registry.step_index(back_to))
            self.store.event(run["id"], "ruecklauf", "integration", "entwicklung", "Integrationsprüfung rot")

    # -- Gates -----------------------------------------------------------------------------
    def _gate_step(self, run: dict[str, Any], step: Step) -> None:
        missing = [kind for kind in step.requires if self.store.latest_artifact(run["id"], kind) is None]
        if missing:
            self._block(run, f"{step.id}: Voraussetzungen fehlen ({', '.join(missing)})", "blockade", step_id=step.id)
            return
        problems = self._gate_checks(run, step)
        if problems:
            self._block(run, f"{step.id}: " + "; ".join(problems), "blockade", step_id=step.id)
            return
        digest = ""
        if step.freeze_baseline:
            baseline = self._freeze_baseline(run)
            digest = baseline["digest"]
        elif step.bind_digest:
            bound = self.store.latest_artifact(run["id"], step.bind_digest)
            digest = str((bound or {}).get("refs", {}).get("digest") or "")
        human = self.registry.human_gate(step.id, run["change_class"])
        if step.id == "G2":
            architecture = self.store.latest_artifact(run["id"], "architektur")
            if any(item.get("new_trust_boundary") for item in (architecture or {}).get("content", {}).get("items", [])):
                human = True
        if human:
            context = self._gate_context(run, step)
            if step.id == "G4" and self.preview is not None:
                implementation = self.store.latest_artifact(run["id"], "implementierung") or {}
                try:
                    base = self.preview.start(Path(str(implementation["refs"]["workspace"])))
                    dms = any("dms" in path for path in run["auftrag"].get("paths", []))
                    context["preview_url"] = base + ("/dms" if dms else "/")
                    self.store.event(run["id"], "vorschau", "integration", "mensch:key-user",
                                     f"Kandidat zur Abnahme unter {context['preview_url']} gestartet")
                except (SandboxError, KeyError, OSError) as exc:
                    context["preview_error"] = str(exc)[:300]
            scenarios = []
            if step.id == "G4" and context.get("preview_url") and self.ui_runner is not None:
                scenarios = scenarios_from(self.store.latest_artifact(run["id"], "akzeptanztests"))
                if scenarios:
                    context["ui_check"] = {"status": "laeuft", "total": len(scenarios)}
            self._update_run(run["id"], status="wartet", reason=f"{step.id} wartet auf {step.decider}")
            decision = self._open_decision(run["id"], step.id, step.id, step.decider or "tech-lead",
                                                f"{step.id} · {step.label}", self._gate_question(run, step),
                                                context, digest, actor=step.id)
            if scenarios:
                threading.Thread(target=self._ui_check, args=(run["id"], decision["id"], scenarios, digest),
                                 daemon=True, name=f"ui-check-{run['id']}").start()
            return
        self.store.event(run["id"], "gate", step.id, step.id, f"{step.id} im genehmigten Standardweg erfüllt",
                         {"digest": digest})
        self._advance(run, step, f"{step.id} erfüllt")

    def _gate_checks(self, run: dict[str, Any], step: Step) -> list[str]:
        problems = []

        def latest(kind: str) -> dict[str, Any]:
            return self.store.latest_artifact(run["id"], kind) or {}

        def reviewed(review_kind: str, subject_kind: str, by_digest: bool = False) -> bool:
            review, subject = latest(review_kind), latest(subject_kind)
            bound = review.get("content", {}).get("subject", {})
            if by_digest:
                return bound.get("digest") == subject.get("refs", {}).get("digest") and \
                    review.get("content", {}).get("status") == "fertig"
            return bound.get("version") == subject.get("version") and review.get("content", {}).get("status") == "fertig"

        if step.id == "EP1":
            packages = latest("projektplan").get("content", {}).get("items", [])
            keys = {item.get("key") for item in packages}
            if not packages:
                problems.append("Projektplan enthält keine Arbeitspakete")
            unknown = sorted({dep for item in packages for dep in item.get("depends_on", []) if dep not in keys})
            if unknown:
                problems.append(f"Abhängigkeiten auf unbekannte Arbeitspakete: {', '.join(unknown)}")
            cyclic = _cycles(packages)
            if cyclic:
                problems.append(f"Zyklische Abhängigkeiten zwischen Arbeitspaketen: {', '.join(cyclic)}")
            allowed_scopes = self._project_scope_set(run["auftrag"])
            bad_scopes = sorted({item["scope"] for item in packages if item.get("scope") and item["scope"] not in allowed_scopes})
            if bad_scopes:
                problems.append(f"Arbeitspakete nennen Änderungsbereiche außerhalb des Projekts: {', '.join(bad_scopes)}")
            if run["auftrag"].get("project_class") == "L" and not any(
                    item.get("v_level") in INTEGRATION_LEVELS for item in packages):
                problems.append("Projektplan enthält kein Integrationspaket (software_integration oder "
                                "systemintegration) für den projektweiten Integrationsnachweis")
        if step.id == "G1" and not reviewed("anforderungsbefund", "anforderungen"):
            problems.append("Prüfung gilt nicht für den aktuellen Anforderungsstand")
        if step.id == "G2" and not reviewed("sicherheitsbefund", "architektur"):
            problems.append("Sicherheitsprüfung gilt nicht für den aktuellen Architekturstand")
        if step.id == "G3":
            integration, implementation = latest("integration"), latest("implementierung")
            if not integration.get("content", {}).get("passed"):
                problems.append("Integrationsprüfung nicht bestanden")
            if integration.get("content", {}).get("digest") != implementation.get("refs", {}).get("digest"):
                problems.append("Integrationsprüfung gehört zu einem anderen Änderungsstand")
            if not reviewed("codebefund", "implementierung", by_digest=True):
                problems.append("Codeprüfung gehört zu einem anderen Änderungsstand")
            if self._requires_kind(run, "integrationstests"):
                problems += self._integration_gaps(run)
        if step.id in {"G4", "G5"}:
            problems += self.verify_manifest(run["id"])
        return problems

    def _integration_gaps(self, run: dict[str, Any]) -> list[str]:
        """Jeder spezifizierte Integrationstestfall braucht ein gültiges Baseline-Kriterium und ein bestandenes
        Ergebnis im Prüfjob genau dieses Kandidaten (Fall-ID ↔ Kriterium ↔ Digest ↔ Testergebnis)."""
        cases = (self.store.latest_artifact(run["id"], "integrationstests") or {}).get("content", {}).get("items", [])
        if not cases:
            return ["Integrationstests aus der Architektur fehlen"]
        baseline = (self.store.latest_artifact(run["id"], "baseline") or {}).get("content", {})
        criteria = _criteria(baseline)
        integration = (self.store.latest_artifact(run["id"], "integration") or {}).get("content", {})
        candidate = (self.store.latest_artifact(run["id"], "implementierung") or {}).get("refs", {}).get("digest")
        results = integration.get("cases", {}) if integration.get("digest") == candidate else {}
        gaps = []
        for case in cases:
            key = str(case.get("key", ""))
            covers = [str(c) for c in case.get("covers", []) or []]
            if not any(c in criteria for c in covers):
                gaps.append(f"Integrationstest {key} sichert kein gültiges Baseline-Kriterium ab")
            if results.get(key) != "bestanden":
                state = results.get(key, "fehlt")
                gaps.append(f"Integrationstest {key} hat am Kandidaten kein bestandenes Ergebnis ({state})")
        return gaps

    def _requires_kind(self, run: dict[str, Any], kind: str) -> bool:
        """Entsteht diese Artefaktart im Zuschnitt des Laufs (Projektklasse)?"""
        producer = self.registry.producer(kind)
        return producer is not None and producer.applies(run["auftrag"])

    def verify_manifest(self, run_id: str) -> list[str]:
        """Der Orchestrator prüft das Nachweispaket selbst (Teil 07, Test 30).

        Nach dem V-Modell hat jede Anforderung der Baseline eine Prüfung auf derselben Ebene
        (Akzeptanztest je Anforderung; bei M/L zusätzlich Integrationstests).
        """
        gaps = []
        run = self.store.run(run_id)
        baseline = (self.store.latest_artifact(run_id, "baseline") or {}).get("content", {})
        tests = (self.store.latest_artifact(run_id, "akzeptanztests") or {}).get("content", {}).get("items", [])
        criteria = _criteria(baseline)
        covered = {criteria[str(item.get("criterion", ""))] for item in tests if str(item.get("criterion", "")) in criteria}
        unknown = sorted({str(item.get("criterion", "")) for item in tests if str(item.get("criterion", "")) not in criteria})
        if unknown:
            gaps.append(f"Akzeptanztests nennen unbekannte Kriterien: {', '.join(unknown)}")
        for requirement in baseline.get("items", []):
            if requirement.get("key") not in covered:
                gaps.append(f"Anforderung {requirement.get('key')} hat keinen Akzeptanztest")
        if self._requires_kind(run, "integrationstests"):
            gaps += self._integration_gaps(run)
        manifest = (self.store.latest_artifact(run_id, "nachweise") or {}).get("content", {})
        claimed = {item.get("title"): item for item in manifest.get("items", [])}
        for kind in ("anforderungen", "baseline", "implementierung", "integration", "codebefund", "akzeptanztests"):
            actual = self.store.latest_artifact(run_id, kind)
            if actual is None:
                gaps.append(f"Primärbeleg {kind} fehlt")
                continue
            entry = claimed.get(kind)
            if entry and entry.get("state") == "belegt" and entry.get("digest") and entry["digest"] != actual["digest"]:
                gaps.append(f"Nachweis {kind} nennt einen falschen Digest")
        integration = (self.store.latest_artifact(run_id, "integration") or {}).get("content", {})
        if not integration.get("passed"):
            gaps.append("Kein bestandener Prüfbericht")
        candidate = (self.store.latest_artifact(run_id, "implementierung") or {}).get("refs", {}).get("digest")
        review = (self.store.latest_artifact(run_id, "codebefund") or {}).get("content", {}).get("subject", {})
        if candidate and integration.get("digest") != candidate:
            gaps.append("Prüfbericht gehört zu einem anderen Änderungsstand")
        if candidate and review.get("digest") != candidate:
            gaps.append("Codeprüfung gehört zu einem anderen Änderungsstand")
        return gaps

    def _freeze_baseline(self, run: dict[str, Any]) -> dict[str, Any]:
        requirements = self.store.latest_artifact(run["id"], "anforderungen") or {}
        mapping = requirements.get("refs", {}).get("rm", {})
        items = requirements.get("content", {}).get("items", [])
        rm_result = self._tool(None, run, "rm.freeze_baseline", {
            "idempotency_key": f"{run['id']}:BL:{requirements.get('version', 0)}",
            "project": run["auftrag"]["project"], "auftrag_id": run["auftrag_id"],
            "name": f"Arbeitsbaseline {run['auftrag_id']} v{requirements.get('version', 0)}",
            "items": [{"id": ref["id"], "version": ref["version"]} for ref in mapping.values()],
        })
        content = {"rm_id": rm_result.get("id"), "items": items, "rm": mapping,
                   "requirements_version": requirements.get("version"), "requirements_digest": requirements.get("digest"),
                   "state": "Arbeitsbaseline fixiert"}
        stored = self.store.add_artifact(run["id"], "baseline", "orchestrator", "G1", content, {})
        self.store.event(run["id"], "baseline", "G1", "flowwork",
                         f"Arbeitsbaseline fixiert ({rm_result.get('id', 'lokal')}, v{stored['version']})",
                         {"digest": stored["digest"]})
        return stored

    def _gate_question(self, run: dict[str, Any], step: Step) -> str:
        texts = {
            "EP1": "Projekt definiert? Einstufung, Arbeitspakete, Wellen und Abnahmekriterien bestätigen.",
            "G1": "Anforderungen fachlich freigeben? Die Arbeitsbaseline ist fixiert und unabhängig geprüft.",
            "G2": "Architektur und Sicherheitsbewertung bestätigen?",
            "G3": "Integrationsstand (Code, Prüfungen, Codeprüfung am selben Digest) bestätigen?",
            "G4": "Fachabnahme: Erfüllt der Kandidat den Auftrag? Die Abnahme gilt nur für den genannten Digest.",
            "G5": "Produktionsfreigabe protokollieren? Die Auslieferung erfolgt außerhalb des Agentennetzes.",
        }
        return texts.get(step.id, step.label)

    def _ui_check(self, run_id: str, decision_id: str, scenarios: list[dict[str, Any]], digest: str) -> None:
        """Klickpfade der Akzeptanztests gegen die Vorschau (läuft neben der offenen Fachabnahme)."""
        assert self.ui_runner is not None and self.preview is not None
        self.store.event(run_id, "start", "orchestrator", "akzeptanztest",
                         f"Klickprüfung: {len(scenarios)} Testfälle im Prüfbrowser gegen die Vorschau")
        try:
            self.ui_runner.prepare_network(self.preview.NAME)
            report = self.ui_runner.run(scenarios)
        except (UiCheckError, OSError, subprocess.SubprocessError) as exc:
            self.store.update_decision_context(decision_id, {"ui_check": {"status": "fehler", "error": str(exc)[:300]}})
            self.store.event(run_id, "fehler", "orchestrator", "akzeptanztest", f"Klickprüfung nicht möglich: {exc}"[:300])
            return
        stored = self.store.add_artifact(run_id, "ui_pruefung", "orchestrator", "G4", report, {"digest": digest})
        summary = {"status": "fertig", "passed": report["passed"], "total": report["total"],
                   "artifact_version": stored["version"],
                   "failed": [s["key"] for s in report["scenarios"] if not s["passed"]]}
        self.store.update_decision_context(decision_id, {"ui_check": summary})
        self.store.event(run_id, "ergebnis", "orchestrator", "mensch:key-user",
                         f"Klickprüfung: {report['passed']} von {report['total']} Testfällen bestanden",
                         {"failed": summary["failed"]})

    def _gate_context(self, run: dict[str, Any], step: Step) -> dict[str, Any]:
        summaries = {}
        for kind in (*step.requires, "baseline", "geschaeftsbewertung", "prozessbewertung", "projektplan",
                     "integrationstests"):
            item = self.store.latest_artifact(run["id"], kind)
            if item:
                summaries[kind] = {"version": item["version"], "digest": item["digest"],
                                   "summary": item["content"].get("summary", "")}
        auftrag = run["auftrag"]
        return {"artifacts": summaries, "change_class": run["change_class"], "ep": step.ep,
                "project_class": auftrag.get("project_class", "S"), "criticality": auftrag.get("criticality", "K1"),
                "domain": auftrag.get("domain", "it")}

    # =================================================================================
    # Menschliche Entscheidungen
    # =================================================================================
    def decide(self, decision_id: str, user: dict[str, Any], outcome: str, comment: str = "") -> dict[str, Any]:
        if outcome not in {"annehmen", "ablehnen"}:
            raise EngineError("Ergebnis muss annehmen oder ablehnen sein")
        comment = comment.strip()
        if outcome == "ablehnen" and len(comment) < 3:
            raise EngineError("Eine Ablehnung braucht eine Begründung")
        with self.lock:
            try:
                decision = self.store.decision(decision_id)
            except KeyError:
                raise EngineError("Entscheidung nicht gefunden") from None
            if decision["status"] != "offen":
                raise EngineError("Entscheidung ist nicht mehr offen")
            self._authorize(user, decision["decider"])
            run = self.store.run(decision["run_id"])
            self._require_run(user, run, "lesen")
            if run["status"] not in {"wartet", "blockiert"}:
                raise EngineError("Lauf wartet nicht auf diese Entscheidung")
            gate = decision["gate"]
            current_id = self._current_step_id(run)
            stale_rules = gate != "blockade" and (
                run["registry_digest"] != self.registry.digest
                or (decision.get("registry_digest") or self.registry.digest) != self.registry.digest)
            moved = gate in GATE_IDS and current_id and current_id != decision["step_id"]
            if stale_rules or moved:
                # Eine unter altem Regelstand oder an einem anderen Schritt geöffnete Entscheidung darf weder
                # übernehmen noch abschließen: sie verfällt, ein Mensch bewertet den Lauf neu.
                why = "Regelstand geändert" if stale_rules else "Lauf steht nicht mehr an diesem Schritt"
                self.store.close_decision(decision_id, "verfallen", "", _person(user), why)
                if gate == "G4" and self.preview is not None:
                    self.preview.stop()
                self._block(run, f"{decision['title']}: Entscheidung verfallen ({why}); Lauf neu bewerten",
                            "blockade", step_id=current_id or decision["step_id"])
                raise EngineError(f"Die Entscheidung ist verfallen ({why}); der Lauf wartet auf eine Neubewertung")
            rebind_index = None
            if gate == "blockade" and outcome == "annehmen" and run["registry_digest"] != self.registry.digest:
                rebind_index = self._rebind_index(run)
            step = self._step_by_id(decision["step_id"]) or self._step_by_id(current_id)
            if step is None:
                raise EngineError("Schritt der Entscheidung ist im aktuellen Ablauf nicht vorhanden")
            if decision["digest"] and gate in {"G3", "G4", "G5"}:
                bound = self.store.latest_artifact(run["id"], step.bind_digest or "implementierung") or {}
                if bound.get("refs", {}).get("digest") != decision["digest"]:
                    self.store.close_decision(decision_id, "verfallen", "", _person(user), "Digest geändert")
                    self._update_run(run["id"], status="aktiv", reason="")
                    raise EngineError("Der Kandidat hat sich geändert; eine neue Entscheidung ist erforderlich")
            person = _person(user)
            self.store.close_decision(decision_id, "angenommen" if outcome == "annehmen" else "abgelehnt",
                                      outcome, person, comment)
            self.store.event(run["id"], "entscheidung", f"mensch:{decision['decider']}", step.role or step.id,
                             f"{person['name']} ({decision['decider']}): {decision['title']} – {outcome}",
                             {"decision": decision_id, "gate": gate})
            if gate == "G4":
                if self.preview is not None:
                    self.preview.stop()
                if outcome == "annehmen":
                    self._adopt(run, person, decision["digest"])
            if rebind_index is not None:
                self._update_run(run["id"], registry_digest=self.registry.digest, step_index=rebind_index)
                self.store.event(run["id"], "steuerung", f"mensch:{decision['decider']}", "orchestrator",
                                 f"Lauf auf Registerstand {self.registry.digest[:12]} umgestellt durch {person['name']} "
                                 f"(Schritt {self.registry.steps[rebind_index].id if rebind_index < len(self.registry.steps) else 'fertig'})")
                run = self.store.run(run["id"])
            self._apply_decision(run, step, decision, outcome, comment, person)
            return self.store.decision(decision_id)

    def _rebind_index(self, run: dict[str, Any]) -> int:
        """Neuer Index eines Laufs nach einer Registeränderung – nur über die stabile Schritt-ID."""
        step_id = self._current_step_id(run)
        if step_id == "fertig":
            return len(self.registry.steps)
        if not step_id or self._step_by_id(step_id) is None:
            raise EngineError(f"Schritt „{step_id or 'unbekannt'}“ gibt es im aktuellen Ablauf nicht; "
                              "den Lauf bitte abbrechen und neu einreichen")
        return self.registry.step_index(step_id)

    def _on_project_defined(self, run: dict[str, Any], person: dict[str, Any], decision: dict[str, Any]) -> None:
        """EP1 für Projektklasse L: Projekt anlegen und Planungslauf abschließen – atomar und wiederanlauffähig."""
        plan = (self.store.latest_artifact(run["id"], "projektplan") or {}).get("content", {})
        packages = [{key: item.get(key) for key in ("key", "title", "result", "v_level", "acceptance", "wave", "effort",
                                                     "depends_on", "scope", "owner_role", "criticality")
                     if item.get(key) not in (None, "", [])} for item in plan.get("items", [])]
        project = self.store.complete_with_project(
            run, packages, person, reason="Projekt definiert; Arbeitspakete laufen als eigene Aufträge",
            completion="projektplanung", step_index=len(self.registry.steps))
        self.store.event(run["id"], "projekt", f"mensch:{decision['decider']}", "projektplanung",
                         f"EP1 Projekt definiert durch {person['name']}: {project['id']} mit {len(packages)} "
                         "Arbeitspaketen angelegt", {"project_id": project["id"]})

    # =================================================================================
    # Projekte und Arbeitspakete (Stufe 2)
    # =================================================================================
    def start_package(self, project_id: str, key: str, user: dict[str, Any], scope: str = "") -> dict[str, Any]:
        """EPi „Iteration geplant“: ein Arbeitspaket als eigenen Auftrag durch das V schicken.

        Entscheiden darf der Product Owner (Auftraggeber) oder der Tech Lead. Vorgänger müssen
        fertig sein. Das Paket läuft im Kurzweg (Projektklasse S); seine Kritikalität bestimmt,
        welche Gates Menschen entscheiden.
        """
        try:
            self._authorize(user, "product-owner")
        except EngineError:
            self._authorize(user, "tech-lead")
        with self.lock:
            try:
                project = self.store.project(project_id)
            except KeyError:
                raise EngineError("Projekt nicht gefunden") from None
            base = project["auftrag"]
            # Projektrecht vor jeder Auskunft (bestehender Lauf, Vorgänger) und vor jeder Zustandsänderung.
            self._require_auftrag(user, base, "aendern")
            states = self._package_states(project)
            package = next((item for item in project["packages"] if item["key"] == key), None)
            if package is None:
                raise EngineError("Arbeitspaket nicht gefunden")
            if package["run_id"]:
                return self.store.run(package["run_id"])
            open_deps = [dep for dep in package.get("depends_on", []) if states.get(dep) != "fertig"]
            if open_deps:
                raise EngineError(f"Vorgänger noch nicht fertig: {', '.join(open_deps)}")
            planned = str(package.get("scope") or "")
            if scope and planned and scope != planned:
                raise EngineError(f"Arbeitspaket {key} hat den genehmigten Bereich {planned}; er lässt sich beim Start "
                                  "nicht ersetzen")
            scope_id = planned or scope
            if not scope_id:
                raise EngineError("Arbeitspaket nennt keinen Änderungsbereich; bitte einen freigegebenen Bereich wählen")
            if scope_id not in self._project_scope_set(base):
                raise EngineError(f"Änderungsbereich {scope_id} gehört nicht zum Projekt {base.get('project', '')}")
            values = {
                "title": f"{key} {package['title']}"[:160],
                "goal": f"{base.get('goal', '')} – Arbeitspaket {key}: {package['result']}"[:2000],
                "user_group": base.get("user_group", "Fachbereich"),
                "behavior": f"{package['result']}. Abnahmekriterium: {package['acceptance']}"[:3000],
                "exclusions": base.get("exclusions", ""),
                "success_example": str(package["acceptance"])[:1500],
                "data_class": base.get("data_class", "intern"),
                "scope": scope_id,
                "project": base.get("project", "FLOW-PLATFORM"),
                "execution": base.get("execution", "automatisch"),
                "project_class": "S",
                # Kritikalität des Projekts ist die Untergrenze; ein Paket kann sie nur verschärfen.
                "criticality": _strictest(CRITICALITIES, package.get("criticality"), base.get("criticality"), "K1"),
                "domain": base.get("domain", "it"),
            }
            inherited = base.get("change_class_explicit") or ("kritisch" if base.get("change_class") == "kritisch" else "")
            if inherited:
                values["change_class"] = inherited  # ausdrückliche Verschärfung des Projekts gilt auch je Paket
            auftrag = self._validated_auftrag(values, user)
            auftrag.update({"project_id": project_id, "package_key": key, "v_level": package.get("v_level", ""),
                            "parent_run": project["run_id"],
                            "catalog_bound": bool(base.get("catalog_bound") or base.get("catalog"))})
            if package.get("v_level") in INTEGRATION_LEVELS:
                auftrag["integration_required"] = True  # projektweiter Integrationsnachweis (Schritt integrationstests)
            try:
                run = self.store.create_package_run(
                    project_id, key, _person(user), title=auftrag["title"], change_class=auftrag["change_class"],
                    auftrag=auftrag, requested_by=_person(user), registry_digest=self.registry.digest,
                    idempotency_key=f"{project_id}:{key}", announce=True,
                    step_id=self.registry.steps[0].id)
            except ValueError as exc:
                raise EngineError(str(exc)) from None
            wave = package.get("wave", 1)
            self.store.event(project["run_id"], "projekt", f"mensch:{_person(user)['username']}", "projektplanung",
                             f"EPi Iteration geplant (Welle {wave}): {key} als {run['auftrag_id']} gestartet",
                             {"project_id": project_id, "package": key, "run_id": run["id"]})
            return run

    def _package_states(self, project: dict[str, Any]) -> dict[str, str]:
        """Status je Arbeitspaket aus dem Status seines Laufs: geplant, bereit, in_arbeit, fertig, gestoppt."""
        runs = {}
        for item in project["packages"]:
            if item["run_id"]:
                try:
                    runs[item["key"]] = self.store.run(item["run_id"])["status"]
                except KeyError:
                    runs[item["key"]] = "abgebrochen"
        states: dict[str, str] = {}
        for item in project["packages"]:
            status = runs.get(item["key"])
            if status == "abgeschlossen":
                states[item["key"]] = "fertig"
            elif status in {"abgebrochen", "abgelehnt"}:
                states[item["key"]] = "gestoppt"
            elif status:
                states[item["key"]] = "in_arbeit"
        for item in project["packages"]:
            if item["key"] not in states:
                ready = all(states.get(dep) == "fertig" for dep in item.get("depends_on", []))
                states[item["key"]] = "bereit" if ready else "geplant"
        return states

    def project_summary(self, project: dict[str, Any]) -> dict[str, Any]:
        states = self._package_states(project)
        packages = []
        for item in project["packages"]:
            run = self.store.run(item["run_id"]) if item["run_id"] else None
            packages.append({**{k: v for k, v in item.items() if k != "started_by"}, "status": states[item["key"]],
                             "auftrag_id": run["auftrag_id"] if run else "",
                             "run_status": run["status"] if run else "",
                             "started_by": item["started_by"].get("name", "") if item["started_by"] else ""})
        values = list(states.values())
        integration_done = any(states[item["key"]] == "fertig" and item.get("v_level") in INTEGRATION_LEVELS
                               for item in project["packages"])
        if values and all(state == "fertig" for state in values):
            # Ohne fertiges Integrationspaket fehlt der projektweite Integrationsnachweis.
            status = "abgeschlossen" if integration_done else "nachweis_offen"
        elif any(state == "in_arbeit" for state in values):
            status = "in_arbeit"
        else:
            status = "definiert"
        waves = sorted({int(item.get("wave") or 1) for item in project["packages"]}) or [1]
        current_wave = next((w for w in waves if any(states[i["key"]] != "fertig" for i in project["packages"]
                                                       if int(i.get("wave") or 1) == w)), waves[-1])
        auftrag = project["auftrag"]
        return {
            "id": project["id"], "run_id": project["run_id"], "title": project["title"], "status": status,
            "code": auftrag.get("project", ""), "catalog": bool(auftrag.get("catalog")),
            "ep": "EP9 Projekt abgeschlossen" if status == "abgeschlossen" else "EP1 Projekt definiert",
            "project_class": auftrag.get("project_class", "L"), "criticality": auftrag.get("criticality", "K1"),
            "domain": auftrag.get("domain", "it"), "project": auftrag.get("project", ""),
            "defined_by": project["defined_by"].get("name", ""), "created_at": project["created_at"],
            "progress": round(sum(1 for s in values if s == "fertig") / len(values) * 100) if values else 0,
            "current_wave": current_wave, "packages": packages,
        }

    def _adopt(self, run: dict[str, Any], person: dict[str, Any], digest: str) -> None:
        if self.adoption is None:
            return
        implementation = self.store.latest_artifact(run["id"], "implementierung") or {}
        try:
            result = self.adoption.adopt(run, implementation.get("refs", {}), approved_by=person["name"], digest=digest)
        except (SandboxError, OSError) as exc:
            self.store.event(run["id"], "fehler", "orchestrator", "repository", f"Übernahme fehlgeschlagen: {exc}")
            return
        self.store.add_artifact(run["id"], "uebernahme", "orchestrator", "G4", result, {})
        self.store.event(run["id"], "uebernahme", "orchestrator", "repository",
                         f"Abgenommener Stand als Branch {result['branch']} übernommen ({result['commit'][:10]})",
                         {"branch": result["branch"], "commit": result["commit"], "pushed": result["pushed"]})

    def _apply_decision(
        self, run: dict[str, Any], step: Step, decision: dict[str, Any], outcome: str, comment: str,
        person: dict[str, Any],
    ) -> None:
        gate = decision["gate"]
        accepted = outcome == "annehmen"
        if gate in GATE_IDS:
            if accepted:
                if gate == "EP1" and run["auftrag"].get("project_class") in step.completes_for:
                    self._on_project_defined(run, person, decision)  # Projekt und Abschluss in einer Transaktion
                    return
                if gate == "G5":
                    self._update_run(run["id"], status="abgeschlossen", step_index=len(self.registry.steps),
                                     completion="produktion",
                                     reason="Produktionsfreigabe protokolliert; Auslieferung manuell")
                    self.store.event(run["id"], "abschluss", "release", "release", "Lauf abgeschlossen")
                    return
                self._update_run(run["id"], status="aktiv", reason="")
                self._advance(run, step, f"{gate} durch {person['name']} bestätigt")
                return
            if gate == "G5":
                self._update_run(run["id"], status="abgelehnt", reason=f"Produktion abgelehnt: {comment}")
                return
            back_to = GATE_BACK_TO[gate]
            finding = [{"severity": "hoch", "location": gate, "impact": comment,
                        "recommendation": f"Rückmeldung von {person['name']} umsetzen"}]
            self._set_corrections(run, pending={back_to: finding})
            self._update_run(run["id"], status="aktiv", step_index=self.registry.step_index(back_to), reason="")
            self.store.event(run["id"], "ruecklauf", f"mensch:{decision['decider']}", self.registry.steps[
                self.registry.step_index(back_to)].role or back_to, f"{gate} abgelehnt: {comment[:120]}")
            return
        if not accepted:
            self._update_run(run["id"], status="abgebrochen", reason=f"{decision['title']}: abgelehnt – {comment}")
            self.store.event(run["id"], "abbruch", f"mensch:{decision['decider']}", "orchestrator", "Lauf abgebrochen")
            return
        if gate == "eskalation":
            self._update_run(run["id"], status="aktiv", reason="")
            self._advance(run, step, f"Fortsetzung trotz Bedenken durch {person['name']}")
        elif gate == "korrekturlimit":
            counts = dict(run["corrections"].get("counts", {}))
            counts[decision["step_id"]] = 0
            back_to = decision["context"].get("back_to") or step.id
            self._set_corrections(run, counts=counts, pending={back_to: decision["context"].get("findings", [])})
            self._update_run(run["id"], status="aktiv", step_index=self.registry.step_index(back_to), reason="")
        else:  # frage, blockade: denselben Schritt mit der Antwort erneut ausführen
            if gate == "blockade" and run["reason"].startswith("Laufbudget"):
                current = self.store.run(run["id"])["corrections"]
                bonus = current.get("budget_bonus", {})
                current["budget_bonus"] = {"max_model_calls": int(bonus.get("max_model_calls", 0)) + 20,
                                           "max_output_tokens": int(bonus.get("max_output_tokens", 0)) + 60000}
                self._update_run(run["id"], corrections=current)
                self.store.event(run["id"], "steuerung", f"mensch:{decision['decider']}", "orchestrator",
                                 f"Laufbudget um 20 Modellaufrufe erhöht durch {person['name']}")
            self._update_run(run["id"], status="aktiv", reason="")

    # -- Fachagenten (außerhalb des V-Modells, nur lokale Modelle, nur Entwürfe) ----------------
    def _local_profiles(self) -> dict[str, Any]:
        profiles = yaml_profiles(self._agents_dir())
        return {name: spec for name, spec in profiles.items()
                if self.profile_providers.get(name) in {"gateway", "simulated"}}

    def save_business_agent(self, spec: dict[str, Any], user: dict[str, Any], agent_id: str = "") -> dict[str, Any]:
        if not fa.is_admin(user):
            raise EngineError("Fachagenten legen nur Administratoren an")
        try:
            clean = fa.validate_spec(spec, self._local_profiles())
        except fa.SpecError as exc:
            raise EngineError(str(exc)) from None
        person = _person(user)
        try:
            saved = self.store.save_business_agent(agent_id, clean, person)
        except KeyError:
            raise EngineError("Fachagent nicht gefunden") from None
        self.store.event(None, "steuerung", f"mensch:{person['username']}", "fachagenten",
                         f"{person['name']} {'ändert' if agent_id else 'legt an'}: Fachagent {saved['id']} {saved['name']}"
                         f" ({saved['status']}, für {', '.join(clean['assigned_roles'] + clean['assigned_users'])})"[:300])
        return saved

    def request_business_design(self, description: str, user: dict[str, Any]) -> dict[str, Any]:
        """Die lokale KI entwirft aus einer Beschreibung einen Fachagenten (nur Vorschlag für den Admin)."""
        if not fa.is_admin(user):
            raise EngineError("Fachagenten legen nur Administratoren an")
        description = " ".join(str(description or "").split())
        if not 15 <= len(description) <= 3000:
            raise EngineError("Beschreibung: 15 bis 3000 Zeichen")
        return self.store.add_business_job("entwurf", "", {"beschreibung": description}, _person(user))

    def submit_business_task(self, agent_id: str, values: dict[str, Any], user: dict[str, Any],
                             context: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            spec = self.store.business_agent(agent_id)
        except KeyError:
            raise EngineError("Fachagent nicht gefunden") from None
        if not fa.may_use(spec, user):
            raise EngineError("Keine Befugnis für diesen Fachagenten")
        if spec["status"] != "aktiv":
            raise EngineError("Fachagent ist pausiert")
        try:
            clean = fa.validate_input(spec["template"], values)
        except fa.SpecError as exc:
            raise EngineError(str(exc)) from None
        allowed = {k: v for k, v in (context or {}).items() if k in spec["context_sources"]}
        return self.store.add_business_job("aufgabe", agent_id, {**clean, "_context": allowed}, _person(user))

    def decide_business_job(self, job_id: str, outcome: str, user: dict[str, Any], edited: dict[str, Any] | None = None,
                            comment: str = "") -> dict[str, Any]:
        if outcome not in {"freigeben", "verwerfen"}:
            raise EngineError("Ergebnis muss freigeben oder verwerfen sein")
        try:
            job = self.store.business_job(job_id)
        except KeyError:
            raise EngineError("Aufgabe nicht gefunden") from None
        if job["kind"] != "aufgabe" or job["status"] != "fertig":
            raise EngineError("Nur fertige Entwürfe lassen sich freigeben oder verwerfen")
        if job["requested_by"].get("username") != user.get("username") and not fa.is_admin(user):
            raise EngineError("Keine Befugnis: freigeben darf, wer die Aufgabe gestellt hat, oder ein Administrator")
        output = dict(job["output"])
        if outcome == "freigeben" and edited:
            for key, value in edited.items():
                if key in output and isinstance(value, str):
                    output[key] = value.strip()[:8000]
        person = _person(user)
        self.store.update_business_job(job_id, status="freigegeben" if outcome == "freigeben" else "verworfen",
                                       output=output, decided_by={**person, "comment": " ".join(comment.split())[:500]})
        self.store.event(None, "entscheidung", f"mensch:{person['username']}", "fachagenten",
                         f"{person['name']}: Entwurf {job_id} {'freigegeben' if outcome == 'freigeben' else 'verworfen'}")
        return self.store.business_job(job_id)

    def _business_agent_identity(self, profile: str, name: str) -> Agent:
        spec = yaml_profiles(self._agents_dir())[profile]
        return Agent(id="FA", role="fachagenten", number=99, name=name, owner="Administration", status="testbetrieb",
                     autonomy="A1", approved_until=date.max, model_profile=profile, family=str(spec["family"]),
                     gateway_alias=str(spec["gateway_alias"]), kind="create", mission=name, tools=(), reads=(),
                     prompt_file=self._agents_dir() / "prompts" / "_gemeinsam.md", reviewed_by=None, escalation="",
                     evidence="")

    def process_business_job(self) -> bool:
        """Eine wartende Fachagenten-Aufgabe mit dem lokalen Modell bearbeiten."""
        waiting = self.store.business_jobs(status="wartend", limit=1)
        if not waiting:
            return False
        job = waiting[0]
        self.store.update_business_job(job["id"], status="in_arbeit")
        started = time.monotonic()
        try:
            if job["kind"] == "entwurf":
                profile, name = "assistenz", "Fachagenten-Entwurf"
                system, user_text = fa.COMMON + "\n\n" + fa.DESIGN_PROMPT, "# Beschreibung\n" + job["input"]["beschreibung"]
                context = {"kind": "entwurf", "beschreibung": job["input"]["beschreibung"]}
            else:
                spec = self.store.business_agent(job["agent_id"])
                profile, name = spec["model_profile"], spec["name"]
                values = {k: v for k, v in job["input"].items() if not k.startswith("_")}
                system, user_text = fa.task_prompt(spec, values, job["input"].get("_context") or {})
                context = {"kind": "aufgabe", "template": spec["template"], "input": values}
            agent = self._business_agent_identity(profile, name)
            provider = self.providers[self.profile_providers[profile]]
            reply = provider.generate(AgentRequest(job["id"], "fachagent", agent, system, user_text, 3000, context))
            result = extract_json(reply.text)
            output = fa.normalize_design(result) if job["kind"] == "entwurf" else \
                fa.normalize_output(spec["template"], result)
        except (ProviderError, ContractError, fa.SpecError, KeyError, ValueError) as exc:
            self.store.update_business_job(job["id"], status="fehler", error=str(exc)[:300],
                                           seconds=round(time.monotonic() - started, 1))
            return True
        self.store.record_usage(job["id"], "fachagent", "fachagenten", reply.provider, reply.model,
                                reply.input_tokens, reply.output_tokens, reply.seconds)
        self.store.update_business_job(job["id"], status="fertig", output=output, model=f"{reply.provider}/{reply.model}",
                                       seconds=round(time.monotonic() - started, 1))
        return True

    def business_overview(self) -> dict[str, Any]:
        jobs = self.store.business_jobs(limit=60)
        agents = self.store.business_agents()
        for agent in agents:
            agent["open_jobs"] = sum(1 for j in jobs if j["agent_id"] == agent["id"] and j["status"] in {"wartend", "in_arbeit", "fertig"})
        return {"agents": agents, "jobs": jobs, "profiles": sorted(self._local_profiles()), **fa.public_templates()}

    # -- Agenteneigenschaften ansehen und ändern -----------------------------------------------
    def _agents_dir(self) -> Path:
        return self.registry.prompts_dir.parent

    @staticmethod
    def _editable_values(registry: Registry, role: str) -> dict[str, Any]:
        agent = registry.agent(role)
        values = {name: value for name, value in agent.public().items() if name in EDITABLE_FIELDS}
        values["prompt_text"] = registry.role_prompt(role)
        return values

    def agent_config(self, role: str) -> dict[str, Any]:
        """Wie ein Agent konfiguriert ist: wirksame Werte, Registerwerte, Übersteuerungen, Laufzeit, Protokoll."""
        try:
            agent = self.registry.agent(role)
            base = registry_module.load(self._agents_dir())
        except RegistryError as exc:
            raise EngineError(str(exc)) from None
        profiles = {name: {"alias": spec.get("gateway_alias"), "family": spec.get("family"),
                           "description": spec.get("description", "")}
                    for name, spec in yaml_profiles(self._agents_dir()).items()}
        escalation = (self.escalation.get("roles") or {}).get(role) if self.escalation.get("enabled") else None
        return {
            "role": role, "id": agent.id, "number": agent.number, "kind": agent.kind,
            "values": self._editable_values(self.registry, role),
            "base": self._editable_values(base, role),
            "overridden": sorted((self.registry.overrides.get(role) or {}).keys()),
            "editable": list(EDITABLE_FIELDS),
            "options": {"status": sorted(STATUSES), "autonomy": sorted(AGENT_AUTONOMY), "model_profile": profiles,
                        "tools": dict(self.registry.tools), "reads": list(self.registry.artifact_kinds),
                        "data_classes": list(DATA_CLASSES)},
            "runtime": {
                "provider": self.profile_providers.get(agent.model_profile, ""), "gateway_alias": agent.gateway_alias,
                "family": agent.family, "escalation": escalation,
                "opencode": role in self.opencode_roles and "opencode" in self.providers,
                "paused": self.store.controls().get(f"agent:{role}") == "pausiert", "active": agent.active(),
            },
            "workflow": [{"id": s.id, "label": s.label, "kind": s.kind, "ep": s.ep} for s in self.registry.steps
                         if s.role == role],
            "reviewed_by": agent.reviewed_by,
            "rights": self._agent_rights(agent),
            "history": self.store.agent_settings_log(role),
            "digest": self.registry.digest[:16], "override_error": self.override_error,
        }

    def update_agent(self, role: str, changes: dict[str, Any], user: dict[str, Any], reason: str) -> dict[str, Any]:
        """Agenteneigenschaften übersteuern (nur Administratoren). ``None`` setzt ein Feld auf das Register zurück.

        Das Ergebnis muss die Registerprüfung bestehen (Unabhängigkeit, Werkzeuge, Artefakte, Datenklassen).
        Der Registerstand ändert sich; offene Läufe halten an, bis ein Mensch sie umstellt.
        """
        if not {str(r) for r in user.get("roles", [])} & CONFIG_ADMIN_ROLES:
            raise EngineError("Agenteneigenschaften ändern nur Administratoren (platform-admin)")
        reason = " ".join(str(reason or "").split())
        if len(reason) < 5:
            raise EngineError("Bitte eine Begründung angeben (mindestens 5 Zeichen)")
        if not isinstance(changes, dict) or not changes:
            raise EngineError("Keine Änderung angegeben")
        with self.lock:
            try:
                self.registry.agent(role)
                base = self._editable_values(registry_module.load(self._agents_dir()), role)
                current = dict(self.registry.overrides.get(role) or {})
                before = self._editable_values(self.registry, role)
                for name, value in changes.items():
                    if value is None or check_override(name, value) == base.get(name):
                        current.pop(name, None)
                    else:
                        current[name] = check_override(name, value)
                overrides = {**self.registry.overrides, role: current}
                updated = registry_module.load(self._agents_dir(), {k: v for k, v in overrides.items() if v})
            except RegistryError as exc:
                raise EngineError(f"Abgelehnt: {exc}") from None
            after = self._editable_values(updated, role)
            diff = {name: [before[name], after[name]] for name in EDITABLE_FIELDS if before.get(name) != after.get(name)}
            if not diff:
                raise EngineError("Keine Änderung gegenüber dem aktuellen Stand")
            person = _person(user)
            logged = {name: ["(geändert)", "(geändert)"] if name == "prompt_text" else pair for name, pair in diff.items()}
            self.store.save_agent_override(role, current, logged, reason, person, updated.digest)
            self.registry = updated
            self.override_error = ""
            self.store.event(None, "steuerung", f"mensch:{person['username']}", role,
                             f"{person['name']} ändert {self.registry.agent(role).name}: {', '.join(diff)} – {reason}"[:300],
                             {"fields": list(diff), "digest": updated.digest[:16]})
        return self.agent_config(role)

    # -- Projektrechte ------------------------------------------------------------------------
    def project_scopes(self, code: str) -> list[str]:
        """Änderungsbereiche eines Katalogprojekts; Muster wie dms-* werden gegen die Bereiche aufgelöst."""
        patterns = [str(p) for p in (self.projects.get(code) or {}).get("scopes", [])]
        return [scope for scope in self.scopes if any(fnmatch.fnmatchcase(scope, p) for p in patterns)] + \
            [p for p in patterns if not any(ch in p for ch in "*?[") and p not in self.scopes]

    @staticmethod
    def project_roles(code: str) -> dict[str, str]:
        return {right: f"flow-prj-{code.lower()}-{right}" for right in ("lesen", "aendern")}

    def auftrag_access(self, user: dict[str, Any], auftrag: dict[str, Any]) -> str:
        """Recht einer Person an einem Auftrag. Nur echte Altaufträge (nie an den Katalog gebunden) sind offen;
        eine Katalogbindung bleibt erhalten, auch wenn Katalogdatei oder Projektcode später fehlen."""
        code = str(auftrag.get("project", ""))
        bound = bool(auftrag.get("catalog_bound") or auftrag.get("catalog"))
        if code in self.projects:
            return self.project_access(user, code)
        if not bound:
            return "aendern"
        roles = {str(r) for r in user.get("roles", [])}
        return "lesen" if roles & OVERSIGHT_ROLES else ""

    def can_see_run(self, user: dict[str, Any], run: dict[str, Any]) -> bool:
        roles = {str(r) for r in user.get("roles", [])}
        return bool(self.auftrag_access(user, run["auftrag"])) or bool(roles & OVERSIGHT_ROLES)

    def _require_auftrag(self, user: dict[str, Any], auftrag: dict[str, Any], need: str) -> None:
        access = self.auftrag_access(user, auftrag)
        if access == "aendern" or (need == "lesen" and access == "lesen"):
            return
        code = str(auftrag.get("project", ""))
        raise EngineError(f"Keine Befugnis im Projekt {code}: {'Änderungsrecht' if need == 'aendern' else 'Projektmitgliedschaft'}"
                          f" fehlt (AD-Gruppe AD-GG-FLOW-PRJ-{code}-{'AENDERN' if need == 'aendern' else 'LESEN'})")

    def _require_run(self, user: dict[str, Any], run: dict[str, Any], need: str) -> None:
        self._require_auftrag(user, run["auftrag"], need)

    def _project_scope_set(self, auftrag: dict[str, Any]) -> set[str]:
        code = str(auftrag.get("project", ""))
        return set(self.project_scopes(code)) if code in self.projects else set(self.scopes)

    def project_access(self, user: dict[str, Any], code: str) -> str:
        """Recht einer Person in einem Katalogprojekt: aendern, lesen oder leer (ohne Katalog: frei)."""
        if not self.projects:
            return "aendern"
        if code not in self.projects:
            return ""
        roles = {str(r) for r in user.get("roles", [])}
        if self.demo_mode and "platform-admin" in roles:
            return "aendern"
        names = self.project_roles(code)
        if names["aendern"] in roles:
            return "aendern"
        return "lesen" if names["lesen"] in roles else ""

    def can_see_project(self, user: dict[str, Any], code: str) -> bool:
        roles = {str(r) for r in user.get("roles", [])}
        return bool(self.project_access(user, code)) or bool(roles & OVERSIGHT_ROLES)

    def _require_project(self, user: dict[str, Any], code: str, need: str) -> None:
        access = self.project_access(user, code)
        if access == "aendern" or (need == "lesen" and access == "lesen"):
            return
        missing = "Änderungsrecht" if need == "aendern" else "Projektmitgliedschaft"
        raise EngineError(f"Keine Befugnis im Projekt {code}: {missing} fehlt (AD-Gruppe "
                          f"AD-GG-FLOW-PRJ-{code}-{'AENDERN' if need == 'aendern' else 'LESEN'})")

    def seed_projects(self) -> list[str]:
        """Legt die Katalogprojekte mit Arbeitspaketen als Projekte an (idempotent, beim Start)."""
        created = []
        for code, spec in self.projects.items():
            packages = [dict(item) for item in spec.get("packages", [])]
            if not packages:
                continue
            project_id = f"PRJ-{code}"
            try:
                self.store.project(project_id)
                continue
            except KeyError:
                pass
            auftrag = {"title": spec["title"], "goal": spec.get("goal", spec["title"]),
                       "user_group": spec.get("user_group", "Fachbereich"), "behavior": spec.get("goal", spec["title"]),
                       "exclusions": "", "success_example": "Alle Arbeitspakete sind abgenommen.",
                       "data_class": "intern", "change_class": "kritisch" if spec.get("criticality") in {"K2", "K3"}
                       else "neue_funktion", "project_class": "L", "criticality": spec.get("criticality", "K1"),
                       "domain": spec.get("domain", "it"), "scope": "", "scope_label": "", "paths": [],
                       "reference_paths": [], "project": code, "execution": "automatisch",
                       "owner": spec.get("owner", "Projektkatalog"), "catalog": True, "catalog_bound": True}
            with self.lock:
                run = self.store.create_run(title=spec["title"], change_class=auftrag["change_class"], auftrag=auftrag,
                                            requested_by=CATALOG_OWNER, registry_digest=self.registry.digest,
                                            idempotency_key=f"katalog:{code}", announce=False)
                project = self.store.complete_with_project(
                    run, packages, CATALOG_OWNER, project_id=project_id, completion="katalog",
                    step_index=len(self.registry.steps),
                    reason="Projekt aus dem Projektkatalog angelegt; Arbeitspakete laufen als eigene Aufträge")
                self.store.event(run["id"], "projekt", "orchestrator", "projektplanung",
                                 f"Projekt {project['id']} aus dem Projektkatalog mit {len(packages)} Arbeitspaketen angelegt",
                                 {"project_id": project["id"]})
            created.append(project_id)
        return created

    def project_catalog(self) -> dict[str, Any]:
        return {code: {"title": spec.get("title", code), "domain": spec.get("domain", "it"),
                       "criticality": spec.get("criticality", "K1"), "owner": spec.get("owner", ""),
                       "scopes": self.project_scopes(code), "roles": self.project_roles(code),
                       "groups": {right: f"AD-GG-FLOW-PRJ-{code}-{right.upper()}" for right in ("lesen", "aendern")}}
                for code, spec in self.projects.items()}

    def _authorize(self, user: dict[str, Any], decider: str) -> None:
        roles = {str(role) for role in user.get("roles", [])}
        allowed = set(self.registry.human_roles.get(decider, {}).get("keycloak_roles", []))
        if roles & allowed:
            return
        if self.demo_mode and "platform-admin" in roles:
            return
        raise EngineError(f"Keine Befugnis für die Rolle {decider}")

    # =================================================================================
    # Steuerung
    # =================================================================================
    def control(self, action: str, user: dict[str, Any], *, role: str = "", run_id: str = "") -> None:
        roles = {str(r) for r in user.get("roles", [])}
        if not roles & CONTROL_ROLES:
            raise EngineError("Steuerung nur für Plattformbetrieb oder Tech Lead")
        actor = _person(user)["name"]
        with self.lock:
            if action in {"pause", "resume"} and not role:
                self.store.set_control("global", "pausiert" if action == "pause" else "bereit", actor)
            elif action in {"pause", "resume"}:
                self.registry.agent(role)
                self.store.set_control(f"agent:{role}", "pausiert" if action == "pause" else "bereit", actor)
                if action == "resume":
                    for item in self.store.runs(limit=200):
                        if item["status"] == "pausiert":
                            self._update_run(item["id"], status="aktiv", reason="")
            elif action == "cancel" and run_id:
                run = self.store.run(run_id)
                if not roles & CROSS_PROJECT_OPERATIONS:
                    self._require_run(user, run, "aendern")  # Tech Lead/Betrieb nur im eigenen Projekt
                if run["status"] not in OPEN_RUN_STATES:
                    raise EngineError("Lauf ist bereits beendet")
                self._update_run(run_id, status="abgebrochen", reason=f"durch {actor} abgebrochen")
                if self.preview is not None and any(
                        d["gate"] == "G4" for d in self.store.decisions(status="offen", run_id=run_id)):
                    self.preview.stop()
                for decision in self.store.decisions(status="offen", run_id=run_id):
                    self.store.close_decision(decision["id"], "verfallen", "", _person(user), "Lauf abgebrochen")
                self.store.event(run_id, "abbruch", "mensch:betrieb", "orchestrator", f"Lauf durch {actor} abgebrochen")
            else:
                raise EngineError("unbekannte Steuerungsaktion")

    # =================================================================================
    # Hilfen
    # =================================================================================
    def _advance(self, run: dict[str, Any], step: Step, message: str) -> None:
        index = self._next_applicable(run, self.registry.step_index(step.id) + 1)
        if index >= len(self.registry.steps):
            self._update_run(run["id"], status="abgeschlossen", step_index=index, reason="")
            return
        following = self.registry.steps[index]
        self._update_run(run["id"], step_index=index, status="aktiv", reason="")
        source = step.role or ("integration" if step.kind == "check" else step.id)
        target = following.role or ("integration" if following.kind == "check" else following.id)
        self.store.event(run["id"], "uebergabe", source, target, f"{message} → {following.label}",
                         {"from_step": step.id, "to_step": following.id})

    def _block(self, run: dict[str, Any], reason: str, gate: str, *, step_id: str) -> None:
        step = next((s for s in self.registry.steps if s.id == step_id), None)
        actor = (step.role or ("integration" if step.kind == "check" else step.id)) if step else "orchestrator"
        self._update_run(run["id"], status="blockiert", reason=reason[:500])
        self._open_decision(run["id"], step_id, gate, "tech-lead", "Lauf blockiert", reason[:1500],
                                 {"step": step_id}, actor=actor)

    def _set_corrections(
        self, run: dict[str, Any], *, counts: dict[str, int] | None = None,
        pending: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        current = self.store.run(run["id"])["corrections"]
        if counts is not None:
            current["counts"] = counts
        if pending is not None:
            current["pending"] = {**current.get("pending", {}), **pending}
        self._update_run(run["id"], corrections=current)

    def _clear_pending(self, run: dict[str, Any], step_id: str) -> None:
        current = self.store.run(run["id"])["corrections"]
        if step_id in current.get("pending", {}):
            current["pending"].pop(step_id)
            self._update_run(run["id"], corrections=current)

    # =================================================================================
    # Sicht für FLOWPORTAL
    # =================================================================================
    def overview(self) -> dict[str, Any]:
        runs = self.store.runs(limit=30)
        open_decisions = self.store.decisions(status="offen")
        referenced: set[str] = set()
        # Laufender Schritt → Beginn (für „seit …“ am laufbezogenen Halter); auch als Menge nutzbar.
        running = {(step["run_id"], step["role"]): iso(step["started"]) for step in self.store.running_steps()}
        controls = self.store.controls()
        events = self.store.events(limit=60)
        participation = self.store.participation([run["id"] for run in runs])  # zwei Sammelabfragen statt 2 je Lauf
        agents = []
        for agent in sorted(self.registry.agents.values(), key=lambda a: a.number):
            current = None
            state = "bereit" if agent.active() else "inaktiv"
            for run in runs:
                if run["status"] not in OPEN_RUN_STATES or run["step_index"] >= len(self.registry.steps):
                    continue
                step = self.registry.steps[run["step_index"]]
                if step.role != agent.role:
                    continue
                if (run["id"], agent.role) in running:
                    state = "arbeitet"
                elif run["status"] == "aktiv" and state != "arbeitet":
                    state = "als_naechstes"
                elif run["status"] in {"wartet", "blockiert"} and state == "bereit":
                    state = "wartet"
                current = {"run_id": run["id"], "auftrag_id": run["auftrag_id"], "title": run["title"],
                           "step": step.id, "label": step.label}
                if state == "arbeitet":
                    break
            if controls.get(f"agent:{agent.role}") == "pausiert":
                state = "pausiert"
            last = next((e for e in reversed(events) if e["actor"] == agent.role), None)
            if current:
                referenced.add(current["run_id"])
            agents.append({**agent.public(), "rights": self._agent_rights(agent), "state": state, "current": current,
                           "overridden": sorted((self.registry.overrides.get(agent.role) or {}).keys()),
                           "last": {"message": last["message"], "at": last["at"], "run_id": last["run_id"]} if last else None})
        edges: Counter[tuple[str, str, str]] = Counter()
        last_seen: dict[tuple[str, str, str], str] = {}
        for event in self.store.events(limit=400):
            if event["kind"] in {"uebergabe", "ruecklauf", "entscheidung", "entscheidung_offen", "werkzeug"}:
                key = (event["actor"], event["target"], event["kind"])
                edges[key] += 1
                last_seen[key] = event["at"]
        steps = self.registry.steps
        usage_by_run = self.store.usage_by_run()
        projects = self.store.projects(limit=20)
        referenced |= {r["id"] for r in runs} | {d["run_id"] for d in open_decisions}
        referenced |= {e["run_id"] for e in events if e.get("run_id")} | {u["run_id"] for u in usage_by_run}
        for project in projects:
            referenced |= {project["run_id"], *(p["run_id"] for p in project["packages"] if p["run_id"])}
        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            # Für die Rechtefilter der Plattform: Projektbindung jedes Laufs, der in dieser Übersicht vorkommt.
            "access": {"runs": self._access_map(referenced),
                       "projects": {p["id"]: {"project": p["auftrag"].get("project", ""),
                                              "bound": bool(p["auftrag"].get("catalog_bound") or p["auftrag"].get("catalog"))}
                                    for p in projects}},
            "control": controls.get("global", "bereit"),
            "agent_controls": {k[6:]: v for k, v in controls.items() if k.startswith("agent:")},
            "demo_mode": self.demo_mode,
            "registry": {"id": self.registry.register_id, "digest": self.registry.digest[:16],
                         "policy_version": self.registry.policy_version},
            "providers": {profile: provider for profile, provider in self.profile_providers.items()},
            "rm_connected": self.rm.enabled,
            "sandbox": self.sandbox is not None,
            "agents": agents,
            "productive_agents": list(self.registry.productive_agents),
            "human_roles": {name: {"label": spec.get("label", name), "keycloak_roles": spec.get("keycloak_roles", []),
                                   "open": sum(1 for d in open_decisions if d["decider"] == name)}
                            for name, spec in self.registry.human_roles.items()},
            "pipeline": [{"id": s.id, "label": s.label, "kind": s.kind, "role": s.role, "decider": s.decider,
                          "ep": s.ep, "when": {k: list(v) for k, v in s.when.items()}, "produces": s.produces,
                          "subject": s.subject} for s in steps],
            "runs": [self._run_summary(run, open_decisions, participation=participation.get(run["id"]),
                                       running=running, controls=controls) for run in runs],
            "projects": [self.project_summary(project) for project in projects],
            "project_catalog": self.project_catalog(),
            "business": self.business_overview(),
            "decisions": [self._decision_summary(d, {r["id"]: r for r in runs}) for d in open_decisions],
            "events": events[-40:],
            "interactions": [
                {"from": a, "to": b, "kind": kind, "count": count, "last_at": last_seen[(a, b, kind)]}
                for (a, b, kind), count in edges.most_common(60)
            ],
            "usage": {"totals": self.store.usage_totals(), "by_run": usage_by_run},
            "metrics": {
                "runs_open": sum(1 for r in runs if r["status"] in OPEN_RUN_STATES),
                # Nur Produktionsfreigaben nach G5 zählen als erledigt; Planung und Katalog getrennt.
                "runs_done": sum(1 for r in runs if self._completion(r) == "produktion"),
                "runs_planned": sum(1 for r in runs if self._completion(r) == "projektplanung"),
                "projects_from_catalog": sum(1 for r in runs if self._completion(r) == "katalog"),
                "decisions_open": len(open_decisions),
                "agents_working": sum(1 for a in agents if a["state"] == "arbeitet"),
                "reworks": sum(1 for e in events if e["kind"] == "ruecklauf"),
            },
        }

    def _access_map(self, run_ids: set[str]) -> dict[str, dict[str, Any]]:
        result = {}
        for run_id in run_ids:
            try:
                auftrag = self.store.run(run_id)["auftrag"]
            except KeyError:
                continue
            result[run_id] = {"project": str(auftrag.get("project", "")),
                              "bound": bool(auftrag.get("catalog_bound") or auftrag.get("catalog"))}
        return result

    def _run_summary(self, run: dict[str, Any], open_decisions: list[dict[str, Any]], *,
                     participation: dict[str, list[Any]] | None = None,
                     running: dict[tuple[str, str], str | None] | set[tuple[str, str]] | None = None,
                     controls: dict[str, str] | None = None) -> dict[str, Any]:
        steps = self.registry.steps
        index = min(run["step_index"], len(steps))
        current = steps[index] if index < len(steps) else None
        waiting = next((d for d in open_decisions if d["run_id"] == run["id"]), None)
        auftrag = run["auftrag"]
        applicable = [i for i, s in enumerate(steps) if s.applies(auftrag)] or [0]
        done = sum(1 for i in applicable if i < index)
        return {
            "id": run["id"], "auftrag_id": run["auftrag_id"], "title": run["title"],
            "change_class": run["change_class"], "status": run["status"], "reason": run["reason"],
            "step": current.id if current else "fertig", "step_label": current.label if current else "Abgeschlossen",
            "role": current.role if current else None, "progress": round(done / len(applicable) * 100),
            "ep": current.ep if current else "", "project_class": auftrag.get("project_class", "S"),
            "criticality": auftrag.get("criticality", "K1"), "domain": auftrag.get("domain", "it"),
            "project_id": auftrag.get("project_id", ""), "package_key": auftrag.get("package_key", ""),
            "project": auftrag.get("project", ""), "requested_by": run["requested_by"].get("name"), "updated_at": run["updated_at"],
            "created_at": run["created_at"], "model_calls": run["model_calls"], "completion": self._completion(run),
            "waiting_for": waiting["decider"] if waiting else None,
            "preview_url": (waiting or {}).get("context", {}).get("preview_url"),
            "branch": ((self.store.latest_artifact(run["id"], "uebernahme") or {}).get("content") or {}).get("branch"),
            "holder": self._holder(run, current, waiting, running, controls),
            **self._participation(run, participation),
        }

    def _holder(self, run: dict[str, Any], current: Step | None, waiting: dict[str, Any] | None,
                running: dict[tuple[str, str], str | None] | set[tuple[str, str]] | None,
                controls: dict[str, str] | None) -> dict[str, Any]:
        """Bei wem dieser eine Lauf gerade hängt (laufbezogen, nicht der Sammelzustand der Agentenrolle).

        Dieselbe Agentenrolle kann in mehreren Läufen anstehen und nur in einem davon arbeiten;
        ein globaler oder rollenbezogener Stopp hält einen eingeplanten Schritt an. ``since`` nennt den
        Beginn genau dieses Halterzustands (laufender Schritt bzw. offene Entscheidung), sofern bekannt;
        ohne ``since`` zeigt die Oberfläche „Lauf zuletzt geändert“.
        """
        if running is None:
            running = {(step["run_id"], step["role"]): iso(step["started"]) for step in self.store.running_steps()}
        if controls is None:
            controls = self.store.controls()
        status = run["status"]
        decider = waiting["decider"] if waiting else None
        if status not in OPEN_RUN_STATES:
            return {"kind": "fertig"}
        opened = {"since": waiting["created_at"]} if waiting and waiting.get("created_at") else {}
        if status == "blockiert":
            return {"kind": "blockiert", "reason": run["reason"], "role": decider, **opened}
        if status == "pausiert":
            return {"kind": "pausiert", "reason": run["reason"]}
        if decider:
            return {"kind": "mensch", "role": decider, **opened}
        if current is None:
            return {"kind": "orchestrator"}
        role = current.role or ""
        active_key = next(((run_id, step_role) for run_id, step_role in running
                           if run_id == run["id"] and (not role or step_role == role)), None)
        if active_key:  # ein laufender Schritt wird auch bei Stopp noch zu Ende geführt
            started = running.get(active_key) if isinstance(running, dict) else None
            return {"kind": "integration" if current.kind == "check" else "agent_arbeitet", "role": role,
                    "running": True, "stopping": controls.get("global") == "pausiert"
                    or controls.get(f"agent:{role}") == "pausiert", **({"since": started} if started else {})}
        if controls.get("global") == "pausiert":
            return {"kind": "pausiert_global"}
        if role and controls.get(f"agent:{role}") == "pausiert":
            return {"kind": "pausiert_agent", "role": role}
        if current.kind == "check":
            return {"kind": "integration", "running": False}
        if role:
            return {"kind": "agent_eingeplant", "role": role}
        return {"kind": "orchestrator"}

    def _participation(self, run: dict[str, Any], loaded: dict[str, list[Any]] | None = None) -> dict[str, Any]:
        """Wer an einem Auftrag beteiligt ist: Personen (Auftrag, Entscheidungen) und Agenten (bisherige Schritte).

        Damit zeigt die Agentenzentrale „Meine Sicht“: Aufträge, an denen ich beteiligt bin, und bei wem sie hängen.
        """
        people: dict[str, str] = {}
        requester = run["requested_by"] or {}
        if requester.get("username"):
            people[str(requester["username"])] = str(requester.get("name") or requester["username"])
        if loaded is None:  # Einzelabruf (Laufdetail); die Übersicht lädt gesammelt über store.participation
            loaded = self.store.participation([run["id"]])[run["id"]]
        for person in loaded["deciders"]:
            person = person or {}
            if person.get("username"):
                people[str(person["username"])] = str(person.get("name") or person["username"])
        roles = list(dict.fromkeys(role for role in loaded["roles"] if role))
        return {"participants": [{"username": u, "name": n} for u, n in people.items()], "agents_involved": roles}

    def _decision_summary(self, decision: dict[str, Any], runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Entscheidung mit Bezug zum Fachauftrag, damit die Person sofort sieht, worum es geht."""
        summary = {key: decision[key] for key in ("id", "run_id", "step_id", "gate", "decider", "title", "question",
                                                   "digest", "created_at", "context")}
        summary["focus"] = self._focus(decision)
        run = runs.get(decision["run_id"])
        if run is None:
            try:
                run = self.store.run(decision["run_id"])
            except KeyError:
                run = None
        if run is not None:
            auftrag = run["auftrag"]
            summary["auftrag"] = {
                "id": run["auftrag_id"], "title": run["title"], "change_class": run["change_class"],
                "requested_by": run["requested_by"].get("name"), "goal": auftrag.get("goal", ""),
                "success_example": auftrag.get("success_example", ""), "scope_label": auftrag.get("scope_label", ""),
                "project_class": auftrag.get("project_class", "S"), "criticality": auftrag.get("criticality", "K1"),
                "domain": auftrag.get("domain", "it"), "project": auftrag.get("project", ""),
            }
        return summary

    GATE_FOCUS = {
        "EP1": ["projektplan", "geschaeftsbewertung"],
        "G1": ["anforderungen", "baseline", "anforderungsbefund"],
        "G2": ["architektur", "sicherheitsbefund"],
        "G3": ["implementierung", "integration", "codebefund"],
        "G4": ["ui_pruefung", "implementierung", "dokumentation", "prozessbewertung", "nachweise"],
        "G5": ["nachweise", "uebernahme", "implementierung"],
    }

    def _focus(self, decision: dict[str, Any]) -> list[str]:
        """Welche Ergebnisse eine Person für diese Entscheidung ansehen muss."""
        if decision["gate"] in self.GATE_FOCUS:
            return self.GATE_FOCUS[decision["gate"]]
        step = next((s for s in self.registry.steps if s.id == decision["step_id"]), None)
        kinds: list[str] = []
        if step is not None:
            if step.produces:
                kinds.append(step.produces)
            if step.subject and step.subject != "auftrag":
                kinds.append(step.subject)
            back_to = decision["context"].get("back_to") or step.on_rework.get("back_to") or step.on_failure.get("back_to")
            target = next((s for s in self.registry.steps if s.id == back_to), None)
            if target is not None and target.produces:
                kinds.append(target.produces)
        return list(dict.fromkeys(kinds or ["auftrag"]))

    def run_detail(self, run_id: str, user: dict[str, Any] | None = None) -> dict[str, Any]:
        run = self.store.run(run_id)
        if user is not None and not self.can_see_run(user, run):
            raise KeyError(run_id)  # wie „nicht gefunden“: keine Auskunft über fremde Läufe
        completion = self._completion(run)
        return {
            "run": run,
            "summary": self._run_summary(run, self.store.decisions(status="offen")),
            "steps": self.store.steps(run_id),
            "artifacts": [{k: a[k] for k in ("kind", "version", "role", "step_id", "digest", "content", "created_at")}
                          | {"refs": {k: v for k, v in a["refs"].items() if k != "workspace"}}
                          for a in self.store.artifacts(run_id)],
            "decisions": self.store.decisions(run_id=run_id),
            "events": self.store.events(run_id=run_id, limit=300),
            # Katalog- und Planungsläufe liefern nichts aus: keine Release-Manifestprüfung.
            "manifest_gaps": [] if completion in {"katalog", "projektplanung"} else self.verify_manifest(run_id),
            "completion": completion,
            "project": self._project_of(run_id),
        }

    @staticmethod
    def _completion(run: dict[str, Any]) -> str:
        """Abschlussart; Altläufe ohne gespeicherte Art werden aus Katalogkennung und Grund abgeleitet."""
        if run["status"] != "abgeschlossen":
            return ""
        if run.get("completion"):
            return str(run["completion"])
        if run["auftrag"].get("catalog"):
            return "katalog"
        if str(run.get("reason", "")).startswith("Projekt definiert"):
            return "projektplanung"
        if str(run.get("reason", "")).startswith("Produktionsfreigabe"):
            return "produktion"
        return "ende"

    def _project_of(self, run_id: str) -> dict[str, Any] | None:
        project = self.store.project_for_run(run_id)
        return self.project_summary(project) if project else None


# Rollen, die Referenzdateien eines Änderungsbereichs lesen (fachlicher Hintergrund, keine Implementierung).
# Wer ein Werkzeug bei jedem Aufruf prüft (Präfix des logischen Werkzeugnamens).
TOOL_ENFORCER = {"rm": "FLOWWORK RM-Adapter", "ticket": "FLOWWORK RM-Adapter", "knowledge": "FLOWWORK RM-Adapter",
                 "repo": "Orchestrator-Sandbox", "ci": "Orchestrator", "sbom": "Orchestrator"}

REFERENCE_READERS = {"anforderungen", "anforderungspruefung", "architektur", "entwicklung", "dokumentation",
                     "akzeptanztest", "codepruefung"}

UI_HINT = (
    'Wenn ein Testfall über die Oberfläche prüfbar ist, ergänze optional "ui": einen Klickpfad, den der '
    "Orchestrator an G4 im Browser gegen die Vorschau ausführt. Schritte: "
    '{"do":"goto","path":"/dms"}, {"do":"click","text":"…"} oder {"do":"click","role":"button","name":"…"}, '
    '{"do":"fill","label":"…","value":"…"}, {"do":"select","label":"…","value":"…"}, '
    '{"do":"upload","label":"…","fixture":"beispiel.stl|beispiel.pdf|beispiel.png|beispiel.txt"}, '
    '{"do":"expect_text","text":"…"}, {"do":"expect_visible","label":"…"}, {"do":"screenshot","name":"…"}. '
    "Nutze sichtbare Beschriftungen aus den Anforderungen, keine CSS-Selektoren, höchstens 25 Schritte. "
    'Auswahllisten bedienst du mit "select" (label = Feldname, value = sichtbarer Optionstext), nicht mit "click". '
    "Prüfe das Ergebnis mit expect_text und beende jeden Klickpfad mit einem screenshot."
)


def _schema_hint(role: str, kind: str) -> str:
    """Pflichtfelder aus dem Ergebnisvertrag, damit schon der erste Versuch vertragskonform ist."""
    if role in REVIEW_ONLY:
        return ('Ergebnisvertrag: "artifacts" ist eine leere Liste; Befunde stehen in "findings" mit '
                "severity, location, impact (optional recommendation). status fertig oder nacharbeit.")
    artifact_type, required, optional, _ = ARTIFACTS[role]
    fields = ", ".join(required)
    extra = f"; optional: {', '.join(optional)}" if optional else ""
    status = "fertig, entscheidung_offen oder abgebrochen (nie nacharbeit)" if kind == "create" else \
        "fertig, nacharbeit oder entscheidung_offen"
    shape = SHAPE_HINTS.get(role, "")
    return (f'Ergebnisvertrag: jedes Artefakt hat "type": "{artifact_type}" und die Pflichtfelder {fields}{extra}. '
            f"Keine weiteren Felder. status: {status}.{shape}")


SHAPE_HINTS = {
    "integrationstest": (' Form von "steps": [{"action": "Aufruf über die Schnittstelle", "expected": "beobachtbares '
                         'Ergebnis"}]; "interface" nennt die Schnittstelle aus der Architektur.'),
    "projektplanung": (' "v_level" ist eine Ebene des V-Modells (zum Beispiel anforderungen, software_architektur, '
                       'implementierung, software_integration, software_verifikation, abnahme); "wave" ist eine Zahl.'),
    "akzeptanztest": (' Form von "steps": [{"action": "Was die Person tut", "expected": "Was sie danach sieht"}] '
                      "– jeder Schritt ein Objekt mit genau diesen beiden Texten, auch bei Dokumentation "
                      '(z. B. action "Seite Wareneingang öffnen", expected "Diagramm und Zuständigkeiten sichtbar").'),
}
UI_SUFFIXES = (".html", ".js", ".css", ".tsx", ".jsx", ".vue")


def _has_ui(paths: list[str]) -> bool:
    """Klickpfade lohnen nur, wenn der Auftrag Oberflächendateien ändert."""
    return any(str(path).endswith(UI_SUFFIXES) for path in paths)


def _require_real_change(role: str, handoff: Handoff, originals: dict[str, str | None] | None) -> None:
    """Entwicklung muss den Ausgangsstand wirklich ändern; unveränderte Dateien sind kein Ergebnis."""
    if role != "entwicklung" or handoff.status != "fertig" or originals is None:
        return
    changed = [item["key"] for item in handoff.artifacts if item.get("content") != originals.get(item["key"])]
    if not changed:
        raise ContractError("alle gelieferten Dateien sind identisch mit dem Ausgangsstand – liefere die "
                            "geänderten Inhalte (vollständige Datei mit deinen Änderungen) oder status "
                            "entscheidung_offen mit der Begründung, warum keine Änderung nötig ist")


def _strictest(order: tuple[str, ...], *values: Any) -> str:
    """Strengster gültiger Wert (spätester in ``order``); ungültige oder leere Werte zählen nicht."""
    valid = [str(v) for v in values if str(v or "") in order]
    return max(valid, key=order.index) if valid else order[0]


def _case_results(output: str, keys: list[str]) -> dict[str, str]:
    """Ergebnis je Testfall-ID aus der Ausgabe des Prüfjobs (z. B. ``PASSED tests/x.py::test_IT_1_rechte``).

    Ein Fall gilt nur als bestanden, wenn ein Test mit seiner ID ausdrücklich bestanden hat und keiner
    mit seiner ID fehlschlug. Ohne Treffer bleibt er „fehlt“ – ein grüner Gesamtlauf genügt nicht.
    """
    results = {}
    lines = output.splitlines()
    for key in keys:
        variants = {key, key.replace("-", "_")}
        pattern = re.compile("|".join(rf"(?<![A-Za-z0-9]){re.escape(v)}(?![0-9A-Za-z])" for v in variants), re.IGNORECASE)
        hits = [line for line in lines if pattern.search(line)]
        failed = any(re.search(r"\b(FAILED|ERROR|FAIL)\b|^not ok", line) for line in hits)
        passed = any(re.search(r"\b(PASSED|PASS)\b|^ok\b", line) for line in hits)
        results[key] = "fehlgeschlagen" if failed else "bestanden" if passed else "fehlt"
    return results


def _criteria(baseline: dict[str, Any]) -> dict[str, str]:
    """Gültige Kriterien der Arbeitsbaseline als ``R1/AC-1`` → Anforderung ``R1``."""
    result = {}
    for requirement in baseline.get("items", []):
        for criterion in requirement.get("acceptance_criteria", []) or []:
            label = str(criterion).split(":", 1)[0].strip()
            if label:
                result[f"{requirement.get('key')}/{label}"] = str(requirement.get("key"))
    return result


def _cycles(packages: list[dict[str, Any]]) -> list[str]:
    """Arbeitspakete, die in einem Abhängigkeitszyklus liegen."""
    graph = {str(item.get("key")): [str(d) for d in item.get("depends_on", []) or []] for item in packages}
    state: dict[str, int] = {}
    cyclic: set[str] = set()

    def visit(node: str, path: list[str]) -> None:
        if state.get(node) == 2:
            return
        if state.get(node) == 1:
            cyclic.update(path[path.index(node):])
            return
        state[node] = 1
        for dep in graph.get(node, []):
            if dep in graph:
                visit(dep, [*path, dep])
        state[node] = 2

    for node in graph:
        visit(node, [node])
    return sorted(cyclic)


def _limit(agent: Agent) -> int | None:
    for key in ("max_drafts_per_run", "max_tasks_per_run", "max_tests_per_run", "max_changed_files",
                "max_packages_per_run"):
        if key in agent.limits:
            return int(agent.limits[key])
    return None


def _person(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "username": str(user.get("username") or "unbekannt"),
        "name": str(user.get("name") or user.get("username") or "Unbekannt"),
        "roles": sorted({str(r) for r in user.get("roles", [])}),
    }


def _diff(originals: dict[str, str | None], changes: dict[str, str]) -> str:
    chunks = []
    for path, new in sorted(changes.items()):
        old = originals.get(path) or ""
        chunks.extend(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                           fromfile=f"a/{path}", tofile=f"b/{path}"))
    return "".join(chunks)


__all__ = ["Engine", "EngineError", "digest_of"]


def yaml_profiles(directory: Path) -> dict[str, dict[str, Any]]:
    """Modellprofile aus dem Register (Auswahl für die Agentenzentrale)."""
    data = yaml.safe_load((directory / "registry.yaml").read_text(encoding="utf-8")) or {}
    return dict(data.get("model_profiles") or {})
