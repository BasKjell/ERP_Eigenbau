"""Codex- und Claude-Abo-CLIs als isolierte Worker (übernommen aus Trading_Ai T-020/T-025/T-027).

Technisch gesperrt, solange ``container.execution_enabled`` nicht ausdrücklich gesetzt ist und
kein unveränderliches Image (``…@sha256:…``) konfiguriert wurde. Die Isolation entspricht dem
geprüften Trading-Pilot:

- Container read-only, ``--cap-drop ALL``, ``no-new-privileges``, Ressourcenlimits, keine Logs.
- Je Anbieter ein internes Docker-Netz mit eigenem Egress-Proxy, der nur den Anbieter erlaubt.
- Anmeldedaten aus einem eigenen, schreibgeschützten Volume; der Worker kopiert ausschließlich
  ``.codex/auth.json`` bzw. ``.claude/.credentials.json`` in ein frisches Home im tmpfs.
- Der Worker sieht kein Repository, keine ``.env`` und keine Fachsystem-Tokens. Er bekommt nur
  den Prompt mit den Arbeitsdaten des Laufs und liefert Text zurück.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import signal
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from .providers import AgentReply, AgentRequest, ProviderError

IMAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]+@sha256:[a-f0-9]{64}")
SAFE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*")
RESTRICTED_NETWORKS = {"none", "host", "bridge", "default"}
EFFORTS = {"low", "medium", "high"}
QUOTA = re.compile(r"hit your limit|usage limit|rate.limit|quota exceeded", re.I)


class QuotaExceeded(ProviderError):
    """Anbieterkontingent erschöpft; derselbe Schritt wird nach der Sperrfrist wiederholt."""


def validate_settings(settings: dict[str, Any]) -> None:
    """Fail closed bei unsicheren oder unvollständigen Worker-Einstellungen."""
    if not isinstance(settings.get("execution_enabled"), bool):
        raise ValueError("container.execution_enabled muss true oder false sein")
    accounts = {name: settings[name] for name in ("codex", "claude") if isinstance(settings.get(name), dict)}
    for name, account in accounts.items():
        for key in ("model", "network", "auth_volume"):
            if not isinstance(account.get(key), str) or not SAFE.fullmatch(account[key]):
                raise ValueError(f"container.{name}.{key} fehlt oder ist ungültig")
        if account["network"] in RESTRICTED_NETWORKS:
            raise ValueError(f"container.{name} braucht ein eigenes internes Docker-Netz")
        if not re.fullmatch(r"http://[A-Za-z0-9_.-]+:[0-9]{1,5}", str(account.get("proxy", ""))):
            raise ValueError(f"container.{name} braucht einen beschränkten Forward-Proxy")
        if account.get("effort", "medium") not in EFFORTS:
            raise ValueError(f"container.{name}.effort muss low, medium oder high sein")
    if len(accounts) == 2:
        for key in ("network", "auth_volume"):
            if accounts["codex"][key] == accounts["claude"][key]:
                raise ValueError(f"Codex und Claude brauchen getrennte {key}")
    if not str(settings.get("worker_script", "/opt/dev_orchestrator_worker.py")).startswith("/opt/"):
        raise ValueError("container.worker_script muss im Image unter /opt liegen")
    if settings["execution_enabled"] and not IMAGE.fullmatch(str(settings.get("image", ""))):
        raise ValueError("Ausführung braucht ein unveränderliches Worker-Image (…@sha256:…)")


class ContainerProvider:
    def __init__(self, name: str, settings: dict[str, Any]) -> None:
        if name not in {"codex", "claude"}:
            raise ValueError("Container-Provider ist codex oder claude")
        validate_settings(settings)
        if not isinstance(settings.get(name), dict):
            raise ValueError(f"container.{name} ist nicht konfiguriert")
        self.name, self.settings, self.account = name, settings, settings[name]
        self.owner = uuid.uuid4().hex
        self.cooldown_until = 0.0

    def preflight(self) -> None:
        if not self.settings["execution_enabled"]:
            raise ProviderError("CLI-Worker technisch gesperrt (container.execution_enabled=false)")
        orphan = _run(["docker", "ps", "-aq", "--filter", "label=flow-agents-worker"]).strip()
        if orphan:
            raise ProviderError("verwaister Worker-Container; vor dem Start prüfen")
        _run(["docker", "image", "inspect", self.settings["image"]])
        network = _run(["docker", "network", "inspect", "--format", "{{.Internal}} {{.Driver}}",
                        self.account["network"]]).strip()
        if network != "true bridge":
            raise ProviderError("Worker-Netz muss eine interne Docker-Bridge sein")
        volume = _run(["docker", "volume", "inspect", "--format", "{{.Driver}} {{json .Options}}",
                       self.account["auth_volume"]]).strip()
        if volume not in {"local null", "local {}"}:
            raise ProviderError("Anmeldedaten brauchen ein gewöhnliches Docker-Volume")

    def generate(self, request: AgentRequest) -> AgentReply:
        if not self.settings["execution_enabled"]:
            raise ProviderError("CLI-Worker technisch gesperrt (container.execution_enabled=false)")
        if time.time() < self.cooldown_until:
            raise ProviderError(f"{self.name}: Kontingentpause aktiv")
        effort = self.account.get("effort", "medium")
        prompt = request.system + "\n\n" + request.user
        if self.name == "codex":
            cli = ["codex", "--ask-for-approval", "never", "exec", "--skip-git-repo-check", "--sandbox", "read-only",
                   "--model", self.account["model"], "-c", f'model_reasoning_effort="{effort}"', "--json", "-"]
        else:
            cli = ["claude", "-p", "--model", self.account["model"], "--effort", effort, "--output-format", "json",
                   "--permission-mode", "dontAsk", "--setting-sources", "", "--tools", "Read", "--allowedTools", "Read",
                   "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--no-session-persistence"]
        # Worker-Einstieg des Trading-Images: Provider, Ausgabelimit, Dateiliste (null = nur Text), CLI.
        script = str(self.settings.get("worker_script", "/opt/dev_orchestrator_worker.py"))
        argv = ["python", script, self.name, str(self.settings.get("output_bytes", 2_000_000)), "null", *cli]
        started = time.monotonic()
        code, output = self._docker(argv, prompt)
        if code:
            raise ProviderError(f"{self.name}: isolierter Worker oder Abo-Anmeldung fehlgeschlagen")
        try:
            envelope = json.loads(output)
        except ValueError:
            raise ProviderError(f"{self.name}: Worker lieferte keine Hülle") from None
        events = str(envelope.get("events", ""))
        if envelope.get("code") and QUOTA.search(events):
            self.cooldown_until = time.time() + int(self.settings.get("cooldown_seconds", 18000))
            raise QuotaExceeded(f"{self.name}: Nutzungslimit erreicht")
        if envelope.get("code"):
            raise ProviderError(f"{self.name}: CLI endete mit Fehler")
        text = _final_text(self.name, events)
        if not text.strip():
            raise ProviderError(f"{self.name}: keine Antwort")
        return AgentReply(text=text, provider=self.name, model=self.account["model"], output_tokens=len(text) // 4,
                          input_tokens=len(prompt) // 4, seconds=round(time.monotonic() - started, 2))

    def docker_args(self, name: str) -> list[str]:
        cfg, account = self.settings, self.account
        uid, gid = os.getuid(), os.getgid()
        args = [
            "docker", "run", "--rm", "-i", "--name", name, "--label", f"flow-agents-worker={self.owner}",
            "--pull", "never", "--read-only", "--init", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--user", f"{uid}:{gid}", "--pids-limit", str(cfg.get("pids", 128)),
            "--memory", str(cfg.get("memory", "4g")), "--memory-swap", str(cfg.get("memory", "4g")),
            "--cpus", str(cfg.get("cpus", 2)),
            "--tmpfs", f"/tmp:rw,nosuid,nodev,size={cfg.get('scratch', '1g')},uid={uid},gid={gid},mode=0700",
            "--tmpfs", f"/work:rw,nosuid,nodev,size=16m,uid={uid},gid={gid},mode=0700",
            "--network", account["network"], "--workdir", "/work", "--env", "HOME=/tmp", "--log-driver", "none",
            "--mount", f"type=volume,source={account['auth_volume']},target=/auth,readonly,volume-nocopy",
        ]
        if self.name == "codex":
            args += ["--tmpfs", f"/run/codex-agent:rw,nosuid,nodev,size=64m,uid={uid},gid={gid},mode=0700"]
        proxy = account["proxy"]
        for key, value in {"http_proxy": proxy, "https_proxy": proxy, "all_proxy": "", "no_proxy": ""}.items():
            args += ["--env", f"{key}={value}", "--env", f"{key.upper()}={value}"]
        return args

    def _docker(self, argv: list[str], prompt: str) -> tuple[int, str]:
        name = f"flow-agents-{uuid.uuid4().hex[:12]}"
        args = [*self.docker_args(name), "--entrypoint", argv[0], self.settings["image"], *argv[1:]]
        timeout, maximum = int(self.settings.get("timeout_seconds", 1800)), int(self.settings.get("output_bytes", 2_000_000))
        try:
            with tempfile.TemporaryFile() as stdin, tempfile.TemporaryFile() as output:
                stdin.write(prompt.encode())
                stdin.seek(0)
                proc = subprocess.Popen(args, stdin=stdin, stdout=output, stderr=output, start_new_session=True)
                try:
                    deadline = time.monotonic() + timeout
                    while proc.poll() is None:
                        if time.monotonic() >= deadline or os.fstat(output.fileno()).st_size > maximum:
                            raise ProviderError(f"{self.name}: Laufzeit- oder Ausgabelimit überschritten")
                        time.sleep(0.2)
                    output.seek(0)
                    return proc.returncode, output.read(maximum).decode(errors="replace")
                finally:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=15, check=False)


def _final_text(provider: str, events: str) -> str:
    if provider == "claude":
        try:
            return str(json.loads(events)["result"])
        except (ValueError, KeyError, TypeError):
            return ""
    messages = []
    for line in events.splitlines():
        with contextlib.suppress(ValueError):
            event = json.loads(line)
            item = event.get("item", {}) if isinstance(event, dict) else {}
            if isinstance(event, dict) and event.get("type") == "item.completed" and item.get("type") == "agent_message":
                messages.append(str(item.get("text", "")))
    return "\n".join(messages)


def _run(args: list[str]) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProviderError(f"{Path(args[0]).name}: {type(exc).__name__}") from None
    if result.returncode:
        raise ProviderError(f"{Path(args[0]).name} {args[1]}: fehlgeschlagen")
    return result.stdout
