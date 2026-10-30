# Open WebUI administrieren

## Dienst und Start

| Merkmal | Wert |
|---|---|
| Compose-Service | `open-webui` |
| Image | `ghcr.io/open-webui/open-webui:v0.12.4` |
| Profil | `webui` |
| URL | `http://localhost:${OPEN_WEBUI_PORT:-3001}` |
| Daten | Volume `open-webui-data` |
| Ollama | standardmäßig `http://host.docker.internal:11434` |

```bash
make webui
docker compose --profile webui ps open-webui
docker compose --profile webui logs --tail=150 open-webui
```

`make full` aktiviert das `webui`-Profil ebenfalls. Der erste registrierte
Benutzer wird lokaler Administrator. Danach Registrierung in den
Admin-Einstellungen deaktivieren, wenn keine weiteren Konten benötigt werden.

## Ollama-Verbindung

Für Ollama auf macOS ist in `.env` konfiguriert:

```dotenv
OPEN_WEBUI_OLLAMA_BASE_URL=http://host.docker.internal:11434
```

Erreichbarkeit vom Host prüfen:

```bash
ollama list
curl http://127.0.0.1:11434/api/version
```

Wird stattdessen der optionale Compose-Ollama-Dienst genutzt, beide Profile
starten und `OPEN_WEBUI_OLLAMA_BASE_URL=http://ollama:11434` setzen.

## MCP-Verbindung

Open WebUI unterstützt Streamable HTTP nativ. Die Verbindung wird nach der
ersten Anmeldung unter **Admin > Integrations > External Tool Servers** mit
`http://platform-mcp:8090/mcp`, Typ **MCP (Streamable HTTP)** und Auth **None**
angelegt. Nur Administratoren dürfen MCP-Server registrieren. Die Freigabe an
Benutzer oder Gruppen erfolgt anschließend über die Open-WebUI-Zugriffsliste.

Die Testdatenwerkzeuge verlangen weiterhin ihre eigene Vorschau und
`confirm=true`; Open WebUI ersetzt diese serverseitige Kontrolle nicht.

## Secrets, Backup und Update

`OPEN_WEBUI_SECRET_KEY` vor einer geteilten Nutzung mit einem langen,
zufälligen Wert ersetzen. Er bleibt über Container-Neustarts stabil, sonst
können Sitzungen und verschlüsselte Integrationsdaten ungültig werden. Das
Volume `open-webui-data` enthält Konten, Chats, Uploads und Konfiguration und
gehört in den Backupplan.

Das Image ist auf eine konkrete Version fixiert. Vor einem Update:

1. Release Notes und Lizenzänderungen prüfen.
2. `open-webui-data` sichern.
3. Version in `compose.yaml` ändern und Testinstanz starten.
4. Modellliste, Chat, MCP-Lesetool, Vorschau und bestätigten Testdatensatz mit
   Rollback abnehmen.

## Lizenz- und Sicherheitsgrenze

Open WebUI verwendet die eigene **Open WebUI License** mit einer
Branding-Bedingung und ist deshalb gesondert von den OSI-Standardlizenzen des
übrigen Stacks zu bewerten. Branding nicht entfernen und Lizenz vor
Mehrbenutzer-, Weitergabe- oder Produktiveinsatz rechtlich prüfen.

Open WebUI ist im PoC nur an `localhost` gebunden. Vor Netzfreigabe sind TLS,
SSO, Rollen, deaktivierte offene Registrierung, Upload-/Modelllimits,
Datenschutzregeln, Rate Limits und ein eingeschränkt authentifizierter
MCP-Endpunkt erforderlich.
