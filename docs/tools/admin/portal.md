# Management-Portal / FastAPI administrieren

## Dienst und Verantwortung

| Merkmal | Wert |
|---|---|
| Compose-Service | `platform-api` |
| Image | lokaler Build aus `services/platform_api` |
| Port | `${DEMO_API_PORT:-8088}` |
| Healthcheck | `GET /health` |
| Metriken | `GET /metrics` |
| persistenter Zustand | Volume `demo-state` |
| Dokumente | `output/pdf` read-only |

## Betrieb

```bash
docker compose up -d --build demo-db platform-api
curl --fail http://localhost:8088/health
curl --fail http://localhost:8088/api/integrations
docker compose logs --tail=150 platform-api
```

`/api/integrations` zeigt Demo-/Live-Modus, Konfiguration und technische
Erreichbarkeit. Das ist noch keine fachliche Berechtigungsprüfung.

## Konfiguration und Sicherheit

- `AI_MODE`, `OLLAMA_BASE_URL` und `OLLAMA_MODEL` steuern die Assistenz.
- `ERPNEXT_*` und `PAPERLESS_*` aktivieren Live-Adapter.
- Tokens gehören in einen Secret-Store, nie in Git oder Screenshots.
- Schreibende API-Routen brauchen vor Produktivbetrieb OIDC, Rollenprüfung,
  CSRF-/Origin-Konzept, Rate Limits und Audit-Events.
- `/docs` ist in produktionsnahen Umgebungen nur intern bereitzustellen.

## Backup, Wiederherstellung und Update

Für die Demo genügt ein Backup von `demo-state`; Code, Seed und PDF-Beispiele
liegen in Git. Vor einem Update `make test`, `make validate` und den
End-to-End-Smoke-Test ausführen. Bei beschädigtem Demo-Zustand zuerst
`POST /api/demo/reset` verwenden, nicht das Volume löschen.

## Abnahme

- Healthcheck grün und Portal lädt ohne Konsolenfehler.
- Reset, Fortschritt, Fehlerfall und Nacharbeit funktionieren.
- Dokumente sind abrufbar und Statusantworten enthalten Quellen.
- Live-Adapter scheitern geschlossen und protokollieren keine Secrets.
