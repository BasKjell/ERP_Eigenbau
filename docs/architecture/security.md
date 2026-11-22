# Sicherheitsmodell

Das produktive Zielbild mit AD-Föderation, MFA, Token-Delegation,
Objektberechtigungen und Abnahmekriterien regelt
[SEC-IAM-001: IAM-Sicherheitskonzept](iam-security-concept.md).
Es ist ein Konzeptentwurf; die produktive Umsetzung ist gesondert nachzuweisen.

## Grundsätze

- Keine Fachanwendung erhält direkten Zugriff auf die Datenbank einer anderen.
- Der AI-Dienst darf nur freigegebene, lesende oder explizit bestätigte Tools
  aufrufen.
- Schreibende Aktionen benötigen Benutzeridentität, Rollenprüfung,
  Idempotenzschlüssel und Audit-Event.
- Passwörter und API-Tokens gehören in Secrets, nicht in Git.
- Dokument- und ERP-Berechtigungen werden serverseitig geprüft; UI-Ausblenden
  ist keine Zugriffskontrolle.
- Die vor externen Weboberflächen liegende Unternehmens-Shell ergänzt nur
  statische Shell-, Theme- und Launcher-Assets. Sie hält keine Fachsitzung,
  hebt keine Upstream-Rechte auf und darf keine API-Antworten oder
  Dokumentinhalte verändern.

## Rollenmodell des PoC

| Rolle | ERP / Prozess | MES / HR | DMS / Desksharing | Admin |
|---|---:|---:|---:|---:|
| sales-user | CRM, Angebot, Auftrag | Status lesen | Kundendokumente lesen, Platz buchen | - |
| procurement-user | Bedarf, Bestellung, Wareneingang | Status lesen | Zertifikate lesen, Platz buchen | - |
| production-user | Work Order lesen | Arbeitsgang rückmelden | Arbeitsunterlagen lesen, Platz buchen | - |
| quality-user | Sperrbestand, Prüfung | Abweichung bearbeiten | Prüfunterlagen schreiben, Platz buchen | - |
| work-user | Redmine-Projekt und Tickets | FLOWWORK lesen/schreiben | Projekt-Wiki lesen | - |
| requirements-user | Requirement-Versionen und Traceability | Review / Baseline | Nachweise referenzieren | - |
| work-admin | Projektvorlagen und Adapter | FLOWWORK verwalten | Redmine-Direktzugriff | FLOWWORK |
| hr-user / hr-admin | Employee-Bezug | Self-Service / Administration | geschützte HR-Akten, Platz buchen | HR |
| desksharing-admin | - | - | Buchungen und Standorte verwalten | Desksharing |
| platform-admin | alle zusammengesetzten Realm-Rollen | alle Bereiche | alle Bereiche | Plattform |

FLOWHR ergänzt `hr-employee` für eigene Daten und Anträge, `hr-manager` für
direkt zugeordnete Teams, `hr-specialist` für Stamm/Regeln und `hr-auditor` für
unveränderliche Prüfung. Recruiting verwendet `recruiter`; Payroll trennt
`payroll-preparer` und `payroll-approver`. Eigene Anträge und selbst
vorbereitete Abrechnungsläufe dürfen nicht selbst genehmigt werden.
Krankheitsgründe werden in Teamansichten nicht offengelegt. Im PoC sind diese
fachlichen Prüfungen vorhanden. Die Plattform kann die OIDC-Identität und
Realm-Rollen inzwischen mit `AUTH_MODE=oidc` erzwingen. Vor Go-live bleiben
die reale HR-Identitätszuordnung, MFA, Lifecycle und die adapterspezifische
Rollenbindung in den Upstream-Systemen ein Gate.

Der Redmine-API-Key bleibt ausschließlich im Plattformdienst. Die
FLOWWORK-Oberfläche erhält weder Key noch Redmine-Administratorrechte. Ein
produktives Redmine-Servicekonto muss auf freigegebene Projekte und Aktionen
begrenzt werden.

## OIDC-Sitzung und Desksharing

Der Plattform-Client verwendet Authorization Code mit PKCE, `state`, einen
kurzlebigen Flow-Cookie und eine signierte `HttpOnly`-Sitzung mit
`SameSite=Lax`. Seiten und APIs prüfen Rollen serverseitig; die UI-Auswahl von
Demobenutzern wird bei SSO nicht als Identitätsquelle verwendet.

Desksharing speichert keine Anwesenheits- oder Leistungsbewertung. Im Audit
stehen Identität, Aktion, Zeitpunkt, Buchungs- und Platz-ID. Für den
Livebetrieb sind Zweck, Sichtbarkeit von Belegungen, Aufbewahrungsfrist und
Beteiligungsrechte des Betriebsrats festzulegen. Buchungsdaten dürfen nicht
ungeprüft für Arbeitszeit- oder Verhaltenskontrolle verwendet werden.

## DMS-Rollen und Projektgrenzen

Paperless verwendet ein zweidimensionales Modell. `DMS-Leser`,
`DMS-Bearbeiter`, `DMS-Pruefer`, `DMS-Freigeber` und `DMS-Administration`
erteilen globale Aktionen. `DMS-Projekt-<Code>-Lesen`, `-Bearbeiten`,
`-Pruefen` und `-Freigeben` begrenzen diese Aktionen auf Dokumentobjekte.
Bereichsgruppen und `DMS-Eingang` decken Dokumente ohne Projekt ab.

Personaldokumente bilden eine zusätzliche harte Grenze:
`DMS-Bereich-HR-Recruiting` sieht Bewerberunterlagen,
`DMS-Bereich-HR-Payroll` sieht Entgeltabrechnungen. Die Paperless-Workflows
erkennen geschützte Dateimuster, setzen `Vertraulich/Personal`, verschieben in
den Personalablagepfad und entfernen `DMS-Eingang`. Globale `DMS-Leser` sind
nicht Teil der Objekt-ACL. Die negative ACL-Prüfung ist automatisiert; vor
Livebetrieb ist dieselbe Trennung mit realen OIDC-Benutzern in Staging zu
belegen.

Die Freigabe folgt Entwurf → Prüfung → Zur Freigabe → Freigegeben. Beim
Statuswechsel werden Änderungsrechte serverseitig entzogen. Prüfer und
Freigeber müssen getrennte reale Identitäten sein; Gruppenunion, Superuser und
gemeinsame Konten würden das Vier-Augen-Prinzip aushebeln.

Das Grafana-DMS-Dashboard greift mit `grafana_reader` ausschließlich auf eine
metadatenbegrenzte Reporting-View ohne OCR- und Binärinhalte zu. Diese
technische Einschränkung ersetzt keine fachliche Projekt-ACL: Die gemeinsame
SQL-Datenquelle übernimmt die Paperless-Benutzeridentität nicht. Daher ist der
Dashboard-Ordner im PoC nur für zentrale Projektleitung/Management freizugeben;
projektgenaue Live-Rechte benötigen getrennte Views oder einen
identitätsbewussten API-Proxy.

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
9. Härtung der App-Shell mit TLS, restriktiven Proxy-Headern, Größen-/Zeitlimits
   und Regressionstests für Login, Upload, Download, REST und WebSocket.
