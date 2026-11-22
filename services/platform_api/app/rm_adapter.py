"""RM-Adapter für FLOWWORK: begrenzte Fachoperationen für Agentenrollen (KI-Entwicklungskonzept Teil 08).

- Jede Operation prüft Token, Rolle und Werkzeug gegen das Agentenregister (``agent_policy``).
- Anlagen sind idempotent: gleicher Schlüssel und gleiche Nutzlast liefern dasselbe Objekt,
  gleicher Schlüssel mit anderer Nutzlast erzeugt einen Konflikt (Test 26).
- Änderungen an Entwürfen brauchen ``expected_version`` (Test 27).
- Es gibt keine Freigabeoperation: Freigaben entstehen nur durch Menschen in FLOWPORTAL (Test 09).
- Das Audit enthält Ereignis, Rolle, Lauf, Operation, Objekt und Entscheidung, keine Inhalte.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any

from .agent_policy import (
    AgentIdentity,
    AgentPolicy,
    PolicyError,
    registry_directory,
    verify_agent_token,
)
from .store import ScenarioStore, utc_now
from .work import WorkError, WorkService

PRIORITIES = {"Muss": "Must", "Soll": "Should", "Kann": "Could"}
DRAFT_FIELDS = {"title", "text", "priority", "rationale", "negative_case", "acceptance_criteria", "source"}
PROJECT = re.compile(r"[A-Z][A-Z0-9-]{2,30}")
MAX_AUDIT = 2000


class RMConflict(RuntimeError):
    def __init__(self, message: str, current: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.current = current or {}


class RMNotFound(LookupError):
    pass


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _prefix(project: str) -> str:
    if not PROJECT.fullmatch(project):
        raise ValueError("Projektkürzel ungültig")
    return project.split("-")[-1][:8]


def _text(value: Any, name: str, limit: int, *, required: bool = True) -> str:
    text = str(value or "").strip()
    if (required and not text) or len(text) > limit or "\0" in text:
        raise ValueError(f"{name}: 1 bis {limit} Zeichen erforderlich")
    return text


class RMAdapter:
    def __init__(self, store: ScenarioStore, work: WorkService) -> None:
        self.store = store
        self.work = work

    # -- Zugang ------------------------------------------------------------------------
    def policy(self) -> AgentPolicy:
        return AgentPolicy.load(registry_directory())

    def handle(self, authorization: str, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        identity: AgentIdentity | None = None
        try:
            identity = verify_agent_token(authorization)
            self.policy().authorize(identity, operation)
            handler = {
                "rm.create_draft": self._create_draft,
                "rm.update_draft": self._update_draft,
                "rm.comment": self._comment,
                "rm.ask_owner": self._ask_owner,
                "rm.create_test": self._create_test,
                "rm.link_trace": self._link_trace,
                "rm.freeze_baseline": self._freeze_baseline,
                "rm.search": self._search,
                "ticket.create": self._create_task,
            }[operation]
            result = handler(identity, payload)
        except (PolicyError, RMConflict, RMNotFound, ValueError, WorkError) as exc:
            self._audit(identity, operation, "", "abgelehnt", type(exc).__name__)
            raise
        self._audit(identity, operation, str(result.get("id", "")), "erlaubt", "")
        return result

    def _audit(self, identity: AgentIdentity | None, operation: str, obj: str, decision: str, reason: str) -> None:
        entry = {
            "at": utc_now(),
            "role": identity.role if identity else "unbekannt",
            "agent": identity.agent_id if identity else "",
            "run": identity.run_id if identity else "",
            "token": identity.token_id if identity else "",
            "operation": operation,
            "object": obj,
            "decision": decision,
            "reason": reason,
        }

        def append(state: dict[str, Any]) -> None:
            log = state["work"].setdefault("rm_audit", [])
            log.append(entry)
            del log[:-MAX_AUDIT]

        self.store.mutate(append)

    def audit(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(reversed(self.store.get()["work"].get("rm_audit", [])[-limit:]))

    # -- Hilfen ------------------------------------------------------------------------
    @staticmethod
    def _idempotent(work: dict[str, Any], key: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{8,120}", key or ""):
            raise ValueError("idempotency_key fehlt oder ist ungültig")
        known = work.setdefault("rm_idempotency", {}).get(key)
        if known is None:
            return None
        if known["digest"] != _digest(payload):
            raise RMConflict("Gleicher Idempotenzschlüssel mit abweichender Nutzlast", {"id": known["id"]})
        return known["result"]

    @staticmethod
    def _remember(work: dict[str, Any], key: str, payload: dict[str, Any], result: dict[str, Any]) -> None:
        work.setdefault("rm_idempotency", {})[key] = {"digest": _digest(payload), "id": result["id"], "result": result}

    @staticmethod
    def _next_id(items: list[dict[str, Any]], prefix: str) -> str:
        numbers = [int(match.group(1)) for item in items
                   if (match := re.fullmatch(rf"{re.escape(prefix)}-(\d+)", str(item.get("id", ""))))]
        return f"{prefix}-{max(numbers, default=0) + 1:03d}"

    @staticmethod
    def _creator(identity: AgentIdentity) -> dict[str, str]:
        return {"role": identity.role, "agent": identity.agent_id, "run": identity.run_id}

    def _draft_values(self, values: Any) -> dict[str, Any]:
        if not isinstance(values, dict) or set(values) - DRAFT_FIELDS:
            raise ValueError("Entwurf enthält unzulässige Felder (z. B. Status oder Freigabe)")
        criteria = values.get("acceptance_criteria")
        if not isinstance(criteria, list) or not criteria or len(criteria) > 12:
            raise ValueError("mindestens ein Akzeptanzkriterium erforderlich")
        priority = str(values.get("priority") or "Muss")
        if priority not in PRIORITIES:
            raise ValueError("Priorität muss Muss, Soll oder Kann sein")
        return {
            "title": _text(values.get("title"), "title", 160),
            "text": _text(values.get("text"), "text", 4000),
            "priority": PRIORITIES[priority],
            "rationale": _text(values.get("rationale"), "rationale", 2000, required=False),
            "negative_case": _text(values.get("negative_case"), "negative_case", 2000, required=False),
            "acceptance_criteria": "\n".join(_text(c, "acceptance_criteria", 1000) for c in criteria),
            "source": _text(values.get("source"), "source", 80),
        }

    # -- Operationen ---------------------------------------------------------------------
    def _create_draft(self, identity: AgentIdentity, payload: dict[str, Any]) -> dict[str, Any]:
        project = str(payload.get("project", ""))
        prefix = _prefix(project)
        values = self._draft_values(payload.get("values"))
        key = str(payload.get("idempotency_key", ""))
        result: dict[str, Any] = {}

        def create(state: dict[str, Any]) -> None:
            work = state["work"]
            self.work._ensure_schema(work)
            known = self._idempotent(work, key, payload)
            if known is not None:
                result.update(known)
                return
            requirement_id = self._next_id(work["requirements"], f"REQ-{prefix}")
            now = utc_now()
            requirement = {
                "id": requirement_id, **values, "type": "Software", "owner": "Product Owner",
                "status": "draft", "version": 1, "project": project, "parent_id": None, "issue_id": None,
                "wiki_title": None, "verification": None, "auftrag_id": str(payload.get("auftrag_id", ""))[:40],
                "agent_key": str(payload.get("key", ""))[:20], "created_by": self._creator(identity),
                "created_at": now, "updated_at": now, "comments": [], "custom_fields": {},
                "history": [{"version": 1, "actor": identity.agent_id, "at": now,
                             "note": f"Entwurf durch {identity.agent_id} im Lauf {identity.run_id}"}],
            }
            work["requirements"].append(requirement)
            result.update({"id": requirement_id, "version": 1, "status": "draft"})
            self._remember(work, key, payload, dict(result))
            self.work._add_activity(work, identity.agent_id, f"Anforderungsentwurf {requirement_id} angelegt")

        self.store.mutate(create)
        return result

    def _requirement(self, work: dict[str, Any], requirement_id: str) -> dict[str, Any]:
        item = next((r for r in work["requirements"] if r.get("id") == requirement_id), None)
        if item is None:
            raise RMNotFound(f"{requirement_id} nicht gefunden")
        return item

    def _update_draft(self, identity: AgentIdentity, payload: dict[str, Any]) -> dict[str, Any]:
        values = self._draft_values(payload.get("values"))
        try:
            expected = int(payload["expected_version"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("expected_version ist Pflicht") from None
        result: dict[str, Any] = {}

        def update(state: dict[str, Any]) -> None:
            work = state["work"]
            item = self._requirement(work, str(payload.get("id", "")))
            creator = item.get("created_by") or {}
            if item.get("status") != "draft" or creator.get("role") != identity.role:
                raise PolicyError("Nur eigene Entwürfe im Status draft sind änderbar")
            if int(item.get("version", 0)) != expected:
                raise RMConflict("Versionskonflikt", {"id": item["id"], "version": item.get("version")})
            item.update(values)
            item["version"] = expected + 1
            item["updated_at"] = utc_now()
            item.setdefault("history", []).insert(0, {
                "version": item["version"], "actor": identity.agent_id, "at": item["updated_at"],
                "note": f"Entwurf überarbeitet im Lauf {identity.run_id}"})
            self.work._mark_suspect_links(work, item["id"], identity.agent_id, sorted(values))
            result.update({"id": item["id"], "version": item["version"], "status": item["status"]})

        self.store.mutate(update)
        return result

    def _comment(self, identity: AgentIdentity, payload: dict[str, Any]) -> dict[str, Any]:
        text = _text(payload.get("text"), "text", 2000)
        result: dict[str, Any] = {}

        def comment(state: dict[str, Any]) -> None:
            item = self._requirement(state["work"], str(payload.get("id", "")))
            if int(payload.get("version", -1)) != int(item.get("version", 0)):
                raise RMConflict("Kommentar bezieht sich auf einen veralteten Stand",
                                 {"id": item["id"], "version": item.get("version")})
            entry = {"id": f"KOM-{len(item.setdefault('comments', [])) + 1:03d}", "version": item["version"],
                     "author": identity.agent_id, "role": identity.role, "run": identity.run_id, "text": text,
                     "at": utc_now()}
            item["comments"].append(entry)
            result.update({"id": item["id"], "comment": entry["id"], "version": item["version"]})

        self.store.mutate(comment)
        return result

    def _ask_owner(self, identity: AgentIdentity, payload: dict[str, Any]) -> dict[str, Any]:
        target = str(payload.get("to", ""))
        if target not in {"product-owner", "tech-lead", "geschaeftsfuehrung"}:
            raise ValueError("Fragen gehen nur an berechtigte Fachverantwortliche")
        entry = {"auftrag_id": _text(payload.get("auftrag_id"), "auftrag_id", 40), "to": target,
                 "question": _text(payload.get("question"), "question", 1500),
                 "impact": _text(payload.get("impact"), "impact", 1500, required=False),
                 "asked_by": identity.agent_id, "run": identity.run_id, "at": utc_now()}
        result: dict[str, Any] = {}

        def ask(state: dict[str, Any]) -> None:
            questions = state["work"].setdefault("rm_questions", [])
            entry["id"] = f"FRG-{len(questions) + 1:04d}"
            questions.append(entry)
            result["id"] = entry["id"]

        self.store.mutate(ask)
        return result

    def _create_test(self, identity: AgentIdentity, payload: dict[str, Any]) -> dict[str, Any]:
        prefix = _prefix(str(payload.get("project", "")))
        steps = payload.get("steps")
        if not isinstance(steps, list) or not steps or len(steps) > 20:
            raise ValueError("Testfall braucht 1 bis 20 Schritte")
        clean_steps = [{"order": index, "action": _text(step.get("action"), "action", 500),
                        "expected": _text(step.get("expected"), "expected", 500)}
                       for index, step in enumerate(steps, start=1) if isinstance(step, dict)]
        if len(clean_steps) != len(steps):
            raise ValueError("Testschritte müssen Objekte sein")
        key = str(payload.get("idempotency_key", ""))
        result: dict[str, Any] = {}

        def create(state: dict[str, Any]) -> None:
            work = state["work"]
            self.work._ensure_schema(work)
            known = self._idempotent(work, key, payload)
            if known is not None:
                result.update(known)
                return
            test_id = self._next_id(work["test_cases"], f"TC-{prefix}")
            now = utc_now()
            work["test_cases"].append({
                "id": test_id, "title": _text(payload.get("title"), "title", 200), "type": "TestCase",
                "status": "draft", "owner": "Qualitätssicherung",
                "preconditions": _text(payload.get("preconditions"), "preconditions", 1000, required=False),
                "steps": clean_steps, "expected_result": clean_steps[-1]["expected"], "version": 1,
                "criterion": _text(payload.get("criterion"), "criterion", 80), "negative": bool(payload.get("negative")),
                "project": payload["project"], "created_by": self._creator(identity), "created_at": now,
                "updated_at": now,
            })
            result.update({"id": test_id, "version": 1})
            self._remember(work, key, payload, dict(result))

        self.store.mutate(create)
        return result

    def _link_trace(self, identity: AgentIdentity, payload: dict[str, Any]) -> dict[str, Any]:
        relationship = str(payload.get("relationship", ""))
        allowed = {"akzeptanztest": {"verifies"}, "planung": {"implements", "references"}}.get(identity.role, set())
        if relationship not in allowed:
            raise PolicyError(f"Beziehung {relationship} ist für die Rolle nicht zulässig")
        requirement_id, item_id = str(payload.get("requirement_id", "")), str(payload.get("item_id", ""))
        result: dict[str, Any] = {}

        def link(state: dict[str, Any]) -> None:
            work = state["work"]
            self.work._ensure_schema(work)
            requirement = self._requirement(work, requirement_id)
            item = self.work._find_item(work, item_id)
            if item is None:
                raise RMNotFound(f"{item_id} nicht gefunden")
            if requirement.get("project") != item[2].get("project"):
                raise PolicyError("Beide Endpunkte müssen im selben Projekt liegen")
            self.work._append_relationship(work, requirement_id, item_id, relationship, identity.agent_id)
            result["id"] = work["relationships"][-1]["id"]

        self.store.mutate(link)
        return result

    def _freeze_baseline(self, identity: AgentIdentity, payload: dict[str, Any]) -> dict[str, Any]:
        project = str(payload.get("project", ""))
        prefix = _prefix(project)
        items = payload.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError("Baseline braucht mindestens eine Anforderung")
        key = str(payload.get("idempotency_key", ""))
        result: dict[str, Any] = {}

        def freeze(state: dict[str, Any]) -> None:
            work = state["work"]
            known = self._idempotent(work, key, payload)
            if known is not None:
                result.update(known)
                return
            snapshot = []
            for entry in items:
                requirement = self._requirement(work, str(entry.get("id", "")))
                if int(requirement.get("version", 0)) != int(entry.get("version", -1)):
                    raise RMConflict("Anforderung hat sich seit der Prüfung geändert",
                                     {"id": requirement["id"], "version": requirement.get("version")})
                snapshot.append({"requirement_id": requirement["id"], "version": requirement["version"],
                                 "status": requirement.get("status"),
                                 "checksum_source": f"{requirement['id']}:{requirement['version']}",
                                 "content_digest": _digest({k: requirement.get(k) for k in sorted(DRAFT_FIELDS)})})
            baseline_id = self._next_id(work["baselines"], f"BL-{prefix}")
            work["baselines"].append({
                "id": baseline_id, "name": _text(payload.get("name"), "name", 160),
                "description": f"Arbeitsbaseline fixiert für {payload.get('auftrag_id', '')}",
                "status": "frozen", "approval": "Arbeitsbaseline fixiert", "project": project,
                "created_at": utc_now(), "created_by": "FLOWAGENTS Orchestrator", "run": identity.run_id,
                "items": snapshot, "digest": _digest(snapshot),
            })
            result.update({"id": baseline_id, "status": "frozen", "digest": _digest(snapshot)})
            self._remember(work, key, payload, dict(result))
            self.work._add_activity(work, "FLOWAGENTS", f"Arbeitsbaseline {baseline_id} fixiert")

        self.store.mutate(freeze)
        return result

    def _search(self, identity: AgentIdentity, payload: dict[str, Any]) -> dict[str, Any]:
        project = str(payload.get("project", ""))
        _prefix(project)
        query = str(payload.get("query", "")).casefold()[:200]
        work = self.store.get()["work"]
        hits = [{"id": r["id"], "title": r.get("title"), "version": r.get("version"), "status": r.get("status")}
                for r in work["requirements"] if r.get("project") == project
                and (not query or query in f"{r.get('title', '')} {r.get('text', '')}".casefold())]
        return {"id": "", "count": len(hits), "items": hits[:50]}

    def _create_task(self, identity: AgentIdentity, payload: dict[str, Any]) -> dict[str, Any]:
        key = str(payload.get("idempotency_key", ""))
        subject = _text(payload.get("subject"), "subject", 200)
        state = self.store.get()["work"]
        known = self._idempotent(deepcopy(state), key, payload)
        if known is not None:
            return known
        issue = self.work.create_issue({"subject": subject, "description": "Covers: " + ", ".join(
            str(c)[:40] for c in (payload.get("covers") or [])[:12]), "priority": "Normal"}, identity.agent_id)
        result = {"id": str(issue.get("key") or issue.get("id"))}
        self.store.mutate(lambda s: self._remember(s["work"], key, payload, dict(result)))
        return result
