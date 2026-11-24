"""RM-Adapter in FLOWWORK und Agentenzentrale (REQ-AGT-010, REQ-AGT-011, REQ-REQ-001 bis -004).

Testnummern verweisen auf den Abnahmeplan, KI-Entwicklungskonzept Teil 10.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import jwt
import pytest
from app import main as main_module
from app.agent_policy import DEMO_RM_SECRET
from app.agents_bff import SYNC_AUDIENCE
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
    other_run = rm("drafts/update", "anforderungen", {**update, "expected_version": 2}, run="RUN-20261122-FFFFFF")
    assert other_run.status_code == 403, "Entwürfe sind an den erzeugenden Lauf gebunden"
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


# -- Agentenzentrale (BFF, Pull-Modell) ------------------------------------------------------
def sync_token(*, audience: str = SYNC_AUDIENCE, ttl: int = 60, secret: str | None = None) -> str:
    now = int(time.time())
    return jwt.encode({"iss": "flow-agents", "aud": audience, "sub": "flow-orchestrator", "iat": now, "exp": now + ttl},
                      secret or main_module.agents_hub.secret, algorithm="HS256")


def publish_state() -> None:
    overview = {"agents": [{"role": "anforderungen", "name": "Anforderungs-Agent", "state": "arbeitet"}],
                "runs": [], "decisions": [], "events": [], "interactions": [], "metrics": {}}
    response = client.post("/api/agents/sync/state", json={"overview": overview, "registry": {"scopes": {"dms-ui": {"label": "DMS"}}}},
                           headers={"Authorization": f"Bearer {sync_token()}"})
    assert response.status_code == 200, response.text


@pytest.fixture()
def fresh_hub(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    hub = main_module.agents_hub
    monkeypatch.setattr(hub, "secret", "t" * 40)
    hub._actions.clear()
    monkeypatch.setattr(hub, "_overview", None)
    monkeypatch.setattr(hub, "_registry", None)
    monkeypatch.setattr(hub, "_seen", 0.0)
    return hub


def test_overview_falls_back_to_registry_when_orchestrator_is_silent(fresh_hub) -> None:  # noqa: ANN001
    data = client.get("/api/agents/overview").json()
    assert data["available"] is False and "meldet sich nicht" in data["reason"]
    assert len(data["agents"]) == 14 and data["runs"] == []
    assert data["viewer"]["username"] == "demo-admin"
    assert client.get("/api/agents/registry").status_code == 503
    rejected = client.post("/api/agents/runs", json={"idempotency_key": "x" * 10})
    assert rejected.status_code == 422


def test_sync_endpoints_require_the_orchestrator_token(fresh_hub) -> None:  # noqa: ANN001
    assert client.get("/api/agents/sync/actions").status_code == 401
    wrong = client.get("/api/agents/sync/actions", headers={"Authorization": f"Bearer {sync_token(audience='flowwork-rm')}"})
    assert wrong.status_code == 401
    forged = client.get("/api/agents/sync/actions", headers={"Authorization": f"Bearer {sync_token(secret='x' * 40)}"})
    assert forged.status_code == 401
    assert client.get("/api/agents/sync/actions", headers={"Authorization": f"Bearer {sync_token(ttl=3600)}"}).status_code == 401
    publish_state()
    overview = client.get("/api/agents/overview").json()
    assert overview["available"] is True and overview["agents"][0]["state"] == "arbeitet"
    assert client.get("/api/agents/registry").json()["scopes"]["dms-ui"]["label"] == "DMS"


def test_portal_actions_are_queued_with_the_person_and_answered_by_the_orchestrator(fresh_hub) -> None:  # noqa: ANN001
    publish_state()
    body = {"idempotency_key": "portal-0001-abc", "title": "Sortierung nach Titel",
            "goal": "Einkauf findet Verfahrensanweisungen schneller", "user_group": "Einkauf",
            "behavior": "Die Liste sortiert sichtbare Dokumente nach Titel", "success_example": "Alpha vor Beta",
            "change_class": "standard", "scope": "dms-ui", "project": "FLOW-DMS"}
    seen: list[dict[str, Any]] = []

    def orchestrator() -> None:
        for _ in range(100):
            actions = client.get("/api/agents/sync/actions", headers={"Authorization": f"Bearer {sync_token()}"}).json()
            if actions:
                seen.extend(actions)
                results = [{"id": a["id"], "status": 201, "body": {"id": "RUN-20261122-ABC123", "auftrag_id": "A-001"}}
                           for a in actions]
                client.post("/api/agents/sync/results", json={"results": results},
                            headers={"Authorization": f"Bearer {sync_token()}"})
                return
            time.sleep(0.05)

    worker = threading.Thread(target=orchestrator)
    worker.start()
    response = client.post("/api/agents/runs", json=body)
    worker.join(5)
    assert response.status_code == 201, response.text
    assert response.json()["auftrag_id"] == "A-001"
    action = seen[0]
    assert action["kind"] == "submit" and action["payload"]["idempotency_key"] == "portal-0001-abc"
    assert "idempotency_key" not in action["payload"]["auftrag"]
    assert action["person"] == {"username": "demo-admin", "name": "Lokale Funktionsdemo", "roles": ["platform-admin"]}


def test_rejections_from_the_orchestrator_reach_the_portal(fresh_hub) -> None:  # noqa: ANN001
    publish_state()

    def orchestrator() -> None:
        for _ in range(100):
            actions = client.get("/api/agents/sync/actions", headers={"Authorization": f"Bearer {sync_token()}"}).json()
            if actions:
                client.post("/api/agents/sync/results", json={"results": [
                    {"id": actions[0]["id"], "status": 403, "body": {"detail": "Keine Befugnis für die Rolle key-user"}}]},
                    headers={"Authorization": f"Bearer {sync_token()}"})
                return
            time.sleep(0.05)

    worker = threading.Thread(target=orchestrator)
    worker.start()
    response = client.post("/api/agents/decisions/ENT-1A2B3C4D", json={"outcome": "annehmen"})
    worker.join(5)
    assert response.status_code == 403 and "Befugnis" in response.json()["detail"]
    assert client.post("/api/agents/decisions/ENT-1A2B3C4D", json={"outcome": "vielleicht"}).status_code == 422


def test_package_start_is_forwarded_as_epi_action(fresh_hub) -> None:  # noqa: ANN001
    publish_state()
    seen: list[dict[str, Any]] = []

    def orchestrator() -> None:
        for _ in range(100):
            actions = client.get("/api/agents/sync/actions", headers={"Authorization": f"Bearer {sync_token()}"}).json()
            if actions:
                seen.extend(actions)
                client.post("/api/agents/sync/results", json={"results": [
                    {"id": actions[0]["id"], "status": 201, "body": {"id": "RUN-20261124-ABC123", "auftrag_id": "A-002"}}]},
                    headers={"Authorization": f"Bearer {sync_token()}"})
                return
            time.sleep(0.05)

    worker = threading.Thread(target=orchestrator)
    worker.start()
    response = client.post("/api/agents/projects/PRJ-001/packages/AP-1/start", json={"scope": "dms-doku"})
    worker.join(5)
    assert response.status_code == 201, response.text
    assert seen[0]["kind"] == "start_package"
    assert seen[0]["payload"] == {"project_id": "PRJ-001", "package_key": "AP-1", "scope": "dms-doku"}
    assert client.post("/api/agents/projects/xyz/packages/AP-1/start", json={}).status_code == 404
    assert client.post("/api/agents/projects/PRJ-001/packages/AP-1/start", json={"scope": "Bad Scope"}).status_code == 422


def test_agents_page_and_dms_page_are_served() -> None:
    agents = client.get("/agents")
    assert agents.status_code == 200 and "Agentenzentrale" in agents.text
    assert agents.headers["cache-control"] == "no-store"
    dms = client.get("/dms")
    assert dms.status_code == 200 and "FLOWDOC" in dms.text
    portal = client.get("/")
    assert 'id="agent-center"' in portal.text


def test_unclaimed_actions_are_withdrawn_after_timeout(fresh_hub) -> None:  # noqa: ANN001
    publish_state()
    with pytest.raises(Exception, match="verworfen"):
        fresh_hub.request("control", {"action": "pause"}, {"username": "demo49", "roles": ["it-user"]}, wait=0.05)
    assert fresh_hub.pending() == []



def test_agent_token_usage_is_exported_as_prometheus_metrics() -> None:
    from app.main import agents_hub

    agents_hub.publish({"runs": [], "usage": {"totals": [
        {"role": "entwicklung", "provider": "gateway", "model": "flow-coder", "calls": 3,
         "input_tokens": 1200, "output_tokens": 340, "seconds": 41.5}]}}, None)
    text = TestClient(app).get("/metrics").text
    assert 'flow_agents_tokens_total{model="flow-coder",provider="gateway",role="entwicklung",type="input"} 1200.0' in text
    assert 'flow_agents_model_calls_total{model="flow-coder",provider="gateway",role="entwicklung"} 3.0' in text
    assert "flow_agents_orchestrator_connected 1.0" in text
