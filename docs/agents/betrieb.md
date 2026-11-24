# FLOWAGENTS – Betrieb

## Bausteine

| Baustein | Ort | Aufgabe |
|---|---|---|
| Orchestrator | Host-Dienst, `scripts/flow_agents.sh`, Zustand in `~/.flow-agents` (0700) | Ablauf, Gates, Budgets, Ereignisse; SQLite mit WAL |
| Plattform-API | Container `platform-api` | Agentenzentrale (BFF), RM-Adapter `/api/rm/v1`, Abgleich `/api/agents/sync` |
| FLOWGATE | Container `agentgateway`, LLM-Listener `127.0.0.1:4000` | je Rolle ein virtueller Schlüssel, nur das Modellprofil der Rolle ([SEC-AI-001](../architecture/ai-gateway-concept.md)) |
| Modelle | Ollama auf dem Host | `flow-builder`/`flow-assist` → qwen3:8b, `flow-coder` → qwen3-coder:30b, `flow-reviewer` → gemma3:12b |
| Prüf-Sandbox | Image `flow-agents-sandbox:1` | Lint und Tests am exakten Stand, `--network none`, read-only, ohne Zugangsdaten |
| Vorschau und Prüfbrowser | `flow-agents-preview` (Port 8098), Image `flow-agents-ui-runner:1`, Netz `flow-agents-ui` | Kandidat im Demo-Modus für G4, Klickprüfung |
| OpenCode-Worker | Image `flow-agents-opencode@sha256:…`, Netz `flow-agents-opencode` | lokaler agentischer Worker, nur FLOWGATE erreichbar |
| Abo-Worker | Image aus Trading_Ai, Netze `trading-dev-codex`/`-claude` mit Egress-Proxy | Codex (Entwicklung) und Claude (Codeprüfung) für komplexe Aufträge |
| Projektkatalog | `agents/projects.json` | Projekte, Änderungsbereiche, Mindest-Kritikalität, Arbeitspakete; Rechte über AD-Gruppen `AD-GG-FLOW-PRJ-*` |
| Zustand | `~/.flow-agents/flow-agents.sqlite` | Läufe, Projekte, Übersteuerungen der Agentenkonfiguration (`agent_settings`), Fachagenten (`business_agents`, `business_jobs`) |

Der Orchestrator öffnet **keinen** aus den Containern erreichbaren Port. Er holt Aktionen
(Fachauftrag, Entscheidung, Steuerung, Laufdetails, Paketstart, Agentenkonfiguration, Fachagenten) bei der
Plattform-API ab und meldet alle zwei
Sekunden seinen Zustand. Sein lokaler API-Port `127.0.0.1:8095` dient nur Diagnose und Status.

## Starten und prüfen

```bash
make sso-all                 # Plattform, Keycloak, Paperless, FLOWGATE …
make agents-sandbox-image    # einmalig: Prüfimage bauen
make agents-up               # Orchestrator starten
make requirements-sync       # Plattformanforderungen nach FLOWWORK übertragen
make agents-status           # Läufe, offene Entscheidungen, letzte Ereignisse
make agents-smoke            # laufende Kette prüfen (Orchestrator, Portal, FLOWGATE, Sandbox)
```

`curl http://127.0.0.1:8095/health` zeigt `platform_sync.connected`. Ist er `false`, meldet das
Portal „Orchestrator meldet sich nicht“ und nimmt keine Aufträge an.

## Konfiguration

`services/agent_orchestrator/config/orchestrator.yaml`:

- `providers`: Modellprofil → `gateway` (lokale Modelle), `simulated` (regelbasiert, für
  Vorführung ohne Modelle) oder `codex`/`claude` (Abo-Worker; Standardweg ist die Eskalation, siehe unten).
- `scopes`: freigegebene Änderungsbereiche; welche ein Projekt nutzen darf, steht in `agents/projects.json`.
- `sandbox`: Prüfimage, Prüfbefehl, erlaubte Pfadpräfixe.
- `preview`, `ui_check`: Vorschau für G4 und Klickprüfung.
- `opencode`: OpenCode-Worker (Image per Digest, internes Netz, Rollen, Rückfall).
- `escalation`, `container`: Weiterleitung komplexer Aufträge an Codex/Claude und deren Isolation.
- `budgets`, `adoption`: Laufbudget je Änderungsklasse, Übernahme als Branch nach G4.
- `demo_mode: true` erlaubt Demo-Geheimnisse und `platform-admin`-Entscheidungen im Demo-Modus.
  **Vor jeder Netzwerknutzung `false` setzen** und Geheimnisse über die Umgebung setzen:
  `FLOW_AGENT_RM_SECRET`, `FLOW_AGENTS_API_SECRET`, `FLOW_AGENT_GATEWAY_KEY_<ROLLE>` für alle 14 Rollen
  (einschließlich `PROJEKTPLANUNG` und `INTEGRATIONSTEST`) sowie `FLOW_AGENT_GATEWAY_KEY_FACHAGENTEN` (gleiche
  Werte in `.env` für Compose und in der Umgebung des Orchestrators).
- Plattform: `DEMO_USER_SWITCH=true` schaltet „Person wechseln“ ein (Standard in `compose.yaml` für die lokale
  Demo); **vor jeder Netzwerknutzung auf `false`**.
- Projektrechte und Demo-Konten erzeugt `python3 scripts/generate_iam_demo.py`; danach
  `docker compose --profile iam run --rm keycloak-sync` und Plattform neu bauen.

## Steuerung und Störungen

| Situation | Verhalten | Handlung |
|---|---|---|
| Agent soll nicht mehr arbeiten | Stopp-Schalter je Agent in `/agents` (Plattformbetrieb) | Wartende Aufträge halten an; „fortsetzen“ hebt auf |
| Alles anhalten | „Alle Agenten anhalten“ | Kein weiterer Schritt; laufender Modellaufruf endet noch |
| Modell lädt/Überlast | bis zu zwei Wiederholungen mit Pause | danach Blockade für den Tech Lead |
| Ungültige Übergabe | eine Wiederholung mit Fehlerhinweis | danach Blockade; Tech Lead: erneut versuchen oder abbrechen |
| Neustart während eines Schritts | Schritt „unterbrochen“, wird idempotent wiederholt | nichts |
| Register/Prompts oder Agentenkonfiguration geändert | laufende Aufträge blockieren | Tech Lead stellt bewusst um oder bricht ab |
| Fachagent: Modell nicht erreichbar | Aufgabe endet mit „Fehler“ und Grund | FLOWGATE/Ollama prüfen, Aufgabe neu geben |
| Budget erschöpft | Blockade ohne weiteren Modellaufruf | Tech Lead entscheidet |

## Token-Verbrauch (Grafana)

Grafana → Ordner „ERP Eigenbau“ → **Lokale KI – Token-Verbrauch** (Profil `ops`:
`docker compose --profile ops up -d prometheus grafana`).

- **Alle lokalen Modelle:** Prometheus liest `agentgateway:15020/metrics`
  (`agentgateway_gen_ai_client_token_usage_sum`, getrennt nach Modell und Eingabe/Ausgabe). Das
  umfasst Agenten und FLOWAI-Chats. Der Zähler beginnt bei jedem Neustart von FLOWGATE neu; die
  Zeitraum-Kacheln rechnen das heraus.
- **Je Agentenrolle:** Der Orchestrator speichert jeden Modellaufruf (Rolle, Modell, Token, Sekunden;
  keine Inhalte) in `model_usage` und meldet die Summen mit der Übersicht. Die Plattform-API stellt sie
  als `flow_agents_tokens_total`, `flow_agents_model_calls_total` und `flow_agents_model_seconds_total`
  bereit.
- **Geschwindigkeit je Modell:** Der Orchestrator ruft FLOWGATE gestreamt auf. Dadurch misst FLOWGATE
  die *Einlesezeit bis zum ersten Token* (`agentgateway_gen_ai_server_time_to_first_token`) und die
  *Zeit je Ausgabe-Token* (`…_time_per_output_token`). Das Panel „Schreibgeschwindigkeit je Modell“
  zeigt daraus die reine Generierung in Token/s. „Ausgabe-Token je Modellsekunde“ enthält dagegen auch
  das Einlesen und liegt deshalb niedriger. Richtwerte auf dem M1 Max (Stand 2026-11-22):
  flow-qwen3-coder-32k ≈ 75, qwen3:8b ≈ 45, gemma3:12b ≈ 28 Token/s beim Schreiben.

## Speicher auf dem 32-GB-Mac

`flow-coder` zeigt auf `flow-qwen3-coder-32k` (Modelfile in `deployment/ollama/`): qwen3-coder:30b
mit 32k statt 64k Kontext, rund 21 statt 25 GB, vollständig auf der GPU. Mit 64k plus Docker-VM (8 GB)
lagerte macOS aus, der Coder fiel auf etwa 2 Token/s und jeder Entwicklungsschritt lief in das
15-Minuten-Timeout. Einmalig anlegen:

```bash
ollama create flow-qwen3-coder-32k -f deployment/ollama/flow-coder.Modelfile
```

Prüfen mit `ollama ps`: Spalte PROCESSOR muss „100% GPU“ zeigen.

## Klickprüfung im Browser (G4)

Der Akzeptanztest-Agent schreibt zu Testfällen optional einen Klickpfad (`goto`, `click`, `fill`,
`select`, `upload`, `expect_text`, `expect_visible`, `screenshot`; Sprache in
`flowagents/uicheck.py`). Sobald an G4 die Vorschau steht, führt der Orchestrator die Pfade mit
Playwright/Chromium aus und hängt Ergebnis und Bildschirmfotos an die Fachabnahme („Änderung
ansehen“ → „Klickprüfung im Browser“). Das Modell selbst steuert keinen Browser.

- Prüfbrowser: Image `flow-agents-ui-runner:1`, einmalig bauen mit
  `docker build -t flow-agents-ui-runner:1 deployment/ui-runner`.
- Isolation: eigenes internes Netz `flow-agents-ui` (nur Vorschau und Prüfbrowser, kein Internet),
  read-only, `--cap-drop ALL`; der Browser lädt nur Adressen der Vorschau; Uploads nur mit
  eingebauten Testdateien (`beispiel.stl`, `.pdf`, `.png`, `.txt`).
- Abschalten: `ui_check.enabled: false`.
- Ablauf, echte Vorführung mit lokaler KI und Bilder: [Klickprüfung mit lokaler KI](klickpruefung.md).

## OpenCode-Worker (lokal, agentisch)

[OpenCode](https://opencode.ai) ist eine Open-Source-Agenten-CLI. FLOWAGENTS nutzt sie als dritten Worker
neben Codex und Claude, aber **ohne Abo und ohne Internet**: OpenCode spricht nur mit FLOWGATE und damit
mit denselben lokalen Modellen und Rollenschlüsseln wie der direkte Aufruf.

| Punkt | Festlegung |
|---|---|
| Auswahl | je Auftrag: „Umsetzung → OpenCode (lokal, agentisch)“; gilt für die Rollen in `opencode.roles` (Standard: Entwicklung) |
| Daten | bleiben im Haus; auch für vertrauliche Aufträge zulässig |
| Image | `services/agent_orchestrator/opencode.Dockerfile`, OpenCode 1.19.6, nur per Digest in `opencode.image` |
| Netz | internes Docker-Netz `flow-agents-opencode` ohne Internet; einziger Partner ist FLOWGATE (`agentgateway:4000`) |
| Container | read-only, `--cap-drop ALL`, `no-new-privileges`, Speicher- und CPU-Grenzen, keine Logs |
| Werkzeuge | Schreiben, Bearbeiten, Shell und Webzugriff verboten; Plugins, Skills, Modellkatalog und Selbstaktualisierung aus |
| Schlüssel | virtueller FLOWGATE-Schlüssel der Rolle über die Prozessumgebung, nie in der Befehlszeile |
| Sicht | kein Repository; nur der Prompt als Datei im tmpfs |
| Ausfall | Rückfall auf den direkten FLOWGATE-Aufruf (`opencode.fallback`), im Ergebnis als Rückfall markiert |

Einrichten, einmal je Rechner:

1. `make agents-opencode-image` und die ausgegebene Image-ID in `opencode.image` eintragen.
2. FLOWGATE mit dem internen Netz starten: `docker compose --profile ai-gateway up -d agentgateway`.
3. `make agents-restart`.

Abschalten: `opencode.enabled: false`. Die Unabhängigkeit von Ersteller und Prüfer bleibt erhalten,
weil OpenCode dasselbe Modell der Rolle nutzt; die Modellfamilie ändert sich nicht.

## Abo-Worker (Codex/Claude) für komplexe Änderungen

Freigeschaltet mit der Umgebung aus Trading_Ai (Details und Regeln: Sicherheitskonzept §7).
Voraussetzungen, einmal je Rechner:

die Egress-Proxys des Trading-Pilots laufen (`orchestrator-pilot-egress.yaml` aus dem
Trading_Ai-Pilot, `docker compose -f <pfad>/orchestrator-pilot-egress.yaml up -d`).

- Die Abo-Anmeldung liegt in den Volumes `trading-dev-codex-auth` und `trading-dev-claude-auth`.
- Komplex sind: Klasse „kritisch“, Änderungsbereiche „ERP-Anbindung“ und „Plattform-API – zentrale
  Routen“, Umsetzung „Codex/Claude (Abo)“ im Auftrag oder zwei gescheiterte lokale Versuche.
- Im Auftragsformular steuert **Umsetzung** das je Auftrag: automatisch, nur lokal, OpenCode (lokal),
  Codex/Claude.
- Abschalten: `escalation.enabled: false` (nur Weiterleitung) oder `container.execution_enabled: false`
  (Worker komplett gesperrt), danach `scripts/flow_agents.sh restart`.

## FLOWDOC mit der lokalen KI weiterentwickeln

1. Stack und Orchestrator laufen (`make sso-all`, `make agents-up`, Prüfung mit `make agents-smoke`).
2. In FLOWPORTAL **＋ Fachauftrag starten**, Projekt `FLOW-DMS` (Änderungsrecht nötig, z. B. `po.demo`),
   Einstufung (meist S/K1) und Änderungsbereich wählen:
   - `dms-doku` – nur die Benutzerhilfe,
   - `dms-ui` – Oberfläche (`dms.js`, `dms.css`),
   - `dms-backend` – Paperless-Anbindung (`dms.py`) mit Tests,
   - `dms-komplett` – Oberfläche, Backend, Tests und Hilfe zusammen.
3. Die Agenten arbeiten mit den lokalen Modellen über FLOWGATE. Du entscheidest in der Inbox
   (je nach Einstufung EP1 und G1, bei K2/K3 alle Gates, immer G4 und G5). Ablehnungen mit Begründung gehen als Befund zurück.
4. **Vor der Fachabnahme (G4)** startet der Kandidat als Vorschau unter `http://localhost:8098/dms`
   (Demo-Modus, Paperless mit dem technischen Demo-Konto). Der Link steht in der Entscheidung.
5. **Nach angenommener Fachabnahme** liegt genau der abgenommene Stand als lokaler Branch
   `agent/A-…` im Repository (`git branch --list 'agent/*'`). Dein Checkout bleibt unverändert.
   Prüfen, ggf. nacharbeiten und selbst mergen; mit `adoption.push: true` wird der Branch zusätzlich
   gepusht.
6. Reicht das Laufbudget nicht, gibt der Tech Lead in der Inbox bewusst 20 weitere Modellaufrufe frei.

Grenzen der lokalen Modelle: Der Entwickler schreibt geänderte Dateien vollständig neu (Eingabe bis
70 000 Zeichen, Ausgabe bis 16 000 Token); die lokalen Prüfer sind nachgiebig. Fachliche
Richtigkeit sichert deshalb die Fachabnahme in der Vorschau. Schwierige Aufgaben eskaliert der
Orchestrator seit 2026-11-22 zu Codex (Entwicklung) bzw. Claude (Codeprüfung), siehe „Abo-Worker“;
vertrauliche Aufträge und Aufträge mit Umsetzung „nur lokal“ bleiben immer auf dem Rechner.
