# ERPNext / Frappe administrieren

## Komponenten

Das Profil `full` umfasst Frontend, Backend, WebSocket, Scheduler, kurze und
lange Worker, Site-Erstellung, MariaDB sowie getrennte Redis-Dienste für Cache
und Queue. `erpnext-shell` veröffentlicht Port `${ERPNEXT_PORT:-8081}` und
reicht alle ERP-Anfragen an das nur intern erreichbare `erpnext-frontend`
weiter. Bei HTML-Seiten ergänzt die Shell die gemeinsame linke
Unternehmensleiste mit eingebettetem 9-Punkte-App-Launcher und Farbsystem. Der
Aufruf von `/` wird direkt auf den ERPNext-Workspace `/desk/setup/home`
geleitet; der technische Frappe-Framework-Workspace bleibt für
Administratoren unter `/desk/build` verfügbar.

Für Socket.IO setzt die Shell den von Frappe erwarteten internen Host
`frontend`. Der Realtime-Dienst ruft die authentifizierende ERP-API über
`erpnext-backend:8000` auf. Damit bleiben Origin-Prüfung und Echtzeitfunktionen
gleichzeitig aktiv. REST-API und Dateien werden unverändert weitergereicht.

Die Site-Konfiguration `host_name` wird bei jedem Lauf von
`erpnext-create-site` auf `ERPNEXT_PUBLIC_URL` gesetzt. Das ist für den
Keycloak-Rücksprung wichtig: In der lokalen Demo muss die öffentliche Adresse
`http://localhost:8081` einschließlich Port lauten. Da das unveränderte
Frappe-Frontend den Port bei einzelnen internen Weiterleitungen entfernt,
korrigiert die äußere FLOWERP-Shell ausschließlich portlose
`http://localhost/...`-Antworten auf die tatsächlich aufgerufene Adresse.
Keycloak-Weiterleitungen auf Port 8082 werden dabei nicht verändert.

ERPNext/Frappe nutzt in dieser Version einen vertraulichen Social-Login-Client
mit Client Secret, sendet aber keinen PKCE-Code-Challenge-Parameter. Deshalb
darf der Keycloak-Client `erpnext` PKCE nicht erzwingen. Portal, Grafana und
die übrigen dafür ausgelegten OIDC-Clients verwenden weiterhin PKCE.

## Erststart, Seed und Diagnose

```bash
docker compose --profile full up -d
docker compose ps -a
docker compose logs --tail=200 erpnext-create-site
docker compose logs --tail=200 erpnext-seed
docker compose logs --tail=200 erpnext-backend erpnext-queue-short
docker compose logs --tail=100 erpnext-shell
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
- Loginseite und Desk über Port 8081 öffnen, Launcher oben links testen und
  Wechsel zu Portal, MES und DMS prüfen.
- Mit `demo01` eine Opportunity und die Work-Order-Liste öffnen. Der Rücksprung
  muss auf Port 8081 bleiben; eine Seite `No permission for Page` ist ein
  Abnahmefehler. Der Seed spiegelt deshalb die zusammengesetzte
  `platform-admin`-Rolle als `System Manager` plus ERP-Fachrollen.
- Rollback-Zeitpunkt und unverarbeitete Queue-Jobs dokumentieren.
