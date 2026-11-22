from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from .config import settings
from .dms_vector import DmsVectorError, DmsVectorIndex
from .paperless_client import PaperlessClient, PaperlessError

paperless = PaperlessClient(settings)
vector_index = DmsVectorIndex(settings, paperless)
mcp = MCPServer("Paperless DMS")


@mcp.tool()
def search_dms_documents(query: str, max_results: int = 20) -> dict[str, object]:
    """Search Paperless metadata/OCR; cite each returned document URL in the answer."""
    try:
        return paperless.search_documents(query, max_results)
    except PaperlessError as exc:
        return {"tool": "search_dms_documents", "status": "error", "error": str(exc)}


@mcp.tool()
def get_dms_document(document_id: int) -> dict[str, object]:
    """Get bounded document metadata and a browser URL, without returning the binary."""
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


@mcp.tool()
def search_dms_documents_semantic(
    query: str, max_results: int = 8
) -> dict[str, object]:
    """Search indexed Paperless OCR text semantically; cite every returned URL."""
    try:
        return vector_index.search(query, max_results)
    except (DmsVectorError, PaperlessError) as exc:
        return {
            "tool": "search_dms_documents_semantic",
            "status": "error",
            "error": str(exc),
        }


@mcp.tool()
def refresh_dms_vector_index(max_documents: int = 100) -> dict[str, object]:
    """Refresh the local pgvector index from bounded Paperless OCR content."""
    try:
        return vector_index.refresh(max_documents)
    except (DmsVectorError, PaperlessError) as exc:
        return {
            "tool": "refresh_dms_vector_index",
            "status": "error",
            "error": str(exc),
        }


@mcp.tool()
def get_dms_vector_index_status() -> dict[str, object]:
    """Report document/chunk counts and the local embedding model."""
    try:
        return vector_index.status()
    except DmsVectorError as exc:
        return {
            "tool": "get_dms_vector_index_status",
            "status": "error",
            "error": str(exc),
        }


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8091,
        stateless_http=True,
        json_response=True,
    )
