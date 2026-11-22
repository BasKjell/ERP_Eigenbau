"""Client für den RM-Adapter in FLOWWORK (KI-Entwicklungskonzept Teil 08).

Der Orchestrator ruft FLOWWORK mit einem kurzlebigen, rollen- und laufgebundenen Token auf.
Der Adapter prüft Signatur, Zielressource (``aud``), Ablauf, Rolle laut Register und die
erlaubte Operation erneut. Modelle sehen diese Tokens nie.
"""

from __future__ import annotations

import json
import secrets
import time
import urllib.error
import urllib.request
from typing import Any, Protocol

import jwt

AUDIENCE = "flowwork-rm"
ISSUER = "flow-agents"


class RMError(RuntimeError):
    """FLOWWORK hat die Operation abgelehnt oder war nicht erreichbar."""


class RMConflict(RMError):
    """Versionskonflikt; ``current`` enthält den bestätigten Objektstand (KI-EK Teil 08)."""

    def __init__(self, message: str, current: dict[str, Any]) -> None:
        super().__init__(message)
        self.current = current


class RM(Protocol):
    enabled: bool

    def call(self, role: str, agent_id: str, run_id: str, operation: str, payload: dict[str, Any]) -> dict[str, Any]: ...


def mint(secret: str, *, role: str, agent_id: str, run_id: str, audience: str = AUDIENCE, ttl: int = 300) -> str:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": audience,
        "sub": agent_id,
        "role": role,
        "run": run_id,
        "iat": now,
        "exp": now + ttl,
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(claims, secret, algorithm="HS256")


# Operation -> (HTTP-Methode, Pfad). IDs werden vom Orchestrator gesetzt, nie vom Modell.
OPERATIONS = {
    "rm.create_draft": ("POST", "/api/rm/v1/drafts"),
    "rm.update_draft": ("POST", "/api/rm/v1/drafts/update"),
    "rm.comment": ("POST", "/api/rm/v1/comments"),
    "rm.ask_owner": ("POST", "/api/rm/v1/questions"),
    "rm.create_test": ("POST", "/api/rm/v1/tests"),
    "rm.link_trace": ("POST", "/api/rm/v1/links"),
    "rm.freeze_baseline": ("POST", "/api/rm/v1/baselines"),
    "rm.search": ("POST", "/api/rm/v1/search"),
    "ticket.create": ("POST", "/api/rm/v1/tasks"),
}


class FlowworkRM:
    enabled = True

    def __init__(self, base_url: str, secret: str, *, timeout: float = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.secret = secret
        self.timeout = timeout

    def call(self, role: str, agent_id: str, run_id: str, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        if operation not in OPERATIONS:
            raise RMError(f"unbekannte Operation {operation}")
        method, path = OPERATIONS[operation]
        token = mint(self.secret, role=role, agent_id=agent_id, run_id=run_id)
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read(2_000_000) or b"{}")
        except urllib.error.HTTPError as exc:
            detail: Any = ""
            try:
                detail = json.loads(exc.read(20_000)).get("detail", "")
            except (ValueError, AttributeError):
                detail = ""
            if exc.code == 409 and isinstance(detail, dict) and isinstance(detail.get("current"), dict):
                raise RMConflict(f"FLOWWORK {operation}: {detail.get('message', 'Konflikt')}", detail["current"]) from None
            raise RMError(f"FLOWWORK {operation}: HTTP {exc.code} {detail}".strip()) from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise RMError(f"FLOWWORK nicht erreichbar: {type(exc).__name__}") from None


class OfflineRM:
    """Ersatz ohne FLOWWORK: protokolliert Aufrufe und vergibt lokale Objekt-IDs."""

    enabled = False

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def call(self, role: str, agent_id: str, run_id: str, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((role, operation, payload))
        number = len(self.calls)
        if operation == "rm.create_draft":
            return {"id": f"LOCAL-REQ-{number:03d}", "version": 1, "status": "draft"}
        if operation == "rm.update_draft":
            return {"id": payload["id"], "version": int(payload["expected_version"]) + 1, "status": "draft"}
        if operation == "rm.freeze_baseline":
            return {"id": f"LOCAL-BL-{number:03d}", "status": "frozen"}
        if operation == "rm.create_test":
            return {"id": f"LOCAL-TC-{number:03d}", "version": 1}
        if operation == "ticket.create":
            return {"id": f"LOCAL-T-{number:03d}"}
        return {"ok": True}
