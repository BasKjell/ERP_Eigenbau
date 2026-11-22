"""FLOWPORTAL-Anbindung an den FLOWAGENTS-Orchestrator (Backend for Frontend, Pull-Modell).

Der Orchestrator läuft außerhalb der Container und öffnet keinen von dort erreichbaren Port.
Er meldet seinen Zustand an ``/api/agents/sync/state`` und holt von Menschen ausgelöste Aktionen
(Fachauftrag, Entscheidung, Steuerung, Laufdetails) bei ``/api/agents/sync/actions`` ab. Die
Person stammt aus der geprüften FLOWID-Sitzung; der Orchestrator prüft die Befugnis erneut.

Meldet sich der Orchestrator nicht, zeigt das Portal das Register mit dem Hinweis
„Orchestrator nicht verbunden“ statt erfundener Aktivität.
"""

from __future__ import annotations

import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import jwt

from .agent_policy import AgentPolicy, PolicyError, registry_directory

DEMO_API_SECRET = "local-agents-api-secret-change-before-network-use"
SYNC_AUDIENCE = "flow-platform-sync"
STALE_AFTER = 15.0
LEASE_SECONDS = 30.0
MAX_ACTIONS = 200


class AgentsUnavailable(RuntimeError):
    pass


class AgentsRejected(RuntimeError):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status


@dataclass
class _Action:
    id: str
    kind: str
    payload: dict[str, Any]
    person: dict[str, Any] | None
    created: float
    leased_until: float = 0.0
    result: dict[str, Any] | None = None
    done: threading.Event = field(default_factory=threading.Event)


class AgentsHub:
    def __init__(self, secret: str | None = None) -> None:
        self.secret = secret or os.getenv("FLOW_AGENTS_API_SECRET", "") or DEMO_API_SECRET
        self._lock = threading.Lock()
        self._actions: dict[str, _Action] = {}
        self._overview: dict[str, Any] | None = None
        self._registry: dict[str, Any] | None = None
        self._seen = 0.0

    # -- Orchestrator-Seite --------------------------------------------------------------
    def verify(self, authorization: str) -> None:
        if not authorization.startswith("Bearer "):
            raise AgentsRejected(401, "Token fehlt")
        try:
            claims = jwt.decode(authorization[7:], self.secret, algorithms=["HS256"], audience=SYNC_AUDIENCE,
                                issuer="flow-agents", options={"require": ["exp", "iat", "aud", "iss"]})
        except jwt.PyJWTError:
            raise AgentsRejected(401, "Token ungültig") from None
        if int(claims["exp"]) - int(claims["iat"]) > 300:
            raise AgentsRejected(401, "Token zu lange gültig")

    def pending(self) -> list[dict[str, Any]]:
        now = time.time()
        with self._lock:
            self._seen = now
            ready = [a for a in self._actions.values() if a.result is None and a.leased_until < now]
            for action in ready[:20]:
                action.leased_until = now + LEASE_SECONDS
            return [{"id": a.id, "kind": a.kind, "payload": a.payload, "person": a.person} for a in ready[:20]]

    def complete(self, results: list[dict[str, Any]]) -> int:
        count = 0
        with self._lock:
            for result in results:
                action = self._actions.get(str(result.get("id", "")))
                if action is None or action.result is not None:
                    continue
                action.result = {"status": int(result.get("status", 500)), "body": result.get("body")}
                action.done.set()
                count += 1
        return count

    def publish(self, overview: dict[str, Any], registry: dict[str, Any] | None) -> None:
        with self._lock:
            self._overview = overview
            if registry:
                self._registry = registry
            self._seen = time.time()

    # -- Portal-Seite --------------------------------------------------------------------
    def connected(self) -> bool:
        return time.time() - self._seen < STALE_AFTER

    def overview(self) -> dict[str, Any]:
        with self._lock:
            overview, seen = self._overview, self._seen
        if overview is None or not self.connected():
            last = time.strftime("%H:%M:%S", time.localtime(seen)) if seen else "noch nie"
            return self.offline(f"Orchestrator meldet sich nicht (letzter Kontakt: {last})")
        return {"available": True, **overview}

    def registry(self) -> dict[str, Any]:
        with self._lock:
            registry = self._registry
        if registry is None or not self.connected():
            raise AgentsUnavailable("Orchestrator nicht verbunden")
        return registry

    def request(self, kind: str, payload: dict[str, Any], person: dict[str, Any] | None,
                *, wait: float = 12.0) -> dict[str, Any]:
        if not self.connected():
            raise AgentsUnavailable("Orchestrator nicht verbunden – Aktion wurde nicht angenommen")
        action = _Action(id=secrets.token_hex(8), kind=kind, payload=payload, created=time.time(),
                         person={"username": str(person.get("username") or person.get("email") or ""),
                                 "name": str(person.get("name") or person.get("username") or ""),
                                 "roles": sorted({str(r) for r in person.get("roles", [])})} if person else None)
        with self._lock:
            self._expire()
            self._actions[action.id] = action
        if not action.done.wait(wait):
            with self._lock:
                if action.leased_until == 0.0 and action.result is None:
                    # Noch nicht abgeholt: zurückziehen, damit sie nicht später unbemerkt ausgeführt wird.
                    self._actions.pop(action.id, None)
                    raise AgentsUnavailable("Orchestrator hat die Aktion nicht abgeholt; sie wurde verworfen")
            raise AgentsUnavailable("Orchestrator bearbeitet die Aktion noch; bitte Status in der Agentenzentrale prüfen")
        result = action.result or {"status": 500, "body": {}}
        if result["status"] >= 400:
            body = result.get("body") or {}
            raise AgentsRejected(result["status"], str(body.get("detail", "Aktion abgelehnt")))
        return result.get("body") or {}

    def _expire(self) -> None:
        cutoff = time.time() - 600
        for key in [k for k, a in self._actions.items() if a.created < cutoff]:
            self._actions.pop(key, None)
        while len(self._actions) >= MAX_ACTIONS:
            self._actions.pop(next(iter(self._actions)))

    @staticmethod
    def offline(reason: str) -> dict[str, Any]:
        try:
            policy = AgentPolicy.load(registry_directory()).public()
        except PolicyError as exc:
            policy = {"agents": [], "register_id": "", "policy_version": "", "error": str(exc)}
        return {
            "available": False,
            "reason": reason,
            "registry": {"id": policy.get("register_id"), "policy_version": policy.get("policy_version")},
            "agents": [{**agent, "state": "unbekannt", "current": None, "last": None, "number": index + 1}
                       for index, agent in enumerate(policy.get("agents", []))],
            "runs": [], "decisions": [], "events": [], "interactions": [], "pipeline": [], "human_roles": {},
            "metrics": {"runs_open": 0, "runs_done": 0, "decisions_open": 0, "agents_working": 0, "reworks": 0},
        }


class AgentUsageCollector:
    """Prometheus-Collector: Token und Modellaufrufe je Agentenrolle aus dem letzten Orchestrator-Stand.

    Enthält nur Zählwerte (Rolle, Anbieter, Modell) – keine Prompts, Antworten oder Auftragsinhalte.
    """

    def __init__(self, hub: AgentsHub) -> None:
        self.hub = hub

    def collect(self):  # noqa: ANN201
        from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

        with self.hub._lock:
            overview = self.hub._overview
        connected = GaugeMetricFamily("flow_agents_orchestrator_connected", "Orchestrator meldet sich (1/0)")
        connected.add_metric([], 1.0 if overview is not None and self.hub.connected() else 0.0)
        yield connected
        labels = ["role", "provider", "model"]
        tokens = CounterMetricFamily("flow_agents_tokens", "Verarbeitete Token je Agentenrolle",
                                     labels=[*labels, "type"])
        calls = CounterMetricFamily("flow_agents_model_calls", "Modellaufrufe je Agentenrolle", labels=labels)
        seconds = CounterMetricFamily("flow_agents_model_seconds", "Modellzeit in Sekunden je Agentenrolle",
                                      labels=labels)
        for row in ((overview or {}).get("usage") or {}).get("totals") or []:
            key = [str(row.get("role", "")), str(row.get("provider", "")), str(row.get("model", ""))]
            tokens.add_metric([*key, "input"], float(row.get("input_tokens") or 0))
            tokens.add_metric([*key, "output"], float(row.get("output_tokens") or 0))
            calls.add_metric(key, float(row.get("calls") or 0))
            seconds.add_metric(key, float(row.get("seconds") or 0))
        yield tokens
        yield calls
        yield seconds

