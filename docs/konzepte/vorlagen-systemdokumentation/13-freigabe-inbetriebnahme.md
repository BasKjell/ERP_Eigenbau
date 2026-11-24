# V13 Freigabe und Inbetriebnahme

Vorlagen-ID V13 · Vorlagenversion 1.1 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Alle Systemtypen. Letztes Dokument vor der Inbetriebnahme. |
| Ausfüllen | IT-Betrieb mit der systemverantwortlichen Person |
| Freigeben | Systemverantwortliche Person, IT-Betrieb, ISB, bei personenbezogenen Daten Datenschutz; Freigabeberechtigte nach [FIRMENANGABE V-13] |
| Zeitpunkt | Vor Inbetriebnahme; erneut bei wesentlicher Änderung und im Überprüfungsintervall |
| Abgrenzung | Diese Vorlage enthält keinen Grundschutz-Check und keine Prüfliste je Anforderung. Welche Anforderungen mit der Systemdokumentation erfüllt sind, ordnet der ISB im Anforderungs- bzw. ISMS-System zu. |
| Normbezug | Orientierung: ISO/IEC 27001:2022 Anhang A 5.36, 8.32 |

## Schritt 1: Übersicht der Systemdokumentation

| Vorlage | Erforderlich laut V01 | Dokument-ID | Status | Stand vom |
| --- | --- | --- | --- | --- |
| V01 bis V12 je Zeile | {{Auswahl: ja; entfällt; Verweis Plattform}} | {{Dokument-ID}} | {{Auswahl: Entwurf; in Prüfung; freigegeben}} | {{Datum}} |

## Schritt 2: Bekannte Abweichungen und Ausnahmen

[HINWEIS: Nur festhalten, was beim Dokumentieren aufgefallen ist und vom Unternehmensstandard abweicht, zum Beispiel ein offener Befund, eine befristete Firewall-Freigabe oder eine noch nicht umgesetzte Einstellung. Keine Prüfung je Anforderung.]

| Abweichung | Beschrieben in | Behandlung | Entschieden von | Befristet bis |
| --- | --- | --- | --- | --- |
| {{Abweichung}} | {{Vorlage und Schritt}} | {{Auswahl: beheben; mindern; akzeptieren}} | {{Name}} | {{Datum}} |

| Feld | Eintrag |
| --- | --- |
| Verweis auf Anforderungs- bzw. ISMS-System oder Risikoregister | {{ID oder „keiner“}} |

## Schritt 3: Datenschutz und Mitbestimmung

| Feld | Eintrag |
| --- | --- |
| Eintrag im Verzeichnis der Verarbeitungstätigkeiten | {{ID oder „keine personenbezogenen Daten“}} |
| Entscheidung zur Datenschutz-Folgenabschätzung | {{Auswahl: nicht erforderlich; durchgeführt; offen}} |
| Beteiligung des Betriebsrats (§ 87 Abs. 1 Nr. 6 BetrVG) | {{Verweis oder „nicht erforderlich“ mit Begründung}} |

## Schritt 4: Freigabe

| Rolle | Name | Entscheidung | Bedingungen | Datum |
| --- | --- | --- | --- | --- |
| Systemverantwortliche Person | {{Name}} | {{Auswahl: freigegeben; freigegeben mit Auflagen; abgelehnt}} | {{Auflagen}} | {{Datum}} |
| IT-Betrieb | {{Name}} | {{Entscheidung}} | {{Auflagen}} | {{Datum}} |
| ISB | {{Name}} | {{Entscheidung}} | {{Auflagen}} | {{Datum}} |
| Datenschutz (bei personenbezogenen Daten) | {{Name}} | {{Entscheidung}} | {{Auflagen}} | {{Datum}} |

## Schritt 5: Inbetriebnahme

| Feld | Eintrag |
| --- | --- |
| Datum der Inbetriebnahme | {{Datum}} |
| Status in Inventar bzw. CMDB | {{Auswahl: in Betrieb; im Aufbau}} |
| Überwachung und Datensicherung aktiv seit | {{Datum}} |
| Ablage der freigegebenen Dokumente | {{DMS-Ort}} |
| Wiedervorlagen für befristete Freigaben und Ausnahmen | {{Daten}} |
| Nächste Überprüfung | {{Datum}} |

## Unternehmensweite Festlegungen

[FIRMENANGABE V-13] Geschäftsführung und ISB legen fest:

| Festlegung | Wert | Verantwortlich |
| --- | --- | --- |
| Freigabeberechtigte je Schutzbedarf | offen | Geschäftsführung |
| Wer Abweichungen bis zu welcher Höhe akzeptieren darf | offen | Geschäftsführung |
| Anforderungs- bzw. ISMS-System, in dem die Zuordnung zu Anforderungen geführt wird | offen | ISB |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    | Vorlage | Erforderlich | Dokument-ID | Status | Stand vom |
    | --- | --- | --- | --- | --- |
    | V01 | ja | SYS-0042-V01 | freigegeben | 12.11.2026 |
    | V02 bis V05, V07 bis V12 | ja | SYS-0042-V02 bis -V12 | freigegeben | 20.11.2026 |
    | V06 | entfällt | – | – | – |

    | Abweichung | Beschrieben in | Behandlung | Entschieden von | Befristet bis |
    | --- | --- | --- | --- | --- |
    | Offene hohe CVE im Image webserver | V05 Schritt A3 | akzeptieren bis zum Update | ISB | 31.12.2026 |
    | Content-Security-Policy nur im Bericht-Modus | V07 Schritt 3 | mindern, Umstellung geplant | ISB | 31.12.2026 |
    | Container webserver und db starten als root und wechseln dann den Benutzer | V05 Schritt B3 | mindern, Image ohne Start als root prüfen | IT-Leitung | 31.03.2027 |

    Verweis: Objekt SYS-0042 im ISMS-Werkzeug, Risikoregister RISK-2026-077.

    | Feld | Eintrag |
    | --- | --- |
    | Verzeichnis der Verarbeitungstätigkeiten | VT-2026-018 |
    | Datenschutz-Folgenabschätzung | nicht erforderlich (Entscheidung Datenschutz vom 06.11.2026) |
    | Betriebsrat | informiert; Betriebsvereinbarung IT-Systeme 2025 deckt die Protokollierung ab |

    | Rolle | Name | Entscheidung | Bedingungen | Datum |
    | --- | --- | --- | --- | --- |
    | Systemverantwortliche Person | Julia Neumann | freigegeben mit Auflagen | Abweichungen fristgerecht beheben | 21.11.2026 |
    | IT-Betrieb | Mara Klein | freigegeben | – | 21.11.2026 |
    | ISB | Dr. Anna Roth | freigegeben mit Auflagen | wie oben | 21.11.2026 |
    | Datenschutz | Datenschutzkoordination | freigegeben | – | 21.11.2026 |

    | Feld | Eintrag |
    | --- | --- |
    | Datum der Inbetriebnahme | 24.11.2026 |
    | Status in der CMDB | in Betrieb (CI-10442) |
    | Überwachung und Datensicherung aktiv seit | 20.11.2026 |
    | Ablage der freigegebenen Dokumente | DMS, Akte SYS-0042 |
    | Wiedervorlagen | 31.12.2026 und 31.03.2027 |
    | Nächste Überprüfung | 24.11.2027 |
