"""Agenteneigenschaften in der Agentenzentrale: alle sehen sie, nur Administratoren ändern sie.

Übersteuerungen laufen durch dieselbe Prüfung wie das Register, werden protokolliert, ändern den
Registerstand und überstehen einen Neustart.
"""

from __future__ import annotations

import pytest

from flowagents.engine import Engine, EngineError
from flowagents.sync import PlatformSync

from .conftest import PO, TECH_LEAD, auftrag, drive

ADMIN = {"username": "admin.demo", "name": "Alex Vollzugriff", "roles": ["platform-admin"]}


def test_everyone_sees_the_full_configuration(make_engine) -> None:  # noqa: ANN001
    config = make_engine().agent_config("akzeptanztest")
    assert config["values"]["tools"] and "implementierung" not in config["values"]["reads"]
    assert config["values"]["prompt_text"].startswith("# Rolle 7")
    assert config["overridden"] == [] and config["history"] == []
    assert config["runtime"]["gateway_alias"] == "flow-reviewer" and config["runtime"]["family"] == "gemma"
    assert "pruefer" in config["options"]["model_profile"] and "rm.get" in config["options"]["tools"]
    with pytest.raises(EngineError, match="nicht im Agentenregister"):
        make_engine().agent_config("gibt_es_nicht")


def test_only_admins_change_agents(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    for person in (PO, TECH_LEAD):
        with pytest.raises(EngineError, match="nur Administratoren"):
            engine.update_agent("planung", {"mission": "Plant anders und besser."}, person, "Test durch Fachbereich")
    with pytest.raises(EngineError, match="Begründung"):
        engine.update_agent("planung", {"mission": "Plant anders und besser."}, ADMIN, "")


def test_admin_change_is_applied_logged_and_changes_the_digest(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    before = engine.registry.digest
    config = engine.update_agent("planung", {"mission": "Plant Aufgaben in kleinen Schritten.",
                                             "prompt_text": "# Planung\n\nPlane in kleinen, prüfbaren Schritten."},
                                 ADMIN, "Kleinere Aufgaben für die lokalen Modelle")
    assert engine.registry.digest != before
    assert engine.registry.agent("planung").mission == "Plant Aufgaben in kleinen Schritten."
    assert "Plane in kleinen" in engine.registry.prompt("planung")
    assert config["overridden"] == ["mission", "prompt_text"]
    entry = config["history"][0]
    assert entry["person"] == "Alex Vollzugriff" and set(entry["changes"]) == {"mission", "prompt_text"}
    assert entry["changes"]["prompt_text"] == ["(geändert)", "(geändert)"]
    assert any("ändert" in e["message"] for e in engine.store.events())


@pytest.mark.parametrize(("role", "changes", "message"), [
    ("akzeptanztest", {"reads": ["auftrag", "baseline", "implementierung"]}, "keine Implementierung"),
    ("codepruefung", {"model_profile": "coder"}, "nicht unabhängig"),
    ("planung", {"tools": ["rm.get", "rm.delete"]}, "unbekannte Werkzeuge"),
    ("planung", {"data_classes": ["geheim"]}, "Datenklasse"),
    ("planung", {"autonomy": "A4"}, "Stufe"),
    ("planung", {"limits": {"max_tasks_per_run": 5000}}, "0 bis 1000"),
    ("planung", {"id": "AG-X"}, "nicht änderbar"),
])
def test_changes_that_break_the_rules_are_rejected(make_engine, role, changes, message) -> None:  # noqa: ANN001
    engine = make_engine()
    digest = engine.registry.digest
    with pytest.raises(EngineError, match=message):
        engine.update_agent(role, changes, ADMIN, "Prüfung der Regeln")
    assert engine.registry.digest == digest and engine.store.agent_overrides() == {}


def test_reset_to_register_and_survive_a_restart(make_engine, registry) -> None:  # noqa: ANN001
    engine = make_engine()
    engine.update_agent("planung", {"owner": "Teamleitung IT"}, ADMIN, "Zuständigkeit gewechselt")
    restarted = Engine(registry, engine.store, engine.providers, engine.profile_providers, engine.rm, None)
    assert restarted.registry.agent("planung").owner == "Teamleitung IT"
    assert restarted.registry.digest == engine.registry.digest
    config = engine.update_agent("planung", {"owner": None}, ADMIN, "Zurück auf das Register")
    assert config["overridden"] == [] and engine.registry.digest == registry.digest
    with pytest.raises(EngineError, match="Keine Änderung"):
        engine.update_agent("planung", {"owner": config["base"]["owner"]}, ADMIN, "gleicher Wert")


def test_open_runs_stop_after_a_change_until_a_person_switches_them(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = engine.submit(auftrag(), PO, "cfg-0001-test")
    engine.update_agent("anforderungen", {"mission": "Leitet Anforderungen knapp ab."}, ADMIN, "Kürzere Anforderungen")
    drive(engine)
    assert engine.store.run(run["id"])["status"] == "blockiert"


def test_configuration_through_the_platform_sync(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    sync = PlatformSync(engine, "http://127.0.0.1:1", "x" * 40)
    seen = sync.execute({"kind": "agent_config", "payload": {"role": "planung"}})
    assert seen["status"] == 200 and seen["body"]["role"] == "planung"
    denied = sync.execute({"kind": "agent_update", "person": PO,
                           "payload": {"role": "planung", "changes": {"owner": "x y"}, "reason": "Versuch"}})
    assert denied["status"] == 403
    done = sync.execute({"kind": "agent_update", "person": ADMIN,
                         "payload": {"role": "planung", "changes": {"owner": "Teamleitung IT"}, "reason": "Wechsel"}})
    assert done["status"] == 200 and done["body"]["overridden"] == ["owner"]
    missing = sync.execute({"kind": "agent_config", "payload": {"role": "gibt_es_nicht"}})
    assert missing["status"] == 404


def test_run_summary_names_participants_and_involved_agents(make_engine) -> None:  # noqa: ANN001
    from .conftest import KEY_USER, open_decision

    engine = make_engine()
    run = engine.submit(auftrag(), PO, "cfg-0002-test")
    drive(engine)
    engine.decide(open_decision(engine, run["id"])["id"], KEY_USER, "annehmen", "geprüft")
    drive(engine)
    summary = next(r for r in engine.overview()["runs"] if r["id"] == run["id"])
    assert {p["username"] for p in summary["participants"]} == {PO["username"], KEY_USER["username"]}
    assert {"anforderungen", "entwicklung", "codepruefung"} <= set(summary["agents_involved"])
    assert summary["waiting_for"] == "release"
