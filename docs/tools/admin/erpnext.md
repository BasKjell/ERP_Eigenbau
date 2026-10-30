# ERPNext / Frappe administrieren

## Komponenten

Das Profil `full` umfasst Frontend, Backend, WebSocket, Scheduler, kurze und
lange Worker, Site-Erstellung, MariaDB sowie getrennte Redis-Dienste für Cache
und Queue. Benutzer greifen nur über `erpnext-frontend` auf Port
`${ERPNEXT_PORT:-8081}` zu.

## Erststart, Seed und Diagnose

```bash
docker compose --profile full up -d
docker compose ps -a
docker compose logs --tail=200 erpnext-create-site
docker compose logs --tail=200 erpnext-seed
docker compose logs --tail=200 erpnext-backend erpnext-queue-short
```

`erpnext-create-site` muss erfolgreich beendet sein. Ein 502 während der
Erstinitialisierung ist erst dann ein Fehler, wenn Backend und Site-Erstellung
bereit sein müssten. `erpnext-seed` muss mit Exitcode 0 enden. Er kann ohne
Duplikate erneut ausgeführt werden:

```bash
docker compose --profile full run --rm erpnext-seed
```

Das Skript liegt unter `deployment/erpnext/seed_demo.py` und liest den gleichen
versionierten Szenariodatensatz wie das Management-Portal. Es ergänzt drei
weitere Fertigungsprodukte, drei eingereichte Work Orders und
Beispielbewegungen mit eindeutigen `ERP-EIGENBAU-DEMO`-Markern. Vorhandene
Stammdaten werden nicht überschrieben; vorhandene Work Orders und bereits
markierte oder verknüpfte Lagerbewegungen werden übersprungen.

Eine erneute Ausführung muss `Created: 0` für die Fachobjekte melden. Die
Lagerbuchungen sind echte, eingereichte Stock Entries und werden deshalb nicht
durch einen Portal-Reset gelöscht.

## Fachkonfiguration

1. Firma, Geschäftsjahr, Währung und Kontenrahmen festlegen.
2. Rollen für Vertrieb, Planung, Einkauf, Lager, Produktion, Qualität,
   Versand und Finanzen nach Minimalprinzip konfigurieren.
3. Nummernkreise, Freigabeworkflows und Änderungsrechte definieren.
4. Artikel, BOM, Routing, Workstations, Lager und Qualitätsvorlagen
   versioniert importieren.
5. API-Benutzer getrennt von Personen anlegen und nur nötige DocTypes
   freigeben.

## MariaDB, Redis und Backup

MariaDB (`erpnext-db-data-v16`) enthält die Fachbelege;
`erpnext-sites-v16` enthält Site-Dateien. Beides muss konsistent gesichert
werden. Redis Cache ist
rekonstruierbar, Queue-Daten und laufende Jobs müssen bei Wiederherstellung
bewusst behandelt werden. Ein Restore wird in einem isolierten Stack getestet,
bevor DNS oder Integrationen umgeschaltet werden.

## Update und Abnahme

- Release Notes und Frappe-/ERPNext-Kompatibilität prüfen.
- Datenbank und Sites sichern, Migrationskopie erstellen.
- `bench migrate` nur im Testklon ausführen.
- Belegkette von Opportunity bis Sales Invoice sowie Rechte testen.
- Worker, Scheduler, WebSocket, E-Mail und API-Integration prüfen.
- Rollback-Zeitpunkt und unverarbeitete Queue-Jobs dokumentieren.
