# Demodaten vollständig über APIs verwalten

Zwei getrennte Host-Skripte verwalten den reproduzierbaren Demodatenbestand,
ohne auf Anwendungsdatenbanken oder Docker-Volumes zuzugreifen:

- `scripts/setup_demo_data.py` legt deklarierte Daten idempotent an oder
  aktualisiert sie.
- `scripts/delete_demo_data.py` löscht ausschließlich Datensätze, deren exakte
  Kennungen in den Repository-Manifesten stehen.

## Voraussetzungen

Die Zielanwendungen müssen bereits installiert und erreichbar sein. Das
Setup-Skript übernimmt keine Datenbankmigration und keine Erstinstallation. Die
Host-URLs und Zugangsdaten kommen aus `.env`; Ausgangspunkt ist
`.env.example`.

```bash
docker compose --profile full --profile work --profile iam up -d
make demo-data-setup
```

Ein einzelnes System lässt sich gezielt synchronisieren:

```bash
python3 scripts/setup_demo_data.py --systems platform,redmine
python3 scripts/setup_demo_data.py --systems keycloak,paperless,erpnext
```

Der Setup-Lauf ist wiederholbar. Er sucht vor dem Schreiben nach stabilen
Schlüsseln und aktualisiert bestehende Demoobjekte, statt Duplikate anzulegen.

## Sicher löschen

Ohne die exakte Bestätigung arbeitet das Löschskript automatisch als
Vorschau. Dadurch führt ein versehentlicher Aufruf zu keiner Änderung.

```bash
make demo-data-delete-preview
make demo-data-delete CONFIRM=DELETE-DEMO-DATA
```

Auch das Cleanup kann auf einzelne Systeme begrenzt werden:

```bash
python3 scripts/delete_demo_data.py \
  --systems redmine,paperless \
  --confirm DELETE-DEMO-DATA
```

Das Skript verwendet keine Präfix- oder Wildcard-Löschung für beliebige
Geschäftsdaten. Keycloak-Benutzer, Redmine-Projekte, Paperless-Dokumente und
ERPNext-Stammsätze werden mit den exakt deklarierten Kennungen verglichen.

## Abgedeckte Systeme

| System | Setup über API | Cleanup über API | Datenquelle |
|---|---|---|---|
| Unternehmensplattform, MES, HR, Desksharing, FLOWWORK | `POST /api/demo/reset` | `POST /api/demo/purge` | `scenario.json` |
| Keycloak | Admin REST / Partial Import | Admin REST / Benutzer-ID | `deployment/keycloak/realm.json` |
| ERPNext | Frappe Resource REST | Frappe Resource REST | `deployment/erpnext/demo_api_records.json` |
| Redmine | Projects, Issues und Wiki REST | Projects REST | `deployment/redmine/demo_api.json` |
| Paperless-ngx | Governance- und Upload-REST | Documents/Governance REST | `governance.json`, `output/pdf` |
| Grafana | keine eigenen Geschäftsdaten | keine | liest DMS- und Management-Reporting-Snapshots |
| Prometheus | keine Demostammdaten | keine | Laufzeitmetriken |

ERPNext erhält aktuell 90 exakt deklarierte Datensätze: unter anderem acht
Kunden, sechs Lieferanten, 14 Artikel, zehn Projekte, acht Arbeitsplätze, zehn
Testmitarbeiter und elf Opportunities mit erwarteten Abschlüssen von 2027 bis
2031. Hinzu kommen Zahlungs- und Lieferbedingungen sowie 15 Lagerbereiche.
Der Plattform-Seed enthält zusätzlich den vollständigen ausführbaren Auftrags-,
MES-, HR- und Desksharing-Demoprozess.

Die Grafana-Geschäftsdaten werden nicht direkt in Grafana importiert. Sie
liegen als reproduzierbarer, read-only Reporting-Snapshot in PostgreSQL und
werden separat aktiviert:

```bash
make management-dashboard
```

Der Snapshot umfasst neun Auftrags-/Forecastzeilen, sechs aktive
Fertigungsaufträge mit 30 Arbeitsgängen und 20 CRM-Opportunities über die Jahre
2027 bis 2031. Diese Trennung hält das API-only-Lifecycle der Fachsysteme ein;
im Livebetrieb ersetzt ein versionierter API-ETL die statischen Inserts.

## Sicherheitsmodell

Für die beiden Plattform-Lifecycle-Endpunkte gibt es einen eigenen Header
`X-Demo-Admin-Token`. Er ist ausschließlich auf `/api/demo/reset` und
`/api/demo/purge` gültig und kann keine Fach- oder Benutzer-APIs aufrufen. Der
Wert steht in `PLATFORM_DEMO_ADMIN_TOKEN` und muss außerhalb der lokalen Demo
geändert und als Secret bereitgestellt werden.

Die anderen Systeme verwenden ihre normalen administrativen APIs:

- Keycloak Admin-Token aus dem Master-Realm,
- ERPNext API-Key/Secret oder Administrator-Sitzung,
- Paperless API-Token oder Administrator-Sitzung,
- Redmine `X-Redmine-API-Key`.

Kennwörter und Token werden weder in den Ergebnisbericht noch in Logmeldungen
geschrieben.

## Manifeste und Erweiterung

Neue Demodaten werden nur über folgende deklarative Quellen ergänzt:

- `services/platform_api/seed/scenario.json`,
- `deployment/keycloak/realm.json`,
- `deployment/erpnext/demo_api_records.json`,
- `deployment/redmine/demo_api.json`,
- `deployment/paperless/governance.json`.

Jeder neue Datensatz benötigt einen stabilen fachlichen Schlüssel. Beim
Cleanup ist die umgekehrte Abhängigkeitsreihenfolge einzuhalten: zuerst Belege
und Dokumente, anschließend Stammdaten und zuletzt übergeordnete Strukturen.
Felder, die ERPNext nach ersten Buchungen sperrt, werden im betreffenden
Manifestdatensatz über `update_omit` ausschließlich beim Aktualisieren
ausgelassen; beim erstmaligen Anlegen bleiben sie vollständig gesetzt.
