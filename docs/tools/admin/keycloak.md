# Keycloak administrieren

Das produktive Zielbild mit AD-Föderation, MFA, Token-Delegation,
Objektberechtigungen und Abnahmekriterien regelt
[SEC-IAM-001: IAM-Sicherheitskonzept](../../architecture/iam-security-concept.md).
Es ist ein Konzeptentwurf; die produktive Umsetzung ist gesondert nachzuweisen.

## Dienst

| Merkmal | Wert |
|---|---|
| Profil / Service | `iam` / `keycloak` |
| Version | in `compose.yaml` fixiert |
| Port | `${KEYCLOAK_PORT:-8082}` |
| Demo-Realm | Import aus `deployment/keycloak/realm.json` |

```bash
make sso
docker compose logs --tail=150 keycloak
```

`make sso` startet Keycloak, baut die Plattform mit `AUTH_MODE=oidc` neu und
aktiviert den nativen Keycloak-Login in Grafana. `make sso-all` startet den
gesamten lokalen Stack mit allen bereits implementierten SSO-Adaptern. Der
reine Befehl `docker compose --profile iam up -d keycloak` startet dagegen nur
den Identity Provider und schützt die Anwendungen noch nicht.

## Gelieferter Realm

| Objekt | Anzahl / Wert |
|---|---|
| Realm | `open-manufacturing` |
| reguläre Demobenutzer | 50 (`demo01` bis `demo50`) |
| Plattform-Admin | 1 (`platform-admin`) |
| Realm-Rollen | 21 |
| simulierte AD-Sicherheitsgruppen | 21 (`AD-GG-FLOW-*`) |
| OIDC-Clients | 6 |
| Sitzung Plattform | standardmäßig 480 Minuten |

Der Plattform-Admin besitzt die zusammengesetzte Rolle `platform-admin`; diese
enthält alle Fachrollen. Für die lokale Demo ist außerdem die Clientrolle
`realm-management/realm-admin` zugeordnet, damit das Konto auch den Demo-Realm
verwalten kann. `demo01` besitzt dieselbe Clientrolle ausschließlich für den
geführten Management-Rundgang und bezieht den fachlichen Vollzugriff weiterhin
aus `AD-GG-FLOW-PLATFORM-ADMIN`. Alle 51 Konten erhalten die Keycloak-
Kontorechte `manage-account`, `manage-account-links` und `view-profile`, damit
das FLOWID-Konto nach der Anmeldung vollständig lädt. Im Livebetrieb werden
Demo- und IAM-Administration entfernt beziehungsweise auf getrennte,
personengebundene Konten verteilt.

Der Realm liegt persistent im Volume `keycloak-data`. `--import-realm`
importiert nur beim ersten Start eines noch nicht vorhandenen Realms. Eine
spätere Änderung von `realm.json` überschreibt daher bewusst keinen laufenden
Realm. Änderungen werden zuerst in Staging migriert und per Export/Backup
abgesichert; ein Löschen des Volumes ist nur für eine entbehrliche lokale Demo
zulässig.

## Seed pflegen und prüfen

```bash
python scripts/generate_iam_demo.py
python scripts/generate_iam_demo.py --check
```

Das Skript erzeugt Keycloak- und Desksharing-Daten gemeinsam. Die zweite Zeile
läuft auch in der CI und verhindert auseinanderlaufende Benutzerkataloge.

## AD-Simulation und Gruppen

Die Live-Demo zeigt die spätere AD-Anbindung ohne echten Domänencontroller.
Benutzer und 21 Sicherheitsgruppen werden deterministisch erzeugt. Alle
Anwendungsrechte werden über Gruppen mit dem Präfix `AD-GG-FLOW-` vererbt; die
Gruppe trägt in Keycloak jeweils genau die zugehörige Realm-Rolle. Die
Management-Demo zeigt am Beispiel `demo06` den Weg vom AD-Konto bis zur
freigegebenen Anwendung.

Für den Livebetrieb wird statt des Demoimports eine LDAP/LDAPS User Federation
gegen das Unternehmens-AD eingerichtet. Der technische LDAP-Benutzer erhält
nur Leserechte auf die freigegebenen Benutzer- und Gruppen-OUs. Passwörter
werden nicht nach Keycloak übernommen.

## Realm und Clients

1. Pro Umgebung getrennten Realm bzw. klar getrennte Clients verwenden.
2. Exakte Login- und Post-Logout-Redirect-URIs sowie Web Origins setzen; keine
   produktiven Wildcards. Die lokalen Wildcards im Demo-Realm sind ausdrücklich
   nicht die Produktionsvorgabe.
3. Öffentliche und vertrauliche Clients passend zum Anwendungstyp wählen.
4. Rollen auf Fachrollen abbilden und Gruppen statt Einzelzuweisungen nutzen.
5. MFA, Passwortregeln, Session-Laufzeiten und Brute-Force-Schutz definieren.
6. Service Accounts separat führen und Secrets regelmäßig rotieren.

Die vorbereiteten Clients und der konkrete Anbindungsstatus sind unter
[Keycloak, Rollen und SSO](../../interfaces/iam-sso.md) dokumentiert.

## Benutzerlebenszyklus und Audit

Eintritt, Rollenwechsel, zeitlich befristete Rechte und Austritt brauchen einen
genehmigten Prozess. Mindestens Anmeldeereignisse, Admin-Aktionen und
Rollenänderungen revisionsgeeignet exportieren. Notfallkonten offline sichern
und jede Nutzung nachträglich prüfen.

Der Compose-Dienst nutzt `start-dev` und ist damit nur für lokale Tests
geeignet. Für Produktion sind externe Datenbank, TLS, Proxy-Konfiguration,
HA, Backup und getestete Realm-Wiederherstellung erforderlich.
