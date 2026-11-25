"""Isolierter Arbeitsbereich für den Entwicklungs-Agenten und die Integrationsprüfung.

- Grundlage ist ein exakter Git-Commit (``git archive``), nie der veränderliche Checkout.
- Der Agent darf nur freigegebene, nicht geschützte Textdateien ändern.
- Der Änderungsstand erhält einen Digest; Review, Gate und Abnahme binden sich daran.
- Prüfungen laufen in einem Container ohne Netzwerk, read-only und ohne Zugangsdaten.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

PROTECTED = (
    "agents/",
    ".github/",
    "AGENTS.md",
    "CLAUDE.md",
    "compose.yaml",
    "compose.ci.yaml",
    "Makefile",
    "deployment/",
    "services/agent_orchestrator/",
    "services/platform_api/app/auth.py",
    "services/platform_api/app/rm_adapter.py",
    "services/platform_api/app/agent_policy.py",
    ".env",
)
SAFE_PATH = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]{0,200}")
MAX_FILE = 300_000


class SandboxError(RuntimeError):
    """Pfad, Inhalt oder Prüfung verletzt die Sandbox-Grenzen."""


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    summary: str
    seconds: float
    command: str
    output: str = ""  # vollständige Ausgabe (gekürzt auf 200k) für die Zuordnung von Testergebnissen je Fall


class CheckRunner(Protocol):
    def run(self, workspace: Path) -> CheckResult: ...


def validate_path(path: str, allowed_prefixes: tuple[str, ...]) -> str:
    pure = PurePosixPath(path)
    if (
        not SAFE_PATH.fullmatch(path)
        or pure.is_absolute()
        or ".." in pure.parts
        or any(part.startswith(".env") for part in pure.parts)
    ):
        raise SandboxError(f"unzulässiger Pfad {path!r}")
    if any(path == item.rstrip("/") or path.startswith(item) for item in PROTECTED):
        raise SandboxError(f"geschützter Pfad {path} (Änderung nur im autorisierten Prozess)")
    if not any(path.startswith(prefix) for prefix in allowed_prefixes):
        raise SandboxError(f"Pfad {path} liegt außerhalb der freigegebenen Bereiche")
    return path


def _git(repo: Path, *args: str, timeout: int = 60) -> str:
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        raise SandboxError(f"git {args[0]} fehlgeschlagen")
    return result.stdout


class Sandbox:
    def __init__(
        self,
        repo: Path,
        state_dir: Path,
        *,
        base_ref: str,
        allowed_prefixes: tuple[str, ...],
        checker: CheckRunner,
    ) -> None:
        self.repo = repo
        self.root = state_dir / "sandboxes"
        self.base_ref = base_ref
        self.allowed_prefixes = allowed_prefixes
        self.checker = checker

    def base_commit(self) -> str:
        sha = _git(self.repo, "rev-parse", "--verify", f"{self.base_ref}^{{commit}}").strip()
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise SandboxError("Basis-Commit nicht auflösbar")
        return sha

    def originals(self, base: str, paths: list[str]) -> dict[str, str | None]:
        files: dict[str, str | None] = {}
        for path in paths:
            validate_path(path, self.allowed_prefixes)
            result = subprocess.run(
                ["git", "show", f"{base}:{path}"], cwd=self.repo, capture_output=True, timeout=30, check=False
            )
            if result.returncode:
                files[path] = None
                continue
            if len(result.stdout) > MAX_FILE or b"\0" in result.stdout:
                raise SandboxError(f"{path} ist zu groß oder binär")
            files[path] = result.stdout.decode("utf-8")
        return files

    def apply(self, run_id: str, base: str, allowed: list[str], changes: dict[str, str]) -> dict[str, object]:
        """Exportiert *base*, schreibt die Änderungen und liefert Digest und Dateiliste."""
        if not changes:
            raise SandboxError("keine Dateiänderung geliefert")
        unexpected = set(changes) - set(allowed)
        if unexpected:
            raise SandboxError(f"Änderung außerhalb der freigegebenen Pfade: {sorted(unexpected)}")
        for path, content in changes.items():
            validate_path(path, self.allowed_prefixes)
            if "\0" in content or len(content.encode()) > MAX_FILE:
                raise SandboxError(f"{path}: binärer oder zu großer Inhalt")
        workspace = self.root / run_id / f"{int(time.time() * 1000)}"
        source = workspace / "source"
        source.mkdir(parents=True, mode=0o700)
        self._export(base, source)
        changed = {}
        for path, content in sorted(changes.items()):
            target = source / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink():
                raise SandboxError(f"{path} ist eine Verknüpfung")
            target.write_text(content, encoding="utf-8")
            changed[path] = hashlib.sha256(content.encode()).hexdigest()
        digest = hashlib.sha256(
            (base + "\n" + "\n".join(f"{path}:{value}" for path, value in sorted(changed.items()))).encode()
        ).hexdigest()
        return {"base": base, "files": changed, "digest": f"sha256:{digest}", "workspace": str(source)}

    def check(self, workspace: str) -> CheckResult:
        path = Path(workspace).resolve()
        if not path.is_relative_to(self.root.resolve()) or not path.is_dir():
            raise SandboxError("Arbeitsbereich liegt nicht in der Sandbox")
        return self.checker.run(path)

    def _export(self, base: str, target: Path) -> None:
        with tempfile.TemporaryFile() as archive:
            subprocess.run(["git", "archive", base], cwd=self.repo, stdout=archive, check=True, timeout=120)
            archive.seek(0)
            with tarfile.open(fileobj=archive) as tar:
                for member in tar:
                    parts = PurePosixPath(member.name).parts
                    if any(part.startswith(".env") and part != ".env.example" for part in parts):
                        continue  # Zugangsdaten gelangen nie in die Sandbox
                    if not (member.isfile() or member.isdir()):
                        continue
                    tar.extract(member, target, filter="data")


class DockerCheck:
    """Pflichtprüfungen in einem Container ohne Netzwerk und ohne Zugangsdaten."""

    def __init__(self, image: str, command: str, *, timeout: int = 900) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/@-]+", image):
            raise SandboxError("ungültiges Prüfimage")
        self.image, self.command, self.timeout = image, command, timeout

    def run(self, workspace: Path) -> CheckResult:
        started = time.monotonic()
        args = [
            "docker", "run", "--rm", "--pull", "never", "--network", "none", "--read-only",
            "--tmpfs", "/tmp:rw,exec,size=1500m", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", "256", "--memory", "3g", "--cpus", "2", "--user", f"{os.getuid()}:{os.getgid()}",
            "--env", "HOME=/tmp", "--log-driver", "none",
            "--mount", f"type=bind,source={workspace},target=/work,readonly",
            "--entrypoint", "/bin/sh", self.image, "-ec", f"cp -R /work /tmp/w && cd /tmp/w && {self.command}",
        ]
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=self.timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return CheckResult(False, f"Prüfcontainer nicht ausführbar: {type(exc).__name__}",
                               time.monotonic() - started, self.command)
        output = (result.stdout + result.stderr).strip()
        tail = "\n".join(output.splitlines()[-12:])
        return CheckResult(result.returncode == 0, tail[-3000:], time.monotonic() - started, self.command,
                           output[-200_000:])


class LocalCheck:
    """Nur für Tests: führt einen festen Befehl lokal aus (nie für Modellcode im Betrieb)."""

    def __init__(self, command: list[str]) -> None:
        self.command = command

    def run(self, workspace: Path) -> CheckResult:
        started = time.monotonic()
        result = subprocess.run(self.command, cwd=workspace, capture_output=True, text=True, timeout=300, check=False)
        output = (result.stdout + result.stderr).strip()
        tail = "\n".join(output.splitlines()[-12:])
        return CheckResult(result.returncode == 0, tail, time.monotonic() - started, " ".join(self.command),
                           output[-200_000:])


def cleanup(state_dir: Path, run_id: str) -> None:
    shutil.rmtree(state_dir / "sandboxes" / run_id, ignore_errors=True)
