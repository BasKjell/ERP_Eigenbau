from app.main import app, store
from fastapi.testclient import TestClient

client = TestClient(app)


def setup_function() -> None:
    store.reset()


def test_finance_page_and_management_dashboard() -> None:
    page = client.get("/finance")
    assert page.status_code == 200
    assert "FLOWFIN" in page.text
    assert "Kontrollierte Test-Schnittstellen" in page.text

    dashboard = client.get("/api/finance/dashboard")
    assert dashboard.status_code == 200
    data = dashboard.json()
    assert data["data_classification"] == "DEMO"
    assert data["metrics"]["production_order_value"] == 255500
    assert data["metrics"]["production_weighted_revenue"] == 223375
    assert data["metrics"]["backlog_value"] == 371000
    assert len(data["revenue_by_month"]) == 5
    assert len(data["cash_forecast"]) == 49
    assert data["cash_forecast"][0]["month"] == "2024-11"
    assert data["cash_forecast"][-1]["month"] == "2028-11"
    assert data["metrics"]["cash_balance"] == 302600
    assert {item["mode"] for item in data["integrations"]} == {"test"}
    assert all(not item["external_connection"] for item in data["integrations"])


def test_budget_forecast_updates_and_recalculates_variance() -> None:
    result = client.post(
        "/api/finance/budgets/BUD-ENG-2027/forecast",
        json={"actor_id": "demo36", "forecast": 475000},
    )
    assert result.status_code == 200
    assert result.json()["variance"] == 5000
    assert result.json()["updated_by"] == "demo36"

    dashboard = client.get("/api/finance/dashboard").json()
    budget = next(item for item in dashboard["budgets"] if item["id"] == "BUD-ENG-2027")
    assert budget["forecast"] == 475000
    assert dashboard["audit"][0]["action"] == "budget_forecast_updated"


def test_expense_workflow_enforces_four_eyes_principle() -> None:
    created = client.post(
        "/api/finance/expenses",
        json={
            "actor_id": "demo37",
            "description": "Testadapter für Kundenabnahme",
            "category": "Prüfmittel",
            "cost_center": "CC-ENG",
            "project_id": "KOM-2027-4711",
            "amount": 750.5,
            "receipt_reference": "DMS-TEST-001",
        },
    )
    assert created.status_code == 200
    assert created.json()["status"] == "pending"
    expense_id = created.json()["id"]

    self_approval = client.post(
        f"/api/finance/expenses/{expense_id}/decision",
        json={"actor_id": "demo37", "decision": "approved", "comment": "selbst"},
    )
    assert self_approval.status_code == 409

    approved = client.post(
        f"/api/finance/expenses/{expense_id}/decision",
        json={
            "actor_id": "demo40",
            "decision": "approved",
            "comment": "Sachlich geprüft",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["decision"]["actor_id"] == "demo40"


def test_asset_register_calculates_monthly_depreciation() -> None:
    result = client.post(
        "/api/finance/assets",
        json={
            "actor_id": "demo36",
            "name": "Mobiler Protokollanalysator",
            "asset_class": "Technische Anlagen",
            "cost_center": "CC-ENG",
            "acquisition_date": "2026-11-04",
            "acquisition_cost": 12000,
            "useful_life_months": 60,
        },
    )
    assert result.status_code == 200
    assert result.json()["monthly_depreciation"] == 200
    assert result.json()["source"] == "FLOWFIN"


def test_datev_adapter_requires_preview_and_never_transmits() -> None:
    preview = client.post(
        "/api/finance/integrations/datev",
        json={"actor_id": "demo36", "key": "2026-11", "confirm": False},
    )
    assert preview.status_code == 200
    assert preview.json()["status"] == "preview"
    assert preview.json()["mode"] == "test"
    assert preview.json()["transmitted"] is False

    invalid = client.post(
        "/api/finance/integrations/datev",
        json={
            "actor_id": "demo36",
            "key": "2026-11",
            "confirm": True,
            "confirmation_token": "invalid-token",
        },
    )
    assert invalid.status_code == 409

    run = client.post(
        "/api/finance/integrations/datev",
        json={
            "actor_id": "demo36",
            "key": "2026-11",
            "confirm": True,
            "confirmation_token": preview.json()["confirmation_token"],
        },
    )
    assert run.status_code == 200
    assert run.json()["status"] == "simulated"
    assert run.json()["mode"] == "test"
    assert run.json()["transmitted"] is False
    assert run.json()["external_reference"].startswith("SIM-DATEV-")


def test_bank_and_einvoice_adapters_are_test_only() -> None:
    bank_preview = client.post(
        "/api/finance/integrations/bank",
        json={"actor_id": "demo36", "key": "2026-11-30", "confirm": False},
    )
    assert bank_preview.status_code == 200
    assert bank_preview.json()["record_count"] == 2
    assert bank_preview.json()["amount"] == 25600
    assert bank_preview.json()["transmitted"] is False

    validation = client.post(
        "/api/finance/integrations/e-invoice/validate",
        json={
            "actor_id": "demo36",
            "invoice_id": "INV-DEMO-001",
            "invoice_format": "xrechnung",
        },
    )
    assert validation.status_code == 200
    assert validation.json()["status"] == "simulated_valid"
    assert validation.json()["mode"] == "test"
    assert validation.json()["transmitted"] is False
    assert all(item["status"] != "failed" for item in validation.json()["checks"])


def test_finance_reset_restores_seed_and_purge_removes_demo_records() -> None:
    client.post(
        "/api/finance/budgets/BUD-ENG-2027/forecast",
        json={"actor_id": "demo36", "forecast": 1},
    )
    restored = client.post("/api/finance/reset")
    assert restored.status_code == 200
    budget = next(
        item for item in restored.json()["budgets"] if item["id"] == "BUD-ENG-2027"
    )
    assert budget["forecast"] == 492000

    purged = client.post("/api/demo/purge")
    assert purged.status_code == 200
    assert purged.json()["finance"]["orders"] == []
    assert purged.json()["finance"]["assets"] == []
