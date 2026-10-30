# Plattform-MCP administrieren

## Dienste

| Merkmal | Wert |
|---|---|
| Compose-Service | `platform-mcp` / `dms-mcp` / `knowledge-mcp` |
| Transport | Streamable HTTP, stateless |
| Endpunkte | `8090` ERP, `8091` DMS, `8092` Wiki |
| SDK | offizieller Python MCP SDK 2.3.0 |
| Lesezugriff | feste ERPNext-, Paperless- und Wiki-Werkzeuge |
| Schreibzugriff | allowlisted ERPNext-Testdaten mit Vorschau und Bestätigung |
| Audit | `demo-state:/data/mcp-write-audit.jsonl` |

```bash
make mcp
docker compose --profile full ps platform-mcp dms-mcp knowledge-mcp
docker compose --profile full logs --tail=150 platform-mcp dms-mcp knowledge-mcp
```

## Konfiguration

| Variable | Zweck | Demo-Standard |
|---|---|---|
| `ERPNEXT_BASE_URL` | interne ERPNext-URL | `http://erpnext-frontend:8080` |
| `ERPNEXT_API_KEY/SECRET` | bevorzugte Tokenanmeldung | leer |
| `ERPNEXT_USERNAME` | lokale Sitzungsanmeldung | `Administrator` |
| `ERPNEXT_PASSWORD` | wird aus `ERPNEXT_ADMIN_PASSWORD` gesetzt | Demo-Passwort |
| `MCP_WRITE_ENABLED` | Schreibwerkzeuge global schalten | `true` |
| `MCP_MAX_WRITE_RECORDS` | Mengenlimit pro Aufruf | `100` |
| `MCP_DEFAULT_COMPANY` | Default für firmenbezogene Daten | Demo-Firma |
| `DMS_MCP_PORT` | lokaler Paperless-MCP-Port | `8091` |
| `KNOWLEDGE_MCP_PORT` | lokaler Wiki-MCP-Port | `8092` |
| `PAPERLESS_API_TOKEN` | bevorzugte DMS-Tokenanmeldung | leer |
| `PAPERLESS_ADMIN_USER/PASSWORD` | lokale Demo-Anmeldung als Fallback | Demo-Zugang |

Außerhalb des lokalen PoC `MCP_WRITE_ENABLED=false` setzen. Für einen
kontrollierten Testbetrieb ein eigenes ERPNext-Servicekonto mit minimalen
Create-/Read-/Delete-Rechten für die freigegebenen DocTypes und Token statt
Administrator-Passwort verwenden.

## Werkzeugfreigabe

Der Katalog liegt serverseitig in `app/master_data.py`. Jeder Typ definiert
DocType, Identitätsfeld, Pflichtfelder, erlaubte Felder, sichere Defaults,
Zahlenkonvertierung, Kindtabellenschema und ein Modellbeispiel. Neue Typen
werden nur mit folgenden Nachweisen aufgenommen:

1. DocType und Felder existieren in der fixierten ERPNext-Version.
2. Pflichtfelder, Links und Dublettenschlüssel sind dokumentiert.
3. Vorschau, Write, Dublettenfall, Mengenlimit und Rollback sind getestet.
4. Es gibt keine freie Wahl von DocType, Systemfeldern, SQL oder Methoden.

## Audit und Wiederherstellung

Pro Schreibaufruf wird eine JSON-Zeile mit Zeit, Typ, Batch-ID, angelegten und
übersprungenen Dokumenten sowie Fehlern geschrieben. Das Rollbackwerkzeug liest
nur dieses Audit und löscht in umgekehrter Reihenfolge. Das Audit ist kein
Ersatz für ein MariaDB-/Site-Backup.

Vor größeren Testimporten:

```bash
docker compose --profile full stop erpnext-backend erpnext-scheduler erpnext-queue-short erpnext-queue-long
# reguläres Site-/Volume-Backup nach Betriebsstandard erstellen
docker compose --profile full start erpnext-backend erpnext-scheduler erpnext-queue-short erpnext-queue-long
```

## Abnahme

Ein normaler Browser-GET ist kein MCP-Test. Ein MCP-Client muss:

1. alle ERP-, DMS- und Wiki-Werkzeuge listen,
2. den Katalog abrufen,
3. einen Datensatz ohne `confirm` nur als Vorschau erhalten,
4. denselben Datensatz bestätigt in ERPNext anlegen,
5. eine Dublette überspringen,
6. die Batch-ID zunächst nur vorschauen und anschließend zurückrollen.

Zusätzlich müssen `get_bom_details`, `get_inventory`,
`list_item_stock_movements` und `list_materials_consumed` gegen reale
ERPNext-Belege geprüft werden. Der DMS-Test sucht einen bekannten OCR-Begriff;
der Wiki-Test sucht eine Prozessregel. Das Hilfsskript `scripts/check_mcp.py`
listet oder ruft Werkzeuge über Streamable HTTP auf.

Vor Netzfreigabe kommen TLS, Keycloak/OAuth, Audience-Prüfung, Rollen, Rate
Limits und zentrale unveränderliche Auditlogs hinzu. Zugangsdaten bleiben
serverseitig und werden weder an MCP-Client noch Ollama ausgegeben.

Siehe auch [MCP-Schnittstelle](../../interfaces/mcp.md) und
[AI-Tools](../../interfaces/ai-tools.md).
