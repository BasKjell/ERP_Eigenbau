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
| `DMS_MCP_PORT` | Paperless-MCP-Endpunkt | 8091 |
| `KNOWLEDGE_MCP_PORT` | Prozess-Wiki-MCP-Endpunkt | 8092 |
| `OPEN_WEBUI_PORT` | lokale Chat-Oberfläche | 3001 |
| `AGENTGATEWAY_UI_PORT` | SSO-geschützte FLOWGATE-Administration | 4001 |
| `MCP_WRITE_ENABLED` | Testdaten-Schreibwerkzeuge aktivieren | true (nur lokale Demo) |
| `MCP_MAX_WRITE_RECORDS` | maximale Datensätze je Schreibaufruf | 100 |
| `MCP_DEFAULT_COMPANY` | Standardfirma für importierte Testdaten | Open Manufacturing Demo GmbH |
| `AI_MODE` | `deterministic` oder `ollama` | deterministic |
| `OLLAMA_BASE_URL` | Modellserver aus dem Container | `host.docker.internal:11434` auf dem Mac |
| `OLLAMA_MODEL` | lokales Modell | qwen3:8b |
| `OLLAMA_TIMEOUT_SECONDS` | maximale Antwortzeit | 120 |
| `AGENTGATEWAY_OLLAMA_BASE_URL` | Ollama aus FLOWGATE | `host.docker.internal:11434/v1` |
| `AGENTGATEWAY_OPENWEBUI_KEY` | eingeschränkter virtueller Schlüssel für FLOWAI | lokaler Demo-Wert; ändern |
| `AGENTGATEWAY_OIDC_CLIENT_SECRET` | Keycloak-Clientgeheimnis für die FLOWGATE-Administration | lokaler Demo-Wert; ändern |
| `AGENTGATEWAY_OIDC_COOKIE_SECRET` | Verschlüsselung der FLOWGATE-OIDC-Sitzung | 64 Hex-Zeichen; ändern |
| `AGENTGATEWAY_SESSION_KEY` | Verschlüsselung interner Gateway-Sitzungs-IDs | 64 Hex-Zeichen; ändern |
| `OPEN_WEBUI_SECRET_KEY` | Sitzungs- und Tokenverschlüsselung | lokaler Demo-Wert; ändern |
| `DOCUMENTATION_PUBLIC_URL` | klickbare Wiki-Basis in KI-Antworten | `http://localhost:8001` |
| `ERPNEXT_PUBLIC_URL` | öffentliche ERPNext-Basis für Links | `http://localhost:8081` |
| `PAPERLESS_PUBLIC_URL` | öffentliche Paperless-Basis für Dokumentlinks | `http://localhost:8010` |
| `ERPNEXT_API_KEY/SECRET` | bevorzugte ERPNext-Tokenanmeldung | leer |
| `ERPNEXT_USERNAME` | lokale ERPNext-Sitzungsanmeldung | Administrator |
| `PAPERLESS_API_TOKEN` | Live-Adapter | leer |
| `PAPERLESS_ADMIN_USER/PASSWORD` | lokaler DMS-MCP-Fallback | Demo-Zugang |
| `GRAFANA_ADMIN_PASSWORD` | initialer lokaler Grafana-Admin | Demo-Zugang |
| `GRAFANA_PAPERLESS_DB_PASSWORD` | Passwort der read-only DMS-Reporting-Rolle | lokaler Demo-Wert |
| `GRAFANA_MANAGEMENT_DB_PASSWORD` | Passwort der read-only Management-Reporting-Rolle | lokaler Demo-Wert |
| `AUTH_MODE` | `demo` oder erzwungene Plattformanmeldung `oidc` | demo |
| `AUTH_SESSION_SECRET` | Signatur der lokalen OIDC-Sitzung | lokaler Demo-Wert; ändern |
| `AUTH_SESSION_MINUTES` | Laufzeit der Plattform-Sitzung | 480 |
| `AUTH_COOKIE_SECURE` | Cookie nur über HTTPS senden | false lokal, true live |
| `PLATFORM_PUBLIC_URL` | öffentliche Callback-Basis | `http://localhost:8088` |
| `OIDC_EXTERNAL_ISSUER` | für Browser erreichbarer Keycloak-Issuer | lokaler Realm |
| `KEYCLOAK_PUBLIC_URL` | stabiler öffentlicher Issuer/Hostname | `http://localhost:8082` |
| `GRAFANA_OIDC_ENABLED` | Keycloak Generic OAuth für Grafana aktivieren | false |

## Einheitliche Unternehmens-Shell

Öffentliche Webports zeigen auf eine schmale Nginx-Shell; die eigentliche
Anwendung bleibt ausschließlich im Compose-Netz erreichbar.

| Öffentlicher Dienst | Shell-Service | Interner Upstream |
|---|---|---|
| Prozess-Wiki | `docs-shell` | `docs:8000` |
| ERPNext | `erpnext-shell` | `erpnext-frontend:8080` |
| Paperless | `paperless-shell` | `paperless-webserver:8000` |
| Redmine | `redmine-shell` | `redmine:3000` |
| Keycloak | `keycloak-shell` | `keycloak:8080` |
| Open WebUI | `open-webui-shell` | `open-webui:8080` |
| Agentgateway | `agentgateway-shell` | `agentgateway:4001` |
| Grafana | `grafana-shell` | `grafana:3000` |
| Prometheus | `prometheus-shell` | `prometheus:9090` |

Die Shell verändert ausschließlich HTML und liefert statische
`company-shell.js`-, `company-theme.css`- und Launcher-Assets aus. APIs,
Downloads und WebSockets werden transparent weitergereicht. Nach einem
Upstream-Update sind Login, Navigation, Upload/Download und WebSockets im
jeweiligen System zu prüfen. `python3 scripts/validate_app_shell.py` erkennt
fehlende Shells, versehentlich veröffentlichte Upstream-Ports und fehlende
Theme-Injektionen.

## Passwörter und Secrets

Die Defaults sind nur für `localhost`. Für jede geteilte oder produktionsnahe
Umgebung:

1. zufällige, lange Werte erzeugen,
2. Secret-Manager bzw. Docker-Secrets verwenden,
3. keine Secret-Werte in Logs oder Screenshots aufnehmen,
4. Rotation und Notfallentzug dokumentieren.

`AUTH_MODE=oidc` darf außerhalb von `localhost` nur zusammen mit HTTPS,
`AUTH_COOKIE_SECURE=true`, einem zufälligen `AUTH_SESSION_SECRET` und exakten
Redirect-URIs aktiviert werden. Details stehen unter
[Keycloak, Rollen und SSO](../interfaces/iam-sso.md).

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
