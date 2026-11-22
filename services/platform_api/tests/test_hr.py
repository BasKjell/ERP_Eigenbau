from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from app.config import Settings, settings
from app.hr import HrError, HrService
from app.store import ScenarioStore


class FakeTimesheetClient:
    def __init__(self, configured: bool = False) -> None:
        self.configured = configured
        self.created: list[tuple[str, dict[str, Any]]] = []

    def create_document(self, doctype: str, values: dict[str, Any]) -> dict[str, Any]:
        self.created.append((doctype, values))
        return {"name": "TS-HR-0001", **values}


def service(
    tmp_path: Path, *, configured: bool = False
) -> tuple[ScenarioStore, HrService, FakeTimesheetClient]:
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(settings.seed_file.read_text(encoding="utf-8"), encoding="utf-8")
    local_settings = Settings(
        data_file=tmp_path / "state.json",
        seed_file=seed_file,
        mcp_default_company="Open Manufacturing Demo GmbH",
    )
    store = ScenarioStore(local_settings.data_file, seed_file)
    client = FakeTimesheetClient(configured)
    return store, HrService(store, local_settings, client), client


def test_dashboard_calculates_presence_balances_and_private_team_absence(
    tmp_path: Path,
) -> None:
    _, hr, _ = service(tmp_path)

    dashboard = hr.dashboard("DEMO-EMP-006", "2026-11-03")

    assert dashboard["is_manager"] is True
    assert dashboard["attendance"]["is_present"] is True
    statuses = {item["id"]: item["status"] for item in dashboard["team"]}
    assert statuses["DEMO-EMP-001"] == "present"
    assert statuses["DEMO-EMP-003"] == "vacation"
    assert statuses["DEMO-EMP-005"] == "absent"
    sick_event = next(
        item for item in dashboard["calendar"]["events"] if item["id"] == "HR-REQ-0003"
    )
    assert sick_event["type"] == "absence"
    assert sick_event["reason"] == ""


def test_punch_requires_alternating_events_and_calculates_closed_time(tmp_path: Path) -> None:
    _, hr, _ = service(tmp_path)

    dashboard = hr.punch(
        "DEMO-EMP-001",
        "OUT",
        "2026-11-03T14:27:00+01:00",
        "terminal",
        "Werkstor Nord",
    )

    assert dashboard["attendance"]["is_present"] is False
    assert dashboard["attendance"]["worked_minutes"] == 510
    with pytest.raises(HrError, match="zuerst Kommen"):
        hr.punch("DEMO-EMP-001", "OUT", "2026-11-03T14:28:00+01:00")


def test_request_workflow_separates_applicant_and_manager(tmp_path: Path) -> None:
    store, hr, _ = service(tmp_path)
    request = hr.create_request(
        "DEMO-EMP-001",
        {
            "type": "vacation",
            "start_date": "2026-12-07",
            "end_date": "2026-12-11",
            "reason": "Erholungsurlaub Dezember",
        },
    )

    with pytest.raises(HrError, match="nicht selbst"):
        hr.decide_request(request["id"], "DEMO-EMP-001", "approved")

    decided = hr.decide_request(
        request["id"], "DEMO-EMP-006", "approved", "Vertretung geklärt"
    )

    assert decided["status"] == "approved"
    employee = next(item for item in store.get()["hr"]["employees"] if item["id"] == "DEMO-EMP-001")
    assert employee["leave_used_days"] == 17


def test_approved_correction_creates_audited_attendance_pair(tmp_path: Path) -> None:
    store, hr, _ = service(tmp_path)

    decided = hr.decide_request(
        "HR-REQ-0007", "DEMO-EMP-006", "approved", "Plausibilisiert"
    )

    assert decided["status"] == "approved"
    events = [
        item
        for item in store.get()["hr"]["attendance"]
        if item["employee_id"] == "DEMO-EMP-005"
    ]
    assert [item["direction"] for item in events] == ["IN", "OUT"]
    assert {item["source"] for item in events} == {"approved_correction"}


def test_erp_export_uses_preview_confirmation_and_idempotency(tmp_path: Path) -> None:
    store, hr, client = service(tmp_path, configured=True)

    preview = hr.export_to_erp("DEMO-EMP-001", "2026-11-02")
    assert preview["status"] == "preview"
    assert preview["interval_count"] == 2
    assert preview["payload"]["time_logs"][0]["activity_type"] == "Anwesenheitszeit"

    exported = hr.export_to_erp(
        "DEMO-EMP-001",
        "2026-11-02",
        confirm=True,
        confirmation_token=preview["confirmation_token"],
    )

    assert exported["export"]["erp_reference"] == "TS-HR-0001"
    assert len(client.created) == 1
    assert client.created[0][0] == "Timesheet"
    assert all(
        item["erp_status"] == "exported"
        for item in store.get()["hr"]["attendance"][:4]
    )
    repeated = hr.export_to_erp("DEMO-EMP-001", "2026-11-02")
    assert repeated["status"] == "already_exported"
    assert len(client.created) == 1


def test_non_manager_cannot_open_team_calendar(tmp_path: Path) -> None:
    _, hr, _ = service(tmp_path)

    with pytest.raises(HrError, match="Führungskräfte"):
        hr.calendar("DEMO-EMP-001", "2026-11", "team")


def test_attendance_warns_for_break_and_daily_maximum(tmp_path: Path) -> None:
    _, hr, _ = service(tmp_path)

    dashboard = hr.punch(
        "DEMO-EMP-001",
        "OUT",
        "2026-11-03T17:01:00+01:00",
        "terminal",
        "Werkstor Nord",
    )

    assert dashboard["attendance"]["worked_minutes"] > 600
    assert any("Mindestpause" in item for item in dashboard["attendance"]["warnings"])
    assert any("Höchstarbeitszeit" in item for item in dashboard["attendance"]["warnings"])


def test_sick_report_is_hidden_from_manager_team_views(tmp_path: Path) -> None:
    _, hr, _ = service(tmp_path)

    request = hr.create_request(
        "DEMO-EMP-001",
        {
            "type": "sick",
            "start_date": "2026-12-01",
            "end_date": "2026-12-02",
            "reason": "Arbeitsunfähigkeit gemeldet",
        },
    )
    dashboard = hr.dashboard("DEMO-EMP-006", "2026-12-01")
    manager_view = next(item for item in dashboard["requests"] if item["id"] == request["id"])
    calendar_view = next(
        item for item in dashboard["calendar"]["events"] if item["id"] == request["id"]
    )

    assert manager_view["type_label"] == "Abwesenheit"
    assert manager_view["reason"] == ""
    assert calendar_view["type"] == "absence"
    assert calendar_view["reason"] == ""


def test_request_rejects_overlap_and_unfunded_time_off(tmp_path: Path) -> None:
    _, hr, _ = service(tmp_path)

    with pytest.raises(HrError, match="überschneidet"):
        hr.create_request(
            "DEMO-EMP-003",
            {
                "type": "sick",
                "start_date": "2026-11-04",
                "end_date": "2026-11-05",
                "reason": "Arbeitsunfähigkeit gemeldet",
            },
        )
    with pytest.raises(HrError, match="Zeitkonto"):
        hr.create_request(
            "DEMO-EMP-005",
            {
                "type": "time_off",
                "start_date": "2026-11-10",
                "end_date": "2026-11-10",
                "minutes": 720,
                "reason": "Nicht gedeckter Abbau",
            },
        )


def test_erp_export_rejects_open_attendance_and_invalid_confirmation(tmp_path: Path) -> None:
    _, hr, _ = service(tmp_path)

    with pytest.raises(HrError, match="noch offen"):
        hr.export_to_erp("DEMO-EMP-001", "2026-11-03")
    with pytest.raises(HrError, match="Ungültige"):
        hr.export_to_erp(
            "DEMO-EMP-001",
            "2026-11-02",
            confirm=True,
            confirmation_token="kein-passender-token",
        )
