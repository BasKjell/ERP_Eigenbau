# Redmine- und Requirements-Schnittstelle

## Systemgrenze

| Informationsobjekt | Führendes System | Schlüssel |
|---|---|---|
| Projekt, Ticket, Status, Termin, Zeitbuchung | Redmine | Projekt-ID / Issue-ID |
| Projekt-Wiki und Wiki-Version | Redmine | Projekt-Identifier / Seitentitel |
| Requirement, Version, Historie | FLOWWORK | `REQ-*` |
| Review, Teilnehmer, Kommentar, Signatur | FLOWWORK | `REV-*` / `CMT-*` |
| Itemtyp, eigenes Feld, Relationship-Regel | FLOWWORK | `TYPE-*` / `FLD-*` / `RULE-*` |
| Typisierte Beziehung / Suspect Link | FLOWWORK | `REL-*` |
| Testfall, Testplan, Testlauf | FLOWWORK | `TC-*` / `TP-*` / `RUN-*` |
| Risiko und Maßnahme | FLOWWORK | `RISK-*` |
| Requirements-Baseline | FLOWWORK | `BL-*` |
| Prüfbericht / freigegebenes Dokument | Paperless-ngx | DMS-Dokument-ID |
| Auftrag / Kommission | ERPNext | Auftrag / Projekt |

Redmine stellt stabile REST-Ressourcen für Projekte und Issues bereit. Wiki,
Relationen und mehrere Metadaten-Endpunkte sind laut offizieller
[Redmine-REST-Dokumentation](https://www.redmine.org/projects/redmine/wiki/Rest_api/)
noch als Alpha gekennzeichnet. Der Adapter kapselt deshalb Redmine-spezifische
Antworten und liefert dem Browser ein stabiles internes Modell.

## Konfiguration

```dotenv
REDMINE_BASE_URL=http://redmine:3000
REDMINE_PUBLIC_URL=http://localhost:8011
REDMINE_API_KEY=<geheimer-service-account-schluessel>
```

Die REST-API muss aktiviert sein. Authentifizierung erfolgt mit
`X-Redmine-API-Key`. Der Browser erhält den Schlüssel nie.

## FLOWWORK-API

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/api/work/dashboard` | Projekte, Issues, Wiki, Requirements und Kennzahlen |
| POST | `/api/work/issues` | Redmine-Ticket anlegen und optional verknüpfen |
| POST | `/api/work/requirements` | versioniertes Requirement anlegen |
| PATCH | `/api/work/requirements/{id}` | Inhalt, Status und Referenzen ändern |
| POST | `/api/work/baselines` | Requirement-Versionen einfrieren |
| GET | `/api/work/baselines/{id}/compare` | Baseline mit aktuellem Stand vergleichen |
| POST | `/api/work/reviews` | moderiertes Review-Paket starten |
| POST | `/api/work/reviews/{id}/comments` | Review-Kommentar und Erwähnungen speichern |
| POST | `/api/work/reviews/{id}/decisions` | Review abschließen, freigeben oder Änderungen fordern |
| POST | `/api/work/admin/item-types` | eigenen Itemtyp und Workflow anlegen |
| POST | `/api/work/admin/fields` | typisiertes eigenes Feld anlegen |
| POST | `/api/work/admin/relationship-types` | Beziehungstyp mit Vorwärts-/Rückwärtsname anlegen |
| POST | `/api/work/admin/relationship-rules` | erlaubte Beziehung und Coverage-Regel anlegen |
| POST | `/api/work/relationships` | typisierte Beziehung anlegen |
| POST | `/api/work/relationships/{id}/clear-suspect` | Änderungsfolge als bewertet markieren |
| POST | `/api/work/tests/cases` | versionierten Testfall anlegen und verknüpfen |
| POST | `/api/work/tests/plans` | Testplan und initialen Testlauf anlegen |
| POST | `/api/work/tests/runs/{run}/cases/{case}` | Test ausführen und Evidenz referenzieren |
| POST | `/api/work/risks` | Risiko bewerten und mit Requirements verknüpfen |
| POST | `/api/work/requirements/{id}/branch` | Requirement für eine Variante ableiten |
| GET | `/api/work/export?format=json|csv|reqif` | Datenpaket exportieren |
| POST | `/api/work/import` | FLOWWORK-JSON-Paket idempotent ergänzen |
| POST | `/api/work/reset` | FLOWWORK-Demodatensatz zurücksetzen |

Die OpenAPI-Spezifikation unter `/openapi.json` eignet sich als Vertrag für
eine KI-gestützte Migrationsplanung.

## Migration

1. Benutzer und Gruppen nach Keycloak übernehmen.
2. Redmine-Projekte samt Identifiern anlegen.
3. Wiki-Seiten importieren; Seitentitel stabil halten.
4. Tickets mit Alt-ID im Betreff oder Custom-Field importieren.
5. Itemtypen, eigene Felder, Beziehungstypen und Relationship-Regeln zuerst
   über das Admin-API übernehmen.
6. Requirements, Risiken und Testfälle importieren.
7. Typisierte Beziehungen und anschließend Reviews/Baselines übernehmen.
8. Ticket- und Wiki-Referenzen per PATCH ergänzen.
9. Coverage und Suspect Links prüfen, einen Export-/Import-Roundtrip ausführen
   und danach eine Migrationsbaseline erzeugen.

Der JSON-Austauschvertrag heißt `flowwork-interchange-1.0`. Der ReqIF-Export
bildet Requirements und Beziehungen ab; projektspezifische eigene Felder und
Workflows werden vollständig im JSON-Paket erhalten. Vor einem produktiven
ReqIF-Austausch mit Jama Connect, DOORS oder einem Lieferanten muss die
Interoperabilität mit den jeweiligen Importprofilen getestet werden.

Ein Batch-Importer muss Alt-ID, Ziel-ID, Prüfsumme, Importzeitpunkt, Ergebnis
und Fehlertext auditierbar protokollieren.

Ohne API-Key arbeitet FLOWWORK mit Demodaten. Ist ein Key konfiguriert,
Redmine aber nicht erreichbar, bleiben lokale Requirements und Baselines
lesbar; Ticket-Schreibaktionen brechen nachvollziehbar ab.
