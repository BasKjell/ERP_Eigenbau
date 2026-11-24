# 05 Oben rechts: Abnahme, Release und Betrieb

Arbeitsreferenz SE-05 · Stand 24.11.2026 · Arbeitsentwurf zur internen Abstimmung

Oben rechts im V wird geprüft, ob das richtige System entstanden ist, und es wird ausgeliefert. Für IT-Anwendungen heißt Auslieferung Inbetriebnahme. Für Produktsoftware heißt sie Freigabe zur Serie, Übergabe an Produktion und Service und Pflege im Feld.

## Abnahme (Validierung)

| Merkmal | IT-Anwendung | Produktsoftware |
| --- | --- | --- |
| Wer nimmt ab | Product Owner bzw. Key User | Produktverantwortung, bei Kundenprojekten der Kunde nach vereinbartem Verfahren |
| Woran | Vorgegebene Szenarien im Staging am konkreten Release-Digest | Validierung im Zielumfeld bzw. am Prüfstand am konkreten Softwarestand und Hardwarestand |
| Ergebnis | Entscheidung, Person, Zeitpunkt, Digest, Begründung | wie IT, zusätzlich Bezug auf Hardware-Revision und Variante |
| Bei Ablehnung | Ticket, neuer Kandidat, erneute Prüfung der betroffenen Kriterien | wie IT |

Agent 7 bereitet Abnahmeszenarien aus den Abnahmekriterien vor. Die Abnahme selbst erklärt ein Mensch in einer angemeldeten Oberfläche; ein Agent kann sie weder erteilen noch vorwegnehmen.

## Release und Auslieferung

- Agent 10 stellt das Nachweispaket zusammen; der Manifest-Dienst prüft die Belege selbst, versioniert und signiert das Release-Manifest (Teil 09).
- **IT:** Der Deploymentdienst liefert nur den abgenommenen Digest aus, prüft Freigabe, Rückfallplan und Zeitfenster (bisher G5).
- **Produktsoftware:** Die Freigabe zur Serie erfolgt nach dem Freigabeprozess des Unternehmens. Das signierte Softwarepaket wird an Produktion (Programmierstation) und Service übergeben. Bei Updates im Feld gelten Signaturprüfung, Rückfallmöglichkeit und Freigabe für die betroffenen Varianten.
- Bei Projektklasse L gibt es für jedes Inkrement eine eigene Lieferung; die Abnahme des Gesamtsystems findet am Ende statt.

## Betrieb und Pflege

| Thema | IT-Anwendung | Produktsoftware |
| --- | --- | --- |
| Verantwortung | Service Owner | Produktverantwortung mit Produkt-Sicherheitsteam |
| Überwachung | Monitoring, Protokolle (siehe Vorlagensatz Systemdokumentation) | Rückmeldungen aus Service und Feld |
| Schwachstellen | Agent 11 gleicht SBOMs mit Meldungen ab; Service Owner bewertet | wie IT; zusätzlich Meldepflichten für aktiv ausgenutzte Schwachstellen nach der EU-Cyberresilienzverordnung, soweit das Produkt darunter fällt (Teil 07) |
| Unterstützungszeitraum | Laufzeit der Anwendung | Festgelegter Unterstützungszeitraum mit Sicherheitsupdates, gegenüber Kunden kommuniziert |
| Änderungen | Neues Vorhaben mit Einstufung nach Teil 01; kleine Änderungen über den Kurzweg | Neues Vorhaben; Änderungen an freigegebenen Produkten laufen zusätzlich über das Änderungsverfahren der Serie |

## Projektabschluss

EP9 schließt das Projekt: Übergabe an Betrieb bzw. Serienbetreuung ist bestätigt, offene Punkte haben Eigentümer, Erfahrungen sind festgehalten, das Nachweispaket ist archiviert. Agent 0 übernimmt Kennzahlen des Projekts (Schätzung und Ist je Arbeitspaket) in die Vergleichsbasis.

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE E-05] Produktverantwortung, Qualität und IT-Betrieb legen den Freigabeprozess zur Serie, Abnahmeverfahren mit Kunden, Unterstützungszeiträume je Produkt, das Verfahren für Updates im Feld und die Zuständigkeit für Meldungen von Schwachstellen fest.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Abnahme, Freigabe und Feldbetreuung / Produktverantwortung und Qualität |
| Zu ergänzen | Serienfreigabe, Kundenabnahme, Unterstützungszeitraum, Update-Verfahren, Meldewege |
| Spätester Entscheid | Vor EP7 des ersten Produktsoftware-Projekts |
| Erwarteter Abschlussbeleg | Freigegebene Prozessbeschreibung |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |
