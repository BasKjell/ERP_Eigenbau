from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from .config import Settings


class PaperlessError(RuntimeError):
    """A sanitized Paperless error suitable for MCP tool results."""


class PaperlessClient:
    """Paperless-ngx REST client with read access and explicit document upload."""

    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.paperless_base_url.rstrip("/")
        self.public_url = settings.paperless_public_url.rstrip("/")
        self.token = settings.paperless_api_token
        self.username = settings.paperless_username
        self.password = settings.paperless_password

    @property
    def configured(self) -> bool:
        return bool(self.token or (self.username and self.password))

    def search_documents(self, query: str, max_results: int = 20) -> dict[str, Any]:
        if not query.strip():
            raise PaperlessError("query is required")
        payload = self._get(
            "/api/documents/",
            {"query": query, "page_size": _limit(max_results)},
        )
        return self._document_result("search_dms_documents", payload, query=query)

    def get_document(self, document_id: int) -> dict[str, Any]:
        payload = self._get(f"/api/documents/{int(document_id)}/")
        return {
            "tool": "get_dms_document",
            "found": True,
            "document": _document_metadata(payload, self.public_url),
            "source": {
                "system": "Paperless-ngx",
                "reference": str(document_id),
                "url": _document_url(self.public_url, document_id),
            },
        }

    def list_recent_documents(self, days: int = 30, max_results: int = 20) -> dict[str, Any]:
        selected_days = max(1, min(int(days), 3650))
        payload = self._get(
            "/api/documents/",
            {"ordering": "-added", "page_size": _limit(max_results)},
        )
        cutoff = datetime.now(UTC) - timedelta(days=selected_days)
        documents = []
        for row in payload.get("results", []):
            added = _parse_datetime(str(row.get("added") or ""))
            if added is None or added >= cutoff:
                documents.append(_document_metadata(row, self.public_url))
        return {
            "tool": "list_recent_dms_documents",
            "days": selected_days,
            "count": len(documents),
            "documents": documents,
            "source": {
                "system": "Paperless-ngx",
                "reference": "recent documents",
                "url": f"{self.public_url}/documents",
            },
        }

    def list_metadata(self, max_results: int = 100) -> dict[str, Any]:
        page_size = _limit(max_results, maximum=200)
        result: dict[str, Any] = {"tool": "list_dms_metadata"}
        for key, endpoint in (
            ("tags", "/api/tags/"),
            ("correspondents", "/api/correspondents/"),
            ("document_types", "/api/document_types/"),
        ):
            payload = self._get(endpoint, {"page_size": page_size, "ordering": "name"})
            result[key] = [
                {
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "document_count": row.get("document_count"),
                }
                for row in payload.get("results", [])
            ]
        result["source"] = {"system": "Paperless-ngx", "reference": "metadata"}
        return result

    def list_documents_for_vector_index(
        self, max_documents: int = 100
    ) -> list[dict[str, Any]]:
        """Return bounded OCR text and metadata for the local vector index."""

        payload = self._get(
            "/api/documents/",
            {"ordering": "id", "page_size": _limit(max_documents, maximum=200)},
        )
        documents: list[dict[str, Any]] = []
        for listed in payload.get("results", []):
            document_id = listed.get("id")
            if document_id is None:
                continue
            row = listed
            if not str(row.get("content") or "").strip():
                row = self._get(f"/api/documents/{int(document_id)}/")
            documents.append(
                {
                    **_document_metadata(row, self.public_url),
                    "content": str(row.get("content") or "").strip(),
                }
            )
        return documents

    def upload_document(
        self, content: bytes, filename: str, title: str
    ) -> dict[str, Any]:
        """Upload one document and return Paperless' asynchronous task id.

        This is the only write operation in the regular client. Callers must make
        the user action and the target access policy explicit before invoking it.
        """

        if not content:
            raise PaperlessError("document content is required")
        clean_filename = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        if not clean_filename or "\r" in clean_filename or "\n" in clean_filename:
            raise PaperlessError("document filename is invalid")
        clean_title = title.strip()
        if not clean_title:
            raise PaperlessError("document title is required")
        boundary = f"paperless-{uuid.uuid4().hex}"
        body = _multipart_body(
            boundary,
            fields={"title": clean_title},
            file_field="document",
            filename=clean_filename,
            content=content,
        )
        payload = self._raw_request(
            "POST",
            "/api/documents/post_document/",
            body,
            f"multipart/form-data; boundary={boundary}",
        )
        task_id: object
        if isinstance(payload, str):
            task_id = payload
        elif isinstance(payload, dict):
            task_id = payload.get("task_id") or payload.get("id") or payload.get("task")
        else:
            task_id = None
        if not task_id:
            raise PaperlessError("Paperless returned no upload task id")
        return {
            "task_id": str(task_id),
            "status": "processing",
            "source": {"system": "Paperless-ngx", "reference": str(task_id)},
        }

    def _document_result(self, tool: str, payload: dict[str, Any], *, query: str) -> dict[str, Any]:
        documents = [
            _document_metadata(row, self.public_url) for row in payload.get("results", [])
        ]
        return {
            "tool": tool,
            "query": query,
            "count": len(documents),
            "total": payload.get("count", len(documents)),
            "documents": documents,
            "source": {
                "system": "Paperless-ngx",
                "reference": query,
                "url": f"{self.public_url}/documents",
            },
        }

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.configured:
            raise PaperlessError("Paperless credentials are not configured")
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        return self._request("GET", f"{path}{query}")

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if not self.token:
            self._authenticate()
        headers = {"Accept": "application/json", "Authorization": f"Token {self.token}"}
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode()
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=data, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            raise PaperlessError(_http_error(exc)) from exc
        except (OSError, ValueError, urllib.error.URLError) as exc:
            raise PaperlessError(f"Paperless request failed: {exc}") from exc
        if not isinstance(result, dict):
            raise PaperlessError("Paperless returned an invalid response")
        return result

    def _raw_request(
        self, method: str, path: str, data: bytes, content_type: str
    ) -> object:
        if not self.token:
            self._authenticate()
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": f"Token {self.token}",
                "Content-Type": content_type,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise PaperlessError(_http_error(exc)) from exc
        except (OSError, ValueError, urllib.error.URLError) as exc:
            raise PaperlessError(f"Paperless upload failed: {exc}") from exc

    def _authenticate(self) -> None:
        if not self.username or not self.password:
            raise PaperlessError("Paperless credentials are not configured")
        request = urllib.request.Request(
            f"{self.base_url}/api/token/",
            data=json.dumps({"username": self.username, "password": self.password}).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            raise PaperlessError(_http_error(exc)) from exc
        except (OSError, ValueError, urllib.error.URLError) as exc:
            raise PaperlessError(f"Paperless authentication failed: {exc}") from exc
        token = payload.get("token") if isinstance(payload, dict) else None
        if not token:
            raise PaperlessError("Paperless returned no authentication token")
        self.token = str(token)


def _document_metadata(row: dict[str, Any], public_url: str = "") -> dict[str, Any]:
    search_hit = row.get("__search_hit__") or {}
    highlights = re.sub(r"<[^>]+>", "", str(search_hit.get("highlights") or ""))
    metadata = {
        "id": row.get("id"),
        "title": row.get("title"),
        "created": row.get("created"),
        "added": row.get("added"),
        "modified": row.get("modified"),
        "correspondent": row.get("correspondent"),
        "document_type": row.get("document_type"),
        "tags": row.get("tags") or [],
        "archive_serial_number": row.get("archive_serial_number"),
        "original_file_name": row.get("original_file_name"),
        "custom_fields": row.get("custom_fields") or [],
        "snippet": highlights[:500] or None,
    }
    if public_url and row.get("id") is not None:
        metadata["url"] = _document_url(public_url, row["id"])
    return metadata


def _document_url(public_url: str, document_id: object) -> str:
    return f"{public_url.rstrip('/')}/documents/{int(document_id)}/details"


def _http_error(exc: urllib.error.HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8", errors="replace"))
        detail = payload.get("detail") or payload.get("non_field_errors") or payload
    except (OSError, ValueError):
        detail = f"HTTP {exc.code}"
    return f"Paperless rejected the request ({exc.code}): {str(detail)[:500]}"


def _limit(value: int, maximum: int = 100) -> int:
    return max(1, min(int(value), maximum))


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _multipart_body(
    boundary: str,
    *,
    fields: dict[str, str],
    file_field: str,
    filename: str,
    content: bytes,
) -> bytes:
    marker = boundary.encode("ascii")
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                b"--" + marker + b"\r\n",
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            b"--" + marker + b"\r\n",
            (
                f'Content-Disposition: form-data; name="{file_field}"; '
                f'filename="{filename}"\r\n'
            ).encode("utf-8"),
            b"Content-Type: application/octet-stream\r\n\r\n",
            content,
            b"\r\n--" + marker + b"--\r\n",
        ]
    )
    return b"".join(chunks)
