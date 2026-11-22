"""MCP-Server „Entwicklung & Repository“ für FLOWAI (Open WebUI).

- Lesen: Code, Doku, Agentenregister und Anforderungen des Repositorys (schreibgeschützt, ohne
  Geheimnisse) sowie der Status der Agentenläufe.
- Ändern: nur als **Vorschlag** eines Fachauftrags. Die Person prüft ihn in FLOWPORTAL und reicht
  ihn mit ihrer FLOWID-Identität ein; danach arbeitet die Agentenkette mit allen Gates.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from .agent_drafts import dev_mcp_token
from .repo_access import RepoAccess, RepoError

repo = RepoAccess(Path(os.getenv("REPOSITORY_DIR", "/repo")))
PLATFORM = os.getenv("PLATFORM_INTERNAL_URL", "http://platform-api:8080").rstrip("/")
mcp = MCPServer("FLOW Entwicklung & Repository")


def _platform(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(
        PLATFORM + path, method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {dev_mcp_token()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read() or b"{}").get("detail")
        except ValueError:
            detail = None
        return {"status": "error", "error": f"Plattform-API {exc.code}: {detail}"}
    except (urllib.error.URLError, OSError) as exc:
        return {"status": "error", "error": f"Plattform-API nicht erreichbar ({type(exc).__name__})"}


def _safe(function, *args: Any) -> dict[str, Any]:  # noqa: ANN001
    try:
        return function(*args)
    except RepoError as exc:
        return {"status": "error", "error": str(exc)}


@mcp.tool()
def repository_overview() -> dict[str, Any]:
    """Überblick über das Repository ERP_Eigenbau: freigegebene Bereiche und wichtige Einstiegsdateien.
    Zuerst aufrufen, wenn der Nutzer nach Code, Aufbau oder Dateien fragt."""
    return repo.overview()


@mcp.tool()
def list_repository_files(path: str = ".", pattern: str = "*", max_results: int = 200) -> dict[str, Any]:
    """Dateien unterhalb eines Pfads auflisten (z. B. path='services/platform_api/app', pattern='*.py')."""
    return _safe(repo.list_files, path, pattern, max_results)


@mcp.tool()
def read_repository_file(path: str, start_line: int = 1, max_lines: int = 400) -> dict[str, Any]:
    """Eine Datei mit Zeilennummern lesen. Antworten immer mit Pfad und Zeilennummern belegen."""
    return _safe(repo.read_file, path, start_line, max_lines)


@mcp.tool()
def search_repository(query: str, path: str = ".", max_results: int = 40) -> dict[str, Any]:
    """Text im Code und in der Doku suchen (z. B. query='ALLOWED_UPLOAD'). Liefert Pfad, Zeile und Treffer."""
    return _safe(repo.search, query, path, max_results)


@mcp.tool()
def agent_status() -> dict[str, Any]:
    """Status der KI-Entwicklung: laufende Fachaufträge, offene Entscheidungen mit Vorschau-Link,
    offene Vorschläge und die freigegebenen Änderungsbereiche."""
    return _platform("GET", "/api/agents/internal/status")


@mcp.tool()
def propose_fachauftrag(
    title: str,
    goal: str,
    behavior: str,
    success_example: str,
    scope: str,
    user_group: str = "Fachbereich",
    exclusions: str = "",
    change_class: str = "neue_funktion",
    project: str = "FLOW-DMS",
    note: str = "",
) -> dict[str, Any]:
    """Einen Fachauftrag für das Agententeam VORSCHLAGEN, wenn der Nutzer eine Änderung möchte.
    Nichts wird direkt geändert: Der Vorschlag erscheint in FLOWPORTAL unter „Zu prüfen“; der Nutzer
    prüft und reicht ihn dort ein. Vorher mit agent_status die passenden Änderungsbereiche (scope)
    ermitteln und mit dem Nutzer Titel, Zweck, Verhalten und ein beobachtbares Erfolgsbeispiel klären.
    change_class: standard (Text/Anzeige), neue_funktion, kritisch (Rechte, Löschung, Migration).
    Dem Nutzer den zurückgegebenen confirm_url nennen."""
    return _platform("POST", "/api/agents/internal/drafts", {
        "title": title, "goal": goal, "behavior": behavior, "success_example": success_example, "scope": scope,
        "user_group": user_group, "exclusions": exclusions, "change_class": change_class, "project": project,
        "note": note,
    })


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8093, stateless_http=True, json_response=True)
