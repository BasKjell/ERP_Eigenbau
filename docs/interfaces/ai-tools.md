# AI Gateway und freigegebene Werkzeuge

## Grundsatz

Ein Modell erhält weder direkten Datenbankzugriff noch freie ERPNext-REST-
Pfade. Es kann ausschließlich serverseitig implementierte Fachwerkzeuge
aufrufen. Lesen, Schreiben und Freigabe bleiben getrennt.

## Modell-Gateway

FLOWAI ruft lokale Modelle ausschließlich über FLOWGATE auf:

```text
Open WebUI → OpenAI-kompatible API → Agentgateway → Ollama → Qwen
```

Agentgateway ist unter Apache-2.0 lizenziert. Der LLM-Port ist nur im internen
Compose-Netz erreichbar. Eine strikte virtuelle Schlüsselrichtlinie erlaubt
dem FLOWAI-Dienstkonto ausschließlich `qwen3:8b` und
`qwen3-coder:30b`. Der direkte Ollama-Adapter in Open WebUI ist deaktiviert.

Die FLOWGATE-Administration unter <http://localhost:4001/ui/> verwendet einen
eigenen vertraulichen Keycloak-Client und prüft den `platform-admin`-Claim.
Dies ist von der Dienstidentität für Modellaufrufe getrennt. Der aktuelle PoC
ordnet Gateway-Verbrauch daher dem Dienst `open-webui`, noch nicht dem
einzelnen Chatbenutzer zu. Details und Live-Grenzen stehen in der
[FLOWGATE-Adminanleitung](../tools/admin/agentgateway.md).

## Heute implementierter ERP-Werkzeugkatalog

| Werkzeug | Quelle | Modus | Bestätigung |
|---|---|---|---|
| `list_production_orders` | ERPNext Work Order | lesen | nein |
| `list_late_purchase_orders` | Portal-Szenario | lesen | nein |
| `get_order_status` | Portal-Szenario | lesen | nein |
| `search_documents` | Portal-Dokumentmetadaten | lesen | nein |
| `get_personal_daily_brief` | FLOWPORTAL und freigegebene Fachquellen | lesen | nein |
| `list_personal_ai_tools` | Rollen- und Werkzeugkatalog | lesen | nein |
| `get_personal_action_context` | persönliche Fokusaktion | lesen | nein |
| `list_manufacturing_products` | ERPNext BOM | lesen | nein |
| `get_bom_details` | ERPNext BOM | lesen | nein |
| `get_inventory` | ERPNext Bin | lesen | nein |
| `list_item_stock_movements` | ERPNext Stock Ledger | lesen | nein |
| `list_materials_consumed` | ERPNext Stock Entry | lesen | nein |
| `list_test_data_types` | MCP-Allowlist | lesen | nein |
| `create_test_data` | ERPNext | Testdaten anlegen | Vorschau + explizit |
| `import_test_data` | ERPNext | CSV/JSON-Testdaten anlegen | Vorschau + explizit |
| `rollback_test_data_batch` | ERPNext/Audit | eigene Batch löschen | Vorschau + explizit |

Fachliche Schreibaktionen wie Bestellanforderung, Belegfreigabe,
Qualitätsfreigabe, Fertigmeldung oder Rechnungsbuchung sind **nicht** als
AI-Werkzeug freigeschaltet. Das Modell kann sie erklären oder vorbereiten;
die berechtigte Person führt sie im Fachsystem aus.

Separate read-only Server bieten:

- Paperless: `search_dms_documents`, `get_dms_document`,
  `list_recent_dms_documents`, `list_dms_metadata`;
- Prozess-Wiki: `list_documentation_sections`,
  `search_process_documentation`, `get_documentation_context`,
  `get_documentation_page`.

## Antwortvertrag

Jede fachliche AI-Antwort enthält:

- verständliche Zusammenfassung,
- verwendete Werkzeuge und System-/Fachreferenzen,
- Unsicherheiten, fehlende Daten und Annahmen,
- bei einem Schreibvorschlag eine normalisierte Vorschau,
- keine erfundenen Freigaben, Seriennummern, Bestände oder Belegstatus.
- bei Wiki- und DMS-Antworten anklickbare Links ausschließlich aus den vom
  Werkzeug gelieferten `url`-Feldern.

## Schreibvertrag für Testdaten

1. Live-Katalog mit `list_test_data_types` lesen.
2. nur gelieferte Typen und Felder verwenden.
3. `create_test_data` bzw. `import_test_data` mit `confirm=false` aufrufen.
4. normalisierte Vorschau vom Benutzer/Data Owner freigeben lassen.
5. identischen Inhalt mit `confirm=true` schreiben.
6. Batch-ID und Ergebnis auditieren; Rollback ebenfalls zuerst vorschauen.

Details, Feldkatalog und Importwellen:
[Migration und API-Import](migration-api.md).

## Lokales Ollama und FLOWGATE aktivieren

```bash
ollama list
ollama pull qwen3:8b        # nur falls noch nicht vorhanden
make ai-gateway
make webui
```

Für direkte, quellenbasierte Antworten des Plattform-APIs werden
`AI_MODE=ollama`,
`OLLAMA_BASE_URL=http://host.docker.internal:11434` und
`OLLAMA_MODEL=qwen3:8b` in `.env` gesetzt. FLOWAI verwendet separat
`AGENTGATEWAY_OLLAMA_BASE_URL=http://host.docker.internal:11434/v1`. Alternativ
kann das Compose-Profil `ai` mit `http://ollama:11434/v1` verwendet werden.
Wenn Ollama nicht erreichbar ist, fällt nur die Plattform-Kurzantwort
kontrolliert auf den deterministischen Modus zurück; FLOWAI zeigt dagegen
einen Modellfehler aus FLOWGATE.

Die Werkzeugauswahl findet serverseitig statt. Nur das minimierte Ergebnis
wird an Ollama gegeben; Quellenchips werden aus Werkzeugergebnissen aufgebaut
und nicht vom Modell erfunden.
