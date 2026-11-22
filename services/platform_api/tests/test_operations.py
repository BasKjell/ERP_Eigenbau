import json
from pathlib import Path
from typing import Any

from app import main as main_module
from app.config import Settings, settings
from app.operations import readiness_report
from app.store import ScenarioStore
from fastapi.testclient import TestClient


def _store_with_documents(tmp_path: Path) -> tuple[ScenarioStore, Path]:
    seed = json.loads(settings.seed_file.read_text(encoding="utf-8"))
    seed_file = tmp_path / "seed.json"
    data_file = tmp_path / "state.json"
    document_dir = tmp_path / "documents"
    document_dir.mkdir()
    seed_file.write_text(json.dumps(seed), encoding="utf-8")
    for document in seed["documents"]:
        (document_dir / document["filename"]).write_bytes(b"%PDF-1.4\n%%EOF\n")
    return ScenarioStore(data_file, seed_file), document_dir


def test_readiness_checks_state_documents_and_required_integrations(
    tmp_path: Path, monkeypatch: Any
) -> None:
    local_store, document_dir = _store_with_documents(tmp_path)
    monkeypatch.setattr(
        "app.operations.integration_status",
        lambda _: [
            {
                "name": "ERPNext",
                "configured": True,
                "reachable": True,
            },
            {
                "name": "Paperless-ngx",
                "configured": True,
                "reachable": True,
            },
        ],
    )

    report = readiness_report(
        local_store,
        Settings(
            data_file=local_store.data_file,
            seed_file=local_store.seed_file,
            document_dir=document_dir,
            readiness_require_integrations=True,
        ),
    )

    assert report["ready"] is True
    assert {check["name"] for check in report["checks"]} == {
        "state-store",
        "documents",
        "external-integrations",
    }


def test_readiness_fails_for_missing_document_and_required_dependency(
    tmp_path: Path, monkeypatch: Any
) -> None:
    local_store, document_dir = _store_with_documents(tmp_path)
    first_document = local_store.get()["documents"][0]["filename"]
    (document_dir / first_document).unlink()
    monkeypatch.setattr(
        "app.operations.integration_status",
        lambda _: [
            {
                "name": "ERPNext",
                "configured": False,
                "reachable": False,
            }
        ],
    )

    report = readiness_report(
        local_store,
        Settings(
            data_file=local_store.data_file,
            seed_file=local_store.seed_file,
            document_dir=document_dir,
            readiness_require_integrations=True,
        ),
    )

    assert report["status"] == "not_ready"
    assert report["ready"] is False
    assert first_document in next(
        check["detail"] for check in report["checks"] if check["name"] == "documents"
    )


def test_readiness_treats_external_systems_as_optional_in_demo_mode(
    tmp_path: Path, monkeypatch: Any
) -> None:
    local_store, document_dir = _store_with_documents(tmp_path)
    monkeypatch.setattr(
        "app.operations.integration_status",
        lambda _: [
            {
                "name": "ERPNext",
                "configured": False,
                "reachable": False,
            }
        ],
    )

    report = readiness_report(
        local_store,
        Settings(document_dir=document_dir, readiness_require_integrations=False),
    )

    assert report["ready"] is True
    integration_check = next(
        check for check in report["checks"] if check["name"] == "external-integrations"
    )
    assert integration_check["required"] is False
    assert integration_check["ok"] is False


def test_api_adds_security_headers_and_returns_503_when_not_ready(
    monkeypatch: Any,
) -> None:
    test_client = TestClient(main_module.app)
    health = test_client.get("/health")
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "SAMEORIGIN"
    assert health.headers["referrer-policy"] == "no-referrer"
    assert health.headers["cache-control"] == "no-store"

    monkeypatch.setattr(
        main_module,
        "readiness_report",
        lambda *_: {"status": "not_ready", "ready": False, "checks": []},
    )
    response = test_client.get("/ready")
    assert response.status_code == 503
    assert response.json()["ready"] is False
