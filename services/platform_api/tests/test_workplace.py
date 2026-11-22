from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.main import app, store, workplace_service
from app.mcp_server import mcp
from app.store import ScenarioStore
from fastapi.testclient import TestClient
from mcp import Client

client = TestClient(app)


def setup_function() -> None:
    store.reset()


def test_procurement_brief_prioritizes_supplier_risk_and_reports_80_percent() -> None:
    brief = workplace_service.daily_brief("USR-006", "2026-11-05")

    assert brief["role"]["key"] == "procurement"
    assert brief["user"]["name"] == "Felix Hoffmann"
    assert brief["kpis"][0]["value"] == "80 %"
    assert brief["actions"][0]["id"] == "supplier-PO-2027-0088"
    assert brief["actions"][0]["priority"] == "critical"
    assert any(item["id"] == "common-desk" for item in brief["actions"])
    assert {item["id"] for item in brief["mcp"]["connected_servers"]} == {
        "platform",
        "dms",
        "wiki",
    }


def test_engineering_brief_combines_task_requirement_and_review_context() -> None:
    brief = workplace_service.daily_brief("USR-045", "2026-11-05")

    assert brief["role"]["key"] == "engineering"
    assert any(item["id"] == "issue-101" for item in brief["actions"])
    assert any(item["id"] == "review-comment" for item in brief["actions"])
    assert any(agent["id"] == "requirements" for agent in brief["agents"])
    tools = {item["name"]: item for item in brief["mcp"]["tools"]}
    assert tools["get_personal_daily_brief"]["status"] == "available"
    assert tools["review_decision"]["status"] == "planned"


def test_personal_action_context_is_scoped_to_users_daily_actions() -> None:
    context = workplace_service.action_context(
        "supplier-PO-2027-0088", "USR-006", "2026-11-05"
    )

    assert context["action"]["source"] == "FLOWERP"
    assert "explizite Bestätigung" in context["guardrail"]


def test_workplace_api_and_mcp_expose_same_daily_brief() -> None:
    response = client.get(
        "/api/workplace/today",
        params={"user_id": "USR-006", "selected_date": "2026-11-05"},
    )
    assert response.status_code == 200
    assert response.json()["role"]["key"] == "procurement"
    profiles = client.get("/api/workplace/profiles").json()
    assert profiles["count"] == 50

    async def call_mcp() -> dict[str, object] | None:
        async with Client(mcp) as mcp_client:
            result = await mcp_client.call_tool(
                "get_personal_daily_brief",
                {"user_id": "USR-006", "selected_date": "2026-11-05"},
            )
            return result.structured_content

    mcp_result = asyncio.run(call_mcp())
    assert mcp_result is not None
    assert mcp_result["kpis"][0]["value"] == "80 %"


def test_future_operating_model_keeps_human_decisions_and_agent_limits_visible() -> None:
    model = workplace_service.future_operating_model()

    assert model["horizon"] == "12 bis 24 Monate"
    assert sum(item["share"] for item in model["scenario_mix"]) == 100
    assert model["status"].startswith("Zielbild")
    assert {item["level"] for item in model["autonomy_levels"]} == {
        "A0",
        "A1",
        "A2",
        "A3",
        "A4",
    }
    assert any(
        "Requirement" in item["human_decision"]
        or "Review" in item["human_decision"]
        for item in model["decision_inbox"]
    )
    assert all(item["owner"] for item in model["agent_register"])

    response = client.get("/api/workplace/future-model")
    assert response.status_code == 200
    assert response.json()["agent_register"][1]["autonomy"] == "A1"

    async def call_mcp() -> dict[str, object] | None:
        async with Client(mcp) as mcp_client:
            result = await mcp_client.call_tool("get_future_operating_model", {})
            return result.structured_content

    mcp_result = asyncio.run(call_mcp())
    assert mcp_result is not None
    assert mcp_result["scenario_mix"][0]["share"] == 55


def test_schema_upgrade_adds_workplace_history_without_resetting_progress(
    tmp_path: Path,
) -> None:
    seed = json.loads(store.seed_file.read_text(encoding="utf-8"))
    state = json.loads(store.seed_file.read_text(encoding="utf-8"))
    state.pop("workplace")
    state["order"]["status"] = "Fortschritt behalten"
    seed_path = tmp_path / "seed.json"
    data_path = tmp_path / "state.json"
    seed_path.write_text(json.dumps(seed), encoding="utf-8")
    data_path.write_text(json.dumps(state), encoding="utf-8")

    upgraded = ScenarioStore(data_path, seed_path).get()

    assert len(upgraded["workplace"]["supplier_delivery_history"]) == 5
    assert upgraded["order"]["status"] == "Fortschritt behalten"
