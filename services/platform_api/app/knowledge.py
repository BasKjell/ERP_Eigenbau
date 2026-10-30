from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class KnowledgeError(RuntimeError):
    """Validation error for the read-only documentation MCP."""


class KnowledgeService:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def list_sections(self) -> dict[str, Any]:
        sections = []
        if self.root.is_dir():
            sections = sorted(
                path.name
                for path in self.root.iterdir()
                if path.is_dir() and not path.name.startswith(".")
            )
        return {
            "tool": "list_documentation_sections",
            "sections": sections,
            "source": {"system": "Process Wiki", "reference": "docs/"},
        }

    def search(self, query: str, max_results: int = 10) -> dict[str, Any]:
        terms = [term for term in re.findall(r"[\wÄÖÜäöüß-]+", query.casefold()) if len(term) > 1]
        if not terms:
            raise KnowledgeError("query must contain a searchable term")
        matches: list[tuple[int, dict[str, Any]]] = []
        for path in self._markdown_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            normalized = text.casefold()
            relative = path.relative_to(self.root).as_posix()
            score = sum(normalized.count(term) for term in terms)
            score += sum(5 for term in terms if term in relative.casefold())
            if score <= 0:
                continue
            index = min(
                (normalized.find(term) for term in terms if normalized.find(term) >= 0),
                default=0,
            )
            start = max(0, index - 160)
            snippet = re.sub(r"\s+", " ", text[start : start + 520]).strip()
            title = next(
                (
                    line.removeprefix("# ").strip()
                    for line in text.splitlines()
                    if line.startswith("# ")
                ),
                path.stem,
            )
            matches.append(
                (score, {"path": relative, "title": title, "score": score, "snippet": snippet})
            )
        selected = [item for _, item in sorted(matches, key=lambda row: (-row[0], row[1]["path"]))]
        selected = selected[: max(1, min(int(max_results), 50))]
        return {
            "tool": "search_process_documentation",
            "query": query,
            "count": len(selected),
            "results": selected,
            "source": {"system": "Process Wiki", "reference": query},
        }

    def get_page(self, path: str, max_characters: int = 20000) -> dict[str, Any]:
        candidate = (self.root / path).resolve()
        if candidate.suffix.casefold() != ".md" or self.root not in candidate.parents:
            raise KnowledgeError("path must reference a Markdown page below docs/")
        if not candidate.is_file():
            raise KnowledgeError("documentation page was not found")
        limit = max(1000, min(int(max_characters), 50000))
        content = candidate.read_text(encoding="utf-8", errors="replace")
        return {
            "tool": "get_documentation_page",
            "path": candidate.relative_to(self.root).as_posix(),
            "truncated": len(content) > limit,
            "content": content[:limit],
            "source": {
                "system": "Process Wiki",
                "reference": candidate.relative_to(self.root).as_posix(),
            },
        }

    def _markdown_files(self) -> list[Path]:
        if not self.root.is_dir():
            return []
        return sorted(self.root.rglob("*.md"))
