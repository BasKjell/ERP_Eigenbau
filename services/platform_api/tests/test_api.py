from app.config import settings
from app.main import app, store
from fastapi.testclient import TestClient

client = TestClient(app)


def setup_function() -> None:
    store.reset()


def test_health_and_initial_state() -> None:
    assert client.get("/health").json()["status"] == "ok"
    state = client.get("/api/demo").json()
    assert state["order"]["id"] == "SO-4711"
    assert state["order"]["product"] == "SCU-100"
    assert len(state["process"]) == 12


def test_process_can_advance() -> None:
    before = client.get("/api/demo").json()
    after = client.post("/api/demo/advance").json()
    assert after["metrics"]["completed_steps"] == before["metrics"]["completed_steps"] + 1
    assert after["process"][0]["status"] == "done"


def test_quality_failure_blocks_progress_until_rework() -> None:
    failed = client.post("/api/demo/failure").json()
    assert failed["quality_incident"]["status"] == "open"
    assert failed["order"]["delivery_risk"] == "at_risk"
    assert client.post("/api/demo/advance").status_code == 409

    reworked = client.post("/api/demo/rework").json()
    assert reworked["quality_incident"]["status"] == "resolved"
    assert reworked["order"]["delivery_risk"] == "on_track"
    assert client.post("/api/demo/advance").status_code == 200


def test_assistant_is_grounded_in_order_and_sources() -> None:
    result = client.post(
        "/api/assistant/ask", json={"question": "Wie ist der Status von Auftrag 4711?"}
    ).json()
    assert "Auftrag 4711" in result["answer"]
    assert result["sources"]
    assert result["mode"] in {"deterministic", "ollama"}


def test_unknown_stage_returns_404() -> None:
    assert client.post("/api/demo/stage/not-real").status_code == 404


def test_all_document_files_are_declared() -> None:
    assert settings.seed_file.exists()
    state = store.get()
    assert {doc["id"] for doc in state["documents"]} == {
        "DOC-DRW-100",
        "DOC-WI-100",
        "DOC-QP-100",
        "DOC-CERT-MB",
        "DOC-ATP-4711",
    }
