"""Fachagenten: Administratoren legen sie an, zugewiesene Personen nutzen sie, ein Mensch gibt frei."""

from __future__ import annotations

import pytest

from flowagents.engine import EngineError
from flowagents.sync import PlatformSync

from .conftest import PO

ADMIN = {"username": "admin.demo", "name": "Alex Vollzugriff", "roles": ["platform-admin"]}
BUYER = {"username": "demo06", "name": "Felix Hoffmann", "roles": ["procurement-user"]}
OTHER = {"username": "demo21", "name": "Julia Schmitz", "roles": ["production-user"]}
SPEC = {"name": "Einkaufs-Mail-Agent", "purpose": "Beantwortet Lieferantenmails mit einem Entwurf.",
        "template": "mail_antwort", "model_profile": "assistenz", "context_sources": ["einkauf"],
        "data_class": "intern", "prompt": "Du beantwortest Lieferantenmails sachlich und sagst nichts Unbelegtes zu.",
        "assigned_roles": ["procurement-user"], "assigned_users": []}
MAIL = {"absender": "a@baltic.example", "betreff": "PO-2027-0088 Verzug", "text": "Wir liefern zwei Tage später."}


def work(engine) -> None:  # noqa: ANN001
    while engine.process_business_job():
        pass


def test_only_admins_create_and_specs_are_checked(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    with pytest.raises(EngineError, match="nur Administratoren"):
        engine.save_business_agent(SPEC, PO)
    for change, message in [({"template": "shell"}, "Vorlage"), ({"model_profile": "gibt-es-nicht"}, "Modellprofil"),
                            ({"context_sources": ["personal"]}, "Datenquellen"), ({"assigned_roles": []}, "zuweisen"),
                            ({"assigned_users": ["x; drop"]}, "ungültige Zuweisung"), ({"prompt": "kurz"}, "prompt")]:
        with pytest.raises(EngineError, match=message):
            engine.save_business_agent({**SPEC, **change}, ADMIN)
    agent = engine.save_business_agent(SPEC, ADMIN)
    assert agent["id"] == "FA-001" and agent["autonomy"] == "A1"
    assert engine.save_business_agent({**SPEC, "status": "pausiert"}, ADMIN, agent["id"])["status"] == "pausiert"


def test_local_ai_drafts_an_agent_for_the_admin(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    with pytest.raises(EngineError, match="nur Administratoren"):
        engine.request_business_design("Ein Agent für Einkaufsmails an Lieferanten", PO)
    job = engine.request_business_design("Ein Agent, der Mails im Einkauf beantwortet", ADMIN)
    work(engine)
    done = engine.store.business_job(job["id"])
    assert done["status"] == "fertig" and done["output"]["template"] == "mail_antwort"
    assert done["output"]["context_sources"] == ["einkauf"]


def test_assigned_user_gets_a_draft_and_decides(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    agent = engine.save_business_agent(SPEC, ADMIN)
    with pytest.raises(EngineError, match="Befugnis"):
        engine.submit_business_task(agent["id"], MAIL, OTHER)
    job = engine.submit_business_task(agent["id"], MAIL, BUYER, {"einkauf": {"bestellungen": []}, "personal": {"x": 1}})
    assert set(job["input"]["_context"]) == {"einkauf"}  # nur Quellen des Agenten
    work(engine)
    done = engine.store.business_job(job["id"])
    assert done["status"] == "fertig" and done["output"]["antwort_text"] and done["output"]["risiko"] == "mittel"
    with pytest.raises(EngineError, match="Befugnis"):
        engine.decide_business_job(job["id"], "freigeben", OTHER)
    final = engine.decide_business_job(job["id"], "freigeben", BUYER, {"antwort_text": "Geprüfter Text"})
    assert final["status"] == "freigegeben" and final["output"]["antwort_text"] == "Geprüfter Text"
    assert final["decided_by"]["username"] == "demo06"
    with pytest.raises(EngineError, match="Nur fertige"):
        engine.decide_business_job(job["id"], "verwerfen", BUYER)
    assert any(u["role"] == "fachagenten" for u in engine.store.usage_totals())


def test_paused_agent_and_missing_input_are_rejected(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    agent = engine.save_business_agent({**SPEC, "status": "pausiert"}, ADMIN)
    with pytest.raises(EngineError, match="pausiert"):
        engine.submit_business_task(agent["id"], MAIL, BUYER)
    engine.save_business_agent(SPEC, ADMIN, agent["id"])
    with pytest.raises(EngineError, match="Text der E-Mail fehlt"):
        engine.submit_business_task(agent["id"], {"betreff": "x"}, BUYER)


def test_model_failure_marks_the_job(make_engine) -> None:  # noqa: ANN001
    from flowagents.providers import ProviderError

    class Broken:
        name = "gateway"

        def generate(self, request):  # noqa: ANN001, ANN202
            raise ProviderError("FLOWGATE nicht erreichbar")

    engine = make_engine(providers={"gateway": Broken()},
                         profile_providers={"builder": "simulated", "coder": "simulated", "pruefer": "simulated",
                                            "assistenz": "gateway", "leitung": "simulated"})
    agent = engine.save_business_agent(SPEC, ADMIN)
    job = engine.submit_business_task(agent["id"], MAIL, BUYER)
    work(engine)
    failed = engine.store.business_job(job["id"])
    assert failed["status"] == "fehler" and "FLOWGATE" in failed["error"]


def test_overview_and_sync(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    sync = PlatformSync(engine, "http://127.0.0.1:1", "x" * 40)
    denied = sync.execute({"kind": "fa_save", "person": PO, "payload": {"spec": SPEC}})
    assert denied["status"] == 403
    saved = sync.execute({"kind": "fa_save", "person": ADMIN, "payload": {"spec": SPEC}})
    assert saved["status"] == 200
    task = sync.execute({"kind": "fa_task", "person": BUYER, "payload": {"agent_id": saved["body"]["id"], "input": MAIL}})
    assert task["status"] == 201
    business = engine.overview()["business"]
    assert business["agents"][0]["open_jobs"] == 1 and "mail_antwort" in business["templates"]
    assert "assistenz" in business["profiles"]
