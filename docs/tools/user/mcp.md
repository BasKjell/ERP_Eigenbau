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
| Welche Testdatentypen sind möglich? | `list_test_data_types` | MCP-Freigabekatalog |
| Mitarbeiter oder Arbeitsplätze anlegen | `create_test_data` | ERPNext |
| Lieferanten oder andere Listen importieren | `import_test_data` | ERPNext |
| eine fehlerhafte Testcharge entfernen | `rollback_test_data_batch` | ERPNext + MCP-Audit |

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
