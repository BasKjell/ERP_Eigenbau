"""FLOWPORTAL-Anbindung an den FLOWAGENTS-Orchestrator (Backend for Frontend).

Der Browser spricht nie direkt mit dem Orchestrator. Die Plattform-API stellt je Aufruf ein
kurzlebiges Token aus; bei Aufträgen, Entscheidungen und Steuerung enthält es die in FLOWID
angemeldete Person. Ist der Orchestrator nicht erreichbar, zeigt das Portal das Register mit
dem Hinweis „Orchestrator nicht erreichbar“ statt erfundener Aktivität.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any

import jwt

from .agent_policy import AgentPolicy, PolicyError, registry_directory

DEMO_API_SECRET = "local-agents-api-secret-change-before-network-use"


class AgentsUnavailable(RuntimeError):
    pass


class AgentsRejected(RuntimeError):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status


class AgentsGateway:
    def __init__(self, base_url: str | None = None, secret: str | None = None, timeout: float = 8) -> None:
        self.base_url = (base_url or os.getenv("AGENTS_API_URL", "http://127.0.0.1:8095")).rstrip("/")
        self.secret = secret or os.getenv("FLOW_AGENTS_API_SECRET", "") or DEMO_API_SECRET
        self.timeout = timeout

    def _token(self, user: dict[str, Any] | None) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {"iss": "flow-platform-api", "aud": "flow-agents-api", "sub": "platform-api",
                                  "iat": now, "exp": now + 60}
        if user:
            claims["user"] = {"username": str(user.get("username") or user.get("email") or ""),
                              "name": str(user.get("name") or user.get("username") or ""),
                              "roles": sorted({str(r) for r in user.get("roles", [])})}
        return jwt.encode(claims, self.secret, algorithm="HS256")

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None,
                user: dict[str, Any] | None = None) -> dict[str, Any]:
        if not re.fullmatch(r"/v1/[A-Za-z0-9_/?=&.-]*", path):
            raise AgentsRejected(400, "ungültiger Pfad")
        data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self._token(user)}"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read(8_000_000) or b"{}")
        except urllib.error.HTTPError as exc:
            try:
                detail = str(json.loads(exc.read(20_000)).get("detail", ""))
            except (ValueError, AttributeError):
                detail = ""
            raise AgentsRejected(exc.code, detail or f"Orchestrator antwortete {exc.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise AgentsUnavailable(f"Orchestrator nicht erreichbar ({type(exc).__name__})") from None

    def overview(self) -> dict[str, Any]:
        try:
            return {"available": True, **self.request("GET", "/v1/overview")}
        except AgentsUnavailable as exc:
            return self.offline(str(exc))

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
