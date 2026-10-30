# Grafana administrieren

## Start und Zugriff

```bash
docker compose --profile ops up -d prometheus grafana
docker compose logs --tail=150 grafana
```

Grafana ist unter `${GRAFANA_PORT:-3000}` erreichbar. Das Demo-Adminpasswort
muss vor geteilter Nutzung geändert werden; Self-Signup ist deaktiviert.

## Provisionierung

Datasources und Dashboards liegen unter `deployment/grafana/provisioning` und
werden als Code versioniert. Änderungen bevorzugt dort statt nur in der UI
vornehmen. Dashboard-Variablen dürfen keine Secrets enthalten.

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
