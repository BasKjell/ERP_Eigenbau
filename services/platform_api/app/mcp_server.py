from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from .business_tools import (
    get_order_status as query_order_status,
)
from .business_tools import (
    list_late_purchase_orders as query_late_purchase_orders,
)
from .business_tools import (
    search_documents as query_documents,
)
from .config import settings
from .erp_read import ERPReadService
from .erpnext_client import ERPNextError
from .master_data import MasterDataError, MasterDataService
from .store import ScenarioStore

store = ScenarioStore(settings.data_file, settings.seed_file)
master_data = MasterDataService(settings)
erp_read = ERPReadService(settings)
mcp = MCPServer("Open Manufacturing Platform")


@mcp.tool()
def list_production_orders(include_planned: bool = False, limit: int = 100) -> dict[str, object]:
    """List live ERPNext work orders in production, optionally including planned orders."""
    try:
        return erp_read.list_production_orders(include_planned, limit)
    except ERPNextError as exc:
        return {"tool": "list_production_orders", "status": "error", "error": str(exc)}


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


@mcp.tool()
def list_manufacturing_products(limit: int = 50) -> dict[str, object]:
    """List submitted active ERPNext BOMs and their manufactured products."""
    try:
        return erp_read.list_products(limit=limit)
    except ERPNextError as exc:
        return {"tool": "list_manufacturing_products", "status": "error", "error": str(exc)}


@mcp.tool()
def get_bom_details(item_code: str) -> dict[str, object]:
    """Get one product BOM including components, quantities and operations."""
    try:
        return erp_read.get_bom(item_code)
    except ERPNextError as exc:
        return {"tool": "get_bom_details", "status": "error", "error": str(exc)}


@mcp.tool()
def get_inventory(item_code: str = "", warehouse: str = "", limit: int = 100) -> dict[str, object]:
    """Read current ERPNext stock balances, optionally for an item or warehouse."""
    try:
        return erp_read.get_inventory(item_code, warehouse, limit)
    except ERPNextError as exc:
        return {"tool": "get_inventory", "status": "error", "error": str(exc)}


@mcp.tool()
def list_item_stock_movements(
    item_code: str,
    date_from: str = "",
    date_to: str = "",
    warehouse: str = "",
    limit: int = 100,
) -> dict[str, object]:
    """List traceable stock-ledger movements for one ERPNext item."""
    try:
        return erp_read.list_stock_movements(item_code, date_from, date_to, warehouse, limit)
    except ERPNextError as exc:
        return {"tool": "list_item_stock_movements", "status": "error", "error": str(exc)}


@mcp.tool()
def list_materials_consumed(
    posting_date: str = "",
    work_order: str = "",
    item_code: str = "",
    limit: int = 100,
) -> dict[str, object]:
    """List raw materials consumed by submitted manufacturing entries on a date."""
    try:
        return erp_read.list_materials_consumed(posting_date, work_order, item_code, limit)
    except ERPNextError as exc:
        return {"tool": "list_materials_consumed", "status": "error", "error": str(exc)}


@mcp.tool()
def list_test_data_types() -> dict[str, object]:
    """List ERPNext test-data types, allowed fields, defaults and examples."""
    return master_data.list_types()


@mcp.tool()
def create_test_data(
    entity_type: str,
    records: list[dict[str, object]],
    confirm: bool = False,
    on_duplicate: str = "skip",
    atomic: bool = True,
) -> dict[str, object]:
    """Preview or create allowlisted ERPNext test records.

    Call first with confirm=false. Only repeat with confirm=true after the user has
    approved the preview. Existing documents are never updated.
    """
    try:
        return master_data.create(
            entity_type,
            records,
            confirm=confirm,
            on_duplicate=on_duplicate,
            atomic=atomic,
        )
    except MasterDataError as exc:
        return {"tool": "create_test_data", "status": "rejected", "error": str(exc)}


@mcp.tool()
def import_test_data(
    entity_type: str,
    content: str,
    data_format: str = "csv",
    confirm: bool = False,
    on_duplicate: str = "skip",
    atomic: bool = True,
) -> dict[str, object]:
    """Preview or import allowlisted ERPNext test records from CSV or JSON text.

    Nested child tables such as timesheet time_logs are JSON arrays. Call first
    with confirm=false and repeat with confirm=true only after user approval.
    """
    try:
        return master_data.import_content(
            entity_type,
            content,
            data_format=data_format,
            confirm=confirm,
            on_duplicate=on_duplicate,
            atomic=atomic,
        )
    except MasterDataError as exc:
        return {"tool": "import_test_data", "status": "rejected", "error": str(exc)}


@mcp.tool()
def rollback_test_data_batch(batch_id: str, confirm: bool = False) -> dict[str, object]:
    """Preview or delete only documents recorded in an MCP test-data batch."""
    try:
        return master_data.rollback(batch_id, confirm=confirm)
    except MasterDataError as exc:
        return {
            "tool": "rollback_test_data_batch",
            "status": "rejected",
            "error": str(exc),
        }


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8090,
        stateless_http=True,
        json_response=True,
    )
