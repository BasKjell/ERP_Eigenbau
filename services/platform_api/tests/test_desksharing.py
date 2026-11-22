from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from app.desksharing import DesksharingError, DesksharingNotFoundError
from app.main import app, desksharing_service, store
from fastapi.testclient import TestClient

client = TestClient(app)


def setup_function() -> None:
    store.reset()


def future_date(days: int = 7) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def test_seed_contains_two_sites_100_desks_and_50_users() -> None:
    state = store.get()
    assert len(state["desksharing"]["sites"]) == 2
    assert {site["id"] for site in state["desksharing"]["sites"]} == {"BER", "HAM"}
    assert len(state["desksharing"]["desks"]) == 100
    assert len(state["desksharing"]["rooms"]) == 12
    assert len(state["iam"]["users"]) == 50
    assert all("desksharing-user" in user["roles"] for user in state["iam"]["users"])
    assert sum(desk["site_id"] == "BER" for desk in state["desksharing"]["desks"]) == 50
    assert sum(desk["site_id"] == "HAM" for desk in state["desksharing"]["desks"]) == 50
    assert all(desk.get("room_id") for desk in state["desksharing"]["desks"])
    assert all(isinstance(desk.get("map_x"), (int, float)) for desk in state["desksharing"]["desks"])


def test_dashboard_filters_site_and_exposes_features() -> None:
    dashboard = desksharing_service.dashboard("USR-031", future_date(), "HAM", "full_day")
    assert dashboard["current_user"]["site_id"] == "HAM"
    assert dashboard["metrics"]["total_desks"] == 50
    assert len(dashboard["desks"]) == 50
    assert all(desk["site_id"] == "HAM" for desk in dashboard["desks"])
    assert any(desk["accessible"] for desk in dashboard["desks"])
    assert any("Höhenverstellbar" in desk["features"] for desk in dashboard["desks"])
    assert len(dashboard["rooms"]) == 6
    assert all("wayfinding" not in desk for desk in dashboard["desks"])


def test_dashboard_exposes_colleague_location_without_route() -> None:
    dashboard = desksharing_service.dashboard(
        "USR-001", "2026-11-05", "BER", "full_day"
    )

    felix = next(
        person
        for person in dashboard["colleague_locations"]
        if person["user_name"] == "Felix Hoffmann"
    )
    assert felix["desk_id"] == "BER-D012"
    assert felix["room_name"] == "Teamraum Kreuzberg"
    assert felix["floor"] == "EG"
    assert "wayfinding" not in felix
    assert all("wayfinding" not in booking for booking in dashboard["my_bookings"])


def test_desksharing_ui_contains_no_wayfinding_controls_or_route_rendering() -> None:
    page = client.get("/desksharing")
    script = client.get("/assets/desksharing.js")

    assert page.status_code == 200
    assert script.status_code == 200
    assert 'id="info-panel"' in page.text
    assert "Weg anzeigen" not in script.text
    assert "Wegbeschreibung" not in script.text
    assert "wayfinding" not in script.text
    assert "map-route" not in script.text
    assert "data-route-booking" not in script.text


def test_booking_prevents_desk_and_user_double_booking_but_allows_other_half_day() -> None:
    selected_date = future_date()
    first = desksharing_service.create_booking(
        "USR-001", "BER-D002", selected_date, "morning", "API-Test"
    )
    assert first["status"] == "booked"
    assert first["slot_label"] == "Vormittag"

    with pytest.raises(DesksharingError, match="Arbeitsplatz.*belegt"):
        desksharing_service.create_booking(
            "USR-002", "BER-D002", selected_date, "full_day"
        )
    with pytest.raises(DesksharingError, match="bereits einen Arbeitsplatz"):
        desksharing_service.create_booking(
            "USR-001", "BER-D003", selected_date, "morning"
        )

    afternoon = desksharing_service.create_booking(
        "USR-002", "BER-D002", selected_date, "afternoon"
    )
    assert afternoon["desk_id"] == "BER-D002"


def test_booking_lifecycle_owner_permissions_and_admin_override() -> None:
    booking = desksharing_service.create_booking(
        "USR-003", "BER-D004", future_date(), "full_day"
    )
    with pytest.raises(DesksharingError, match="Nur eigene"):
        desksharing_service.cancel_booking(booking["id"], "USR-004")

    checked_in = desksharing_service.check_in(booking["id"], "USR-003")
    assert checked_in["status"] == "checked_in"
    checked_out = desksharing_service.check_out(booking["id"], "USR-003")
    assert checked_out["status"] == "completed"

    other = desksharing_service.create_booking(
        "USR-004", "BER-D005", future_date(8), "full_day"
    )
    cancelled = desksharing_service.cancel_booking(other["id"], "USR-049")
    assert cancelled["status"] == "cancelled"
    admin = desksharing_service.admin_dashboard("USR-049")
    assert admin["desks"] == 100
    assert admin["users"] == 50
    assert admin["audit"][0]["actor_id"] == "USR-049"


def test_invalid_user_desk_slot_and_admin_role_are_rejected() -> None:
    with pytest.raises(DesksharingNotFoundError, match="Benutzer"):
        desksharing_service.dashboard("missing")
    with pytest.raises(DesksharingNotFoundError, match="Arbeitsplatz"):
        desksharing_service.create_booking(
            "USR-001", "NO-DESK", future_date(), "full_day"
        )
    with pytest.raises(DesksharingError, match="Zeitfenster"):
        desksharing_service.dashboard("USR-001", future_date(), "BER", "night")
    with pytest.raises(DesksharingError, match="Administration"):
        desksharing_service.admin_dashboard("USR-002")


def test_desksharing_page_and_api_workflow() -> None:
    page = client.get("/desksharing")
    assert page.status_code == 200
    assert "FLOWSPACE" in page.text
    assert "Platz oder Kollegen finden" in page.text
    assert "Gebäudeplan" in page.text
    assert "Kollegen finden" in page.text

    selected_date = future_date()
    dashboard = client.get(
        "/api/desksharing/dashboard",
        params={
            "user_id": "USR-001",
            "booking_date": selected_date,
            "site_id": "BER",
            "slot": "full_day",
        },
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["metrics"]["total_desks"] == 50

    created = client.post(
        "/api/desksharing/bookings",
        json={
            "user_id": "USR-001",
            "desk_id": "BER-D006",
            "date": selected_date,
            "slot": "full_day",
            "note": "Projekt SCU-100",
        },
    )
    assert created.status_code == 200
    booking_id = created.json()["id"]
    assert client.post(
        f"/api/desksharing/bookings/{booking_id}/check-in",
        json={"actor_id": "USR-001"},
    ).json()["status"] == "checked_in"
    assert client.post(
        f"/api/desksharing/bookings/{booking_id}/check-out",
        json={"actor_id": "USR-001"},
    ).json()["status"] == "completed"


def test_store_upgrade_adds_iam_and_desksharing_without_reset(tmp_path: Path) -> None:
    from app.config import settings
    from app.store import ScenarioStore

    seed = json.loads(settings.seed_file.read_text(encoding="utf-8"))
    existing = json.loads(json.dumps(seed))
    existing.pop("iam")
    existing.pop("desksharing")
    existing["process"][0]["status"] = "done"
    seed_file = tmp_path / "seed.json"
    data_file = tmp_path / "state.json"
    seed_file.write_text(json.dumps(seed), encoding="utf-8")
    data_file.write_text(json.dumps(existing), encoding="utf-8")

    upgraded = ScenarioStore(data_file, seed_file).get()
    assert len(upgraded["iam"]["users"]) == 50
    assert len(upgraded["desksharing"]["desks"]) == 100
    assert len(upgraded["desksharing"]["rooms"]) == 12
    assert upgraded["process"][0]["status"] == "done"


def test_store_upgrade_enriches_existing_desksharing_layout(tmp_path: Path) -> None:
    from app.config import settings
    from app.store import ScenarioStore

    seed = json.loads(settings.seed_file.read_text(encoding="utf-8"))
    existing = json.loads(json.dumps(seed))
    existing["desksharing"].pop("rooms")
    existing["desksharing"]["sites"][0].pop("building_code")
    existing["desksharing"]["sites"][0].pop("entry_label")
    for key in ("room_id", "map_x", "map_y"):
        existing["desksharing"]["desks"][0].pop(key)
    seed_file = tmp_path / "seed.json"
    data_file = tmp_path / "state.json"
    seed_file.write_text(json.dumps(seed), encoding="utf-8")
    data_file.write_text(json.dumps(existing), encoding="utf-8")

    upgraded = ScenarioStore(data_file, seed_file).get()["desksharing"]

    assert len(upgraded["rooms"]) == 12
    assert upgraded["sites"][0]["building_code"] == "BER-01"
    assert upgraded["desks"][0]["room_id"] == "BER-EG-FOK"
    assert upgraded["desks"][0]["map_x"] == 10
