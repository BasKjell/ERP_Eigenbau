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
| `create_purchase_request` | ERPNext | schreiben | immer |
| `release_work_order` | ERPNext | schreiben | immer + Rolle |

## Antwortvertrag

Jede Antwort enthält:

- verständliche Zusammenfassung,
- Unsicherheit oder fehlende Daten,
- System und Fachreferenz der Quellen,
- bei Schreibvorschlägen eine explizite Bestätigung vor Ausführung.

## Lokales Ollama aktivieren

```bash
docker compose --profile ai up -d ollama
docker compose exec ollama ollama pull qwen3:4b
```

Danach `AI_MODE=ollama` in `.env` setzen und `platform-api` neu starten. Wenn
Ollama nicht erreichbar ist, fällt der PoC kontrolliert auf die
deterministische, quellenbasierte Antwort zurück.
