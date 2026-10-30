from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from .config import Settings
from .erpnext_client import ERPNextClient, ERPNextError


class ERPReadService:
    """Allowlisted, read-only ERPNext queries exposed through MCP."""

    def __init__(self, settings: Settings, client: ERPNextClient | None = None) -> None:
        self.client = client or ERPNextClient(settings)

    def list_products(self, limit: int = 50) -> dict[str, Any]:
        rows = self.client.list_documents(
            "BOM",
            fields=["name", "item", "item_name", "quantity", "is_active", "is_default"],
            filters=[["docstatus", "=", 1], ["is_active", "=", 1]],
            order_by="item asc",
            limit=limit,
        )
        return {
            "tool": "list_manufacturing_products",
            "count": len(rows),
            "products": rows,
            "source": {"system": "ERPNext", "reference": "BOM"},
        }

    def list_production_orders(
        self, include_planned: bool = False, limit: int = 100
    ) -> dict[str, Any]:
        """List submitted ERPNext work orders that are active on the shopfloor."""
        statuses = ["In Process"]
        if include_planned:
            statuses.extend(["Not Started", "Stock Reserved", "Stock Partially Reserved"])
        rows = self.client.list_documents(
            "Work Order",
            fields=[
                "name",
                "production_item",
                "item_name",
                "qty",
                "produced_qty",
                "material_transferred_for_manufacturing",
                "status",
                "planned_start_date",
                "planned_end_date",
                "expected_delivery_date",
                "sales_order",
                "bom_no",
                "wip_warehouse",
                "fg_warehouse",
            ],
            filters=[["docstatus", "=", 1], ["status", "in", statuses]],
            order_by="planned_start_date asc, name asc",
            limit=limit,
        )
        orders = []
        for row in rows:
            quantity = float(row.get("qty") or 0)
            produced = float(row.get("produced_qty") or 0)
            transferred = float(row.get("material_transferred_for_manufacturing") or 0)
            orders.append(
                {
                    **row,
                    "remaining_qty": max(quantity - produced, 0),
                    "progress_percent": round(produced / quantity * 100, 1) if quantity else 0,
                    "material_transfer_percent": (
                        round(transferred / quantity * 100, 1) if quantity else 0
                    ),
                }
            )
        return {
            "tool": "list_production_orders",
            "include_planned": include_planned,
            "count": len(orders),
            "orders": orders,
            "source": {"system": "ERPNext", "reference": "Work Order"},
        }

    def get_bom(self, item_code: str) -> dict[str, Any]:
        rows = self.client.list_documents(
            "BOM",
            fields=["name", "item", "item_name", "quantity", "is_active", "is_default"],
            filters=[
                ["docstatus", "=", 1],
                ["is_active", "=", 1],
                ["item", "=", item_code],
            ],
            order_by="is_default desc, modified desc",
            limit=1,
        )
        if not rows:
            return {
                "tool": "get_bom_details",
                "found": False,
                "item_code": item_code,
                "source": {"system": "ERPNext", "reference": item_code},
            }
        document = self.client.get_document("BOM", str(rows[0]["name"]))
        items = [
            {
                "item_code": row.get("item_code"),
                "item_name": row.get("item_name"),
                "qty": row.get("qty"),
                "uom": row.get("uom"),
                "source_warehouse": row.get("source_warehouse"),
            }
            for row in document.get("items", [])
        ]
        operations = [
            {
                "sequence_id": row.get("sequence_id"),
                "operation": row.get("operation"),
                "workstation": row.get("workstation"),
                "time_in_mins": row.get("time_in_mins"),
                "batch_size": row.get("batch_size"),
            }
            for row in document.get("operations", [])
        ]
        return {
            "tool": "get_bom_details",
            "found": True,
            "bom": {
                "name": document.get("name"),
                "item": document.get("item"),
                "item_name": document.get("item_name"),
                "quantity": document.get("quantity"),
                "items": items,
                "operations": operations,
            },
            "source": {"system": "ERPNext", "reference": document.get("name")},
        }

    def get_inventory(
        self, item_code: str = "", warehouse: str = "", limit: int = 100
    ) -> dict[str, Any]:
        filters: list[list[object]] = []
        if item_code:
            filters.append(["item_code", "=", item_code])
        if warehouse:
            filters.append(["warehouse", "=", warehouse])
        rows = self.client.list_documents(
            "Bin",
            fields=[
                "name",
                "item_code",
                "warehouse",
                "actual_qty",
                "reserved_qty",
                "ordered_qty",
                "planned_qty",
                "projected_qty",
            ],
            filters=filters,
            order_by="item_code asc, warehouse asc",
            limit=limit,
        )
        return {
            "tool": "get_inventory",
            "count": len(rows),
            "item_code": item_code or None,
            "warehouse": warehouse or None,
            "balances": rows,
            "source": {"system": "ERPNext", "reference": "Bin"},
        }

    def list_stock_movements(
        self,
        item_code: str,
        date_from: str = "",
        date_to: str = "",
        warehouse: str = "",
        limit: int = 100,
    ) -> dict[str, Any]:
        if not item_code.strip():
            raise ERPNextError("item_code is required")
        filters: list[list[object]] = [
            ["item_code", "=", item_code],
            ["is_cancelled", "=", 0],
        ]
        if date_from:
            filters.append(["posting_date", ">=", _iso_date(date_from, "date_from")])
        if date_to:
            filters.append(["posting_date", "<=", _iso_date(date_to, "date_to")])
        if warehouse:
            filters.append(["warehouse", "=", warehouse])
        rows = self.client.list_documents(
            "Stock Ledger Entry",
            fields=[
                "name",
                "posting_date",
                "posting_time",
                "item_code",
                "warehouse",
                "actual_qty",
                "qty_after_transaction",
                "valuation_rate",
                "stock_value_difference",
                "voucher_type",
                "voucher_no",
            ],
            filters=filters,
            order_by="posting_date desc, posting_time desc, creation desc",
            limit=limit,
        )
        return {
            "tool": "list_item_stock_movements",
            "count": len(rows),
            "item_code": item_code,
            "date_from": date_from or None,
            "date_to": date_to or None,
            "warehouse": warehouse or None,
            "movements": rows,
            "source": {"system": "ERPNext", "reference": "Stock Ledger Entry"},
        }

    def list_materials_consumed(
        self,
        posting_date: str = "",
        work_order: str = "",
        item_code: str = "",
        limit: int = 100,
    ) -> dict[str, Any]:
        selected_date = _iso_date(posting_date or date.today().isoformat(), "posting_date")
        filters: list[list[object]] = [
            ["docstatus", "=", 1],
            ["posting_date", "=", selected_date],
        ]
        if work_order:
            filters.append(["work_order", "=", work_order])
        entries = self.client.list_documents(
            "Stock Entry",
            fields=[
                "name",
                "posting_date",
                "posting_time",
                "stock_entry_type",
                "purpose",
                "work_order",
                "remarks",
            ],
            filters=filters,
            order_by="posting_date desc, posting_time desc, creation desc",
            limit=min(limit, 100),
        )
        allowed_purposes = {"Manufacture", "Material Consumption for Manufacture"}
        details: list[dict[str, Any]] = []
        totals: defaultdict[str, float] = defaultdict(float)
        for entry in entries:
            purpose = str(entry.get("stock_entry_type") or entry.get("purpose") or "")
            if purpose not in allowed_purposes:
                continue
            document = self.client.get_document("Stock Entry", str(entry["name"]))
            finished_items = [
                str(row.get("item_code"))
                for row in document.get("items", [])
                if row.get("is_finished_item") and row.get("item_code")
            ]
            for row in document.get("items", []):
                code = str(row.get("item_code") or "")
                if not row.get("s_warehouse") or row.get("is_finished_item"):
                    continue
                if item_code and code.casefold() != item_code.casefold():
                    continue
                qty = float(row.get("qty") or 0)
                totals[code] += qty
                details.append(
                    {
                        "stock_entry": document.get("name"),
                        "posting_date": document.get("posting_date"),
                        "posting_time": document.get("posting_time"),
                        "work_order": document.get("work_order"),
                        "item_code": code,
                        "item_name": row.get("item_name"),
                        "qty": qty,
                        "uom": row.get("uom"),
                        "source_warehouse": row.get("s_warehouse"),
                        "finished_item": finished_items[0] if finished_items else None,
                        "bom": document.get("bom_no"),
                        "remarks": document.get("remarks"),
                    }
                )
                if len(details) >= limit:
                    break
            if len(details) >= limit:
                break
        return {
            "tool": "list_materials_consumed",
            "posting_date": selected_date,
            "work_order": work_order or None,
            "item_code": item_code or None,
            "count": len(details),
            "totals": [{"item_code": code, "qty": qty} for code, qty in sorted(totals.items())],
            "consumptions": details,
            "source": {"system": "ERPNext", "reference": "Stock Entry"},
        }


def _iso_date(value: str, field_name: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ERPNextError(f"{field_name} must use YYYY-MM-DD") from exc
