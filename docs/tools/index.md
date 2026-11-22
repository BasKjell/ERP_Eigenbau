# Werkzeugkatalog und Dokumentationsmatrix

Diese Seite ist der verbindliche Einstieg für alle im PoC eingesetzten
Werkzeuge. Zu jedem Werkzeug gibt es eine getrennte Benutzer- und
Administrationsanleitung. Die Benutzeranleitungen verbinden den fachlichen
Unternehmensprozess direkt mit den nötigen Bedienschritten.

Der kompakte [Prozesskatalog je Anwendung](../user-guides/tool-process-catalog.md)
fasst für jede Oberfläche mindestens einen typischen Ablauf zusammen und
verlinkt von dort in die detaillierten Anleitungen.

| Werkzeug | Zweck im Prozess | Benutzeranleitung | Administration |
|---|---|---|---|
| FLOWMANAGE / FastAPI | Prozesscockpit und geführte 25-Schritte-Demo | [Management-Demo](../user-guides/presentation.md) | [Portal administrieren](admin/portal.md) |
| FLOWPORTAL | Rollenbasierter Einstieg und App-Launcher | [Portal und Launcher](../user-guides/company-portal.md) | [Portal administrieren](admin/portal.md) |
| FLOWWORK / FLOWTASK (Redmine) | Projekte, Tickets, Wiki, Requirements, Traceability und Baselines | [FLOWWORK benutzen](../user-guides/flowwork.md) | [Redmine administrieren](admin/redmine.md) |
| FLOWQ | Geführte Wareneingangsprüfung, Stichproben, Messmittel und ERP-/DMS-Übergabe | [FLOWQ benutzen](../user-guides/quality.md) | [Messgeräte- und ERP-Vertrag](../interfaces/quality-measurement.md) |
| FLOWHR | Anwesenheit, Zeitkonto, Abwesenheitskalender und Genehmigungen | [FLOWHR benutzen](user/flowhr.md) | [FLOWHR administrieren](admin/flowhr.md) |
| FLOWSPACE | Arbeitsplatz suchen, buchen, ein-/auschecken und verwalten | [Desksharing benutzen](../user-guides/desksharing.md) | [IAM- und Rollenbetrieb](admin/keycloak.md) |
| ERP-, DMS- und Wiki-MCP | standardisierte Fachabfragen und kontrollierte ERP-Testdaten | [MCP-Werkzeuge nutzen](user/mcp.md) | [MCP administrieren](admin/mcp.md) |
| FLOWERP (ERPNext / Frappe) | CRM, Verkauf, MRP, Einkauf, Fertigung, Lager, Finanzen | [ERPNext im Prozess](user/erpnext.md) | [ERPNext administrieren](admin/erpnext.md) |
| FLOWDOC (Paperless-ngx) | Dokumentenlenkung und Nachweise | [Dokumente im Prozess](user/paperless.md) | [Paperless administrieren](admin/paperless.md) |
| FLOWID (Keycloak) | Anmeldung, Rollen und SSO | [Anmelden und Rollen nutzen](user/keycloak.md) | [Keycloak administrieren](admin/keycloak.md) |
| Ollama / AI-Assistent | lokale, quellenbasierte Auskunft | [Assistent sicher nutzen](user/ollama.md) | [Ollama administrieren](admin/ollama.md) |
| FLOWAI (Open WebUI) | lokale Chat-Oberfläche und MCP-Host für Ollama | [Open WebUI nutzen](user/open-webui.md) | [Open WebUI administrieren](admin/open-webui.md) |
| FLOWGATE (Agentgateway) | zentrales Qwen-Routing, virtuelle Schlüssel, Modellrichtlinien und SSO-geschützte Administration | [Prozesskatalog](../user-guides/tool-process-catalog.md) | [FLOWGATE administrieren](admin/agentgateway.md) |
| FLOWINSIGHT (Grafana) | Betriebs- und Prozessübersichten | [Dashboards nutzen](user/grafana.md) | [Grafana administrieren](admin/grafana.md) |
| FLOWOPS (Prometheus) | technische Metriken und Alarmgrundlage | [Metriken richtig einordnen](user/prometheus.md) | [Prometheus administrieren](admin/prometheus.md) |
| PostgreSQL / pgvector | Portalzustand und spätere Vektorsuche | [Datenzugriff und Datenfehler](user/postgresql.md) | [PostgreSQL administrieren](admin/postgresql.md) |
| FLOWDOCS (MkDocs Material) | Prozess-, Benutzer- und Admin-Wiki | [Wiki benutzen](user/mkdocs.md) | [Wiki administrieren](admin/mkdocs.md) |
| Docker Compose | reproduzierbarer lokaler Betrieb | [Demo-Stack bedienen](user/docker-compose.md) | [Stack administrieren](admin/docker-compose.md) |

## Mitgeführte Laufzeitkomponenten

MariaDB und Redis sind technische Abhängigkeiten von ERPNext bzw.
Paperless-ngx und haben keinen fachlichen Direktzugriff. Betrieb, Backup und
Störungsbehandlung sind deshalb in den Admin-Anleitungen von
[ERPNext](admin/erpnext.md) und [Paperless](admin/paperless.md) enthalten. Für
Benutzer gilt: keine Datenbank- oder Queue-Zugriffe; Korrekturen erfolgen immer
über die jeweilige Fachanwendung.

## Dokumentationsregel

Eine Änderung an einem Werkzeug ist erst fertig, wenn gleichzeitig

1. die betroffene Prozessbeschreibung,
2. die Benutzeranleitung,
3. die Administrationsanleitung und
4. die Schnittstellen- oder Architekturseite

aktualisiert und mit `make validate` geprüft wurden.
