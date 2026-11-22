from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

_STOP_WORDS = frozenset(
    {
        "aber",
        "als",
        "am",
        "an",
        "auf",
        "aus",
        "bei",
        "bitte",
        "das",
        "dem",
        "den",
        "der",
        "des",
        "die",
        "ein",
        "eine",
        "einem",
        "einen",
        "einer",
        "es",
        "für",
        "fuer",
        "gibt",
        "ich",
        "im",
        "in",
        "ist",
        "kann",
        "man",
        "mir",
        "mit",
        "oder",
        "sind",
        "und",
        "von",
        "warum",
        "was",
        "welche",
        "welcher",
        "welchen",
        "wer",
        "wie",
        "wir",
        "wo",
        "zu",
        "zum",
        "zur",
    }
)
_HEADING = re.compile(r"^(#{1,4})\s+(.+?)\s*#*\s*$")


class KnowledgeError(RuntimeError):
    """Validation error for the read-only documentation MCP."""


class KnowledgeService:
    def __init__(
        self, root: Path, public_base_url: str = "http://localhost:8001"
    ) -> None:
        self.root = root.resolve()
        self.public_base_url = public_base_url.rstrip("/")

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
            "section_urls": {
                section: f"{self.public_base_url}/{quote(section)}/"
                for section in sections
            },
            "source": {
                "system": "Process Wiki",
                "reference": "docs/",
                "url": f"{self.public_base_url}/",
            },
        }

    def search(self, query: str, max_results: int = 10) -> dict[str, Any]:
        all_terms = [
            term
            for term in re.findall(r"[\wÄÖÜäöüß]+", query.casefold())
            if len(term) > 1
        ]
        terms = [term for term in all_terms if term not in _STOP_WORDS] or all_terms
        if not terms:
            raise KnowledgeError("query must contain a searchable term")
        matches_by_path: dict[str, tuple[int, dict[str, Any]]] = {}
        for path in self._markdown_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            relative = path.relative_to(self.root).as_posix()
            title = self._title(text, path.stem)
            path_text = relative.casefold()
            for section, content in self._sections(text, title):
                normalized = content.casefold()
                heading_text = section.casefold()
                score = sum(normalized.count(term) for term in terms)
                score += sum(8 for term in terms if term in heading_text)
                score += sum(5 for term in terms if term in title.casefold())
                score += sum(4 for term in terms if term in path_text)
                if score <= 0:
                    continue
                item = {
                    "path": relative,
                    "title": title,
                    "section": section,
                    "score": score,
                    "snippet": self._snippet(content, terms),
                    "url": self._page_url(
                        relative, section if section != title else ""
                    ),
                }
                previous = matches_by_path.get(relative)
                if previous is None or score > previous[0]:
                    matches_by_path[relative] = (score, item)
        selected = [
            item
            for _, item in sorted(
                matches_by_path.values(), key=lambda row: (-row[0], row[1]["path"])
            )
        ]
        selected = selected[: max(1, min(int(max_results), 50))]
        return {
            "tool": "search_process_documentation",
            "query": query,
            "count": len(selected),
            "results": selected,
            "answer_instruction": (
                "Fasse nur die gelieferten Fundstellen zusammen und verlinke die "
                "verwendeten Quellen mit dem jeweiligen url-Feld als Markdown-Link."
            ),
            "source": {
                "system": "Process Wiki",
                "reference": query,
                "url": f"{self.public_base_url}/",
            },
        }

    def get_context(self, question: str, max_results: int = 5) -> dict[str, Any]:
        result = self.search(question, max_results)
        return {
            "tool": "get_documentation_context",
            "question": question,
            "count": result["count"],
            "context": result["results"],
            "answer_instruction": result["answer_instruction"],
            "source": result["source"],
        }

    def get_page(self, path: str, max_characters: int = 20000) -> dict[str, Any]:
        candidate = (self.root / path).resolve()
        if candidate.suffix.casefold() != ".md" or self.root not in candidate.parents:
            raise KnowledgeError("path must reference a Markdown page below docs/")
        if not candidate.is_file():
            raise KnowledgeError("documentation page was not found")
        limit = max(1000, min(int(max_characters), 50000))
        content = candidate.read_text(encoding="utf-8", errors="replace")
        relative = candidate.relative_to(self.root).as_posix()
        url = self._page_url(relative)
        return {
            "tool": "get_documentation_page",
            "path": relative,
            "title": self._title(content, candidate.stem),
            "url": url,
            "truncated": len(content) > limit,
            "content": content[:limit],
            "source": {
                "system": "Process Wiki",
                "reference": relative,
                "url": url,
            },
        }

    @staticmethod
    def _title(text: str, fallback: str) -> str:
        return next(
            (
                match.group(2).strip()
                for line in text.splitlines()
                if (match := _HEADING.match(line)) and len(match.group(1)) == 1
            ),
            fallback,
        )

    @staticmethod
    def _sections(text: str, title: str) -> list[tuple[str, str]]:
        sections: list[tuple[str, str]] = []
        heading = title
        lines: list[str] = []
        for line in text.splitlines():
            match = _HEADING.match(line)
            if match:
                if lines and any(part.strip() for part in lines):
                    sections.append((heading, "\n".join(lines)))
                heading = match.group(2).strip()
                lines = []
                continue
            lines.append(line)
        if lines and any(part.strip() for part in lines):
            sections.append((heading, "\n".join(lines)))
        return sections or [(title, text)]

    @staticmethod
    def _snippet(content: str, terms: list[str], max_characters: int = 1200) -> str:
        normalized = content.casefold()
        index = min(
            (normalized.find(term) for term in terms if normalized.find(term) >= 0),
            default=0,
        )
        start = max(0, index - 180)
        return re.sub(r"\s+", " ", content[start : start + max_characters]).strip()

    def _page_url(self, relative: str, heading: str = "") -> str:
        page = relative[:-3] if relative.casefold().endswith(".md") else relative
        if page == "index":
            page = ""
        elif page.endswith("/index"):
            page = page[: -len("index")]
        else:
            page = f"{page}/"
        url = f"{self.public_base_url}/{quote(page, safe='/')}"
        if heading:
            slug = re.sub(r"[^\w-]", "", re.sub(r"[\s_]+", "-", heading.casefold()))
            if slug:
                url = f"{url}#{quote(slug)}"
        return url

    def _markdown_files(self) -> list[Path]:
        if not self.root.is_dir():
            return []
        return sorted(self.root.rglob("*.md"))
