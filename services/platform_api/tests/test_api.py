import asyncio
import json
from pathlib import Path
from typing import Any

from app import main as main_module
from app.business_tools import list_late_purchase_orders, list_production_orders
from app.config import Settings, settings
from app.dms_mcp_server import mcp as dms_mcp
from app.erp_read import ERPReadService
from app.knowledge import KnowledgeService
from app.knowledge_mcp_server import mcp as knowledge_mcp
from app.main import app, store
from app.master_data import AuditLog, MasterDataError, MasterDataService
from app.mcp_server import mcp
from app.paperless_client import PaperlessClient
from app.store import ScenarioStore
from fastapi.testclient import TestClient
from mcp import Client

client = TestClient(app)


def setup_function() -> None:
    store.reset()


def test_health_and_initial_state() -> None:
    assert client.get("/health").json()["status"] == "ok"
    state = client.get("/api/demo").json()
    assert state["order"]["id"] == "SO-4711"
    assert state["order"]["product"] == "SCU-100"
    assert len(state["process"]) == 12


def test_existing_demo_state_is_upgraded_with_mes_and_hr_without_reset(tmp_path: Path) -> None:
    seed = json.loads(settings.seed_file.read_text(encoding="utf-8"))
    existing = json.loads(json.dumps(seed))
    existing.pop("mes")
    existing.pop("hr")
    existing["process"][0]["status"] = "done"
    seed_file = tmp_path / "seed.json"
    data_file = tmp_path / "state.json"
    seed_file.write_text(json.dumps(seed), encoding="utf-8")
    data_file.write_text(json.dumps(existing), encoding="utf-8")

    upgraded = ScenarioStore(data_file, seed_file).get()
    assert "mes" in upgraded
    assert "hr" in upgraded
    assert upgraded["process"][0]["status"] == "done"


def test_hr_page_dashboard_calendar_and_workflows() -> None:
    page = client.get("/hr")
    assert page.status_code == 200
    assert "FLOWHR" in page.text
    assert 'data-close-dialog="request-dialog"' in page.text
    assert '<option value="sick">Krankmeldung</option>' in page.text

    dashboard = client.get(
        "/api/hr/dashboard",
        params={"employee_id": "DEMO-EMP-006", "selected_date": "2026-11-03"},
    ).json()
    assert dashboard["is_manager"] is True
    assert len(dashboard["team"]) == 6
    assert dashboard["metrics"]["team_pending_approvals"] == 3

    calendar = client.get(
        "/api/hr/calendar",
        params={"employee_id": "DEMO-EMP-006", "month": "2026-11", "scope": "team"},
    ).json()
    assert {item["type"] for item in calendar["events"]} >= {
        "vacation",
        "absence",
        "remote_work",
    }

    request = client.post(
        "/api/hr/requests",
        json={
            "employee_id": "DEMO-EMP-001",
            "type": "vacation",
            "start_date": "2026-12-07",
            "end_date": "2026-12-11",
            "reason": "Urlaub für API-Test",
        },
    )
    assert request.status_code == 200
    request_id = request.json()["id"]
    own_decision = client.post(
        f"/api/hr/requests/{request_id}/decision",
        json={"approver_id": "DEMO-EMP-001", "decision": "approved"},
    )
    assert own_decision.status_code == 409
    approval = client.post(
        f"/api/hr/requests/{request_id}/decision",
        json={
            "approver_id": "DEMO-EMP-006",
            "decision": "approved",
            "comment": "Vertretung geklärt",
        },
    )
    assert approval.status_code == 200
    assert approval.json()["status"] == "approved"


def test_hr_erp_export_requires_preview_and_is_idempotent() -> None:
    preview = client.post(
        "/api/hr/export/erp",
        json={
            "employee_id": "DEMO-EMP-001",
            "date": "2026-11-02",
            "confirm": False,
        },
    )
    assert preview.status_code == 200
    assert preview.json()["interval_count"] == 2

    result = client.post(
        "/api/hr/export/erp",
        json={
            "employee_id": "DEMO-EMP-001",
            "date": "2026-11-02",
            "confirm": True,
            "confirmation_token": preview.json()["confirmation_token"],
        },
    )
    assert result.status_code == 200
    assert result.json()["status"] == "success"
    repeated = client.post(
        "/api/hr/export/erp",
        json={
            "employee_id": "DEMO-EMP-001",
            "date": "2026-11-02",
            "confirm": False,
        },
    )
    assert repeated.json()["status"] == "already_exported"


def test_recruiting_and_payroll_api_workflows_render_documents_inline() -> None:
    page = client.get("/hr")
    assert 'data-view="recruiting"' in page.text
    assert 'data-view="payroll"' in page.text

    recruiting = client.get(
        "/api/hr/recruiting", params={"actor_id": "HR-USER-001"}
    )
    assert recruiting.status_code == 200
    assert recruiting.json()["dms"]["access_group"] == "DMS-Bereich-HR-Recruiting"
    created = client.post(
        "/api/hr/recruiting/applications",
        json={
            "actor_id": "HR-USER-001",
            "vacancy_id": "VAC-0001",
            "candidate_name": "API Bewerber",
            "email": "api.bewerber@example.invalid",
            "source": "API-Test",
        },
    )
    assert created.status_code == 200
    application_id = created.json()["id"]
    moved = client.post(
        f"/api/hr/recruiting/applications/{application_id}/stage",
        json={"actor_id": "HR-USER-001", "stage": "screening", "note": "geprüft"},
    )
    assert moved.json()["stage"] == "screening"
    linked = client.post(
        f"/api/hr/recruiting/applications/{application_id}/documents/link",
        json={
            "actor_id": "HR-USER-001",
            "document_id": "DOC-HR-CV-001",
            "document_type": "Lebenslauf",
        },
    )
    assert linked.json()["access_group"] == "DMS-Bereich-HR-Recruiting"

    preview = client.post(
        "/api/hr/payroll/PAY-2026-10/prepare", json={"actor_id": "HR-USER-001"}
    )
    assert preview.status_code == 200
    wrong_role = client.post(
        "/api/hr/payroll/PAY-2026-10/approve",
        json={
            "actor_id": "HR-USER-001",
            "confirmation_token": preview.json()["token"],
        },
    )
    assert wrong_role.status_code == 409
    approval = client.post(
        "/api/hr/payroll/PAY-2026-10/approve",
        json={
            "actor_id": "HR-USER-002",
            "confirmation_token": preview.json()["token"],
        },
    )
    assert approval.status_code == 200
    run_id = approval.json()["run"]["id"]
    delivery = client.post(
        f"/api/hr/payroll/runs/{run_id}/deliver",
        json={"actor_id": "HR-USER-002"},
    )
    assert delivery.status_code == 200
    assert delivery.json()["run"]["erp_reference"].startswith("SIM-JE-")

    payslip = client.get(
        f"/api/hr/payroll/runs/{run_id}/payslips/DEMO-EMP-001",
        params={"actor_id": "HR-USER-001"},
    )
    assert payslip.status_code == 200
    assert payslip.content.startswith(b"%PDF")
    assert payslip.headers["content-disposition"].startswith("inline;")


def test_mes_workplace_exposes_personal_queue_and_linked_documents() -> None:
    page = client.get("/mes")
    assert page.status_code == 200
    assert "FLOWMES" in page.text

    dashboard = client.get(
        "/api/mes/dashboard", params={"operator_id": "DEMO-EMP-002"}
    ).json()
    assert dashboard["next_job"]["id"] == "JC-2027-0130"
    assert dashboard["next_job"]["status"] == "ready"
    assert dashboard["next_job"]["remaining_qty"] == 5
    assert len(dashboard["next_job"]["route"]) == 5

    documents = client.get("/api/mes/jobs/JC-2027-0130/documents").json()
    assert {document["id"] for document in documents["linked_documents"]} == {
        "DOC-WI-100",
        "DOC-DRW-100",
        "DOC-CERT-MB",
    }
    assert documents["dms_search"]["mode"] in {"simulated", "live", "error"}


def test_mes_job_can_start_book_time_pause_and_report_issue() -> None:
    job_id = "JC-2027-0130"
    assert client.post(
        f"/api/mes/jobs/{job_id}/start", json={"operator_id": "DEMO-EMP-001"}
    ).status_code == 409

    started = client.post(
        f"/api/mes/jobs/{job_id}/start", json={"operator_id": "DEMO-EMP-002"}
    ).json()
    assert started["status"] == "in_progress"
    assert started["time_logs"][-1]["ended_at"] is None

    paused = client.post(
        f"/api/mes/jobs/{job_id}/pause",
        json={
            "operator_id": "DEMO-EMP-002",
            "reason": "Technische Klärung",
            "note": "J4 prüfen",
        },
    ).json()
    assert paused["status"] == "paused"
    assert paused["time_logs"][-1]["minutes"] >= 1

    booked = client.post(
        f"/api/mes/jobs/{job_id}/time",
        json={
            "operator_id": "DEMO-EMP-002",
            "minutes": 15,
            "activity": "Rüstzeit",
            "note": "ESD-Platz eingerichtet",
        },
    ).json()
    assert booked["booked_minutes"] >= 16

    issue = client.post(
        f"/api/mes/jobs/{job_id}/issue",
        json={
            "operator_id": "DEMO-EMP-002",
            "category": "Materialfehler",
            "description": "Steckverbinder beschädigt",
        },
    ).json()
    assert issue["status"] == "blocked"
    assert issue["issue"]["status"] == "open"

    resolved = client.post(
        f"/api/mes/jobs/{job_id}/issue/resolve",
        json={
            "operator_id": "DEMO-EMP-002",
            "resolution": "Steckverbinder ersetzt und Sichtprüfung wiederholt",
        },
    ).json()
    assert resolved["status"] == "ready"
    assert resolved["issue"]["status"] == "resolved"


def test_mes_completion_enforces_checklist_and_releases_next_operation() -> None:
    job_id = "JC-2027-0130"
    start = {"operator_id": "DEMO-EMP-002"}
    assert client.post(f"/api/mes/jobs/{job_id}/start", json=start).status_code == 200

    incomplete = {
        **start,
        "completed_qty": 5,
        "scrap_qty": 0,
        "serial_numbers": [f"SN-{number}" for number in range(10001, 10006)],
        "checklist": ["esd"],
        "note": "",
    }
    assert client.post(
        f"/api/mes/jobs/{job_id}/complete", json=incomplete
    ).status_code == 409

    completed = client.post(
        f"/api/mes/jobs/{job_id}/complete",
        json={**incomplete, "checklist": ["esd", "revision", "j4", "visual"]},
    ).json()
    assert completed["status"] == "completed"
    assert completed["completed_qty"] == 5

    next_job = client.get("/api/mes/jobs/JC-2027-0131").json()
    assert next_job["status"] == "ready"

    reset = client.post(
        "/api/mes/reset", params={"operator_id": "DEMO-EMP-002"}
    ).json()
    assert reset["next_job"]["id"] == "JC-2027-0130"
    assert reset["next_job"]["status"] == "ready"


def test_process_can_advance() -> None:
    before = client.get("/api/demo").json()
    after = client.post("/api/demo/advance").json()
    assert after["metrics"]["completed_steps"] == before["metrics"]["completed_steps"] + 1
    assert after["process"][0]["status"] == "done"


def test_quality_failure_blocks_progress_until_rework() -> None:
    failed = client.post("/api/demo/failure").json()
    assert failed["quality_incident"]["status"] == "open"
    assert failed["order"]["delivery_risk"] == "at_risk"
    assert client.post("/api/demo/advance").status_code == 409

    reworked = client.post("/api/demo/rework").json()
    assert reworked["quality_incident"]["status"] == "resolved"
    assert reworked["order"]["delivery_risk"] == "on_track"
    assert client.post("/api/demo/advance").status_code == 200


def test_assistant_is_grounded_in_order_and_sources() -> None:
    result = client.post(
        "/api/assistant/ask", json={"question": "Wie ist der Status von Auftrag 4711?"}
    ).json()
    assert "Auftrag 4711" in result["answer"]
    assert result["sources"]
    assert result["mode"] in {"deterministic", "ollama"}


def test_unknown_stage_returns_404() -> None:
    assert client.post("/api/demo/stage/not-real").status_code == 404


def test_all_document_files_are_declared() -> None:
    assert settings.seed_file.exists()
    state = store.get()
    assert {doc["id"] for doc in state["documents"]} == {
        "DOC-DRW-100",
        "DOC-WI-100",
        "DOC-QP-100",
        "DOC-CERT-MB",
        "DOC-ATP-4711",
        "DOC-HR-CV-001",
        "DOC-HR-PAY-001",
    }


def test_pdf_documents_are_served_inline(
    tmp_path: Path, monkeypatch: Any
) -> None:
    document = store.get()["documents"][0]
    document_path = tmp_path / document["filename"]
    document_path.write_bytes(b"%PDF-1.4\n%%EOF\n")
    monkeypatch.setattr(main_module, "settings", Settings(document_dir=tmp_path))

    response = client.get(f"/api/documents/{document['id']}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline;")


def test_seed_declares_consistent_commercial_and_workforce_master_data() -> None:
    scenario = json.loads(settings.seed_file.read_text(encoding="utf-8"))

    assert {row["code"] for row in scenario["commercial_master_data"]["incoterms"]} == {
        "EXW",
        "FCA",
        "DAP",
    }
    assert {row["name"] for row in scenario["commercial_master_data"]["payment_terms"]} == {
        "30 Tage netto",
        "14 Tage 2 Prozent Skonto",
    }

    workstations = {row["id"]: row for row in scenario["capacity"]}
    operations = {row["name"] for row in scenario["capacity"]}
    employees = scenario["workforce"]["employees"]
    assert len(workstations) == 5
    assert len(employees) == 6
    assert all(row["workstation_type"] and row["hour_rate"] > 0 for row in workstations.values())
    assert all(
        (not employee["workstation"])
        or (
            employee["workstation"] in workstations
            and employee["operation"] in operations
        )
        for employee in employees
    )

    projects = {row["id"]: row for row in scenario["projects"]}
    assert projects["KOM-2027-4711"]["customer"] == "NordMarine Systems GmbH"
    assert {row["project_type"] for row in projects.values()} == {
        "Kundenkommission",
        "Interne Fertigung",
    }

    warehouses = {row["id"]: row for row in scenario["warehouses"]}
    assert len(warehouses) == 18
    assert warehouses["Kleinteilelager - OMD"]["parent"] == "Materiallager - OMD"
    assert warehouses["Palettenlager - OMD"]["parent"] == "Materiallager - OMD"
    assert all(
        row["parent"] == "All Warehouses - OMD" or row["parent"] in warehouses
        for row in warehouses.values()
    )


def test_read_tools_report_production_and_late_purchase_orders() -> None:
    initial = store.get()
    late = list_late_purchase_orders(initial)
    assert late["count"] == 1
    assert late["orders"][0]["id"] == "PO-2027-0088"
    assert list_production_orders(initial)["count"] == 0

    production = store.set_stage("production")
    active = list_production_orders(production)
    assert active["count"] == 1
    assert active["orders"][0]["work_order"] == "WO-2027-0042"


def test_assistant_exposes_grounding_tools_for_procurement_question() -> None:
    result = client.post(
        "/api/assistant/ask", json={"question": "Welche Bestellungen sind verspätet?"}
    ).json()
    assert "PO-2027-0088" in result["answer"]
    assert result["tools_used"] == ["list_late_purchase_orders"]
    assert any(source["reference"] == "PO-2027-0088" for source in result["sources"])


def test_mcp_server_exposes_approved_read_and_test_data_tools() -> None:
    async def inspect_server() -> tuple[list[str], dict[str, object] | None]:
        async with Client(mcp) as client:
            tools = await client.list_tools()
            result = await client.call_tool("list_late_purchase_orders", {})
            return [tool.name for tool in tools.tools], result.structured_content

    names, result = asyncio.run(inspect_server())
    assert names == [
        "list_production_orders",
        "list_late_purchase_orders",
        "get_order_status",
        "search_documents",
        "get_personal_daily_brief",
        "list_personal_ai_tools",
        "get_personal_action_context",
        "get_future_operating_model",
        "list_manufacturing_products",
        "get_bom_details",
        "get_inventory",
        "list_item_stock_movements",
        "list_materials_consumed",
        "list_test_data_types",
        "create_test_data",
        "import_test_data",
        "rollback_test_data_batch",
    ]
    assert result is not None
    assert result["count"] == 1


def test_dms_and_wiki_mcp_servers_expose_document_tools() -> None:
    async def inspect_server(server: Any) -> list[str]:
        async with Client(server) as mcp_client:
            tools = await mcp_client.list_tools()
            return [tool.name for tool in tools.tools]

    assert asyncio.run(inspect_server(dms_mcp)) == [
        "search_dms_documents",
        "get_dms_document",
        "list_recent_dms_documents",
        "list_dms_metadata",
        "search_dms_documents_semantic",
        "refresh_dms_vector_index",
        "get_dms_vector_index_status",
    ]
    assert asyncio.run(inspect_server(knowledge_mcp)) == [
        "list_documentation_sections",
        "search_process_documentation",
        "get_documentation_context",
        "get_documentation_page",
    ]


class FakeERPReadClient:
    configured = True

    def list_documents(
        self,
        doctype: str,
        *,
        fields: list[str],
        filters: list[list[object]] | None = None,
        order_by: str = "modified desc",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        del fields, filters, order_by, limit
        if doctype == "Work Order":
            return [
                {
                    "name": "WO-DEMO-IOX-24-01",
                    "production_item": "IOX-24",
                    "item_name": "Remote-I/O-Modul",
                    "qty": 4,
                    "produced_qty": 1,
                    "material_transferred_for_manufacturing": 2,
                    "status": "In Process",
                    "wip_warehouse": "Work In Progress - OMD",
                    "fg_warehouse": "Finished Goods - OMD",
                }
            ]
        if doctype == "BOM":
            return [
                {
                    "name": "BOM-IOX-24-001",
                    "item": "IOX-24",
                    "item_name": "Remote-I/O-Modul",
                    "quantity": 1,
                    "is_active": 1,
                    "is_default": 1,
                }
            ]
        if doctype == "Bin":
            return [
                {
                    "item_code": "PCB-IOX-24",
                    "warehouse": "Stores - OMD",
                    "actual_qty": 42,
                    "projected_qty": 42,
                }
            ]
        if doctype == "Stock Ledger Entry":
            return [
                {
                    "posting_date": "2026-10-30",
                    "item_code": "PCB-IOX-24",
                    "warehouse": "Work In Progress - OMD",
                    "actual_qty": -3,
                    "qty_after_transaction": 0,
                    "voucher_type": "Stock Entry",
                    "voucher_no": "MAT-STE-0001",
                }
            ]
        if doctype == "Stock Entry":
            return [
                {
                    "name": "MAT-STE-0001",
                    "posting_date": "2026-10-30",
                    "posting_time": "11:10:00",
                    "stock_entry_type": "Manufacture",
                    "purpose": "Manufacture",
                    "work_order": None,
                    "remarks": "demo",
                }
            ]
        raise AssertionError(f"Unexpected doctype: {doctype}")

    def get_document(self, doctype: str, name: str) -> dict[str, Any]:
        if doctype == "BOM":
            return {
                "name": name,
                "item": "IOX-24",
                "item_name": "Remote-I/O-Modul",
                "quantity": 1,
                "items": [{"item_code": "PCB-IOX-24", "item_name": "I/O-Platine", "qty": 1}],
                "operations": [
                    {
                        "sequence_id": 1,
                        "operation": "Elektronikmontage",
                        "workstation": "WS-ELEC",
                        "time_in_mins": 35,
                    }
                ],
            }
        if doctype == "Stock Entry":
            return {
                "name": name,
                "posting_date": "2026-10-30",
                "posting_time": "11:10:00",
                "bom_no": "BOM-IOX-24-001",
                "remarks": "demo",
                "items": [
                    {
                        "item_code": "PCB-IOX-24",
                        "item_name": "I/O-Platine",
                        "qty": 3,
                        "uom": "Nos",
                        "s_warehouse": "Work In Progress - OMD",
                        "is_finished_item": 0,
                    },
                    {
                        "item_code": "IOX-24",
                        "qty": 3,
                        "t_warehouse": "Finished Goods - OMD",
                        "is_finished_item": 1,
                    },
                ],
            }
        raise AssertionError(f"Unexpected document: {doctype} {name}")


def test_erp_read_service_covers_boms_inventory_and_stock_traceability() -> None:
    service = ERPReadService(Settings(), client=FakeERPReadClient())
    work_orders = service.list_production_orders()
    assert work_orders["orders"][0]["remaining_qty"] == 3
    assert work_orders["orders"][0]["progress_percent"] == 25.0
    assert work_orders["orders"][0]["material_transfer_percent"] == 50.0
    assert service.list_products()["products"][0]["item"] == "IOX-24"
    assert service.get_bom("IOX-24")["bom"]["operations"][0]["time_in_mins"] == 35
    assert service.get_inventory("PCB-IOX-24")["balances"][0]["actual_qty"] == 42
    movements = service.list_stock_movements("PCB-IOX-24", "2026-10-30", "2026-10-30")
    assert movements["movements"][0]["actual_qty"] == -3
    consumed = service.list_materials_consumed("2026-10-30")
    assert consumed["totals"] == [{"item_code": "PCB-IOX-24", "qty": 3.0}]


def test_knowledge_service_searches_and_restricts_paths(tmp_path: Path) -> None:
    (tmp_path / "processes").mkdir()
    (tmp_path / "processes" / "production.md").write_text(
        "# Produktion\n\n## Materialbuchung\n\n"
        "Materialverbrauch wird über Stock Entry gebucht.",
        encoding="utf-8",
    )
    service = KnowledgeService(tmp_path, "http://localhost:8001")
    result = service.search("Wie funktioniert die Materialverbrauch-Buchung?")
    assert result["results"][0]["path"] == "processes/production.md"
    assert result["results"][0]["section"] == "Materialbuchung"
    assert (
        result["results"][0]["url"]
        == "http://localhost:8001/processes/production/#materialbuchung"
    )
    assert result["answer_instruction"].startswith("Fasse nur")
    context = service.get_context("Wo wird der Materialverbrauch gebucht?")
    assert context["context"][0]["url"].endswith("#materialbuchung")
    page = service.get_page("processes/production.md")
    assert "Stock Entry" in page["content"]
    assert page["url"] == "http://localhost:8001/processes/production/"


def test_paperless_client_returns_bounded_metadata(monkeypatch: Any) -> None:
    service = PaperlessClient(Settings(paperless_api_token="test-token"))
    monkeypatch.setattr(
        service,
        "_get",
        lambda path, params=None: {
            "count": 1,
            "results": [
                {
                    "id": 7,
                    "title": "SCU-100 Prüfplan",
                    "tags": [3],
                    "content": "must not be returned in full",
                    "__search_hit__": {"highlights": "Text <span>SCU-100</span>"},
                }
            ],
        },
    )
    result = service.search_documents("SCU-100", 5)
    assert result["documents"][0]["snippet"] == "Text SCU-100"
    assert result["documents"][0]["url"] == "http://localhost:8010/documents/7/details"
    assert "content" not in result["documents"][0]


class FakeDocumentClient:
    configured = True

    def __init__(self) -> None:
        self.documents: dict[tuple[str, str], dict[str, Any]] = {}
        self.deleted: list[tuple[str, str]] = []
        self.counter = 0

    def find_document(self, doctype: str, field: str, value: object) -> str | None:
        for (stored_doctype, name), document in self.documents.items():
            if stored_doctype == doctype and document.get(field) == value:
                return name
        return None

    def create_document(self, doctype: str, values: dict[str, Any]) -> dict[str, Any]:
        self.counter += 1
        name = f"TEST-{self.counter:05d}"
        self.documents[(doctype, name)] = dict(values)
        return {"name": name, **values}

    def delete_document(self, doctype: str, name: str) -> None:
        self.documents.pop((doctype, name))
        self.deleted.append((doctype, name))


def master_data_service(tmp_path: Path) -> tuple[MasterDataService, FakeDocumentClient]:
    fake = FakeDocumentClient()
    local_settings = Settings(
        mcp_write_enabled=True,
        mcp_max_write_records=3,
        mcp_audit_file=tmp_path / "audit.jsonl",
    )
    return (
        MasterDataService(
            local_settings, client=fake, audit=AuditLog(local_settings.mcp_audit_file)
        ),
        fake,
    )


def test_master_data_catalog_covers_people_time_and_manufacturing(tmp_path: Path) -> None:
    service, _ = master_data_service(tmp_path)
    result = service.list_types()
    names = {entity["entity_type"] for entity in result["entities"]}
    assert result["count"] >= 22
    assert {
        "employees",
        "timesheets",
        "workstations",
        "suppliers",
        "items",
        "projects",
        "project_types",
        "warehouses",
        "warehouse_types",
    } <= names
    entities = {entity["entity_type"]: entity for entity in result["entities"]}
    assert "project_type" in entities["projects"]["allowed_fields"]
    assert "warehouse_type" in entities["warehouses"]["allowed_fields"]


def test_create_test_data_requires_preview_then_confirmation(tmp_path: Path) -> None:
    service, fake = master_data_service(tmp_path)
    records = [{"supplier_name": "TEST-Lieferant Nord"}]

    preview = service.create("suppliers", records)
    assert preview["mode"] == "preview"
    assert preview["records"][0]["supplier_type"] == "Company"
    assert not fake.documents

    result = service.create("suppliers", records, confirm=True)
    assert result["status"] == "created"
    assert len(result["created"]) == 1
    assert result["batch_id"]

    duplicate = service.create("suppliers", records, confirm=True)
    assert duplicate["created"] == []
    assert duplicate["skipped"][0]["reason"] == "duplicate"


def test_csv_and_json_imports_validate_and_normalize(tmp_path: Path) -> None:
    service, _ = master_data_service(tmp_path)
    csv_preview = service.import_content(
        "workstations",
        "workstation_name,production_capacity,status\nTEST-MONT-9,3,Production\n",
    )
    assert csv_preview["data_format"] == "csv"
    assert csv_preview["records"][0]["production_capacity"] == 3

    json_preview = service.import_content(
        "timesheets",
        '[{"employee":"HR-EMP-00001","time_logs":[{"activity_type":"Fertigung",'
        '"from_time":"2026-10-30 08:00:00","hours":8}]}]',
        data_format="json",
    )
    assert json_preview["records"][0]["time_logs"][0]["hours"] == 8


def test_unknown_fields_and_record_limit_are_rejected(tmp_path: Path) -> None:
    service, _ = master_data_service(tmp_path)
    try:
        service.create("suppliers", [{"supplier_name": "Test", "owner": "Administrator"}])
    except MasterDataError as exc:
        assert "unsupported fields" in str(exc)
    else:
        raise AssertionError("Unsupported fields were accepted")

    try:
        service.create("uoms", [{"uom_name": str(index)} for index in range(4)])
    except MasterDataError as exc:
        assert "At most 3" in str(exc)
    else:
        raise AssertionError("Record limit was not enforced")


def test_only_audited_batch_can_be_rolled_back(tmp_path: Path) -> None:
    service, fake = master_data_service(tmp_path)
    created = service.create("activity_types", [{"activity_type": "TEST-Ruestzeit"}], confirm=True)
    batch_id = created["batch_id"]

    preview = service.rollback(batch_id)
    assert preview["requires_confirmation"] is True
    assert fake.documents

    result = service.rollback(batch_id, confirm=True)
    assert result["status"] == "rolled_back"
    assert not fake.documents
    assert fake.deleted == [("Activity Type", "TEST-00001")]
