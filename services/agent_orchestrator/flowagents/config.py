"""Betriebskonfiguration des Orchestrators laden und Engine zusammensetzen (fail closed)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from . import registry as registry_module
from .adoption import Adoption, Preview
from .container import ContainerProvider, validate_settings
from .engine import Engine
from .providers import GatewayProvider, Provider, SimulatedProvider
from .rm import FlowworkRM, OfflineRM
from .sandbox import DockerCheck, LocalCheck, Sandbox
from .store import Store
from .sync import PlatformSync
from .uicheck import UiRunner

DEMO_SECRET_HINT = "change-before-network-use"
PROVIDER_NAMES = ("gateway", "simulated", "codex", "claude")


class ConfigError(ValueError):
    pass


@dataclass
class Runtime:
    engine: Engine
    store: Store
    settings: dict[str, Any]
    api_secret: str
    host: str
    port: int
    poll_seconds: float
    sync: PlatformSync | None = None


def _secret(settings: dict[str, Any], key: str, default: str) -> str:
    name = str(settings.get(key) or "")
    value = os.environ.get(name, "") if name else ""
    if value:
        return value
    if settings.get("demo_mode"):
        return default
    raise ConfigError(f"Geheimnis {name or key} fehlt (Umgebungsvariable)")


def load_settings(path: Path) -> dict[str, Any]:
    try:
        settings = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Konfiguration nicht lesbar: {type(exc).__name__}") from None
    if not isinstance(settings, dict):
        raise ConfigError("Konfiguration muss ein Objekt sein")
    for name, key in (("FLOW_AGENTS_STATE", "state_directory"), ("FLOW_AGENTS_PLATFORM_URL", "platform_url"),
                      ("FLOW_AGENTS_GATEWAY_URL", "gateway.url")):
        if name in os.environ:
            if "." in key:
                outer, inner = key.split(".")
                settings.setdefault(outer, {})[inner] = os.environ[name]
            else:
                settings[key] = os.environ[name]
    return settings


def build(config_path: Path, *, repo_root: Path) -> Runtime:
    settings = load_settings(config_path)
    agents_dir = (repo_root / str(settings.get("agents_directory", "agents"))).resolve()
    try:
        registry = registry_module.load(agents_dir)
    except registry_module.RegistryError as exc:
        raise ConfigError(f"Agentenregister ungültig: {exc}") from None

    state = Path(str(settings.get("state_directory", "~/.flow-agents"))).expanduser()
    if not state.is_absolute():
        raise ConfigError("state_directory muss absolut sein")
    state = state.resolve()
    if state.is_relative_to(repo_root.resolve()):
        raise ConfigError("state_directory muss außerhalb des Repositorys liegen")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    if state.stat().st_mode & 0o077:
        raise ConfigError("state_directory muss privat sein (0700)")
    store = Store(state / "flow-agents.sqlite")

    profile_providers = dict(settings.get("providers") or {})
    unknown = {value for value in profile_providers.values() if value not in PROVIDER_NAMES}
    if unknown:
        raise ConfigError(f"unbekannte Provider {sorted(unknown)}")
    used = set(profile_providers.values())
    providers: dict[str, Provider] = {"simulated": SimulatedProvider()}
    if "gateway" in used:
        gateway = settings.get("gateway") or {}
        prefix = str(gateway.get("keys_env_prefix", "FLOW_AGENT_GATEWAY_KEY_"))
        keys = {}
        for role in registry.agents:
            env_name = prefix + re.sub(r"[^A-Z0-9]", "_", role.upper())
            value = os.environ.get(env_name, "")
            if not value and settings.get("demo_mode"):
                value = f"agw-demo-{role}-{DEMO_SECRET_HINT}"
            if value:
                keys[role] = value
        providers["gateway"] = GatewayProvider(
            str(gateway.get("url", "http://127.0.0.1:4000")), keys,
            timeout=float(gateway.get("timeout_seconds", 900)), no_think=bool(gateway.get("no_think", True)),
        )
    container = settings.get("container") or {"execution_enabled": False}
    escalation = dict(settings.get("escalation") or {})
    escalation_roles = {str(k): str(v) for k, v in (escalation.get("roles") or {}).items()}
    _check_escalation(registry, escalation_roles)
    workers = (used | (set(escalation_roles.values()) if escalation.get("enabled") else set())) & {"codex", "claude"}
    if workers:
        try:
            validate_settings(container)
        except ValueError as exc:
            raise ConfigError(str(exc)) from None
        for name in workers:
            providers[name] = ContainerProvider(name, container)

    rm_secret = _secret(settings, "rm_secret_env", f"local-agent-rm-secret-{DEMO_SECRET_HINT}")
    rm = FlowworkRM(str(settings["platform_url"]), rm_secret) if settings.get("platform_url") else OfflineRM()

    sandbox = None
    sandbox_settings = settings.get("sandbox") or {}
    if sandbox_settings.get("enabled", True):
        repository = (repo_root / str(sandbox_settings.get("repository", "."))).resolve()
        mode = sandbox_settings.get("check", "docker")
        if mode == "docker":
            checker = DockerCheck(str(sandbox_settings.get("image", "flow-agents-sandbox:1")),
                                  str(sandbox_settings["command"]), timeout=int(sandbox_settings.get("timeout", 900)))
        elif mode == "local-test-only":
            checker = LocalCheck(list(sandbox_settings["command_argv"]))
        else:
            raise ConfigError("sandbox.check muss docker sein")
        sandbox = Sandbox(repository, state, base_ref=str(sandbox_settings.get("base_ref", "HEAD")),
                          allowed_prefixes=tuple(sandbox_settings.get("allowed_prefixes") or ()), checker=checker)

    adoption = preview = None
    adopt = settings.get("adoption") or {}
    if sandbox is not None and adopt.get("enabled", False):
        adoption = Adoption(sandbox.repo, state, allowed_prefixes=sandbox.allowed_prefixes,
                            push=bool(adopt.get("push", False)), remote=str(adopt.get("remote", "origin")))
    preview_settings = settings.get("preview") or {}
    if sandbox is not None and preview_settings.get("enabled", False):
        preview = Preview(image=str(preview_settings["image"]), port=int(preview_settings.get("port", 8098)),
                          network=str(preview_settings["network"]),
                          env={str(k): str(v) for k, v in (preview_settings.get("env") or {}).items()})
    ui_runner = None
    ui_settings = settings.get("ui_check") or {}
    if preview is not None and ui_settings.get("enabled", False):
        ui_runner = UiRunner(image=str(ui_settings.get("image", "flow-agents-ui-runner:1")),
                             timeout_seconds=int(ui_settings.get("timeout_seconds", 240)))
    budgets = {name: {k: int(v) for k, v in spec.items()} for name, spec in (settings.get("budgets") or {}).items()}
    engine = Engine(registry, store, providers, profile_providers, rm, sandbox,
                    scopes=dict(settings.get("scopes") or {}), demo_mode=bool(settings.get("demo_mode")),
                    adoption=adoption, preview=preview, budgets=budgets,
                    escalation={**escalation, "roles": escalation_roles}, ui_runner=ui_runner)
    listen = str(settings.get("listen", "127.0.0.1:8095"))
    host, _, port = listen.rpartition(":")
    api_secret = _secret(settings, "api_secret_env", f"local-agents-api-secret-{DEMO_SECRET_HINT}")
    sync = None
    if settings.get("platform_url") and settings.get("platform_sync", True):
        sync = PlatformSync(engine, str(settings["platform_url"]), api_secret)
    return Runtime(engine, store, settings, api_secret, host or "127.0.0.1", int(port),
                   float(settings.get("poll_seconds", 3)), sync)


WORKER_FAMILY = {"codex": "openai", "claude": "anthropic"}


def _check_escalation(registry: Any, roles: dict[str, str]) -> None:
    """Auch eskaliert gilt: Ersteller und Prüfer eines Artefakts gehören zu verschiedenen Modellfamilien."""
    for role, worker in roles.items():
        if worker not in WORKER_FAMILY:
            raise ConfigError(f"escalation.roles.{role}: nur codex oder claude")
        if role not in registry.agents:
            raise ConfigError(f"escalation.roles.{role}: unbekannte Rolle")

    def family(role: str) -> set[str]:
        local = registry.agents[role].family.casefold()
        return {local, WORKER_FAMILY[roles[role]]} if role in roles else {local}

    for author in registry.agents.values():
        reviewer = author.reviewed_by
        if reviewer and reviewer in registry.agents and family(author.role) & family(reviewer):
            raise ConfigError(f"Eskalation verletzt die Unabhängigkeit: {author.role} und "
                              f"{reviewer} könnten dieselbe Modellfamilie nutzen")
