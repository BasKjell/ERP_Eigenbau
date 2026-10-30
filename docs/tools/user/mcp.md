# MCP-Werkzeuge im Prozess nutzen

MCP verbindet einen lokalen Assistenten mit eng freigegebenen Fachfunktionen.
Für reine Statusfragen verwendet der Assistent die Lesewerkzeuge. Für
ERPNext-Testdaten gilt immer: Katalog prüfen, Vorschau kontrollieren und erst
danach ausdrücklich bestätigen.

## Unterstützte Vorgänge

| Wunsch | Werkzeug | Führendes System |
|---|---|---|
| Welche Aufträge sind in Produktion? | `list_production_orders` | ERPNext Work Order |
| Welche Bestellungen sind verspätet? | `list_late_purchase_orders` | ERPNext Purchase Order |
| Welche Produkte und Stücklisten gibt es? | `list_manufacturing_products`, `get_bom_details` | ERPNext BOM |
| Wie viel Bestand gibt es von Artikel X? | `get_inventory` | ERPNext Bin |
| Welche Materialien wurden heute verbaut? | `list_materials_consumed` | ERPNext Stock Entry |
| Welche Lagerbuchungen gab es für Artikel X? | `list_item_stock_movements` | ERPNext Stock Ledger Entry |
| Welche Prüfpläne oder Zeichnungen gibt es? | `search_dms_documents` | Paperless-ngx |
| Wie ist der dokumentierte Prozess? | `search_process_documentation` | Prozess-Wiki |
| Welche Testdatentypen sind möglich? | `list_test_data_types` | MCP-Freigabekatalog |
| Mitarbeiter oder Arbeitsplätze anlegen | `create_test_data` | ERPNext |
| Lieferanten oder andere Listen importieren | `import_test_data` | ERPNext |
| eine fehlerhafte Testcharge entfernen | `rollback_test_data_batch` | ERPNext + MCP-Audit |

## Bestände und Materialverbrauch fragen

Für zeitbezogene Fragen ein Datum im Format `YYYY-MM-DD` nennen. „Heute“ wird
vom MCP-Server auf das lokale Tagesdatum aufgelöst. Beispiele:

> Welche Materialien wurden heute in Fertigungsbuchungen verbaut? Gruppiere
> nach Artikel und nenne die zugehörigen Stock Entries.

> Zeige alle Lagerbuchungen für `CON-M12` vom 2026-10-30, einschließlich Lager,
> Mengenänderung, Restbestand und Belegnummer.

`list_materials_consumed` zählt ausschließlich gebuchte Fertigungs- und
Materialverbrauchsbelege; eine reine Umlagerung ins WIP-Lager gilt nicht als
Verbrauch. `list_item_stock_movements` zeigt dagegen die vollständige
Artikelspur einschließlich Zugang, Umlagerung, Verbrauch und Abstimmung.

## DMS und Prozess-Wiki

Der DMS-MCP liefert nur Paperless-Metadaten und kurze OCR-Treffer. Binärdateien
werden im Paperless-Webclient geöffnet. Der Wiki-MCP liest ausschließlich
Markdown-Seiten unter `docs/`. Bei Antworten soll das Modell Dokument-ID bzw.
Wiki-Pfad als Quelle nennen.

## Einzelne Testdaten anlegen

Beispielanweisung an den lokalen Assistenten:

> Zeige mir zuerst die Vorschau für einen Testlieferanten namens
> TEST-Motorenwerke GmbH aus Deutschland. Lege ihn noch nicht an.

Der Assistent ruft `create_test_data` mit `entity_type=suppliers` auf. Prüfe in
der Vorschau besonders Name, Gruppe, Land und Datensatzanzahl. Erst danach:

> Die Vorschau ist richtig. Bestätige genau diese Anlage.

Der erfolgreiche Aufruf liefert den ERPNext-Dokumentnamen und eine `batch_id`.

## Mitarbeiter und Arbeitszeiten

Für Mitarbeiter sind mindestens Vorname, Geschlecht, Geburtsdatum und
Eintrittsdatum erforderlich; die Demo-Firma wird ergänzt. Eine eindeutige
`employee_number` hilft, doppelte Imports zu erkennen. Benutzerkonten werden
nicht automatisch angelegt.

Arbeitszeiten werden als `timesheets` mit einer Kindliste `time_logs`
übergeben. Jeder Eintrag braucht Tätigkeitsart und Startzeit sowie Endzeit oder
Stundenzahl. Die referenzierte Tätigkeitsart und der Mitarbeiter müssen vorher
in ERPNext vorhanden sein.

```json
[
  {
    "employee": "HR-EMP-00001",
    "time_logs": [
      {
        "activity_type": "Fertigung",
        "from_time": "2026-10-30 08:00:00",
        "to_time": "2026-10-30 16:00:00",
        "description": "Test-Arbeitszeit"
      }
    ]
  }
]
```

## CSV oder JSON importieren

Bitte den Assistenten ausdrücklich um eine Vorschau, etwa:

> Importiere diese CSV als Lieferanten-Testdaten. Zeige nur die Vorschau und
> warte auf meine Bestätigung.

```csv
supplier_name,supplier_group,country
TEST-Antrieb Nord,All Supplier Groups,Germany
TEST-Sensorik West,All Supplier Groups,Germany
```

CSV-Spalten müssen den Feldnamen aus `list_test_data_types` entsprechen.
Komplexe Kindtabellen sind als JSON leichter zu importieren. Der Server
überspringt vorhandene Identitäten standardmäßig und verändert sie nicht.

## Testcharge zurücknehmen

1. `batch_id` aus dem Anlageergebnis kopieren.
2. `rollback_test_data_batch` zunächst ohne Bestätigung aufrufen lassen.
3. Dokumentliste kontrollieren.
4. Löschung ausdrücklich bestätigen.

Das Löschen kann scheitern, wenn inzwischen Belege auf die Testdaten verweisen.
Dann die Abhängigkeiten zuerst fachlich in ERPNext auflösen. Produktive oder
manuell angelegte Dokumente ohne passende Audit-Charge kann dieses Werkzeug
nicht löschen.

Weitere technische Details stehen unter
[MCP-Schnittstelle](../../interfaces/mcp.md).
