"""Vertrauenswürdiger Einstiegspunkt im Worker-Image (aus Trading_Ai dev_orchestrator_worker.py).

Kopiert ausschließlich die Anmeldedatei des Anbieters in ein frisches Home im tmpfs, prüft die
Abo-Anmeldung, führt die CLI mit dem Prompt auf stdin aus und gibt eine begrenzte JSON-Hülle aus.
"""

from __future__ import annotations

import json
import os
import signal
import stat
import subprocess
import sys
from contextlib import suppress
from pathlib import Path

CODEX_AGENT_ROOT = Path("/run/codex-agent")


def read_file(root: Path, name: str, limit: int) -> bytes:
    path = root
    for part in name.split("/")[:-1]:
        path /= part
        if not stat.S_ISDIR(path.lstat().st_mode):
            raise ValueError("unsafe parent")
    path /= name.split("/")[-1]
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("unsafe credential file")
        value = handle.read(limit + 1)
        if len(value) > limit:
            raise ValueError("oversized credential file")
        return value


def prepare_home(provider: str, auth: Path, home: Path) -> dict[str, str]:
    credential = {"codex": ".codex/auth.json", "claude": ".claude/.credentials.json"}[provider]
    value = read_file(auth, credential, 1024 * 1024)
    target = home / credential
    target.parent.mkdir(parents=True, mode=0o700)
    with target.open("xb") as handle:
        os.fchmod(handle.fileno(), 0o600)
        handle.write(value)
    env = {**os.environ, "HOME": str(home), "CODEX_HOME": str(home / ".codex"), "CLAUDE_CONFIG_DIR": str(home / ".claude")}
    return env


def subscription_confirmed(provider: str, env: dict[str, str]) -> bool:
    args = ["codex", "login", "status"] if provider == "codex" else ["claude", "auth", "status"]
    result = subprocess.run(args, env=env, capture_output=True, text=True, check=False)
    if result.returncode:
        return False
    if provider == "codex":
        return "logged in using chatgpt" in (result.stdout + result.stderr).lower()
    status = json.loads(result.stdout)
    return status.get("loggedIn") is True and status.get("authMethod") == "claude.ai"


def main() -> int:
    provider, maximum = sys.argv[1], int(sys.argv[2])
    home = CODEX_AGENT_ROOT / "home" if provider == "codex" else Path("/tmp/agent-home")
    try:
        home.mkdir(mode=0o700)
        env = prepare_home(provider, Path("/auth"), home)
        if not subscription_confirmed(provider, env):
            return 1
    except (OSError, ValueError):
        return 1
    prompt = sys.stdin.buffer.read(4_000_000)
    logfile = Path("/tmp/agent-events")
    with logfile.open("wb") as output:
        proc = subprocess.Popen(sys.argv[3:], cwd="/work", env=env, stdin=subprocess.PIPE, stdout=output,
                                stderr=output, start_new_session=True)
        try:
            proc.communicate(prompt)
            code = proc.returncode
        finally:
            with suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
    with logfile.open("rb") as output:
        events = output.read(maximum + 1)
    if len(events) > maximum:
        return 1
    print(json.dumps({"code": code, "events": events.decode(errors="replace")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
