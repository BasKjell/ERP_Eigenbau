# Werkzeugkatalog und Dokumentationsmatrix

Diese Seite ist der verbindliche Einstieg für alle im PoC eingesetzten
Werkzeuge. Zu jedem Werkzeug gibt es eine getrennte Benutzer- und
Administrationsanleitung. Die Benutzeranleitungen verbinden den fachlichen
Unternehmensprozess direkt mit den nötigen Bedienschritten.

| Werkzeug | Zweck im Prozess | Benutzeranleitung | Administration |
|---|---|---|---|
| Management-Portal / FastAPI | Prozesscockpit, Demo, Integrations-API | [Portal bedienen](user/portal.md) | [Portal administrieren](admin/portal.md) |
| Plattform-MCP | standardisierte Read-only-Werkzeuge für Assistenten | [MCP-Werkzeuge nutzen](user/mcp.md) | [MCP administrieren](admin/mcp.md) |
| ERPNext / Frappe | CRM, Verkauf, MRP, Einkauf, Fertigung, Lager, Finanzen | [ERPNext im Prozess](user/erpnext.md) | [ERPNext administrieren](admin/erpnext.md) |
| Paperless-ngx | Dokumentenlenkung und Nachweise | [Dokumente im Prozess](user/paperless.md) | [Paperless administrieren](admin/paperless.md) |
| Keycloak | Anmeldung, Rollen und SSO | [Anmelden und Rollen nutzen](user/keycloak.md) | [Keycloak administrieren](admin/keycloak.md) |
| Ollama / AI-Assistent | lokale, quellenbasierte Auskunft | [Assistent sicher nutzen](user/ollama.md) | [Ollama administrieren](admin/ollama.md) |
| Grafana | Betriebs- und Prozessübersichten | [Dashboards nutzen](user/grafana.md) | [Grafana administrieren](admin/grafana.md) |
| Prometheus | technische Metriken und Alarmgrundlage | [Metriken richtig einordnen](user/prometheus.md) | [Prometheus administrieren](admin/prometheus.md) |
| PostgreSQL / pgvector | Portalzustand und spätere Vektorsuche | [Datenzugriff und Datenfehler](user/postgresql.md) | [PostgreSQL administrieren](admin/postgresql.md) |
| MkDocs Material | Prozess-, Benutzer- und Admin-Wiki | [Wiki benutzen](user/mkdocs.md) | [Wiki administrieren](admin/mkdocs.md) |
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
