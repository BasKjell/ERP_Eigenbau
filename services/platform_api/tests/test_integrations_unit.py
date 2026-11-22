import io
import json
import urllib.error
import urllib.request
from typing import Any

import pytest
from app.config import Settings
from app.erpnext_client import ERPNextClient, ERPNextError
from app.integrations import integration_status, paperless_search
from app.paperless_client import PaperlessClient, PaperlessError


class JsonResponse:
    def __init__(self, payload: dict[str, Any], status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def __enter__(self) -> "JsonResponse":
        self.stream = io.BytesIO(json.dumps(self.payload).encode())
        return self

    def __exit__(self, *args: object) -> None:
        self.stream.close()

    def read(self, size: int = -1) -> bytes:
        return self.stream.read(size)


def test_paperless_search_encodes_query_and_sends_token(monkeypatch: Any) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: float) -> JsonResponse:
        assert timeout == 4
        assert request.full_url.endswith("/api/documents/?query=SCU-100+%26+Plan")
        assert request.get_header("Authorization") == "Token secret-token"
        return JsonResponse({"count": 1, "results": [{"id": 17, "title": "Plan"}]})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = paperless_search(
        "SCU-100 & Plan",
        Settings(
            paperless_base_url="http://paperless.test",
            paperless_api_token="secret-token",
        ),
    )

    assert result["mode"] == "live"
    assert result["results"][0]["id"] == 17


def test_paperless_search_degrades_cleanly_on_network_error(monkeypatch: Any) -> None:
    def fail(*_: object, **__: object) -> None:
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", fail)
    result = paperless_search(
        "SCU-100", Settings(paperless_api_token="configured")
    )
    assert result["mode"] == "error"
    assert result["results"] == []


def test_integration_status_distinguishes_configuration_and_reachability(
    monkeypatch: Any,
) -> None:
    def fake_urlopen(
        url: str | urllib.request.Request, timeout: float
    ) -> JsonResponse:
        target = url.full_url if isinstance(url, urllib.request.Request) else url
        assert timeout in {1.5, 4}
        if "erp.test" in target:
            return JsonResponse({"message": "pong"})
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = integration_status(
        Settings(
            erpnext_base_url="http://erp.test",
            erpnext_api_key="key",
            erpnext_api_secret="secret",
            paperless_base_url="http://paperless.test",
            paperless_api_token="token",
        )
    )

    assert result[0]["reachable"] is True
    assert result[0]["mode"] == "live"
    assert result[1]["reachable"] is False
    assert result[2]["name"] == "Redmine"
    assert result[2]["configured"] is False


class RecordingOpener:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.requests: list[urllib.request.Request] = []

    def open(self, request: urllib.request.Request, timeout: float) -> JsonResponse:
        assert timeout == 30
        self.requests.append(request)
        return JsonResponse(self.payload)


class SequentialOpener:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = iter(payloads)
        self.requests: list[urllib.request.Request] = []

    def open(self, request: urllib.request.Request, timeout: float) -> JsonResponse:
        self.requests.append(request)
        assert timeout in {15, 30}
        return JsonResponse(next(self.payloads))


def test_erpnext_client_uses_token_and_bounds_list_page_size() -> None:
    client = ERPNextClient(
        Settings(
            erpnext_base_url="http://erp.test",
            erpnext_api_key="key",
            erpnext_api_secret="secret",
        )
    )
    opener = RecordingOpener({"data": [{"name": "WO-1"}]})
    client._opener = opener

    rows = client.list_documents("Work Order", fields=["name"], limit=999)

    assert rows == [{"name": "WO-1"}]
    request = opener.requests[0]
    assert request.get_header("Authorization") == "token key:secret"
    assert "limit_page_length=200" in request.full_url
    assert "Work%20Order" in request.full_url


def test_erpnext_client_rejects_invalid_filter_without_network_call() -> None:
    client = ERPNextClient(
        Settings(erpnext_api_key="key", erpnext_api_secret="secret")
    )
    with pytest.raises(ERPNextError, match="filters must contain"):
        client.list_documents(
            "Work Order", fields=["name"], filters=[["status", "="]]
        )


def test_erpnext_client_password_login_and_document_crud() -> None:
    client = ERPNextClient(
        Settings(
            erpnext_base_url="http://erp.test",
            erpnext_username="integration-user",
            erpnext_password="secret",
        )
    )
    opener = SequentialOpener(
        [
            {"message": "Logged In"},
            {"data": {"name": "BOM-1", "item": "SCU-100"}},
            {"data": {"name": "SUP-1"}},
            {"message": "ok"},
        ]
    )
    client._opener = opener

    assert client.get_document("BOM", "BOM-1")["item"] == "SCU-100"
    assert client.create_document("Supplier", {"supplier_name": "Test"})["name"] == "SUP-1"
    client.delete_document("Supplier", "SUP-1")

    assert opener.requests[0].full_url == "http://erp.test/api/method/login"
    assert opener.requests[1].full_url.endswith("/api/resource/BOM/BOM-1")
    assert opener.requests[2].method == "POST"
    assert opener.requests[3].method == "DELETE"


def test_paperless_client_validates_query_and_response(monkeypatch: Any) -> None:
    client = PaperlessClient(Settings(paperless_api_token="token"))
    with pytest.raises(PaperlessError, match="query is required"):
        client.search_documents("  ")

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: JsonResponse(["invalid"]),
    )
    with pytest.raises(PaperlessError, match="invalid response"):
        client.get_document(7)


def test_paperless_document_upload_uses_authenticated_multipart(monkeypatch: Any) -> None:
    requests: list[urllib.request.Request] = []

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> JsonResponse:
        assert timeout == 30
        requests.append(request)
        return JsonResponse("task-4711")  # type: ignore[arg-type]

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = PaperlessClient(
        Settings(
            paperless_base_url="http://paperless.test",
            paperless_api_token="upload-token",
        )
    )

    result = client.upload_document(
        b"%PDF-1.4 fictional", "Entgeltabrechnung_TEST.pdf", "Entgeltabrechnung Test"
    )

    assert result["task_id"] == "task-4711"
    request = requests[0]
    assert request.full_url.endswith("/api/documents/post_document/")
    assert request.get_header("Authorization") == "Token upload-token"
    assert request.get_header("Content-type").startswith("multipart/form-data; boundary=")
    assert b'filename="Entgeltabrechnung_TEST.pdf"' in request.data
    assert b"%PDF-1.4 fictional" in request.data


def test_paperless_upload_rejects_empty_or_unsafe_filename() -> None:
    client = PaperlessClient(Settings(paperless_api_token="token"))
    with pytest.raises(PaperlessError, match="content"):
        client.upload_document(b"", "document.pdf", "Document")
    with pytest.raises(PaperlessError, match="filename"):
        client.upload_document(b"x", "invalid\nname.pdf", "Document")


def test_paperless_vector_index_source_fetches_missing_ocr_detail(
    monkeypatch: Any,
) -> None:
    responses = iter(
        [
            JsonResponse(
                {
                    "count": 1,
                    "results": [{"id": 17, "title": "Prüfplan SCU-100"}],
                }
            ),
            JsonResponse(
                {
                    "id": 17,
                    "title": "Prüfplan SCU-100",
                    "content": "Stichprobe im Wareneingang: fünf Teile prüfen.",
                }
            ),
        ]
    )
    requests: list[urllib.request.Request] = []

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> JsonResponse:
        assert timeout == 15
        requests.append(request)
        return next(responses)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = PaperlessClient(
        Settings(
            paperless_base_url="http://paperless.test",
            paperless_public_url="http://localhost:8010",
            paperless_api_token="token",
        )
    )

    documents = client.list_documents_for_vector_index(10)

    assert documents[0]["content"].startswith("Stichprobe")
    assert documents[0]["url"] == "http://localhost:8010/documents/17/details"
    assert requests[1].full_url.endswith("/api/documents/17/")


def test_paperless_client_login_recent_documents_and_metadata(monkeypatch: Any) -> None:
    responses = iter(
        [
            JsonResponse({"token": "session-token"}),
            JsonResponse({"id": 7, "title": "Prüfplan", "tags": [3]}),
        ]
    )
    requests: list[urllib.request.Request] = []

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> JsonResponse:
        assert timeout == 15
        requests.append(request)
        return next(responses)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = PaperlessClient(
        Settings(
            paperless_base_url="http://paperless.test",
            paperless_username="service-user",
            paperless_password="secret",
        )
    )
    document = client.get_document(7)
    assert document["document"]["title"] == "Prüfplan"
    assert requests[0].full_url.endswith("/api/token/")
    assert requests[1].get_header("Authorization") == "Token session-token"

    monkeypatch.setattr(
        client,
        "_get",
        lambda path, params=None: {
            "results": [
                {
                    "id": 8,
                    "title": "Aktuell",
                    "added": "2999-01-01T00:00:00Z",
                },
                {
                    "id": 9,
                    "title": "Alt",
                    "added": "2000-01-01T00:00:00Z",
                },
            ]
        },
    )
    recent = client.list_recent_documents(days=30, max_results=500)
    assert [row["id"] for row in recent["documents"]] == [8]


def test_paperless_metadata_reads_all_allowlisted_catalogs(monkeypatch: Any) -> None:
    client = PaperlessClient(Settings(paperless_api_token="token"))
    calls: list[str] = []

    def fake_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
        calls.append(path)
        return {
            "results": [
                {"id": 1, "name": path.strip("/"), "document_count": 2}
            ]
        }

    monkeypatch.setattr(client, "_get", fake_get)
    result = client.list_metadata(max_results=999)
    assert calls == ["/api/tags/", "/api/correspondents/", "/api/document_types/"]
    assert result["tags"][0]["document_count"] == 2
