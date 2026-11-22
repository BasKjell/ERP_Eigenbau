from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader

from app.config import Settings, settings
from app.people import PeopleError, PeopleNotFoundError, PeopleService
from app.store import ScenarioStore


class FakeDms:
    def __init__(self, configured: bool = False) -> None:
        self.configured = configured
        self.uploads: list[dict[str, Any]] = []

    def upload_document(
        self, content: bytes, filename: str, title: str
    ) -> dict[str, Any]:
        self.uploads.append(
            {"content": content, "filename": filename, "title": title}
        )
        return {"task_id": f"DMS-TASK-{len(self.uploads):04d}"}


class FakeAccounting:
    def __init__(self, configured: bool = False) -> None:
        self.configured = configured
        self.created: list[tuple[str, dict[str, Any]]] = []

    def create_document(self, doctype: str, values: dict[str, Any]) -> dict[str, Any]:
        self.created.append((doctype, values))
        return {"name": "JV-PAYROLL-0001", **values}


def service(
    tmp_path: Path, *, dms: bool = False, erp: bool = False
) -> tuple[ScenarioStore, PeopleService, FakeDms, FakeAccounting]:
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(settings.seed_file.read_text(encoding="utf-8"), encoding="utf-8")
    local_settings = Settings(
        data_file=tmp_path / "state.json",
        seed_file=seed_file,
        mcp_default_company="Open Manufacturing Demo GmbH",
    )
    store = ScenarioStore(local_settings.data_file, seed_file)
    dms_client = FakeDms(dms)
    accounting = FakeAccounting(erp)
    people = PeopleService(store, local_settings, dms_client, accounting)
    return store, people, dms_client, accounting


def test_recruiting_dashboard_is_role_protected_and_shows_dms_policy(
    tmp_path: Path,
) -> None:
    _, people, _, _ = service(tmp_path)

    dashboard = people.recruiting_dashboard("HR-USER-001")

    assert dashboard["metrics"] == {
        "open_vacancies": 2,
        "active_applications": 2,
        "interviews": 1,
        "retention_due": 0,
    }
    assert dashboard["dms"]["access_group"] == "DMS-Bereich-HR-Recruiting"
    with pytest.raises(PeopleNotFoundError, match="nicht gefunden"):
        people.recruiting_dashboard("DEMO-EMP-001")


def test_application_creation_duplicate_control_and_ordered_stage_transitions(
    tmp_path: Path,
) -> None:
    _, people, _, _ = service(tmp_path)
    values = {
        "vacancy_id": "VAC-0001",
        "candidate_name": "Mia Test",
        "email": "mia.test@example.invalid",
        "phone": "+49 30 5550103",
        "source": "Karriereseite",
    }

    created = people.create_application("HR-USER-001", values)
    assert created["id"] == "APP-0003"
    assert created["stage"] == "new"
    assert created["privacy_notice_version"] == "DS-HR-2026-01"
    with pytest.raises(PeopleError, match="bereits Bewerbung"):
        people.create_application("HR-USER-001", values)
    with pytest.raises(PeopleError, match="Nächste zulässige"):
        people.move_application(created["id"], "HR-USER-001", "offer")

    screening = people.move_application(
        created["id"], "HR-USER-001", "screening", "Unterlagen vollständig"
    )
    assert screening["stage"] == "screening"
    assert screening["history"][-1]["actor_id"] == "HR-USER-001"


def test_recruiting_document_link_and_upload_stay_in_protected_area(
    tmp_path: Path,
) -> None:
    _, people, dms, _ = service(tmp_path, dms=True)

    linked = people.link_application_document(
        "APP-0002", "HR-USER-001", "DOC-HR-CV-001", "Lebenslauf"
    )
    assert linked["access_group"] == "DMS-Bereich-HR-Recruiting"
    with pytest.raises(PeopleError, match="geschützten Bewerberakte"):
        people.link_application_document(
            "APP-0002", "HR-USER-001", "DOC-WI-100", "Arbeitsanweisung"
        )

    uploaded = people.upload_application_document(
        "APP-0002",
        "HR-USER-001",
        b"%PDF-1.4 fictional",
        "lebenslauf.pdf",
        "Lebenslauf",
    )
    assert uploaded["dms_task_id"] == "DMS-TASK-0001"
    assert dms.uploads[0]["filename"] == "Bewerbung_APP-0002_lebenslauf.pdf"
    assert uploaded["status"] == "processing"


def test_recruiting_upload_fails_closed_without_dms(tmp_path: Path) -> None:
    _, people, _, _ = service(tmp_path)

    with pytest.raises(PeopleError, match="nicht konfiguriert"):
        people.upload_application_document(
            "APP-0001", "HR-USER-001", b"%PDF", "unterlage.pdf", "Lebenslauf"
        )


def test_payroll_requires_complete_master_data_and_four_eyes(tmp_path: Path) -> None:
    store, people, _, _ = service(tmp_path)

    preview = people.prepare_payroll("PAY-2026-10", "HR-USER-001")
    assert preview["employee_count"] == 6
    assert preview["gross_cents"] == 2_551_500
    assert preview["net_cents"] == 1_698_650

    def add_approver_role(state: dict[str, Any]) -> None:
        state["hr"]["admin_users"][0]["roles"].append("payroll_approver")

    store.mutate(add_approver_role)
    with pytest.raises(PeopleError, match="verschiedene Personen"):
        people.approve_payroll("PAY-2026-10", "HR-USER-001", preview["token"])

    approved = people.approve_payroll(
        "PAY-2026-10", "HR-USER-002", preview["token"]
    )
    assert approved["run"]["status"] == "approved_pending_delivery"
    assert approved["run"]["prepared_by"] != approved["run"]["approved_by"]
    repeated = people.approve_payroll(
        "PAY-2026-10", "HR-USER-002", preview["token"]
    )
    assert repeated["status"] == "already_approved"
    assert store.get()["hr"]["payroll"]["periods"][0]["status"] == "approved"


def test_payroll_rejects_incomplete_data_and_unlocked_time(tmp_path: Path) -> None:
    store, people, _, _ = service(tmp_path)

    def unlock(state: dict[str, Any]) -> None:
        state["hr"]["payroll"]["periods"][0]["attendance_status"] = "open"

    store.mutate(unlock)
    with pytest.raises(PeopleError, match="Anwesenheitsdaten"):
        people.prepare_payroll("PAY-2026-10", "HR-USER-001")

    def incomplete(state: dict[str, Any]) -> None:
        state["hr"]["payroll"]["periods"][0]["attendance_status"] = "locked"
        state["hr"]["payroll"]["profiles"][0]["checks"]["bank"] = False

    store.mutate(incomplete)
    with pytest.raises(PeopleError, match="DEMO-EMP-001"):
        people.prepare_payroll("PAY-2026-10", "HR-USER-001")


def test_payroll_delivery_is_resumable_idempotent_and_balanced(tmp_path: Path) -> None:
    store, people, dms, accounting = service(tmp_path, dms=True, erp=True)
    preview = people.prepare_payroll("PAY-2026-10", "HR-USER-001")
    run = people.approve_payroll(
        "PAY-2026-10", "HR-USER-002", preview["token"]
    )["run"]

    delivered = people.deliver_payroll(run["id"], "HR-USER-002")

    assert delivered["run"]["erp_reference"] == "JV-PAYROLL-0001"
    assert len(dms.uploads) == 6
    assert all(item["content"].startswith(b"%PDF") for item in dms.uploads)
    assert all(
        item["filename"].startswith("Entgeltabrechnung_PAY-2026-10_")
        for item in dms.uploads
    )
    assert len(accounting.created) == 1
    doctype, journal = accounting.created[0]
    assert doctype == "Journal Entry"
    debit = sum(item.get("debit_in_account_currency", 0) for item in journal["accounts"])
    credit = sum(item.get("credit_in_account_currency", 0) for item in journal["accounts"])
    assert debit == credit
    repeated = people.deliver_payroll(run["id"], "HR-USER-002")
    assert repeated["status"] == "already_delivered"
    assert len(dms.uploads) == 6
    assert len(accounting.created) == 1
    assert store.get()["hr"]["payroll"]["periods"][0]["status"] == "closed"


def test_payslip_is_valid_pdf_and_access_is_limited(tmp_path: Path) -> None:
    _, people, _, _ = service(tmp_path)
    preview = people.prepare_payroll("PAY-2026-10", "HR-USER-001")
    run = people.approve_payroll(
        "PAY-2026-10", "HR-USER-002", preview["token"]
    )["run"]

    content = people.payslip_pdf(run["id"], "DEMO-EMP-001", "DEMO-EMP-001")
    assert content.startswith(b"%PDF")
    reader = PdfReader(__import__("io").BytesIO(content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Demonstrationsbeleg" in text
    assert "2.493,00 EUR" in text
    with pytest.raises(PeopleNotFoundError, match="HR-Benutzer"):
        people.payslip_pdf(run["id"], "DEMO-EMP-001", "DEMO-EMP-002")
