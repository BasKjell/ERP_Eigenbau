# Model Context Protocol (MCP)

## Implementierter Umfang

Der lokale MCP-Server läuft unter `http://localhost:8090/mcp`. Er verwendet
den offiziellen Python-SDK und trennt quellenbasierte Leseabfragen von
kontrollierten Testdaten-Schreibaktionen.

| Werkzeug | Zweck |
|---|---|
| `list_production_orders` | aktive Fertigungsaufträge anzeigen |
| `list_late_purchase_orders` | verspätete Bestellungen anzeigen |
| `get_order_status` | Kundenauftragsstatus und Risiken anzeigen |
| `search_documents` | freigegebene Dokumentmetadaten suchen |
| `list_test_data_types` | erlaubte ERPNext-Typen, Felder, Defaults und Beispiele liefern |
| `create_test_data` | einzelne oder mehrere Testdatensätze vorschauen und anlegen |
| `import_test_data` | CSV- oder JSON-Inhalt vorschauen und importieren |
| `rollback_test_data_batch` | ausschließlich eine auditierte MCP-Testdatencharge löschen |

Der Katalog deckt unter anderem Mitarbeiter, Arbeitszeitnachweise,
Arbeitsplätze und -typen, Werkshallen, Arbeitsgänge, Lieferanten, Kunden,
Artikel, Lager, Abteilungen, Stellen, Niederlassungen, Projekte,
Tätigkeitsarten, Feiertagslisten und Mengeneinheiten ab. Freies SQL,
beliebige DocTypes und beliebige Felder sind nicht möglich.

```mermaid
flowchart LR
  U[Benutzer] --> H[MCP-fähiger LLM-Host]
  H --> C[Katalog oder Vorschau]
  C --> U
  U -->|explizite Bestätigung| W[freigegebenes Schreibwerkzeug]
  W --> V[Schema-, Mengen- und Feldprüfung]
  V --> E[ERPNext REST API]
  E --> A[Audit mit Batch-ID]
  A --> H
```

Ollama ist Modellserver, aber kein MCP-Host. Ein Desktop-Client, Codex, ein
Gateway oder eine andere MCP-fähige Anwendung verbindet das lokale Modell mit
`http://localhost:8090/mcp`. Das Management-Portal verwendet weiterhin seinen
eigenen, nur lesenden Assistentenpfad.

## Schreibvertrag

1. Das Modell ruft `list_test_data_types` auf und verwendet nur die gelieferten
   Feldnamen.
2. `create_test_data` oder `import_test_data` wird zunächst ohne
   `confirm` aufgerufen und liefert nur eine normalisierte Vorschau.
3. Erst nach Benutzerfreigabe wird derselbe Aufruf mit `confirm=true`
   wiederholt.
4. Bestehende Dokumente werden mit `on_duplicate=skip` übersprungen oder mit
   `on_duplicate=error` als Fehler behandelt; es gibt kein verstecktes Update.
5. Jeder Schreibaufruf erhält eine `batch_id`. Nur diese protokollierten
   Dokumente können über `rollback_test_data_batch` nach erneuter Vorschau und
   Bestätigung gelöscht werden.

Standardmäßig ist ein Import atomar: Scheitert ein Datensatz, versucht der
Server die im selben Aufruf bereits angelegten Dokumente wieder zu löschen.
ERPNext kann ein Rollback verhindern, wenn inzwischen abhängige Belege
existieren; solche Fehler stehen explizit in `rollback_errors`.

## Importformate

JSON besteht aus einer Liste von Objekten oder aus
`{"records": [...]}`. CSV verwendet in der ersten Zeile die ERPNext-Feldnamen.
Kindtabellen werden in einer CSV-Zelle als JSON-Liste übergeben, zum Beispiel
`time_logs` eines Arbeitszeitnachweises. Ein Aufruf ist auf 1 MB und
standardmäßig 100 Datensätze begrenzt.

## Sicherheitsgrenzen

- Schreibwerkzeuge benötigen `MCP_WRITE_ENABLED=true`, gültige serverseitige
  ERPNext-Zugangsdaten und `confirm=true`.
- Zugangsdaten werden nie an Modell oder MCP-Client zurückgegeben.
- Systemfelder wie `owner`, beliebige DocTypes, SQL und Shell bleiben gesperrt.
- Auditereignisse liegen im Volume unter `/data/mcp-write-audit.jsonl`.
- Die Administrator-Anmeldung ist nur für die lokale Demo vorgesehen. Vor
  jeder Netzfreigabe sind ein eingeschränktes Servicekonto, Tokenauthentifizierung,
  TLS, Keycloak/OAuth, Rollen, Rate Limits und Backups erforderlich.

## Start und Prüfung

```bash
docker compose --profile full up -d --build
docker compose up -d --build platform-mcp
docker compose logs --tail=150 platform-mcp
```

Ein Browser-GET ist kein vollständiger MCP-Aufruf. Der Funktionstest erfolgt
mit einem MCP-Client oder MCP Inspector über den Streamable-HTTP-Endpunkt.
