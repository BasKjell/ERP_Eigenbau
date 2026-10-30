# Prometheus administrieren

## Dienst und Prüfung

Prometheus läuft im Profil `ops` auf Port `9090`. Die Konfiguration ist
read-only aus `deployment/prometheus/prometheus.yml` eingebunden.

```bash
docker compose --profile ops up -d prometheus
curl --fail http://localhost:9090/-/ready
curl --fail http://localhost:9090/api/v1/targets
docker compose logs --tail=150 prometheus
```

## Targets und Regeln

Jedes Target braucht einen stabilen Jobnamen, sinnvolle Labels und einen
definierten Scrape-Zeitraum. Labels dürfen keine Kunden-, Seriennummern oder
andere hoch-kardinalen Fachwerte enthalten. Regeln werden versioniert,
syntaktisch geprüft und mit realistischen Ausfällen getestet.

## Aufbewahrung und Sicherheit

Das Volume `prometheus-data` enthält lokale Zeitreihen. Retention wird nach
Speicher, Diagnosebedarf und Datenschutz festgelegt. Für längere, hoch
verfügbare Aufbewahrung ist eine externe Architektur erforderlich. Die
Prometheus-UI ist im Zielbetrieb nicht ungeschützt öffentlich erreichbar.

Nach einem Update Targets, Regelstatus, Abfrageergebnisse, Grafana-Datasource
und einen kontrollierten Testalarm prüfen.
