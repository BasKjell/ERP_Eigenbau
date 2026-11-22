"""Ablaufsteuerung: Fachauftrag -> Rollen -> Gates -> Fachabnahme (KI-Entwicklungskonzept Teil 02/03).

Die Engine ist deterministisch. Sie entscheidet anhand von ``agents/workflow.yaml`` und dem
gespeicherten Zustand, welche Rolle als Nächstes arbeitet. Modelle liefern nur Text; die Engine
prüft den Ergebnisvertrag, führt erlaubte Werkzeugaufrufe mit der Rollenidentität aus, bindet
Prüfungen und Abnahmen an Version und Digest und legt menschliche Entscheidungen in die
Entscheidungs-Inbox.
"""

from __future__ import annotations

import difflib
import json
import re
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any

from .adoption import Adoption, Preview
from .contract import ARTIFACTS, REVIEW_ONLY, ContractError, Handoff, extract_json, validate
from .providers import AgentReply, AgentRequest, Provider, ProviderError
from .registry import Agent, Registry, Step
from .rm import RM, RMConflict, RMError
from .sandbox import Sandbox, SandboxError, validate_path
from .store import OPEN_RUN_STATES, Store, digest_of

ORCHESTRATOR = ("orchestrator", "FLOW-ORCHESTRATOR")
GATE_BACK_TO = {"G1": "anforderungen", "G2": "architektur", "G3": "entwicklung", "G4": "entwicklung"}
DATA_CLASSES = ("oeffentlich", "intern", "vertraulich")
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
        if self.sandbox is not None:
            for scope in self.scopes.values():
                for path in scope.get("paths", []):
                    validate_path(path, self.sandbox.allowed_prefixes)  # fail closed beim Start
        self.lock = threading.RLock()

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
                )
            except ValueError as exc:
                raise EngineError(str(exc)) from None

    def _validated_auftrag(self, values: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        allowed = {"title", "goal", "user_group", "behavior", "exclusions", "success_example", "data_class",
                   "change_class", "scope", "project", "execution"}
        unknown = set(values) - allowed
        if unknown:
            raise EngineError(f"unbekannte Auftragsfelder {sorted(unknown)}")

        def text(name: str, low: int, high: int, required: bool = True) -> str:
            value = str(values.get(name) or "").strip()
            if (required and len(value) < low) or len(value) > high:
                raise EngineError(f"{name}: {low} bis {high} Zeichen erforderlich")
            return value

        change_class = str(values.get("change_class") or "neue_funktion")
        if change_class not in self.registry.classes:
            raise EngineError("unbekannte Änderungsklasse")
        data_class = str(values.get("data_class") or "intern")
        if data_class not in DATA_CLASSES:
            raise EngineError("Datenklasse muss oeffentlich, intern oder vertraulich sein")
        if data_class == "vertraulich" and change_class == "standard":
            raise EngineError("vertrauliche Daten sind keine Standardänderung")
        scope_id = str(values.get("scope") or "")
        scope = self.scopes.get(scope_id)
        if scope is None:
            raise EngineError("Änderungsbereich (scope) fehlt oder ist nicht freigegeben")
        checked = list(scope.get("paths", []))
        if self.sandbox is not None and checked:
            try:
                size = sum(len(text or "") for text in self.sandbox.originals(self.sandbox.base_commit(), checked).values())
            except SandboxError as exc:
                raise EngineError(f"Änderungsbereich nicht lesbar: {exc}") from None
            limit = self._scope_limit(scope, str(values.get("execution") or "automatisch"), data_class)
            if size > limit:
                raise EngineError("Änderungsbereich ist zu groß für die lokalen Modelle; bitte einen kleineren "
                                  "Bereich wählen oder die Umsetzung durch Codex/Claude zulassen")
        execution = str(values.get("execution") or "automatisch")
        if execution not in {"automatisch", "lokal", "abo"}:
            raise EngineError("Umsetzung muss automatisch, lokal oder abo sein")
        if execution == "abo" and data_class == "vertraulich":
            raise EngineError("vertrauliche Daten werden nur lokal verarbeitet")
        project = str(values.get("project") or "FLOW-PLATFORM")
        if not re.fullmatch(r"[A-Z][A-Z0-9-]{2,30}", project):
            raise EngineError("Projektkürzel ungültig")
        return {
            "title": text("title", 5, 160),
            "goal": text("goal", 10, 2000),
            "user_group": text("user_group", 2, 160),
            "behavior": text("behavior", 10, 3000),
            "exclusions": text("exclusions", 0, 1500, required=False),
            "success_example": text("success_example", 5, 1500),
            "data_class": data_class,
            "change_class": change_class,
            "scope": scope_id,
            "scope_label": str(scope.get("label", scope_id)),
            "paths": sorted(set(checked)),
            "project": project,
            "execution": execution,
            "owner": _person(user)["name"],
        }

    # =================================================================================
    # Ein Arbeitsschritt
    # =================================================================================
    def recover(self) -> None:
        """Nach Neustart: unterbrochene Schritte markieren; idempotente Schritte laufen erneut."""
        for step in self.store.running_steps():
            self.store.finish_step(step["id"], "unterbrochen", error="Dienst wurde während des Schritts beendet")
            self.store.event(step["run_id"], "wiederanlauf", "orchestrator", step["role"] or step["step_id"],
                             f"Schritt {step['step_id']} nach Neustart erneut eingeplant")

    def cycle(self) -> bool:
        """Bearbeitet höchstens einen Schritt. Liefert True, wenn Arbeit erledigt wurde."""
        if self.store.control("global", "bereit") != "bereit":
            return False
        with self.lock:
            run = self.store.next_active()
            if run is None:
                return False
            if run["registry_digest"] != self.registry.digest:
                self._block(run, "Agentenregister oder Ablauf wurden geändert; Lauf neu bewerten",
                            "blockade", step_id=self._step(run).id if run["step_index"] < len(self.registry.steps) else "")
                return True
            if run["step_index"] >= len(self.registry.steps):
                self.store.update_run(run["id"], status="abgeschlossen")
                return True
            step = self._step(run)
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

    # -- Agentenschritt ------------------------------------------------------------------
    def _agent_step(self, run: dict[str, Any], step: Step) -> None:
        agent = self.registry.agent(step.role or "")
        if not agent.active():
            self._block(run, f"{agent.name} ist im Register nicht aktiv oder die Freigabe ist abgelaufen",
                        "blockade", step_id=step.id)
            return
        if self.store.control(f"agent:{agent.role}") == "pausiert":
            self.store.update_run(run["id"], status="pausiert", reason=f"{agent.name} ist pausiert")
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
                handoff = validate(extract_json(reply.text), role=agent.role, kind=step.kind,
                                   limit=_limit(agent))
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
        esc = self.escalation
        target = (esc.get("roles") or {}).get(agent.role)
        if not esc.get("enabled") or not target or target not in self.providers:
            return local, ""
        auftrag = run["auftrag"]
        if auftrag.get("data_class") == "vertraulich" or auftrag.get("execution") == "lokal":
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
        self.store.update_run(run["id"], model_calls=calls, output_tokens=tokens)
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
            self.store.update_run(run["id"], status="wartet", reason=f"Frage an {decider}")
            self.store.open_decision(
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
                    self.store.update_run(run["id"], status="wartet", reason="Korrekturlimit erreicht")
                    self.store.open_decision(
                        run["id"], step.id, "korrekturlimit", "tech-lead",
                        f"{self.registry.max_correction_rounds} Korrekturrunden ohne Erfolg",
                        "Befunde bestehen weiter. Weitere Runde zulassen oder Lauf abbrechen?",
                        {"findings": handoff.blocking_findings(), "back_to": back_to}, actor=agent.role,
                    )
                    return
                self._set_corrections(run, counts=counts, pending={back_to: handoff.blocking_findings()})
                target = self.registry.step_index(back_to)
                creator = self.registry.steps[target].role or back_to
                self.store.update_run(run["id"], step_index=target, reason="")
                self.store.event(run["id"], "ruecklauf", agent.role, creator,
                                 f"{agent.name} gibt {len(handoff.blocking_findings())} Befund(e) zurück",
                                 {"round": counts[step.id]})
                return
            decider = step.on_rework.get("decision", "tech-lead")
            self.store.update_run(run["id"], status="wartet", reason=f"Eskalation an {decider}")
            self.store.open_decision(
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
        pending = (run["corrections"].get("pending") or {}).get(step.id)
        if pending:
            context["findings_to_fix"] = pending
        if agent.role == "entwicklung":
            paths = list(run["auftrag"].get("paths") or [])
            context["allowed_paths"] = paths
            if self.sandbox is not None and paths:
                base = self.sandbox.base_commit()
                context["base_commit"] = base
                context["files"] = self.sandbox.originals(base, paths)
                # ~20k Token Eingabe plus 16k Token Ausgabe passen in das 40k-Kontextfenster der lokalen Modelle.
                if sum(len(text or "") for text in context["files"].values()) > 70_000:
                    raise SandboxError("freigegebene Dateien sind zu groß für den Modellkontext")
        return context

    def _render(self, run: dict[str, Any], step: Step, agent: Agent, context: dict[str, Any]) -> str:
        data = json.dumps(context, ensure_ascii=False, indent=1)
        if len(data) > 110_000:
            data = data[:110_000] + "\n… (gekürzt)"
        lines = [
            f"Lauf: {run['id']} · Auftrag: {run['auftrag_id']} · Schritt: {step.id} ({step.label})",
            f"Rolle: {agent.id} {agent.name} · Stufe {agent.autonomy} · Klasse: {run['change_class']}",
        ]
        if agent.role == "entwicklung":
            lines.append("Freigegebene Pfade: " + (", ".join(context.get("allowed_paths") or []) or "keine"))
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
            refs = self.sandbox.apply(run["id"], base, paths, changes)
            refs["diff"] = _diff(originals, changes)[:100_000]
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
            except SandboxError as exc:
                passed, summary, seconds, command = False, str(exc), 0.0, ""
        with self.lock:
            content = {"passed": passed, "digest": implementation["refs"].get("digest"),
                       "implementation_version": implementation["version"], "summary": summary,
                       "seconds": round(seconds, 1), "command": command}
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
                self.store.update_run(run["id"], status="wartet", reason="Korrekturlimit erreicht")
                self.store.open_decision(run["id"], step.id, "korrekturlimit", "tech-lead",
                                         "Integrationsprüfung wiederholt rot",
                                         "Weitere Runde zulassen oder Lauf abbrechen?",
                                         {"findings": finding, "back_to": back_to}, actor="integration")
                return
            self._set_corrections(run, counts=counts, pending={back_to: finding})
            self.store.update_run(run["id"], step_index=self.registry.step_index(back_to))
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
            self.store.update_run(run["id"], status="wartet", reason=f"{step.id} wartet auf {step.decider}")
            self.store.open_decision(run["id"], step.id, step.id, step.decider or "tech-lead",
                                     f"{step.id} · {step.label}", self._gate_question(run, step),
                                     context, digest, actor=step.id)
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
        if step.id in {"G4", "G5"}:
            problems += self.verify_manifest(run["id"])
        return problems

    def verify_manifest(self, run_id: str) -> list[str]:
        """Der Orchestrator prüft das Nachweispaket selbst (Teil 07, Test 30)."""
        gaps = []
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
            "G1": "Anforderungen fachlich freigeben? Die Arbeitsbaseline ist fixiert und unabhängig geprüft.",
            "G2": "Architektur und Sicherheitsbewertung bestätigen?",
            "G3": "Integrationsstand (Code, Prüfungen, Codeprüfung am selben Digest) bestätigen?",
            "G4": "Fachabnahme: Erfüllt der Kandidat den Auftrag? Die Abnahme gilt nur für den genannten Digest.",
            "G5": "Produktionsfreigabe protokollieren? Die Auslieferung erfolgt außerhalb des Agentennetzes.",
        }
        return texts.get(step.id, step.label)

    def _gate_context(self, run: dict[str, Any], step: Step) -> dict[str, Any]:
        summaries = {}
        for kind in (*step.requires, "baseline", "geschaeftsbewertung", "prozessbewertung"):
            item = self.store.latest_artifact(run["id"], kind)
            if item:
                summaries[kind] = {"version": item["version"], "digest": item["digest"],
                                   "summary": item["content"].get("summary", "")}
        return {"artifacts": summaries, "change_class": run["change_class"]}

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
            if run["status"] not in {"wartet", "blockiert"}:
                raise EngineError("Lauf wartet nicht auf diese Entscheidung")
            step = self.registry.steps[run["step_index"]]
            gate = decision["gate"]
            if decision["digest"] and gate in {"G3", "G4", "G5"}:
                bound = self.store.latest_artifact(run["id"], step.bind_digest or "implementierung") or {}
                if bound.get("refs", {}).get("digest") != decision["digest"]:
                    self.store.close_decision(decision_id, "verfallen", "", _person(user), "Digest geändert")
                    self.store.update_run(run["id"], status="aktiv", reason="")
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
            self._apply_decision(run, step, decision, outcome, comment, person)
            return self.store.decision(decision_id)

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
        if gate in {"G1", "G2", "G3", "G4", "G5"}:
            if accepted:
                if gate == "G5":
                    self.store.update_run(run["id"], status="abgeschlossen", step_index=len(self.registry.steps),
                                          reason="Produktionsfreigabe protokolliert; Auslieferung manuell")
                    self.store.event(run["id"], "abschluss", "release", "release", "Lauf abgeschlossen")
                    return
                self.store.update_run(run["id"], status="aktiv", reason="")
                self._advance(run, step, f"{gate} durch {person['name']} bestätigt")
                return
            if gate == "G5":
                self.store.update_run(run["id"], status="abgelehnt", reason=f"Produktion abgelehnt: {comment}")
                return
            back_to = GATE_BACK_TO[gate]
            finding = [{"severity": "hoch", "location": gate, "impact": comment,
                        "recommendation": f"Rückmeldung von {person['name']} umsetzen"}]
            self._set_corrections(run, pending={back_to: finding})
            self.store.update_run(run["id"], status="aktiv", step_index=self.registry.step_index(back_to), reason="")
            self.store.event(run["id"], "ruecklauf", f"mensch:{decision['decider']}", self.registry.steps[
                self.registry.step_index(back_to)].role or back_to, f"{gate} abgelehnt: {comment[:120]}")
            return
        if not accepted:
            self.store.update_run(run["id"], status="abgebrochen", reason=f"{decision['title']}: abgelehnt – {comment}")
            self.store.event(run["id"], "abbruch", f"mensch:{decision['decider']}", "orchestrator", "Lauf abgebrochen")
            return
        if gate == "eskalation":
            self.store.update_run(run["id"], status="aktiv", reason="")
            self._advance(run, step, f"Fortsetzung trotz Bedenken durch {person['name']}")
        elif gate == "korrekturlimit":
            counts = dict(run["corrections"].get("counts", {}))
            counts[decision["step_id"]] = 0
            back_to = decision["context"].get("back_to") or step.id
            self._set_corrections(run, counts=counts, pending={back_to: decision["context"].get("findings", [])})
            self.store.update_run(run["id"], status="aktiv", step_index=self.registry.step_index(back_to), reason="")
        else:  # frage, blockade: denselben Schritt mit der Antwort erneut ausführen
            if gate == "blockade" and run["reason"].startswith("Laufbudget"):
                current = self.store.run(run["id"])["corrections"]
                bonus = current.get("budget_bonus", {})
                current["budget_bonus"] = {"max_model_calls": int(bonus.get("max_model_calls", 0)) + 20,
                                           "max_output_tokens": int(bonus.get("max_output_tokens", 0)) + 60000}
                self.store.update_run(run["id"], corrections=current)
                self.store.event(run["id"], "steuerung", f"mensch:{decision['decider']}", "orchestrator",
                                 f"Laufbudget um 20 Modellaufrufe erhöht durch {person['name']}")
            if gate == "blockade" and run["registry_digest"] != self.registry.digest:
                # Ein Mensch stellt den Lauf bewusst auf den aktuellen Regelstand um.
                self.store.update_run(run["id"], registry_digest=self.registry.digest)
                self.store.event(run["id"], "steuerung", f"mensch:{decision['decider']}", "orchestrator",
                                 f"Lauf auf Registerstand {self.registry.digest[:12]} umgestellt durch {person['name']}")
            self.store.update_run(run["id"], status="aktiv", reason="")

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
        if not roles & {"platform-admin", "it-user", "work-admin"}:
            raise EngineError("Steuerung nur für Plattformbetrieb")
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
                            self.store.update_run(item["id"], status="aktiv", reason="")
            elif action == "cancel" and run_id:
                run = self.store.run(run_id)
                if run["status"] not in OPEN_RUN_STATES:
                    raise EngineError("Lauf ist bereits beendet")
                self.store.update_run(run_id, status="abgebrochen", reason=f"durch {actor} abgebrochen")
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
        index = self.registry.step_index(step.id) + 1
        if index >= len(self.registry.steps):
            self.store.update_run(run["id"], status="abgeschlossen", step_index=index, reason="")
            return
        following = self.registry.steps[index]
        self.store.update_run(run["id"], step_index=index, status="aktiv", reason="")
        source = step.role or ("integration" if step.kind == "check" else step.id)
        target = following.role or ("integration" if following.kind == "check" else following.id)
        self.store.event(run["id"], "uebergabe", source, target, f"{message} → {following.label}",
                         {"from_step": step.id, "to_step": following.id})

    def _block(self, run: dict[str, Any], reason: str, gate: str, *, step_id: str) -> None:
        step = next((s for s in self.registry.steps if s.id == step_id), None)
        actor = (step.role or ("integration" if step.kind == "check" else step.id)) if step else "orchestrator"
        self.store.update_run(run["id"], status="blockiert", reason=reason[:500])
        self.store.open_decision(run["id"], step_id, gate, "tech-lead", "Lauf blockiert", reason[:1500],
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
        self.store.update_run(run["id"], corrections=current)

    def _clear_pending(self, run: dict[str, Any], step_id: str) -> None:
        current = self.store.run(run["id"])["corrections"]
        if step_id in current.get("pending", {}):
            current["pending"].pop(step_id)
            self.store.update_run(run["id"], corrections=current)

    # =================================================================================
    # Sicht für FLOWPORTAL
    # =================================================================================
    def overview(self) -> dict[str, Any]:
        runs = self.store.runs(limit=30)
        open_decisions = self.store.decisions(status="offen")
        running = {(step["run_id"], step["role"]) for step in self.store.running_steps()}
        controls = self.store.controls()
        events = self.store.events(limit=60)
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
            agents.append({**agent.public(), "state": state, "current": current,
                           "last": {"message": last["message"], "at": last["at"]} if last else None})
        edges: Counter[tuple[str, str, str]] = Counter()
        last_seen: dict[tuple[str, str, str], str] = {}
        for event in self.store.events(limit=400):
            if event["kind"] in {"uebergabe", "ruecklauf", "entscheidung", "entscheidung_offen", "werkzeug"}:
                key = (event["actor"], event["target"], event["kind"])
                edges[key] += 1
                last_seen[key] = event["at"]
        steps = self.registry.steps
        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
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
            "pipeline": [{"id": s.id, "label": s.label, "kind": s.kind, "role": s.role, "decider": s.decider}
                         for s in steps],
            "runs": [self._run_summary(run, open_decisions) for run in runs],
            "decisions": [self._decision_summary(d, {r["id"]: r for r in runs}) for d in open_decisions],
            "events": events[-40:],
            "interactions": [
                {"from": a, "to": b, "kind": kind, "count": count, "last_at": last_seen[(a, b, kind)]}
                for (a, b, kind), count in edges.most_common(60)
            ],
            "usage": {"totals": self.store.usage_totals(), "by_run": self.store.usage_by_run()},
            "metrics": {
                "runs_open": sum(1 for r in runs if r["status"] in OPEN_RUN_STATES),
                "runs_done": sum(1 for r in runs if r["status"] == "abgeschlossen"),
                "decisions_open": len(open_decisions),
                "agents_working": sum(1 for a in agents if a["state"] == "arbeitet"),
                "reworks": sum(1 for e in events if e["kind"] == "ruecklauf"),
            },
        }

    def _run_summary(self, run: dict[str, Any], open_decisions: list[dict[str, Any]]) -> dict[str, Any]:
        steps = self.registry.steps
        index = min(run["step_index"], len(steps))
        current = steps[index] if index < len(steps) else None
        waiting = next((d for d in open_decisions if d["run_id"] == run["id"]), None)
        return {
            "id": run["id"], "auftrag_id": run["auftrag_id"], "title": run["title"],
            "change_class": run["change_class"], "status": run["status"], "reason": run["reason"],
            "step": current.id if current else "fertig", "step_label": current.label if current else "Abgeschlossen",
            "role": current.role if current else None, "progress": round(index / len(steps) * 100),
            "requested_by": run["requested_by"].get("name"), "updated_at": run["updated_at"],
            "created_at": run["created_at"], "model_calls": run["model_calls"],
            "waiting_for": waiting["decider"] if waiting else None,
            "preview_url": (waiting or {}).get("context", {}).get("preview_url"),
            "branch": ((self.store.latest_artifact(run["id"], "uebernahme") or {}).get("content") or {}).get("branch"),
        }

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
            }
        return summary

    GATE_FOCUS = {
        "G1": ["anforderungen", "baseline", "anforderungsbefund"],
        "G2": ["architektur", "sicherheitsbefund"],
        "G3": ["implementierung", "integration", "codebefund"],
        "G4": ["implementierung", "dokumentation", "prozessbewertung", "nachweise"],
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

    def run_detail(self, run_id: str) -> dict[str, Any]:
        run = self.store.run(run_id)
        return {
            "run": run,
            "summary": self._run_summary(run, self.store.decisions(status="offen")),
            "steps": self.store.steps(run_id),
            "artifacts": [{k: a[k] for k in ("kind", "version", "role", "step_id", "digest", "content", "created_at")}
                          | {"refs": {k: v for k, v in a["refs"].items() if k != "workspace"}}
                          for a in self.store.artifacts(run_id)],
            "decisions": self.store.decisions(run_id=run_id),
            "events": self.store.events(run_id=run_id, limit=300),
            "manifest_gaps": self.verify_manifest(run_id),
        }


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
    return (f'Ergebnisvertrag: jedes Artefakt hat "type": "{artifact_type}" und die Pflichtfelder {fields}{extra}. '
            f"Keine weiteren Felder. status: {status}.")


def _limit(agent: Agent) -> int | None:
    for key in ("max_drafts_per_run", "max_tasks_per_run", "max_tests_per_run", "max_changed_files"):
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
