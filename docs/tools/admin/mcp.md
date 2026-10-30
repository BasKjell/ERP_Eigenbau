# Plattform-MCP administrieren

## Dienst

| Merkmal | Wert |
|---|---|
| Compose-Service | `platform-mcp` |
| Transport | Streamable HTTP, stateless |
| Endpunkt | `http://localhost:${MCP_PORT:-8090}/mcp` |
| SDK | offizieller Python MCP SDK 2.3.0 |
| Rechte | ausschließlich lesen |
| Zustand | gemeinsames Volume `demo-state` |

```bash
docker compose up -d --build platform-mcp
docker compose logs --tail=150 platform-mcp
```

Ein normaler Browser-GET ist kein vollständiger MCP-Test. Zur Abnahme verbindet
sich ein MCP-Client, liest die Werkzeugliste und ruft jedes Werkzeug mit einem
bekannten Positiv- und Leerfall auf.

## Werkzeugfreigabe

Neue Werkzeuge brauchen eine fachliche Beschreibung, enges Eingabeschema,
serverseitige Rollenprüfung, begrenzte Ergebnismenge, Quellenreferenz und
Tests. Generisches SQL, Shellzugriff und beliebige DocType-Abfragen bleiben
gesperrt. Ein späteres Schreibwerkzeug benötigt zusätzlich explizite
Bestätigung, Idempotenz, Audit und einen getesteten Rollbackpfad.

## Netz und Authentifizierung

Der aktuelle Port ist nur für den lokalen PoC gedacht. Vor einer Freigabe im
Netz: TLS, Keycloak/OAuth, Token-Audience, Clientrollen, Rate Limits, CORS-/Host
Allowlist und zentrale Auditlogs konfigurieren. Upstream-Credentials bleiben
im Server und werden weder an den MCP-Client noch an Ollama ausgegeben.

Siehe auch [MCP-Schnittstelle](../../interfaces/mcp.md) und
[AI-Tools](../../interfaces/ai-tools.md).
