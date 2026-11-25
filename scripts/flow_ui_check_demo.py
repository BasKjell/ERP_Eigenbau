#!/usr/bin/env python3
"""Vorführung der Klickprüfung mit lokaler KI (FLOWAGENTS, Doku: docs/agents/klickpruefung.md).

1. Der Akzeptanztest-Agent (Rolle 7, Modellprofil pruefer über FLOWGATE, lokal) schreibt zu einer
   Anforderung Testfälle mit Klickpfad – genau mit dem Prompt-Baustein, den der Orchestrator nutzt.
2. Der Orchestrator-Code prüft die Klickpfade (feste Sprache, keine Selektoren, keine fremden Adressen).
3. Der Prüfbrowser (Playwright/Chromium im internen Netz ohne Internet) führt sie gegen die Vorschau aus.
4. Ergebnis und Bildschirmfotos landen in docs/agents/bilder/klickpruefung/.

Voraussetzungen: FLOWGATE läuft, Image flow-agents-ui-runner:1, Vorschau-Container flow-agents-preview
(z. B. über `python scripts/flow_ui_check_demo.py --start-preview`). Nur lokale Demo-Schlüssel.

    PYTHONPATH=services/agent_orchestrator .venv/bin/python scripts/flow_ui_check_demo.py --start-preview
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "agent_orchestrator"))

from flowagents import registry as registry_module  # noqa: E402
from flowagents.adoption import Preview  # noqa: E402
from flowagents.contract import extract_json  # noqa: E402
from flowagents.engine import UI_HINT  # noqa: E402
from flowagents.providers import AgentRequest, GatewayProvider  # noqa: E402
from flowagents.uicheck import UiCheckError, UiRunner, validate_steps  # noqa: E402

OUT = ROOT / "docs" / "agents" / "bilder" / "klickpruefung"
DEMO_KEY = "agw-demo-akzeptanztest-change-before-network-use"

REQUIREMENT = """Anforderung R1 (FLOWSPACE, Arbeitsplatz buchen):
Eine Person wählt auf der Seite /desksharing den Standort und prüft die Verfügbarkeit.
- AC-1: Nach Auswahl „Hamburg · Projektbüro“ im Feld „Standort“ und Klick auf „Verfügbarkeit prüfen“
  zeigt die Seite den Standort Hamburg mit seinen freien Plätzen.
- AC-2: Das Feld „Zeitfenster“ bietet „Ganztägig“, „Vormittag“ und „Nachmittag“ an.
Sichtbare Beschriftungen der Seite: Überschrift „Dein Platz.“, Felder „Datum“, „Standort“
(Optionen „Berlin · Werk & Büro“, „Hamburg · Projektbüro“), „Zeitfenster“, Knopf „Verfügbarkeit prüfen“.
Testdaten: synthetisch, Demo-Modus, keine Buchung anlegen."""


def ask_local_agent() -> list[dict]:
    registry = registry_module.load(ROOT / "agents")
    agent = registry.agents["akzeptanztest"]
    system = (ROOT / "agents" / "prompts" / "07-akzeptanztest.md").read_text(encoding="utf-8")
    system += (
        "\n\n" + UI_HINT + "\n\nAntworte nur mit JSON: "
        '{"status": "fertig", "summary": "…", "artifacts": [{"type": "testfall", "key": "AT-1", "title": "…", '
        '"criterion": "R1/AC-1", "preconditions": "…", "steps": [{"action": "…", "expected": "…"}], '
        '"negative": false, "ui": [ … ]}]}. Jeder Klickpfad endet mit einem screenshot.'
    )
    key = os.environ.get("FLOW_AGENT_GATEWAY_KEY_AKZEPTANZTEST", DEMO_KEY)
    gateway = GatewayProvider(os.environ.get("FLOWGATE_URL", "http://127.0.0.1:4000"), {"akzeptanztest": key})
    user, attempts = REQUIREMENT, []
    for attempt in range(1, 4):
        reply = gateway.generate(AgentRequest("DEMO-UI", "akzeptanztests", agent, system, user, 4096))
        print(f"Versuch {attempt}: {reply.provider}/{reply.model}, {reply.output_tokens} Token, {reply.seconds} s")
        try:
            result = extract_json(reply.text)
            scenarios = [{"key": item.get("key", ""), "title": item.get("title", ""),
                          "steps": validate_steps(item["ui"], item.get("key", "ui"))}
                         for item in result.get("artifacts", []) if item.get("ui")]
        except (ValueError, UiCheckError) as exc:
            # Wie im Orchestrator: Vertragsfehler gehen als Rückmeldung an denselben Agenten zurück.
            attempts.append({"attempt": attempt, "error": str(exc)})
            print(f"  zurückgewiesen: {exc}")
            user = f"{REQUIREMENT}\n\nDein letzter Entwurf wurde zurückgewiesen: {exc}. Liefere alle Testfälle neu."
            continue
        meta = {"model": f"{reply.provider}/{reply.model}", "attempts": attempts, "artifacts": result.get("artifacts", [])}
        return [meta, *scenarios]
    raise SystemExit("Der Agent hat keinen gültigen Klickpfad geliefert.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-preview", action="store_true", help="Vorschau aus dem aktuellen Arbeitsstand starten")
    parser.add_argument("--replay", action="store_true",
                        help="die zuletzt vom Agenten erzeugten Klickpfade (ergebnis.json) erneut ausführen")
    args = parser.parse_args()
    if args.start_preview:
        Preview(image="erp-eigenbau-platform-api:latest", port=8098, network="erp-eigenbau_platform",
                env={"DEMO_DATA_FILE": "/data/scenario.json", "AGENT_REGISTRY_DIR": "/app/agents"}).start(ROOT)
    if args.replay:
        previous = json.loads((OUT / "ergebnis.json").read_text(encoding="utf-8"))
        meta = {key: previous[key] for key in ("model", "attempts", "artifacts") if key in previous}
        scenarios = [{**s, "steps": validate_steps(s["steps"], s["key"])} for s in previous["scenarios_run"]]
    else:
        meta, *scenarios = ask_local_agent()
    if not scenarios:
        print("Der Agent hat keinen Klickpfad geliefert.")
        return 1
    runner = UiRunner(image="flow-agents-ui-runner:1")
    created = runner.prepare_network(Preview.NAME)
    try:
        report = runner.run(scenarios)
    finally:
        if created:  # nur ein von diesem Lauf angelegtes Netz wieder entfernen
            runner.remove_network(Preview.NAME)
    OUT.mkdir(parents=True, exist_ok=True)
    for scenario in report["scenarios"]:
        for shot in scenario["screenshots"]:
            (OUT / f"{scenario['key']}-{shot['name']}.png").write_bytes(base64.b64decode(shot["data"]))
            shot["data"] = f"{scenario['key']}-{shot['name']}.png"
    (OUT / "ergebnis.json").write_text(json.dumps({**meta, "scenarios_run": scenarios, "report": report},
                                                  ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Klickprüfung: {report['passed']} von {report['total']} bestanden in {report['seconds']} s → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
