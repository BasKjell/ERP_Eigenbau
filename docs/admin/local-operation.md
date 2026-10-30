# Lokaler Betrieb auf dem MacBook

## Voraussetzungen

- Docker Desktop mit Compose v2
- mindestens 6 GB freier RAM für den Demo-Stack
- etwa 16 GB freier RAM und 20 GB Speicher für das `full`-Profil empfohlen
- freie Ports 8088, 8001, 8081 und 8010; für optionale Profile zusätzlich
  8082, 8091, 8092, 11434, 3001, 9090 und 3000

## Erster Start

```bash
cp .env.example .env
make demo
```

Der erste Build lädt Basis-Images. Folgeaufrufe verwenden den lokalen Cache.

## Full-Stack starten

```bash
make full
docker compose ps
docker compose logs -f erpnext-create-site
```

ERPNext ist bereit, wenn `erpnext-create-site` erfolgreich beendet ist und
`erpnext-frontend` läuft. Der einmalige `erpnext-seed` muss ebenfalls mit
Exitcode 0 beendet sein. Je nach Mac und Verbindung kann die erste
Initialisierung mehrere Minuten dauern. Der Seed kann unabhängig wiederholt
werden:

```bash
docker compose --profile full run --rm erpnext-seed
```

`make full` startet auch Open WebUI. Nur die lokale Chat-Oberfläche wird mit
`make webui` gestartet. Sie verwendet standardmäßig das auf dem Mac laufende
Ollama unter `host.docker.internal:11434`.

## Stoppen und Zurücksetzen

```bash
make stop                 # Container stoppen, Datenvolumes behalten
make reset                # nur Management-Szenario zurücksetzen
```

Ein vollständiges Löschen der Volumes ist absichtlich nicht als Make-Ziel
vorhanden, weil dabei ERP-, DMS- und Datenbankdaten verloren gehen. Falls ein
bewusster Neuaufbau nötig ist, vorher exportieren und die Zielvolumes einzeln
prüfen.

## Diagnose

| Symptom | Prüfung | Maßnahme |
|---|---|---|
| Portal lädt nicht | `docker compose logs platform-api` | Port prüfen, Image neu bauen |
| Wiki fehlt | `docker compose logs docs` | `mkdocs.yml` und Markdown-Build prüfen |
| ERPNext zeigt 502 | `docker compose ps -a` | auf Site-Erstellung warten, Backend-Log prüfen |
| `erpnext-create-site` meldet TLS-Fehler | Image und Volume-Namen mit `compose.yaml` vergleichen | MariaDB 11.8 und die v16-Volumes verwenden |
| `erpnext-seed` endet mit Fehler | `docker compose logs erpnext-seed` | Schema-/Stammdatenfehler beheben, Seed erneut starten |
| Paperless startet nicht | DB-/Broker-Health prüfen | Secrets und Volumes prüfen |
| PDF liefert 404 | `ls output/pdf` | Beispieldokumente neu generieren |
| AI antwortet deterministisch | `AI_MODE` und Ollama prüfen | Modell laden, API neu starten |
| Open WebUI zeigt keine Modelle | Host-Ollama und `OPEN_WEBUI_OLLAMA_BASE_URL` prüfen | `ollama list`, danach Open WebUI neu starten |
| MCP fehlt in Open WebUI | Admin > Integrations prüfen | Streamable HTTP mit `http://platform-mcp:8090/mcp` einrichten |
| DMS-MCP liefert Authfehler | Paperless-Zugang oder Token prüfen | `dms-mcp` neu starten; Servicekonto verwenden |
| Wiki-MCP findet keine Seite | Mount `/docs` und Suchbegriff prüfen | `knowledge-mcp` neu erstellen |

## Backup-Mindestumfang

- `erpnext-sites-v16`, `erpnext-db-data-v16`
- `paperless-data`, `paperless-media`, `paperless-db-data`
- `demo-state` nur für laufende Präsentationsstände
- `open-webui-data` für Benutzer, Chats und Open-WebUI-Konfiguration
- Git-Repository für Code und Dokumentation
- Keycloak-Konfiguration/Realm und Secrets getrennt
