"""Regressionstests zum unabhängigen Review (Codex, Basis 879043a, Head d9b7fa1).

A · Ablauf und Gates: Einstufung (A1), Registerbindung (A2), Integrationstests je Fall (A3),
EP1-Prüfungen (A4), atomare Übergänge (A5), Abschlussarten (A6).
B · Projektrechte: Auskunft erst nach Projektrecht (B1), Katalogbindung bleibt erhalten (B3).
B2 und B4 testet die Plattform (services/platform_api/tests/test_project_rights_demo.py).
"""

from __future__ import annotations

import dataclasses

import pytest

from flowagents.engine import EngineError, _case_results, _cycles
from flowagents.registry import Step
from flowagents.sandbox import LocalCheck

from .conftest import KEY_USER, PO, RELEASE, TECH_LEAD, auftrag, drive, open_decision
from .test_project_rights import CATALOG, PO_DMS, PO_TM, TL_TM, person

PLATFORM_ADMIN = {"username": "betrieb", "name": "Betrieb", "roles": ["platform-admin"]}
TL_DMS = person(TECH_LEAD, "flow-prj-flow-dms-lesen", "flow-prj-flow-dms-aendern")


def submit(engine, idem: str = "rv-0001-test", user: dict | None = None, **overrides):  # noqa: ANN001, ANN201
    return engine.submit(auftrag(**overrides), user or PO, idem)


def with_registry_change(engine, *, insert_before: str | None = None) -> None:  # noqa: ANN001
    """Simuliert eine Registeränderung; optional verschiebt ein neuer (nicht anwendbarer) Schritt die Indizes."""
    steps = list(engine.registry.steps)
    if insert_before:
        extra = Step(id="neuer_schritt", label="Neuer Schritt", kind="create", role="planung", produces="plan",
                     when={"project_class": ("L",)})
        steps.insert(engine.registry.step_index(insert_before), extra)
    engine.registry = dataclasses.replace(engine.registry, steps=tuple(steps), digest=engine.registry.digest + "-neu")


# =====================================================================================
# Wichtigste Regression 1 (B1): projektfremder PO erfährt beim erneuten Start nichts
# =====================================================================================
def test_foreign_po_gets_neither_run_nor_dependency_information(make_engine) -> None:  # noqa: ANN001
    engine = make_engine(projects=CATALOG)
    engine.seed_projects()
    child = engine.start_package("PRJ-TM-100", "AP-1", PO_TM)
    for key in ("AP-1", "AP-2"):  # AP-1 läuft bereits, AP-2 hat einen offenen Vorgänger
        with pytest.raises(EngineError) as denied:
            engine.start_package("PRJ-TM-100", key, PO_DMS)
        message = str(denied.value)
        assert "Keine Befugnis im Projekt TM-100" in message
        assert child["id"] not in message and child["auftrag_id"] not in message and "Vorgänger" not in message
    assert engine.start_package("PRJ-TM-100", "AP-1", PO_TM)["id"] == child["id"], "Berechtigte bekommen den Lauf"


def test_cancel_needs_the_project_right_or_cross_project_operations(make_engine) -> None:  # noqa: ANN001
    engine = make_engine(projects=CATALOG)
    engine.seed_projects()
    child = engine.start_package("PRJ-TM-100", "AP-1", PO_TM)
    with pytest.raises(EngineError, match="Keine Befugnis im Projekt TM-100"):
        engine.control("cancel", TL_DMS, run_id=child["id"])  # Tech Lead eines anderen Projekts
    assert engine.store.run(child["id"])["status"] != "abgebrochen"
    engine.control("cancel", TL_TM, run_id=child["id"])
    assert engine.store.run(child["id"])["status"] == "abgebrochen"


def test_platform_operations_may_cancel_across_projects(make_engine) -> None:  # noqa: ANN001
    engine = make_engine(projects=CATALOG)
    engine.seed_projects()
    child = engine.start_package("PRJ-TM-100", "AP-1", PO_TM)
    engine.control("cancel", PLATFORM_ADMIN, run_id=child["id"])
    assert engine.store.run(child["id"])["status"] == "abgebrochen"


# =====================================================================================
# Wichtigste Regression 2 (A2): Entscheidung vor Registeränderung löst nichts aus
# =====================================================================================
@pytest.mark.parametrize("gate", ["G4", "G5"])
def test_gate_decision_opened_before_a_registry_change_cannot_adopt_or_finish(make_engine, gate) -> None:  # noqa: ANN001
    adopted: list[str] = []

    class Adoption:
        def adopt(self, run, refs, *, approved_by, digest):  # noqa: ANN001, ANN201
            adopted.append(run["id"])
            return {"branch": "agent/x", "commit": "0" * 40, "pushed": False}

    engine = make_engine(adoption=Adoption())
    run = submit(engine)
    drive(engine)
    decision = open_decision(engine, run["id"])
    if gate == "G5":
        engine.decide(decision["id"], KEY_USER, "annehmen", "geprüft")
        adopted.clear()
        drive(engine)
        decision = open_decision(engine, run["id"])
    assert decision["gate"] == gate
    with_registry_change(engine, insert_before=gate)
    decider = KEY_USER if gate == "G4" else RELEASE
    with pytest.raises(EngineError, match="verfallen"):
        engine.decide(decision["id"], decider, "annehmen", "ok")
    current = engine.store.run(run["id"])
    assert adopted == [], "keine Übernahme durch eine verfallene Entscheidung"
    if gate == "G4":
        assert engine.store.latest_artifact(run["id"], "uebernahme") is None
    assert current["status"] == "blockiert" and current["completion"] == ""
    assert engine.store.decision(decision["id"])["status"] == "verfallen"
    # Der Tech Lead bewertet neu; der Lauf kehrt über die stabile Schritt-ID an dasselbe Gate zurück,
    # obwohl sich der Index durch den neuen Schritt verschoben hat.
    blockade = open_decision(engine, run["id"])
    assert blockade["gate"] == "blockade" and blockade["step_id"] == gate
    engine.decide(blockade["id"], TECH_LEAD, "annehmen", "Neue Regeln geprüft")
    rebound = engine.store.run(run["id"])
    assert rebound["registry_digest"] == engine.registry.digest and rebound["step_id"] == gate
    assert engine.registry.steps[rebound["step_index"]].id == gate
    drive(engine)
    reopened = open_decision(engine, run["id"])
    assert reopened["gate"] == gate and reopened["registry_digest"] == engine.registry.digest


def test_open_legacy_runs_get_a_stable_step_id_on_start(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine)
    drive(engine)
    decision = open_decision(engine, run["id"])
    engine.store.db.execute("UPDATE runs SET step_id='', registry_digest='alt' WHERE id=?", (run["id"],))
    engine.store.db.commit()
    engine._migrate_step_ids()
    assert engine.store.run(run["id"])["step_id"] == decision["step_id"] == "G4", "aus dem offenen Gate abgeleitet"


def test_rebinding_fails_closed_when_the_step_no_longer_exists(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine)
    engine.store.update_run(run["id"], step_id="entfernter_schritt", registry_digest="alt")
    engine.cycle()
    blockade = open_decision(engine, run["id"])
    with pytest.raises(EngineError, match="gibt es im aktuellen Ablauf nicht"):
        engine.decide(blockade["id"], TECH_LEAD, "annehmen", "weiter")
    assert engine.store.decision(blockade["id"])["status"] == "offen"


# =====================================================================================
# Wichtigste Regression 3 (A3): grüner CI-Lauf genügt an G3 nicht ohne Ergebnis je Fall
# =====================================================================================
def m_run(engine):  # noqa: ANN001, ANN201
    """M-Lauf bis hinter die Integrationsprüfung (EP1 und G1 nimmt der PO an)."""
    run = submit(engine, project_class="M", criticality="K1")
    for _ in range(6):
        drive(engine)
        if engine.store.latest_artifact(run["id"], "integration"):
            break
        decision = open_decision(engine, run["id"])
        if decision["gate"] not in {"EP1", "G1", "G2", "G3"}:
            break
        engine.decide(decision["id"], PO if decision["decider"] == "product-owner" else TECH_LEAD, "annehmen", "ok")
    return run


def test_green_ci_without_case_results_does_not_pass_g3(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    engine.sandbox.checker = LocalCheck(["true"])  # grün, aber ohne Ergebnis je Integrationstestfall
    run = m_run(engine)
    integration = engine.store.latest_artifact(run["id"], "integration")["content"]
    cases = engine.store.latest_artifact(run["id"], "integrationstests")["content"]["items"]
    assert cases and integration["passed"] is False
    assert set(integration["cases"].values()) == {"fehlt"} and "ohne bestandenes Ergebnis" in integration["summary"]
    assert not any(d["gate"] == "G3" and d["status"] == "angenommen" for d in engine.store.decisions(run_id=run["id"]))
    assert not any(e["kind"] == "gate" and e["actor"] == "G3" for e in engine.store.events(run_id=run["id"]))
    # Auch das Gate selbst prüft je Fall: ein als „bestanden“ markierter Gesamtlauf ohne Fälle reicht nicht.
    implementation = engine.store.latest_artifact(run["id"], "implementierung")
    engine.store.add_artifact(run["id"], "integration", "integration", "integration",
                              {**integration, "passed": True, "cases": {},
                               "digest": implementation["refs"]["digest"]}, {})
    problems = engine._gate_checks(engine.store.run(run["id"]), engine._step_by_id("G3"))
    assert any("kein bestandenes Ergebnis" in p for p in problems)


def test_m_run_with_named_case_tests_passes_g3(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = m_run(engine)
    integration = engine.store.latest_artifact(run["id"], "integration")["content"]
    assert integration["passed"] and set(integration["cases"].values()) == {"bestanden"}
    assert engine._integration_gaps(engine.store.run(run["id"])) == []


def test_case_results_need_an_explicit_pass_per_id() -> None:
    output = "PASSED tests/t.py::test_IT_1_rechte\nFAILED tests/t.py::test_IT_10_last\nok 3 - IT-2 schnittstelle"
    assert _case_results(output, ["IT-1", "IT-10", "IT-2", "IT-3"]) == {
        "IT-1": "bestanden", "IT-10": "fehlgeschlagen", "IT-2": "bestanden", "IT-3": "fehlt"}


def test_integration_case_must_cover_a_valid_baseline_criterion(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = m_run(engine)
    cases = engine.store.latest_artifact(run["id"], "integrationstests")
    engine.store.add_artifact(run["id"], "integrationstests", "integrationstest", "integrationstests",
                              {**cases["content"], "items": [{**cases["content"]["items"][0], "covers": ["R9/AC-7"]}]}, {})
    assert any("kein gültiges Baseline-Kriterium" in g for g in engine._integration_gaps(engine.store.run(run["id"])))


def test_manifest_ignores_acceptance_tests_with_unknown_criteria(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine)
    drive(engine)
    tests = engine.store.latest_artifact(run["id"], "akzeptanztests")
    forged = [{**item, "criterion": item["criterion"].split("/")[0] + "/AC-99"} for item in tests["content"]["items"]]
    engine.store.add_artifact(run["id"], "akzeptanztests", "akzeptanztest", "akzeptanztests",
                              {**tests["content"], "items": forged}, {})
    gaps = engine.verify_manifest(run["id"])
    assert any("unbekannte Kriterien" in g for g in gaps)
    assert "Anforderung R1 hat keinen Akzeptanztest" in gaps, "ein Präfix allein ist keine Abdeckung"


# =====================================================================================
# A1: Einstufung – ohne, teilweise, vollständig; Vererbung an Arbeitspakete
# =====================================================================================
@pytest.mark.parametrize(("values", "expected"), [
    ({}, ("S", "K1", "neue_funktion")),                                     # ohne Einstufung
    ({"criticality": "K1"}, ("S", "K1", "neue_funktion")),                  # teilweise: nur K1 schwächt nicht ab
    ({"criticality": "K2"}, ("S", "K2", "kritisch")),
    ({"project_class": "M"}, ("M", "K1", "neue_funktion")),                 # teilweise: nur Klasse
    ({"project_class": "S", "criticality": "K1"}, ("S", "K1", "standard")),  # vollständig
    ({"project_class": "S", "criticality": "K1", "change_class": "kritisch"}, ("S", "K1", "kritisch")),
    ({"project_class": "L", "criticality": "K3"}, ("L", "K3", "kritisch")),
])
def test_classification_without_partial_and_full(make_engine, values, expected) -> None:  # noqa: ANN001
    engine = make_engine()
    assert engine._classify(values) == expected


def test_explicitly_critical_l_project_passes_strictness_to_its_packages(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    values = auftrag(project_class="L", criticality="K1", change_class="kritisch", title="Kritisches Großprojekt")
    run = engine.submit(values, PO, "rv-l-kritisch")
    assert run["change_class"] == "kritisch" and run["auftrag"]["change_class_explicit"] == "kritisch"
    drive(engine)
    ep1 = open_decision(engine, run["id"])
    assert ep1["gate"] == "EP1"
    engine.decide(ep1["id"], PO, "annehmen", "Projekt definiert")
    project = engine.store.project_for_run(run["id"])
    child = engine.start_package(project["id"], "AP-1", PO)
    assert child["auftrag"]["project_class"] == "S" and child["change_class"] == "kritisch", \
        "die ausdrückliche Verschärfung gilt auch je Paket (menschliche Gates bleiben)"


def test_package_cannot_lower_the_project_criticality(make_engine) -> None:  # noqa: ANN001
    engine = make_engine(projects=CATALOG)
    engine.seed_projects()
    project = engine.store.project("PRJ-TM-100")
    engine.store.db.execute("UPDATE work_packages SET spec=json_set(spec, '$.criticality', 'K1') WHERE key='AP-1'")
    engine.store.db.commit()
    child = engine.start_package(project["id"], "AP-1", PO_TM)
    assert child["auftrag"]["criticality"] == "K2" and child["change_class"] == "kritisch"


# =====================================================================================
# A4: EP1 prüft Abhängigkeiten und Projektbereiche; genehmigter Bereich ist fest
# =====================================================================================
def test_cycles_are_detected() -> None:
    packages = [{"key": "A", "depends_on": ["C"]}, {"key": "B", "depends_on": ["A"]}, {"key": "C", "depends_on": ["B"]},
                {"key": "D", "depends_on": []}]
    assert _cycles(packages) == ["A", "B", "C"]


def l_plan(engine):  # noqa: ANN001, ANN201
    values = auftrag(project_class="L", criticality="K1", title="Großprojekt mit Plan")
    values.pop("change_class")
    run = engine.submit(values, PO_DMS if engine.projects else PO, "rv-l-plan")
    drive(engine)
    return run


def replace_plan(engine, run, change) -> list[str]:  # noqa: ANN001
    plan = engine.store.latest_artifact(run["id"], "projektplan")
    items = [change(dict(item)) for item in plan["content"]["items"]]
    engine.store.add_artifact(run["id"], "projektplan", "projektplanung", "projektplanung",
                              {**plan["content"], "items": items}, {})
    return engine._gate_checks(engine.store.run(run["id"]), engine._step_by_id("EP1"))


def test_ep1_rejects_cyclic_dependencies(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = l_plan(engine)
    problems = replace_plan(engine, run, lambda i: {**i, "depends_on": ["AP-5"]} if i["key"] == "AP-1" else i)
    assert any("Zyklische Abhängigkeiten" in p for p in problems)


def test_ep1_checks_scopes_against_the_project_not_the_global_list(make_engine) -> None:  # noqa: ANN001
    engine = make_engine(projects=CATALOG)
    engine.scopes = {**engine.scopes, "fremd": {"label": "Fremd", "paths": ["docs/x.md"]}}  # global, nicht im Projekt
    run = l_plan(engine)
    problems = replace_plan(engine, run, lambda i: {**i, "scope": "fremd"} if i["key"] == "AP-3" else i)
    assert any("außerhalb des Projekts: fremd" in p for p in problems)


def test_ep1_for_l_needs_an_integration_package(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = l_plan(engine)
    problems = replace_plan(engine, run, lambda i: {**i, "v_level": "software_verifikation"}
                            if i["v_level"] == "software_integration" else i)
    assert any("kein Integrationspaket" in p for p in problems)


def test_approved_package_scope_cannot_be_replaced_at_start(make_engine) -> None:  # noqa: ANN001
    engine = make_engine(projects=CATALOG)
    engine.seed_projects()
    with pytest.raises(EngineError, match="lässt sich beim Start nicht ersetzen"):
        engine.start_package("PRJ-TM-100", "AP-1", PO_TM, scope="anderer-bereich")


def test_l_project_needs_the_integration_package_before_it_counts_as_done(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = l_plan(engine)
    engine.decide(open_decision(engine, run["id"])["id"], PO, "annehmen", "Projekt definiert")
    project = engine.store.project_for_run(run["id"])
    for item in project["packages"]:
        engine.store.db.execute("UPDATE work_packages SET run_id=? WHERE project_id=? AND key=?",
                                (run["id"] if item["v_level"] != "software_integration" else "", project["id"], item["key"]))
    engine.store.db.commit()
    integration_key = next(i["key"] for i in project["packages"] if i["v_level"] == "software_integration")
    summary = engine.project_summary(engine.store.project(project["id"]))
    assert summary["status"] != "abgeschlossen"
    package = next(p for p in summary["packages"] if p["key"] == integration_key)
    assert package["status"] in {"bereit", "geplant"}
    child_values = engine.start_package(project["id"], integration_key, PO, scope="doku")["auftrag"]
    assert child_values["integration_required"] is True
    assert engine._step_by_id("integrationstests").applies(child_values), "Integrationspaket läuft durch die Tests"


# =====================================================================================
# A5: atomare und wiederanlauffähige Übergänge
# =====================================================================================
def test_package_run_left_without_binding_is_bound_instead_of_duplicated(make_engine) -> None:  # noqa: ANN001
    engine = make_engine(projects=CATALOG)
    engine.seed_projects()
    first = engine.start_package("PRJ-TM-100", "AP-1", PO_TM)
    # Absturz-Simulation: Lauf existiert, Bindung fehlt.
    engine.store.db.execute("UPDATE work_packages SET run_id='' WHERE key='AP-1'")
    engine.store.db.commit()
    again = engine.start_package("PRJ-TM-100", "AP-1", PO_TM)
    assert again["id"] == first["id"] and len([r for r in engine.store.runs() if r["auftrag"].get("package_key")]) == 1
    assert engine.store.project("PRJ-TM-100")["packages"][0]["run_id"] == first["id"]


def test_ep1_completion_and_project_creation_are_one_transaction(make_engine, monkeypatch) -> None:  # noqa: ANN001
    engine = make_engine()
    run = l_plan(engine)
    ep1 = open_decision(engine, run["id"])

    def crash(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("Absturz beim Anlegen der Arbeitspakete")

    monkeypatch.setattr(engine.store, "_create_project", crash)
    with pytest.raises(RuntimeError):
        engine.decide(ep1["id"], PO, "annehmen", "Projekt definiert")
    current = engine.store.run(run["id"])
    assert current["status"] != "abgeschlossen", "kein abgeschlossener Planungslauf ohne Projekt"
    monkeypatch.undo()
    engine.recover()  # wartet ohne offene Entscheidung → Gate erneut einplanen
    drive(engine)
    engine.decide(open_decision(engine, run["id"])["id"], PO, "annehmen", "Projekt definiert")
    assert engine.store.run(run["id"])["status"] == "abgeschlossen" and engine.store.project_for_run(run["id"])


# =====================================================================================
# A6: Abschlussarten getrennt; Katalog- und Planungsläufe ohne Release-Manifest
# =====================================================================================
def test_completion_kinds_are_kept_apart(make_engine) -> None:  # noqa: ANN001
    engine = make_engine(projects=CATALOG)
    engine.seed_projects()
    catalog_run = engine.store.project("PRJ-TM-100")["run_id"]
    planned = l_plan(engine)
    engine.decide(open_decision(engine, planned["id"])["id"], PO_DMS, "annehmen", "Projekt definiert")
    produced = submit(engine, "rv-prod-0001", user=PO_DMS)
    drive(engine)
    engine.decide(open_decision(engine, produced["id"])["id"], person(KEY_USER, "flow-prj-flow-dms-lesen"), "annehmen", "ok")
    drive(engine)
    engine.decide(open_decision(engine, produced["id"])["id"], person(RELEASE, "flow-prj-flow-dms-lesen"), "annehmen", "ok")
    kinds = {r["id"]: r["completion"] for r in engine.store.runs()}
    assert kinds[catalog_run] == "katalog" and kinds[planned["id"]] == "projektplanung"
    assert kinds[produced["id"]] == "produktion"
    metrics = engine.overview()["metrics"]
    assert metrics["runs_done"] == 1 and metrics["runs_planned"] == 1 and metrics["projects_from_catalog"] == 1
    assert engine.run_detail(catalog_run)["manifest_gaps"] == [] and engine.run_detail(catalog_run)["completion"] == "katalog"
    assert engine.store.latest_artifact(planned["id"], "uebernahme") is None, "EP1 löst keine Übernahme aus"


# =====================================================================================
# B3: Katalogbindung bleibt erhalten; Detailrechte im Orchestrator
# =====================================================================================
def test_bound_runs_stay_protected_when_the_catalog_loses_the_project(make_engine) -> None:  # noqa: ANN001
    engine = make_engine(projects=CATALOG)
    run = submit(engine, "rv-bound-0001", user=PO_DMS)
    assert run["auftrag"]["catalog_bound"] is True
    for catalog in ({}, {"TM-100": CATALOG["TM-100"]}):  # Katalog leer bzw. Projektcode entfernt
        engine.projects = catalog
        assert engine.auftrag_access(PO, run["auftrag"]) == ""
        with pytest.raises(KeyError):
            engine.run_detail(run["id"], PO)
    assert engine.run_detail(run["id"], person(PO, "flow-isb"))["run"]["id"] == run["id"], "Aufsicht sieht weiter"


def test_true_legacy_runs_stay_open(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine, "rv-legacy-0001", project="FLOW-ALT")
    assert run["auftrag"]["catalog_bound"] is False
    engine.projects = CATALOG  # Katalog kommt später; FLOW-ALT steht nicht darin
    assert engine.auftrag_access(PO, run["auftrag"]) == "aendern"


def test_run_detail_needs_the_project_right(make_engine) -> None:  # noqa: ANN001
    engine = make_engine(projects=CATALOG)
    run = submit(engine, "rv-detail-0001", user=PO_DMS)
    with pytest.raises(KeyError):
        engine.run_detail(run["id"], PO_TM)
    assert engine.run_detail(run["id"], PO_DMS)["run"]["id"] == run["id"]


def test_overview_names_the_project_binding_of_every_referenced_run(make_engine) -> None:  # noqa: ANN001
    engine = make_engine(projects=CATALOG)
    run = submit(engine, "rv-access-0001", user=PO_DMS)
    drive(engine)
    overview = engine.overview()
    referenced = {e["run_id"] for e in overview["events"] if e.get("run_id")} | {r["id"] for r in overview["runs"]}
    assert referenced <= set(overview["access"]["runs"])
    assert overview["access"]["runs"][run["id"]] == {"project": "FLOW-DMS", "bound": True}
    assert all(a["last"] is None or "run_id" in a["last"] for a in overview["agents"])
