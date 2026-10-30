# Lokaler Betrieb auf dem MacBook

## Voraussetzungen

- Docker Desktop mit Compose v2
- mindestens 6 GB freier RAM für den Demo-Stack
- etwa 16 GB freier RAM und 20 GB Speicher für das `full`-Profil empfohlen
- freie Ports 8088, 8001, 8081 und 8010; für optionale Profile zusätzlich
  8082, 11434, 9090 und 3000

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

## Backup-Mindestumfang

- `erpnext-sites-v16`, `erpnext-db-data-v16`
- `paperless-data`, `paperless-media`, `paperless-db-data`
- `demo-state` nur für laufende Präsentationsstände
- Git-Repository für Code und Dokumentation
- Keycloak-Konfiguration/Realm und Secrets getrennt
