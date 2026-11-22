import io
import json
import urllib.request
from pathlib import Path
from typing import Any

from app.assistant import answer_question
from app.business_tools import select_read_tools, sources_from_results
from app.config import Settings, settings
from app.store import ScenarioStore


class JsonResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.stream = io.BytesIO(json.dumps(payload).encode())

    def __enter__(self) -> "JsonResponse":
        return self

    def __exit__(self, *args: object) -> None:
        self.stream.close()

    def read(self, size: int = -1) -> bytes:
        return self.stream.read(size)


def _store(tmp_path: Path) -> ScenarioStore:
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(settings.seed_file.read_text(encoding="utf-8"), encoding="utf-8")
    return ScenarioStore(tmp_path / "state.json", seed_file)


def test_deterministic_assistant_covers_production_documents_and_capacity(
    tmp_path: Path,
) -> None:
    local_store = _store(tmp_path)
    production = local_store.set_stage("production")

    result = answer_question("Welche Fertigung ist aktiv?", production, Settings())
    assert "WO-2027-0042" in result["answer"]
    assert result["tools_used"] == ["list_production_orders"]

    documents = answer_question("Welche Dokumentrevision gilt?", production, Settings())
    assert documents["tools_used"] == ["search_documents"]
    assert any(source["reference"] == "DOC-DRW-100" for source in documents["sources"])

    capacity = answer_question("Wo ist der Kapazitätsengpass?", production, Settings())
    assert "Auslastung" in capacity["answer"]
    assert any(source["system"] == "MES" for source in capacity["sources"])


def test_assistant_explains_open_quality_incident(tmp_path: Path) -> None:
    local_store = _store(tmp_path)
    state = local_store.inject_failure()
    result = answer_question("Warum gibt es eine Abweichung?", state, Settings())
    assert "NCR-2027-0017" in result["answer"]
    assert result["sources"][0]["system"] == "MES"


def test_ollama_answer_uses_allowlisted_tools_and_cleans_model_output(
    tmp_path: Path, monkeypatch: Any
) -> None:
    local_store = _store(tmp_path)
    state = local_store.set_stage("production")

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> JsonResponse:
        assert request.full_url == "http://ollama.test/api/generate"
        assert timeout == 2
        payload = json.loads(request.data or b"{}")
        assert "list_production_orders" in payload["prompt"]
        return JsonResponse(
            {"response": "<think>intern</think> **WO-2027-0042** ist aktiv."}
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = answer_question(
        "Welche Produktion ist aktiv?",
        state,
        Settings(
            ai_mode="ollama",
            ollama_base_url="http://ollama.test",
            ollama_timeout_seconds=2,
        ),
    )
    assert result["mode"] == "ollama"
    assert result["answer"] == "WO-2027-0042 ist aktiv."
    assert result["tools_used"] == ["list_production_orders"]


def test_tool_selection_and_sources_cover_document_and_fallback_paths(
    tmp_path: Path,
) -> None:
    state = _store(tmp_path).get()
    assert select_read_tools("Zeige das Dokument für SCU", state)[0]["tool"] == "search_documents"
    assert select_read_tools("Allgemeiner Status", state)[0]["tool"] == "get_order_status"

    sources = sources_from_results(
        [
            {
                "tool": "example",
                "orders": [{"id": "PO-1"}],
                "documents": [{"id": "DOC-1", "title": "Plan"}],
            },
            {
                "tool": "duplicate",
                "source": {"system": "ERPNext", "reference": "PO-1"},
            },
        ]
    )
    assert {(source["system"], source["reference"]) for source in sources} == {
        ("ERPNext", "PO-1"),
        ("Paperless", "DOC-1"),
    }
