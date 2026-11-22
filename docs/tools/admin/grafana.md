# Grafana administrieren

## Start und Zugriff

```bash
make dms-dashboard
make management-dashboard
docker compose logs --tail=150 grafana
```

Grafana ist unter `${GRAFANA_PORT:-3000}` über `grafana-shell` erreichbar;
der Upstream `grafana` besitzt keinen Hostport. Das Demo-Adminpasswort
muss vor geteilter Nutzung geändert werden; Self-Signup ist deaktiviert.

Mit `make sso` oder `make sso-all` ist Generic OAuth aktiviert. Grafana
leitet dann ohne zusätzlichen Grafana-Anmeldedialog zu Keycloak weiter und
legt beim ersten erfolgreichen Login ausschließlich berechtigte Konten an:

| Keycloak-Rolle | Grafana-Rolle |
|---|---|
| `platform-admin` | Grafana Server Admin |
| `grafana-viewer` | Viewer |
| keine der beiden Rollen | Anmeldung wird abgewiesen |

Für die lokale Demo kann `platform-admin` administrieren; `demo01` ist ein
geeignetes Viewer-Konto. Der lokale Grafana-Benutzer `admin` bleibt nur als
Notfallzugang bestehen. Sein Passwort kommt aus `GRAFANA_ADMIN_PASSWORD` und
soll nicht im normalen Benutzerbetrieb verwendet werden. Mit
`GRAFANA_DISABLE_LOGIN_FORM=true` kann die lokale Maske nach einem geprüften
Notfallzugang vollständig ausgeblendet werden.

`make dms-dashboard` aktualisiert zuerst die read-only Reporting-View in der
Paperless-Datenbank und startet danach Prometheus und Grafana. Nur technische
Dashboards können alternativ direkt mit `docker compose --profile ops up -d`
gestartet werden. Dabei `grafana-shell` und `prometheus-shell` mit starten.

## Provisionierung

Datasources und Dashboards liegen unter `deployment/grafana/provisioning` und
werden als Code versioniert. Änderungen bevorzugt dort statt nur in der UI
vornehmen. Dashboard-Variablen dürfen keine Secrets enthalten.

Der DMS-Lieferplan wird aus diesen Artefakten provisioniert:

| Artefakt | Funktion |
|---|---|
| `deployment/paperless/reporting.sql` | erzeugt View und eingeschränkte DB-Rolle |
| `deployment/paperless/apply_reporting.sh` | wendet SQL idempotent an und rotiert das Reporting-Passwort |
| `deployment/grafana/provisioning/datasources/paperless-reporting.yml` | bindet die View an Grafana an |
| `deployment/grafana/provisioning/dashboards/json/dms-document-deliveries.json` | definiert das Projekt-Dashboard |

Die View `reporting.dms_document_schedule` enthält nur Metadaten und abgeleitete
Terminwerte, keinen OCR-Text und keine Dokumentbinärdaten. Die Rolle
`grafana_reader` darf ausschließlich diese View lesen. Ihr Passwort kommt aus
`GRAFANA_PAPERLESS_DB_PASSWORD` und muss im Livebetrieb aus einem Secret-Store
kommen. Nach einer Rotation erneut `make dms-dashboard` ausführen und Grafana
neu starten.

Die Management-Dashboards lesen über die Infinity-Datenquelle `platform-live-api`
direkt aus der internen, token-geschützten FLOW-Live-API. Die API konsolidiert
FLOWFIN, FLOWMES und ERPNext nur lesend. Das ältere PostgreSQL-Modell bleibt als
Fallback und ausführbarer Datenvertrag bestehen:

| Artefakt | Funktion |
|---|---|
| `deployment/postgres/management_reporting.sql` | Reportingtabellen, Views, Seed-Snapshot und DB-Rolle |
| `deployment/postgres/apply_management_reporting.sh` | idempotente Anwendung und Passwortrotation |
| `deployment/grafana/provisioning/datasources/management-reporting.yml` | Grafana-Datenquelle `management-reporting` |
| `deployment/grafana/provisioning/datasources/platform-live-api.yml` | aktive Live-Datenquelle für alle Management-Dashboards |
| `management-executive.json` | Umsatz, Backlog, Marge, Risiken und Budget |
| `management-production-live.json` | aktive Fertigungsaufträge, aktueller Arbeitsgang und Arbeitsplatzlast |
| `management-crm-pipeline.json` | mehrjährige Brutto- und gewichtete Opportunity-Pipeline |
| `management-project-cash.json` | Projektprofitabilität, Cash und offene Posten |
| `management-innovation-quality.json` | F&E, Software, Qualität und Gewährleistung |

`REPORTING_API_TOKEN` authentifiziert ausschließlich Grafanas serverseitige
Lesezugriffe auf `/api/reporting/live`. Das Token darf nicht in Dashboard-JSON
oder im Browser erscheinen. `grafana_management_reader` darf zusätzlich
ausschließlich die freigegebenen Views und
Reportingtabellen lesen. Dazu gehören die abgeleiteten Views
`management_production_wip`, `management_workstation_load`,
`management_crm_pipeline` und `management_crm_pipeline_yearly`; direkte
Schreibrechte bestehen nicht. Das Passwort kommt aus
`GRAFANA_MANAGEMENT_DB_PASSWORD`. Mit `make test-management-reporting` werden
Kennzahlen und der verweigerte Zugriff auf `public.knowledge_chunks` geprüft.

Produktiv dürfen die Seed-Inserts nicht periodisch ausgeführt werden. Sie
werden durch einen versionierten ETL/ELT-Lauf ersetzt, der Quellreferenz,
Änderungszeit, Datenalter sowie Summen- und Mengenabstimmung protokolliert.

## Fachliche Datenquelle

Paperless bleibt die einzige Pflegeoberfläche. Die View extrahiert die
Custom-Fields Projekt, Meilenstein, Lieferobjekt, Verantwortung, Baseline,
Liefertermin, Forecast, Ist-Lieferung, Empfänger, Vertragskennzeichen,
Fortschritt und Terminnotiz. Der Terminstatus wird bei jeder Abfrage anhand des
aktuellen Tages neu berechnet.

Prüfung nach Änderung oder Update:

```bash
make seed-dms
make dms-dashboard
make test-dms-reporting
docker compose logs --tail=200 paperless-reporting-seed grafana
```

In Grafana unter **Connections → Data sources → Paperless
Dokumentenplanung** muss der Verbindungstest `Database Connection OK` ergeben.
Danach das Dashboard nach Projekt filtern und mindestens je einen gelieferten,
fälligen und gefährdeten Termin plausibilisieren.

## Berechtigungsgrenze

!!! warning "Paperless-ACL wird nicht automatisch auf Grafana übertragen"
    Die gemeinsame SQL-Datenquelle kennt nicht den angemeldeten
    Paperless-Benutzer. Jeder Grafana-Benutzer mit Zugriff auf dieses Dashboard
    kann daher alle Projekte sehen, die in der Reporting-View enthalten sind.
    Im PoC darf der Dashboard-Ordner nur für die zentrale Projektleitung und
    freigegebene Managementrollen sichtbar sein.

Für den Livebetrieb ist abhängig vom Schutzbedarf eine dieser Varianten
umzusetzen:

1. getrennte Views/Datenquellen und Grafana-Ordner je Mandant oder Projekt,
2. PostgreSQL Row-Level-Security mit getrennten technischen Identitäten oder
3. bevorzugt ein API-Proxy, der die Benutzeridentität übernimmt und die
   Paperless-Objektberechtigung vor jeder Abfrage erzwingt.

Vor der Freigabe ist ein negativer Test mit einem Fremdprojektkonto Pflicht.
Grafana-Viewer dürfen außerdem keine Explore-, SQL-Editor- oder
Datenquellen-Administrationsrechte erhalten.

## Rollen, Alarme und Betrieb

- Viewer, Editor und Admin trennen; SSO-Rollen im Zielbetrieb mappen.
- Dashboards nach Umgebung und Verantwortungsbereich organisieren.
- Jeder Alarm hat Schwellwert, Dauer, Verantwortlichen, Runbook und
  Eskalationsweg.
- Technische und fachliche Kennzahlen klar kennzeichnen.
- Zeitzone, Datenlücke und Abfragezeitraum sichtbar machen.

`grafana-data` sichert UI-Zustand, Benutzer und nicht provisionierte Objekte.
Zusätzlich müssen Provisionierungsdateien aus Git und externe Alert-Kanäle
gesichert werden. Nach Updates Login, Datasource, Dashboard und Testalarm
prüfen.
