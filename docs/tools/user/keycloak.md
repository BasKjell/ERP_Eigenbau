# Mit Keycloak anmelden und Rollen nutzen

Keycloak ist die zentrale Anmeldung. Das `iam`-Profil stellt den Realm
`open-manufacturing` bereit. Mit `make sso` erzwingen Management-Portal, MES,
HR, Desksharing, Grafana und ihre APIs die Anmeldung und serverseitige
Rollenprüfung. Grafana leitet dabei automatisch zu Keycloak weiter.

## Anmelden

1. Fachanwendung öffnen und **Anmelden** wählen.
2. Auf der Keycloak-Seite nur das persönliche Konto verwenden.
3. Nach erfolgreicher Anmeldung Anwendung und angezeigte Rolle prüfen.
4. Bei einem geteilten Arbeitsplatz nach Abschluss in Fachanwendung und
   Keycloak abmelden und Browserfenster schließen.

## Lokale Beispielkonten

| Konten | Initialpasswort | Hinweis |
|---|---|---|
| `demo01` bis `demo50` | `Demo-User-2026!` | fiktive Demoidentitäten, nur lokal |
| `platform-admin` | `Admin-Start-2026!` | temporär; Keycloak verlangt beim ersten Login ein neues Passwort |

Die Passwörter sind absichtlich dokumentierte Demo-Credentials. Sie dürfen
nicht in einer erreichbaren Test-, Abnahme- oder Produktivumgebung verwendet
werden.

## Rollen im Prozess

| Rolle | Typische Prozessaufgabe |
|---|---|
| `sales-user` | Opportunity, Angebot und Auftrag |
| `planning-user` | MRP, Kapazität und Fertigungsauftrag |
| `production-user` | MES, Job Cards und Rückmeldungen |
| `quality-user` | Abweichung, Wiederholtest und Freigabe |
| `finance-user` | Rechnung und Forderung |
| `hr-user` / `hr-admin` | HR-Self-Service bzw. HR-Administration |
| `desksharing-user` / `desksharing-admin` | eigene Buchung bzw. Standortsteuerung |
| `management-user` | End-to-End-Sicht |
| `platform-admin` | alle Plattformrollen; in der lokalen Demo zusätzlich Administration des Keycloak-Realms |

Fehlt eine Funktion, keine fremden Konten verwenden. Benötigte Rolle,
fachliche Begründung und gewünschte Dauer an den Rollenverantwortlichen
melden. Rollen werden nach Minimalprinzip und Vier-Augen-Freigabe vergeben.
