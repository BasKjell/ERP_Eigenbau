# MCP-Werkzeuge im Prozess nutzen

MCP standardisiert den Zugriff eines Assistenten auf freigegebene
Fachfunktionen. Benutzer stellen ihre Frage im Portal oder in einem
autorisierten MCP-Client; sie rufen den technischen Endpunkt nicht direkt auf.

## Verfügbare Fragen und Prozessbezug

| Frage | Werkzeug | Führende Quelle |
|---|---|---|
| Welche Aufträge sind gerade in Produktion? | `list_production_orders` | ERPNext Work Order |
| Welche Bestellungen sind verspätet? | `list_late_purchase_orders` | ERPNext Purchase Order |
| Wie ist der Status von SO-4711? | `get_order_status` | ERPNext Sales Order |
| Welche Unterlagen gelten für SCU-100? | `search_documents` | Paperless-Metadaten |

1. Frage mit eindeutiger Beleg-, Artikel- oder Serienreferenz stellen.
2. Angezeigten `Tool`-Chip prüfen.
3. Fachreferenzen in den Quellenchips kontrollieren.
4. Vor einer Entscheidung den Beleg im führenden System öffnen.

Der MCP-Server ist read-only. Er nimmt keine Bestellung, Freigabe, Buchung
oder Stammdatenänderung vor. Details zur Architektur stehen unter
[MCP-Schnittstelle](../../interfaces/mcp.md).
