# V07 Anwendung, Webdienst und Schnittstellen

Vorlagen-ID V07 · Vorlagenversion 1.0 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Jedes System mit einer Anwendung (Systemtypen B, C, D; bei F für Verwaltungsoberflächen der Plattform) |
| Ausfüllen | Anwendungsbetreuung mit dem IT-Betrieb; Schnittstellen mit den Verantwortlichen der Partnersysteme |
| Prüfen | Systemverantwortliche Person und ISB |
| Zeitpunkt | Bei Einrichtung; Aktualisierung bei Versionswechsel, neuer Schnittstelle oder geänderter Konfiguration |
| Normbezug | APP.6, APP.3.1, APP.3.2, OPS.1.1.6, bei Eigenentwicklung CON.8; ISO/IEC 27001:2022 Anhang A 5.14, 8.24, 8.25, 8.26, 8.29, 8.31 |

## Schritt 1: Software

| Feld | Eintrag |
| --- | --- |
| Produkt und Version | {{Produkt, Version}} |
| Hersteller bzw. Projekt | {{Hersteller}} |
| Lizenz und Lizenzprüfung | {{Lizenz}}, {{Ergebnis der Prüfung nach [FIRMENANGABE V-07]}} |
| Bezugsquelle und Prüfung der Echtheit | {{Quelle, Prüfsumme bzw. Signatur}} |
| Support bzw. Wartung der Version bis | {{Datum}} |
| Eigenentwicklung | {{nein / ja: Release-Manifest bzw. Release-Nummer}} |

## Schritt 2: Komponenten

| Komponente | Aufgabe | Läuft auf bzw. in | Port (siehe V03) | Version |
| --- | --- | --- | --- | --- |
| {{Komponente}} | {{Auswahl: Weboberfläche; Backend; Hintergrundverarbeitung; Cache bzw. Puffer; Datenbank; Reverse Proxy}} | {{Host oder Container}} | {{Port}} | {{Version}} |

Architekturskizze als Anlage: {{Dateiname}}

## Schritt 3: Konfiguration

| Feld | Eintrag |
| --- | --- |
| Ablage der Konfiguration | {{Git-Pfad bzw. Konfigurationsmanagement}} |
| Konfigurationsparameter mit Sicherheitsbezug | {{Liste mit Werten, ohne Geheimnisse}} |

Prüfpunkte:

- ☐ Debug- bzw. Entwicklungsmodus ist aus.
- ☐ Standardkonten und Standardpasswörter sind entfernt bzw. geändert (siehe V04).
- ☐ Beispielinhalte und nicht benötigte Module bzw. Plugins sind entfernt.
- ☐ Verwaltungsoberflächen sind nur aus der Management-Zone oder für Administrationsrollen erreichbar.
- ☐ Grenzen für Uploads und Anfragen sind gesetzt.
- ☐ Sicherheitsrelevante HTTP-Header sind gesetzt (zum Beispiel Strict-Transport-Security, Content-Security-Policy, X-Content-Type-Options, frame-ancestors).

## Schritt 4: Anmeldung und Rechte in der Anwendung

| Feld | Eintrag |
| --- | --- |
| Anmeldeverfahren | {{Auswahl: OIDC über Keycloak; SAML; LDAP; lokal}}, {{Client-ID}} |
| Abbildung von Gruppen auf Rollen | {{siehe V04 Schritt 4}} |
| Sitzungsdauer und Abmeldung | {{Dauer; Abmeldung über alle Anwendungen ja/nein}} |
| Lokale Konten in der Anwendung | {{keine / welche, Begründung}} |
| Feinrechte (Objekte, Mandanten) | {{Beschreibung}} |

## Schritt 5: Schnittstellen

| Schnittstelle | Richtung | Partnersystem (ID) | Protokoll | Authentisierung | Datenarten | Schutzbedarf | Spezifikation | Verantwortlich |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| {{Name}} | {{Auswahl: eingehend; ausgehend}} | {{System-ID}} | {{Auswahl: REST/OpenAPI; Ereignis über Message Broker; Datei; E-Mail; MCP; Datenbankzugriff}} | {{Verfahren}} | {{Datenarten}} | {{Stufe}} | {{Ablage}} | {{Name}} |

[HINWEIS: Direkter Zugriff fremder Systeme auf die Datenbank der Anwendung ist zu vermeiden; wenn unvermeidbar, mit eigener, eingeschränkter Datenbankrolle (V08).]

## Schritt 6: Datenablage

| Ablageort | Inhalt | Personenbezogen | Verschlüsselt | Aufbewahrung und Löschung | Gesichert (siehe V10) |
| --- | --- | --- | --- | --- | --- |
| {{Auswahl: Datenbank; Dateisystem bzw. Volume; Objektspeicher; Cache; Protokolle}} | {{Inhalt}} | {{ja/nein}} | {{ja/nein}} | {{Regel}} | {{ja/nein}} |

## Schritt 7: Webserver bzw. Reverse Proxy

| Feld | Eintrag |
| --- | --- |
| Produkt und Version | {{Produkt}} |
| TLS-Konfiguration | {{siehe V03 Schritt 6}} |
| Zugriffsprotokolle | {{Ablage, siehe V09}} |
| Ratenbegrenzung und Schutz vor Missbrauch | {{Einstellungen}} |
| Versionsangaben in Antworten unterdrückt | {{ja/nein}} |

## Schritt 8: Tests und Abnahme

| Test | Datum | Ergebnis | Nachweis |
| --- | --- | --- | --- |
| Funktionstest durch Fachbereich | {{Datum}} | {{Ergebnis}} | {{Anlage}} |
| Anmeldung und Rechte, inkl. Negativtest mit fremder Rolle | {{Datum}} | {{Ergebnis}} | {{Anlage}} |
| Schwachstellenscan der Webanwendung | {{Datum}} | {{Ergebnis}} | {{Anlage}} |
| Penetrationstest (ab Schwelle nach [FIRMENANGABE V-07]) | {{Datum oder „nicht erforderlich“}} | {{Ergebnis}} | {{Anlage}} |

## Ist-Stand erheben

| Zweck | Befehl bzw. Quelle |
| --- | --- |
| HTTP-Header und Weiterleitungen | `curl -sI https://<host>/` |
| TLS-Version und Zertifikat | `openssl s_client -connect <host>:443 -servername <host>` |
| Version der Anwendung | Versionsanzeige oder Versions-Endpunkt der Anwendung |
| Wirksame Konfiguration | Export aus der Anwendung bzw. Konfigurationsdatei aus Git |

## Unternehmensweite Festlegungen

[FIRMENANGABE V-07] Business Applications und ISB legen fest:

| Festlegung | Wert | Verantwortlich |
| --- | --- | --- |
| Zulassung von Software und Lizenzregel (zum Beispiel Technologie-Radar aus dem IT-Zielbild) | offen | Architektur-Runde |
| Standard-Anmeldeverfahren für Anwendungen | offen | Identitätsmanagement |
| Pflicht-Header und Mindestkonfiguration für Webdienste | offen | ISB |
| Schwelle für Penetrationstests (zum Beispiel ab Schutzbedarf hoch oder bei Erreichbarkeit aus dem Internet) | offen | ISB |
| Ablage von Schnittstellenspezifikationen | offen | Business Applications |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    | Feld | Eintrag |
    | --- | --- |
    | Produkt und Version | Paperless-ngx 2.18.4 |
    | Hersteller bzw. Projekt | Open-Source-Projekt paperless-ngx |
    | Lizenz | GPL-3.0; zulässig nach Lizenzregel, Prüfung LIZ-2026-019 |
    | Bezugsquelle | Container-Image aus dem Projekt-Repository, gespiegelt in die interne Registry, Signatur geprüft |
    | Support bis | Community-Projekt; neue Versionen etwa monatlich, Aktualisierung nach V11 |
    | Eigenentwicklung | nein |

    | Komponente | Aufgabe | Läuft in | Port | Version |
    | --- | --- | --- | --- | --- |
    | webserver | Weboberfläche, API, Texterkennung, Hintergrundverarbeitung | Container webserver | 8000 intern | 2.18.4 |
    | db | Datenbank | Container db | 5432 intern | PostgreSQL 17.6 |
    | broker | Aufgabenpuffer | Container broker | 6379 intern | Valkey 8.1 |
    | proxy | TLS, Reverse Proxy | Container proxy | 443, 80 | nginx 1.28 |

    Konfiguration in apps/flowdoc/flowdoc.env und compose.yaml. Sicherheitsrelevant: PAPERLESS_DEBUG=false, PAPERLESS_URL=<https://flowdoc.flowcorp.example>, PAPERLESS_ALLOWED_HOSTS=flowdoc.flowcorp.example, Anmeldung nur über OIDC, lokale Anmeldung nach Einrichtung abgeschaltet, Uploadgrenze 100 MB in nginx. Alle Prüfpunkte erfüllt; Content-Security-Policy im Bericht-Modus bis 31.12.2026, weil die Oberfläche noch Anpassungen braucht.

    Anmeldung: OIDC über Keycloak, Client flowdoc; Rollen aus AD-Gruppen (V04); Sitzungsdauer 8 Stunden; Abmeldung über alle Anwendungen über Keycloak; keine lokalen Konten außer dem gesperrten Einrichtungskonto.

    | Schnittstelle | Richtung | Partner | Protokoll | Authentisierung | Datenarten | Schutzbedarf | Spezifikation | Verantwortlich |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | Belegabruf | eingehend | SYS-0011 Mailserver | IMAPS | Konto svc-paperless-imap | Eingangsrechnungen | hoch | IF-2026-031 | Plattformbetrieb |
    | Belegverweis | ausgehend an Abfrage | SYS-0031 FLOWERP | REST-API der Anwendung | Token erp-verweis | Metadaten, PDF | hoch | IF-2026-032 | Business Applications |
    | KI-Suche | ausgehend an Abfrage | SYS-0050 DMS-MCP-Server | REST-API, nur lesend | technisches Konto, später Delegation | Texte freigegebener Dokumente | hoch | IF-2026-040 | KI-Plattformteam |

    | Ablageort | Inhalt | Personenbezogen | Verschlüsselt | Aufbewahrung | Gesichert |
    | --- | --- | --- | --- | --- | --- |
    | Datenbank | Metadaten, Tags, Benutzer, Rechte | ja | ja (Datenträger) | wie Dokumente | ja |
    | Volume flowdoc_media | Originale und PDF/A | ja | ja (Datenträger) | nach Dokumenttyp, siehe V01 | ja |
    | Volume flowdoc_data | Suchindex | ja | ja (Datenträger) | wird neu aufgebaut | ja |
    | Protokolle | Zugriffe, Fehler | ja | – | 90 Tage zentral | über zentrale Protokollierung |

    | Test | Datum | Ergebnis | Nachweis |
    | --- | --- | --- | --- |
    | Funktionstest Rechnungswesen | 17.11.2026 | bestanden | TEST-2026-0442 |
    | Rechte, Negativtest mit Rolle flowdoc-lesen auf Rechnungen | 17.11.2026 | Zugriff korrekt verweigert | TEST-2026-0443 |
    | Schwachstellenscan der Webanwendung | 19.11.2026 | 0 hoch, 2 mittel (behoben am 20.11.) | SCAN-2026-0711 |
    | Penetrationstest | – | nicht erforderlich, nur intern erreichbar | Entscheidung ISB vom 12.11.2026 |
