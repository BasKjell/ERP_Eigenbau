"""Übernahme abgenommener Kandidaten ins Repository und Vorschau für die Fachabnahme.

Beides sind deterministische Dienste außerhalb der Agentenlaufzeit (KI-EK Teil 03):

- ``Adoption`` erzeugt nach der Fachabnahme (G4) aus genau dem abgenommenen Digest einen lokalen
  Branch ``agent/<Auftrag>-…`` mit einem Commit. Der Checkout der Person bleibt unberührt
  (eigener Git-Worktree im Zustandsordner). Push ist optional, Merge bleibt beim Menschen.
- ``Preview`` startet den Kandidaten vor G4 als zweite Plattform-API (nur Loopback), damit der
  Key User die Änderung in der Oberfläche prüft und nicht nur im Diff.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

from .sandbox import SandboxError, validate_path


def _git(repo: Path, *args: str, timeout: int = 120) -> str:
    result = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", *args], cwd=repo, capture_output=True,
                            text=True, timeout=timeout, check=False)
    if result.returncode:
        command = next((arg for arg in args if not arg.startswith("-") and "=" not in arg), args[0])
        detail = (result.stderr.strip() or result.stdout.strip())[:200]
        raise SandboxError(f"git {command} fehlgeschlagen: {detail}")
    return result.stdout.strip()


def slug(text: str, limit: int = 40) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")[:limit].strip("-") or "aenderung"


class Adoption:
    def __init__(self, repo: Path, state_dir: Path, *, allowed_prefixes: tuple[str, ...], push: bool = False,
                 remote: str = "origin") -> None:
        self.repo, self.state_dir, self.allowed_prefixes = repo, state_dir, allowed_prefixes
        self.push, self.remote = push, remote

    def adopt(self, run: dict[str, Any], refs: dict[str, Any], *, approved_by: str, digest: str) -> dict[str, Any]:
        base, files, workspace = str(refs.get("base", "")), dict(refs.get("files") or {}), Path(str(refs.get("workspace", "")))
        if refs.get("digest") != digest:
            raise SandboxError("Übernahme nur für den abgenommenen Digest")
        if not re.fullmatch(r"[0-9a-f]{40}", base) or not files or not workspace.is_dir():
            raise SandboxError("Kandidat ist nicht mehr vollständig vorhanden")
        if not workspace.resolve().is_relative_to((self.state_dir / "sandboxes").resolve()):
            raise SandboxError("Arbeitsbereich liegt nicht in der Sandbox")
        contents: dict[str, bytes] = {}
        for path, expected in files.items():
            validate_path(path, self.allowed_prefixes)
            data = (workspace / path).read_bytes()
            if hashlib.sha256(data).hexdigest() != expected:
                raise SandboxError(f"{path} weicht vom geprüften Stand ab")
            contents[path] = data
        branch = f"agent/{run['auftrag_id']}-{slug(run['title'])}"
        if _git(self.repo, "branch", "--list", branch):
            branch = f"{branch}-{run['id'][-6:].lower()}"
        tree = Path(tempfile.mkdtemp(prefix="adopt-", dir=self.state_dir))
        try:
            _git(self.repo, "worktree", "add", "--detach", str(tree / "wt"), base)
            worktree = tree / "wt"
            for path, data in contents.items():
                target = worktree / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            _git(worktree, "add", "--", *contents)
            staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=worktree, capture_output=True,
                                    timeout=60, check=False)
            if staged.returncode == 0:
                raise SandboxError("abgenommener Stand entspricht dem Ausgangsstand – nichts zu übernehmen")
            message = (f"feat({run['auftrag']['project'].lower()}): {run['title']}\n\n"
                       f"Fachauftrag {run['auftrag_id']} ({run['change_class']}), Lauf {run['id']}.\n"
                       f"Fachabnahme G4 durch {approved_by} für {digest}.\n"
                       f"Erstellt von FLOWAGENTS (lokale Rollen über FLOWGATE); Merge durch einen Menschen.\n\n"
                       f"Agent: flowagents / {run['id']}")
            _git(worktree, "-c", "user.name=FLOWAGENTS", "-c", "user.email=flow-agents@localhost.invalid",
                 "commit", "-q", "-m", message)
            commit = _git(worktree, "rev-parse", "HEAD")
            _git(self.repo, "branch", branch, commit)
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(tree / "wt")], cwd=self.repo,
                           capture_output=True, check=False)
            shutil.rmtree(tree, ignore_errors=True)
        pushed = False
        if self.push:
            _git(self.repo, "push", self.remote, f"refs/heads/{branch}:refs/heads/{branch}", timeout=180)
            pushed = True
        return {"branch": branch, "commit": commit, "base": base, "files": sorted(contents), "pushed": pushed}


class Preview:
    """Kandidat als zweite Plattform-API auf 127.0.0.1:<port> (Demo-Modus, read-only Code)."""

    NAME = "flow-agents-preview"

    def __init__(self, *, image: str, port: int, network: str, env: dict[str, str]) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/@-]+", image) or not 1024 < port < 65536:
            raise SandboxError("ungültige Vorschau-Konfiguration")
        self.image, self.port, self.network, self.env = image, port, network, env

    def start(self, workspace: Path) -> str:
        app = workspace / "services" / "platform_api" / "app"
        if not app.is_dir():
            raise SandboxError("Kandidat enthält keine Plattform-API")
        self.stop()
        uid, gid = os.getuid(), os.getgid()
        args = ["docker", "run", "-d", "--name", self.NAME, "--label", "flow-agents-preview=1", "--pull", "never",
                "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", f"{uid}:{gid}",
                "--tmpfs", f"/data:rw,size=200m,uid={uid},gid={gid}", "--tmpfs", f"/tmp:rw,size=200m,uid={uid},gid={gid}",
                "--memory", "1g", "--pids-limit", "256", "-p", f"127.0.0.1:{self.port}:8080",
                "--network", self.network, "--env", "AUTH_MODE=demo", "--env", "HOME=/tmp",
                "--mount", f"type=bind,source={app},target=/app/app,readonly",
                "--mount", f"type=bind,source={workspace / 'agents'},target=/app/agents,readonly"]
        for key, value in self.env.items():
            args += ["--env", f"{key}={value}"]
        result = subprocess.run([*args, self.image], capture_output=True, text=True, timeout=60, check=False)
        if result.returncode:
            raise SandboxError(f"Vorschau startet nicht: {result.stderr.strip()[:200]}")
        return f"http://localhost:{self.port}"

    def stop(self) -> None:
        subprocess.run(["docker", "rm", "-f", self.NAME], capture_output=True, timeout=30, check=False)
