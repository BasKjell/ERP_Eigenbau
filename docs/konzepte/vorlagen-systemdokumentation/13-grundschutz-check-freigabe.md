# V13 Grundschutz-Check, Freigabe und Inbetriebnahme

Vorlagen-ID V13 · Vorlagenversion 1.0 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Alle Systemtypen. Letztes Dokument vor der Inbetriebnahme. |
| Ausfüllen | IT-Betrieb mit der systemverantwortlichen Person |
| Prüfen und freigeben | ISB, systemverantwortliche Person, bei personenbezogenen Daten Datenschutz; Freigabeberechtigte nach [FIRMENANGABE V-13] |
| Zeitpunkt | Vor Inbetriebnahme; erneut bei wesentlicher Änderung und im Überprüfungsintervall |
| Normbezug | IT-Grundschutz-Check nach BSI-Standard 200-2, Risikoanalyse nach BSI-Standard 200-3; ISO/IEC 27001:2022 Abschnitt 6.1.3 und Anhang A 5.36, 8.29, 8.32 |

## Schritt 1: Vollständigkeit der Dokumentation

| Vorlage | Laut V01 erforderlich | Dokument-ID | Status | Geprüft von |
| --- | --- | --- | --- | --- |
| V01 bis V12 je Zeile | {{ja / entfällt / Verweis Plattform}} | {{Dokument-ID}} | {{Auswahl: Entwurf; in Prüfung; freigegeben}} | {{Name}} |

## Schritt 2: IT-Grundschutz-Check

[HINWEIS: Für jeden in V01 Schritt 6 als zutreffend modellierten Baustein werden alle Anforderungen der Stufen Basis und Standard geprüft, bei hohem Schutzbedarf zusätzlich die Anforderungen für erhöhten Schutzbedarf, soweit die Risikoanalyse sie vorsieht. Anforderungs-ID und Titel kommen aus dem geltenden Kompendium bzw. aus dem ISMS-Werkzeug. Wird ein ISMS-Werkzeug genutzt, genügt dessen Export als Anlage.]

| Anforderung (ID, Titel) | Stufe | Umsetzung | Nachweis bzw. Begründung | Maßnahme und Termin | Verantwortlich |
| --- | --- | --- | --- | --- | --- |
| {{ID, Titel}} | {{Auswahl: Basis; Standard; erhöht}} | {{Auswahl: ja; teilweise; nein; entbehrlich}} | {{Verweis auf Vorlage und Schritt, bei „entbehrlich“ Begründung}} | {{bei „teilweise“ oder „nein“}} | {{Name}} |

## Schritt 3: Risikoanalyse

| Feld | Eintrag |
| --- | --- |
| Erforderlich laut V01 Schritt 7 | {{ja/nein}} |
| Risikoregister-IDs | {{IDs}} |
| Ergebnis | {{zusätzliche Maßnahmen, verbleibende Risiken}} |

## Schritt 4: Abweichungen und Restrisiken

[HINWEIS: Hier stehen alle nicht erfüllten Prüfpunkte aus V01 bis V12, alle nicht oder teilweise umgesetzten Anforderungen und alle genehmigten Ausnahmen.]

| Abweichung | Risiko | Behandlung | Akzeptiert von | Befristet bis |
| --- | --- | --- | --- | --- |
| {{Abweichung}} | {{Bewertung}} | {{Auswahl: beheben; mindern; akzeptieren; vermeiden}} | {{befugte Person}} | {{Datum}} |

## Schritt 5: Abnahmetests

| Test | Ergebnis | Datum | Nachweis |
| --- | --- | --- | --- |
| Portscan stimmt mit V03 überein | {{Ergebnis}} | {{Datum}} | {{Anlage}} |
| Härtungsprüfung nach V02 | {{Ergebnis}} | {{Datum}} | {{Anlage}} |
| Schwachstellenscan ohne offene kritische Befunde (V11) | {{Ergebnis}} | {{Datum}} | {{Anlage}} |
| Anmeldung und Rechte, inklusive Negativtest (V04, V07) | {{Ergebnis}} | {{Datum}} | {{Anlage}} |
| Protokollweiterleitung und Testalarm (V09) | {{Ergebnis}} | {{Datum}} | {{Anlage}} |
| Wiederherstellungstest (V10) | {{Ergebnis}} | {{Datum}} | {{Anlage}} |
| Funktionstest bzw. fachliche Abnahme (V07) | {{Ergebnis}} | {{Datum}} | {{Anlage}} |
| Betrieb durch Vertretung nach Handbuch (V12) | {{Ergebnis}} | {{Datum}} | {{Anlage}} |

## Schritt 6: Datenschutz und Mitbestimmung

- ☐ Eintrag im Verzeichnis der Verarbeitungstätigkeiten ist angelegt bzw. aktualisiert.
- ☐ Über eine Datenschutz-Folgenabschätzung ist entschieden.
- ☐ Der Betriebsrat ist beteiligt, wenn das System zur Verhaltens- oder Leistungskontrolle geeignet ist (§ 87 Abs. 1 Nr. 6 BetrVG).

## Schritt 7: Freigabe

| Rolle | Name | Entscheidung | Bedingungen | Datum |
| --- | --- | --- | --- | --- |
| Systemverantwortliche Person | {{Name}} | {{Auswahl: freigegeben; freigegeben mit Auflagen; abgelehnt}} | {{Auflagen}} | {{Datum}} |
| IT-Betrieb | {{Name}} | {{Entscheidung}} | {{Auflagen}} | {{Datum}} |
| ISB | {{Name}} | {{Entscheidung}} | {{Auflagen}} | {{Datum}} |
| Datenschutz (bei personenbezogenen Daten) | {{Name}} | {{Entscheidung}} | {{Auflagen}} | {{Datum}} |

## Schritt 8: Inbetriebnahme

- ☐ Inventar bzw. CMDB auf „in Betrieb“ gesetzt.
- ☐ Überwachung und Alarmierung aktiv.
- ☐ Datensicherung läuft und meldet Erfolg.
- ☐ Alle Dokumente im DMS freigegeben und mit nächstem Überprüfungsdatum versehen.
- ☐ Befristete Freigaben (Firewall, Ausnahmen) haben Wiedervorlagen.

| Feld | Eintrag |
| --- | --- |
| Datum der Inbetriebnahme | {{Datum}} |
| Nächste Überprüfung | {{Datum}} |

## Unternehmensweite Festlegungen

[FIRMENANGABE V-13] Geschäftsführung und ISB legen fest:

| Festlegung | Wert | Verantwortlich |
| --- | --- | --- |
| Freigabeberechtigte je Schutzbedarf und Risikohöhe | offen | Geschäftsführung |
| Wer Restrisiken bis zu welcher Höhe akzeptieren darf | offen | Geschäftsführung |
| ISMS-Werkzeug für Grundschutz-Check und Risikoregister | offen | ISB |
| Pflicht-Abnahmetests je Schutzbedarf | offen | ISB |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    | Vorlage | Erforderlich | Dokument-ID | Status | Geprüft von |
    | --- | --- | --- | --- | --- |
    | V01 | ja | SYS-0042-V01 | freigegeben | ISB, 12.11.2026 |
    | V02 bis V05, V07 bis V12 | ja | SYS-0042-V02 bis -V12 | freigegeben | Tim Wolf, 20.11.2026 |
    | V06 | entfällt | – | – | – |

    Grundschutz-Check (Auszug). Die Anforderungs-IDs im Beispiel sind Platzhalter; echte IDs und Titel kommen aus dem geltenden Kompendium bzw. dem ISMS-Werkzeug.

    | Anforderung | Stufe | Umsetzung | Nachweis bzw. Begründung | Maßnahme | Verantwortlich |
    | --- | --- | --- | --- | --- | --- |
    | SYS.1.6.Axx Images nur aus vertrauenswürdigen Quellen | Basis | ja | V05 Schritt A1 und A2 | – | Plattformbetrieb |
    | SYS.1.6.Axx Container ohne root-Rechte | Standard | teilweise | V05 Schritt B3: webserver und db starten als root und wechseln dann den Benutzer | Prüfung eines Images ohne Start als root bis 31.03.2027 | Plattformbetrieb |
    | APP.3.2.Axx Sichere Konfiguration des Webservers | Basis | ja | V07 Schritt 3 und 7 | – | Plattformbetrieb |
    | APP.4.3.Axx Datenbanksicherung | Basis | ja | V08 Schritt 6, V10 | – | Plattformbetrieb |
    | SYS.1.1.Axx Hochverfügbarkeit | erhöht | entbehrlich | Verfügbarkeit normal, RTO 8 Stunden mit Wiederherstellung erreicht | – | – |

    Risikoanalyse: RISK-2026-077; zusätzliche Maßnahmen Datenträgerverschlüsselung, Objektsperre der Sicherung, halbjährliche Rezertifizierung.

    | Abweichung | Risiko | Behandlung | Akzeptiert von | Befristet bis |
    | --- | --- | --- | --- | --- |
    | Offene hohe CVE im Image webserver | mittel | akzeptieren bis zum Update | ISB | 31.12.2026 |
    | Content-Security-Policy nur im Bericht-Modus | gering | mindern, Umstellung geplant | ISB | 31.12.2026 |
    | Container starten teilweise als root | gering | mindern, siehe Grundschutz-Check | IT-Leitung | 31.03.2027 |

    Abnahmetests: alle acht bestanden zwischen 17. und 20.11.2026, Nachweise als Anlagen A1 bis A8.

    Datenschutz: VVT-Eintrag VT-2026-018 angelegt; DSFA nicht erforderlich (Entscheidung Datenschutz vom 06.11.2026); Betriebsrat informiert, Betriebsvereinbarung IT-Systeme 2025 deckt die Protokollierung ab.

    | Rolle | Name | Entscheidung | Bedingungen | Datum |
    | --- | --- | --- | --- | --- |
    | Systemverantwortliche Person | Julia Neumann | freigegeben mit Auflagen | Abweichungen fristgerecht beheben | 21.11.2026 |
    | IT-Betrieb | Mara Klein | freigegeben | – | 21.11.2026 |
    | ISB | Dr. Anna Roth | freigegeben mit Auflagen | wie oben | 21.11.2026 |
    | Datenschutz | Datenschutzkoordination | freigegeben | – | 21.11.2026 |

    Inbetriebnahme am 24.11.2026; alle Prüfpunkte erfüllt; nächste Überprüfung 24.11.2027, Wiedervorlagen für 31.12.2026 und 31.03.2027 angelegt.
