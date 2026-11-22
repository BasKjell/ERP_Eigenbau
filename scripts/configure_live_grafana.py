#!/usr/bin/env python3
"""Switch all management dashboards to the token-protected live API datasource."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "deployment" / "grafana" / "provisioning" / "dashboards" / "json"
DATASOURCE = {"type": "yesoreyeram-infinity-datasource", "uid": "platform-live-api"}
URL = "http://platform-api:8080/api/reporting/live"


def columns(*values: tuple[str, str, str]) -> list[dict[str, str]]:
    return [
        {"selector": selector, "text": title, "type": field_type}
        for selector, title, field_type in values
    ]


MAPPINGS: dict[str, dict[int, tuple[str, str, list[dict[str, str]]]]] = {
    "management-executive.json": {
        1: ("executive_kpis", "table", columns(("production_order_value", "Auftragswert Produktion", "number"))),
        2: ("executive_kpis", "table", columns(("production_weighted_revenue", "Gewichteter Produktionsumsatz", "number"))),
        3: ("executive_kpis", "table", columns(("weighted_backlog", "Gewichteter Backlog", "number"))),
        4: ("executive_kpis", "table", columns(("expected_margin", "Erwartete Marge", "number"))),
        5: ("executive_kpis", "table", columns(("orders_at_risk", "Gefährdete Aufträge", "number"))),
        6: ("monthly_revenue", "timeseries", columns(("time", "time", "timestamp"), ("order_value", "Brutto-Auftragswert", "number"), ("weighted_revenue", "Gewichteter Umsatz", "number"))),
        7: ("budget_status", "table", columns(("budget_name", "budget_name", "string"), ("forecast_usage_percent", "forecast_usage_percent", "number"))),
        8: ("orders", "table", columns(("order_id", "order_id", "string"), ("project_id", "project_id", "string"), ("customer", "customer", "string"), ("product", "product", "string"), ("stage", "stage", "string"), ("progress", "progress", "number"), ("order_value", "order_value", "number"), ("weighted_revenue", "weighted_revenue", "number"), ("expected_margin", "expected_margin", "number"), ("expected_margin_percent", "expected_margin_percent", "number"), ("expected_invoice_date", "expected_invoice_date", "timestamp"), ("risk", "risk", "string"))),
    },
    "management-production-live.json": {
        1: ("production_kpis", "table", columns(("active_work_orders", "Aktive Fertigungsaufträge", "number"))),
        2: ("production_kpis", "table", columns(("production_order_value", "Wert im Umlauf", "number"))),
        3: ("production_kpis", "table", columns(("blocked_work_orders", "Blockiert", "number"))),
        4: ("production_kpis", "table", columns(("orders_at_risk", "Terminrisiken", "number"))),
        5: ("production_wip", "table", columns(("work_order_id", "work_order_id", "string"), ("sales_order_id", "sales_order_id", "string"), ("project_id", "project_id", "string"), ("customer", "customer", "string"), ("product", "product", "string"), ("quantity", "quantity", "number"), ("current_operation", "current_operation", "string"), ("operation_status", "operation_status", "string"), ("workstation", "workstation", "string"), ("assigned_employee", "assigned_employee", "string"), ("completed_operations", "completed_operations", "number"), ("operation_count", "operation_count", "number"), ("progress_percent", "progress_percent", "number"), ("due_date", "due_date", "timestamp"), ("risk", "risk", "string"), ("order_value", "order_value", "number"))),
        6: ("operation_summary", "table", columns(("current_operation", "current_operation", "string"), ("orders", "Aufträge", "number"))),
        7: ("workstation_load", "table", columns(("workstation", "workstation", "string"), ("remaining_planned_minutes", "remaining_planned_minutes", "number"))),
        8: ("workstation_load", "table", columns(("workstation", "workstation", "string"), ("open_operations", "open_operations", "number"), ("active_operations", "active_operations", "number"), ("blocked_operations", "blocked_operations", "number"))),
    },
    "management-crm-pipeline.json": {
        1: ("crm_kpis", "table", columns(("gross_pipeline", "Brutto-Pipeline", "number"))),
        2: ("crm_kpis", "table", columns(("weighted_pipeline", "Gewichtete Pipeline", "number"))),
        3: ("crm_kpis", "table", columns(("open_opportunities", "Opportunities", "number"))),
        4: ("crm_kpis", "table", columns(("average_probability", "Ø Wahrscheinlichkeit", "number"))),
        5: ("crm_yearly", "timeseries", columns(("time", "time", "timestamp"), ("pipeline_value", "Brutto-Pipeline", "number"), ("weighted_pipeline", "Gewichtete Pipeline", "number"))),
        6: ("crm_stage", "table", columns(("stage", "stage", "string"), ("weighted_value", "weighted_value", "number"))),
        7: ("crm_opportunities", "table", columns(("opportunity_id", "opportunity_id", "string"), ("opportunity_name", "opportunity_name", "string"), ("customer", "customer", "string"), ("product", "product", "string"), ("stage", "stage", "string"), ("sales_owner", "sales_owner", "string"), ("expected_close_date", "expected_close_date", "timestamp"), ("close_year", "close_year", "number"), ("opportunity_value", "opportunity_value", "number"), ("probability", "probability", "number"), ("weighted_value", "weighted_value", "number"), ("source", "source", "string"), ("region", "region", "string"))),
    },
    "management-project-cash.json": {
        1: ("cash", "timeseries", columns(("time", "time", "timestamp"), ("liquidity", "Liquidität", "number"), ("inflow", "Einzahlungen", "number"), ("outflow", "Auszahlungen", "number"))),
        2: ("open_items", "table", columns(("type", "item_type", "string"), ("document", "document_reference", "string"), ("partner", "partner", "string"), ("due_date", "due_date", "timestamp"), ("amount", "amount", "number"), ("status", "status", "string"), ("project_id", "project_id", "string"))),
        3: ("project_profitability", "table", columns(("project_id", "project_id", "string"), ("order_id", "order_id", "string"), ("customer", "customer", "string"), ("product", "product", "string"), ("progress", "progress", "number"), ("order_value", "order_value", "number"), ("actual_cost", "actual_cost", "number"), ("forecast_cost", "forecast_cost", "number"), ("expected_margin", "expected_margin", "number"), ("expected_margin_percent", "expected_margin_percent", "number"), ("risk", "risk", "string"))),
    },
    "management-innovation-quality.json": {
        1: ("quality_monthly", "timeseries", columns(("time", "time", "timestamp"), ("Nacharbeit", "Nacharbeit", "number"), ("Ausschuss", "Ausschuss", "number"), ("Prüfung", "Prüfung", "number"), ("Gewährleistung", "Gewährleistung", "number"))),
        2: ("innovation_portfolio", "table", columns(("portfolio_type", "portfolio_type", "string"), ("portfolio_id", "portfolio_id", "string"), ("name", "name", "string"), ("owner_name", "owner_name", "string"), ("status", "status", "string"), ("actual_cost", "actual_cost", "number"), ("forecast_cost", "forecast_cost", "number"), ("target_date", "target_date", "timestamp"), ("risk", "risk", "string"))),
        3: ("quality_costs", "table", columns(("id", "quality_id", "string"), ("category", "category", "string"), ("project_id", "project_id", "string"), ("amount", "amount", "number"), ("period", "period", "timestamp"))),
    },
}


def query(dataset: str, output_format: str, selected_columns: list[dict[str, str]]) -> dict[str, object]:
    return {
        "columns": selected_columns,
        "datasource": DATASOURCE,
        "filters": [],
        "format": output_format,
        "global_query_id": "",
        "parser": "backend",
        "refId": "A",
        "root_selector": f"$.{dataset}",
        "source": "url",
        "type": "json",
        "url": URL,
        "url_options": {"method": "GET"},
    }


def main() -> None:
    for filename, panels in MAPPINGS.items():
        path = DASHBOARD_DIR / filename
        dashboard = json.loads(path.read_text(encoding="utf-8"))
        for panel in dashboard["panels"]:
            dataset, output_format, selected_columns = panels[panel["id"]]
            panel["datasource"] = DATASOURCE
            panel["targets"] = [query(dataset, output_format, selected_columns)]
        dashboard["refresh"] = "30s"
        dashboard["tags"] = sorted(set(dashboard.get("tags", [])) - {"demo"} | {"live"})
    # Keep the generated dashboards stable across repeated provisioning runs.
    dashboard["version"] = max(int(dashboard.get("version", 1)), 3)
        path.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Configured {filename} for direct live API reads")


if __name__ == "__main__":
    main()
