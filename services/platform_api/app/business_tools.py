from __future__ import annotations

from typing import Any


def list_production_orders(state: dict[str, Any]) -> dict[str, Any]:
    """List work orders that are currently active on the shopfloor."""
    production = next(step for step in state["process"] if step["id"] == "production")
    orders: list[dict[str, Any]] = []
    if production["status"] in {"active", "blocked"}:
        order = state["order"]
        orders.append(
            {
                "work_order": order["work_order"],
                "sales_order": order["id"],
                "product": order["product"],
                "quantity": order["quantity"],
                "status": "aktiv" if production["status"] == "active" else "blockiert",
                "progress_percent": production["progress"],
                "delivery_risk": (
                    "im Plan" if order["delivery_risk"] == "on_track" else "gefaehrdet"
                ),
            }
        )
    return {
        "tool": "list_production_orders",
        "count": len(orders),
        "orders": orders,
        "source": {"system": "ERPNext", "reference": "Work Order"},
    }


def list_late_purchase_orders(state: dict[str, Any]) -> dict[str, Any]:
    """List purchase orders whose expected date is later than the promised date."""
    orders = [
        order
        for order in state.get("purchase_orders", [])
        if order.get("status") == "late" or order.get("delay_days", 0) > 0
    ]
    return {
        "tool": "list_late_purchase_orders",
        "count": len(orders),
        "orders": orders,
        "source": {"system": "ERPNext", "reference": "Purchase Order"},
    }


def get_order_status(state: dict[str, Any], order_id: str = "SO-4711") -> dict[str, Any]:
    """Return the grounded status and current process step for a sales order."""
    order = state["order"]
    if order["id"].casefold() != order_id.casefold():
        return {
            "tool": "get_order_status",
            "found": False,
            "order_id": order_id,
            "source": {"system": "ERPNext", "reference": order_id},
        }
    active = next(
        (step for step in state["process"] if step["status"] in {"active", "blocked"}),
        state["process"][-1],
    )
    return {
        "tool": "get_order_status",
        "found": True,
        "order": order,
        "current_step": active,
        "metrics": state["metrics"],
        "quality_incident": state.get("quality_incident"),
        "source": {"system": "ERPNext", "reference": order["id"]},
    }


def search_documents(state: dict[str, Any], query: str) -> dict[str, Any]:
    """Search demo document metadata by title, item, revision, tag or ID."""
    needle = query.casefold()
    matches = []
    for document in state["documents"]:
        haystack = " ".join(
            [
                document["id"],
                document["title"],
                document["item"],
                document["revision"],
                *document["tags"],
            ]
        ).casefold()
        if needle in haystack:
            matches.append(document)
    return {
        "tool": "search_documents",
        "query": query,
        "count": len(matches),
        "documents": matches,
        "source": {"system": "Paperless", "reference": query},
    }


def select_read_tools(question: str, state: dict[str, Any]) -> list[dict[str, Any]]:
    """Select the smallest read-only tool set needed for a natural-language question."""
    normalized = question.casefold()
    if any(word in normalized for word in ("produktion", "fertigung", "work order")):
        return [list_production_orders(state)]
    if any(word in normalized for word in ("bestellung", "purchase", "lieferant")) and any(
        word in normalized for word in ("verspät", "verspaet", "überfällig", "ueberfaellig", "late")
    ):
        return [list_late_purchase_orders(state)]
    if any(word in normalized for word in ("dokument", "revision", "zeichnung", "prüfplan", "pruefplan")):
        query = "SCU-100" if "scu" in normalized or "revision" in normalized else question
        return [search_documents(state, query)]
    return [get_order_status(state)]


def sources_from_results(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build compact source chips from tool results without trusting model output."""
    sources: list[dict[str, str]] = []
    for result in results:
        source = result.get("source")
        if source:
            sources.append(
                {
                    "system": str(source["system"]),
                    "reference": str(source["reference"]),
                    "label": result["tool"],
                }
            )
        for order in result.get("orders", []):
            reference = order.get("work_order") or order.get("id")
            if reference:
                sources.append(
                    {
                        "system": "ERPNext",
                        "reference": str(reference),
                        "label": result["tool"],
                    }
                )
        for document in result.get("documents", []):
            sources.append(
                {
                    "system": "Paperless",
                    "reference": str(document["id"]),
                    "label": str(document["title"]),
                }
            )
    unique = {(source["system"], source["reference"]): source for source in sources}
    return list(unique.values())
