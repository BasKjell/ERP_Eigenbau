"""Schreibgeschützter Repository-Zugriff für FLOWAI (Open WebUI) – nur Lesen, nie Schreiben.

Grenzen (SEC-AGT-001, Grundsatz 7/8):
- Nur freigegebene Wurzeln des eingehängten Repositorys (read-only Mount im Container).
- Keine Geheimnisse: ``.env*``, Schlüssel, Zertifikate, Anmeldedateien und Git-Interna sind gesperrt;
  Treffer mit offensichtlichen Geheimnissen werden geschwärzt.
- Begrenzte Größe je Datei und Antwort.
Änderungen entstehen ausschließlich als Fachauftrag über die Agentenkette.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path, PurePosixPath
from typing import Any

ALLOWED_ROOTS = ("agents", "services", "docs", "requirements", "scripts", "deployment", "AGENTS.md", "README.md",
                 "compose.yaml", "Makefile", "mkdocs.yml", "pyproject.toml")
BLOCKED_PARTS = (".git", "__pycache__", ".venv", "node_modules", ".pytest_cache", ".ruff_cache")
BLOCKED_NAMES = re.compile(r"(^\.env|\.pem$|\.key$|\.p12$|\.pfx$|credentials|secret|id_rsa|\.sqlite)", re.I)
TEXT_SUFFIXES = {".py", ".js", ".css", ".html", ".md", ".yaml", ".yml", ".json", ".toml", ".txt", ".sql", ".sh",
                 ".rb", ".conf", ".inc", ".csv", ".ini", ".cfg", ".Dockerfile", ""}
SECRET_VALUE = re.compile(r"(gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
MAX_FILE = 200_000


class RepoError(ValueError):
    pass


class RepoAccess:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _resolve(self, path: str) -> Path:
        clean = PurePosixPath(path.strip().lstrip("/") or ".")
        if ".." in clean.parts:
            raise RepoError("Pfad außerhalb des Repositorys")
        if clean.parts and clean.parts[0] != "." and clean.parts[0] not in ALLOWED_ROOTS:
            raise RepoError(f"Bereich {clean.parts[0]} ist nicht freigegeben (erlaubt: {', '.join(ALLOWED_ROOTS)})")
        if any(part in BLOCKED_PARTS for part in clean.parts) or any(BLOCKED_NAMES.search(p) for p in clean.parts):
            raise RepoError("Pfad ist gesperrt (Geheimnisse oder interne Dateien)")
        target = (self.root / clean).resolve()
        if not target.is_relative_to(self.root):
            raise RepoError("Pfad außerhalb des Repositorys")
        return target

    def _allowed(self, path: Path) -> bool:
        relative = path.relative_to(self.root)
        parts = relative.parts
        return (bool(parts) and parts[0] in ALLOWED_ROOTS
                and not any(p in BLOCKED_PARTS for p in parts)
                and not any(BLOCKED_NAMES.search(p) for p in parts)
                and not path.is_symlink())

    def overview(self) -> dict[str, Any]:
        entries = []
        for name in ALLOWED_ROOTS:
            path = self.root / name
            if path.exists():
                entries.append({"path": name, "type": "dir" if path.is_dir() else "file"})
        return {
            "repository": "ERP_Eigenbau (schreibgeschützt)",
            "roots": entries,
            "hints": {
                "FLOWDOC (DMS-Oberfläche)": ["services/platform_api/app/dms.py", "services/platform_api/app/static/dms.js",
                                            "services/platform_api/app/static/dms.html", "services/platform_api/tests/test_dms.py"],
                "Agentenplattform": ["agents/registry.yaml", "agents/workflow.yaml", "services/agent_orchestrator/flowagents/engine.py"],
                "Regeln und Doku": ["AGENTS.md", "docs/agents/bedienung.md", "docs/agents/sicherheitskonzept.md"],
                "Anforderungen": ["requirements/catalog.yaml"],
            },
        }

    def list_files(self, path: str = ".", pattern: str = "*", max_results: int = 200) -> dict[str, Any]:
        base = self._resolve(path)
        if not base.is_dir():
            raise RepoError("Verzeichnis nicht gefunden")
        files = []
        for item in sorted(base.rglob("*")):
            if len(files) >= min(max_results, 500):
                break
            if item.is_file() and self._allowed(item) and fnmatch.fnmatch(item.name, pattern):
                files.append({"path": str(item.relative_to(self.root)), "bytes": item.stat().st_size})
        return {"path": path, "count": len(files), "files": files}

    def read_file(self, path: str, start_line: int = 1, max_lines: int = 400) -> dict[str, Any]:
        target = self._resolve(path)
        if not target.is_file() or not self._allowed(target):
            raise RepoError("Datei nicht gefunden oder gesperrt")
        if target.stat().st_size > MAX_FILE:
            raise RepoError("Datei ist zu groß für die Anzeige")
        data = target.read_bytes()
        if b"\0" in data:
            raise RepoError("Binärdatei")
        lines = data.decode("utf-8", errors="replace").splitlines()
        start = max(1, int(start_line))
        count = max(1, min(int(max_lines), 800))
        chunk = lines[start - 1:start - 1 + count]
        text = SECRET_VALUE.sub("[GESCHWÄRZT]", "\n".join(f"{start + i:5d}  {line}" for i, line in enumerate(chunk)))
        return {"path": str(target.relative_to(self.root)), "total_lines": len(lines), "from_line": start,
                "to_line": start + len(chunk) - 1, "content": text}

    def search(self, query: str, path: str = ".", max_results: int = 40) -> dict[str, Any]:
        if not 2 <= len(query.strip()) <= 200:
            raise RepoError("Suchbegriff mit 2 bis 200 Zeichen angeben")
        base = self._resolve(path)
        needle = query.strip().casefold()
        hits: list[dict[str, Any]] = []
        candidates = [base] if base.is_file() else sorted(base.rglob("*"))
        for item in candidates:
            if len(hits) >= min(max_results, 100):
                break
            if not item.is_file() or not self._allowed(item) or item.stat().st_size > MAX_FILE:
                continue
            if item.suffix not in TEXT_SUFFIXES and not item.name.endswith("Dockerfile"):
                continue
            try:
                text = item.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                if needle in line.casefold():
                    hits.append({"path": str(item.relative_to(self.root)), "line": number,
                                 "text": SECRET_VALUE.sub("[GESCHWÄRZT]", line.strip())[:240]})
                    if len(hits) >= min(max_results, 100):
                        break
        return {"query": query, "count": len(hits), "hits": hits}
