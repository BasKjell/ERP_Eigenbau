# 00 KI-gestützte Softwareentwicklung nach dem V-Modell

Arbeitsreferenz SE-00 · Stand 24.11.2026 · Arbeitsentwurf zur internen Abstimmung

## Worum es geht

Dieses Konzept regelt, wie das Unternehmen Software mit Unterstützung lokaler KI-Agenten entwickelt, und zwar für alle Bereiche: IT-Anwendungen für den eigenen Betrieb, Produktsoftware und Firmware, Prüf- und Fertigungssoftware sowie kleine Engineering-Werkzeuge. Es reicht von der Planung großer Vorhaben mit vielen Arbeitspaketen bis zur kleinen Änderung an einer bestehenden Anwendung.

Es verallgemeinert das bisherige KI-Entwicklungskonzept, das am Beispiel eines DMS für die interne IT geschrieben war. Die bewährten Grundlagen bleiben: getrennte Agentenrollen, lokale Modelle, Rechtefluss vom AD bis zur Wissenssuche, Freigaben nur durch Menschen, Nachweise je Release. Neu sind die Projektplanung am Anfang, der ausdrückliche Bezug auf das V-Modell mit allen Ebenen, Domänenprofile für Engineering und Produkte sowie die Bewertung der KI als Entwicklungswerkzeug.

## Grundsätze

1. **Erst planen, dann spezifizieren.** Jedes Vorhaben beginnt mit Projektauftrag und Einstufung; große Vorhaben mit einem Projektstrukturplan aus Arbeitspaketen (Teil 01).
2. **Das V-Modell ist der Rahmen.** Zu jeder Vorgabe auf der linken Seite gehört eine Prüfung auf derselben Ebene rechts (Teil 02).
3. **So viel Prozess wie nötig.** Projektklasse (S, M, L) und Kritikalität (K1 bis K3) bestimmen den Zuschnitt; kleine Änderungen nutzen einen Kurzweg.
4. **KI erstellt und prüft, Menschen entscheiden.** Kein Agent prüft sein eigenes Ergebnis, kein Agent gibt frei, nimmt ab oder akzeptiert Risiken (Teil 06).
5. **Rechte gelten bis zum letzten Werkzeugaufruf.** Person, Agentenrolle und Zielkonto werden getrennt geprüft; Kundenprojekte sind voneinander getrennt (Teil 08).
6. **Nur belegte Ergebnisse zählen.** Fortschritt, Tests und Abnahmen werden aus Primärquellen nachgewiesen und im signierten Release-Manifest gebündelt (Teil 09).
7. **Bei Sicherheitsfunktionen gilt die Norm.** In K3-Anteilen liefert die KI nur Entwürfe; qualifizierte Menschen verantworten und prüfen (Teil 07).
8. **Arbeitsschutz geht vor.** Kein Agent löst an Prüfständen oder Hardware Aktionen ohne Freigabe einer berechtigten Person vor Ort aus (Teil 04).

## Bezug zum V-Modell

Das bisherige KI-Entwicklungskonzept folgte der Logik des V-Modells nur verkürzt: Seine Prüfpunkte G1 bis G5 entsprechen Anforderungen, Architektur, Integration, Abnahme und Auslieferung. System- und Integrationsebenen und die Projektplanung fehlten. Dieses Konzept baut deshalb ausdrücklich auf dem V-Modell auf.

- Die Ebenen folgen den Lebenszyklusprozessen der ISO/IEC/IEEE 15288 (System) und 12207 (Software).
- Die Entscheidungspunkte EP0 bis EP9 sind an das V-Modell XT des Bundes angelehnt („Projekt genehmigt“, „Projekt definiert“, „Anforderungen festgelegt“, „System entworfen“ und so weiter).
- Die System- und Softwareebenen entsprechen den Prozessen von Automotive SPICE, sodass Kundenbewertungen im Fahrzeugumfeld darauf aufsetzen können.
- G1 bis G5 bleiben als Kurzweg für kleine Änderungen erhalten.

![Links absteigend Projektplanung, Anforderungen, Systemanforderungen, Systemarchitektur, Software-Anforderungen, Software-Architektur und Feinentwurf; unten Implementierung; rechts aufsteigend Modulverifikation, Software-Integration, Software-Verifikation, Systemintegration, Systemverifikation und Abnahme. Waagerechte Linien verbinden jede Prüfung mit ihrer Vorgabe. An den Kästen stehen die zuständigen Agenten und Entscheidungspunkte.](bilder/01_V-Modell.png)

*Abbildung 01: V-Modell mit Projektplanung, KI-Agenten und Entscheidungspunkten*

## Ablauf in Kürze

| Abschnitt | Was passiert | Teil |
| --- | --- | --- |
| Projektplanung | Projektauftrag, Einstufung, Zuschnitt, Projektstrukturplan mit Arbeitspaketen, Planung in Wellen; EP0 und EP1 | 01 |
| Linke Seite | Anforderungen der Nutzer, Systemanforderungen, Systemarchitektur, Software-Anforderungen, Software-Architektur, Feinentwurf; EP2 bis EP4 | 03 |
| Spitze | Implementierung mit Unit-Tests und Codeprüfung | 04 |
| Rechte Seite | Modulverifikation, Integration, Software- und Systemverifikation; EP5 und EP6 | 04 |
| Oben rechts | Abnahme, Release bzw. Serienfreigabe, Betrieb und Pflege; EP7 bis EP9 | 05 |

## Die Teile des Konzepts

| Nr. und Titel | Wofür | Federführung (Vorschlag) |
| --- | --- | --- |
| 01 Projektinitiierung und Planung | Projektauftrag, Einstufung, Projektstrukturplan, Arbeitspakete, Planung in Wellen | Projektmanagement |
| 02 V-Modell und Zuschnitt | Ebenen, Entscheidungspunkte, Zuschnitt nach Klasse und Kritikalität, Kurzweg | Qualitätsmanagement |
| 03 Anforderungen und Entwurf | Linke Seite: Anforderungen aller Ebenen, Architektur, Feinentwurf, Sicherheitsanalysen | Entwicklungsleitungen |
| 04 Realisierung, Integration, Verifikation | Spitze und rechte Seite: Implementierung, Tests aller Ebenen, Testumgebungen, CI | Entwicklungsleitungen und Testmanagement |
| 05 Abnahme, Release, Betrieb | Validierung, Auslieferung bzw. Serienfreigabe, Feldbetreuung, Projektabschluss | Produktverantwortung, IT-Betrieb |
| 06 Rollen, Agenten, Unabhängigkeit | Menschliche Rollen, 13 Agentenrollen, Regeln zur Unabhängigkeit | Bereichsleitungen mit Qualität |
| 07 Domänen und Normen | Profile A bis D, geltende Normen, Bewertung der KI als Werkzeug | Qualität, ISB, Produktverantwortung |
| 08 Plattform, Identitäten, Rechte | Zonen, Identitäten, Rechtefluss, neue Werkzeuge, Kundentrennung | Plattformbetrieb |
| 09 Konfiguration, Rückverfolgbarkeit, Nachweise | Baselines, Verknüpfungen über das V, Nachweise je Entscheidungspunkt, Release-Manifest | Konfigurationsmanagement |
| 10 Arbeitsaufträge der Agenten | Systemanweisungen aller Rollen, maschinenlesbare Übergabe | KI-Plattformteam |
| 11 Einführung und Abnahmetests | Stufen von IT-Kurzweg bis Großprojekt, zusätzliche Tests 37 bis 48, Kennzahlen | Geschäftsführung mit Qualität |

## Verhältnis zu den anderen Dokumenten

| Dokument | Verhältnis |
| --- | --- |
| KI-Entwicklungskonzept (Word-Fassung und Revision vom 20.11.2026) | Wird durch dieses Konzept verallgemeinert. Die technischen Teile zu Keycloak, MCP-Verträgen, Gateway-Regeln und die Abnahmetests 01 bis 36 gelten weiter. |
| Unternehmenskonzept für den Einsatz lokaler KI | Regelt den KI-Einsatz in den Fachprozessen; dieses Konzept regelt die Entwicklung der Software dafür. |
| IT-Zielbild Business Applications | Gibt Plattform und Technologie-Standards für Profil A vor. |
| Vorlagensatz Systemdokumentation (V00 bis V14) | Dokumentiert jedes System, das in Betrieb geht. |
| Vorhandenes Entwicklungs- bzw. Projekthandbuch | Geht vor; dieses Konzept wird daran angepasst [FIRMENANGABE E-02]. |

## Was zuerst entschieden werden muss

| Zeitpunkt | Offene Firmenangaben | Ergebnis |
| --- | --- | --- |
| Vor dem technischen Pilot | E-08 Plattform und Trennung, E-10 Arbeitsaufträge, E-11 Einführungsplan | Plattform mit Abnahmetests, Pilotauswahl |
| Vor dem ersten Projekt der Klasse M | E-01 Projektklassen und Planung, E-02 Prozessmodell und Zuschnitt, E-06 Rollen | Freigegebenes Entwicklungshandbuch |
| Vor dem ersten Engineering-Projekt | E-03 Anforderungen und Architektur, E-04 Codier- und Testvorgaben, E-07 Normprofil und Werkzeugbewertung | Profil B bzw. C einsatzbereit |
| Vor der ersten Auslieferung | E-05 Abnahme und Serienfreigabe, E-09 Konfigurationsmanagement | Release-Manifest und Freigabeprozess |

Die Kennzeichnung [FIRMENANGABE E-xx] steht an jeder Stelle, an der Unternehmenswissen fehlt. Am Ende jedes Teils beschreibt eine Tabelle, wer die Angabe liefert, bis wann und mit welchem Beleg.

## Quellen für den Abgleich

- ISO/IEC/IEEE 15288 Systemlebenszyklus und ISO/IEC/IEEE 12207 Softwarelebenszyklus
- ISO/IEC/IEEE 29148 Anforderungen, ISO/IEC/IEEE 42010 Architekturbeschreibung, ISO/IEC/IEEE 29119 Softwaretest
- V-Modell XT des Bundes
- Automotive SPICE (VDA QMC)
- ISO/IEC 27001:2022 und BSI IT-Grundschutz-Kompendium, insbesondere CON.8, CON.10, APP.7, OPS.1.1.6
- Verordnung (EU) 2024/2847 (Cyberresilienzverordnung) — <https://eur-lex.europa.eu/eli/reg/2024/2847/oj>
- Verordnung (EU) 2023/1230 (Maschinenverordnung) — <https://eur-lex.europa.eu/eli/reg/2023/1230/oj>
- IEC 62443-4-1, IEC 61508, ISO 13849, ISO 26262, ISO/SAE 21434 je nach Produkt
- BSI und ANSSI, AI Coding Assistants — <https://www.bsi.bund.de/SharedDocs/Downloads/EN/BSI/KI/ANSSI_BSI_AI_Coding_Assistants.pdf?__blob=publicationFile>
- Verordnung (EU) 2024/1689 (KI-Verordnung) — <https://eur-lex.europa.eu/eli/reg/2024/1689/oj>

Normtexte werden am lizenzierten Exemplar des Unternehmens in der geltenden Ausgabe abgeglichen.
