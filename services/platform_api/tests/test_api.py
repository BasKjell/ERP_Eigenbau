import asyncio

from app.business_tools import list_late_purchase_orders, list_production_orders
from app.config import settings
from app.main import app, store
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


def test_mcp_server_exposes_only_the_approved_read_tools() -> None:
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
    ]
    assert result is not None
    assert result["count"] == 1
