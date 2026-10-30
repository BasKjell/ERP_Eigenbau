# Konfiguration

## Umgebungsvariablen

Die Datei `.env.example` ist versioniert. Lokale Werte liegen in `.env` und
werden durch `.gitignore` ausgeschlossen.

| Variable | Zweck | Standard im PoC |
|---|---|---|
| `DEMO_API_PORT` | Management-Portal/API | 8080 |
| `DOCS_PORT` | MkDocs | 8001 |
| `ERPNEXT_PORT` | ERPNext | 8081 |
| `PAPERLESS_PORT` | Paperless | 8010 |
| `MCP_PORT` | MCP-Endpunkt | 8090 |
| `MCP_WRITE_ENABLED` | Testdaten-Schreibwerkzeuge aktivieren | true (nur lokale Demo) |
| `MCP_MAX_WRITE_RECORDS` | maximale Datensätze je Schreibaufruf | 100 |
| `MCP_DEFAULT_COMPANY` | Standardfirma für importierte Testdaten | Open Manufacturing Demo GmbH |
| `AI_MODE` | `deterministic` oder `ollama` | deterministic |
| `OLLAMA_BASE_URL` | Modellserver aus dem Container | `host.docker.internal:11434` auf dem Mac |
| `OLLAMA_MODEL` | lokales Modell | qwen3:8b |
| `OLLAMA_TIMEOUT_SECONDS` | maximale Antwortzeit | 120 |
| `ERPNEXT_API_KEY/SECRET` | bevorzugte ERPNext-Tokenanmeldung | leer |
| `ERPNEXT_USERNAME` | lokale ERPNext-Sitzungsanmeldung | Administrator |
| `PAPERLESS_API_TOKEN` | Live-Adapter | leer |

## Passwörter und Secrets

Die Defaults sind nur für `localhost`. Für jede geteilte oder produktionsnahe
Umgebung:

1. zufällige, lange Werte erzeugen,
2. Secret-Manager bzw. Docker-Secrets verwenden,
3. keine Secret-Werte in Logs oder Screenshots aufnehmen,
4. Rotation und Notfallentzug dokumentieren.

## Integrationsmodus prüfen

```bash
curl http://localhost:8088/api/integrations
```

`mode=demo` bedeutet, dass der Portalzustand verwendet wird. `configured=true`
bedeutet, dass Credentials gesetzt sind. `reachable=true` bestätigt nur die
technische Erreichbarkeit; eine fachliche Berechtigungsprüfung gehört in den
Abnahmetest.

## Versionsstrategie

Container-Tags sind fixiert. Ein Update-PR enthält:

- Release Notes und Sicherheitsrelevanz,
- Backup-/Rollback-Hinweis,
- erfolgreiches `make validate`,
- API- und UI-Smoke-Test,
- Datenbankmigration im Testklon,
- aktualisierte Dokumentation bei Verhaltensänderung.
