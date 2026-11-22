# Paperless-ngx-Schnittstelle

## Suchvertrag

Das Portal sucht Dokumente nicht per Dateipfad, sondern über die
Paperless-REST-API. Standardabfrage im PoC:

```http
GET /api/documents/?query=SCU-100
Authorization: Token <service-token>
```

Die lokale Integrations-API kapselt das unter:

```http
GET /api/documents/search?q=SCU-100
```

Für lokale Assistenten steht derselbe read-only Zugriff als Streamable-HTTP-MCP
unter `http://localhost:8091/mcp` bereit. Open WebUI verwendet intern
`http://dms-mcp:8091/mcp`. Der Server kann suchen, einzelne Metadaten lesen,
neue Dokumente auflisten und Tags/Dokumenttypen/Korrespondenten abfragen.

## Semantische Suche in pgvector

`dms-vector-seed` liest in der Demo maximal 200 Paperless-Dokumente, zerlegt
Titel und OCR-Inhalt in begrenzte Textblöcke und speichert lokale
768-dimensionale Einbettungen in `demo-db.knowledge_chunks`. Es findet dadurch
auch inhaltlich ähnliche Dokumente, wenn die Suchfrage nicht exakt dieselben
Wörter wie der Titel verwendet. Die Quelldatei bleibt ausschließlich in
Paperless.

```bash
make dms-vector-index
```

FLOWAI verwendet dafür `search_dms_documents_semantic`. Exakte Nummern,
Seriennummern und Titel werden weiterhin mit `search_dms_documents` gesucht.
Neue oder geänderte Dokumente werden über `refresh_dms_vector_index` oder das
Make-Ziel neu indiziert. Jeder Treffer enthält einen klickbaren Link zur
Paperless-Detailseite.

Der Demoindex benutzt einen vollständig lokalen, deterministischen
Feature-Encoder (`flow-hash-de-768-v1`) und benötigt kein Cloud-Modell. Für
den Livebetrieb können Einbettungen aus einem freigegebenen lokalen Modell
ergänzt werden; Modellname, Dimension, Chunking und Neuindizierung müssen dann
versioniert zusammenpassen.

## Metadatenkonvention

| Information | Paperless-Abbildung | Beispiel |
|---|---|---|
| Dokumenttyp | document_type | Prüfplan |
| Produkt | tag | SCU-100 |
| Revision | tag/custom field | Revision-C |
| Auftrag | tag/custom field | SO-4711 |
| Fertigungsauftrag | tag/custom field | WO-2027-0042 |
| Seriennummer | custom field | SN-10004 |
| Charge | custom field | BE-24117 |
| Meilenstein | custom field | Kundenabnahme |
| Lieferobjekt | custom field | Abnahmeunterlagen |
| Baseline-Version | custom field | BL-01 |
| Baseline-Termin | custom field (date) | 2026-11-15 |
| aktueller Liefertermin | custom field (date) | 2026-11-18 |
| Forecast-Termin | custom field (date) | 2026-11-22 |
| tatsächliche Lieferung | custom field (date) | 2026-11-19 |
| Fortschritt | custom field (integer) | 40 |

## Read-only Reportingvertrag für Grafana

Der Seed `paperless-reporting-seed` erzeugt in der Paperless-PostgreSQL-
Datenbank die View `reporting.dms_document_schedule`. Sie verbindet
Dokumentstammdaten, DMS-Status-Tags und die terminrelevanten Custom-Fields und
liefert zusätzlich `schedule_status`, `days_to_due`,
`baseline_variance_days`, `forecast_variance_days`, `delivered` und `overdue`.

Die technische Rolle `grafana_reader` besitzt `CONNECT`, Schema-`USAGE` und
`SELECT` ausschließlich auf dieser View. Zugriffe auf Tabellen im Schema
`public`, OCR-Inhalte und Dokumentbinärdaten sind entzogen. Der Vertrag ist
bewusst nur lesend; Terminänderungen erfolgen über die Paperless-API oder den
Webclient.

Die View bildet Paperless-Objektberechtigungen nicht benutzerspezifisch ab.
Deshalb muss der Grafana-Zugriff im Livebetrieb zusätzlich nach Projekt oder
Managementrolle begrenzt werden; für fein granulare Rechte ist ein
authentifizierter API-Proxy vorzuziehen.

## Governance- und Berechtigungsvertrag

Rollen, Custom Fields, Projekt-Tags, Ablagepfade und Workflows werden
deklarativ aus `deployment/paperless/governance.json` über die Paperless-API
angelegt. Der administrative Seed läuft getrennt vom read-only DMS-MCP und
wird mit `make seed-dms` wiederholt.

Globale Funktionsrechte allein reichen nicht. Dokumente erhalten zusätzlich
objektbezogene `view`- und `change`-Gruppen. Ein Benutzer benötigt daher eine
Funktionsrolle und eine passende Projektgruppe. Der DMS-MCP und damit auch der
Vektorindex erben exakt die Sichtbarkeit ihres Servicekontos; im Livebetrieb
darf das kein Admin- oder Superuserkonto sein. Eine Mehrbenutzerlösung muss
Gruppen-/Projekt-ACLs bereits vor der Indizierung filtern oder einen getrennten
Index je zulässigem Sicherheitsbereich nutzen.

Für eine Projektvorlage erzeugt der Seed:

- vier Zugriffsgruppen für Lesen, Bearbeiten, Prüfen und Freigeben,
- Projekt-Tag und Storage Path,
- eine Klassifizierungsregel für neue Dokumente,
- Statusübergänge inklusive Rechteentzug und Schutz vor direkter Freigabe.

Personalunterlagen verwenden bewusst keine Projektgruppen. Zwei geschützte
Bereiche klassifizieren Dateimuster und setzen exklusive Objekt-ACLs:

| Bereich | Objektgruppe | Beispiele |
|---|---|---|
| HR-Recruiting | `DMS-Bereich-HR-Recruiting` | Bewerbung, Lebenslauf, Arbeitsvertrag |
| HR-Payroll | `DMS-Bereich-HR-Payroll` | Entgelt-/Lohnabrechnung |

Nach der Klassifizierung wird `DMS-Eingang` entzogen und
`Vertraulich/Personal` gesetzt. FLOWHR nutzt die Paperless-Upload-API für
explizite Bewerber- und Payroll-Aktionen; der allgemeine DMS-MCP bleibt
read-only. Details stehen unter
[Recruiting, Payroll, DMS und ERP](hr-dms-payroll.md).

Die API-Importreihenfolge lautet: Gruppen → Metadaten → Projektobjekte →
Workflows → Dokumente → Objektberechtigungen → fachliche Sichtbarkeitsprobe.
Ein Dokumentimport ohne abschließende ACL-Prüfung ist unvollständig.

## API-Zugang aktivieren

1. Technisches Paperless-Konto mit minimalen Leserechten anlegen.
2. API-Token erzeugen.
3. `PAPERLESS_API_TOKEN` ausschließlich als Secret setzen.
4. Integration unter `/api/integrations` prüfen.
5. Suche und Berechtigungsgrenzen mit einem erlaubten und einem unerlaubten
   Dokument testen.

## Verfügbarkeit

Fällt Paperless aus, bleiben Auftrags- und Fertigungsdaten verfügbar. Ein
Arbeitsgang, der zwingend eine freigegebene Arbeitsunterlage benötigt, darf
jedoch nicht neu gestartet werden, solange die gültige Revision nicht sicher
nachgewiesen werden kann.
