# Docker-Compose-Stack administrieren

## Profile

| Profil | Inhalt | Start |
|---|---|---|
| Standard | Portal, Demo-DB, Wiki | `make demo` |
| `full` | zusätzlich ERPNext und Paperless | `make full` |
| `iam` | Keycloak | `docker compose --profile iam up -d` |
| `ai` | Ollama | `make ai` |
| `ops` | Prometheus und Grafana | `docker compose --profile ops up -d` |

## Sichere Betriebsroutine

```bash
docker compose --profile full --profile iam --profile ai --profile ops config --quiet
docker compose ps -a
docker compose logs --tail=150 SERVICE
make stop
```

`.env.example` ist Vorlage, `.env` bleibt unversioniert. Vor Start Ports,
Speicher, Secrets und Volume-Ziele prüfen. Images sind fixiert und werden nur
nach Release-Note-, Backup- und Migrationstest aktualisiert.

## Daten und Wiederanlauf

`make stop` erhält Volumes. Ein `down -v` ist absichtlich kein Make-Ziel, weil
es Daten löscht. Backups werden je Fachsystem konsistent erstellt; eine Liste
der Volumes allein ersetzt keinen Restore-Test. Nach Host-Neustart zuerst
Datenbanken, dann abhängige Dienste und zuletzt Integrationen prüfen.

## Abnahme

- Alle erwarteten Services sind `running`, `healthy` oder erfolgreich beendet.
- Portal, Wiki, ERPNext und Paperless sind über ihre definierten Ports
  erreichbar.
- Persistenz über einen kontrollierten Neustart ist nachgewiesen.
- Logs enthalten keine Secrets und keine wiederkehrenden Fehler.
- `make test` und `make validate` sind erfolgreich.

Compose ist die lokale PoC-Laufzeit, nicht automatisch eine produktive
Orchestrierung. Für Produktion sind TLS, Secret-Management, Backup, Monitoring,
HA, Ressourcenlimits und Updateverfahren separat freizugeben.
