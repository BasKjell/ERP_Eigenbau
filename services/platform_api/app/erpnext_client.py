from __future__ import annotations

import http.cookiejar
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .config import Settings


class ERPNextError(RuntimeError):
    """A sanitized ERPNext REST error suitable for MCP tool results."""


class ERPNextClient:
    """Small standard-library client for the allowlisted ERPNext REST operations."""

    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.erpnext_base_url.rstrip("/")
        self.api_key = settings.erpnext_api_key
        self.api_secret = settings.erpnext_api_secret
        self.username = settings.erpnext_username
        self.password = settings.erpnext_password
        self._cookies = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cookies)
        )
        self._login_lock = threading.Lock()
        self._logged_in = False

    @property
    def configured(self) -> bool:
        token_auth = bool(self.api_key and self.api_secret)
        password_auth = bool(self.username and self.password)
        return token_auth or password_auth

    def find_document(self, doctype: str, field: str, value: object) -> str | None:
        query = urllib.parse.urlencode(
            {
                "filters": json.dumps([[doctype, field, "=", value]]),
                "fields": json.dumps(["name"]),
                "limit_page_length": 1,
            }
        )
        result = self._request(
            "GET", f"/api/resource/{urllib.parse.quote(doctype, safe='')}?{query}"
        )
        rows = result.get("data", [])
        return str(rows[0]["name"]) if rows else None

    def list_documents(
        self,
        doctype: str,
        *,
        fields: list[str],
        filters: list[list[object]] | None = None,
        order_by: str = "modified desc",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Read a bounded DocType list through Frappe's authenticated REST API."""
        page_length = max(1, min(int(limit), 200))
        normalized_filters = []
        for item in filters or []:
            if len(item) != 3:
                raise ERPNextError("ERPNext filters must contain field, operator and value")
            normalized_filters.append([doctype, *item])
        query = urllib.parse.urlencode(
            {
                "fields": json.dumps(fields),
                "filters": json.dumps(normalized_filters),
                "order_by": order_by,
                "limit_page_length": page_length,
            }
        )
        result = self._request(
            "GET", f"/api/resource/{urllib.parse.quote(doctype, safe='')}?{query}"
        )
        rows = result.get("data", [])
        if not isinstance(rows, list):
            raise ERPNextError("ERPNext returned an invalid document list")
        return [row for row in rows if isinstance(row, dict)]

    def get_document(self, doctype: str, name: str) -> dict[str, Any]:
        """Read one named document including its child tables."""
        result = self._request(
            "GET",
            "/api/resource/"
            f"{urllib.parse.quote(doctype, safe='')}/"
            f"{urllib.parse.quote(name, safe='')}",
        )
        data = result.get("data")
        if not isinstance(data, dict):
            raise ERPNextError("ERPNext returned an invalid document")
        return data

    def create_document(self, doctype: str, values: dict[str, Any]) -> dict[str, Any]:
        result = self._request(
            "POST",
            f"/api/resource/{urllib.parse.quote(doctype, safe='')}",
            values,
        )
        data = result.get("data")
        if not isinstance(data, dict) or not data.get("name"):
            raise ERPNextError("ERPNext returned no document identifier")
        return data

    def delete_document(self, doctype: str, name: str) -> None:
        self._request(
            "DELETE",
            "/api/resource/"
            f"{urllib.parse.quote(doctype, safe='')}/"
            f"{urllib.parse.quote(name, safe='')}",
        )

    def _login(self) -> None:
        if self._logged_in or self.api_key:
            return
        if not self.username or not self.password:
            raise ERPNextError("ERPNext credentials are not configured")
        with self._login_lock:
            if self._logged_in:
                return
            data = urllib.parse.urlencode(
                {"usr": self.username, "pwd": self.password}
            ).encode()
            request = urllib.request.Request(
                f"{self.base_url}/api/method/login",
                data=data,
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            try:
                with self._opener.open(request, timeout=15) as response:
                    json.load(response)
            except urllib.error.HTTPError as exc:
                raise ERPNextError(self._http_error(exc)) from exc
            except (OSError, ValueError, urllib.error.URLError) as exc:
                raise ERPNextError(f"ERPNext login failed: {exc}") from exc
            self._logged_in = True

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        self._login()
        headers = {"Accept": "application/json"}
        if self.api_key and self.api_secret:
            headers["Authorization"] = f"token {self.api_key}:{self.api_secret}"
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=data, method=method, headers=headers
        )
        try:
            with self._opener.open(request, timeout=30) as response:
                result = json.load(response)
                return result if isinstance(result, dict) else {"data": result}
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403} and not self.api_key and self._logged_in:
                self._logged_in = False
            raise ERPNextError(self._http_error(exc)) from exc
        except (OSError, ValueError, urllib.error.URLError) as exc:
            raise ERPNextError(f"ERPNext request failed: {exc}") from exc

    @staticmethod
    def _http_error(exc: urllib.error.HTTPError) -> str:
        try:
            payload = json.loads(exc.read().decode("utf-8", errors="replace"))
        except (ValueError, OSError):
            return f"ERPNext returned HTTP {exc.code}"
        message = payload.get("message") or payload.get("exception")
        if not message and payload.get("_server_messages"):
            try:
                messages = json.loads(payload["_server_messages"])
                decoded = [json.loads(item).get("message", item) for item in messages]
                message = "; ".join(str(item) for item in decoded)
            except (TypeError, ValueError):
                message = payload["_server_messages"]
        clean = str(message or f"HTTP {exc.code}").replace("\n", " ")
        return f"ERPNext rejected the request ({exc.code}): {clean[:800]}"
