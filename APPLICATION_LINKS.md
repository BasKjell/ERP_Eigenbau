# Lokale Anwendungslinks

Die folgenden Links verwenden die Standardports aus `.env.example`. Wenn ein
Port in der lokalen `.env` geändert wurde, muss der Link entsprechend angepasst
werden.

## Kernanwendungen

| Anwendung | Link | Start |
|---|---|---|
| FLOWPORTAL · Unternehmensportal | [http://localhost:8088](http://localhost:8088) | `make demo` |
| FLOWMANAGE · Management-Demo | [http://localhost:8088/management](http://localhost:8088/management) | `make demo` |
| FLOWMANAGE · geführter Rundgang | [Rundgang starten](http://localhost:8088/management?managementDemo=1&tourStep=0) | 25 Schritte mit Zurück/Weiter |
| FLOWFIN · Management und Finanzen | [http://localhost:8088/finance](http://localhost:8088/finance) | `make demo` |
| FLOWWORK · Tickets und Requirements | [http://localhost:8088/work](http://localhost:8088/work) | `make demo`, mit FLOWTASK `make work` |
| FLOWQ · Wareneingangsprüfung | [http://localhost:8088/quality](http://localhost:8088/quality) | `make demo` |
| FLOWTASK · Redmine | [http://localhost:8011](http://localhost:8011) | `make work` oder `make full` |
| FLOWMES · Shopfloor | [http://localhost:8088/mes](http://localhost:8088/mes) | `make demo` |
| FLOWHR · Personalprozesse | [http://localhost:8088/hr](http://localhost:8088/hr) | `make demo` |
| FLOWSPACE · Desksharing | [http://localhost:8088/desksharing](http://localhost:8088/desksharing) | `make demo` oder geschützt mit `make sso` |
| FLOWSPACE · Gebäudeplan und Kollegensuche | [Berlin-Demoplan öffnen](http://localhost:8088/desksharing?date=2026-11-05&site=BER&floor=EG&room=BER-EG-TEAM&colleague=Felix%20Hoffmann) | Raum, Platz und markierten Kollegenplatz demonstrieren |
| FLOWDOCS · Prozess-Wiki | [http://localhost:8001](http://localhost:8001) | `make demo` |
| FLOWERP · ERPNext | [http://localhost:8081](http://localhost:8081) | `make full` |
| FLOWDOC · Paperless-ngx | [http://localhost:8010](http://localhost:8010) | `make full` |
| FLOWAI · Open WebUI | [http://localhost:3001](http://localhost:3001) | `make full` oder `make webui` |
| FLOWGATE · Agentgateway | [http://localhost:4001/ui/](http://localhost:4001/ui/) | `make ai-gateway`, Adminzugriff über Keycloak |
| FLOWPORTAL · persönlicher KI-Arbeitsplatz | [Einkaufsbriefing öffnen](http://localhost:8088/?user_id=USR-006&date=2026-11-05) | Tagesaufgaben, Agenten und MCP-Werkzeuge je Rolle |
| FLOWMANAGE · Arbeitsplatz 2028 | [Management-Zielbild öffnen](http://localhost:8088/management#future-model) | Arbeitsteilung, Entscheidungs-Inbox, Agentenregister und Autonomiestufen |

## API und Betriebsstatus

| Endpunkt | Link | Zweck |
|---|---|---|
| FLOWAPI · API-Dokumentation | [http://localhost:8088/docs](http://localhost:8088/docs) | interaktive OpenAPI-Oberfläche |
| OpenAPI-Vertrag | [http://localhost:8088/openapi.json](http://localhost:8088/openapi.json) | maschinenlesbarer API-Vertrag |
| Liveness | [http://localhost:8088/health](http://localhost:8088/health) | prüft, ob die API antwortet |
| Readiness | [http://localhost:8088/ready](http://localhost:8088/ready) | prüft Daten, PDFs und optional ERP/DMS |
| Integrationsstatus | [http://localhost:8088/api/integrations](http://localhost:8088/api/integrations) | Status von ERPNext, Paperless und Redmine |
| Prometheus-Metriken der API | [http://localhost:8088/metrics](http://localhost:8088/metrics) | technische API-Metriken |

## MCP-Schnittstellen

Diese URLs sind für MCP-fähige Clients wie Open WebUI oder eine lokale KI
bestimmt; sie sind keine normalen Bedienoberflächen.

| MCP-Server | Link | Start |
|---|---|---|
| ERP-/Plattform-MCP | [http://localhost:8090/mcp](http://localhost:8090/mcp) | `make demo` oder `make mcp` |
| DMS-/Paperless-MCP | [http://localhost:8091/mcp](http://localhost:8091/mcp) | `make full`, danach `make mcp` |
| Prozess-Wiki-MCP | [http://localhost:8092/mcp](http://localhost:8092/mcp) | `make mcp` |

## Identität, KI und Monitoring

| Anwendung | Link | Start |
|---|---|---|
| FLOWID · Konto/SSO (Keycloak) | [http://localhost:8082/realms/open-manufacturing/account](http://localhost:8082/realms/open-manufacturing/account) | `make sso` |
| FLOWID · Administration | [http://localhost:8082/admin](http://localhost:8082/admin) | `make sso` |
| Ollama API | [http://localhost:11434/api/tags](http://localhost:11434/api/tags) | `docker compose --profile ai up -d ollama` oder Ollama auf dem Host |
| FLOWOPS · Prometheus | [http://localhost:9090](http://localhost:9090) | `docker compose --profile ops up -d` |
| Prometheus Readiness | [http://localhost:9090/-/ready](http://localhost:9090/-/ready) | Profil `ops` |
| FLOWINSIGHT · Grafana | [http://localhost:3000](http://localhost:3000) | `docker compose --profile ops up -d` |
| DMS-Dokumentenlieferplan | [http://localhost:3000/d/dms-document-deliveries/dms-e28093-dokumentenlieferplan](http://localhost:3000/d/dms-document-deliveries/dms-e28093-dokumentenlieferplan) | `make dms-dashboard` |
| Management – Executive Cockpit | [http://localhost:3000/d/management-executive](http://localhost:3000/d/management-executive) | `make management-dashboard` |
| Management – Fertigung & Arbeitsgänge | [http://localhost:3000/d/management-production-live](http://localhost:3000/d/management-production-live) | `make management-dashboard` |
| Management – CRM-Pipeline 2027–2031 | [http://localhost:3000/d/management-crm-pipeline](http://localhost:3000/d/management-crm-pipeline) | `make management-dashboard` |
| Management – Projekte & Cash | [http://localhost:3000/d/management-project-cash](http://localhost:3000/d/management-project-cash) | `make management-dashboard` |
| Management – Engineering & Qualität | [http://localhost:3000/d/management-innovation-quality](http://localhost:3000/d/management-innovation-quality) | `make management-dashboard` |

## Weitere interne Dienste

PostgreSQL/pgvector, MariaDB und Redis besitzen bewusst keine Browseroberfläche
und werden nur innerhalb des Docker-Netzwerks verwendet. Ihre Administration
ist im [Prozess-Wiki](http://localhost:8001) dokumentiert.

## Gesamten Stack starten

```bash
make full
docker compose --profile iam --profile ai --profile ai-gateway --profile ops up -d
make mcp
```

Den aktuellen Containerstatus zeigt:

```bash
docker compose --profile full --profile iam --profile ai --profile ai-gateway --profile ops ps -a
```
