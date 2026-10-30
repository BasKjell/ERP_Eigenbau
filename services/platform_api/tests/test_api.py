import asyncio
from pathlib import Path
from typing import Any

from app.business_tools import list_late_purchase_orders, list_production_orders
from app.config import Settings, settings
from app.main import app, store
from app.master_data import AuditLog, MasterDataError, MasterDataService
from app.mcp_server import mcp
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
    }


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
        "list_test_data_types",
        "create_test_data",
        "import_test_data",
        "rollback_test_data_batch",
    ]
    assert result is not None
    assert result["count"] == 1


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
        MasterDataService(local_settings, client=fake, audit=AuditLog(local_settings.mcp_audit_file)),
        fake,
    )


def test_master_data_catalog_covers_people_time_and_manufacturing(tmp_path: Path) -> None:
    service, _ = master_data_service(tmp_path)
    result = service.list_types()
    names = {entity["entity_type"] for entity in result["entities"]}
    assert result["count"] >= 20
    assert {"employees", "timesheets", "workstations", "suppliers", "items"} <= names


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
    created = service.create(
        "activity_types", [{"activity_type": "TEST-Ruestzeit"}], confirm=True
    )
    batch_id = created["batch_id"]

    preview = service.rollback(batch_id)
    assert preview["requires_confirmation"] is True
    assert fake.documents

    result = service.rollback(batch_id, confirm=True)
    assert result["status"] == "rolled_back"
    assert not fake.documents
    assert fake.deleted == [("Activity Type", "TEST-00001")]
