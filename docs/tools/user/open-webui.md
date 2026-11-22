# Open WebUI mit dem lokalen Modell nutzen

Open WebUI ist als FLOWAI die lokale Chat-Oberfläche für die auf dem Mac
installierten Ollama-Modelle. Sie ist unter <http://localhost:3001> erreichbar
und nutzt das bestehende Keycloak-SSO. Der Modellzugriff läuft kontrolliert
über FLOWGATE; Benutzer benötigen keinen Ollama- oder Gateway-Schlüssel.

## Erster Chat

1. FLOWAI öffnen und mit dem Keycloak-Demokonto anmelden.
2. Oben im Modellwähler `qwen3:8b` auswählen. Für umfangreiche Codeaufgaben
   kann `qwen3-coder:30b` verwendet werden; es benötigt deutlich mehr Speicher.
3. Eine harmlose Frage stellen und prüfen, ob eine Antwort gestreamt wird.
4. Fachliche ERPNext-Antworten nur dann verwenden, wenn das MCP-Werkzeug aktiv
   war und die genannte Referenz im ERPNext-Webclient geprüft wurde.

Chats und Einstellungen liegen lokal im Docker-Volume `open-webui-data`. Die
Modellgewichte bleiben in der vorhandenen Ollama-Installation auf dem Mac.

## Unternehmenswissen verwenden

Die drei Unternehmensquellen werden bei einer neuen Installation bereits als
MCP-Verbindungen vorkonfiguriert:

| Anzeige in Open WebUI | Quelle | Inhalt |
|---|---|---|
| `Unternehmenswissen` | Prozess-Wiki | Prozesse, Benutzeranleitungen, Administration und Schnittstellen |
| `DMS-Dokumente & Vektorsuche` | Paperless-ngx + pgvector | freigegebene Metadaten, OCR-Treffer und semantische Suche |
| `ERPNext-Unternehmensdaten` | ERPNext/Plattform | Aufträge, BOMs, Bestände, Materialbewegungen und kontrollierte Testdaten |

Der Plattform-MCP enthält zusätzlich den persönlichen KI-Arbeitsplatz. Ein
Mitarbeiter kann das Tagesbriefing mit folgendem Prompt abrufen:

> Rufe `get_personal_daily_brief` für `USR-006` und `2026-11-05` auf. Fasse
> meine drei wichtigsten Aktionen zusammen, nenne jede Quelle und führe keine
> Schreibaktion aus.

`list_personal_ai_tools` zeigt, welche Werkzeuge für die Rollen des gewählten
Profils verfügbar sind. Ein Status `planned` bedeutet, dass FLOWAI derzeit nur
vorbereiten oder in die Fachanwendung verlinken darf.

Für Management-Fragen liefert `get_future_operating_model` das dokumentierte
12- bis 24-Monats-Zielbild. Die darin enthaltenen Automatisierungsanteile sind
Szenariowerte und dürfen nicht als gemessene Produktivleistung dargestellt
werden.

Im Chat über **+ > Tools** mindestens `Unternehmenswissen` aktivieren. Für eine
Frage, die zusätzlich aktuelle Belege oder Dokumente benötigt, auch
`ERPNext-Unternehmensdaten` beziehungsweise `DMS-Dokumente` wählen. Beispiel:

> Fasse mir den Ablauf vom Wareneingang bis zur Fertigmeldung zusammen. Nenne
> die zuständige Rolle und verlinke jede verwendete Wiki-Seite.

Das Modell ruft `get_documentation_context` oder
`search_process_documentation` auf, fasst nur die gelieferten Ausschnitte
zusammen und übernimmt die zurückgegebenen `url`-Felder als anklickbare
Markdown-Links. Für mehr Detail kann es anschließend
`get_documentation_page` aufrufen. Eine Antwort ohne Werkzeugaufruf und ohne
Quellenlinks ist nicht als dokumentationsgestützt zu behandeln.

Der DMS-MCP liefert zu jedem Treffer eine URL wie
`http://localhost:8010/documents/4711/details`. Der Wiki-MCP verlinkt direkt
auf die Seite und, soweit möglich, auf die passende Überschrift. Dadurch muss
niemand den Seitenpfad aus einer Antwort manuell im Wiki suchen.

Für eine inhaltliche DMS-Frage eignet sich beispielsweise:

> Suche semantisch nach der Anweisung für Stichproben im Wareneingang von
> SCU-100. Fasse nur die gefundenen Ausschnitte zusammen und verlinke jedes
> verwendete Paperless-Dokument.

FLOWAI ruft dazu `search_dms_documents_semantic` auf. Meldet das Werkzeug einen
leeren Index, darf es einmal `refresh_dms_vector_index` ausführen und die Suche
wiederholen. Freigaben und Revisionen werden weiterhin im DMS geprüft.

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
| Kein Modell sichtbar | Administrator prüft FLOWGATE und anschließend Ollama |
| MCP-Werkzeug fehlt | Verbindungstyp muss MCP (Streamable HTTP) sein |
| Modell benutzt kein Werkzeug | Werkzeug im Chat aktivieren und Tool-Aufruf ausdrücklich verlangen |
| Wiki-/DMS-Link fehlt | nur Antworten mit zurückgegebenem `url`-Feld akzeptieren |
| Schreibaufruf bleibt Vorschau | nach Kontrolle bewusst `confirm=true` verlangen |
| Antwort ist unplausibel | ERPNext-Referenz öffnen; Fachsystem ist führend |

Technische Details stehen in der
[Administrationsanleitung](../admin/open-webui.md) und unter
[MCP-Schnittstelle](../../interfaces/mcp.md).
