# 4 Portal, Anmeldung und Integration

Arbeitsentwurf zur internen Abstimmung · Stand 20.11.2026 · SSO über Keycloak ist festgelegt. Weitere Produktauswahl und Zeiträume sind offen.

Der erste Portalstand zeigt die erlaubten Anwendungen und führt Mitarbeitende direkt zur Aufgabe im führenden System. Eine Einkäuferin öffnet etwa aus „Meine Aufgaben“ die zu prüfende Bestellung im ERP. Das ERP prüft ihre aktuelle Zuständigkeit und zeichnet die Entscheidung auf. Das Portal benötigt dafür kein allgemeines Buchungs- oder Freigaberecht.

## Ein Einstieg mit schrittweisem Ausbau

| Ausbaustufe | Nutzererlebnis | Beleg für die Abnahme |
|---|---|---|
| 1 · Einstieg | Eine Startseite mit Anmeldung über Keycloak und Deep Links. Eigenentwicklungen nutzen gemeinsame Bedienelemente. | Ein deaktivierter Nutzer erhält keinen Zugang. Ein Link auf ein fremdes Objekt wird auch beim Direktaufruf abgewiesen. |
| 2 · Aufgaben | Adapter liefern ID, zulässigen Anzeigetext, Fälligkeit und Link. Die Freigabe erfolgt im Fachsystem. | Nach Umzuweisung oder Vertretungsende verschwinden Titel und Metadaten auch aus der zwischengespeicherten Übersicht. |
| 3 · Suche | DMS, Wiki, Tickets und freigegebene ERP-Daten werden getrennt indiziert. Eine spätere KI-Suche nutzt denselben Berechtigungsdienst. | Dokumentrecht während einer Sitzung entziehen. Treffer, Titel, Zitate, Vorschau und Cache bleiben danach gesperrt. |
| 4 · Selbstbedienung | Kontoverwaltung, MFA und Vertretungen über die fachlich zuständigen Dienste. Ein vorhandenes Portal kann den selbstgebauten Startbildschirm ersetzen. | Zuständigkeit und Rücknahme eines Vertretungsrechts sind im Zielsystem nachvollziehbar. |

## Keycloak als zentraler SSO-Dienst

Active Directory bleibt zunächst die führende Quelle für Benutzerkonten und Gruppen. Keycloak bindet AD über eine lesende LDAP-Föderation mit TLS (LDAPS) an und setzt die MFA für die interaktive Anmeldung durch. Portal, ERP und DMS erhalten jeweils einen eigenen Keycloak-Client. Neue Anwendungen verwenden OpenID Connect, geeignete Bestandsprodukte können SAML 2.0 verwenden. Unterstützt ein Produkt keines der Verfahren, dokumentiert der Anwendungseigner den Übergangsweg. [Q19]

Beispiel: Eine Einkäuferin meldet sich über Keycloak am Portal an und öffnet einen DMS-Link. Das DMS nutzt die bereits bestehende Keycloak-Sitzung für seine eigene Anmeldung. Die zugeordnete AD-Gruppe kann die Anwendungsrolle Einkauf vermitteln. Ob die Einkäuferin genau diese Dokumentrevision lesen oder freigeben darf, entscheidet das DMS anhand seiner aktuellen Rechte.

Für produktive Business Applications und die KI-Entwicklung werden getrennte Realms als Betriebsmodell vorgesehen. Clients, Rollen und Dienstkonten werden je Realm verwaltet. Aufgerufene APIs prüfen Aussteller und Zielressource des Tokens. Ein Token eines Entwicklungsagenten darf keinen Zugriff auf das produktive DMS eröffnen. Die gemeinsame AD-Anbindung ermöglicht beiden Bereichen dasselbe Benutzerkonto. Realmübergreifendes SSO würde eine eigene Vertrauensbeziehung und Prüfung erfordern.

## Lebenszyklus und Rechteentzug

Die Personalschnittstelle führt Beschäftigungsstatus und Organisation. Das Zielsystem entscheidet über Objekt, Revision, Mandant und Aktion. Für jede Anwendung gelten eigene Tests für Rollenabbildung, lokale Sitzungen, Tokenlaufzeit und Logout. Ein Back-Channel-Logout wird nur als wirksam geführt, wenn die konkrete Anwendung ihn verarbeitet. Bei unerreichbarer Rechtequelle bleiben geschützte Suchergebnisse gesperrt.

Keycloak authentifiziert die Person, während ein Dienst mit eigener Identität arbeitet. Ein schreibender Adapter prüft beides: die Befugnisse seiner Rolle und bei delegiertem Auftrag die der Person. KI-Entwicklungsagenten arbeiten in Nicht-Produktion. Ein späterer produktiver Suchdienst erhält eigene Konten und Berechtigungen. Die Indextechnik (pgvector, OpenSearch oder Qdrant) entscheidet diese Frage nicht.

## Führende Systeme und Austauschmuster

| Geschäftsobjekt | Fachlich führend im Zielentwurf | Konsumenten |
|---|---|---|
| Technischer Artikelstand, Zeichnung, Engineering-Stückliste | PLM nach bestätigtem Freigabeprozess | ERP übernimmt freigegebenen Stand samt Revision. DMS führt bei Bedarf einen referenzierten Beleg. |
| Beschaffung, Fertigungsauftrag, Lager, Kontierung und Buchung | ERP | DMS erhält Belegreferenz. BI erhält freigegebenen Auszug. |
| Geschäftsdokument und Aufbewahrungsentscheidung | DMS mit Archivfunktion und benanntem Dateneigner | Portal, ERP und Suche referenzieren Dokument-ID und Version. |
| Anforderungen, Tests und fachliche Abnahme von Software | RM-System, beispielsweise Jama, mit CI-Belegen | Orchestrator und Git verweisen auf Baseline und Release. |
| Ticket, Projektaufgabe, Projektplan | Zuständiges Ticket-/Projektsystem. Bei Easy Redmine und MS Project Führung je Feld und Terminfreigabe vereinbaren. | Portal zeigt zugewiesene Arbeit. Rückschreiben nur gemäß Freigaberegel. |

Synchrone Abfragen nutzen dokumentierte APIs. Ereignisse tragen ID, Quelle, Objekt-ID, Schema- und Objektversion. Bei gekoppelter Datenbankänderung und Veröffentlichung eignet sich eine transaktionale Outbox. Verbraucher speichern bereits verarbeitete Ereignisse. Wiederholung, verspätete Zustellung und Fehlerwarteschlange gehören in die Abnahme. DATEV, EDI und vorhandene Dateiimporte dürfen über kontrollierte Übergabestellen laufen. Für Berichte entstehen eigene Datenbestände mit geklärter Aktualität und Zugriffsschutz.

Beispiel Eingangsrechnung: Der Eingangsdienst sichert den empfangenen Beleg und vergibt eine stabile ID. Der ERP-Adapter ordnet Geschäftspartner und Bestellung zu. Nach Timeout fragt er den bereits erzeugten Vorgang anhand des Fremdschlüssels ab. Ein zweiter Zustellversuch erzeugt keine zweite Rechnung. Stimmen Betrag oder Identität nicht überein, bleibt der Vorgang zur fachlichen Klärung offen. Der Buchungsbeleg und das Eingangsoriginal bleiben verknüpft.

Interne Referenz: KI-Softwareentwicklung nach dem V-Modell, Teil 08, sowie SEC-IAM-001 und SEC-AI-001. Der Schutz vor unberechtigter Offenlegung ist im Pilot an jedem Ausgabeweg zu prüfen.

## Quellen und Referenzen

- [Q17] ISO/IEC 27001:2022. BSI · Prüfgrundlage für Zertifizierungen und Kompendium Edition 2023 — <https://www.iso.org/standard/27001> — <https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Grundschutz/Zertifikat/Veroeffentl/Pruefgrundlagen_Kompendium.pdf?__blob=publicationFile> — <https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Grundschutz/IT-GS-Kompendium/IT_Grundschutz_Kompendium_Edition2023.pdf?__blob=publicationFile>
- [Q19] Keycloak · Server Administration Guide, LDAP-Föderation, Realms, OIDC und SAML — <https://www.keycloak.org/docs/latest/server_admin/>
