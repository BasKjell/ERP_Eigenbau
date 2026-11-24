"""OpenCode als lokaler Agenten-Worker (Open-Source-CLI, https://opencode.ai).

OpenCode läuft wie die Codex-/Claude-Worker in einem isolierten Container, nutzt aber kein Abo,
sondern die lokalen Modelle über FLOWGATE. Damit bleiben auch vertrauliche Aufträge im Haus.

Isolation (fail closed):

- Image nur per Digest (``…@sha256:…``) und mit fester OpenCode-Version (``opencode.Dockerfile``).
- Container read-only, ``--cap-drop ALL``, ``no-new-privileges``, Ressourcenlimits, keine Logs.
- Internes Docker-Netz ohne Internet (``flow-agents-opencode``); einziger Partner ist FLOWGATE.
- Schlüssel ist der virtuelle FLOWGATE-Schlüssel der Rolle; er geht über die Prozessumgebung an
  ``docker run --env FLOWGATE_KEY`` und steht nie in der Befehlszeile. FLOWGATE erlaubt je Schlüssel nur
  den Modellalias des Profils.
- OpenCode sieht kein Repository: nur den Prompt als Datei ``/work/auftrag.md`` im tmpfs.
  Schreiben, Bearbeiten, Shell und Webzugriff sind per Konfiguration verboten, Plugins, Skills,
  Modellkatalog-Abruf und Selbstaktualisierung abgeschaltet.

Fällt der Worker aus (Image, Netz, Laufzeit), antwortet auf Wunsch der direkte FLOWGATE-Aufruf
(``fallback``); das Ergebnis ist dann als Rückfall gekennzeichnet.
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
from typing import Any

from .providers import AgentReply, AgentRequest, Provider, ProviderError

IMAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]+@sha256:[a-f0-9]{64}")
SAFE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*")
URL = re.compile(r"http://[A-Za-z0-9_.-]+:[0-9]{1,5}/v1")
# Alles, was OpenCode nach außen führen könnte, ist aus.
QUIET_ENV = {
    "HOME": "/tmp",
    "OPENCODE_DISABLE_AUTOUPDATE": "1",
    "OPENCODE_DISABLE_MODELS_FETCH": "1",
    "OPENCODE_DISABLE_DEFAULT_PLUGINS": "1",
    "OPENCODE_DISABLE_LSP_DOWNLOAD": "1",
    "OPENCODE_DISABLE_CLAUDE_CODE": "1",
    "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
    "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
}


def validate_settings(settings: dict[str, Any]) -> None:
    if not isinstance(settings.get("enabled"), bool):
        raise ValueError("opencode.enabled muss true oder false sein")
    if not settings["enabled"]:
        return
    if not IMAGE.fullmatch(str(settings.get("image", ""))):
        raise ValueError("opencode.image braucht ein unveränderliches Image (…@sha256:…)")
    network = str(settings.get("network", ""))
    if not SAFE.fullmatch(network) or network in {"none", "host", "bridge", "default"}:
        raise ValueError("opencode.network muss ein eigenes internes Docker-Netz sein")
    if not URL.fullmatch(str(settings.get("gateway_url", ""))):
        raise ValueError("opencode.gateway_url muss http://<dienst>:<port>/v1 im internen Netz sein")


def opencode_config(gateway_url: str, alias: str) -> dict[str, Any]:
    """OpenCode-Konfiguration: nur FLOWGATE als Anbieter, nur der Alias des Profils, keine Werkzeuge."""
    return {
        "$schema": "https://opencode.ai/config.json",
        "autoupdate": False,
        "share": "disabled",
        "model": f"flowgate/{alias}",
        "provider": {"flowgate": {
            "npm": "@ai-sdk/openai-compatible", "name": "FLOWGATE",
            "options": {"baseURL": gateway_url, "apiKey": "{env:FLOWGATE_KEY}"},
            "models": {alias: {"name": alias}},
        }},
        "permission": {"edit": "deny", "bash": "deny", "webfetch": "deny"},
        "tools": {"write": False, "edit": False, "bash": False, "webfetch": False, "patch": False, "todowrite": False},
    }


def parse_events(output: str) -> tuple[str, int, int]:
    """Text der letzten Antwort und Tokenzahlen aus ``opencode run --format json``."""
    texts: dict[str, list[str]] = {}
    last_message = ""
    tokens_in = tokens_out = 0
    for line in output.splitlines():
        with contextlib.suppress(ValueError, AttributeError, TypeError):
            event = json.loads(line)
            part = event.get("part") or {}
            if event.get("type") == "text" and part.get("text"):
                last_message = str(part.get("messageID", ""))
                texts.setdefault(last_message, []).append(str(part["text"]))
            elif event.get("type") == "step_finish":
                tokens = part.get("tokens") or {}
                tokens_in += int(tokens.get("input", 0))
                tokens_out += int(tokens.get("output", 0))
    return "".join(texts.get(last_message, [])), tokens_in, tokens_out


class OpenCodeProvider:
    name = "opencode"

    def __init__(self, settings: dict[str, Any], keys: dict[str, str], fallback: Provider | None = None) -> None:
        validate_settings(settings)
        self.settings, self.keys, self.fallback = settings, keys, fallback
        self.owner = uuid.uuid4().hex

    def preflight(self) -> None:
        if not self.settings["enabled"]:
            raise ProviderError("OpenCode-Worker ist abgeschaltet (opencode.enabled=false)")
        _run(["docker", "image", "inspect", self.settings["image"]])
        network = _run(["docker", "network", "inspect", "--format", "{{.Internal}} {{.Driver}}",
                        self.settings["network"]]).strip()
        if network != "true bridge":
            raise ProviderError("OpenCode-Netz muss eine interne Docker-Bridge sein")

    def generate(self, request: AgentRequest) -> AgentReply:
        try:
            return self._generate(request)
        except ProviderError as exc:
            if self.fallback is None:
                raise
            reply = self.fallback.generate(request)
            return AgentReply(text=reply.text, provider=f"{reply.provider} (Rückfall: {exc})"[:120], model=reply.model,
                              output_tokens=reply.output_tokens, input_tokens=reply.input_tokens,
                              seconds=reply.seconds, first_token_seconds=reply.first_token_seconds)

    def _generate(self, request: AgentRequest) -> AgentReply:
        if not self.settings["enabled"]:
            raise ProviderError("OpenCode-Worker ist abgeschaltet")
        key = self.keys.get(request.agent.role)
        if not key:
            raise ProviderError(f"kein FLOWGATE-Schlüssel für Rolle {request.agent.role}")
        alias = request.agent.gateway_alias
        prompt = request.system + "\n\n" + request.user
        started = time.monotonic()
        code, output = self._docker(alias, key, prompt)
        if code:
            raise ProviderError(f"OpenCode endete mit Fehler ({code})")
        text, tokens_in, tokens_out = parse_events(output)
        if not text.strip():
            raise ProviderError("OpenCode lieferte keine Antwort")
        return AgentReply(text=text, provider=self.name, model=alias, output_tokens=tokens_out or len(text) // 4,
                          input_tokens=tokens_in or len(prompt) // 4, seconds=round(time.monotonic() - started, 2))

    def docker_args(self, name: str, alias: str) -> list[str]:
        cfg = self.settings
        uid, gid = os.getuid(), os.getgid()
        args = [
            "docker", "run", "--rm", "-i", "--name", name, "--label", f"flow-agents-opencode={self.owner}",
            "--pull", "never", "--read-only", "--init", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--user", f"{uid}:{gid}", "--pids-limit", str(cfg.get("pids", 256)),
            "--memory", str(cfg.get("memory", "2g")), "--memory-swap", str(cfg.get("memory", "2g")),
            "--cpus", str(cfg.get("cpus", 2)),
            "--tmpfs", f"/tmp:rw,nosuid,nodev,size={cfg.get('scratch', '512m')},uid={uid},gid={gid},mode=0700",
            "--tmpfs", f"/work:rw,nosuid,nodev,size=16m,uid={uid},gid={gid},mode=0700",
            "--network", str(cfg["network"]), "--workdir", "/work", "--log-driver", "none",
            "--env", "FLOWGATE_KEY", "--env", "FLOW_MODEL=" + alias, "--env", "OPENCODE_CONFIG_CONTENT",
        ]
        for key, value in QUIET_ENV.items():
            args += ["--env", f"{key}={value}"]
        return args

    def _docker(self, alias: str, key: str, prompt: str) -> tuple[int, str]:
        name = f"flow-agents-opencode-{uuid.uuid4().hex[:12]}"
        args = [*self.docker_args(name, alias), self.settings["image"]]
        env = {**os.environ, "FLOWGATE_KEY": key,
               "OPENCODE_CONFIG_CONTENT": json.dumps(opencode_config(str(self.settings["gateway_url"]), alias))}
        timeout = int(self.settings.get("timeout_seconds", 1800))
        maximum = int(self.settings.get("output_bytes", 4_000_000))
        try:
            with tempfile.TemporaryFile() as stdin, tempfile.TemporaryFile() as output:
                stdin.write(prompt.encode())
                stdin.seek(0)
                proc = subprocess.Popen(args, stdin=stdin, stdout=output, stderr=subprocess.DEVNULL, env=env,
                                        start_new_session=True)
                try:
                    deadline = time.monotonic() + timeout
                    while proc.poll() is None:
                        if time.monotonic() >= deadline or os.fstat(output.fileno()).st_size > maximum:
                            raise ProviderError("OpenCode: Laufzeit- oder Ausgabelimit überschritten")
                        time.sleep(0.2)
                    output.seek(0)
                    return proc.returncode, output.read(maximum).decode(errors="replace")
                finally:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
        except OSError as exc:
            raise ProviderError(f"OpenCode: Docker nicht verfügbar ({type(exc).__name__})") from None
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=15, check=False)


def _run(args: list[str]) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProviderError(f"docker: {type(exc).__name__}") from None
    if result.returncode:
        raise ProviderError(f"docker {args[1]}: fehlgeschlagen")
    return result.stdout
