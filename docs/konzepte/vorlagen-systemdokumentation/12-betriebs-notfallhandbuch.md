# V12 Betriebs- und Notfallhandbuch

Vorlagen-ID V12 · Vorlagenversion 1.1 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Alle Systemtypen |
| Ausfüllen | IT-Betrieb |
| Prüfen | Vertretung im Betrieb (muss das System allein nach diesem Handbuch betreiben können), Notfallmanagement |
| Zeitpunkt | Vor Inbetriebnahme; Aktualisierung bei jeder Änderung an Abläufen, Kontakten oder Abhängigkeiten |
| Normbezug | OPS.1.1.2, DER.2.1, DER.4; ISO/IEC 27001:2022 Anhang A 5.24, 5.25, 5.26, 5.29, 5.30, 5.37 |

## Schritt 1: Kontakte

| Rolle | Name bzw. Team | Erreichbarkeit | Vertretung |
| --- | --- | --- | --- |
| Systemverantwortliche Person | {{Name}} | {{Telefon, Zeiten}} | {{Name}} |
| Technischer Betrieb | {{Team}} | {{Kanal}} | {{Name}} |
| Rufbereitschaft | {{Team}} | [FIRMENANGABE V-12] | – |
| Hersteller bzw. Dienstleister | {{Firma}} | {{Hotline, Vertragsnummer}} | – |
| ISB bzw. Meldestelle für Sicherheitsvorfälle | {{Stelle}} | [FIRMENANGABE V-12] | – |

[HINWEIS: Zugangsdaten zu Herstellerportalen stehen im Secret-Manager, nicht hier.]

## Schritt 2: Betriebszeiten und Service-Level

| Feld | Eintrag |
| --- | --- |
| Betriebszeit | {{zum Beispiel Mo–Fr 6–20 Uhr}} |
| Service-Level-Klasse | {{Klasse nach [FIRMENANGABE V-12]}} |
| Wartungsfenster | {{siehe V11 Schritt 3}} |

## Schritt 3: Routinetätigkeiten

| Tätigkeit | Häufigkeit | Durchführung (Runbook) | Verantwortlich |
| --- | --- | --- | --- |
| {{Tätigkeit}} | {{Häufigkeit}} | {{Verweis}} | {{Name}} |

[HINWEIS: Typisch sind Prüfung der Alarme und Sicherungsläufe, Rezertifizierung der Konten (V04), Wiederherstellungstest (V10), Prüfung der Zertifikate, Überprüfung dieser Dokumentation.]

## Schritt 4: Start, Stopp und Funktionsprüfung

| Vorgang | Reihenfolge und Befehle | Erwartetes Ergebnis |
| --- | --- | --- |
| Start | {{Schritte}} | {{Ergebnis}} |
| Stopp | {{Schritte}} | {{Ergebnis}} |
| Neustart einer Komponente | {{Schritte}} | {{Ergebnis}} |
| Funktionsprüfung nach Start | {{zum Beispiel Health-Check-Adresse, Testanmeldung}} | {{Ergebnis}} |

## Schritt 5: Abhängigkeiten im Betrieb

| System | Wenn es ausfällt | Was hier zu tun ist |
| --- | --- | --- |
| {{System-ID}} | {{Auswirkung}} | {{Maßnahme}} |

## Schritt 6: Bekannte Störungen

| Fehlerbild | Ursache | Lösung | Eskalation |
| --- | --- | --- | --- |
| {{Fehlerbild}} | {{Ursache}} | {{Lösung}} | {{an wen, ab wann}} |

## Schritt 7: Notfall und Wiederanlauf

| Szenario | Erstmaßnahmen | Wiederanlauf | Ersatzverfahren für die Nutzer | Zielzeit |
| --- | --- | --- | --- | --- |
| {{Auswahl: Ausfall Hardware bzw. Plattform; Datenverlust bzw. Beschädigung; Kompromittierung; Ausfall einer Abhängigkeit}} | {{Maßnahmen}} | {{Verweis auf V10 Schritt 5}} | {{manueller Ablauf}} | {{RTO}} |

## Schritt 8: Sicherheitsvorfall

| Schritt | Vorgehen |
| --- | --- |
| Erkennen und melden | Verdacht sofort an [FIRMENANGABE V-12] melden. |
| Erstmaßnahmen | {{zum Beispiel System vom Netz trennen bzw. isolieren, Beweise sichern, keine Neuinstallation vor Freigabe durch die Vorfallbearbeitung}} |
| Meldepflichten prüfen | Datenschutz prüft die Meldung an die Aufsichtsbehörde innerhalb von 72 Stunden (Art. 33 DSGVO). Fällt das Unternehmen unter NIS2, gelten zusätzlich die Meldefristen an das BSI. |
| Kommunikation | {{wer informiert Nutzer, Leitung, gegebenenfalls Kunden}} |

## Schritt 9: Notfallkarte

[HINWEIS: Eine Seite zum Ausdrucken bzw. zur Ablage im Notfallhandbuch; sie muss auch ohne IT erreichbar sein.]

| Feld | Eintrag |
| --- | --- |
| System | {{System-ID, Name}} |
| Wichtig für | {{Prozesse}} |
| Bei Ausfall zuerst anrufen | {{Rufbereitschaft}} |
| Ersatzverfahren | {{Kurzfassung}} |
| Wiederanlauf | {{Verweis}} |
| Ort der Sicherungen und Schlüssel | {{Verweis}} |

## Unternehmensweite Festlegungen

[FIRMENANGABE V-12] IT-Leitung, Notfallmanagement und ISB legen fest:

| Festlegung | Wert | Verantwortlich |
| --- | --- | --- |
| Rufbereitschaft und Erreichbarkeit | offen | IT-Leitung |
| Meldestelle und Meldeweg für Sicherheitsvorfälle | offen | ISB |
| Service-Level-Klassen | offen | IT-Leitung |
| Ablage des Notfallhandbuchs (auch offline verfügbar) | offen | Notfallmanagement |
| NIS2-Betroffenheit und Meldewege an das BSI | offen | ISB |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    | Rolle | Name bzw. Team | Erreichbarkeit | Vertretung |
    | --- | --- | --- | --- |
    | Systemverantwortliche Person | Julia Neumann | Durchwahl 2140, Mo–Fr 8–17 Uhr | Tim Becker |
    | Technischer Betrieb | Team Plattformbetrieb | Ticket-Queue „Plattform“ | Mara Klein |
    | Rufbereitschaft | Plattform | Rufnummer laut Bereitschaftsplan | – |
    | Hersteller bzw. Dienstleister | keiner (Community-Projekt) | – | – |
    | Meldestelle Sicherheitsvorfälle | ISB | Sicherheits-Hotline laut Intranet | – |

    Betriebszeit Mo–Fr 6–20 Uhr, Service-Level-Klasse B, Wartungsfenster dienstags 19–21 Uhr.

    | Tätigkeit | Häufigkeit | Runbook | Verantwortlich |
    | --- | --- | --- | --- |
    | Alarme und Sicherungsläufe prüfen | täglich | RB-FLOWDOC-03 | Plattformbetrieb |
    | Wiederherstellungstest vollständig | halbjährlich | RB-FLOWDOC-02 | Plattformbetrieb |
    | Rezertifizierung der Rollen | halbjährlich | V04 Schritt 9 | Systemverantwortliche Person |
    | Überprüfung dieser Dokumentation | jährlich | – | Plattformbetrieb |

    | Vorgang | Reihenfolge und Befehle | Erwartetes Ergebnis |
    | --- | --- | --- |
    | Start | `sudo systemctl start flowdoc` (startet `docker compose up -d` im Projektordner; Reihenfolge db, broker, webserver, proxy über Abhängigkeiten) | alle vier Container „healthy“ |
    | Stopp | `sudo systemctl stop flowdoc` | keine Container des Projekts aktiv |
    | Neustart einer Komponente | `sudo docker compose -p flowdoc restart webserver` | Container wieder „healthy“ |
    | Funktionsprüfung | Aufruf <https://flowdoc.flowcorp.example>, Anmeldung mit Testkonto, Suche nach Testdokument „PRÜFDOK-001“ | Anmeldung erfolgreich, Testdokument gefunden |

    | System | Wenn es ausfällt | Maßnahme |
    | --- | --- | --- |
    | SYS-0005 Keycloak | Keine Anmeldung | Warten auf Wiederherstellung; bei Dringlichkeit Notfallkonto nach Freigabe |
    | SYS-0011 Mailserver | Keine neuen Belege | Nichts tun; Abruf läuft nach Wiederherstellung automatisch nach |

    | Fehlerbild | Ursache | Lösung | Eskalation |
    | --- | --- | --- | --- |
    | Upload hängt bei großen PDFs | Grenze in nginx | Grenze prüfen, Datei teilen | Plattformbetrieb |
    | Neue Mails werden nicht verarbeitet | Passwort des IMAP-Kontos abgelaufen | Rotation nach V04 nachziehen | Plattformbetrieb |

    | Szenario | Erstmaßnahmen | Wiederanlauf | Ersatzverfahren | Zielzeit |
    | --- | --- | --- | --- | --- |
    | Ausfall der VM | Plattformstatus prüfen, Neustart über Plattform | sonst V10 Schritt 5 | Belege bleiben im Postfach; Buchung mit Papierkopie | 8 Std. |
    | Kompromittierung | Netz trennen, ISB informieren, Beweise sichern | Neuaufbau nach Freigabe durch Vorfallbearbeitung | wie oben | nach Freigabe |

    Notfallkarte: liegt als Blatt „SYS-0042“ im Notfallhandbuch Band IT, Stand 21.11.2026.
