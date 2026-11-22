# Übergabe: FLOWAGENTS, Agentenzentrale, FLOWWORK-Anbindung und FLOWDOC

**Branch:** `claude/flow-agents` (lokal, nicht gepusht) · **Basis:** `codex/erpnext-demo-seed` mit
Snapshot-Commit `c28bb9c` (unveränderter Codex-Arbeitsstand vom 2026-11-22)
**Autor:** Claude Code / claude-opus-5-5 · **Risikoklasse:** K (Agentenrechte, Tokens, Register,
Ablauf, CI, normative Regeln) → unabhängiges Review durch Codex, danach Freigabe durch Bas.

Review-Diff: `git diff codex/erpnext-demo-seed..claude/flow-agents`

## Auftrag (Bas, 2026-11-22)

1. Die Agentenstruktur aus `Trading_Ai` übernehmen und vollständig lauffähig machen.
2. Je Aufgabe ein eigener Agent; zusätzlich ein Agent mit Geschäftsführungs-Sicht auf die Abläufe.
3. Requirements im Jama-Nachbau (FLOWWORK) festhalten; Entwicklung separat abnehmen.
4. Landingpage zeigt, was die Agenten tun und wie sie zusammenarbeiten.
5. DMS mit komplett eigener Oberfläche; Werkzeuge nur über APIs anbinden.
6. BSI-orientierter Ansatz nach dem KI-Entwicklungs-/Unternehmenskonzept.

## Was entstanden ist (Status: implementiert und getestet, nicht integriert)

| Bereich | Dateien | Kern |
|---|---|---|
| Register und Ablauf | `agents/registry.yaml`, `agents/workflow.yaml`, `agents/prompts/` | 11 Rollen + Geschäftsführungs-Agent, Klassen, G1–G5, Budget |
| Orchestrator | `services/agent_orchestrator/flowagents/` | Engine, Vertrag, Store, Provider, Sandbox, Pull-Abgleich, gesperrte Abo-Worker |
| RM-Adapter | `services/platform_api/app/agent_policy.py`, `rm_adapter.py` | Token-/Registerprüfung, idempotente Entwürfe, Baseline nur durch Orchestrator |
| Agentenzentrale | `agents_bff.py`, `flow_routes.py`, `static/agent-center.*`, `static/agents.html`, `portal.html` | Live-Karte, Inbox, Fachauftrag, Laufdetails, Stopp-Schalter |
| FLOWDOC | `dms.py`, `static/dms.*` | eigene DMS-Oberfläche im Namen der Person |
| Requirements | `requirements/catalog.yaml`, `app/requirements_catalog.py` | 29 Anforderungen, 63 Testverweise, Sync nach FLOWWORK |
| Betrieb | `compose.yaml`, `deployment/agentgateway/config.yaml`, `scripts/flow_agents.sh`, `Makefile`, CI | Rollenschlüssel, Loopback-LLM-Port, Remote-User-API, `make agents-*` |
| Regeln/Doku | `AGENTS.md`, `CLAUDE.md`, ADR-007/008, `docs/agents/`, `docs/user-guides/flowdoc.md` | |

Nebenbei: Ruff-Befunde im Codex-Bestand behoben (`b43691e`, reine Formatierung); das
Docker-Test-Target war vorher rot.

## Nachweise (lokal ausgeführt am 2026-11-22)

- `make agents-test`: Ruff sauber, 65 Tests grün (Orchestrator); `make agents-smoke` 8/8 gegen die laufende Kette.
- Plattform: `pytest services/platform_api/tests` grün; `docker build --target test`
  (Ruff + Coverage ≥ 75 %) grün.
- `make requirements-check`: 29 Anforderungen, 63 Testverweise gültig.
- `mkdocs build --strict`, `validate_app_shell.py`, `validate_open_webui_config.py`, `docker compose config`: grün.
- Live: FLOWGATE lehnt fremde Modelle je Rollenschlüssel ab (403) und Aufrufe ohne Schlüssel (401).
- Live-Lauf A-001 mit lokalen Modellen (Ergebnis siehe Abschnitt „Live-Lauf“).
- **Nicht ausgeführt:** GitHub-CI (Branch nicht gepusht), `make test-integration` gegen alle
  Live-Systeme, Abo-Worker (gesperrt).

## Live-Lauf A-001 (lokale Modelle über FLOWGATE, Klasse „neue Funktion“)

Auftrag: Bedienhilfe für die Titel-Sortierung in FLOWDOC (Bereich `dms-doku`).
Durchlaufen: Geschäftsführungs-Agent → Anforderungen ↔ Prüfung → G1 (abgelehnt im Portal, dann
nach zwei Prüfrunden und Korrekturlimit freigegeben) → Architektur → Sicherheit → G2 → Planung →
Akzeptanztests → Entwicklung → Integrationsprüfung offline (bestanden, 14 s) → Codeprüfung → G3 →
Dokumentation → Nachweise → Geschäftsführungs-Agent → G4. Die Fachabnahme wurde zweimal begründet
abgelehnt, weil die Hilfe den Statusfilter falsch beschrieb (Codeprüfung hatte das nicht erkannt).
Danach war das Laufbudget (40 Modellaufrufe) erschöpft; der Lauf **wartet auf den Tech Lead**
(`ENT-F70F0B65`). In FLOWWORK liegen REQ-DMS-001…003, Baselines BL-DMS-001/002, Testfälle und Tickets.

Gegriffene Schutzmechanismen: Ergebnisvertrag mit Wiederholung, menschliche G1-/G4-Ablehnung als
Befund, Korrekturlimit, Register-Umstellung nach Prompt-Änderung, Wiederanlauf nach Neustart,
Digest-Bindung, Laufbudget. Gefundene und behobene Fehler: siehe `docs/agents/modellbewertung.md`.

## Prüfschwerpunkte für Codex (Klasse K)

1. `agent_policy.verify_agent_token` und `rm_adapter.handle`: Kann eine Rolle eine fremde Operation,
   einen fremden Entwurf oder eine Baseline erreichen? Audit ohne Inhalte?
2. `flow_routes`: `/api/rm/v1/` und `/api/agents/sync/` sind vom Sitzungs-Middleware ausgenommen –
   ist die eigene Authentifizierung vollständig? Werden Agenten-Tokens an `/api/work` abgewiesen?
3. `agents_bff.AgentsHub`: Person in Aktionen nur aus der Sitzung; Leasing/Timeouts; Speicherbegrenzung.
4. `engine.decide`/`_authorize`: Rollenprüfung, Digest-Bindung (G3–G5), `demo_mode`-Ausnahme für
   `platform-admin`.
5. `sandbox.validate_path`, `Sandbox._export`, `DockerCheck`: Pfadflucht, Symlinks, `.env`, Netzwerk.
6. `dms.DmsService`: kein technischer Rückfall im OIDC-Modus; Remote-User-Header nur aus der Sitzung.
7. `container.py`: Isolation 1:1 zum Trading-Pilot? `validate_settings` fail closed?
8. Kompatibilität mit dem Codex-Bestand: `auth.py`, `main.py`, `compose.yaml`, `app-launcher.js`.

## Bewusste Entscheidungen

- **Pull-Modell** statt Port: Die Plattform-API im Container erreicht unter Docker Desktop keinen
  Loopback-Dienst des Hosts; den Orchestrator auf alle Schnittstellen zu öffnen wurde verworfen.
- **Orchestrator auf dem Host**, nicht im Container: Die Integrationsprüfung braucht Docker; ein
  Docker-Socket im Orchestrator-Container widerspräche KI-EK Teil 03.
- **Prompts im Register-Digest:** Eine Änderung blockiert laufende Aufträge, bis der Tech Lead umstellt.
- **Entscheidungsrollen** vorläufig auf vorhandene Keycloak-Rollen abgebildet (kein Realm-Drift).
- **Kein Push, kein PR:** Das Repository ist öffentlich und der Codex-Arbeitsstand war nicht gepusht.

## Nachtrag 2026-11-22 abends: Entwicklungsumgebung für die lokale KI

Auf Wunsch von Bas **ohne Codex-Review** umgesetzt (Codex-Kontingent erst in drei Tagen); das Review
wird für den gesamten Branch nachgeholt: Übernahme abgenommener Stände als Branch `agent/A-…`,
Vorschau des Kandidaten vor G4 auf `127.0.0.1:8098`, Änderungsbereiche `dms-backend` und
`dms-komplett`, Laufbudget je Klasse mit Nachschlag durch den Tech Lead (REQ-AGT-015 bis -017).
Neue Prüfschwerpunkte: `flowagents/adoption.py` (Integrität, Worktree, kein Eingriff in den Checkout)
und die Vorschau (Demo-Modus mit technischem Paperless-Konto, nur Loopback).

## Offene Punkte / nächste Schritte

1. Codex-Review dieses Branches (Klasse K), danach Freigabe durch Bas; erst dann Push und PR.
2. *(erledigt 2026-11-22)* Eigene Realm-Rollen `flow-*` mit Demo-Konten je Rolle; Register umgestellt.
3. Modell-Evaluation je Rolle mit Referenzfällen (Test 34); lokale Prüfer sind nachweislich nachgiebig.
4. RM-Wiederanlauf: Bei Versionskonflikt nach Unterbrechung Objektstatus abfragen statt blockieren.
5. GitHub-PR-Weg für Entwicklungsergebnisse. *(Abo-Worker sind seit 2026-11-22 freigeschaltet und
   nutzen die Trading-Pilot-Infrastruktur: Image, Egress-Proxys, Login-Volumes.)*
6. Offene Abnahmefälle und Sicherheitslücken: `docs/agents/sicherheit.md`.
