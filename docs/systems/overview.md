# Systemübersicht

| System | Technologie | Lizenz | Profil | Port | Doku |
|---|---|---|---|---:|---|
| FLOWPORTAL / FLOWMANAGE | Python, FastAPI | MIT | Standard | 8088 | [Benutzer](../tools/user/portal.md) · [Demo](../user-guides/presentation.md) · [Admin](../tools/admin/portal.md) |
| FLOWWORK / Requirements | HTML/JS, FastAPI | MIT | Standard | 8088 `/work` | [Benutzer](../user-guides/flowwork.md) · [Schnittstelle](../interfaces/redmine-requirements.md) |
| FLOWQ / Wareneingangsprüfung | HTML/JS, FastAPI | MIT | Standard | 8088 `/quality` | [Benutzer](../user-guides/quality.md) · [Messgeräte/API](../interfaces/quality-measurement.md) |
| FLOWTASK / Redmine | Ruby on Rails | GPLv2 | work/full | 8011 | [Benutzer](../user-guides/flowwork.md) · [Admin](../tools/admin/redmine.md) |
| FLOWHR / Personalprozesse | HTML/JS, FastAPI | MIT | Standard | 8088 `/hr` | [Benutzer](../tools/user/flowhr.md) · [Admin](../tools/admin/flowhr.md) · [Recruiting/Payroll](../interfaces/hr-dms-payroll.md) |
| FLOWSPACE / Desksharing | HTML/JS, FastAPI | MIT | Standard | 8088 `/desksharing` | [Benutzer](../user-guides/desksharing.md) · [IAM/SSO](../interfaces/iam-sso.md) |
| FLOWFIN / Management & Finance | HTML/JS, FastAPI | MIT | Standard | 8088 `/finance` | [Benutzer](../user-guides/finance.md) · [Reporting/API](../interfaces/finance-reporting.md) |
| ERPNext-MCP | Python, MCP SDK | MIT | Standard | 8090 | [Benutzer](../tools/user/mcp.md) · [Admin](../tools/admin/mcp.md) |
| DMS-MCP | Python, MCP SDK | MIT | full | 8091 | [Benutzer](../tools/user/mcp.md) · [Admin](../tools/admin/mcp.md) |
| Prozess-Wiki-MCP | Python, MCP SDK | MIT | Standard | 8092 | [Benutzer](../tools/user/mcp.md) · [Admin](../tools/admin/mcp.md) |
| FLOWDOCS / Prozess-Wiki | MkDocs Material | MIT | Standard | 8001 | [Benutzer](../tools/user/mkdocs.md) · [Admin](../tools/admin/mkdocs.md) |
| PostgreSQL + pgvector | PostgreSQL/C | PostgreSQL | Standard | intern | [Benutzer](../tools/user/postgresql.md) · [Admin](../tools/admin/postgresql.md) |
| FLOWERP / ERPNext/Frappe | Python | GPLv3/MIT | full | 8081 | [Benutzer](../tools/user/erpnext.md) · [Admin](../tools/admin/erpnext.md) |
| FLOWDOC / Paperless-ngx | Python/Django | GPLv3 | full | 8010 | [Benutzer](../tools/user/paperless.md) · [Admin](../tools/admin/paperless.md) |
| FLOWID / Keycloak | Java | Apache-2.0 | iam | 8082 | [Benutzer](../tools/user/keycloak.md) · [Admin](../tools/admin/keycloak.md) |
| Ollama | Go | MIT | ai | 11434 | [Benutzer](../tools/user/ollama.md) · [Admin](../tools/admin/ollama.md) |
| FLOWAI / Open WebUI | Python/TypeScript | Open WebUI License | webui | 3001 | [Benutzer](../tools/user/open-webui.md) · [Admin](../tools/admin/open-webui.md) |
| FLOWGATE / Agentgateway | Rust/TypeScript | Apache-2.0 | ai-gateway, webui | 4001 (Admin-UI) | [Admin](../tools/admin/agentgateway.md) |
| FLOWOPS / Prometheus | Go | Apache-2.0 | ops | 9090 | [Benutzer](../tools/user/prometheus.md) · [Admin](../tools/admin/prometheus.md) |
| FLOWINSIGHT / Grafana | Go/TypeScript | AGPLv3 | ops | 3000 | [Benutzer](../tools/user/grafana.md) · [Admin](../tools/admin/grafana.md) |
| Docker Compose | Go | Apache-2.0 | Laufzeit | - | [Benutzer](../tools/user/docker-compose.md) · [Admin](../tools/admin/docker-compose.md) |

MariaDB und Redis laufen als interne Abhängigkeiten von ERPNext und Paperless.
Sie sind in den jeweiligen Admin-Anleitungen abgedeckt und haben bewusst
keinen fachlichen Direktzugriff.

## Startkombinationen

```bash
make demo                                      # Portal + Wiki + pgvector
make full                                      # zusätzlich ERPNext + Paperless
make work                                      # FLOWWORK + Redmine
make sso                                       # Keycloak + erzwungenes Plattform-SSO
docker compose --profile ai up -d ollama      # lokales LLM
make ai-gateway                                # Agentgateway + Keycloak-SSO
make webui                                     # Web-Chat ueber FLOWGATE zu Host-Ollama
make mcp                                       # ERP-, DMS- und Wiki-MCP
docker compose --profile ops up -d             # Monitoring
make management-dashboard                      # Management-Reporting + Grafana
```

Versionen sind im Compose-File explizit fixiert. Updates erfolgen bewusst per
Pull Request mit Release-Note-Prüfung, Backup und Smoke-Test.
