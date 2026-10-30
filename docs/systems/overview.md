# Systemübersicht

| System | Technologie | Lizenz | Profil | Port | Doku |
|---|---|---|---|---:|---|
| Management Portal / Integration | Python, FastAPI | MIT | Standard | 8088 | [Benutzer](../tools/user/portal.md) · [Admin](../tools/admin/portal.md) |
| ERPNext-MCP | Python, MCP SDK | MIT | Standard | 8090 | [Benutzer](../tools/user/mcp.md) · [Admin](../tools/admin/mcp.md) |
| DMS-MCP | Python, MCP SDK | MIT | full | 8091 | [Benutzer](../tools/user/mcp.md) · [Admin](../tools/admin/mcp.md) |
| Prozess-Wiki-MCP | Python, MCP SDK | MIT | Standard | 8092 | [Benutzer](../tools/user/mcp.md) · [Admin](../tools/admin/mcp.md) |
| Prozess-Wiki | MkDocs Material | MIT | Standard | 8001 | [Benutzer](../tools/user/mkdocs.md) · [Admin](../tools/admin/mkdocs.md) |
| PostgreSQL + pgvector | PostgreSQL/C | PostgreSQL | Standard | intern | [Benutzer](../tools/user/postgresql.md) · [Admin](../tools/admin/postgresql.md) |
| ERPNext/Frappe | Python | GPLv3/MIT | full | 8081 | [Benutzer](../tools/user/erpnext.md) · [Admin](../tools/admin/erpnext.md) |
| Paperless-ngx | Python/Django | GPLv3 | full | 8010 | [Benutzer](../tools/user/paperless.md) · [Admin](../tools/admin/paperless.md) |
| Keycloak | Java | Apache-2.0 | iam | 8082 | [Benutzer](../tools/user/keycloak.md) · [Admin](../tools/admin/keycloak.md) |
| Ollama | Go | MIT | ai | 11434 | [Benutzer](../tools/user/ollama.md) · [Admin](../tools/admin/ollama.md) |
| Open WebUI | Python/TypeScript | Open WebUI License | webui | 3001 | [Benutzer](../tools/user/open-webui.md) · [Admin](../tools/admin/open-webui.md) |
| Prometheus | Go | Apache-2.0 | ops | 9090 | [Benutzer](../tools/user/prometheus.md) · [Admin](../tools/admin/prometheus.md) |
| Grafana | Go/TypeScript | AGPLv3 | ops | 3000 | [Benutzer](../tools/user/grafana.md) · [Admin](../tools/admin/grafana.md) |
| Docker Compose | Go | Apache-2.0 | Laufzeit | - | [Benutzer](../tools/user/docker-compose.md) · [Admin](../tools/admin/docker-compose.md) |

MariaDB und Redis laufen als interne Abhängigkeiten von ERPNext und Paperless.
Sie sind in den jeweiligen Admin-Anleitungen abgedeckt und haben bewusst
keinen fachlichen Direktzugriff.

## Startkombinationen

```bash
make demo                                      # Portal + Wiki + pgvector
make full                                      # zusätzlich ERPNext + Paperless
docker compose --profile iam up -d keycloak   # SSO-Demo
docker compose --profile ai up -d ollama      # lokales LLM
make webui                                     # Web-Chat fuer Host-Ollama
make mcp                                       # ERP-, DMS- und Wiki-MCP
docker compose --profile ops up -d             # Monitoring
```

Versionen sind im Compose-File explizit fixiert. Updates erfolgen bewusst per
Pull Request mit Release-Note-Prüfung, Backup und Smoke-Test.
