"""FLOWDOC – eigene DMS-Oberfläche über die Paperless-API (REQ-DMS-001 bis REQ-DMS-008)."""

from __future__ import annotations

import json
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from app.config import settings
from app.dms import DmsError, DmsService

TAGS = [{"id": 1, "name": "Status/Entwurf", "color": "#999", "document_count": 1},
        {"id": 2, "name": "Status/In Prüfung", "color": "#fa0", "document_count": 0},
        {"id": 3, "name": "Status/Freigegeben", "color": "#0a0", "document_count": 1},
        {"id": 4, "name": "Projekt/KOM-2027-4711", "color": "#00f", "document_count": 2}]
DOCUMENTS = {
    10: {"id": 10, "title": "Beta Verfahrensanweisung", "tags": [3, 4], "document_type": 1, "correspondent": None,
         "created_date": "2026-11-01", "added": "2026-11-02T10:00:00Z", "content": "Text Beta", "owner": 1},
    11: {"id": 11, "title": "Alpha Verfahrensanweisung", "tags": [1, 4], "document_type": 1, "correspondent": None,
         "created_date": "2026-11-03", "added": "2026-11-03T10:00:00Z", "content": "Text Alpha", "owner": 1},
    12: {"id": 12, "title": "Delta gesperrt für Einkauf", "tags": [3], "document_type": 1, "correspondent": None,
         "created_date": "2026-11-04", "added": "2026-11-04T10:00:00Z", "content": "Geheim", "owner": 2},
}
VISIBLE = {"demo01": {10, 11}, "demo02": {12}}


class FakePaperless(BaseHTTPRequestHandler):
    requests: list[dict[str, Any]] = []

    def _user(self) -> str | None:
        user = self.headers.get("X-Flow-Sso-User")
        if user:
            return user
        return "admin" if self.headers.get("Authorization") == "Token technical" else None

    def _send(self, status: int, payload: Any, content_type: str = "application/json") -> None:
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _visible(self, user: str) -> set[int]:
        return set(DOCUMENTS) if user == "admin" else VISIBLE.get(user, set())

    def do_GET(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        query = parse_qs(url.query)
        user = self._user()
        FakePaperless.requests.append({"method": "GET", "path": url.path, "query": query, "user": user})
        if user is None:
            return self._send(401, {"detail": "no auth"})
        if url.path == "/api/tags/":
            return self._send(200, {"results": TAGS})
        if url.path in {"/api/document_types/", "/api/correspondents/", "/api/storage_paths/"}:
            rows = [{"id": 1, "name": "Verfahrensanweisung", "document_count": 3}] if "document_types" in url.path else []
            return self._send(200, {"results": rows})
        if url.path == "/api/documents/":
            rows = [DOCUMENTS[i] for i in sorted(self._visible(user))]
            if "tags__id__all" in query:
                wanted = {int(t) for t in query["tags__id__all"][0].split(",")}
                rows = [r for r in rows if wanted <= set(r["tags"])]
            ordering = query.get("ordering", ["-created"])[0]
            if ordering.lstrip("-") == "title":
                rows.sort(key=lambda r: r["title"], reverse=ordering.startswith("-"))
            return self._send(200, {"count": len(rows), "results": rows})
        parts = url.path.strip("/").split("/")
        if len(parts) >= 3 and parts[1] == "documents" and parts[2].isdigit():
            document_id = int(parts[2])
            if document_id not in self._visible(user):
                return self._send(404, {"detail": "Not found"})
            if len(parts) == 3:
                return self._send(200, {**DOCUMENTS[document_id], "user_can_change": user == "demo01"})
            if parts[3] == "notes":
                return self._send(200, [{"id": 1, "note": "Geprüft", "created": "2026-11-05", "user": {"username": "demo01"}}])
            if parts[3] in {"thumb", "preview", "download"}:
                return self._send(200, b"%PDF-1.4 fake", "application/pdf")
        if url.path == "/api/tasks/":
            return self._send(200, [{"task_id": query["task_id"][0], "status": "SUCCESS", "related_document": "13"}])
        return self._send(404, {"detail": "unknown"})

    def do_POST(self) -> None:  # noqa: N802
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        user = self._user()
        FakePaperless.requests.append({"method": "POST", "path": self.path, "user": user, "body": body[:2000]})
        if user is None:
            return self._send(401, {})
        if self.path == "/api/documents/post_document/":
            return self._send(200, "3f2a1b4c-aaaa-bbbb-cccc-1234567890ab")
        if self.path.endswith("/notes/"):
            return self._send(200, [])
        return self._send(404, {})

    def do_PATCH(self) -> None:  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        user = self._user()
        document_id = int(self.path.strip("/").split("/")[2])
        FakePaperless.requests.append({"method": "PATCH", "path": self.path, "user": user, "json": body})
        if user != "demo01":
            return self._send(403, {"detail": "forbidden"})
        DOCUMENTS[document_id]["tags"] = body["tags"]
        return self._send(200, DOCUMENTS[document_id])

    def log_message(self, *args: Any) -> None:
        return


@pytest.fixture()
def paperless():  # noqa: ANN201
    snapshot = json.loads(json.dumps(DOCUMENTS))
    server = HTTPServer(("127.0.0.1", 0), FakePaperless)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    FakePaperless.requests.clear()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    DOCUMENTS.clear()
    DOCUMENTS.update({int(k): v for k, v in snapshot.items()})


def service(url: str, mode: str = "oidc", token: str = "") -> DmsService:
    return DmsService(replace(settings, paperless_base_url=url, auth_mode=mode, paperless_api_token=token,
                              paperless_username="", paperless_password=""))


def test_18_search_runs_in_the_name_of_the_person(paperless: str) -> None:
    dms = service(paperless)
    first = dms.search({"username": "demo01"})
    other = dms.search({"username": "demo02"})
    assert {d["title"] for d in first["results"]} == {"Alpha Verfahrensanweisung", "Beta Verfahrensanweisung"}
    assert first["count"] == 2 and other["count"] == 1
    assert "Delta" not in json.dumps(first) and "Alpha" not in json.dumps(other)
    assert all(r["user"] in {"demo01", "demo02"} for r in FakePaperless.requests), "kein technisches Konto im OIDC-Modus"
    assert first["access"] == "im Namen von demo01"


def test_oidc_mode_never_falls_back_to_the_technical_account(paperless: str) -> None:
    dms = service(paperless, token="technical")
    with pytest.raises(DmsError) as error:
        dms.search(None)
    assert error.value.status == 401
    with pytest.raises(DmsError):
        dms.search({"username": "bad user;"})


def test_demo_mode_uses_and_labels_the_technical_account(paperless: str) -> None:
    result = service(paperless, mode="demo", token="technical").search(None)
    assert result["count"] == 3 and result["access"] == "technisches Konto (Demo)"
    with pytest.raises(DmsError) as error:
        service(paperless, mode="demo").search(None)
    assert error.value.status == 503


def test_a17_sort_by_title_and_status_filter(paperless: str) -> None:
    dms = service(paperless)
    ordered = dms.search({"username": "demo01"}, ordering="title")
    assert [d["title"][:5] for d in ordered["results"]] == ["Alpha", "Beta "]
    assert FakePaperless.requests[-1]["query"]["ordering"] == ["title"]
    released = dms.search({"username": "demo01"}, status="Status/Freigegeben")
    assert [d["title"][:4] for d in released["results"]] == ["Beta"]
    assert released["results"][0]["status"] == "Status/Freigegeben"
    assert all(not t["name"].startswith("Status/") for t in released["results"][0]["tags"])
    with pytest.raises(DmsError, match="Sortierung"):
        dms.search({"username": "demo01"}, ordering="owner;drop")


def test_detail_preview_and_hidden_documents(paperless: str) -> None:
    dms = service(paperless)
    detail = dms.document({"username": "demo01"}, 11)
    assert detail["status"] == "Status/Entwurf" and detail["transitions"] == ["pruefen"]
    assert detail["notes"][0]["note"] == "Geprüft" and detail["user_can_change"] is True
    data, content_type = dms.binary({"username": "demo01"}, 11, "preview")
    assert data.startswith(b"%PDF") and content_type == "application/pdf"
    with pytest.raises(DmsError) as error:
        dms.document({"username": "demo01"}, 12)
    assert error.value.status == 404


def test_status_transition_respects_source_status_and_paperless_rights(paperless: str) -> None:
    dms = service(paperless)
    updated = dms.transition({"username": "demo01"}, 11, "pruefen")
    assert updated["status"] == "Status/In Prüfung"
    with pytest.raises(DmsError, match="nicht im Status"):
        dms.transition({"username": "demo01"}, 11, "pruefen")
    with pytest.raises(DmsError) as error:
        dms.transition({"username": "demo02"}, 12, "zurueckweisen")
    assert error.value.status == 409  # Delta steht nicht in Prüfung


def test_upload_is_validated_and_delegated(paperless: str) -> None:
    dms = service(paperless)
    with pytest.raises(DmsError, match="Dateityp"):
        dms.upload({"username": "demo01"}, b"MZ", "tool.exe", "Tool")
    with pytest.raises(DmsError, match="größer"):
        dms.upload({"username": "demo01"}, b"", "leer.pdf", "Leer")
    task = dms.upload({"username": "demo01"}, b"%PDF-1.4", "Prüfplan.pdf", "Prüfplan", document_type=1, tags=[4])
    assert task["task_id"].startswith("3f2a1b4c")
    upload = FakePaperless.requests[-1]
    assert upload["user"] == "demo01" and b'name="tags"' in upload["body"]
    assert dms.task({"username": "demo01"}, task["task_id"])["document_id"] == "13"
