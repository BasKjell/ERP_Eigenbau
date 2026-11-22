# FLOWAGENTS – Betrieb

## Bausteine

| Baustein | Ort | Aufgabe |
|---|---|---|
| Orchestrator | Host-Dienst, `scripts/flow_agents.sh`, Zustand in `~/.flow-agents` (0700) | Ablauf, Gates, Budgets, Ereignisse; SQLite mit WAL |
| Plattform-API | Container `platform-api` | Agentenzentrale (BFF), RM-Adapter `/api/rm/v1`, Abgleich `/api/agents/sync` |
| FLOWGATE | Container `agentgateway`, LLM-Listener `127.0.0.1:4000` | je Rolle ein virtueller Schlüssel, nur das Modellprofil der Rolle |
| Modelle | Ollama auf dem Host | `flow-builder`/`flow-assist` → qwen3:8b, `flow-coder` → qwen3-coder:30b, `flow-reviewer` → gemma3:12b |
| Prüf-Sandbox | Image `flow-agents-sandbox:1` | Lint und Tests am exakten Stand, `--network none`, read-only, ohne Zugangsdaten |

Der Orchestrator öffnet **keinen** aus den Containern erreichbaren Port. Er holt Aktionen
(Fachauftrag, Entscheidung, Steuerung, Laufdetails) bei der Plattform-API ab und meldet alle zwei
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
  Vorführung ohne Modelle) oder `codex`/`claude` (gesperrt).
- `scopes`: freigegebene Änderungsbereiche je Fachauftrag.
- `sandbox`: Prüfimage, Prüfbefehl, erlaubte Pfadpräfixe.
- `demo_mode: true` erlaubt Demo-Geheimnisse und `platform-admin`-Entscheidungen im Demo-Modus.
  **Vor jeder Netzwerknutzung `false` setzen** und Geheimnisse über die Umgebung setzen:
  `FLOW_AGENT_RM_SECRET`, `FLOW_AGENTS_API_SECRET`, `FLOW_AGENT_GATEWAY_KEY_<ROLLE>` (gleiche Werte in
  `.env` für Compose und in der Umgebung des Orchestrators).

## Steuerung und Störungen

| Situation | Verhalten | Handlung |
|---|---|---|
| Agent soll nicht mehr arbeiten | Stopp-Schalter je Agent in `/agents` (Plattformbetrieb) | Wartende Aufträge halten an; „fortsetzen“ hebt auf |
| Alles anhalten | „Alle Agenten anhalten“ | Kein weiterer Schritt; laufender Modellaufruf endet noch |
| Modell lädt/Überlast | bis zu zwei Wiederholungen mit Pause | danach Blockade für den Tech Lead |
| Ungültige Übergabe | eine Wiederholung mit Fehlerhinweis | danach Blockade; Tech Lead: erneut versuchen oder abbrechen |
| Neustart während eines Schritts | Schritt „unterbrochen“, wird idempotent wiederholt | nichts |
| Register/Prompts geändert | laufende Aufträge blockieren | Tech Lead stellt bewusst um oder bricht ab |
| Budget erschöpft | Blockade ohne weiteren Modellaufruf | Tech Lead entscheidet |

## Abo-Worker (Codex/Claude) – gesperrt

Übernommen aus `Trading_Ai` (T-020/T-025/T-027): isolierte Container, read-only, `cap-drop ALL`,
eigenes internes Netz mit Egress-Proxy je Anbieter, Anmeldedaten nur aus schreibgeschütztem Volume,
frisches Home im tmpfs. Aktivierung erst nach unabhängiger Prüfung und ausdrücklicher Freigabe:

1. Worker-Image aus `services/agent_orchestrator/worker.Dockerfile` mit geprüften CLI-Versionen bauen,
   Digest eintragen (`container.image`).
2. Netze `flow-dev-codex`/`flow-dev-claude` und Egress-Proxys nach dem Muster
   `orchestrator-pilot-egress.yaml` aus dem Trading-Pilot anlegen und mit den Verify-Proben prüfen.
3. Volumes `flow-dev-codex-auth`/`flow-dev-claude-auth` mit der Container-UID anmelden.
4. `container.execution_enabled: true` und ein Modellprofil auf `codex` oder `claude` setzen.
   Bewährte Aufteilung: Claude erstellt, Codex prüft (oder umgekehrt) – nie dieselbe Familie.

## FLOWDOC mit der lokalen KI weiterentwickeln

1. Stack und Orchestrator laufen (`make sso-all`, `make agents-up`, Prüfung mit `make agents-smoke`).
2. In FLOWPORTAL **＋ Fachauftrag starten**, Projekt `FLOW-DMS`, Änderungsbereich wählen:
   - `dms-doku` – nur die Benutzerhilfe,
   - `dms-ui` – Oberfläche (`dms.js`, `dms.css`),
   - `dms-backend` – Paperless-Anbindung (`dms.py`) mit Tests,
   - `dms-komplett` – Oberfläche, Backend, Tests und Hilfe zusammen.
3. Die Agenten arbeiten mit den lokalen Modellen über FLOWGATE. Du entscheidest in der Inbox
   (je nach Klasse G1, immer G4 und G5). Ablehnungen mit Begründung gehen als Befund zurück.
4. **Vor der Fachabnahme (G4)** startet der Kandidat als Vorschau unter `http://localhost:8098/dms`
   (Demo-Modus, Paperless mit dem technischen Demo-Konto). Der Link steht in der Entscheidung.
5. **Nach angenommener Fachabnahme** liegt genau der abgenommene Stand als lokaler Branch
   `agent/A-…` im Repository (`git branch --list 'agent/*'`). Dein Checkout bleibt unverändert.
   Prüfen, ggf. nacharbeiten und selbst mergen; mit `adoption.push: true` wird der Branch zusätzlich
   gepusht.
6. Reicht das Laufbudget nicht, gibt der Tech Lead in der Inbox bewusst 20 weitere Modellaufrufe frei.

Grenzen der lokalen Modelle: Der Entwickler schreibt geänderte Dateien vollständig neu (Eingabe bis
70 000 Zeichen, Ausgabe bis 16 000 Token); die lokalen Prüfer sind nachgiebig. Fachliche
Richtigkeit sichert deshalb die Fachabnahme in der Vorschau. Für schwierige Aufgaben ist die
Eskalation zu Claude/Codex vorgesehen (siehe „Abo-Worker“), aber noch nicht freigeschaltet.
