# Open WebUI administrieren

## Dienst und Start

| Merkmal | Wert |
|---|---|
| Compose-Service | `open-webui` hinter `open-webui-shell` |
| Image | `ghcr.io/open-webui/open-webui:v0.12.4` |
| Profil | `webui` |
| URL | `http://localhost:${OPEN_WEBUI_PORT:-3001}` |
| Daten | Volume `open-webui-data` |
| Modellzugang | `http://agentgateway:4000/v1` über FLOWGATE |

```bash
make webui
docker compose --profile webui ps open-webui open-webui-shell
docker compose --profile webui logs --tail=150 open-webui open-webui-shell
```

`make full` aktiviert das `webui`-Profil ebenfalls. Die Anmeldung wird vom
gemeinsamen Keycloak-Proxy übernommen; das offene Loginformular ist
deaktiviert.

## Qwen über FLOWGATE

FLOWAI greift nicht mehr direkt auf Ollama zu. Die relevante Konfiguration ist:

```dotenv
AGENTGATEWAY_OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
AGENTGATEWAY_OPENWEBUI_KEY=...
```

Erreichbarkeit vom Host prüfen:

```bash
ollama list
curl http://127.0.0.1:11434/api/version
```

Wird stattdessen der optionale Compose-Ollama-Dienst genutzt, beide Profile
starten und `AGENTGATEWAY_OLLAMA_BASE_URL=http://ollama:11434/v1` setzen.
Open WebUI hat `ENABLE_OLLAMA_API=false`; seine OpenAI-kompatible Verbindung
zeigt ausschließlich auf FLOWGATE. `ENABLE_PERSISTENT_CONFIG=false` stellt
sicher, dass eine alte UI-Konfiguration diesen kontrollierten Datenweg nicht
umgeht. Modelle, Schlüssel und OIDC sind in der
[FLOWGATE-Adminanleitung](agentgateway.md) beschrieben.

## MCP-Verbindung

Open WebUI unterstützt Streamable HTTP nativ. `compose.yaml` liefert die drei
Verbindungen bei einer frischen Instanz deklarativ über
`TOOL_SERVER_CONNECTIONS` aus:

- `erp` → `http://platform-mcp:8090/mcp`
- `dms` → `http://dms-mcp:8091/mcp`
- `wiki` → `http://knowledge-mcp:8092/mcp`

Alle drei Einträge müssen den Typ **MCP**, Authentifizierung **None** und
`config.enable=true` haben. Nach einem Upgrade unter
**Admin > Integrations > External Tool Servers** prüfen, ob ältere Einträge
versehentlich als `OpenAPI` gespeichert sind; in diesem Fall Verbindungstyp
auf **MCP (Streamable HTTP)** ändern und speichern. `localhost` ist in den
Server-URLs falsch, weil Open WebUI die Dienste über das Compose-Netz erreicht.

Nur Administratoren dürfen MCP-Server registrieren. Die Freigabe an Benutzer
oder Gruppen erfolgt anschließend über die Open-WebUI-Zugriffsliste. Wiki und
DMS sind technisch read-only; nur der ERP-Server besitzt die gesondert
bestätigten Testdatenwerkzeuge. Der Wiki-Server liefert öffentliche
Browser-URLs aus `DOCUMENTATION_PUBLIC_URL`, der DMS-Server Dokumentlinks aus
`PAPERLESS_PUBLIC_URL`.

Die Testdatenwerkzeuge verlangen weiterhin ihre eigene Vorschau und
`confirm=true`; Open WebUI ersetzt diese serverseitige Kontrolle nicht.

## Berechtigungsgrenze

In der lokalen Demo verwenden ERP- und DMS-MCP technische Servicezugänge. Eine
Open-WebUI-Freigabe steuert daher nur, **wer das Werkzeug sieht**, nicht welche
einzelnen ERP-Belege oder Paperless-Dokumente das Werkzeug lesen darf. Vor dem
Mehrbenutzer-Livebetrieb gilt deshalb:

1. `Unternehmenswissen` kann für alle internen Benutzer lesbar sein.
2. ERP- und DMS-MCP zunächst nur explizit freigegebenen Gruppen zuordnen.
3. MCP-Endpunkte mit Keycloak/OAuth absichern und die Benutzeridentität bis zum
   Fachsystem durchreichen.
4. Ergebnisfilter und Berechtigungsprüfung serverseitig testen; niemals auf
   Modellprompt oder UI-Ausblendung vertrauen.
5. HR-, Bewerbungs-, Payroll- und andere personenbezogene Daten erst danach als
   KI-Werkzeug freigeben.

Damit ist das Wiki sofort breit nutzbar; „alle Unternehmensdaten für alle“ ist
bewusst **nicht** die Live-Voreinstellung.

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
5. Prüfen, dass `get_documentation_context` klickbare Links auf
   `DOCUMENTATION_PUBLIC_URL` und DMS-Treffer Links auf
   `PAPERLESS_PUBLIC_URL` zurückgeben.

## Lizenz- und Sicherheitsgrenze

Open WebUI verwendet die eigene **Open WebUI License** mit einer
Branding-Bedingung und ist deshalb gesondert von den OSI-Standardlizenzen des
übrigen Stacks zu bewerten. Branding nicht entfernen und Lizenz vor
Mehrbenutzer-, Weitergabe- oder Produktiveinsatz rechtlich prüfen.

Open WebUI ist im PoC nur an `localhost` gebunden. Vor Netzfreigabe sind TLS,
Rollen, Upload-/Modelllimits, Datenschutzregeln, Rate Limits, individuelle
Nutzungszuordnung im Gateway und authentifizierte MCP-Endpunkte erforderlich.
