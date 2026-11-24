# 07 Domänenprofile, Normen und Bewertung der KI-Werkzeuge

Arbeitsreferenz SE-07 · Stand 24.11.2026 · Arbeitsentwurf zur internen Abstimmung

Der Prozess nach dem V-Modell ist für alle Bereiche gleich. Was sich unterscheidet, sind die geltenden Normen, die Prüftiefe und die Nachweise. Das regeln vier Domänenprofile. Ein Vorhaben kann mehrere Profile berühren, etwa Firmware, Prüfstandsoftware und eine App im selben Projekt; dann gilt je Teilsystem das passende Profil.

Die folgende Zuordnung ist ein Arbeitsvorschlag. Ob eine Norm oder ein Gesetz tatsächlich gilt, hängt vom konkreten Produkt, Markt und Kunden ab und wird je Vorhaben festgestellt [FIRMENANGABE E-07].

## Profil A: IT-Anwendungen für den eigenen Betrieb

| Bereich | Bezug |
| --- | --- |
| Informationssicherheit | ISO/IEC 27001:2022 Anhang A 8.25 bis 8.34 (sichere Entwicklung, Tests, Trennung der Umgebungen, Änderungen); IT-Grundschutz CON.8 Software-Entwicklung, CON.10 Entwicklung von Webanwendungen, APP.7 Entwicklung von Individualsoftware, OPS.1.1.6 Software-Tests und -Freigaben |
| Datenschutz | DSGVO, insbesondere Datenschutz durch Technikgestaltung (Art. 25) und gegebenenfalls Datenschutz-Folgenabschätzung |
| KI-Einsatz | KI-Verordnung, insbesondere KI-Kompetenz der Beschäftigten (Art. 4); Empfehlungen von BSI und ANSSI zu KI-Programmierassistenten |
| Betrieb | Vorlagensatz Systemdokumentation (V00 bis V14) für jedes in Betrieb gehende System |

## Profil B: Produktsoftware und Firmware

Software, die mit einem Produkt an Kunden geht, etwa die Firmware eines Steuergeräts.

| Bereich | Bezug |
| --- | --- |
| Cybersicherheit von Produkten | EU-Cyberresilienzverordnung (Verordnung (EU) 2024/2847) für Produkte mit digitalen Elementen: Meldepflichten für aktiv ausgenutzte Schwachstellen und schwerwiegende Vorfälle seit 11.09.2026, die übrigen Pflichten ab 11.12.2027; dazu gehören sichere Entwicklung, Schwachstellenbehandlung, Unterstützungszeitraum, SBOM und technische Dokumentation |
| Sicherer Entwicklungsprozess | IEC 62443-4-1 (Lebenszyklus sicherer Produktentwicklung) und IEC 62443-4-2 (technische Anforderungen an Komponenten) für industrielle Automatisierung; im Fahrzeugbereich ISO/SAE 21434 |
| Funktionale Sicherheit (nur K3) | Je nach Produkt IEC 61508, ISO 13849, IEC 62061 oder ISO 26262 |
| Maschinen und Funk | Maschinenverordnung (EU) 2023/1230 ab 20.01.2027, soweit Steuerungen sicherheitsrelevant sind; bei Funkschnittstellen die Cybersicherheitsanforderungen nach der Funkanlagenrichtlinie |
| Prozessbewertung durch Kunden | Automotive SPICE, wenn Kunden es fordern; das V-Modell dieses Konzepts entspricht dessen System- und Softwareprozessen |
| Open-Source-Lizenzen | Mit der Auslieferung entstehen Lizenzpflichten (zum Beispiel Quelltextangebot bei Copyleft-Lizenzen); Lizenzprüfung je Komponente vor der Serienfreigabe |
| Aufbewahrung | Technische Dokumentation und Nachweise mindestens so lange, wie Gesetz und Kunden es verlangen; nach der Cyberresilienzverordnung zehn Jahre bzw. für die Dauer des Unterstützungszeitraums, falls länger |

## Profil C: Prüf-, Mess- und Fertigungssoftware

Software, die Prüfentscheidungen trifft, Messwerte erzeugt oder Maschinen in der Fertigung steuert, etwa Prüfstandsoftware oder Erweiterungen des MES.

| Bereich | Bezug |
| --- | --- |
| Qualitätsmanagement | Validierung vor dem Einsatz und nach jeder Änderung nach den Vorgaben des QM-Systems (zum Beispiel ISO 9001, bei Automotive IATF 16949); Bezug auf Prüfplan und Messmittelfähigkeit |
| Sicherheit an Anlagen | Wenn die Software Bewegungen oder Energie steuert: Bewertung nach Maschinensicherheit, gegebenenfalls K3 |
| Betrieb | Vorlagensatz Systemdokumentation, wenn die Software auf Servern bzw. Fertigungsrechnern betrieben wird |

## Profil D: Engineering-Werkzeuge, Skripte und Berechnungen

Kleine Werkzeuge im Engineering, etwa Auswerteskripte, Berechnungstools oder Automatisierung von CAD und Simulation.

| Bereich | Bezug |
| --- | --- |
| Prozess | In der Regel Projektklasse S mit Kurzweg; Versionierung im Git statt auf Laufwerken |
| Validierung | Wenn Ergebnisse in Produktentscheidungen oder Nachweise eingehen: Prüfung mit bekannten Referenzfällen und Dokumentation des Gültigkeitsbereichs |

## Bewertung der KI als Entwicklungswerkzeug

Normen der funktionalen Sicherheit verlangen, Software-Werkzeuge danach zu bewerten, wie sehr ihre Fehler in das Produkt gelangen können und wie sicher solche Fehler entdeckt werden (zum Beispiel Werkzeugklassen nach IEC 61508-3 oder Tool Confidence Level nach ISO 26262-8). KI-Agenten, die Code, Tests oder Anforderungen erzeugen, sind solche Werkzeuge.

| Grundsatz | Umsetzung |
| --- | --- |
| Ergebnisse statt Werkzeug absichern | Ein Sprachmodell lässt sich nicht wie ein klassisches Werkzeug qualifizieren. Deshalb wird jedes Ergebnis, das in sicherheitsrelevante Teile eingeht, durch Verfahren geprüft, die Fehler unabhängig vom Werkzeug entdecken: menschliches Review, Tests gegen die Vorgabe, statische Analyse, Abdeckungsmessung. |
| Werkzeugbewertung dokumentieren | Für jede Agentenrolle, die in K2- oder K3-Anteilen arbeitet, gibt es eine Werkzeugbewertung mit Einsatzzweck, möglichen Fehlern, Entdeckungsmaßnahmen und Ergebnis. |
| Werkzeugkette einfrieren | Modell, Modellversion, Quantisierung, Prompt bzw. Rollenvertrag, Gateway-Regeln und Compiler werden je Release festgehalten (Teil 09). Ein Wechsel löst eine Neubewertung mit den festgelegten Referenzfällen aus. |
| Einschränkung bei K3 | In K3-Anteilen erstellt die KI nur Entwürfe und Prüfhinweise. Verantwortlich für jedes Ergebnis ist eine qualifizierte Person, die es prüft, als wäre es von einem Menschen erstellt. |
| Kundenvorgaben | Manche Kunden schränken den Einsatz von KI in ihren Projekten ein oder verlangen eine Offenlegung. Das wird je Projekt in EP1 geklärt. |

## Kontrollzuordnung für ISMS und QM

| ISO/IEC 27001:2022 Anhang A | Maßnahme in diesem Konzept | Beleg |
| --- | --- | --- |
| 5.8 Informationssicherheit im Projektmanagement | Einstufung und Sicherheitsplan in der Projektplanung (Teil 01) | Projekthandbuch, Einstufung |
| 8.25 bis 8.27 sichere Entwicklung, Anforderungen, Architektur | Linke Seite des V-Modells mit Sicherheitsanalysen (Teil 03) | Baselines, Architekturentscheidungen, Bedrohungsmodell |
| 8.28 und 8.29 sicheres Programmieren und Testen | Codierrichtlinien, Reviews, Tests auf allen Ebenen (Teil 04) | CI-Berichte, Reviews, Testberichte |
| 8.30 ausgelagerte Entwicklung | Lieferanten im Projektstrukturplan mit gleichen Vorgaben | Lieferantenvereinbarung, Nachweise der Lieferanten |
| 8.31 bis 8.33 Trennung der Umgebungen, Änderungen, Testdaten | Getrennte Umgebungen, Änderungssteuerung, synthetische Testdaten (Teile 08, 09) | Netztest, Changes, Datenherkunft |
| 5.3, 5.15 bis 5.18, 8.4 Aufgabentrennung, Zugriff, Quellcode | Rollen und Rechte (Teile 06, 08) | Rollenmatrix, Entzugstest |

Ist ISO 9001 im Geltungsbereich, ordnet das Qualitätsmanagement die Entscheidungspunkte den Anforderungen an Entwicklung (Planung, Eingaben, Steuerung, Ergebnisse, Änderungen) zu. Die konkrete Zuordnung zu Grundschutz-Anforderungen erfolgt im betrieblichen Grundschutzmodell; bei einer Umstellung auf Grundschutz++ wird sie nachgezogen.

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE E-07] Qualität, ISB, Produktverantwortung und Recht stellen je Domänenprofil fest, welche Normen und Gesetze tatsächlich gelten (insbesondere Cyberresilienzverordnung, funktionale Sicherheit, Kundenvorgaben), welche Zertifikate vorhanden sind und welche Kundenverträge den Einsatz von KI regeln. Für Profil B und C wird eine Werkzeugbewertung der Agentenrollen erstellt.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Normprofil und Werkzeugbewertung / Qualität mit ISB und Produktverantwortung |
| Zu ergänzen | Geltende Normen je Profil, Zertifikate, Kundenvorgaben zu KI, Werkzeugbewertung |
| Spätester Entscheid | Vor EP1 des ersten Projekts im jeweiligen Profil |
| Erwarteter Abschlussbeleg | Freigegebenes Normprofil je Domäne und Werkzeugbewertung |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |
