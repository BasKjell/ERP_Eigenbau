"""Anzeige der Agentenzentrale: laufbezogener Halter, Freigabebeziehung, Sammelabfragen (REQ-PRT-001).

Regressionstests zum Codex-Review „FLOWAGENTS Anzeige, Bedienung und Dokumentation“ (Befunde 1, 3, 4, 8).
"""

from __future__ import annotations

import subprocess
from typing import Any

from flowagents import uicheck

from .conftest import PO, auftrag, drive


def _run(run_id: str, status: str = "aktiv") -> dict[str, Any]:
    return {"id": run_id, "status": status, "reason": ""}


def test_holder_is_per_run_not_per_agent_role(make_engine) -> None:  # noqa: ANN001
    """REQ-PRT-001: Zwei Läufe bei derselben Rolle – nur der tatsächlich bearbeitete zeigt „arbeitet“."""
    engine = make_engine()
    step = next(s for s in engine.registry.steps if s.role == "entwicklung")
    running = {("RUN-B", "entwicklung")}
    assert engine._holder(_run("RUN-A"), step, None, running, {})["kind"] == "agent_eingeplant"
    assert engine._holder(_run("RUN-B"), step, None, running, {})["kind"] == "agent_arbeitet"


def test_holder_shows_global_and_agent_pause(make_engine) -> None:  # noqa: ANN001
    """REQ-PRT-001: Ein Stopp hält eingeplante Läufe an und wird je Lauf als „angehalten“ angezeigt."""
    engine = make_engine()
    step = next(s for s in engine.registry.steps if s.role == "entwicklung")
    assert engine._holder(_run("RUN-A"), step, None, set(), {"global": "pausiert"})["kind"] == "pausiert_global"
    paused = engine._holder(_run("RUN-A"), step, None, set(), {"agent:entwicklung": "pausiert"})
    assert paused == {"kind": "pausiert_agent", "role": "entwicklung"}
    # ein bereits laufender Schritt wird zu Ende geführt und als solcher gekennzeichnet
    finishing = engine._holder(_run("RUN-A"), step, None, {("RUN-A", "entwicklung")}, {"global": "pausiert"})
    assert finishing["kind"] == "agent_arbeitet" and finishing["stopping"] is True


def test_holder_names_waiting_person_and_blocked_reason(make_engine) -> None:  # noqa: ANN001
    """REQ-PRT-001: Wartet ein Lauf auf einen Menschen, zeigt der Halter dessen Rolle."""
    engine = make_engine()
    gate = next(s for s in engine.registry.steps if s.id == "G4")
    waiting = {"decider": "key-user"}
    assert engine._holder(_run("RUN-A", "wartet"), gate, waiting, set(), {}) == {"kind": "mensch", "role": "key-user"}
    blocked = engine._holder({**_run("RUN-A", "blockiert"), "reason": "Budget"}, gate, waiting, set(), {})
    assert blocked == {"kind": "blockiert", "reason": "Budget", "role": "key-user"}
    assert engine._holder(_run("RUN-A", "abgeschlossen"), None, None, set(), {}) == {"kind": "fertig"}


def test_approval_relation_follows_gate_requires(make_engine) -> None:  # noqa: ANN001
    """REQ-PRT-001: „Freigabe“ nur, wenn das Gate das Ergebnis voraussetzt; sonst nächster Entscheidungspunkt."""
    engine = make_engine()
    agents = {a["role"]: a["rights"]["decided_by"] for a in engine.overview()["agents"]}
    assert any(d["gate"] == "G3" and d["relation"] == "freigabe" for d in agents["entwicklung"])
    assert any(d["gate"] == "G1" and d["relation"] == "freigabe" for d in agents["anforderungspruefung"])
    planning = agents["planung"]  # G3 setzt den Plan nicht voraus
    assert not any(d["relation"] == "freigabe" for d in planning)
    assert any(d["gate"] == "G3" and d["relation"] == "naechste" for d in planning)
    for entries in agents.values():
        approved = {(d["gate"], d["role"]) for d in entries if d["relation"] == "freigabe"}
        assert not any(d["relation"] == "naechste" and (d["gate"], d["role"]) in approved for d in entries)


def test_participation_is_loaded_in_bulk(make_engine) -> None:  # noqa: ANN001
    """REQ-PRT-001: Beteiligung vieler Läufe mit zwei Sammelabfragen, gleiches Ergebnis wie je Lauf."""
    engine = make_engine()
    first = engine.submit(auftrag(), PO, "disp-0001")
    second = engine.submit(auftrag(title="Zweiter Auftrag zur Anzeige"), PO, "disp-0002")
    drive(engine)
    loaded = engine.store.participation([first["id"], second["id"], "RUN-UNBEKANNT"])
    assert loaded["RUN-UNBEKANNT"] == {"deciders": [], "roles": []}
    for run_id in (first["id"], second["id"]):
        assert loaded[run_id]["roles"] == [s["role"] for s in engine.store.steps(run_id)]
        single = engine._participation(engine.store.run(run_id))
        assert single == engine._participation(engine.store.run(run_id), loaded[run_id])
        assert "geschaeftsfuehrung" in single["agents_involved"]
    indexes = {row[0] for row in engine.store.db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert {"steps_run", "decisions_run"} <= indexes


def test_demo_removes_only_the_network_it_created(monkeypatch) -> None:  # noqa: ANN001
    """REQ-PRT-001: Die Klickprüfung entfernt das interne Netz nur, wenn dieser Lauf es angelegt hat."""
    calls: list[list[str]] = []

    def fake_run(args, **_):  # noqa: ANN001, ANN202
        calls.append(args)
        missing = args[:3] == ["docker", "network", "inspect"] and state["missing"]
        return subprocess.CompletedProcess(args, 1 if missing else 0, stdout="true\n", stderr="")

    monkeypatch.setattr(uicheck.subprocess, "run", fake_run)
    runner = uicheck.UiRunner(image="flow-agents-ui-runner:1")
    state = {"missing": True}
    assert runner.prepare_network("flow-agents-preview") is True
    assert ["docker", "network", "create", "--internal", runner.network] in calls
    runner.remove_network("flow-agents-preview")
    assert ["docker", "network", "rm", runner.network] in calls
    state["missing"] = False
    calls.clear()
    assert runner.prepare_network("flow-agents-preview") is False
    assert not any(c[:3] == ["docker", "network", "create"] for c in calls)


def test_overview_runs_carry_holder_without_per_run_queries(make_engine, monkeypatch) -> None:  # noqa: ANN001
    """REQ-PRT-001: Die Übersicht liefert je Lauf den Halter und lädt Beteiligung nicht je Lauf nach."""
    engine = make_engine()
    for number in range(3):
        engine.submit(auftrag(title=f"Übersichtsauftrag {number}"), PO, f"disp-1{number:03d}")
    drive(engine)
    calls: list[str] = []
    original_steps = engine.store.steps
    monkeypatch.setattr(engine.store, "steps", lambda run_id: calls.append(run_id) or original_steps(run_id))
    runs = engine.overview()["runs"]
    assert not calls, "Schritte je Lauf nachgeladen (N+1)"
    assert len(runs) == 3 and all(run["holder"]["kind"] for run in runs)
    assert all(run["agents_involved"] for run in runs)


def test_holder_since_is_the_start_of_the_actual_holder_state(make_engine) -> None:  # noqa: ANN001
    """REQ-PRT-001: „seit …“ bezieht sich auf den Beginn des Halterzustands – laufender Schritt bzw. offene
    Entscheidung –, nicht auf die letzte Änderung des Laufs. Ohne bekannten Beginn kein „since“."""
    engine = make_engine()
    step = next(s for s in engine.registry.steps if s.role == "entwicklung")
    gate = next(s for s in engine.registry.steps if s.id == "G4")
    working = engine._holder(_run("RUN-A"), step, None, {("RUN-A", "entwicklung"): "2026-11-25T08:00:00+00:00"}, {})
    assert working["since"] == "2026-11-25T08:00:00+00:00"
    waiting = engine._holder(_run("RUN-A", "wartet"), gate, {"decider": "key-user",
                                                           "created_at": "2026-11-25T07:00:00+00:00"}, {}, {})
    assert waiting == {"kind": "mensch", "role": "key-user", "since": "2026-11-25T07:00:00+00:00"}
    assert "since" not in engine._holder(_run("RUN-A"), step, None, {}, {}), "eingeplant: Beginn unbekannt"
    assert "since" not in engine._holder(_run("RUN-A"), step, None, set(), {"global": "pausiert"})


def test_overview_holder_since_comes_from_the_open_decision(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = engine.submit(auftrag(), PO, "disp-since-0001")
    drive(engine)
    summary = next(r for r in engine.overview()["runs"] if r["id"] == run["id"])
    decision = engine.store.decisions(status="offen", run_id=run["id"])[0]
    assert summary["holder"]["kind"] == "mensch" and summary["holder"]["since"] == decision["created_at"]
