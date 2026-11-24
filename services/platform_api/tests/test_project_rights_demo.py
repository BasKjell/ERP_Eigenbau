"""Projektrechte in der Agentenzentrale und Benutzerwechsel in der Demo (agents/projects.json).

Die Plattform blendet Aufträge, Entscheidungen und Projekte fremder Projekte aus; durchgesetzt wird im
Orchestrator. Der Benutzerwechsel meldet über Keycloak ab und mit vorbelegtem Konto neu an.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from app import main as main_module
from app.auth import OidcAuth
from app.config import Settings
from app.flow_routes import project_rights, visible_overview
from fastapi.testclient import TestClient


def oidc_settings() -> Settings:
    return Settings(auth_mode="oidc", auth_session_secret="unit-test-session-secret",
                    platform_public_url="http://testserver",
                    oidc_external_issuer="http://keycloak.example/realms/open-manufacturing",
                    oidc_internal_issuer="http://keycloak:8080/realms/open-manufacturing")


SEED = Path(__file__).resolve().parents[1] / "seed" / "scenario.json"
CATALOG = {
    "TM-100": {"roles": {"lesen": "flow-prj-tm-100-lesen", "aendern": "flow-prj-tm-100-aendern"}},
    "PS-TM100": {"roles": {"lesen": "flow-prj-ps-tm100-lesen", "aendern": "flow-prj-ps-tm100-aendern"}},
}
OVERVIEW = {
    "demo_mode": True,
    "project_catalog": CATALOG,
    "runs": [{"id": "R1", "project": "TM-100"}, {"id": "R2", "project": "PS-TM100"}, {"id": "R3", "project": "FLOW-ALT"}],
    "decisions": [{"run_id": "R1", "auftrag": {"project": "TM-100"}}, {"run_id": "R2", "auftrag": {"project": "PS-TM100"}}],
    "projects": [{"id": "PRJ-TM-100", "code": "TM-100"}, {"id": "PRJ-PS-TM100", "code": "PS-TM100"}],
    "events": [{"run_id": "R1"}, {"run_id": "R2"}, {"run_id": "R3"}],
}


def test_member_sees_only_own_projects_and_legacy_runs() -> None:
    viewer = {"roles": ["flow-po", "flow-prj-tm-100-lesen"]}
    shown = visible_overview(OVERVIEW, viewer)
    assert [r["id"] for r in shown["runs"]] == ["R1", "R3"]
    assert [d["run_id"] for d in shown["decisions"]] == ["R1"]
    assert [p["code"] for p in shown["projects"]] == ["TM-100"]
    assert [e["run_id"] for e in shown["events"]] == ["R1", "R3"]
    assert list(shown["project_catalog"]) == ["TM-100"] and shown["hidden_runs"] == 1


def test_oversight_and_admin_see_everything() -> None:
    for roles in (["flow-isb"], ["flow-gf"], ["platform-admin"]):
        assert len(visible_overview(OVERVIEW, {"roles": roles})["runs"]) == 3


def test_project_rights_per_viewer() -> None:
    viewer = {"roles": ["flow-prj-tm-100-lesen", "flow-prj-tm-100-aendern", "flow-prj-ps-tm100-lesen"]}
    assert project_rights(CATALOG, viewer, False) == {"TM-100": "aendern", "PS-TM100": "lesen"}
    assert project_rights(CATALOG, {"roles": ["platform-admin"]}, True) == {"TM-100": "aendern", "PS-TM100": "aendern"}
    assert project_rights(CATALOG, {"roles": ["platform-admin"]}, False) == {"TM-100": "", "PS-TM100": ""}


@pytest.fixture()
def switch_client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, OidcAuth]:
    settings = dataclasses.replace(oidc_settings(), demo_user_switch=True, seed_file=SEED)
    auth = OidcAuth(settings)
    monkeypatch.setattr(main_module, "settings", settings)
    monkeypatch.setattr(main_module, "oidc_auth", auth)
    main_module._demo_catalog.cache_clear()
    yield TestClient(main_module.app), auth
    main_module._demo_catalog.cache_clear()


def session(auth: OidcAuth, username: str) -> dict[str, str]:
    return {auth.SESSION_COOKIE: auth._sign({"expires_at": 4_102_444_800,
                                              "user": {"username": username, "roles": ["dms-user"]}})}


def test_demo_accounts_list_functions_and_project_rights(switch_client) -> None:  # noqa: ANN001
    client, auth = switch_client
    assert client.get("/api/auth/demo-accounts").status_code == 401
    data = client.get("/api/auth/demo-accounts", cookies=session(auth, "po.demo")).json()
    accounts = {a["username"]: a for a in data["accounts"]}
    assert data["current"] == "po.demo" and data["enabled"] is True
    assert accounts["admin.demo"]["function"].startswith("Administration")
    assert set(accounts["admin.demo"]["projects"].values()) == {"aendern"}
    assert accounts["po.demo"]["projects"]["TM-100"] == "aendern" and accounts["po.demo"]["projects"]["PS-TM100"] == ""
    assert accounts["dev.demo"]["projects"]["TM-100"] == "lesen"
    assert "TM-100" in data["projects"]


def test_switch_logs_out_at_keycloak_and_prefills_the_account(switch_client) -> None:  # noqa: ANN001
    client, auth = switch_client
    assert client.get("/auth/switch?user=nicht.da", follow_redirects=False).status_code == 404
    response = client.get("/auth/switch?user=techlead.demo&next=/agents", follow_redirects=False,
                          cookies={**session(auth, "po.demo"), auth.ID_TOKEN_COOKIE: "idt"})
    location = urlparse(response.headers["location"])
    assert location.path.endswith("/protocol/openid-connect/logout")
    query = parse_qs(location.query)
    assert query["id_token_hint"] == ["idt"]
    target = urlparse(query["post_logout_redirect_uri"][0])
    assert target.path == "/auth/login" and parse_qs(target.query) == {"next": ["/agents"], "login_hint": ["techlead.demo"]}
    login = urlparse(client.get(query["post_logout_redirect_uri"][0].replace("http://testserver", ""),
                                follow_redirects=False).headers["location"])
    assert parse_qs(login.query)["login_hint"] == ["techlead.demo"] and parse_qs(login.query)["prompt"] == ["login"]


def test_login_hint_is_ignored_for_unknown_accounts(switch_client) -> None:  # noqa: ANN001
    client, _ = switch_client
    login = urlparse(client.get("/auth/login?login_hint=evil", follow_redirects=False).headers["location"])
    assert "login_hint" not in parse_qs(login.query)


def test_switch_is_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = dataclasses.replace(oidc_settings(), demo_user_switch=False, seed_file=SEED)
    monkeypatch.setattr(main_module, "settings", settings)
    monkeypatch.setattr(main_module, "oidc_auth", OidcAuth(settings))
    client = TestClient(main_module.app)
    assert client.get("/auth/switch?user=po.demo", follow_redirects=False).status_code == 404


def test_only_admins_may_change_agent_configuration(switch_client) -> None:  # noqa: ANN001
    client, auth = switch_client
    payload = {"changes": {"owner": "Teamleitung IT"}, "reason": "Zuständigkeit gewechselt"}
    assert client.put("/api/agents/agents/planung/config", json=payload).status_code == 401
    denied = client.put("/api/agents/agents/planung/config", json=payload, cookies=session(auth, "po.demo"))
    assert denied.status_code == 403 and "Administratoren" in denied.json()["detail"]
    assert client.put("/api/agents/agents/Bad-Role/config", json=payload,
                      cookies=session(auth, "po.demo")).status_code == 404
    assert client.put("/api/agents/agents/planung/config", json={"changes": {}, "reason": "x"},
                      cookies=session(auth, "po.demo")).status_code == 422


BUSINESS = {
    "agents": [{"id": "FA-001", "name": "Einkauf", "prompt": "geheim", "assigned_roles": ["procurement-user"],
                "assigned_users": [], "context_sources": ["einkauf"]},
               {"id": "FA-002", "name": "Qualität", "prompt": "x", "assigned_roles": [], "assigned_users": ["demo17"],
                "context_sources": []}],
    "jobs": [{"id": "J1", "kind": "aufgabe", "agent_id": "FA-001", "requested_by": {"username": "demo06"},
              "input": {"text": "Mail", "_context": {"einkauf": {}}}},
             {"id": "J2", "kind": "aufgabe", "agent_id": "FA-001", "requested_by": {"username": "demo07"}, "input": {}},
             {"id": "J3", "kind": "entwurf", "agent_id": "", "requested_by": {"username": "admin.demo"}, "input": {}}],
    "sources": {"einkauf": {"roles": ["procurement-user"]}},
}


def test_business_agents_are_visible_only_to_assigned_people() -> None:
    from app.flow_routes import business_for

    buyer = business_for(BUSINESS, {"username": "demo06", "roles": ["procurement-user"]})
    assert [a["id"] for a in buyer["agents"]] == ["FA-001"] and "prompt" not in buyer["agents"][0]
    assert [j["id"] for j in buyer["jobs"]] == ["J1"] and "_context" not in buyer["jobs"][0]["input"]
    assert buyer["can_admin"] is False
    assert business_for(BUSINESS, {"username": "demo21", "roles": ["production-user"]})["agents"] == []
    admin = business_for(BUSINESS, {"username": "admin.demo", "roles": ["platform-admin"]})
    assert len(admin["agents"]) == 2 and {j["id"] for j in admin["jobs"]} == {"J1", "J2", "J3"}


def test_background_data_only_for_entitled_people() -> None:
    from app.flow_routes import business_context

    data = {"purchase_orders": [{"id": "PO-1"}] * 40, "workplace": {"supplier_delivery_history": []}}
    entitled = business_context(["einkauf"], BUSINESS["sources"], {"roles": ["procurement-user"]}, lambda: data)
    assert len(entitled["einkauf"]["bestellungen"]) == 25
    assert business_context(["einkauf"], BUSINESS["sources"], {"roles": ["sales-user"]}, lambda: data) == {}


def test_only_admins_manage_business_agents(switch_client) -> None:  # noqa: ANN001
    client, auth = switch_client
    spec = {"spec": {"name": "X"}}
    assert client.post("/api/agents/fachagenten", json=spec).status_code == 401
    assert client.post("/api/agents/fachagenten", json=spec, cookies=session(auth, "po.demo")).status_code == 403
    assert client.post("/api/agents/fachagenten/entwurf", json={"description": "Ein Agent für Einkaufsmails"},
                       cookies=session(auth, "po.demo")).status_code == 403
