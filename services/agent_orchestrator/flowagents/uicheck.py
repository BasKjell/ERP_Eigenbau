"""Klickprüfung: Agenten beschreiben Klickpfade, der Orchestrator führt sie im Browser aus.

Grundsatz 2 des Sicherheitskonzepts bleibt gewahrt: Das Modell bedient keinen Browser. Der
Akzeptanztest-Agent liefert je Testfall optional einen Klickpfad (``ui``) als Daten in einer kleinen,
geprüften Sprache. Erst an G4 führt der Orchestrator diese Pfade mit einem headless Chromium gegen
die Vorschau des Kandidaten aus – im Demo-Modus, mit Testdaten, in einem internen Docker-Netz ohne
Internet. Ergebnis und Bildschirmfotos gehen als Nachweis an die Fachabnahme.

Sprache (je Schritt ein Objekt, ``do`` ist Pflicht):

- ``{"do": "goto", "path": "/dms"}`` – nur Pfade der Vorschau, keine fremden Adressen
- ``{"do": "click", "text": "Ablegen"}`` oder ``{"do": "click", "role": "button", "name": "Ablegen"}``
- ``{"do": "fill", "label": "Titel", "value": "Prüfbericht"}``
- ``{"do": "select", "label": "Dokumenttyp", "value": "3D-Modell STL"}``
- ``{"do": "upload", "label": "Datei", "fixture": "beispiel.stl"}`` – nur eingebaute Testdateien
- ``{"do": "expect_text", "text": "gespeichert"}`` / ``{"do": "expect_visible", "label": "Datei"}``
- ``{"do": "screenshot", "name": "nach-upload"}``
"""

from __future__ import annotations

import base64
import contextlib
import json
import re
import subprocess
import time
from typing import Any

ACTIONS = {"goto", "click", "fill", "select", "upload", "expect_text", "expect_visible", "screenshot"}
FIXTURES = {"beispiel.pdf", "beispiel.stl", "beispiel.png", "beispiel.txt"}
ROLES = {"button", "link", "tab", "checkbox", "radio", "menuitem", "option", "textbox", "combobox", "heading"}
TARGETS = ("text", "label", "role", "name", "placeholder")
MAX_SCENARIOS, MAX_STEPS, MAX_TEXT = 8, 25, 300
PATH = re.compile(r"/[A-Za-z0-9/_\-.?=&%]*")
NETWORK = "flow-agents-ui"


class UiCheckError(ValueError):
    """Ungültiger Klickpfad oder nicht ausführbare Klickprüfung."""


def validate_steps(steps: Any, label: str = "ui") -> list[dict[str, str]]:
    """Prüft einen Klickpfad streng; liefert die normalisierten Schritte."""
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        raise UiCheckError(f"{label}: 1 bis {MAX_STEPS} Schritte")
    clean = []
    for index, step in enumerate(steps, 1):
        where = f"{label}[{index}]"
        if not isinstance(step, dict) or step.get("do") not in ACTIONS:
            raise UiCheckError(f"{where}: do muss einer von {sorted(ACTIONS)} sein")
        unknown = set(step) - {"do", "path", "value", "fixture", *TARGETS}
        if unknown:
            raise UiCheckError(f"{where}: unbekannte Felder {sorted(unknown)}")
        item = {key: str(value) for key, value in step.items()}
        if any(len(value) > MAX_TEXT for value in item.values()):
            raise UiCheckError(f"{where}: Texte höchstens {MAX_TEXT} Zeichen")
        action = item["do"]
        if action == "goto":
            if not PATH.fullmatch(item.get("path", "")) or ".." in item["path"] or item["path"].startswith("//"):
                raise UiCheckError(f"{where}: goto braucht einen Pfad der Vorschau wie /dms")
        elif action == "screenshot":
            item["name"] = re.sub(r"[^A-Za-z0-9_-]", "-", item.get("name", f"bild-{index}"))[:40]
        else:
            if not any(item.get(key) for key in ("text", "label", "role", "placeholder")):
                raise UiCheckError(f"{where}: Ziel fehlt (text, label, role+name oder placeholder)")
            if item.get("role") and (item["role"] not in ROLES or not item.get("name")):
                raise UiCheckError(f"{where}: role muss einer von {sorted(ROLES)} sein und braucht name")
            if action in {"fill", "select"} and "value" not in item:
                raise UiCheckError(f"{where}: {action} braucht value")
            if action == "upload" and item.get("fixture") not in FIXTURES:
                raise UiCheckError(f"{where}: upload nur mit {sorted(FIXTURES)}")
        clean.append(item)
    return clean


def scenarios_from(acceptance: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Klickpfade aus dem Artefakt der Akzeptanztests (ungültige wurden schon am Vertrag abgewiesen)."""
    scenarios = []
    for item in ((acceptance or {}).get("content") or {}).get("items", []):
        if item.get("ui"):
            scenarios.append({"key": str(item.get("key", "")), "title": str(item.get("title", "")),
                              "steps": validate_steps(item["ui"], str(item.get("key", "ui")))})
    return scenarios[:MAX_SCENARIOS]


class UiRunner:
    """Führt Klickpfade in einem isolierten Playwright-Container gegen die Vorschau aus."""

    def __init__(self, *, image: str, target: str = "http://flow-agents-preview:8080",
                 timeout_seconds: int = 240, network: str = NETWORK) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/@-]+", image):
            raise UiCheckError("ungültiges Image für die Klickprüfung")
        self.image, self.target, self.timeout, self.network = image, target, timeout_seconds, network

    def docker_args(self) -> list[str]:
        return ["docker", "run", "--rm", "-i", "--pull", "never", "--read-only", "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges", "--network", self.network, "--memory", "1500m",
                "--pids-limit", "512", "--shm-size", "256m", "--tmpfs", "/tmp:rw,size=300m",
                "--env", "HOME=/tmp", "--log-driver", "none", "--label", "flow-agents-ui=1", self.image]

    def prepare_network(self, preview_container: str) -> None:
        """Internes Netz ohne Internet; nur Vorschau und Prüfbrowser hängen daran."""
        inspect = subprocess.run(["docker", "network", "inspect", "--format", "{{.Internal}}", self.network],
                                 capture_output=True, text=True, timeout=30, check=False)
        if inspect.returncode:
            subprocess.run(["docker", "network", "create", "--internal", self.network],
                           capture_output=True, text=True, timeout=30, check=True)
        elif inspect.stdout.strip() != "true":
            raise UiCheckError(f"Netz {self.network} muss intern sein")
        subprocess.run(["docker", "network", "connect", self.network, preview_container],
                       capture_output=True, text=True, timeout=30, check=False)

    def run(self, scenarios: list[dict[str, Any]]) -> dict[str, Any]:
        payload = json.dumps({"base_url": self.target, "scenarios": scenarios})
        started = time.monotonic()
        try:
            result = subprocess.run(self.docker_args(), input=payload, capture_output=True, text=True,
                                    timeout=self.timeout, check=False)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(OSError, subprocess.SubprocessError):
                subprocess.run(["docker", "rm", "-f", *_running()], capture_output=True, timeout=30, check=False)
            raise UiCheckError("Klickprüfung hat das Zeitlimit überschritten") from None
        if result.returncode:
            raise UiCheckError(f"Prüfbrowser fehlgeschlagen: {result.stderr.strip()[-300:]}")
        try:
            report = json.loads(result.stdout)
        except ValueError:
            raise UiCheckError("Prüfbrowser lieferte kein Ergebnis") from None
        return summarize(report, time.monotonic() - started)


def summarize(report: dict[str, Any], seconds: float = 0.0) -> dict[str, Any]:
    """Begrenzt Größe und Inhalt des Berichts (Texte gekürzt, höchstens 6 Bilder à 400 KB)."""
    scenarios, images = [], 0
    for scenario in report.get("scenarios", [])[:MAX_SCENARIOS]:
        shots = []
        for shot in scenario.get("screenshots", []):
            data = str(shot.get("data", ""))
            if images < 6 and data and len(data) <= 550_000:
                with contextlib.suppress(ValueError):
                    base64.b64decode(data, validate=True)
                    shots.append({"name": str(shot.get("name", ""))[:40], "data": data})
                    images += 1
        steps = [{"do": str(s.get("do", "")), "ok": bool(s.get("ok")), "note": str(s.get("note", ""))[:200]}
                 for s in scenario.get("steps", [])[:MAX_STEPS]]
        scenarios.append({"key": str(scenario.get("key", ""))[:40], "title": str(scenario.get("title", ""))[:160],
                          "passed": bool(scenario.get("passed")) and all(s["ok"] for s in steps),
                          "steps": steps, "screenshots": shots})
    passed = sum(1 for s in scenarios if s["passed"])
    return {"passed": passed, "total": len(scenarios), "seconds": round(seconds, 1), "scenarios": scenarios}


def _running() -> list[str]:
    result = subprocess.run(["docker", "ps", "-q", "--filter", "label=flow-agents-ui=1"],
                            capture_output=True, text=True, timeout=30, check=False)
    return result.stdout.split() or ["flow-agents-ui-none"]
