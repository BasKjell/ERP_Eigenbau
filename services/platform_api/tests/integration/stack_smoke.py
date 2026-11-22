"""Cross-container smoke checks for API, ERP/DMS adapters, MES, HR, MCP and wiki."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import time
import urllib.error
import urllib.request
from typing import Any

from mcp import Client

API_URL = os.getenv("TEST_API_URL", "http://platform-api:8080").rstrip("/")
DOCS_URL = os.getenv("TEST_DOCS_URL", "http://docs:8000").rstrip("/")


def request(path: str) -> tuple[Any, dict[str, str], int]:
    with urllib.request.urlopen(f"{API_URL}{path}", timeout=5) as response:
        content_type = response.headers.get_content_type()
        payload = response.read()
        body = json.loads(payload) if content_type == "application/json" else payload
        headers = {key.casefold(): value for key, value in response.headers.items()}
        return body, headers, response.status


def post(path: str, payload: dict[str, Any]) -> tuple[Any, dict[str, str], int]:
    encoded = json.dumps(payload).encode()
    call = urllib.request.Request(
        f"{API_URL}{path}",
        data=encoded,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(call, timeout=5) as response:
        body = json.loads(response.read())
        headers = {key.casefold(): value for key, value in response.headers.items()}
        return body, headers, response.status


def wait_for(url: str, timeout: int = 60) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status < 500:
                    return
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
        time.sleep(1)
    raise AssertionError(f"{url} was not ready: {last_error}")


async def check_mcp_contracts() -> None:
    async with Client("http://platform-mcp:8090/mcp") as client:
        tools = await client.list_tools()
        assert "list_production_orders" in {tool.name for tool in tools.tools}
        assert "get_personal_daily_brief" in {tool.name for tool in tools.tools}
        assert "get_future_operating_model" in {tool.name for tool in tools.tools}
        production = await client.call_tool("list_production_orders", {})
        assert production.structured_content is not None
        assert production.structured_content["orders"][0]["name"] == "WO-CI-0001"
        assert production.structured_content["orders"][0]["remaining_qty"] == 3

    async with Client("http://dms-mcp-ci:8091/mcp") as client:
        result = await client.call_tool(
            "search_dms_documents", {"query": "SCU-100", "max_results": 5}
        )
        assert result.structured_content is not None
        assert result.structured_content["documents"][0]["id"] == 4711

    async with Client("http://knowledge-mcp:8092/mcp") as client:
        tools = await client.list_tools()
        assert "get_documentation_context" in {tool.name for tool in tools.tools}
        result = await client.call_tool(
            "get_documentation_context",
            {"question": "Wie funktioniert die Live-Readiness?", "max_results": 5},
        )
        assert result.structured_content is not None
        assert result.structured_content["count"] >= 1
        assert result.structured_content["context"][0]["url"].startswith(
            "http://localhost:8001/"
        )


def main() -> None:
    wait_for(f"{API_URL}/health")
    wait_for(DOCS_URL)

    readiness, headers, status = request("/ready")
    assert status == 200, readiness
    assert readiness["status"] == "ready", readiness
    assert all(
        check["ok"] for check in readiness["checks"] if check["required"]
    ), readiness
    assert headers["x-content-type-options"] == "nosniff"

    integrations, _, _ = request("/api/integrations")
    assert {item["name"] for item in integrations} == {
        "ERPNext",
        "Paperless-ngx",
        "Redmine",
    }
    assert all(item["configured"] and item["reachable"] for item in integrations)

    work, _, _ = request("/api/work/dashboard")
    assert work["mode"] == "live", work
    assert work["issues"][0]["key"] == "#101"
    assert work["wiki"][0]["title"] == "SCU-100_Requirements"
    live_issue, _, _ = post(
        "/api/work/issues",
        {
            "subject": "CI Redmine Ticket",
            "description": "Integrationstest",
            "priority": "Normal",
            "assignee": "CI Engineer",
        },
    )
    assert live_issue["key"] == "#105"

    search, _, _ = request("/api/documents/search?q=SCU-100%20%26%20Plan")
    assert search["mode"] == "live", search
    assert search["results"][0]["id"] == 4711
    assert search["results"][0]["title"] == "SCU-100 & Plan Montageanweisung"

    mes_documents, _, _ = request("/api/mes/jobs/JC-2027-0130/documents")
    assert mes_documents["dms_search"]["mode"] == "live", mes_documents
    assert mes_documents["integration"]["reachable"] is True

    hr_dashboard, _, _ = request(
        "/api/hr/dashboard?employee_id=DEMO-EMP-006&selected_date=2026-11-03"
    )
    assert hr_dashboard["is_manager"] is True
    assert len(hr_dashboard["team"]) == 6
    assert hr_dashboard["metrics"]["team_pending_approvals"] == 3

    desksharing, _, _ = request(
        "/api/desksharing/dashboard?user_id=USR-001&booking_date=2027-01-20&site_id=BER&slot=full_day"
    )
    assert desksharing["metrics"]["total_desks"] == 50
    assert len(desksharing["demo_users"]) == 50
    desk_booking, _, _ = post(
        "/api/desksharing/bookings",
        {
            "user_id": "USR-001",
            "desk_id": "BER-D006",
            "date": "2027-01-20",
            "slot": "full_day",
            "note": "CI-Integration",
        },
    )
    assert desk_booking["status"] == "booked"
    checked_in, _, _ = post(
        f"/api/desksharing/bookings/{desk_booking['id']}/check-in",
        {"actor_id": "USR-001"},
    )
    assert checked_in["status"] == "checked_in"

    finance, _, _ = request("/api/finance/dashboard")
    assert finance["metrics"]["production_order_value"] == 255500
    assert finance["metrics"]["production_weighted_revenue"] == 223375
    assert all(item["mode"] == "test" for item in finance["integrations"])
    datev_preview, _, _ = post(
        "/api/finance/integrations/datev",
        {"actor_id": "demo36", "key": "2026-11", "confirm": False},
    )
    assert datev_preview["transmitted"] is False
    datev_run, _, _ = post(
        "/api/finance/integrations/datev",
        {
            "actor_id": "demo36",
            "key": "2026-11",
            "confirm": True,
            "confirmation_token": datev_preview["confirmation_token"],
        },
    )
    assert datev_run["status"] == "simulated"
    assert datev_run["transmitted"] is False

    hr_preview, _, _ = post(
        "/api/hr/export/erp",
        {"employee_id": "DEMO-EMP-001", "date": "2026-11-02", "confirm": False},
    )
    assert hr_preview["status"] == "preview"
    assert hr_preview["mode"] == "live"
    hr_export, _, _ = post(
        "/api/hr/export/erp",
        {
            "employee_id": "DEMO-EMP-001",
            "date": "2026-11-02",
            "confirm": True,
            "confirmation_token": hr_preview["confirmation_token"],
        },
    )
    assert hr_export["export"]["erp_reference"] == "TS-HR-CI-0001"
    repeated_export, _, _ = post(
        "/api/hr/export/erp",
        {"employee_id": "DEMO-EMP-001", "date": "2026-11-02", "confirm": False},
    )
    assert repeated_export["status"] == "already_exported"

    recruiting, _, _ = request("/api/hr/recruiting?actor_id=HR-USER-001")
    assert recruiting["metrics"]["active_applications"] == 2
    assert recruiting["dms"]["access_group"] == "DMS-Bereich-HR-Recruiting"
    application, _, _ = post(
        "/api/hr/recruiting/applications",
        {
            "actor_id": "HR-USER-001",
            "vacancy_id": "VAC-0001",
            "candidate_name": "CI Bewerber",
            "email": "ci.bewerber@example.invalid",
            "phone": "",
            "source": "Integrationstest",
        },
    )
    assert application["stage"] == "new"
    moved, _, _ = post(
        f"/api/hr/recruiting/applications/{application['id']}/stage",
        {"actor_id": "HR-USER-001", "stage": "screening", "note": "CI"},
    )
    assert moved["stage"] == "screening"

    payroll_preview, _, _ = post(
        "/api/hr/payroll/PAY-2026-10/prepare", {"actor_id": "HR-USER-001"}
    )
    assert payroll_preview["employee_count"] == 6
    payroll_approved, _, _ = post(
        "/api/hr/payroll/PAY-2026-10/approve",
        {
            "actor_id": "HR-USER-002",
            "confirmation_token": payroll_preview["token"],
        },
    )
    run_id = payroll_approved["run"]["id"]
    payroll_delivered, _, _ = post(
        f"/api/hr/payroll/runs/{run_id}/deliver", {"actor_id": "HR-USER-002"}
    )
    assert payroll_delivered["run"]["erp_reference"] == "JV-PAYROLL-CI-0001"
    payslip, payslip_headers, _ = request(
        f"/api/hr/payroll/runs/{run_id}/payslips/DEMO-EMP-001?actor_id=HR-USER-001"
    )
    assert payslip.startswith(b"%PDF")
    assert payslip_headers["content-disposition"].startswith("inline;")

    document, document_headers, _ = request("/api/documents/DOC-WI-100")
    assert document.startswith(b"%PDF")
    assert document_headers["content-disposition"].startswith("inline;")

    with urllib.request.urlopen(DOCS_URL, timeout=5) as response:
        wiki = response.read().decode("utf-8")
    assert "Open Manufacturing Platform" in wiki

    for host, port in (
        ("platform-mcp", 8090),
        ("dms-mcp-ci", 8091),
        ("knowledge-mcp", 8092),
    ):
        with socket.create_connection((host, port), timeout=5):
            pass
    asyncio.run(check_mcp_contracts())

    purged, _, _ = post("/api/demo/purge", {})
    assert purged["scenario"]["data_status"] == "purged"
    assert purged["documents"] == []
    assert purged["mes"]["jobs"] == []
    assert purged["hr"]["employees"] == []
    assert purged["work"]["requirements"] == []
    assert purged["finance"]["orders"] == []
    restored, _, _ = post("/api/demo/reset", {})
    assert restored["documents"]
    assert restored["mes"]["jobs"]
    assert restored["hr"]["employees"]
    assert restored["work"]["requirements"]
    assert restored["finance"]["orders"]
    print("Cross-system integration checks including demo lifecycle passed")


if __name__ == "__main__":
    main()
