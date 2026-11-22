"""Ablauf Ende-zu-Ende mit simulierten Rollen (REQ-AGT-003, -005, -006, -007, -008).

Die Nummern in den Testnamen verweisen auf den Abnahmeplan, KI-Entwicklungskonzept Teil 10.
"""

from __future__ import annotations

import pytest

from flowagents.engine import EngineError
from flowagents.providers import AgentReply, ProviderError
from flowagents.sandbox import SandboxError

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


def test_changed_registry_blocks_running_run_until_a_human_rebinds_it(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine)
    engine.store.db.execute("UPDATE runs SET registry_digest='alt' WHERE id=?", (run["id"],))
    engine.store.db.commit()
    engine.cycle()
    decision = open_decision(engine, run["id"])
    assert "Agentenregister" in decision["question"]
    engine.decide(decision["id"], TECH_LEAD, "annehmen", "Neue Rollenanweisungen geprüft")
    assert engine.store.run(run["id"])["registry_digest"] == engine.registry.digest
    drive(engine)
    assert open_decision(engine, run["id"])["gate"] == "G4"


def test_reviewers_do_not_see_settled_gate_decisions(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine, change_class="neue_funktion")
    drive(engine)
    engine.decide(open_decision(engine, run["id"])["id"], PO, "ablehnen", "AC-2 ist nicht prüfbar")
    current = engine.store.run(run["id"])
    creator = engine._context(current, engine.registry.steps[engine.registry.step_index("anforderungen")],
                              engine.registry.agent("anforderungen"))
    assert creator["findings_to_fix"][0]["impact"] == "AC-2 ist nicht prüfbar"
    reviewer_step = engine.registry.steps[engine.registry.step_index("anforderungspruefung")]
    reviewer = engine._context(current, reviewer_step, engine.registry.agent("anforderungspruefung"))
    assert reviewer["decisions"] == [] and "findings_to_fix" not in reviewer


def test_resumed_update_uses_the_confirmed_version_after_a_conflict(make_engine) -> None:  # noqa: ANN001
    from flowagents.rm import RMConflict

    engine = make_engine()
    calls: list[tuple[str, dict]] = []
    original = engine.rm.call

    def flaky(role, agent_id, run_id, operation, payload):  # noqa: ANN001, ANN202
        calls.append((operation, dict(payload)))
        if operation == "rm.update_draft" and payload["expected_version"] == 1:
            raise RMConflict("Versionskonflikt", {"id": payload["id"], "version": 2})
        return original(role, agent_id, run_id, operation, payload)

    engine.rm.call = flaky
    run = submit(engine, behavior="Ansicht sortiert nach Titel [sim:nacharbeit] mit sichtbaren Dokumenten.")
    drive(engine)
    updates = [p for op, p in calls if op == "rm.update_draft"]
    assert [u["expected_version"] for u in updates[:2]] == [1, 2]
    assert open_decision(engine, run["id"])["gate"] == "G4"


def test_render_names_the_role_specific_contract_fields(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine)
    tester_step = engine.registry.steps[engine.registry.step_index("akzeptanztests")]
    text = engine._render(run, tester_step, engine.registry.agent("akzeptanztest"), {"auftrag": {}})
    assert '"type": "testfall"' in text and "criterion" in text and "nie nacharbeit" in text
    review_step = engine.registry.steps[engine.registry.step_index("codepruefung")]
    review = engine._render(run, review_step, engine.registry.agent("codepruefung"), {"auftrag": {}})
    assert "leere Liste" in review


def test_model_usage_is_recorded_per_role_and_run(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine)
    drive(engine)
    usage = engine.overview()["usage"]
    roles = {row["role"] for row in usage["totals"]}
    assert {"geschaeftsfuehrung", "anforderungen", "entwicklung"} <= roles
    assert sum(row["calls"] for row in usage["totals"]) == engine.store.run(run["id"])["model_calls"]
    assert usage["by_run"][0]["auftrag_id"] == "A-001" and usage["by_run"][0]["output_tokens"] > 0



# -- Eskalation komplexer Aufträge an Codex/Claude (REQ-AGT-021) ------------------------------
class Worker:
    """Abo-Worker-Attrappe: antwortet wie der Simulator, meldet sich aber als codex/claude."""

    def __init__(self, name: str, *, fail: bool = False) -> None:
        from flowagents.providers import SimulatedProvider

        self.name, self.fail, self.inner, self.roles = name, fail, SimulatedProvider(), []

    def generate(self, request):  # noqa: ANN001, ANN201
        self.roles.append(request.agent.role)
        if self.fail:
            raise ProviderError(f"{self.name}: Nutzungslimit erreicht")
        reply = self.inner.generate(request)
        return AgentReply(text=reply.text, provider=self.name, model=self.name, output_tokens=reply.output_tokens)


ESCALATION = {"enabled": True, "roles": {"entwicklung": "codex", "codepruefung": "claude"},
              "complex_classes": ["kritisch"], "after_local_failures": 2, "fallback_local": True}


def escalating_engine(make_engine, **workers):  # noqa: ANN001, ANN003, ANN201
    codex, claude = workers.get("codex") or Worker("codex"), workers.get("claude") or Worker("claude")
    engine = make_engine(providers={"codex": codex, "claude": claude}, escalation=ESCALATION)
    engine.scopes["komplex"] = {"label": "Komplex", "complexity": "hoch", "paths": ["docs/dms.md"]}
    return engine, codex, claude


def test_complex_scope_is_developed_by_codex_and_reviewed_by_claude(make_engine) -> None:  # noqa: ANN001
    engine, codex, claude = escalating_engine(make_engine)
    run = submit(engine, scope="komplex")
    drive(engine)
    assert set(codex.roles) == {"entwicklung"} and set(claude.roles) == {"codepruefung"}
    events = [e for e in engine.store.events(run_id=run["id"]) if e["kind"] == "eskalation"]
    assert events and "komplex" in events[0]["message"]
    usage = {row["role"]: row["provider"] for row in engine.overview()["usage"]["totals"]}
    assert usage["entwicklung"] == "codex" and usage["anforderungen"] == "simulated"


def test_simple_or_confidential_work_stays_local(make_engine) -> None:  # noqa: ANN001
    engine, codex, claude = escalating_engine(make_engine)
    submit(engine)
    submit(engine, scope="komplex", data_class="vertraulich", change_class="kritisch")
    submit(engine, scope="komplex", execution="lokal")
    drive(engine)
    assert codex.roles == [] and claude.roles == []
    with pytest.raises(EngineError, match="nur lokal"):
        submit(engine, execution="abo", data_class="vertraulich", change_class="kritisch")


def test_unavailable_worker_falls_back_to_the_local_model(make_engine) -> None:  # noqa: ANN001
    engine, codex, _ = escalating_engine(make_engine, codex=Worker("codex", fail=True))
    run = submit(engine, execution="abo")
    drive(engine)
    assert codex.roles == ["entwicklung"]
    messages = [e["message"] for e in engine.store.events(run_id=run["id"]) if e["kind"] == "eskalation"]
    assert any("weiter mit dem lokalen Modell" in m for m in messages)
    assert open_decision(engine, run["id"])["gate"] == "G4"


def test_escalation_must_keep_creator_and_reviewer_independent(registry) -> None:  # noqa: ANN001
    from flowagents.config import ConfigError, _check_escalation

    _check_escalation(registry, {"entwicklung": "codex", "codepruefung": "claude"})
    with pytest.raises(ConfigError, match="Unabhängigkeit"):
        _check_escalation(registry, {"entwicklung": "codex", "codepruefung": "codex"})
    with pytest.raises(ConfigError, match="nur codex oder claude"):
        _check_escalation(registry, {"entwicklung": "gpt"})


# -- Klickprüfung (REQ-AGT-022) -------------------------------------------------------------------
def test_click_paths_are_validated_strictly() -> None:
    from flowagents.uicheck import UiCheckError, validate_steps

    good = validate_steps([{"do": "goto", "path": "/dms"}, {"do": "click", "role": "button", "name": "Ablegen"},
                           {"do": "upload", "label": "Datei", "fixture": "beispiel.stl"},
                           {"do": "expect_text", "text": "gespeichert"}, {"do": "screenshot", "name": "nach upload"}])
    assert good[-1]["name"] == "nach-upload"
    for bad, match in [([{"do": "goto", "path": "https://evil.example"}], "Pfad"),
                       ([{"do": "goto", "path": "//evil.example/x"}], "Pfad"),
                       ([{"do": "evaluate", "text": "x"}], "do muss"),
                       ([{"do": "click", "css": "#x"}], "unbekannte Felder"),
                       ([{"do": "upload", "label": "Datei", "fixture": "/etc/passwd"}], "upload nur"),
                       ([{"do": "fill", "label": "Titel"}], "braucht value"),
                       ([{"do": "click", "role": "button"}], "braucht name"),
                       ([{"do": "click", "text": "x"}] * 26, "Schritte")]:
        with pytest.raises(UiCheckError, match=match):
            validate_steps(bad)


def test_acceptance_contract_rejects_an_invalid_click_path() -> None:
    from flowagents.contract import validate

    case = {"type": "testfall", "key": "T1", "title": "STL", "criterion": "R1", "steps": [{"action": "a", "expected": "b"}]}
    ok = {"status": "fertig", "summary": "s", "artifacts": [{**case, "ui": [{"do": "goto", "path": "/dms"}]}]}
    assert validate(ok, role="akzeptanztest", kind="create").artifacts[0]["ui"]
    bad = {**ok, "artifacts": [{**case, "ui": [{"do": "goto", "path": "http://x"}]}]}
    with pytest.raises(Exception, match="Pfad"):
        validate(bad, role="akzeptanztest", kind="create")


class FakeUi:
    NAME = "flow-agents-preview"

    def __init__(self) -> None:
        self.seen: list = []

    def prepare_network(self, name: str) -> None:
        self.seen.append(("net", name))

    def run(self, scenarios):  # noqa: ANN001, ANN201
        self.seen.append(("run", scenarios))
        return {"passed": 1, "total": 1, "seconds": 1.0,
                "scenarios": [{"key": scenarios[0]["key"], "title": "t", "passed": True, "steps": [], "screenshots": []}]}


class FakePreview:
    NAME = "flow-agents-preview"

    def start(self, workspace):  # noqa: ANN001, ANN201
        return "http://localhost:8098"

    def stop(self) -> None:
        return None


def test_g4_runs_click_paths_against_the_preview_and_attaches_the_result(make_engine, monkeypatch) -> None:  # noqa: ANN001
    import threading

    from flowagents.providers import SimulatedProvider

    original = SimulatedProvider.generate

    def with_ui(self, request):  # noqa: ANN001, ANN202
        reply = original(self, request)
        if request.agent.role != "akzeptanztest":
            return reply
        import json as _json

        data = _json.loads(reply.text)
        for item in data.get("artifacts", []):
            item["ui"] = [{"do": "goto", "path": "/dms"}, {"do": "expect_text", "text": "Dokumente"}]
        return AgentReply(text=_json.dumps(data), provider=reply.provider, model=reply.model,
                          output_tokens=reply.output_tokens)

    monkeypatch.setattr(SimulatedProvider, "generate", with_ui)
    ui = FakeUi()
    engine = make_engine(ui_runner=ui, preview=FakePreview())
    run = submit(engine)
    drive(engine)
    for thread in threading.enumerate():
        if thread.name.startswith("ui-check-"):
            thread.join(10)
    decision = open_decision(engine, run["id"])
    assert decision["gate"] == "G4" and decision["context"]["ui_check"]["passed"] == 1
    assert ui.seen[0] == ("net", "flow-agents-preview") and ui.seen[1][1][0]["steps"][0]["path"] == "/dms"
    assert engine.store.latest_artifact(run["id"], "ui_pruefung")["content"]["total"] == 1


# -- Referenzdateien je Änderungsbereich (REQ-AGT-023) ---------------------------------------------
def test_reference_files_are_readable_but_not_writable(make_engine, git_repo) -> None:  # noqa: ANN001
    import subprocess

    (git_repo / "docs" / "prozess.md").write_text("# Wareneingang\nWE bucht, QS prüft.\n")
    subprocess.run(["git", "add", "-A"], cwd=git_repo, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "ref"],
                   cwd=git_repo, check=True)
    engine = make_engine()
    engine.scopes["prozess"] = {"label": "Prozess", "paths": ["docs/dms.md"], "reads": ["docs/prozess.md"]}
    run = submit(engine, scope="prozess")
    assert run["auftrag"]["reference_paths"] == ["docs/prozess.md"]
    seen = {}
    original = engine._render

    def spy(run_, step, agent, context):  # noqa: ANN001, ANN202
        seen[agent.role] = context
        return original(run_, step, agent, context)

    engine._render = spy
    drive(engine)
    assert "WE bucht" in seen["entwicklung"]["reference_files"]["docs/prozess.md"]
    assert seen["entwicklung"]["allowed_paths"] == ["docs/dms.md"]
    assert "reference_files" not in seen["geschaeftsfuehrung"]
    with pytest.raises(SandboxError, match="außerhalb"):
        engine.sandbox.apply("RUN-X", engine.sandbox.base_commit(), ["docs/dms.md"], {"docs/prozess.md": "x"})
