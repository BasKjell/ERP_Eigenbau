# V01 Systemsteckbrief und Schutzbedarf

Vorlagen-ID V01 · Vorlagenversion 1.1 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Alle Systemtypen. Erstes Dokument jedes Systems. |
| Ausfüllen | Systemverantwortliche Person gemeinsam mit dem IT-Betrieb |
| Prüfen | ISB; bei personenbezogenen Daten zusätzlich Datenschutz |
| Zeitpunkt | Vor Beschaffung oder Installation; Aktualisierung bei jeder wesentlichen Änderung |
| Normbezug | Orientierung: BSI-Standard 200-2 (Strukturanalyse, Schutzbedarfsfeststellung); ISO/IEC 27001:2022 Anhang A 5.9, 5.12, 5.31, 5.34 |

## Schritt 1: System identifizieren

| Feld | Eintrag |
| --- | --- |
| System-ID | {{System-ID}} [HINWEIS: nach Namenskonvention aus V00] |
| Systemname | {{Systemname}} |
| Zweck in einem Satz | {{Zweck}} |
| Systemtyp | {{Auswahl: A Grundinstallation; B Anwendung direkt; C Docker/Compose; D Kubernetes; E Datenbankserver; F Plattform}} |
| Umgebung | {{Auswahl: Produktion; Test; Entwicklung}} |
| Produkt, Hersteller bzw. Projekt, Version | {{Produkt}} |
| Lizenz | {{Lizenz}} [HINWEIS: bei Open Source die konkrete Lizenz, zum Beispiel GPL-3.0; bei Kaufsoftware Lizenzmodell und Vertrag] |
| Betriebsort | {{Auswahl: eigene Hardware; VM auf Virtualisierungsplattform; Docker-Host; Kubernetes-Cluster}}: {{Name bzw. Dokument-ID der Plattform}} |
| Herstellersupport bzw. Wartungsvertrag bis | {{Datum}} |
| Inventar- bzw. CMDB-Eintrag | {{Eintrags-ID}} |
| Lebenszyklus-Status | {{Auswahl: geplant; im Aufbau; in Betrieb; in Stilllegung; stillgelegt}} |

## Schritt 2: Verantwortung festlegen

| Rolle | Name | Vertretung |
| --- | --- | --- |
| Systemverantwortliche Person (fachlich, entscheidet über Nutzung und Risiken) | {{Name}} | {{Name}} |
| Technisch verantwortlich (Betrieb) | {{Name oder Team}} | {{Name}} |
| Prozessverantwortliche im Fachbereich | {{Name}} | {{Name}} |
| Dienstleister mit Zugriff | {{Firma, Vertragsnummer oder „keiner“}} | – |
| Ansprechperson Datenschutz | {{Name}} | – |

## Schritt 3: Einbettung beschreiben

| Feld | Eintrag |
| --- | --- |
| Unterstützte Geschäftsprozesse | {{Prozesse}} |
| Nutzerkreis und ungefähre Anzahl | {{Nutzerkreis}} |
| Erreichbar aus | {{Auswahl: nur intern; intern und über VPN; aus dem Internet}} |

Abhängigkeiten:

| Richtung | System (ID) | Zweck | Auswirkung bei Ausfall |
| --- | --- | --- | --- |
| {{Auswahl: nutzt; wird genutzt von}} | {{System-ID}} | {{Zweck}} | {{Auswirkung}} |

## Schritt 4: Daten erfassen

| Informationsart | Personenbezogen | Besondere Kategorien (Art. 9 DSGVO) | Herkunft | Aufbewahrungsfrist | Führendes System |
| --- | --- | --- | --- | --- | --- |
| {{Informationsart}} | {{ja/nein}} | {{ja/nein}} | {{Herkunft}} | {{Frist}} | {{dieses System oder anderes}} |

| Feld | Eintrag |
| --- | --- |
| Eintrag im Verzeichnis der Verarbeitungstätigkeiten | {{Nummer oder „nicht erforderlich“}} |
| Vertrag zur Auftragsverarbeitung | {{Vertragsnummer oder „nicht erforderlich“}} |
| Datenschutz-Folgenabschätzung erforderlich | {{ja/nein, Begründung}} |

## Schritt 5: Schutzbedarf feststellen

[HINWEIS: Kategorien und Schadensszenarien nach [FIRMENANGABE V-01]. Es gilt das Maximumprinzip: Der höchste Schutzbedarf der verarbeiteten Informationen und der abhängigen Prozesse bestimmt den Schutzbedarf des Systems. Kumulations- und Verteilungseffekt prüfen (BSI-Standard 200-2).]

| Grundwert | Schutzbedarf | Begründung (welcher Schaden in welchem Szenario) |
| --- | --- | --- |
| Vertraulichkeit | {{Auswahl: normal; hoch; sehr hoch}} | {{Begründung}} |
| Integrität | {{Auswahl: normal; hoch; sehr hoch}} | {{Begründung}} |
| Verfügbarkeit | {{Auswahl: normal; hoch; sehr hoch}} | {{Begründung}} |

| Kennwert | Eintrag |
| --- | --- |
| Maximal tolerierbare Ausfallzeit (wird RTO in V10) | {{Stunden oder Tage}} |
| Maximal tolerierbarer Datenverlust (wird RPO in V10) | {{Stunden}} |

## Schritt 6: Verweis auf das Anforderungssystem

[HINWEIS: Welche Anforderungen aus IT-Grundschutz oder ISO/IEC 27001 dieses System betreffen und welche davon die Systemdokumentation erfüllt, ordnet der ISB im Anforderungs- bzw. ISMS-System zu. Hier steht nur der Verweis; eine Prüfliste je Anforderung gehört nicht in die Systemdokumentation.]

| Feld | Eintrag |
| --- | --- |
| Objekt im Anforderungs- bzw. ISMS-System | {{ID oder Name}} |
| Risikoregister-ID, falls geführt | {{ID oder „keine“}} |

## Schritt 7: Vorlagen auswählen

[HINWEIS: Auswahl nach der Matrix in V00. Bei „Verweis Plattform“ die Dokument-ID der Plattformdokumentation eintragen.]

| Vorlage | Entscheidung | Begründung | Dokument-ID |
| --- | --- | --- | --- |
| V02 bis V14 je Zeile | {{Auswahl: Pflicht; entfällt; Verweis Plattform; später}} | {{Begründung}} | {{Dokument-ID}} |

## Unternehmensweite Festlegungen

[FIRMENANGABE V-01] ISB und Datenschutz legen fest:

| Festlegung | Wert | Verantwortlich |
| --- | --- | --- |
| Schutzbedarfskategorien mit Schadensszenarien und Schwellen (zum Beispiel finanzieller Schaden, Verstoß gegen Gesetze, Beeinträchtigung der Aufgabenerfüllung) | offen | ISB |
| Ablage von Inventar bzw. CMDB, Risikoregister und Verzeichnis der Verarbeitungstätigkeiten | offen | IT-Leitung, Datenschutz |
| Wann ein System als „wesentlich geändert“ gilt | offen | ISB |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    | Feld | Eintrag |
    | --- | --- |
    | System-ID | SYS-0042 |
    | Systemname | FLOWDOC Dokumentenmanagement |
    | Zweck in einem Satz | Erfassen, Verschlagworten und Wiederfinden von Eingangsbelegen, Verträgen und Arbeitsanweisungen |
    | Systemtyp | C Docker/Compose |
    | Umgebung | Produktion |
    | Produkt | Paperless-ngx 2.18 (Projekt paperless-ngx), PostgreSQL 17, Valkey 8, nginx 1.28 |
    | Lizenz | Paperless-ngx GPL-3.0; PostgreSQL-Lizenz; Valkey BSD-3-Clause; nginx BSD-2-Clause |
    | Betriebsort | VM auf Virtualisierungsplattform VIRT-01 (Dokument PLT-0003-V01) |
    | Herstellersupport bis | Community-Projekt ohne Vertrag; Supportende je Version in V11 |
    | CMDB-Eintrag | CI-10442 |
    | Lebenszyklus-Status | im Aufbau |

    | Rolle | Name | Vertretung |
    | --- | --- | --- |
    | Systemverantwortliche Person | Julia Neumann, Leitung Rechnungswesen | Tim Becker |
    | Technisch verantwortlich | Team Plattformbetrieb | Mara Klein |
    | Dienstleister mit Zugriff | keiner | – |
    | Ansprechperson Datenschutz | Datenschutzkoordination | – |

    | Richtung | System (ID) | Zweck | Auswirkung bei Ausfall |
    | --- | --- | --- | --- |
    | nutzt | SYS-0005 Keycloak | Anmeldung | Keine Anmeldung möglich; Notfallkonto siehe V04 |
    | nutzt | SYS-0011 Mailserver | Abruf von Eingangsrechnungen per IMAP | Belege bleiben im Postfach, Abruf später |
    | wird genutzt von | SYS-0031 FLOWERP | Verweis auf Belege | Belege im ERP nicht abrufbar, Buchung manuell möglich |

    | Informationsart | Personenbezogen | Besondere Kategorien | Herkunft | Aufbewahrungsfrist | Führendes System |
    | --- | --- | --- | --- | --- | --- |
    | Eingangsrechnungen | ja (Ansprechpartner) | nein | E-Mail, Scan | 8 Jahre, Archiv führend | Archiv; FLOWDOC Arbeitskopie |
    | Verträge | ja | nein | Scan | Laufzeit plus 6 Jahre | FLOWDOC |
    | Arbeitsanweisungen | nein | nein | Fachbereiche | bis Ersatz plus 2 Jahre | FLOWDOC |

    | Grundwert | Schutzbedarf | Begründung |
    | --- | --- | --- |
    | Vertraulichkeit | hoch | Verträge und Rechnungen mit personenbezogenen Daten und Konditionen; Offenlegung schadet Kunden- und Lieferantenbeziehungen |
    | Integrität | hoch | Veränderte Belege führen zu Fehlbuchungen und Verstößen gegen Aufbewahrungspflichten |
    | Verfügbarkeit | normal | Ausfall bis ein Arbeitstag überbrückbar; Belege kommen weiter per E-Mail an |

    Maximal tolerierbare Ausfallzeit: 8 Stunden. Maximal tolerierbarer Datenverlust: 24 Stunden.

    Anforderungssystem: Objekt SYS-0042 im ISMS-Werkzeug; die Zuordnung zu den Anforderungen führt der ISB. Risikoregister-ID RISK-2026-077.
