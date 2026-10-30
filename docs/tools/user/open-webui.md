# Open WebUI mit dem lokalen Modell nutzen

Open WebUI ist die allgemeine lokale Chat-Oberfläche für die auf dem Mac
installierten Ollama-Modelle. Sie ist unter <http://localhost:3001> erreichbar.
Der erste registrierte Benutzer wird Administrator der lokalen Instanz.

## Erster Chat

1. Open WebUI öffnen und das lokale Administratorkonto registrieren.
2. Oben im Modellwähler `qwen3:8b` auswählen. Für umfangreiche Codeaufgaben
   kann `qwen3-coder:30b` verwendet werden; es benötigt deutlich mehr Speicher.
3. Eine harmlose Frage stellen und prüfen, ob eine Antwort gestreamt wird.
4. Fachliche ERPNext-Antworten nur dann verwenden, wenn das MCP-Werkzeug aktiv
   war und die genannte Referenz im ERPNext-Webclient geprüft wurde.

Chats und Einstellungen liegen lokal im Docker-Volume `open-webui-data`. Die
Modellgewichte bleiben in der vorhandenen Ollama-Installation auf dem Mac.

## ERPNext-MCP einmalig verbinden

Diese Einrichtung ist nur für den Administrator sichtbar:

1. **Settings > Admin > Integrations** öffnen.
2. Unter **External Tool Servers** eine Verbindung hinzufügen.
3. Typ **MCP (Streamable HTTP)** wählen.
4. Als Server-ID zum Beispiel `erp` und als URL
   `http://platform-mcp:8090/mcp` eintragen.
5. Authentifizierung **None** wählen und speichern.
6. Im Chat das Werkzeug bzw. den verbundenen Server für `qwen3:8b`
   aktivieren.

`localhost:8090` ist an dieser Stelle falsch: Aus dem Open-WebUI-Container ist
der MCP-Dienst unter seinem Compose-Namen `platform-mcp` erreichbar.

## Testdaten sicher anlegen

Schreibaufträge immer in zwei getrennten Schritten formulieren:

> Rufe `list_test_data_types` auf. Erstelle anschließend nur eine Vorschau für
> zwei Testlieferanten; verwende noch nicht `confirm=true`.

Vorschau, Typen, Felder und Anzahl kontrollieren. Erst danach:

> Die Vorschau ist korrekt. Wiederhole genau denselben Aufruf mit
> `confirm=true` und gib mir die Batch-ID zurück.

Mit der Batch-ID kann eine Testcharge ebenfalls erst als Vorschau und dann
bestätigt zurückgerollt werden. Das Modell darf keine produktiven Stammdaten,
Benutzerrechte oder Buchungen ohne einen gesonderten Freigabeprozess ändern.

## Fehlerbilder

| Problem | Prüfung |
|---|---|
| Kein Modell sichtbar | Administrator prüft die Ollama-Verbindung |
| MCP-Werkzeug fehlt | Verbindungstyp muss MCP (Streamable HTTP) sein |
| Modell benutzt kein Werkzeug | Werkzeug im Chat aktivieren und Tool-Aufruf ausdrücklich verlangen |
| Schreibaufruf bleibt Vorschau | nach Kontrolle bewusst `confirm=true` verlangen |
| Antwort ist unplausibel | ERPNext-Referenz öffnen; Fachsystem ist führend |

Technische Details stehen in der
[Administrationsanleitung](../admin/open-webui.md) und unter
[MCP-Schnittstelle](../../interfaces/mcp.md).
