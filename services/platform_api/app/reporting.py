from __future__ import annotations

import threading
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

from .config import Settings
from .erpnext_client import ERPNextClient, ERPNextError
from .finance import FinanceService
from .mes import MesService


def _number(value: object, default: float = 0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


class LiveReportingService:
    """Read-only, short-lived reporting projection over the operational APIs.

    The service intentionally does not persist a second business-data snapshot.
    Grafana reads this projection through an internal token-protected endpoint.
    """

    def __init__(
        self,
        finance: FinanceService,
        mes: MesService,
        settings: Settings,
        erp: ERPNextClient | None = None,
        cache_seconds: float = 5,
    ) -> None:
        self.finance = finance
        self.mes = mes
        self.erp = erp or ERPNextClient(settings)
        self.cache_seconds = cache_seconds
        self._lock = threading.Lock()
        self._cached_at = 0.0
        self._cached: dict[str, Any] | None = None

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            if self._cached is not None and now - self._cached_at < self.cache_seconds:
                return self._cached
            result = self._build()
            self._cached = result
            self._cached_at = now
            return result

    def _build(self) -> dict[str, Any]:
        finance = self.finance.dashboard()
        mes = self.mes.dashboard()
        sources: list[dict[str, Any]] = [
            {"system": "FLOWFIN", "mode": "live", "detail": "aktuelle Anwendungsdaten"},
            {"system": "FLOWMES", "mode": "live", "detail": "aktuelle Rückmeldungen"},
        ]

        orders = [dict(item) for item in finance["orders"]]
        opportunities = self._fallback_opportunities(orders)
        erp_work_orders: list[dict[str, Any]] = []
        if self.erp.configured:
            erp_orders, orders_error = self._erp_sales_orders(orders)
            if erp_orders:
                orders = erp_orders
            erp_opportunities, opportunities_error = self._erp_opportunities()
            if erp_opportunities:
                opportunities = erp_opportunities
            erp_work_orders, work_orders_error = self._erp_work_orders()
            errors = [item for item in (orders_error, opportunities_error, work_orders_error) if item]
            sources.append(
                {
                    "system": "ERPNext",
                    "mode": "live" if len(errors) < 3 else "fallback",
                    "detail": "; ".join(errors) if errors else "REST API verbunden",
                }
            )
        else:
            sources.append(
                {"system": "ERPNext", "mode": "fallback", "detail": "Credentials fehlen"}
            )

        production_wip = self._production_wip(mes["jobs"], erp_work_orders, orders)
        workstation_load = self._workstation_load(mes["jobs"])
        operation_summary = [
            {"current_operation": operation, "orders": count}
            for operation, count in Counter(
                item["current_operation"] for item in production_wip
            ).most_common()
        ]
        production_kpis = [{
            "active_work_orders": len(production_wip),
            "production_order_value": sum(_number(item["order_value"]) for item in production_wip),
            "blocked_work_orders": sum(item["operation_status"] == "blocked" for item in production_wip),
            "orders_at_risk": sum(item["risk"] == "at_risk" for item in production_wip),
        }]

        active_orders = [item for item in orders if item.get("status") not in {"cancelled", "invoiced"}]
        active_production = [
            item for item in active_orders if item.get("stage") in {"Produktion", "Endprüfung"}
        ]
        executive_kpis = [{
            "production_order_value": sum(_number(item.get("order_value")) for item in active_production),
            "production_weighted_revenue": sum(_number(item.get("weighted_revenue")) for item in active_production),
            "weighted_backlog": sum(_number(item.get("weighted_revenue")) for item in active_orders),
            "expected_margin": sum(_number(item.get("expected_margin")) for item in active_orders),
            "orders_at_risk": sum(item.get("risk") == "at_risk" for item in active_orders),
            "active_work_orders": len(production_wip),
            "blocked_work_orders": production_kpis[0]["blocked_work_orders"],
        }]

        crm_yearly: dict[int, dict[str, float]] = defaultdict(
            lambda: {"pipeline_value": 0, "weighted_pipeline": 0}
        )
        crm_stages: dict[str, float] = defaultdict(float)
        for item in opportunities:
            if item["status"] != "open":
                continue
            year = int(str(item["expected_close_date"])[:4])
            crm_yearly[year]["pipeline_value"] += _number(item["opportunity_value"])
            crm_yearly[year]["weighted_pipeline"] += _number(item["weighted_value"])
            crm_stages[item["stage"]] += _number(item["weighted_value"])
        open_opportunities = [item for item in opportunities if item["status"] == "open"]
        crm_kpis = [{
            "gross_pipeline": sum(_number(item["opportunity_value"]) for item in open_opportunities),
            "weighted_pipeline": sum(_number(item["weighted_value"]) for item in open_opportunities),
            "open_opportunities": len(open_opportunities),
            "average_probability": round(
                sum(_number(item["probability"]) for item in open_opportunities)
                / max(1, len(open_opportunities)), 1
            ),
        }]

        quality_rows = [dict(item) for item in finance["quality_costs"]]
        for item in finance["warranty_cases"]:
            quality_rows.append({
                "id": item["id"],
                "category": "Gewährleistung",
                "project_id": item.get("project_id", "RMA"),
                "amount": item["amount"],
                "period": item.get("period", finance["as_of"][:7]),
            })
        quality_months: dict[str, dict[str, Any]] = defaultdict(dict)
        for item in quality_rows:
            month = str(item["period"])[:7]
            quality_months[month]["time"] = f"{month}-01"
            quality_months[month][item["category"]] = (
                _number(quality_months[month].get(item["category"])) + _number(item["amount"])
            )

        portfolio = [
            {
                "portfolio_type": "R&D",
                "portfolio_id": item["id"],
                "name": item["name"],
                "owner_name": item.get("owner", "Engineering"),
                "status": item["status"],
                "actual_cost": item.get("actual_cost", 0),
                "forecast_cost": item["forecast_cost"],
                "target_date": item.get("release_target"),
                "risk": item.get("risk", "medium"),
            }
            for item in finance["rd_projects"]
        ]
        portfolio.extend(
            {
                "portfolio_type": "Software",
                "portfolio_id": item["id"],
                "name": item["product"],
                "owner_name": item.get("owner", item.get("allocation", "IT")),
                "status": item.get("status", "active"),
                "actual_cost": item.get("annual_value", 0),
                "forecast_cost": item.get("annual_value", 0),
                "target_date": item.get("renewal_date"),
                "risk": item.get("risk", "low"),
            }
            for item in finance["subscriptions"]
        )

        return {
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "sources": sources,
            "executive_kpis": executive_kpis,
            "monthly_revenue": [
                {"time": f"{item['month']}-01", **item}
                for item in self._monthly_revenue(orders)
            ],
            "orders": [{**item, "order_id": item["id"]} for item in orders],
            "budget_status": [
                {**item, "budget_name": item["name"], "forecast_usage_percent": item["usage_percent"]}
                for item in finance["budgets"]
            ],
            "production_kpis": production_kpis,
            "production_wip": production_wip,
            "operation_summary": operation_summary,
            "workstation_load": workstation_load,
            "crm_kpis": crm_kpis,
            "crm_yearly": [
                {"time": f"{year}-01-01", "close_year": year, **values}
                for year, values in sorted(crm_yearly.items())
            ],
            "crm_stage": [
                {"stage": stage, "weighted_value": value}
                for stage, value in sorted(crm_stages.items(), key=lambda item: item[1], reverse=True)
            ],
            "crm_opportunities": opportunities,
            "cash": [
                {
                    "time": f"{item['month']}-01",
                    "liquidity": item["closing_balance"],
                    "inflow": item["inflow"],
                    "outflow": item["outflow"],
                }
                for item in finance["cash_forecast"]
            ],
            "open_items": finance["open_items"],
            "project_profitability": [
                {**item, "order_value": item["revenue"]}
                for item in finance["project_profitability"]
            ],
            "quality_monthly": [quality_months[key] for key in sorted(quality_months)],
            "innovation_portfolio": portfolio,
            "quality_costs": quality_rows,
        }

    def _erp_sales_orders(
        self, fallback_orders: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], str | None]:
        try:
            rows = self.erp.list_documents(
                "Sales Order",
                fields=["name", "customer", "customer_name", "status", "grand_total", "delivery_date", "per_delivered", "project", "owner"],
                filters=[["docstatus", "=", 1]],
                order_by="delivery_date asc, name asc",
                limit=200,
            )
        except ERPNextError as exc:
            return [], str(exc)
        fallback = {item["id"]: item for item in fallback_orders}
        result = []
        for row in rows:
            base = dict(fallback.get(str(row.get("name")), {}))
            value = _number(row.get("grand_total"), _number(base.get("order_value")))
            cost = _number(base.get("forecast_cost"))
            progress = _number(row.get("per_delivered"), _number(base.get("progress")))
            status = str(row.get("status") or base.get("status") or "open")
            base.update({
                "id": str(row.get("name")),
                "project_id": row.get("project") or base.get("project_id") or "",
                "customer": row.get("customer_name") or row.get("customer") or base.get("customer") or "",
                "product": base.get("product") or "ERPNext-Auftrag",
                "stage": base.get("stage") or ("Abgeschlossen" if status == "Completed" else "Produktion"),
                "status": status.casefold().replace(" ", "_"),
                "order_value": value,
                "probability": 100,
                "actual_cost": _number(base.get("actual_cost")),
                "forecast_cost": cost,
                "progress": progress,
                "expected_invoice_date": row.get("delivery_date") or base.get("expected_invoice_date") or "",
                "risk": base.get("risk", "on_track"),
                "owner": row.get("owner") or base.get("owner") or "",
                "weighted_revenue": value,
                "expected_margin": value - cost,
                "expected_margin_percent": round((value - cost) / value * 100, 1) if value else 0,
            })
            result.append(base)
        return result, None

    def _erp_opportunities(self) -> tuple[list[dict[str, Any]], str | None]:
        try:
            rows = self.erp.list_documents(
                "Opportunity",
                fields=["name", "title", "party_name", "customer_name", "sales_stage", "status", "opportunity_amount", "probability", "expected_closing", "opportunity_owner", "utm_source", "territory"],
                order_by="expected_closing asc, name asc",
                limit=200,
            )
        except ERPNextError as exc:
            return [], str(exc)
        result = []
        for row in rows:
            value = _number(row.get("opportunity_amount"))
            probability = _number(row.get("probability"))
            status = str(row.get("status") or "Open").casefold()
            result.append({
                "opportunity_id": str(row.get("name")),
                "opportunity_name": row.get("title") or row.get("name"),
                "customer": row.get("customer_name") or row.get("party_name") or "",
                "product": row.get("title") or "Opportunity",
                "stage": row.get("sales_stage") or "Offen",
                "status": "open" if status not in {"converted", "lost", "closed"} else ("won" if status == "converted" else "lost"),
                "sales_owner": row.get("opportunity_owner") or "",
                "expected_close_date": row.get("expected_closing") or "2099-12-31",
                "close_year": int(str(row.get("expected_closing") or "2099")[:4]),
                "opportunity_value": value,
                "probability": probability,
                "weighted_value": round(value * probability / 100, 2),
                "source": row.get("utm_source") or "ERPNext",
                "region": row.get("territory") or "",
            })
        return result, None

    def _erp_work_orders(self) -> tuple[list[dict[str, Any]], str | None]:
        try:
            return self.erp.list_documents(
                "Work Order",
                fields=["name", "production_item", "item_name", "qty", "produced_qty", "status", "planned_start_date", "planned_end_date", "expected_delivery_date", "sales_order"],
                filters=[["docstatus", "=", 1], ["status", "not in", ["Completed", "Cancelled", "Stopped"]]],
                order_by="planned_start_date asc, name asc",
                limit=200,
            ), None
        except ERPNextError as exc:
            return [], str(exc)

    @staticmethod
    def _fallback_opportunities(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for item in orders:
            if item.get("stage") != "Vertrieb" and item.get("status") != "quotation":
                continue
            value = _number(item.get("order_value"))
            probability = _number(item.get("probability"))
            result.append({
                "opportunity_id": item["id"], "opportunity_name": item["product"],
                "customer": item["customer"], "product": item["product"],
                "stage": item["stage"], "status": "open", "sales_owner": item.get("owner", ""),
                "expected_close_date": item["expected_invoice_date"],
                "close_year": int(item["expected_invoice_date"][:4]),
                "opportunity_value": value, "probability": probability,
                "weighted_value": round(value * probability / 100, 2),
                "source": "FLOWFIN", "region": "",
            })
        return result

    @staticmethod
    def _monthly_revenue(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
        months: dict[str, dict[str, float]] = defaultdict(
            lambda: {"order_value": 0, "weighted_revenue": 0}
        )
        for item in orders:
            month = str(item.get("expected_invoice_date") or "")[:7]
            if len(month) != 7:
                continue
            months[month]["order_value"] += _number(item.get("order_value"))
            months[month]["weighted_revenue"] += _number(item.get("weighted_revenue"))
        return [{"month": month, **values} for month, values in sorted(months.items())]

    @staticmethod
    def _production_wip(
        jobs: list[dict[str, Any]], erp_work_orders: list[dict[str, Any]], orders: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for job in jobs:
            grouped[str(job["work_order"])].append(job)
        for work_order in erp_work_orders:
            grouped.setdefault(str(work_order["name"]), [])
        order_map = {item["id"]: item for item in orders}
        erp_map = {str(item["name"]): item for item in erp_work_orders}
        priority = {"in_progress": 0, "blocked": 1, "paused": 2, "ready": 3, "waiting": 4, "completed": 5}
        result = []
        for work_order, route in grouped.items():
            erp = erp_map.get(work_order, {})
            if route and all(item["status"] == "completed" for item in route):
                continue
            current = min(route, key=lambda item: (priority.get(item["status"], 9), item["sequence"])) if route else None
            sales_order = str((current or {}).get("sales_order") or erp.get("sales_order") or "")
            order = order_map.get(sales_order, {})
            completed = sum(item["status"] == "completed" for item in route)
            count = len(route) or 1
            result.append({
                "work_order_id": work_order,
                "sales_order_id": sales_order,
                "project_id": (current or {}).get("project") or order.get("project_id") or "",
                "customer": order.get("customer", ""),
                "product": (current or {}).get("item_name") or erp.get("item_name") or order.get("product", ""),
                "quantity": (current or {}).get("target_qty") or erp.get("qty") or 0,
                "current_operation": (current or {}).get("operation") or "ERPNext-Planung",
                "operation_status": (current or {}).get("status") or "ready",
                "workstation": (current or {}).get("workstation") or "",
                "assigned_employee": ((current or {}).get("operator") or {}).get("name", ""),
                "completed_operations": completed,
                "operation_count": count,
                "progress_percent": round(completed / count * 100, 1),
                "due_date": (current or {}).get("due_at") or erp.get("expected_delivery_date") or order.get("expected_invoice_date"),
                "risk": order.get("risk", "on_track"),
                "order_value": order.get("order_value", 0),
            })
        return sorted(result, key=lambda item: (str(item["due_date"]), item["work_order_id"]))

    @staticmethod
    def _workstation_load(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"open_operations": 0, "active_operations": 0, "blocked_operations": 0, "remaining_planned_minutes": 0}
        )
        for job in jobs:
            if job["status"] == "completed":
                continue
            row = rows[job["workstation"]]
            row["open_operations"] += 1
            row["active_operations"] += job["status"] == "in_progress"
            row["blocked_operations"] += job["status"] == "blocked"
            row["remaining_planned_minutes"] += max(0, _number(job.get("planned_minutes")) - _number(job.get("booked_minutes")))
        return [{"workstation": workstation, **values} for workstation, values in sorted(rows.items())]
