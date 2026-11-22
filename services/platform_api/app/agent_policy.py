"""Serverseitige Agentenrichtlinie der Plattform-API (KI-Entwicklungskonzept Teil 04/08/09).

Die Plattform-API vertraut dem Orchestrator nicht blind: Sie liest das versionierte
Agentenregister selbst und lässt eine Werkzeugoperation nur zu, wenn das Token gültig ist,
für FLOWWORK ausgestellt wurde, die Rolle aktiv ist und die Operation im Register steht.
Fehlt das Register oder ist es ungültig, sind alle Agentenoperationen gesperrt (fail closed).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import jwt
import yaml

ACTIVE = frozenset({"testbetrieb", "befristet_produktiv"})
FORBIDDEN_TOOL = re.compile(r"(approve|freigabe|merge|delete|loesch|deploy|admin|release)", re.I)
ORCHESTRATOR_ROLE = "orchestrator"
ORCHESTRATOR_ID = "FLOW-ORCHESTRATOR"
ORCHESTRATOR_TOOLS = frozenset({"rm.freeze_baseline"})
RM_AUDIENCE = "flowwork-rm"
RM_ISSUER = "flow-agents"
DEMO_RM_SECRET = "local-agent-rm-secret-change-before-network-use"


class PolicyError(PermissionError):
    def __init__(self, message: str, status: int = 403) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class AgentIdentity:
    role: str
    agent_id: str
    run_id: str
    token_id: str


@dataclass(frozen=True)
class AgentPolicy:
    agents: dict[str, dict[str, Any]]
    register_id: str
    policy_version: str
    source: str

    @classmethod
    def load(cls, directory: Path) -> AgentPolicy:
        try:
            data = yaml.safe_load((directory / "registry.yaml").read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise PolicyError(f"Agentenregister nicht lesbar: {type(exc).__name__}", 503) from exc
        if not isinstance(data, dict) or not isinstance(data.get("agents"), list):
            raise PolicyError("Agentenregister ungültig", 503)
        tools = set((data.get("tools") or {}).keys())
        if any(FORBIDDEN_TOOL.search(name) for name in tools):
            raise PolicyError("Agentenregister enthält verbotene Werkzeuge", 503)
        agents: dict[str, dict[str, Any]] = {}
        for entry in data["agents"]:
            role = str(entry.get("role", ""))
            if not role or role in agents or role == ORCHESTRATOR_ROLE:
                raise PolicyError("Agentenregister enthält doppelte oder reservierte Rollen", 503)
            entry_tools = set(entry.get("tools") or [])
            if entry_tools - tools:
                raise PolicyError(f"Agent {entry.get('id')}: unbekanntes Werkzeug", 503)
            agents[role] = {
                "id": str(entry.get("id")),
                "name": str(entry.get("name")),
                "status": str(entry.get("status")),
                "autonomy": str(entry.get("autonomy")),
                "approved_until": date.fromisoformat(str(entry.get("approved_until"))),
                "tools": frozenset(entry_tools),
            }
        return cls(agents, str(data.get("register_id", "")), str(data.get("policy_version", "")), str(directory))

    def authorize(self, identity: AgentIdentity, operation: str, today: date | None = None) -> None:
        if identity.role == ORCHESTRATOR_ROLE:
            if identity.agent_id != ORCHESTRATOR_ID or operation not in ORCHESTRATOR_TOOLS:
                raise PolicyError(f"Orchestrator darf {operation} nicht ausführen")
            return
        if operation in ORCHESTRATOR_TOOLS:
            raise PolicyError(f"{operation} ist dem Orchestrator vorbehalten")
        agent = self.agents.get(identity.role)
        if agent is None or agent["id"] != identity.agent_id:
            raise PolicyError("Rolle oder Agenten-ID stehen nicht im Register")
        if agent["status"] not in ACTIVE or (today or date.today()) > agent["approved_until"]:
            raise PolicyError(f"{agent['name']} ist nicht aktiv freigegeben")
        if operation not in agent["tools"]:
            raise PolicyError(f"{agent['name']} besitzt das Werkzeug {operation} nicht")

    def public(self) -> dict[str, Any]:
        return {
            "register_id": self.register_id,
            "policy_version": self.policy_version,
            "agents": [
                {"role": role, "id": a["id"], "name": a["name"], "status": a["status"], "autonomy": a["autonomy"],
                 "approved_until": a["approved_until"].isoformat(), "tools": sorted(a["tools"])}
                for role, a in self.agents.items()
            ],
        }


def registry_directory() -> Path:
    configured = os.getenv("AGENT_REGISTRY_DIR")
    if configured:
        return Path(configured)
    for candidate in (Path("/app/agents"), Path(__file__).resolve().parents[3] / "agents"):
        if (candidate / "registry.yaml").is_file():
            return candidate
    return Path("/app/agents")


def rm_secret() -> str:
    return os.getenv("FLOW_AGENT_RM_SECRET", "") or DEMO_RM_SECRET


def verify_agent_token(authorization: str, *, secret: str | None = None) -> AgentIdentity:
    if not authorization.startswith("Bearer "):
        raise PolicyError("Agenten-Token fehlt", 401)
    try:
        claims = jwt.decode(
            authorization[7:],
            secret or rm_secret(),
            algorithms=["HS256"],
            audience=RM_AUDIENCE,
            issuer=RM_ISSUER,
            options={"require": ["exp", "iat", "aud", "iss", "sub", "jti"]},
        )
    except jwt.PyJWTError as exc:
        raise PolicyError("Agenten-Token ungültig oder abgelaufen", 401) from exc
    if int(claims["exp"]) - int(claims["iat"]) > 600:
        raise PolicyError("Agenten-Token ist zu lange gültig", 401)
    role, run_id = str(claims.get("role", "")), str(claims.get("run", ""))
    if not re.fullmatch(r"[a-z][a-z_-]{2,40}", role) or not re.fullmatch(r"RUN-[0-9]{8}-[0-9A-F]{6}", run_id):
        raise PolicyError("Agenten-Token ohne gültige Rolle oder Laufbindung", 401)
    return AgentIdentity(role=role, agent_id=str(claims["sub"]), run_id=run_id, token_id=str(claims["jti"]))
