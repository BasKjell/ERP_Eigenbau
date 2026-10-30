# Sicherheitsmodell

## Grundsätze

- Keine Fachanwendung erhält direkten Zugriff auf die Datenbank einer anderen.
- Der AI-Dienst darf nur freigegebene, lesende oder explizit bestätigte Tools
  aufrufen.
- Schreibende Aktionen benötigen Benutzeridentität, Rollenprüfung,
  Idempotenzschlüssel und Audit-Event.
- Passwörter und API-Tokens gehören in Secrets, nicht in Git.
- Dokument- und ERP-Berechtigungen werden serverseitig geprüft; UI-Ausblenden
  ist keine Zugriffskontrolle.

## Rollenmodell des PoC

| Rolle | ERP | MES | DMS | Admin |
|---|---:|---:|---:|---:|
| sales-user | CRM, Angebot, Auftrag | Status lesen | Kundendokumente lesen | - |
| procurement-user | Bedarf, Bestellung, Wareneingang | Status lesen | Zertifikate lesen | - |
| production-user | Work Order lesen | Arbeitsgang rückmelden | Arbeitsunterlagen lesen | - |
| quality-user | Sperrbestand, Prüfung | Abweichung bearbeiten | Prüfunterlagen schreiben | - |
| platform-admin | Konfiguration | Konfiguration | Konfiguration | Betrieb |

## Produktive Härtung

Die mitgelieferten Demo-Passwörter sind absichtlich sichtbar und nur lokal zu
verwenden. Vor produktivem Einsatz sind mindestens erforderlich:

1. externe Secret-Verwaltung und Rotation,
2. TLS an allen Endpunkten,
3. Keycloak mit Unternehmens-AD/LDAP,
4. Netzwerksegmentierung und Egress-Regeln,
5. verschlüsselte, getestete Backups,
6. zentrales Audit-Log und Alarmierung,
7. Datenschutz- und Aufbewahrungskonzept,
8. Hersteller- und Container-Sicherheitsupdates.
