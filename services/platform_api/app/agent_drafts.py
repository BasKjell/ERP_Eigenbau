"""Fachauftrags-Vorschläge aus FLOWAI (Open WebUI).

FLOWAI darf einen Fachauftrag nur **vorschlagen** (Stufe A1). Der Vorschlag erscheint in FLOWPORTAL
unter „Zu prüfen“; eingereicht wird er erst, wenn eine angemeldete Person ihn prüft und mit ihrer
FLOWID-Identität abschickt. So entsteht keine Änderung ohne menschliche Bestätigung.
"""

from __future__ import annotations

import hmac
import os
import secrets
from typing import Any

from .store import ScenarioStore, utc_now

DEMO_TOKEN = "local-dev-mcp-token-change-before-network-use"
FIELDS = ("title", "goal", "user_group", "behavior", "exclusions", "success_example", "data_class",
          "change_class", "scope", "project")
MAX_OPEN = 50


class DraftError(ValueError):
    pass


def dev_mcp_token() -> str:
    return os.getenv("FLOW_DEV_MCP_TOKEN", "") or DEMO_TOKEN


def verify_internal(authorization: str) -> None:
    expected = f"Bearer {dev_mcp_token()}"
    if not hmac.compare_digest(authorization.encode(), expected.encode()):
        raise PermissionError("Dienst-Token fehlt oder ist ungültig")


class DraftService:
    def __init__(self, store: ScenarioStore) -> None:
        self.store = store

    def create(self, values: dict[str, Any], source: str, note: str = "") -> dict[str, Any]:
        draft = {key: str(values.get(key) or "").strip() for key in FIELDS}
        if len(draft["title"]) < 5 or len(draft["goal"]) < 10 or len(draft["behavior"]) < 10:
            raise DraftError("Titel (≥ 5), Zweck (≥ 10) und Verhalten (≥ 10 Zeichen) sind Pflicht")
        draft["change_class"] = draft["change_class"] or "neue_funktion"
        draft["data_class"] = draft["data_class"] or "intern"
        draft["project"] = draft["project"] or "FLOW-DMS"
        if draft["change_class"] not in {"standard", "neue_funktion", "kritisch"}:
            raise DraftError("Änderungsklasse muss standard, neue_funktion oder kritisch sein")
        if any(len(value) > 3000 for value in draft.values()):
            raise DraftError("Feld zu lang")
        entry = {"id": f"VOR-{secrets.token_hex(3).upper()}", **draft, "status": "offen", "source": source[:80],
                 "note": note.strip()[:1000], "created_at": utc_now()}

        def add(state: dict[str, Any]) -> None:
            drafts = state.setdefault("agent_drafts", [])
            if sum(1 for d in drafts if d["status"] == "offen") >= MAX_OPEN:
                raise DraftError("Zu viele offene Vorschläge")
            drafts.append(entry)

        self.store.mutate(add)
        return entry

    def open(self) -> list[dict[str, Any]]:
        return [d for d in self.store.get().get("agent_drafts", []) if d["status"] == "offen"]

    def get(self, draft_id: str) -> dict[str, Any]:
        draft = next((d for d in self.store.get().get("agent_drafts", []) if d["id"] == draft_id), None)
        if draft is None:
            raise KeyError(draft_id)
        return draft

    def close(self, draft_id: str, status: str, actor: str, run_id: str = "") -> dict[str, Any]:
        result: dict[str, Any] = {}

        def update(state: dict[str, Any]) -> None:
            draft = next((d for d in state.get("agent_drafts", []) if d["id"] == draft_id), None)
            if draft is None:
                raise KeyError(draft_id)
            if draft["status"] != "offen":
                raise DraftError("Vorschlag ist bereits erledigt")
            draft.update({"status": status, "closed_by": actor, "closed_at": utc_now(), "run_id": run_id})
            result.update(draft)

        self.store.mutate(update)
        return result
