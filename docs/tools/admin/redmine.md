# Redmine und FLOWWORK administrieren

## Start

```bash
cp .env.example .env
make work
```

FLOWWORK ist unter `http://localhost:8088/work`, Redmine direkt unter
`http://localhost:8011` erreichbar. Der idempotente Seed aktiviert die REST-API
und erzeugt Demo-Projekte, Wiki-Seiten und Tickets.

| Container | Aufgabe | Persistenz |
|---|---|---|
| `redmine-db` | PostgreSQL-Datenbank | `redmine-db-data` |
| `redmine` | Webanwendung und REST-API | `redmine-files` |
| `redmine-shell` | gemeinsame Navigation und transparenter Web-Proxy | keine eigene |
| `redmine-seed` | idempotenter Demo-Seed | keine eigene |
| `platform-api` | SSO-Oberfläche und Adapter | `demo-state` |

## Sicherheit

- Demo-Passwörter und Demo-API-Key vor Produktiveinsatz ersetzen.
- Der Redmine-API-Key ist ein serverseitiges Secret und darf nie in
  Browsercode ausgeliefert werden.
- Redmine bietet ohne Erweiterung kein natives Keycloak-OIDC. Entweder ein
  gepflegtes OIDC-Plugin hinter Reverse Proxy validieren oder den direkten
  Redmine-Zugang auf Administratoren begrenzen.
- Im Livebetrieb ein dediziertes API-Servicekonto mit minimalen Projektrollen
  statt des globalen Administrators verwenden.

## Backup

Konsistent zu sichern sind Datenbank und Dateivolume:

```bash
docker compose exec redmine-db pg_dump -U redmine -Fc redmine > redmine.dump
docker run --rm -v erp-eigenbau_redmine-files:/data -v "$PWD":/backup alpine \
  tar czf /backup/redmine-files.tgz -C /data .
```

## Updateverfahren

1. Release Notes und Plugin-Kompatibilität prüfen.
2. Datenbank und Dateien sichern.
3. Image-Tag in `compose.yaml` ändern.
4. Migration in einer Testumgebung starten.
5. `make test` und `make test-integration` ausführen.
6. Ticketanlage und Wiki-Verknüpfung manuell prüfen.
7. FLOWWORK-Regression für eigene Felder, Relationship-Regeln, Suspect Links,
   Review-Signaturen, Testlauf, Risiko, Varianten und Baseline-Vergleich
   ausführen.
8. JSON- und ReqIF-Export erzeugen und in der Testumgebung erneut einlesen.

Das Image ist explizit versioniert; unkontrollierte `latest`-Updates sind
ausgeschlossen.

## FLOWWORK-Konfiguration sichern

Redmine und FLOWWORK haben getrennte führende Daten. Neben Redmine-Datenbank
und Dateien muss deshalb auch das Volume `demo-state` beziehungsweise im
Livebetrieb die konfigurierte FLOWWORK-Datenbank gesichert werden. Der
zusätzliche Austausch-Export enthält Itemtypen, Felder, Relationship-Modell,
Requirements, Tests, Risiken und Baselines:

```bash
curl --fail --output flowwork-export.json \
  'http://localhost:8088/api/work/export?format=json'
curl --fail --output flowwork-export.reqif \
  'http://localhost:8088/api/work/export?format=reqif'
```

Für eine Rücksicherung ist der Datenbank-/Volume-Restore führend. Der
JSON-Import ergänzt nur noch nicht vorhandene IDs und ist als kontrollierter
Migrationsweg, nicht als vollständiger Disaster-Recovery-Ersatz gedacht.
