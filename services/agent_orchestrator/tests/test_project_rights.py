"""Projektkatalog mit Projektrechten aus den AD-Gruppen (agents/projects.json).

Aufträge einreichen und Arbeitspakete starten nur mit Änderungsrecht im Projekt, entscheiden nur als
Projektmitglied, nur Änderungsbereiche des Projekts und mindestens die Kritikalität des Projekts.
"""

from __future__ import annotations

import json

import pytest

from flowagents.engine import EngineError

from .conftest import AGENTS_DIR, KEY_USER, PO, TECH_LEAD, auftrag, drive, open_decision

CATALOG = {
    "FLOW-DMS": {"title": "FLOWDOC", "domain": "it", "criticality": "K1", "scopes": ["doku"]},
    "TM-100": {"title": "Testprodukt", "domain": "produkt", "criticality": "K2", "scopes": ["doku"],
               "packages": [
                   {"key": "AP-1", "title": "Lastenheft", "result": "Lastenheft", "v_level": "anforderungen",
                    "acceptance": "freigegeben", "wave": 1, "depends_on": [], "scope": "doku"},
                   {"key": "AP-2", "title": "Architektur", "result": "Architektur", "v_level": "systemarchitektur",
                    "acceptance": "deckt AP-1 ab", "wave": 1, "depends_on": ["AP-1"], "scope": "doku"},
               ]},
}


def person(base: dict, *rights: str) -> dict:
    return {**base, "roles": [*base["roles"], *rights]}


PO_DMS = person(PO, "flow-prj-flow-dms-lesen", "flow-prj-flow-dms-aendern")
PO_TM = person(PO, "flow-prj-tm-100-lesen", "flow-prj-tm-100-aendern")
PO_READ = person(PO, "flow-prj-flow-dms-lesen")
TL_TM = person(TECH_LEAD, "flow-prj-tm-100-lesen", "flow-prj-tm-100-aendern")
KEY_DMS = person(KEY_USER, "flow-prj-flow-dms-lesen")


@pytest.fixture()
def engine(make_engine):  # noqa: ANN001, ANN201
    return make_engine(projects=CATALOG)


def test_submit_needs_change_right_in_the_project(engine) -> None:  # noqa: ANN001
    with pytest.raises(EngineError, match="Änderungsrecht fehlt"):
        engine.submit(auftrag(), PO, "pr-0001-test")
    with pytest.raises(EngineError, match="Änderungsrecht fehlt"):
        engine.submit(auftrag(), PO_READ, "pr-0002-test")
    run = engine.submit(auftrag(), PO_DMS, "pr-0003-test")
    assert run["auftrag"]["project"] == "FLOW-DMS"


def test_project_outside_the_catalog_is_rejected(engine) -> None:  # noqa: ANN001
    with pytest.raises(EngineError, match="nicht im Projektkatalog"):
        engine.submit(auftrag(project="FLOW-XYZ"), PO_DMS, "pr-0004-test")


def test_project_scopes_are_resolved_and_validated(make_engine) -> None:  # noqa: ANN001
    engine = make_engine(projects={**CATALOG, "FLOW-DMS": {**CATALOG["FLOW-DMS"], "scopes": ["doku"]},
                                   "OTHER": {"title": "x", "scopes": ["doku"]}})
    assert engine.project_scopes("FLOW-DMS") == ["doku"]
    with pytest.raises(EngineError, match="Änderungsbereiche"):
        make_engine(projects={"FLOW-DMS": {"title": "x", "scopes": ["gibt-es-nicht"]}})


def test_project_sets_minimum_criticality_and_domain(engine) -> None:  # noqa: ANN001
    values = auftrag(project="TM-100", project_class="S", criticality="K1")
    values.pop("change_class")
    run = engine.submit(values, PO_TM, "pr-0005-test")
    assert run["auftrag"]["criticality"] == "K2" and run["change_class"] == "kritisch"
    assert run["auftrag"]["domain"] == "produkt"


def test_deciding_needs_project_membership(engine) -> None:  # noqa: ANN001
    run = engine.submit(auftrag(), PO_DMS, "pr-0006-test")
    drive(engine)
    decision = open_decision(engine, run["id"])
    assert decision["gate"] == "G4"
    with pytest.raises(EngineError, match="Projektmitgliedschaft fehlt"):
        engine.decide(decision["id"], KEY_USER, "annehmen", "geprüft")
    engine.decide(decision["id"], KEY_DMS, "annehmen", "geprüft")


def test_catalog_projects_are_seeded_once_with_their_packages(engine) -> None:  # noqa: ANN001
    assert engine.seed_projects() == ["PRJ-TM-100"]
    assert engine.seed_projects() == []
    project = engine.store.project("PRJ-TM-100")
    summary = engine.project_summary(project)
    assert summary["code"] == "TM-100" and summary["catalog"] is True
    assert {p["key"]: p["status"] for p in summary["packages"]} == {"AP-1": "bereit", "AP-2": "geplant"}
    assert engine.store.run(project["run_id"])["status"] == "abgeschlossen"


def test_package_start_needs_change_right_in_the_project(engine) -> None:  # noqa: ANN001
    engine.seed_projects()
    with pytest.raises(EngineError, match="Änderungsrecht fehlt"):
        engine.start_package("PRJ-TM-100", "AP-1", PO_DMS)
    child = engine.start_package("PRJ-TM-100", "AP-1", TL_TM)
    assert child["auftrag"]["project"] == "TM-100" and child["change_class"] == "kritisch"


def test_legacy_runs_outside_the_catalog_stay_open_to_all(make_engine) -> None:  # noqa: ANN001
    legacy = make_engine()
    run = legacy.submit(auftrag(project="FLOW-ALT"), PO, "pr-0007-test")
    drive(legacy)
    engine = make_engine(projects=CATALOG)
    decision = open_decision(engine, run["id"])
    engine.decide(decision["id"], KEY_USER, "annehmen", "geprüft")


def test_overview_publishes_the_catalog_with_ad_groups(engine) -> None:  # noqa: ANN001
    catalog = engine.overview()["project_catalog"]
    assert catalog["TM-100"]["roles"] == {"lesen": "flow-prj-tm-100-lesen", "aendern": "flow-prj-tm-100-aendern"}
    assert catalog["TM-100"]["groups"]["aendern"] == "AD-GG-FLOW-PRJ-TM-100-AENDERN"


def test_repository_catalog_matches_scopes_and_iam_generator() -> None:
    projects = json.loads((AGENTS_DIR / "projects.json").read_text(encoding="utf-8"))["projects"]
    assert {"FLOW-PLATFORM", "FLOW-DMS", "TM-100", "PS-TM100"} <= set(projects)
    realm = json.loads((AGENTS_DIR.parent / "deployment" / "keycloak" / "realm.json").read_text(encoding="utf-8"))
    groups = {g["name"] for g in realm["groups"]}
    for code in projects:
        assert f"AD-GG-FLOW-PRJ-{code}-AENDERN" in groups and f"AD-GG-FLOW-PRJ-{code}-LESEN" in groups
    admin = next(u for u in realm["users"] if u["username"] == "admin.demo")
    assert all(f"/AD-GG-FLOW-PRJ-{code}-AENDERN" in admin["groups"] for code in projects)
