from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from .config import settings
from .knowledge import KnowledgeError, KnowledgeService

knowledge = KnowledgeService(settings.documentation_dir)
mcp = MCPServer("ERP Process Wiki")


@mcp.tool()
def list_documentation_sections() -> dict[str, object]:
    """List top-level sections in the local process and tool documentation."""
    return knowledge.list_sections()


@mcp.tool()
def search_process_documentation(query: str, max_results: int = 10) -> dict[str, object]:
    """Search the local process, user and administration documentation."""
    try:
        return knowledge.search(query, max_results)
    except KnowledgeError as exc:
        return {"tool": "search_process_documentation", "status": "error", "error": str(exc)}


@mcp.tool()
def get_documentation_page(path: str, max_characters: int = 20000) -> dict[str, object]:
    """Read one Markdown page below docs/ using its search-result path."""
    try:
        return knowledge.get_page(path, max_characters)
    except KnowledgeError as exc:
        return {"tool": "get_documentation_page", "status": "error", "error": str(exc)}


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8092,
        stateless_http=True,
        json_response=True,
    )
