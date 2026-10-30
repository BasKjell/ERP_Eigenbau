# Mit Keycloak anmelden und Rollen nutzen

Keycloak ist im Zielbild die zentrale Anmeldung. Das optionale `iam`-Profil
stellt dafür den Realm `manufacturing` bereit. Der Kern-PoC kann auch ohne SSO
laufen; produktive Benutzerkonten gehören nicht in die Fachanwendungen
doppelt gepflegt.

## Anmelden

1. Fachanwendung öffnen und **Anmelden** wählen.
2. Auf der Keycloak-Seite nur das persönliche Konto verwenden.
3. Nach erfolgreicher Anmeldung Anwendung und angezeigte Rolle prüfen.
4. Bei einem geteilten Arbeitsplatz nach Abschluss in Fachanwendung und
   Keycloak abmelden und Browserfenster schließen.

## Rollen im Prozess

| Rolle | Typische Prozessaufgabe |
|---|---|
| `sales-user` | Opportunity, Angebot und Auftrag |
| `planning-user` | MRP, Kapazität und Fertigungsauftrag |
| `shopfloor-user` | Job Cards und Rückmeldungen |
| `quality-user` | Abweichung, Wiederholtest und Freigabe |
| `finance-user` | Rechnung und Forderung |
| `management-reader` | lesende End-to-End-Sicht |

Fehlt eine Funktion, keine fremden Konten verwenden. Benötigte Rolle,
fachliche Begründung und gewünschte Dauer an den Rollenverantwortlichen
melden. Rollen werden nach Minimalprinzip und Vier-Augen-Freigabe vergeben.
