from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import settings
from app.main import app, store
from app.store import ScenarioStore
from fastapi.testclient import TestClient

client = TestClient(app)


def setup_function() -> None:
    store.reset()


def test_flowq_page_dashboard_and_management_tour_are_connected() -> None:
    page = client.get("/quality")
    dashboard = client.get("/api/quality/dashboard")
    launcher = client.get("/assets/app-launcher.js")

    assert page.status_code == 200
    assert "FLOWQ" in page.text
    assert "Wareneingang prüfen" in page.text
    assert "data-app-launcher" in page.text
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["product"] == "FLOWQ"
    assert body["metrics"]["open_receipts"] == 3
    assert len(body["receipts"]) == 3
    assert body["receipts"][0]["plan"]["work_test_plan_id"] == "TP-0001"
    assert body["interfaces"]["measurement_endpoint"] == "/api/quality/v1/measurements"
    assert "Wareneingang einfach prüfen" in launcher.text
    assert "Jama-Connect-Funktionsumfang" in launcher.text


def test_aql_sampling_is_deterministic_and_gateway_is_idempotent() -> None:
    started = client.post(
        "/api/quality/inspections",
        json={"receipt_id": "PREC-2027-0045", "operator_id": "QOP-001"},
    )
    assert started.status_code == 200
    inspection = started.json()
    assert inspection["sample_size"] == 8
    assert inspection["acceptance_number"] == 0
    assert inspection["rejection_number"] == 1
    assert len(set(inspection["sample_refs"])) == 8

    repeated = client.post(
        "/api/quality/inspections",
        json={"receipt_id": "PREC-2027-0045", "operator_id": "QOP-001"},
    )
    assert repeated.status_code == 200
    assert repeated.json()["id"] == inspection["id"]

    payload = {
        "inspection_id": inspection["id"],
        "characteristic_id": "PCB-WIDTH",
        "sample_ref": inspection["sample_refs"][0],
        "value": 100.02,
        "unit": "mm",
        "instrument_id": "MM-CAL-001",
        "source": "rest",
        "external_event_id": "EDGE-01-4711",
        "actor_id": "FLOWQ-EDGE-01",
    }
    first = client.post("/api/quality/v1/measurements", json=payload)
    replay = client.post("/api/quality/v1/measurements", json=payload)
    assert first.status_code == 200
    assert first.json()["status"] == "passed"
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]
    assert replay.json()["idempotent_replay"] is True


def test_expired_instrument_is_rejected_and_can_be_calibrated() -> None:
    inspection = client.post(
        "/api/quality/inspections",
        json={"receipt_id": "PREC-2027-0045", "operator_id": "QOP-001"},
    ).json()
    measurement = {
        "characteristic_id": "PCB-WIDTH",
        "sample_ref": inspection["sample_refs"][0],
        "value": 100,
        "unit": "mm",
        "instrument_id": "MM-CAL-OLD",
        "source": "manual",
        "actor_id": "QOP-001",
    }
    blocked = client.post(
        f"/api/quality/inspections/{inspection['id']}/measurements",
        json=measurement,
    )
    assert blocked.status_code == 409
    assert "kalibriert" in blocked.json()["detail"]

    calibrated = client.post(
        "/api/quality/instruments/MM-CAL-OLD/calibration",
        json={
            "actor_id": "QOP-002",
            "calibrated_at": "2026-11-05",
            "valid_until": "2030-11-05",
            "certificate_document_id": "DMS-CAL-NEW",
        },
    )
    assert calibrated.status_code == 200
    assert calibrated.json()["calibration_state"] == "valid"
    accepted = client.post(
        f"/api/quality/inspections/{inspection['id']}/measurements",
        json=measurement,
    )
    assert accepted.status_code == 200


def _record_full_inspection(
    inspection: dict[str, Any], *, failing_sample: str | None = None
) -> None:
    for sample in inspection["sample_refs"]:
        for characteristic in inspection["plan"]["characteristics"]:
            if characteristic["type"] == "numeric":
                value = characteristic["target"]
                if sample == failing_sample:
                    value = characteristic["max_value"] + 10
                instrument_id = (
                    "MM-DMM-001"
                    if "multimeter" in characteristic.get("instrument_types", [])
                    else "MM-CAL-001"
                )
            else:
                value = sample != failing_sample
                instrument_id = None
            response = client.post(
                f"/api/quality/inspections/{inspection['id']}/measurements",
                json={
                    "characteristic_id": characteristic["id"],
                    "sample_ref": sample,
                    "value": value,
                    "unit": characteristic.get("unit", ""),
                    "instrument_id": instrument_id,
                    "source": "manual",
                    "actor_id": "QOP-001",
                },
            )
            assert response.status_code == 200, response.text


def test_completed_inspection_prepares_erp_and_dms_release() -> None:
    inspection = client.post(
        "/api/quality/inspections",
        json={"receipt_id": "PREC-2027-0047", "operator_id": "QOP-001"},
    ).json()
    assert inspection["sample_size"] == 5
    _record_full_inspection(inspection)

    completed = client.post(
        f"/api/quality/inspections/{inspection['id']}/complete",
        json={"actor_id": "QOP-001"},
    )
    assert completed.status_code == 200
    body = completed.json()
    assert body["decision"] == "accepted"
    assert body["receipt"]["target_warehouse"] == "Elektroniklager - OMD"
    assert body["erp_sync"]["doctype"] == "Quality Inspection"
    assert body["erp_sync"]["payload"]["reference_name"] == "PREC-2027-0047"
    assert body["dms_protocol"]["document_type"] == "Wareneingangsprüfprotokoll"

    preview = client.post(
        f"/api/quality/inspections/{inspection['id']}/erp-sync",
        json={"actor_id": "QOP-001", "confirm": False},
    )
    assert preview.status_code == 200
    assert preview.json()["status"] == "pending"

    synced = client.post(
        f"/api/quality/inspections/{inspection['id']}/erp-sync",
        json={"actor_id": "QOP-001", "confirm": True},
    )
    assert synced.status_code == 200
    assert synced.json()["status"] == "synced"
    assert synced.json()["erp_reference"].startswith("DEMO-QI-IN-")


def test_failed_sample_blocks_lot_and_opens_ncr() -> None:
    inspection = client.post(
        "/api/quality/inspections",
        json={"receipt_id": "PREC-2027-0046", "operator_id": "QOP-001"},
    ).json()
    _record_full_inspection(inspection, failing_sample=inspection["sample_refs"][0])
    completed = client.post(
        f"/api/quality/inspections/{inspection['id']}/complete",
        json={"actor_id": "QOP-001"},
    )

    assert completed.status_code == 200
    body = completed.json()
    assert body["decision"] == "rejected"
    assert body["receipt"]["target_warehouse"] == "Sperrlager - OMD"
    assert body["ncr_id"] == "NCR-WE-0001"


def test_existing_state_is_upgraded_with_quality_domain(tmp_path: Path) -> None:
    seed = json.loads(settings.seed_file.read_text(encoding="utf-8"))
    existing = json.loads(json.dumps(seed))
    existing.pop("quality")
    seed_file = tmp_path / "seed.json"
    data_file = tmp_path / "data.json"
    seed_file.write_text(json.dumps(seed), encoding="utf-8")
    data_file.write_text(json.dumps(existing), encoding="utf-8")

    upgraded = ScenarioStore(data_file, seed_file).get()

    assert upgraded["quality"]["receipts"][0]["id"] == "PREC-2027-0045"
    assert upgraded["quality"]["inspection_plans"][0]["id"] == "IP-PCB-MAIN-42"
