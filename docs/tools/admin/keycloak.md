# Keycloak administrieren

## Dienst

| Merkmal | Wert |
|---|---|
| Profil / Service | `iam` / `keycloak` |
| Version | in `compose.yaml` fixiert |
| Port | `${KEYCLOAK_PORT:-8082}` |
| Demo-Realm | Import aus `deployment/keycloak/realm.json` |

```bash
docker compose --profile iam up -d keycloak
docker compose logs --tail=150 keycloak
```

## Realm und Clients

1. Pro Umgebung getrennten Realm bzw. klar getrennte Clients verwenden.
2. Exakte Redirect-URIs und Web Origins setzen; keine produktiven Wildcards.
3. Öffentliche und vertrauliche Clients passend zum Anwendungstyp wählen.
4. Rollen auf Fachrollen abbilden und Gruppen statt Einzelzuweisungen nutzen.
5. MFA, Passwortregeln, Session-Laufzeiten und Brute-Force-Schutz definieren.
6. Service Accounts separat führen und Secrets regelmäßig rotieren.

## Benutzerlebenszyklus und Audit

Eintritt, Rollenwechsel, zeitlich befristete Rechte und Austritt brauchen einen
genehmigten Prozess. Mindestens Anmeldeereignisse, Admin-Aktionen und
Rollenänderungen revisionsgeeignet exportieren. Notfallkonten offline sichern
und jede Nutzung nachträglich prüfen.

Der Compose-Dienst nutzt `start-dev` und ist damit nur für lokale Tests
geeignet. Für Produktion sind externe Datenbank, TLS, Proxy-Konfiguration,
HA, Backup und getestete Realm-Wiederherstellung erforderlich.
