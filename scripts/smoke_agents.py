"""Smoke-Test der laufenden FLOWAGENTS-Kette (make agents-smoke).

Prüft ohne Modellaufruf mit Wirkung:
1. Orchestrator antwortet und ist mit der Plattform-API verbunden (Pull-Abgleich).
2. Plattform-API antwortet; Abgleich-Endpunkte lehnen fehlende Tokens ab.
3. FLOWGATE: Rollenschlüssel ohne fremdes Modell (403), ohne Schlüssel (401).
4. RM-Adapter lehnt Aufrufe ohne Agenten-Token ab (401).
5. Prüfimage für die Integrationsprüfung ist vorhanden.

Exit-Code 0 nur, wenn alle Prüfungen bestehen. Nur Loopback-Adressen.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

ORCHESTRATOR = "http://127.0.0.1:8095"
PLATFORM = os.getenv("PLATFORM_URL", "http://127.0.0.1:8088")
GATEWAY = "http://127.0.0.1:4000"
DEMO_KEY = "agw-demo-planung-change-before-network-use"


def request(url: str, *, method: str = "GET", body: dict | None = None, headers: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except ValueError:
            return exc.code, {}
    except (urllib.error.URLError, OSError) as exc:
        return 0, {"error": type(exc).__name__}


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    status, health = request(f"{ORCHESTRATOR}/health")
    results.append(("Orchestrator antwortet", status == 200, str(health.get("control", health))))
    sync = health.get("platform_sync", {}) if status == 200 else {}
    results.append(("Orchestrator mit FLOWPORTAL verbunden", bool(sync.get("connected")), sync.get("error", "")))

    status, _ = request(f"{PLATFORM}/health")
    results.append(("Plattform-API antwortet", status == 200, str(status)))
    status, _ = request(f"{PLATFORM}/api/agents/sync/actions")
    results.append(("Abgleich ohne Token abgelehnt", status == 401, str(status)))
    status, _ = request(f"{PLATFORM}/api/rm/v1/drafts", method="POST", body={})
    results.append(("RM-Adapter ohne Agenten-Token abgelehnt", status == 401, str(status)))

    key = os.getenv("FLOW_AGENT_GATEWAY_KEY_PLANUNG", DEMO_KEY)
    tiny = {"model": "flow-coder", "max_tokens": 1, "messages": [{"role": "user", "content": "x"}]}
    status, _ = request(f"{GATEWAY}/v1/chat/completions", method="POST", body=tiny,
                        headers={"Authorization": f"Bearer {key}"})
    results.append(("FLOWGATE: fremdes Modell für Rolle gesperrt (403)", status == 403, str(status)))
    status, _ = request(f"{GATEWAY}/v1/chat/completions", method="POST", body=tiny)
    results.append(("FLOWGATE: ohne Schlüssel gesperrt (401)", status == 401, str(status)))

    image = subprocess.run(["docker", "image", "inspect", "flow-agents-sandbox:1"], capture_output=True, check=False)
    results.append(("Prüfimage flow-agents-sandbox:1 vorhanden", image.returncode == 0, "make agents-sandbox-image"))

    width = max(len(name) for name, _, _ in results)
    for name, ok, detail in results:
        print(f"{'OK  ' if ok else 'FEHLT'} {name.ljust(width)}  {detail if not ok else ''}".rstrip())
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
