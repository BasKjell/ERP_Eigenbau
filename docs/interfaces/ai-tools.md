# AI Gateway und freigegebene Tools

## Grundsatz

Das Modell erhält keinen direkten Datenbankzugriff. Es kann ausschließlich
fachliche Tools mit serverseitiger Rollenprüfung aufrufen.

## Tool-Katalog

| Tool | Quelle | Lesen/Schreiben | Bestätigung |
|---|---|---|---|
| `get_sales_order` | ERPNext | lesen | nein |
| `get_stock` | ERPNext | lesen | nein |
| `get_work_order` | MES/ERPNext | lesen | nein |
| `get_capacity` | ERPNext | lesen | nein |
| `search_documents` | Paperless | lesen | nein |
| `get_quality_incident` | MES | lesen | nein |
| `list_test_data_types` | MCP-Katalog | lesen | nein |
| `create_test_data` | ERPNext | Testdaten schreiben | Vorschau + immer |
| `import_test_data` | ERPNext | CSV/JSON-Testdaten schreiben | Vorschau + immer |
| `rollback_test_data_batch` | ERPNext/Audit | Testdaten löschen | Vorschau + immer |
| `create_purchase_request` | ERPNext | schreiben | immer |
| `release_work_order` | ERPNext | schreiben | immer + Rolle |

Im implementierten PoC sind die vier Lesewerkzeuge
`list_production_orders`, `list_late_purchase_orders`, `get_order_status` und
`search_documents` sowie die vier kontrollierten Testdatenwerkzeuge aktiv.
Fachliche Buchungen wie Bestellanforderung oder Fertigungsfreigabe bleiben
Zielbild und sind nicht freigeschaltet. Die Testdatenwerkzeuge aktualisieren
keine vorhandenen Dokumente und akzeptieren nur einen festen DocType- und
Feldkatalog.

## Antwortvertrag

Jede Antwort enthält:

- verständliche Zusammenfassung,
- Unsicherheit oder fehlende Daten,
- System und Fachreferenz der Quellen,
- bei Schreibvorschlägen eine explizite Bestätigung vor Ausführung.

## Lokales Ollama aktivieren

```bash
ollama list
ollama pull qwen3:8b        # nur falls noch nicht vorhanden
```

Für Ollama auf dem Mac werden `AI_MODE=ollama`,
`OLLAMA_BASE_URL=http://host.docker.internal:11434` und
`OLLAMA_MODEL=qwen3:8b` in `.env` gesetzt. Danach `platform-api` neu starten.
Alternativ kann das Compose-Profil `ai` mit der internen URL
`http://ollama:11434` verwendet werden. Wenn
Ollama nicht erreichbar ist, fällt der PoC kontrolliert auf die
deterministische, quellenbasierte Antwort zurück.

Die Werkzeugauswahl findet serverseitig statt. Nur das minimierte Ergebnis
wird an Ollama gegeben; Quellenchips werden nicht vom Modell erfunden, sondern
aus den Werkzeugergebnissen aufgebaut.
