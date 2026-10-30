from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from .business_tools import (
    get_order_status as query_order_status,
    list_late_purchase_orders as query_late_purchase_orders,
    list_production_orders as query_production_orders,
    search_documents as query_documents,
)
from .config import settings
from .store import ScenarioStore

store = ScenarioStore(settings.data_file, settings.seed_file)
mcp = MCPServer("Open Manufacturing Platform")


@mcp.tool()
def list_production_orders() -> dict[str, object]:
    """List all work orders that are currently active in production."""
    return query_production_orders(store.get())


@mcp.tool()
def list_late_purchase_orders() -> dict[str, object]:
    """List purchase orders that are late against their promised delivery date."""
    return query_late_purchase_orders(store.get())


@mcp.tool()
def get_order_status(order_id: str = "SO-4711") -> dict[str, object]:
    """Get the current status, process step and delivery risk for a sales order."""
    return query_order_status(store.get(), order_id)


@mcp.tool()
def search_documents(query: str) -> dict[str, object]:
    """Search approved manufacturing document metadata without returning file contents."""
    return query_documents(store.get(), query)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8090,
        stateless_http=True,
        json_response=True,
    )
