# 07 Keycloak, Identitäten und Berechtigungen

Arbeitsreferenz KI-U-07 · Stand 20.11.2026 · Arbeitsentwurf zur internen Abstimmung

## Wer darf wann in wessen Auftrag handeln?

Keycloak (FLOWID) ist als SSO-Dienst vorgegeben. AD führt Personen und freigegebene Gruppen, Keycloak bindet das Verzeichnis lesend über LDAPS an. Die Berechtigungskette der Referenzumgebung bleibt erhalten: AD-Benutzer → AD-Gruppe `AD-GG-FLOW-<ROLLE>` → Keycloak-Gruppe → Realm-Rolle → Anwendung. Vorgesehen sind getrennte Realms für KI-Entwicklung und produktive Business Applications; der Realm `open-manufacturing` der Referenzumgebung ist der Realm für die Business Applications. Clientregistrierungen, Schlüssel, Administratoren und Dienstkonten werden pro Realm verwaltet. Ein gemeinsames AD-Konto vereinfacht die Anmeldung. Eine Vertrauensbeziehung über Realmgrenzen bedarf eines gesonderten Entwurfs. Produktive Endpunkte akzeptieren keine Entwicklungsidentität.

Webanwendungen nutzen bevorzugt OpenID Connect mit Authorization Code und PKCE. Bei unterstützten Altsystemen kommt SAML infrage. Interaktive Konten nutzen MFA. Für Administrations- und Notfallkonten gelten getrennte Nutzung und Protokollierung. Browser und Portalseiten erhalten nur die für die Anwendung erforderlichen Informationen. Das Entfernen eines Menüpunkts allein verhindert keinen direkten API-Zugriff.

| Entscheidungsebene | Verbindliche Entscheidung im Zielbild | Beleg |
| --- | --- | --- |
| Anmeldung | Keycloak authentisiert Person bzw. Dienst und stellt Token für die vorgesehene Zielressource aus | Test mit gültigem und falschem Aussteller |
| Funktionsrecht | API prüft Signatur, Aussteller, Zielgruppe, Frist, Client und benötigten Scope | Negativtest mit Token eines anderen Dienstes |
| Objekt und Version | Fachsystem oder nachweisbar gleichwertiger Autorisierungsdienst prüft Person, Projekt, Objekt, Revision und Aktion | DMS-Dokument für Person A sichtbar, für Person B verborgen |
| Handlungsauftrag | Workflow prüft genehmigten Use Case, Agentenrolle, erlaubte Wirkung, aktuellen Bestätigungsstand und Empfänger | Geänderter ERP-Entwurf erfordert erneute Bestätigung |

## Delegation und automatisierte Dienste

Bei persönlicher Delegation bildet die wirksame Berechtigung die Schnittmenge aus Personenrecht, Werkzeugrecht, Dienstrecht und genehmigtem Auftrag. Das Zielsystem erhält eine verifizierbare Personen- und Dienstzuordnung, etwa über einen für Ziel und Aktion ausgestellten Delegationstoken. Technische Voraussetzungen werden je Anwendung getestet. Wo ältere Produkte keine sichere Delegation bieten, wird ein begrenzter Adapter mit verbindlicher Objektprüfung vorgesehen. Bei fehlender Gleichwertigkeit bleibt die Aktion im Fachsystem manuell. Hintergrunddienste erhalten eine eigene Identität und schriftlich begründeten Systemauftrag mit Objektmenge und Ablaufdatum. Ein Dienstkonto darf keinen Benutzer vortäuschen.

## Eintritt, Wechsel, Austritt und Notbetrieb

Der Fachverantwortliche genehmigt Funktionsrechte. Der Dateneigentümer genehmigt den Zugriff auf geschützte Datenräume. IAM setzt sie um und dokumentiert Beginn, Ende und Rezertifizierung. Beim Abteilungswechsel werden Altberechtigungen entzogen und delegierte Aufgaben erneut zugeordnet. Bei Austritt werden Sitzungen, Dienstdelegationen, Warteschlangenaufträge und persönliche Caches berücksichtigt. Beim Ausfall des Identitäts- oder Rechtesystems blockieren geschützte KI-Zugriffe. Ein kontrollierter Notzugriff auf Fachsysteme folgt deren eigenem Verfahren und wird nachträglich geprüft.

Pflichttests im vorgesehenen Betrieb sind Rechteentzug während einer Suche und zwischen Vorschau und ERP-Schreibvorgang, falscher Mandant, abgelaufene Bestätigung und Aufruf einer Produktions-API mit einem Entwicklungstoken. Prüfer dokumentieren tatsächliche Entzugszeit einschließlich Caches und noch laufender Sitzungen. Zielwerte werden vor der Freigabe festgelegt.

## Stand in der Referenzumgebung

Das IAM-Sicherheitskonzept SEC-IAM-001 der Referenzumgebung beschreibt dasselbe Zielbild und ist mit diesem Teil abzugleichen.

| Thema | Heute in der Referenzumgebung | Ziel nach diesem Konzept |
| --- | --- | --- |
| Verzeichnis | AD mit 51 fiktiven Identitäten und 21 Realm-Rollen simuliert | Lesende LDAPS-Anbindung an das echte AD |
| Portal und Eigenentwicklungen | OIDC mit PKCE, serverseitige Pfad- und API-Prüfung | Unverändert, ergänzt um MFA und kurze Sitzungen |
| FLOWERP | Keycloak-Anmeldung über vertraulichen Client; Frappe sendet in der eingesetzten Version kein PKCE | Client-Härtung prüfen, PKCE sobald verfügbar |
| FLOWDOC, FLOWTASK, FLOWAI | Anmeldung über vorgeschalteten Proxy mit vertrauenswürdigem Header; Header von außen werden überschrieben | Beibehalten, aber Objektrechte im Fachsystem prüfen |
| KI-Werkzeuge | MCP-Server lesen DMS und ERP mit technischen Konten | Delegation mit Benutzeridentität bis ins Fachsystem |
| Nachweise | Negativtests, MFA, Sitzungswiderruf und Notfallzugang noch offen | Pflichttests oben vor Livebetrieb |

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE U-07] IAM und Fachsystemowner ergänzen reale Realms, die Abbildung der simulierten Gruppen `AD-GG-FLOW-*` auf echte AD-Gruppen, Anwendungsrollen, MFA-Verfahren, Entzugsziel, Stellvertretungen, Rezertifizierungsintervall und Ausführung der Notfallkontrolle. Zuordnung fachlich bestätigen.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Rechtematrix / IAM und Fachowner |
| Zu ergänzen | Gruppe, Rolle, Zielressource, Objektentscheidung und Entzugsfrist |
| Spätester Entscheid | Vor Anschluss produktiver Identitäten |
| Erwarteter Abschlussbeleg | Tatsächlicher Rechteentzug am Fachobjekt |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |

Quelle: Keycloak, Server Administration Guide — <https://www.keycloak.org/docs/latest/server_admin/>
