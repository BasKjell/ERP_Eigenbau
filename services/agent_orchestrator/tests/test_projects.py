"""Großprojekte mit Arbeitspaketen (KI-Softwareentwicklung nach dem V-Modell, Teil 01, Stufe 2).

Ein L-Lauf plant Arbeitspakete und endet an EP1. Danach entsteht ein Projekt; jedes Paket läuft
als eigener Auftrag durch das V, sobald seine Vorgänger fertig sind (EPi „Iteration geplant“).
"""

from __future__ import annotations

import pytest

from flowagents.engine import EngineError
from flowagents.sync import PlatformSync

from .conftest import KEY_USER, NOBODY, PO, RELEASE, TECH_LEAD, auftrag, drive, open_decision


def define_project(engine):  # noqa: ANN001, ANN201
    values = auftrag(project_class="L", criticality="K1", title="Neue Dokumentenablage für den Einkauf")
    values.pop("change_class")
    run = engine.submit(values, PO, "prj-0001-test")
    drive(engine)
    engine.decide(open_decision(engine, run["id"])["id"], PO, "annehmen", "Projekt definiert")
    drive(engine)
    project = engine.store.project_for_run(run["id"])
    assert project is not None
    return run, project


def finish(engine, run_id: str) -> None:  # noqa: ANN001
    """Ein Paketlauf im Kurzweg bis zum Abschluss (Fachabnahme und Produktion)."""
    drive(engine)
    engine.decide(open_decision(engine, run_id)["id"], KEY_USER, "annehmen", "geprüft")
    drive(engine)
    engine.decide(open_decision(engine, run_id)["id"], RELEASE, "annehmen", "ok")
    assert engine.store.run(run_id)["status"] == "abgeschlossen"


def test_ep1_creates_a_project_with_the_planned_work_packages(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run, project = define_project(engine)
    assert project["id"] == "PRJ-" + run["auftrag_id"].split("-")[1]
    assert [p["key"] for p in project["packages"]] == ["AP-1", "AP-2", "AP-3", "AP-4", "AP-5"]
    summary = engine.project_summary(project)
    states = {p["key"]: p["status"] for p in summary["packages"]}
    assert states == {"AP-1": "bereit", "AP-2": "geplant", "AP-3": "geplant", "AP-4": "geplant", "AP-5": "geplant"}
    assert summary["status"] == "definiert" and summary["current_wave"] == 1
    assert any("Arbeitspaketen angelegt" in e["message"] for e in engine.store.events(run_id=run["id"]))


def test_package_starts_as_own_run_in_the_short_path(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    _, project = define_project(engine)
    child = engine.start_package(project["id"], "AP-1", PO)
    assert child["auftrag"]["project_id"] == project["id"] and child["auftrag"]["package_key"] == "AP-1"
    assert child["auftrag"]["project_class"] == "S" and child["change_class"] == "standard"
    assert child["auftrag"]["scope"] == "doku"
    # Erneutes Starten liefert denselben Lauf, kein zweiter Auftrag.
    assert engine.start_package(project["id"], "AP-1", PO)["id"] == child["id"]
    assert len(engine.store.runs()) == 2
    summary = engine.project_summary(engine.store.project(project["id"]))
    assert summary["status"] == "in_arbeit"
    assert next(p for p in summary["packages"] if p["key"] == "AP-1")["auftrag_id"] == child["auftrag_id"]


def test_dependencies_must_be_finished_before_a_package_starts(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    _, project = define_project(engine)
    with pytest.raises(EngineError, match="Vorgänger"):
        engine.start_package(project["id"], "AP-2", PO, "doku")
    child = engine.start_package(project["id"], "AP-1", PO)
    finish(engine, child["id"])
    states = {p["key"]: p["status"] for p in engine.project_summary(engine.store.project(project["id"]))["packages"]}
    assert states["AP-1"] == "fertig" and states["AP-2"] == "bereit"


def test_package_without_scope_needs_one_from_the_person(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    _, project = define_project(engine)
    finish(engine, engine.start_package(project["id"], "AP-1", PO)["id"])
    with pytest.raises(EngineError, match="Änderungsbereich"):
        engine.start_package(project["id"], "AP-2", TECH_LEAD)
    with pytest.raises(EngineError, match="Änderungsbereich"):
        engine.start_package(project["id"], "AP-2", TECH_LEAD, "unbekannt")
    child = engine.start_package(project["id"], "AP-2", TECH_LEAD, "doku")
    assert child["auftrag"]["scope"] == "doku" and child["requested_by"]["username"] == TECH_LEAD["username"]


def test_only_product_owner_or_tech_lead_start_packages(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    _, project = define_project(engine)
    with pytest.raises(EngineError, match="Befugnis"):
        engine.start_package(project["id"], "AP-1", NOBODY)
    with pytest.raises(EngineError, match="nicht gefunden"):
        engine.start_package("PRJ-999", "AP-1", PO)
    with pytest.raises(EngineError, match="nicht gefunden"):
        engine.start_package(project["id"], "AP-9", PO)


def test_project_is_complete_when_all_packages_are_finished(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    _, project = define_project(engine)
    for key in ("AP-1", "AP-2", "AP-3", "AP-4", "AP-5"):
        finish(engine, engine.start_package(project["id"], key, PO, "doku")["id"])
    summary = engine.project_summary(engine.store.project(project["id"]))
    assert summary["status"] == "abgeschlossen" and summary["progress"] == 100
    assert summary["ep"].startswith("EP9")


def test_cancelled_package_is_shown_as_stopped(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    _, project = define_project(engine)
    child = engine.start_package(project["id"], "AP-1", PO)
    engine.control("cancel", TECH_LEAD, run_id=child["id"])
    states = {p["key"]: p["status"] for p in engine.project_summary(engine.store.project(project["id"]))["packages"]}
    assert states["AP-1"] == "gestoppt" and states["AP-2"] == "geplant"


def test_overview_and_run_detail_show_the_project(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run, project = define_project(engine)
    child = engine.start_package(project["id"], "AP-1", PO)
    overview = engine.overview()
    assert overview["projects"][0]["id"] == project["id"]
    child_summary = next(r for r in overview["runs"] if r["id"] == child["id"])
    assert child_summary["project_id"] == project["id"] and child_summary["package_key"] == "AP-1"
    assert engine.run_detail(child["id"])["project"]["id"] == project["id"]
    assert engine.run_detail(run["id"])["project"]["id"] == project["id"]


def test_package_start_arrives_through_the_platform_sync(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    _, project = define_project(engine)
    sync = PlatformSync(engine, "http://127.0.0.1:1", "x" * 40)
    result = sync.execute({"kind": "start_package", "person": PO,
                           "payload": {"project_id": project["id"], "package_key": "AP-1"}})
    assert result["status"] == 201 and result["body"]["auftrag"]["package_key"] == "AP-1"
    denied = sync.execute({"kind": "start_package", "person": NOBODY,
                           "payload": {"project_id": project["id"], "package_key": "AP-1"}})
    assert denied["status"] == 403


def test_k2_project_passes_its_criticality_to_the_packages(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    values = auftrag(project_class="L", criticality="K2", title="Firmware-Update über Servicezugang")
    values.pop("change_class")
    run = engine.submit(values, PO, "prj-k2-0001")
    drive(engine)
    engine.decide(open_decision(engine, run["id"])["id"], PO, "annehmen", "ok")
    drive(engine)
    project = engine.store.project_for_run(run["id"])
    child = engine.start_package(project["id"], "AP-1", PO)
    assert child["auftrag"]["criticality"] == "K2" and child["change_class"] == "kritisch"
