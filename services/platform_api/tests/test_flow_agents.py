"""RM-Adapter in FLOWWORK und Agentenzentrale (REQ-AGT-010, REQ-AGT-011, REQ-REQ-001 bis -004).

Testnummern verweisen auf den Abnahmeplan, KI-Entwicklungskonzept Teil 10.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import jwt
import pytest
from app import main as main_module
from app.agent_policy import DEMO_RM_SECRET
from app.agents_bff import AgentsGateway
from app.main import app, store
from fastapi.testclient import TestClient

client = TestClient(app)
RUN = "RUN-20261122-ABC123"
AGENT_IDS = {"anforderungen": "AG-ENG-01", "anforderungspruefung": "AG-ENG-02", "entwicklung": "AG-ENG-06",
             "akzeptanztest": "AG-ENG-07", "planung": "AG-ENG-05", "schwachstellen": "AG-ENG-11",
             "orchestrator": "FLOW-ORCHESTRATOR"}


def setup_function() -> None:
    store.reset()


def token(role: str, *, audience: str = "flowwork-rm", ttl: int = 120, secret: str = DEMO_RM_SECRET,
          agent_id: str | None = None, run: str = RUN) -> str:
    now = int(time.time())
    claims = {"iss": "flow-agents", "aud": audience, "sub": agent_id or AGENT_IDS[role], "role": role, "run": run,
              "iat": now, "exp": now + ttl, "jti": f"t{now}{role}"}
    return jwt.encode(claims, secret, algorithm="HS256")


def rm(path: str, role: str | None, payload: dict[str, Any], **token_args: Any):  # noqa: ANN201
    headers = {"Authorization": f"Bearer {token(role, **token_args)}"} if role else {}
    return client.post(f"/api/rm/v1/{path}", json=payload, headers=headers)


def draft_payload(key: str = "RUN-20261122-ABC123:R1", title: str = "Sortierung nach Titel") -> dict[str, Any]:
    return {"idempotency_key": key, "project": "FLOW-DMS", "auftrag_id": "A-017", "key": "R1",
            "values": {"title": title, "text": "Die Ansicht muss nach Titel sortieren.", "priority": "Muss",
                       "acceptance_criteria": ["AC-1: Alpha vor Beta"], "source": "A-017",
                       "negative_case": "Entwürfe bleiben unsichtbar"}}


def requirement(requirement_id: str) -> dict[str, Any]:
    return next(r for r in store.get()["work"]["requirements"] if r["id"] == requirement_id)


def test_requirements_agent_creates_versioned_draft_in_flowwork() -> None:
    response = rm("drafts", "anforderungen", draft_payload())
    assert response.status_code == 200, response.text
    created = response.json()
    assert created == {"id": "REQ-DMS-001", "version": 1, "status": "draft"}
    item = requirement("REQ-DMS-001")
    assert item["project"] == "FLOW-DMS" and item["created_by"]["run"] == RUN and item["priority"] == "Must"
    dashboard = client.get("/api/work/dashboard").json()
    assert any(r["id"] == "REQ-DMS-001" for r in dashboard["requirements"])


def test_02_developer_cannot_create_requirement_drafts() -> None:
    response = rm("drafts", "entwicklung", draft_payload())
    assert response.status_code == 403
    assert not any(r.get("project") == "FLOW-DMS" for r in store.get()["work"]["requirements"])
    audit = store.get()["work"]["rm_audit"][-1]
    assert audit["decision"] == "abgelehnt" and audit["role"] == "entwicklung"
    assert "values" not in audit and "Sortierung" not in str(audit)


def test_04_missing_or_expired_token_is_rejected() -> None:
    assert rm("drafts", None, draft_payload()).status_code == 401
    assert rm("drafts", "anforderungen", draft_payload(), ttl=-10).status_code == 401
    assert rm("drafts", "anforderungen", draft_payload(), ttl=3600).status_code == 401
    assert rm("drafts", "anforderungen", draft_payload(), secret="x" * 40).status_code == 401
    assert rm("drafts", "anforderungen", draft_payload(), run="kein-lauf").status_code == 401


def test_05_token_for_another_audience_is_rejected() -> None:
    assert rm("drafts", "anforderungen", draft_payload(), audience="flow-agents-api").status_code == 401


def test_agent_id_must_match_role_and_inactive_roles_are_locked() -> None:
    assert rm("drafts", "anforderungen", draft_payload(), agent_id="AG-ENG-06").status_code == 403
    assert rm("search", "schwachstellen", {"project": "FLOW-DMS"}).status_code == 403


def test_09_agents_cannot_approve_requirements() -> None:
    created = rm("drafts", "anforderungen", draft_payload()).json()
    payload = {"id": created["id"], "expected_version": 1,
               "values": {**draft_payload()["values"], "status": "approved"}}
    assert rm("drafts/update", "anforderungen", payload).status_code == 422
    patched = client.patch(f"/api/work/requirements/{created['id']}", json={"status": "approved"},
                           headers={"Authorization": f"Bearer {token('anforderungen')}"})
    assert patched.status_code == 403
    assert requirement(created["id"])["status"] == "draft"


def test_26_create_draft_is_idempotent_and_detects_conflicting_payloads() -> None:
    first = rm("drafts", "anforderungen", draft_payload()).json()
    again = rm("drafts", "anforderungen", draft_payload()).json()
    assert first == again
    assert sum(1 for r in store.get()["work"]["requirements"] if r.get("project") == "FLOW-DMS") == 1
    conflict = rm("drafts", "anforderungen", draft_payload(title="Anderer Titel"))
    assert conflict.status_code == 409


def test_27_concurrent_updates_against_same_version_conflict() -> None:
    created = rm("drafts", "anforderungen", draft_payload()).json()
    update = {"id": created["id"], "expected_version": 1, "values": {**draft_payload()["values"], "title": "Neu"}}
    assert rm("drafts/update", "anforderungen", update).json()["version"] == 2
    second = rm("drafts/update", "anforderungen", {**update, "values": {**update["values"], "title": "Parallel"}})
    assert second.status_code == 409
    assert second.json()["detail"]["current"]["version"] == 2
    assert requirement(created["id"])["title"] == "Neu"


def test_comments_bind_to_current_version_only() -> None:
    created = rm("drafts", "anforderungen", draft_payload()).json()
    ok = rm("comments", "anforderungspruefung", {"id": created["id"], "version": 1, "text": "[mittel] Negativfall"})
    assert ok.status_code == 200
    stale = rm("comments", "anforderungspruefung", {"id": created["id"], "version": 7, "text": "alt"})
    assert stale.status_code == 409
    assert rm("comments", "anforderungen", {"id": created["id"], "version": 1, "text": "x"}).status_code == 403


def test_baseline_freeze_is_reserved_for_orchestrator_and_checks_versions() -> None:
    created = rm("drafts", "anforderungen", draft_payload()).json()
    payload = {"idempotency_key": f"{RUN}:BL:1", "project": "FLOW-DMS", "auftrag_id": "A-017",
               "name": "Arbeitsbaseline A-017 v1", "items": [{"id": created["id"], "version": 1}]}
    assert rm("baselines", "anforderungen", payload).status_code == 403
    frozen = rm("baselines", "orchestrator", payload)
    assert frozen.status_code == 200 and frozen.json()["id"] == "BL-DMS-001"
    baseline = next(b for b in store.get()["work"]["baselines"] if b["id"] == "BL-DMS-001")
    assert baseline["approval"] == "Arbeitsbaseline fixiert" and baseline["status"] == "frozen"
    stale = {**payload, "idempotency_key": f"{RUN}:BL:2", "items": [{"id": created["id"], "version": 5}]}
    assert rm("baselines", "orchestrator", stale).status_code == 409
    assert rm("baselines", "orchestrator", payload, agent_id="AG-ENG-01").status_code == 403


def test_acceptance_tests_are_linked_within_the_same_project() -> None:
    created = rm("drafts", "anforderungen", draft_payload()).json()
    test = rm("tests", "akzeptanztest", {"idempotency_key": f"{RUN}:AT-1:1", "project": "FLOW-DMS", "key": "AT-1",
                                         "title": "Alpha vor Beta", "criterion": "R1/AC-1",
                                         "steps": [{"action": "Sortieren", "expected": "Alpha zuerst"}]})
    assert test.status_code == 200, test.text
    link = rm("links", "akzeptanztest", {"requirement_id": created["id"], "item_id": test.json()["id"],
                                         "relationship": "verifies"})
    assert link.status_code == 200, link.text
    relation = store.get()["work"]["relationships"][-1]
    assert relation["source_id"] == created["id"] and relation["relationship_type"] == "verifies"
    foreign = rm("links", "akzeptanztest", {"requirement_id": "REQ-SCU-001", "item_id": test.json()["id"],
                                            "relationship": "verifies"})
    assert foreign.status_code == 403
    wrong_type = rm("links", "akzeptanztest", {"requirement_id": created["id"], "item_id": test.json()["id"],
                                               "relationship": "implements"})
    assert wrong_type.status_code == 403


def test_registry_missing_locks_all_agent_operations(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENT_REGISTRY_DIR", str(tmp_path))
    assert rm("drafts", "anforderungen", draft_payload()).status_code == 503


# -- Agentenzentrale (BFF) -------------------------------------------------------------------
def test_overview_falls_back_to_registry_when_orchestrator_is_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main_module.agents_gateway, "base_url", "http://127.0.0.1:9")
    response = client.get("/api/agents/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False and "nicht erreichbar" in data["reason"]
    assert len(data["agents"]) == 12 and data["runs"] == []
    assert data["viewer"]["username"] == "demo-admin"


def test_agent_actions_forward_the_signed_in_person(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, Any, Any]] = []

    def fake(method: str, path: str, payload: Any = None, user: Any = None) -> dict[str, Any]:
        calls.append((method, path, payload, user))
        return {"id": "RUN-20261122-ABC123"} if path == "/v1/runs" else {"ok": True}

    monkeypatch.setattr(main_module.agents_gateway, "request", fake)
    body = {"idempotency_key": "portal-0001-abc", "title": "Sortierung nach Titel",
            "goal": "Einkauf findet Verfahrensanweisungen schneller", "user_group": "Einkauf",
            "behavior": "Die Liste sortiert sichtbare Dokumente nach Titel", "success_example": "Alpha vor Beta",
            "change_class": "standard", "scope": "dms-ui", "project": "FLOW-DMS"}
    assert client.post("/api/agents/runs", json=body).status_code == 201
    method, path, payload, user = calls[-1]
    assert (method, path) == ("POST", "/v1/runs") and payload["idempotency_key"] == "portal-0001-abc"
    assert "idempotency_key" not in payload["auftrag"] and user["username"] == "demo-admin"
    assert client.post("/api/agents/decisions/ENT-1A2B3C4D", json={"outcome": "annehmen"}).status_code == 200
    assert calls[-1][1] == "/v1/decisions/ENT-1A2B3C4D" and calls[-1][2]["outcome"] == "annehmen"
    assert client.post("/api/agents/decisions/../../x", json={"outcome": "annehmen"}).status_code in {404, 405}
    assert client.post("/api/agents/runs", json={**body, "change_class": "alles"}).status_code == 422


def test_bff_tokens_are_short_lived_and_carry_the_person() -> None:
    gateway = AgentsGateway("http://127.0.0.1:9", "s" * 40)
    claims = jwt.decode(gateway._token({"username": "demo45", "name": "H", "roles": ["requirements-user"]}),
                        "s" * 40, algorithms=["HS256"], audience="flow-agents-api")
    assert claims["iss"] == "flow-platform-api" and claims["exp"] - claims["iat"] == 60
    assert claims["user"] == {"username": "demo45", "name": "H", "roles": ["requirements-user"]}


def test_agents_page_and_dms_page_are_served() -> None:
    agents = client.get("/agents")
    assert agents.status_code == 200 and "Agentenzentrale" in agents.text
    assert agents.headers["cache-control"] == "no-store"
    dms = client.get("/dms")
    assert dms.status_code == 200 and "FLOWDOC" in dms.text
    portal = client.get("/")
    assert 'id="agent-center"' in portal.text
