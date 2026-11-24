"""OpenCode als lokaler Agenten-Worker (flowagents/opencode.py).

Isolation fail closed, Schlüssel nie in der Befehlszeile, keine Werkzeuge, Rückfall auf FLOWGATE und
Auswahl je Auftrag über „Umsetzung: opencode“.
"""

from __future__ import annotations

import json

import pytest

from flowagents.engine import EngineError
from flowagents.opencode import OpenCodeProvider, opencode_config, parse_events, validate_settings
from flowagents.providers import AgentReply, AgentRequest, ProviderError

from .conftest import PO, auftrag, drive
from .test_engine import Worker

IMAGE = "flow-agents-opencode@sha256:" + "a" * 64
SETTINGS = {"enabled": True, "image": IMAGE, "network": "flow-agents-opencode",
            "gateway_url": "http://agentgateway:4000/v1"}
EVENTS = "\n".join(json.dumps(e) for e in [
    {"type": "step_start", "part": {}},
    {"type": "text", "part": {"messageID": "m1", "text": "Ich prüfe …"}},
    {"type": "text", "part": {"messageID": "m2", "text": '{"status": '}},
    {"type": "text", "part": {"messageID": "m2", "text": '"ok"}'}},
    {"type": "step_finish", "part": {"tokens": {"input": 120, "output": 8}}},
    "kein json",
])


@pytest.mark.parametrize(("change", "message"), [
    ({"image": "flow-agents-opencode:1"}, "unveränderliches Image"),
    ({"network": "bridge"}, "internes Docker-Netz"),
    ({"gateway_url": "https://api.example.com/v1"}, "gateway_url"),
    ({"enabled": "ja"}, "true oder false"),
])
def test_unsafe_settings_are_rejected(change, message) -> None:  # noqa: ANN001
    with pytest.raises(ValueError, match=message):
        validate_settings({**SETTINGS, **change})


def test_disabled_worker_needs_no_image() -> None:
    validate_settings({"enabled": False})


def test_container_is_isolated_and_the_key_stays_out_of_the_command_line() -> None:
    provider = OpenCodeProvider(SETTINGS, {"entwicklung": "geheim-123"})
    args = provider.docker_args("flow-agents-opencode-x", "flow-coder")
    joined = " ".join(args)
    for flag in ("--read-only", "--cap-drop ALL", "no-new-privileges", "--network flow-agents-opencode",
                 "--log-driver none", "--pull never"):
        assert flag in joined
    assert "geheim-123" not in joined and "--env FLOWGATE_KEY" in joined
    assert "OPENCODE_DISABLE_AUTOUPDATE=1" in joined and "OPENCODE_DISABLE_MODELS_FETCH=1" in joined


def test_config_allows_only_flowgate_and_no_tools() -> None:
    config = opencode_config("http://agentgateway:4000/v1", "flow-coder")
    assert list(config["provider"]) == ["flowgate"]
    assert config["provider"]["flowgate"]["options"]["apiKey"] == "{env:FLOWGATE_KEY}"
    assert config["model"] == "flowgate/flow-coder" and config["share"] == "disabled"
    assert set(config["permission"].values()) == {"deny"}
    assert not any(config["tools"].values())


def test_events_give_the_last_answer_and_tokens() -> None:
    assert parse_events(EVENTS) == ('{"status": "ok"}', 120, 8)


def request(registry, role: str = "entwicklung") -> AgentRequest:  # noqa: ANN001
    return AgentRequest("RUN-1", role, registry.agents[role], "System", "Auftrag", 400)


def test_generate_runs_the_worker_with_the_role_key(registry, monkeypatch) -> None:  # noqa: ANN001
    provider = OpenCodeProvider(SETTINGS, {"entwicklung": "k"})
    seen = {}

    def fake(alias, key, prompt):  # noqa: ANN001, ANN202
        seen.update(alias=alias, key=key, prompt=prompt)
        return 0, EVENTS

    monkeypatch.setattr(provider, "_docker", fake)
    reply = provider.generate(request(registry))
    assert (reply.provider, reply.model, reply.text) == ("opencode", "flow-coder", '{"status": "ok"}')
    assert seen == {"alias": "flow-coder", "key": "k", "prompt": "System\n\nAuftrag"}


def test_missing_key_or_failure_falls_back_to_flowgate(registry, monkeypatch) -> None:  # noqa: ANN001
    class Gateway:
        name = "gateway"

        def generate(self, req):  # noqa: ANN001, ANN202
            return AgentReply(text="{}", provider="gateway", model=req.agent.gateway_alias, output_tokens=1)

    provider = OpenCodeProvider(SETTINGS, {"entwicklung": "k"}, fallback=Gateway())
    monkeypatch.setattr(provider, "_docker", lambda *a: (1, ""))
    reply = provider.generate(request(registry))
    assert reply.provider.startswith("gateway (Rückfall: OpenCode endete mit Fehler")
    strict = OpenCodeProvider(SETTINGS, {})
    with pytest.raises(ProviderError, match="kein FLOWGATE-Schlüssel"):
        strict.generate(request(registry))


def test_order_with_opencode_runs_development_through_the_worker(make_engine) -> None:  # noqa: ANN001
    worker = Worker("opencode")
    engine = make_engine(providers={"opencode": worker})
    run = engine.submit(auftrag(execution="opencode"), PO,
                        "oc-0001-test")
    drive(engine)
    assert set(worker.roles) == {"entwicklung"}
    events = [e for e in engine.store.events(run_id=run["id"]) if e["kind"] == "eskalation"]
    assert events and "OpenCode" in events[0]["message"]


def test_opencode_order_needs_the_worker(make_engine) -> None:  # noqa: ANN001
    with pytest.raises(EngineError, match="OpenCode-Worker ist nicht eingerichtet"):
        make_engine().submit(auftrag(execution="opencode"), PO, "oc-0002-test")
