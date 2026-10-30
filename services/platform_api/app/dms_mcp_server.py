from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from .config import settings
from .paperless_client import PaperlessClient, PaperlessError

paperless = PaperlessClient(settings)
mcp = MCPServer("Paperless DMS")


@mcp.tool()
def search_dms_documents(query: str, max_results: int = 20) -> dict[str, object]:
    """Search Paperless title and OCR text, returning metadata and short snippets."""
    try:
        return paperless.search_documents(query, max_results)
    except PaperlessError as exc:
        return {"tool": "search_dms_documents", "status": "error", "error": str(exc)}


@mcp.tool()
def get_dms_document(document_id: int) -> dict[str, object]:
    """Get metadata for one Paperless document without returning the binary file."""
    try:
        return paperless.get_document(document_id)
    except PaperlessError as exc:
        return {"tool": "get_dms_document", "status": "error", "error": str(exc)}


@mcp.tool()
def list_recent_dms_documents(days: int = 30, max_results: int = 20) -> dict[str, object]:
    """List recently added Paperless documents in a bounded date window."""
    try:
        return paperless.list_recent_documents(days, max_results)
    except PaperlessError as exc:
        return {"tool": "list_recent_dms_documents", "status": "error", "error": str(exc)}


@mcp.tool()
def list_dms_metadata(max_results: int = 100) -> dict[str, object]:
    """List Paperless tags, correspondents and document types."""
    try:
        return paperless.list_metadata(max_results)
    except PaperlessError as exc:
        return {"tool": "list_dms_metadata", "status": "error", "error": str(exc)}


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8091,
        stateless_http=True,
        json_response=True,
    )
