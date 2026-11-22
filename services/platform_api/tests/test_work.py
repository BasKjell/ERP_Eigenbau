from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

from app.config import Settings, settings
from app.main import app, store
from app.redmine import RedmineClient
from app.store import ScenarioStore
from app.work import WorkService
from fastapi.testclient import TestClient

client = TestClient(app)


def setup_function() -> None:
    store.reset()


def test_portal_and_flowwork_pages_expose_shared_app_launcher() -> None:
    portal = client.get("/")
    work = client.get("/work")
    management = client.get("/management")

    assert portal.status_code == 200
    assert portal.headers["cache-control"] == "no-store"
    assert "Meine Anwendungen" in portal.text
    assert "Mein KI-Arbeitsplatz" in portal.text
    assert 'data-tour="future-workplace"' in portal.text
    assert 'data-app-launcher' in portal.text
    assert 'href="/assets/company-theme.css"' in portal.text
    assert work.status_code == 200
    assert work.headers["cache-control"] == "no-store"
    assert "Requirement Center" in work.text
    assert 'src="/assets/app-launcher.js?v=20261116"' in work.text
    assert 'src="/assets/work.js?v=20261110"' in work.text
    assert 'href="/assets/company-theme.css"' in work.text
    assert management.status_code == 200
    assert management.headers["cache-control"] == "no-store"
    assert "Ein Wertstrom" in management.text
    assert "FLOWMANAGE" in management.text
    assert "Routine läuft im Hintergrund" in management.text
    assert "Vom Datenfundament zur begrenzten Autonomie" in management.text
    assert "Leitplanken für den Livebetrieb" in management.text
    assert 'data-tour="future-operating-model"' in management.text
    assert "Ein Konto aus dem AD" in management.text
    assert 'data-tour="iam-sso"' in management.text
    assert "/api/workplace/future-model" in client.get("/assets/app.js").text
    assert '$("#future-roadmap")' in client.get("/assets/app.js").text
    assert 'href="/management?managementDemo=1&amp;tourStep=0"' in management.text
    assert "Geführte Management-Demo starten" in management.text
    assert 'href="/assets/company-theme.css"' in management.text

    launcher = client.get("/assets/app-launcher.js")
    assert launcher.status_code == 200
    assert "PlatformLauncherConfig" in launcher.text
    assert "platformHref" in launcher.text
    assert "identityEndpoint" in launcher.text
    assert launcher.text.count("{ app:") == 25
    assert "AD-GG-FLOW-PROCUREMENT-USER" in launcher.text
    assert 'name: "FLOWPORTAL"' in launcher.text
    assert 'name: "FLOWERP"' in launcher.text
    assert 'name: "FLOWQ"' in launcher.text
    assert 'name: "FLOWDOC"' in launcher.text
    assert 'name: "FLOWAI"' in launcher.text
    assert 'name: "FLOWOPS"' in launcher.text
    assert 'target.searchParams.set("managementDemo", "1")' in launcher.text
    assert 'target.searchParams.set("tourStep", String(index))' in launcher.text
    assert 'tour.className = "platform-tour"' in launcher.text
    assert "Jama-Connect-Funktionsumfang" in launcher.text
    assert "Wareneingang einfach prüfen" in launcher.text
    assert "Gebäudeplan und Kollegensuche" in launcher.text
    assert "Zielbild Arbeitsplatz 2028" in launcher.text
    assert "Felix%20Hoffmann" in launcher.text
    assert "Arbeitsplatz von Felix Hoffmann im Grundriss markieren" in launcher.text
    assert "Felix Hoffmann mit markiertem Laufweg" not in launcher.text

    work_script = client.get("/assets/work.js")
    assert work_script.status_code == 200
    assert 'const params = new URLSearchParams(location.search)' in work_script.text
    assert 'params.set("view", name)' in work_script.text
    assert 'history.replaceState(null, "", `${location.pathname}?${params}`)' in work_script.text

    shell = client.get("/assets/company-shell.js")
    assert shell.status_code == 200
    assert "company-shell-rail" in shell.text
    assert "company-shell-active" in shell.text
    assert 'data-bs-theme", "light"' in shell.text
    assert 'name: "FLOWDOC"' in shell.text

    docs = client.get("/docs")
    assert docs.status_code == 200
    assert 'content="api"' in docs.text
    assert 'src="/assets/company-shell.js"' in docs.text


def test_work_dashboard_contains_redmine_issues_and_traceability() -> None:
    dashboard = client.get("/api/work/dashboard")

    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["product"] == "FLOWWORK"
    assert body["metrics"]["requirements"] == 5
    assert body["metrics"]["open_tasks"] == 3
    assert body["traceability"][0]["issue"]["key"] == "#101"
    assert body["traceability"][0]["complete"] is True


def test_requirement_lifecycle_issue_link_and_baseline() -> None:
    created = client.post(
        "/api/work/requirements",
        json={
            "title": "Diagnosezustand anzeigen",
            "text": "Das System muss den aktuellen Diagnosezustand anzeigen.",
            "type": "Software",
            "priority": "Must",
            "owner": "System Engineering",
            "acceptance_criteria": "Zustand wird innerhalb einer Sekunde aktualisiert.",
        },
    )
    assert created.status_code == 200
    requirement = created.json()
    assert requirement["id"] == "REQ-SCU-006"
    assert requirement["version"] == 1

    review = client.patch(
        f"/api/work/requirements/{requirement['id']}",
        json={"status": "review", "change_note": "Review gestartet"},
    )
    assert review.status_code == 200
    assert review.json()["version"] == 2
    assert review.json()["history"][0]["note"] == "Review gestartet"

    issue = client.post(
        "/api/work/issues",
        json={
            "subject": "Diagnoseanzeige umsetzen",
            "description": "Umsetzung gemäß neuer Anforderung",
            "priority": "Hoch",
            "assignee": "Software Team",
            "due_date": "2026-12-01",
            "requirement_id": requirement["id"],
        },
    )
    assert issue.status_code == 200
    assert issue.json()["key"] == "#105"

    baseline = client.post(
        "/api/work/baselines",
        json={
            "name": "Software Requirements Review",
            "description": "Stand zur Review",
            "requirement_ids": [requirement["id"]],
        },
    )
    assert baseline.status_code == 200
    assert baseline.json()["items"][0]["requirement_id"] == requirement["id"]
    assert baseline.json()["items"][0]["version"] == 3


def test_existing_state_is_upgraded_with_work_domain(tmp_path: Path) -> None:
    seed = json.loads(settings.seed_file.read_text(encoding="utf-8"))
    existing = json.loads(json.dumps(seed))
    existing.pop("work")
    seed_file = tmp_path / "seed.json"
    data_file = tmp_path / "data.json"
    seed_file.write_text(json.dumps(seed), encoding="utf-8")
    data_file.write_text(json.dumps(existing), encoding="utf-8")

    upgraded = ScenarioStore(data_file, seed_file).get()

    assert upgraded["work"]["requirements"][0]["id"] == "REQ-SCU-001"


def test_existing_work_state_receives_new_governance_collections(tmp_path: Path) -> None:
    seed = json.loads(settings.seed_file.read_text(encoding="utf-8"))
    existing = json.loads(json.dumps(seed))
    for key in (
        "item_types",
        "field_definitions",
        "relationship_types",
        "relationship_rules",
        "relationships",
        "reviews",
        "test_cases",
        "test_plans",
        "test_runs",
        "risks",
    ):
        existing["work"].pop(key)
    seed_file = tmp_path / "seed.json"
    data_file = tmp_path / "data.json"
    seed_file.write_text(json.dumps(seed), encoding="utf-8")
    data_file.write_text(json.dumps(existing), encoding="utf-8")

    upgraded = ScenarioStore(data_file, seed_file).get()["work"]

    assert upgraded["item_types"][0]["key"] == "Stakeholder"
    assert upgraded["reviews"][0]["id"] == "REV-0001"
    assert upgraded["test_cases"][0]["id"] == "TC-CAN-042"
    assert upgraded["relationships"][0]["id"] == "REL-0001"


def test_redmine_client_sends_api_key_and_normalises_issue(monkeypatch: Any) -> None:
    requests: list[urllib.request.Request] = []

    class Response:
        status = 200

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "issue": {
                        "id": 4711,
                        "subject": "API Ticket",
                        "status": {"id": 1, "name": "Neu"},
                        "project": {"id": 1, "name": "SCU-100"},
                    }
                }
            ).encode()

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> Response:
        assert timeout == 4
        requests.append(request)
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    redmine = RedmineClient(
        Settings(
            redmine_base_url="http://redmine.test",
            redmine_public_url="http://redmine.public",
            redmine_api_key="secret-key",
        )
    )

    issue = redmine.create_issue(
        {"project_id": "scu-100", "subject": "API Ticket", "description": "Test"}
    )

    assert issue["key"] == "#4711"
    assert issue["url"] == "http://redmine.public/issues/4711"
    assert requests[0].get_header("X-redmine-api-key") == "secret-key"
    assert json.loads(requests[0].data)["issue"]["project_id"] == "scu-100"


def test_work_service_falls_back_to_seed_when_redmine_is_not_configured() -> None:
    service = WorkService(store, Settings(redmine_api_key=""))

    dashboard = service.dashboard()

    assert dashboard["mode"] == "simulated"
    assert dashboard["issues"][0]["source"] == "demo"


def test_custom_fields_are_configurable_and_validated_per_item_type() -> None:
    field = client.post(
        "/api/work/admin/fields",
        json={
            "key": "CYBER_LEVEL",
            "name": "Cybersecurity Level",
            "field_type": "select",
            "required": True,
            "options": ["Basis", "Erhöht", "Kritisch"],
            "applies_to": ["Software"],
        },
    )
    assert field.status_code == 200
    assert field.json()["key"] == "CYBER_LEVEL"

    missing = client.post(
        "/api/work/requirements",
        json={
            "title": "Sichere Diagnoseverbindung",
            "text": "Die Diagnoseverbindung muss authentifiziert sein.",
            "type": "Software",
            "priority": "Must",
            "owner": "Security Engineering",
        },
    )
    assert missing.status_code == 409
    assert "Pflichtfeld" in missing.json()["detail"]

    created = client.post(
        "/api/work/requirements",
        json={
            "title": "Sichere Diagnoseverbindung",
            "text": "Die Diagnoseverbindung muss authentifiziert sein.",
            "type": "Software",
            "priority": "Must",
            "owner": "Security Engineering",
            "custom_fields": {"CYBER_LEVEL": "Kritisch"},
        },
    )
    assert created.status_code == 200
    assert created.json()["custom_fields"]["CYBER_LEVEL"] == "Kritisch"


def test_relationship_model_marks_and_clears_suspect_links() -> None:
    changed = client.patch(
        "/api/work/requirements/REQ-SCU-002",
        json={"title": "Eindeutige rückverfolgbare Seriennummer", "change_note": "Norm präzisiert"},
    )
    assert changed.status_code == 200

    dashboard = client.get("/api/work/dashboard").json()
    suspects = [
        item for item in dashboard["relationships"] if item["source_id"] == "REQ-SCU-002"
    ]
    assert suspects
    assert all(item["suspect"] is True for item in suspects)
    assert dashboard["metrics"]["suspect_links"] >= 2

    cleared = client.post(
        f"/api/work/relationships/{suspects[0]['id']}/clear-suspect"
    )
    assert cleared.status_code == 200
    assert cleared.json()["suspect"] is False
    assert cleared.json()["assessed_by"] == "Demo Benutzer"


def test_review_center_enforces_approver_and_electronic_signature() -> None:
    created = client.post(
        "/api/work/reviews",
        json={
            "title": "Software Requirements Review",
            "item_ids": ["REQ-SCU-005"],
            "participants": [
                {"name": "Demo Benutzer", "role": "approver"},
                {"name": "Qualität", "role": "reviewer"},
            ],
            "deadline": "2026-12-01",
            "require_signature": True,
        },
    )
    assert created.status_code == 200
    review_id = created.json()["id"]

    comment = client.post(
        f"/api/work/reviews/{review_id}/comments",
        json={"item_id": "REQ-SCU-005", "text": "Bitte @tim die Fehlermeldung präzisieren."},
    )
    assert comment.status_code == 200
    assert comment.json()["mentions"] == ["tim"]

    unsigned = client.post(
        f"/api/work/reviews/{review_id}/decisions",
        json={"decision": "approved"},
    )
    assert unsigned.status_code == 409

    approved = client.post(
        f"/api/work/reviews/{review_id}/decisions",
        json={
            "decision": "approved",
            "signature": "Demo Benutzer · elektronisch bestätigt",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["participants"][0]["signature"]


def test_test_management_risk_and_end_to_end_relationships() -> None:
    test_case = client.post(
        "/api/work/tests/cases",
        json={
            "title": "Ungültige Zeitbuchung abweisen",
            "owner": "Qualität",
            "steps": [
                {"order": 1, "action": "Gesperrten Auftrag wählen", "expected": "Buchung abgewiesen"}
            ],
            "expected_result": "Nachvollziehbare Fehlermeldung",
            "status": "approved",
            "requirement_ids": ["REQ-SCU-005"],
        },
    )
    assert test_case.status_code == 200
    test_case_id = test_case.json()["id"]

    plan = client.post(
        "/api/work/tests/plans",
        json={
            "name": "MES Regression",
            "owner": "Qualität",
            "test_case_ids": [test_case_id],
        },
    )
    assert plan.status_code == 200
    run_id = plan.json()["run_id"]

    executed = client.post(
        f"/api/work/tests/runs/{run_id}/cases/{test_case_id}",
        json={"result": "failed", "defect_issue_id": "#104", "evidence": "DMS-TEST-009"},
    )
    assert executed.status_code == 200
    assert executed.json()["result"] == "failed"

    risk = client.post(
        "/api/work/risks",
        json={
            "title": "Fehlerhafte Zeitzuordnung",
            "description": "Kosten werden dem falschen Auftrag zugeordnet.",
            "probability": 3,
            "impact": 4,
            "mitigation": "Validierung gegen freigegebene Aufträge",
            "owner": "Produktionsleitung",
            "requirement_ids": ["REQ-SCU-005"],
        },
    )
    assert risk.status_code == 200
    assert risk.json()["rating"] == 12

    dashboard = client.get("/api/work/dashboard").json()
    assert any(
        item["source_id"] == "REQ-SCU-005" and item["target_id"] == test_case_id
        for item in dashboard["relationships"]
    )
    assert any(
        item["source_id"] == risk.json()["id"] and item["target_id"] == "REQ-SCU-005"
        for item in dashboard["relationships"]
    )


def test_branch_baseline_compare_and_interchange_exports() -> None:
    branch = client.post(
        "/api/work/requirements/REQ-SCU-001/branch",
        json={"variant": "SCU Arctic"},
    )
    assert branch.status_code == 200
    assert branch.json()["source_id"] == "REQ-SCU-001"
    assert branch.json()["status"] == "draft"

    comparison = client.get("/api/work/baselines/BL-SCU-001/compare")
    assert comparison.status_code == 200
    assert branch.json()["id"] in comparison.json()["added"]

    json_export = client.get("/api/work/export?format=json")
    assert json_export.status_code == 200
    assert json_export.json()["schema"] == "flowwork-interchange-1.0"
    assert "attachment" in json_export.headers["content-disposition"]

    csv_export = client.get("/api/work/export?format=csv")
    assert csv_export.status_code == 200
    assert "REQ-SCU-001" in csv_export.text

    reqif_export = client.get("/api/work/export?format=reqif")
    assert reqif_export.status_code == 200
    assert "<REQ-IF" in reqif_export.text
    assert "<SPEC-RELATIONS>" in reqif_export.text
