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
