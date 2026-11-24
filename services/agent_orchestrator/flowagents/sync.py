"""Abgleich mit der Plattform-API (Pull-Modell, keine eingehende Verbindung zum Orchestrator).

Der Orchestrator läuft außerhalb der Container und öffnet keinen von dort erreichbaren Port.
Er meldet seinen Zustand an FLOWPORTAL und holt dort von Menschen ausgelöste Aktionen ab
(Fachauftrag, Entscheidung, Steuerung, Laufdetails). Die Plattform-API hat die Person über
FLOWID geprüft; die Engine prüft die Befugnis für jede Aktion erneut.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any

import jwt

from .engine import Engine, EngineError

AUDIENCE = "flow-platform-sync"
ISSUER = "flow-agents"
ACTIONS = ("submit", "decide", "control", "detail", "start_package", "agent_config", "agent_update")


class SyncError(RuntimeError):
    pass


class PlatformSync:
    def __init__(self, engine: Engine, base_url: str, secret: str, *, registry_extra: dict[str, Any] | None = None,
                 timeout: float = 10) -> None:
        self.engine = engine
        self.base_url = base_url.rstrip("/")
        self.secret = secret
        self.timeout = timeout
        self.registry_extra = registry_extra or {}
        self.connected = False
        self.last_error = ""

    def _token(self) -> str:
        now = int(time.time())
        return jwt.encode({"iss": ISSUER, "aud": AUDIENCE, "sub": "flow-orchestrator", "iat": now, "exp": now + 60},
                          self.secret, algorithm="HS256")

    def _request(self, method: str, path: str, payload: Any = None) -> Any:
        data = json.dumps(payload, ensure_ascii=False, default=str).encode() if payload is not None else None
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self._token()}"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read(4_000_000) or b"null")
        except urllib.error.HTTPError as exc:
            raise SyncError(f"Plattform-API antwortete {exc.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise SyncError(f"Plattform-API nicht erreichbar ({type(exc).__name__})") from None

    def execute(self, action: dict[str, Any]) -> dict[str, Any]:
        """Eine Aktion ausführen; Fehler werden als Ergebnis zurückgemeldet, nicht geworfen."""
        kind, payload, person = action.get("kind"), action.get("payload") or {}, action.get("person")
        try:
            if kind not in ACTIONS:
                return {"status": 400, "body": {"detail": "unbekannte Aktion"}}
            if kind == "detail":
                return {"status": 200, "body": self.engine.run_detail(str(payload.get("run_id", "")))}
            if kind == "agent_config":
                return {"status": 200, "body": self.engine.agent_config(str(payload.get("role", "")))}
            if not isinstance(person, dict) or not person.get("username"):
                return {"status": 403, "body": {"detail": "Aktion braucht eine angemeldete Person"}}
            if kind == "submit":
                body = self.engine.submit(dict(payload.get("auftrag") or {}), person,
                                          str(payload.get("idempotency_key", "")))
                return {"status": 201, "body": body}
            if kind == "start_package":
                body = self.engine.start_package(str(payload.get("project_id", "")), str(payload.get("package_key", "")),
                                                 person, str(payload.get("scope", "")))
                return {"status": 201, "body": body}
            if kind == "agent_update":
                body = self.engine.update_agent(str(payload.get("role", "")), dict(payload.get("changes") or {}),
                                                person, str(payload.get("reason", "")))
                return {"status": 200, "body": body}
            if kind == "decide":
                body = self.engine.decide(str(payload.get("decision_id", "")), person, str(payload.get("outcome", "")),
                                          str(payload.get("comment", "")))
                return {"status": 200, "body": body}
            self.engine.control(str(payload.get("action", "")), person, role=str(payload.get("role", "")),
                                run_id=str(payload.get("run_id", "")))
            return {"status": 200, "body": {"ok": True, "controls": self.engine.store.controls()}}
        except KeyError:
            return {"status": 404, "body": {"detail": "nicht gefunden"}}
        except EngineError as exc:
            message = str(exc)
            denied = ("Befugnis" in message or "Steuerung nur" in message or "nur Administratoren" in message)
            status = 403 if denied else 404 if "steht nicht im Agentenregister" in message else \
                409 if kind != "submit" else 422
            return {"status": status, "body": {"detail": message}}

    def once(self) -> int:
        """Ein Abgleich: Aktionen holen, ausführen, Ergebnisse und Zustand melden."""
        actions = self._request("GET", "/api/agents/sync/actions") or []
        results = []
        for action in actions[:20]:
            result = self.execute(action)
            results.append({"id": action.get("id"), **result})
        if results:
            self._request("POST", "/api/agents/sync/results", {"results": results})
        registry = {**self.engine.registry.public(),
                    "scopes": {k: {"label": v.get("label", k)} for k, v in self.engine.scopes.items()},
                    **self.registry_extra}
        self._request("POST", "/api/agents/sync/state", {"overview": self.engine.overview(), "registry": registry})
        return len(results)

    def run(self, stop: threading.Event, interval: float = 2.0) -> None:
        while not stop.is_set():
            try:
                handled = self.once()
                self.connected, self.last_error = True, ""
            except SyncError as exc:
                if self.connected or not self.last_error:
                    self.engine.store.event(None, "fehler", "orchestrator", "flowportal", str(exc), {})
                self.connected, self.last_error, handled = False, str(exc), 0
            stop.wait(0.2 if handled else interval)
