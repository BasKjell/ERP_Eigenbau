from app.config import Settings
from app.finance import FinanceService
from app.main import app, store
from app.mes import MesService
from app.reporting import LiveReportingService
from fastapi.testclient import TestClient

client = TestClient(app)


def setup_function() -> None:
    store.reset()


def test_live_reporting_requires_internal_token() -> None:
    assert client.get("/api/reporting/live").status_code == 401
    response = client.get(
        "/api/reporting/live",
        headers={"X-Flow-Reporting-Token": "local-reporting-token-change-before-network-use"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["cash"][0]["time"] == "2024-11-01"
    assert data["cash"][-1]["time"] == "2028-11-01"
    assert data["executive_kpis"][0]["production_order_value"] == 255500
    assert data["production_wip"][0]["current_operation"] == "Elektronikmontage"
    assert {item["system"] for item in data["sources"]} == {"FLOWFIN", "FLOWMES", "ERPNext"}


def test_reporting_projection_reflects_current_mes_state() -> None:
    settings = Settings(erpnext_username="", erpnext_password="")
    service = LiveReportingService(
        FinanceService(store), MesService(store, settings), settings, cache_seconds=0
    )
    before = service.snapshot()
    assert before["production_wip"][0]["current_operation"] == "Elektronikmontage"
    MesService(store, settings).start("JC-2027-0130", "DEMO-EMP-002")
    after = service.snapshot()
    assert after["production_wip"][0]["operation_status"] == "in_progress"
