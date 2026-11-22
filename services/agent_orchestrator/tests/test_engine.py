"""Ablauf Ende-zu-Ende mit simulierten Rollen (REQ-AGT-003, -005, -006, -007, -008).

Die Nummern in den Testnamen verweisen auf den Abnahmeplan, KI-Entwicklungskonzept Teil 10.
"""

from __future__ import annotations

import pytest

from flowagents.engine import EngineError
from flowagents.providers import AgentReply, ProviderError

from .conftest import KEY_USER, MANAGEMENT, NOBODY, PO, RELEASE, TECH_LEAD, auftrag, drive, open_decision


def submit(engine, **overrides):  # noqa: ANN001, ANN003, ANN201
    return engine.submit(auftrag(**overrides), PO, f"key-{len(engine.store.runs()) + 1:04d}-test")


def test_35_standard_change_runs_to_fachabnahme_and_release(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine)
    drive(engine)
    decision = open_decision(engine, run["id"])
    assert decision["gate"] == "G4" and decision["decider"] == "key-user"
    assert decision["digest"].startswith("sha256:")
    steps = [s["step_id"] for s in engine.store.steps(run["id"])]
    assert steps[:3] == ["auftragspruefung", "anforderungen", "anforderungspruefung"]
    assert "integrationspruefung" in steps and "codepruefung" in steps and "prozesspruefung" in steps
    # Standardweg: G1 bis G3 automatisch erfüllt, aber nachvollziehbar protokolliert.
    gate_events = [e["message"] for e in engine.store.events(run_id=run["id"]) if e["kind"] == "gate"]
    assert len(gate_events) == 3
    engine.decide(decision["id"], KEY_USER, "annehmen", "Reihenfolge und Sichtbarkeit geprüft")
    drive(engine)
    release = open_decision(engine, run["id"])
    assert release["gate"] == "G5"
    engine.decide(release["id"], RELEASE, "annehmen", "Standard-Change")
    final = engine.store.run(run["id"])
    assert final["status"] == "abgeschlossen"
    assert "Auslieferung manuell" in final["reason"]
    # Jede Rolle hat ihr Ergebnis als versioniertes Artefakt hinterlegt.
    kinds = {a["kind"] for a in engine.store.artifacts(run["id"])}
    assert {"geschaeftsbewertung", "anforderungen", "anforderungsbefund", "baseline", "architektur",
            "sicherheitsbefund", "plan", "akzeptanztests", "implementierung", "integration", "codebefund",
            "dokumentation", "nachweise", "prozessbewertung"} <= kinds


def test_new_function_waits_for_product_owner_at_g1(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine, change_class="neue_funktion")
    drive(engine)
    decision = open_decision(engine, run["id"])
    assert decision["gate"] == "G1" and decision["decider"] == "product-owner"
    assert engine.store.latest_artifact(run["id"], "baseline")["content"]["state"] == "Arbeitsbaseline fixiert"


def test_g1_rejection_sends_findings_back_to_requirements_agent(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine, change_class="neue_funktion")
    drive(engine)
    decision = open_decision(engine, run["id"])
    with pytest.raises(EngineError, match="Begründung"):
        engine.decide(decision["id"], PO, "ablehnen", "")
    engine.decide(decision["id"], PO, "ablehnen", "Sonderzeichen-Sortierung fehlt")
    assert engine.store.run(run["id"])["step_index"] == engine.registry.step_index("anforderungen")
    drive(engine)
    assert len(engine.store.artifacts(run["id"], ("anforderungen",))) == 2
    assert open_decision(engine, run["id"])["gate"] == "G1"


def test_review_rework_loop_then_pass(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine, behavior="Ansicht sortiert nach Titel [sim:nacharbeit] mit sichtbaren Dokumenten.")
    drive(engine)
    events = [e for e in engine.store.events(run_id=run["id"]) if e["kind"] == "ruecklauf"]
    assert events and events[0]["actor"] == "anforderungspruefung" and events[0]["target"] == "anforderungen"
    reviews = engine.store.artifacts(run["id"], ("anforderungsbefund",))
    assert [r["content"]["status"] for r in reviews] == ["nacharbeit", "fertig"]
    assert open_decision(engine, run["id"])["gate"] == "G4"


def test_ceo_agent_concerns_escalate_to_product_owner(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine, goal="Irgendetwas verbessern [sim:gf-bedenken] im Dokumentenbereich.")
    drive(engine)
    decision = open_decision(engine, run["id"])
    assert decision["gate"] == "eskalation" and decision["decider"] == "product-owner"
    assert engine.store.steps(run["id"])[0]["role"] == "geschaeftsfuehrung"
    engine.decide(decision["id"], PO, "annehmen", "Pilot mit Messung")
    drive(engine)
    assert open_decision(engine, run["id"])["gate"] == "G4"


def test_agent_question_goes_to_inbox_and_answer_is_used(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine, behavior="Altdokumente mit Fristen übernehmen [sim:frage] inklusive Löschsperren.")
    drive(engine)
    decision = open_decision(engine, run["id"])
    assert decision["gate"] == "frage" and "Aufbewahrungsfrist" in decision["question"]
    engine.decide(decision["id"], PO, "annehmen", "10 Jahre ab Ablage")
    drive(engine)
    assert open_decision(engine, run["id"])["gate"] == "G4"


def test_16_person_without_role_cannot_decide(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine)
    drive(engine)
    decision = open_decision(engine, run["id"])
    for person in (NOBODY, MANAGEMENT, RELEASE):
        with pytest.raises(EngineError, match="Befugnis"):
            engine.decide(decision["id"], person, "annehmen")
    assert engine.store.decision(decision["id"])["status"] == "offen"


def test_submit_requires_product_owner_role_and_valid_scope(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    with pytest.raises(EngineError, match="Befugnis"):
        engine.submit(auftrag(), NOBODY, "key-unauthorized")
    with pytest.raises(EngineError, match="Änderungsbereich"):
        engine.submit(auftrag(scope="agents"), PO, "key-bad-scope")
    with pytest.raises(EngineError, match="vertrauliche"):
        engine.submit(auftrag(data_class="vertraulich"), PO, "key-confidential")


def test_26_submit_is_idempotent(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    first = engine.submit(auftrag(), PO, "same-key-0001")
    again = engine.submit(auftrag(), PO, "same-key-0001")
    assert first["id"] == again["id"] and len(engine.store.runs()) == 1
    with pytest.raises(EngineError, match="anderem Auftrag"):
        engine.submit(auftrag(title="Ganz anderer Auftrag"), PO, "same-key-0001")


def test_29_changed_candidate_invalidates_fachabnahme(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine)
    drive(engine)
    decision = open_decision(engine, run["id"])
    implementation = engine.store.latest_artifact(run["id"], "implementierung")
    engine.store.add_artifact(run["id"], "implementierung", "entwicklung", "entwicklung", {"files": {}},
                              {**implementation["refs"], "digest": "sha256:anderer-kandidat"})
    with pytest.raises(EngineError, match="neue Entscheidung"):
        engine.decide(decision["id"], KEY_USER, "annehmen")
    assert engine.store.decision(decision["id"])["status"] == "verfallen"
    drive(engine)
    # Das Gate prüft den neuen Stand erneut und blockiert, weil Prüfungen zum alten Digest gehören.
    blocked = open_decision(engine, run["id"])
    assert blocked["gate"] == "blockade"
    assert "anderen Änderungsstand" in blocked["question"]


def test_28_red_integration_goes_back_to_developer_and_limits_rounds(make_engine) -> None:  # noqa: ANN001
    engine = make_engine(check_passes=False)
    run = submit(engine)
    drive(engine)
    decision = open_decision(engine, run["id"])
    assert decision["gate"] == "korrekturlimit" and decision["decider"] == "tech-lead"
    attempts = [s for s in engine.store.steps(run["id"]) if s["step_id"] == "entwicklung"]
    assert len(attempts) == engine.registry.max_correction_rounds + 1
    engine.decide(decision["id"], TECH_LEAD, "ablehnen", "Manuell übernehmen")
    assert engine.store.run(run["id"])["status"] == "abgebrochen"


def test_30_manifest_gap_blocks_fachabnahme(make_engine) -> None:  # noqa: ANN001
    engine = make_engine(sandbox=False)
    run = submit(engine)
    drive(engine)
    decision = open_decision(engine, run["id"])
    # Ohne Sandbox gibt es keine Implementierung: der Ablauf stoppt vor G3/G4 mit einer Blockade.
    assert decision["gate"] == "blockade"
    assert engine.store.run(run["id"])["status"] == "blockiert"


def test_15_paused_agent_holds_waiting_runs(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    engine.control("pause", TECH_LEAD, role="anforderungen")
    run = submit(engine)
    drive(engine)
    assert engine.store.run(run["id"])["status"] == "pausiert"
    assert all(s["role"] != "anforderungen" for s in engine.store.steps(run["id"]))
    engine.control("resume", TECH_LEAD, role="anforderungen")
    drive(engine)
    assert open_decision(engine, run["id"])["gate"] == "G4"


def test_global_stop_switch_and_control_rights(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    with pytest.raises(EngineError, match="Steuerung"):
        engine.control("pause", KEY_USER)
    engine.control("pause", TECH_LEAD)
    submit(engine)
    assert engine.cycle() is False
    engine.control("resume", TECH_LEAD)
    assert engine.cycle() is True


def test_14_budget_exhaustion_blocks_further_model_calls(make_engine, registry) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine)
    engine.store.update_run(run["id"], model_calls=registry.budget["max_model_calls"])
    drive(engine)
    decision = open_decision(engine, run["id"])
    assert "Laufbudget" in decision["question"]
    assert engine.store.steps(run["id"]) == []


class BrokenProvider:
    name = "gateway"

    def __init__(self, text: str | None) -> None:
        self.text = text
        self.calls = 0

    def generate(self, request):  # noqa: ANN001, ANN201
        self.calls += 1
        if self.text is None:
            raise ProviderError("FLOWGATE nicht erreichbar: URLError")
        return AgentReply(self.text, "gateway", "flow-reviewer", 10)


@pytest.mark.parametrize("text", [None, '{"status": "fertig", "summary": "x", "approve_everything": true}'])
def test_provider_failure_or_invalid_handoff_blocks_safely(make_engine, text) -> None:  # noqa: ANN001
    broken = BrokenProvider(text)
    engine = make_engine(providers={"gateway": broken},
                         profile_providers={"builder": "simulated", "coder": "simulated", "pruefer": "simulated",
                                            "assistenz": "simulated", "leitung": "gateway"})
    run = submit(engine)
    drive(engine)
    decision = open_decision(engine, run["id"])
    assert decision["gate"] == "blockade"
    assert broken.calls == (1 if text is None else 2)  # ungültige Übergabe: genau eine Wiederholung
    assert engine.store.latest_artifact(run["id"], "geschaeftsbewertung") is None
    # Nach Behebung setzt der Tech Lead denselben Schritt fort.
    broken.text = '{"status": "fertig", "summary": "ok", "artifacts": [{"type": "bewertung", "key": "GF-1", ' \
                  '"title": "t", "benefit": "b", "staff_effort": "s", "process_fit": "p", "risks": [], ' \
                  '"recommendation": "weiter"}]}'
    engine.decide(decision["id"], TECH_LEAD, "annehmen", "erneut versuchen")
    engine.cycle()
    assert engine.store.latest_artifact(run["id"], "geschaeftsbewertung") is not None


def test_overview_shows_agents_interactions_and_inbox(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine, change_class="neue_funktion")
    drive(engine)
    overview = engine.overview()
    assert len(overview["agents"]) == 12
    assert overview["metrics"]["decisions_open"] == 1
    assert overview["decisions"][0]["decider"] == "product-owner"
    assert overview["runs"][0]["waiting_for"] == "product-owner"
    pairs = {(edge["from"], edge["to"]) for edge in overview["interactions"]}
    assert ("geschaeftsfuehrung", "anforderungen") in pairs
    assert ("anforderungen", "anforderungspruefung") in pairs
    detail = engine.run_detail(run["id"])
    assert all("workspace" not in a["refs"] for a in detail["artifacts"])


def test_restart_recovers_interrupted_step(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine)
    row = engine.store.start_step(run["id"], "auftragspruefung", "geschaeftsfuehrung")
    engine.recover()
    assert engine.store.steps(run["id"])[0]["status"] == "unterbrochen" and row
    drive(engine)
    assert open_decision(engine, run["id"])["gate"] == "G4"


def test_changed_registry_blocks_running_run(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine)
    engine.store.db.execute("UPDATE runs SET registry_digest='alt' WHERE id=?", (run["id"],))
    engine.store.db.commit()
    engine.cycle()
    assert "Agentenregister" in open_decision(engine, run["id"])["question"]
