"""V-Modell im Ablauf (KI-Softwareentwicklung nach dem V-Modell, Teile 01, 02, 04, 09).

Einstufung nach Projektklasse und Kritikalität, Projektplanung mit EP1, Integrationstests
für M/L, Kurzweg für S und Prüfung, dass jede Anforderung einen Test hat.
"""

from __future__ import annotations

import pytest

from flowagents.engine import EngineError

from .conftest import KEY_USER, PO, RELEASE, TECH_LEAD, auftrag, drive, open_decision


def submit(engine, **overrides):  # noqa: ANN001, ANN003, ANN201
    values = auftrag(**overrides)
    if ("project_class" in overrides or "criticality" in overrides) and "change_class" not in overrides:
        values.pop("change_class")
    return engine.submit(values, PO, f"vm-{len(engine.store.runs()) + 1:04d}-test")


@pytest.mark.parametrize(("project_class", "criticality", "expected"), [
    ("S", "K1", "standard"), ("M", "K1", "neue_funktion"), ("L", "K1", "neue_funktion"),
    ("S", "K2", "kritisch"), ("M", "K3", "kritisch"),
])
def test_classification_derives_the_change_class(make_engine, project_class, criticality, expected) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine, project_class=project_class, criticality=criticality)
    assert run["change_class"] == expected
    assert run["auftrag"]["project_class"] == project_class and run["auftrag"]["criticality"] == criticality


def test_explicit_change_class_may_only_tighten_the_path(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    stricter = submit(engine, project_class="S", criticality="K1", change_class="kritisch")
    assert stricter["change_class"] == "kritisch"
    looser = submit(engine, project_class="M", criticality="K2", change_class="standard")
    assert looser["change_class"] == "kritisch"


def test_invalid_classification_is_rejected(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    with pytest.raises(EngineError, match="Projektklasse"):
        submit(engine, project_class="XL")
    with pytest.raises(EngineError, match="Kritikalität"):
        submit(engine, project_class="M", criticality="K9")
    with pytest.raises(EngineError, match="Domäne"):
        submit(engine, project_class="M", domain="raumfahrt")


def test_without_classification_the_short_path_stays_unchanged(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine)
    assert run["auftrag"]["project_class"] == "S" and run["change_class"] == "standard"
    drive(engine)
    assert open_decision(engine, run["id"])["gate"] == "G4"
    kinds = {a["kind"] for a in engine.store.artifacts(run["id"])}
    assert "projektplan" not in kinds and "integrationstests" not in kinds
    skipped = [e for e in engine.store.events(run_id=run["id"]) if e["kind"] == "uebersprungen"]
    assert not skipped  # der Übergang überspringt nicht geltende Schritte direkt


def test_m_project_plans_work_packages_and_waits_for_ep1(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine, project_class="M", criticality="K1")
    drive(engine)
    decision = open_decision(engine, run["id"])
    assert decision["gate"] == "EP1" and decision["decider"] == "product-owner"
    assert decision["context"]["ep"] == "EP1 Projekt definiert"
    plan = engine.store.latest_artifact(run["id"], "projektplan")
    levels = {item["v_level"] for item in plan["content"]["items"]}
    assert {"anforderungen", "implementierung", "abnahme"} <= levels
    assert engine._focus(decision) == ["projektplan", "geschaeftsbewertung"]


def test_m_project_runs_through_the_v_with_integration_tests(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine, project_class="M", criticality="K1")
    drive(engine)
    engine.decide(open_decision(engine, run["id"])["id"], PO, "annehmen", "Pakete passen")
    drive(engine)
    g1 = open_decision(engine, run["id"])
    assert g1["gate"] == "G1"
    engine.decide(g1["id"], PO, "annehmen")
    drive(engine)
    fachabnahme = open_decision(engine, run["id"])
    assert fachabnahme["gate"] == "G4"
    tests = engine.store.latest_artifact(run["id"], "integrationstests")
    assert tests and all(item["interface"] for item in tests["content"]["items"])
    assert engine.verify_manifest(run["id"]) == []
    order = [s["step_id"] for s in engine.store.steps(run["id"])]
    assert order.index("projektplanung") < order.index("anforderungen") < order.index("integrationstests") < order.index("entwicklung")
    engine.decide(fachabnahme["id"], KEY_USER, "annehmen", "geprüft")
    drive(engine)
    engine.decide(open_decision(engine, run["id"])["id"], RELEASE, "annehmen", "ok")
    assert engine.store.run(run["id"])["status"] == "abgeschlossen"


def test_ep1_rejection_returns_to_project_planning(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine, project_class="M", criticality="K1")
    drive(engine)
    engine.decide(open_decision(engine, run["id"])["id"], PO, "ablehnen", "Abnahme fehlt als eigenes Paket")
    drive(engine)
    attempts = [s for s in engine.store.steps(run["id"]) if s["step_id"] == "projektplanung"]
    assert len(attempts) == 2
    assert open_decision(engine, run["id"])["gate"] == "EP1"


def test_ep1_needs_a_product_owner(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine, project_class="M", criticality="K1")
    drive(engine)
    with pytest.raises(EngineError, match="Befugnis"):
        engine.decide(open_decision(engine, run["id"])["id"], TECH_LEAD, "annehmen")


def test_l_project_ends_after_ep1_as_planning_run(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine, project_class="L", criticality="K1")
    drive(engine)
    engine.decide(open_decision(engine, run["id"])["id"], PO, "annehmen", "Projekt definiert")
    drive(engine)
    final = engine.store.run(run["id"])
    assert final["status"] == "abgeschlossen" and "Arbeitspakete" in final["reason"]
    assert "anforderungen" not in [s["step_id"] for s in engine.store.steps(run["id"])]


def test_k2_requires_people_at_every_gate(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine, project_class="S", criticality="K2")
    assert run["change_class"] == "kritisch"
    drive(engine)
    assert open_decision(engine, run["id"])["gate"] == "G1"


def test_k3_prompt_marks_results_as_drafts(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = engine.store.run(submit(engine, project_class="M", criticality="K3")["id"])
    step = engine.registry.steps[engine.registry.step_index("anforderungen")]
    agent = engine.registry.agent("anforderungen")
    text = engine._render(run, step, agent, {"auftrag": run["auftrag"]})
    assert "Kritikalität K3" in text and "Projektklasse M" in text


def test_manifest_reports_a_requirement_without_test(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine)
    drive(engine)
    tests = engine.store.latest_artifact(run["id"], "akzeptanztests")
    kept = [item for item in tests["content"]["items"] if not item["criterion"].startswith("R2/")]
    engine.store.add_artifact(run["id"], "akzeptanztests", "akzeptanztest", "akzeptanztests",
                              {**tests["content"], "items": kept}, {})
    assert "Anforderung R2 hat keinen Akzeptanztest" in engine.verify_manifest(run["id"])


def test_overview_shows_classification_and_decision_points(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    submit(engine, project_class="M", criticality="K2", domain="produkt")
    drive(engine)
    overview = engine.overview()
    run = overview["runs"][0]
    assert (run["project_class"], run["criticality"], run["domain"]) == ("M", "K2", "produkt")
    pipeline = {step["id"]: step for step in overview["pipeline"]}
    assert pipeline["EP1"]["when"] == {"project_class": ["M", "L"]}
    assert pipeline["G3"]["ep"].startswith("EP5")
    numbers = {agent["role"]: agent["number"] for agent in overview["agents"]}
    assert numbers["projektplanung"] == 0 and numbers["integrationstest"] == 13
