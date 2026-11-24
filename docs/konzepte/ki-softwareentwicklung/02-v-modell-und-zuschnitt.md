# 02 Das V-Modell als Rahmen und sein Zuschnitt

Arbeitsreferenz SE-02 · Stand 24.11.2026 · Arbeitsentwurf zur internen Abstimmung

Das Konzept folgt dem V-Modell. Die linke Seite zerlegt das Vorhaben von den Anforderungen der Nutzer bis zum Feinentwurf. Unten wird umgesetzt. Die rechte Seite setzt die Teile wieder zusammen und prüft auf jeder Ebene gegen das Dokument, das auf der linken Seite auf derselben Höhe entstanden ist. Die KI-Agenten arbeiten auf beiden Seiten, aber nie als Ersteller und Prüfer desselben Ergebnisses.

Die Ebenen orientieren sich an den Lebenszyklusprozessen der ISO/IEC/IEEE 15288 (System) und 12207 (Software) und sind mit Automotive SPICE und dem V-Modell XT des Bundes vereinbar. Die Entscheidungspunkte sind an das V-Modell XT angelehnt. Welches Referenzmodell im Einzelfall verbindlich ist, ergibt sich aus Domänenprofil und Kundenvorgaben (Teil 07).

![Links absteigend Projektplanung, Anforderungen, Systemanforderungen, Systemarchitektur, Software-Anforderungen, Software-Architektur und Feinentwurf; unten Implementierung; rechts aufsteigend Modulverifikation, Software-Integration, Software-Verifikation, Systemintegration, Systemverifikation und Abnahme. Waagerechte Linien verbinden jede Prüfung mit ihrer Vorgabe. An den Kästen stehen die zuständigen Agenten und Entscheidungspunkte.](bilder/01_V-Modell.png)

*Abbildung 01: V-Modell mit Projektplanung, KI-Agenten und Entscheidungspunkten*

## Ebenen und ihre Prüfung

| Ebene links (Vorgabe) | Ergebnis | Ebene rechts (Prüfung) | Prüft gegen |
| --- | --- | --- | --- |
| Projektplanung | Projekthandbuch, Projektstrukturplan, Arbeitspakete (Teil 01) | Projektabschluss | Projektziele und Pläne |
| Anforderungen der Nutzer bzw. Kunden | Lastenheft bzw. Fachauftrag, Abnahmekriterien | Abnahme (Validierung) | Ist es das richtige System für den Zweck? |
| Systemanforderungen | Pflichtenheft bzw. Systemanforderungen inkl. Sicherheit, Leistung, Betrieb | Systemverifikation | Erfüllt das integrierte System jede Systemanforderung? |
| Systemarchitektur | Teilsysteme, Schnittstellen, Aufteilung Hardware/Software, Bedrohungsmodell | Systemintegration und Integrationstest | Arbeiten die Teilsysteme über ihre Schnittstellen richtig zusammen? |
| Software-Anforderungen | Anforderungen je Softwareteilsystem | Software-Verifikation | Erfüllt die Software ihre Anforderungen? |
| Software-Architektur | Komponenten, Schnittstellen, Datenflüsse, dynamisches Verhalten | Software-Integration und Integrationstest | Arbeiten die Komponenten richtig zusammen? |
| Feinentwurf | Entwurf der einzelnen Module bzw. Einheiten | Modulverifikation | Tut jedes Modul, was sein Entwurf verlangt? |
| Implementierung | Code, Konfiguration, Unit-Tests | (Spitze des V) | – |

Bei reiner IT-Software ohne eigene Hardware fallen System- und Softwareebene oft zusammen; dann gilt nur eine Anforderungs- und eine Architekturebene. Bei Produktsoftware und Firmware sind beide Ebenen getrennt, weil Hardware, Mechanik und Software zusammen das System bilden.

## Entscheidungspunkte

| Entscheidungspunkt | Inhalt | Bisheriger Prüfpunkt |
| --- | --- | --- |
| EP0 Projekt genehmigt | Projektauftrag, Einstufung, Budget (Teil 01) | neu |
| EP1 Projekt definiert | Projekthandbuch, Zuschnitt, Projektstrukturplan, Pläne (Teil 01) | neu |
| EPi Iteration geplant | Detailplan des nächsten Inkrements (Teil 01) | neu |
| EP2 Anforderungen festgelegt | Baseline der Nutzer- und Systemanforderungen mit Abnahmekriterien | G1 Auftrag und Baseline |
| EP3 System entworfen | System- und Software-Architektur, Bedrohungsmodell, Teststrategie je Ebene | G2 Architektur |
| EP4 Feinentwurf abgeschlossen | Feinentwurf der Module, sofern im Zuschnitt vorgesehen | neu |
| EP5 Systemelemente realisiert und integriert | Code geprüft, Modul- und Integrationstests bestanden | G3 Integration |
| EP6 System verifiziert | Software- und Systemverifikation bestanden, Nachweise vollständig | neu |
| EP7 Abnahme erfolgt | Validierung durch Fachbereich bzw. Kunde am konkreten Stand | G4 Fachabnahme |
| EP8 Lieferung freigegeben | Release-Freigabe und Auslieferung bzw. Serienfreigabe | G5 Produktion |
| EP9 Projekt abgeschlossen | Übergabe in Betrieb bzw. Serienbetreuung, Erfahrungen festgehalten | neu |

Die Prüfpunkte G1 bis G5 des bisherigen KI-Entwicklungskonzepts bleiben als Kurzweg für kleine Änderungen erhalten.

## Zuschnitt nach Projektklasse

| Element | S klein | M mittel | L groß |
| --- | --- | --- | --- |
| Projektplanung | Ticket mit Einstufung | Vereinfachter Plan, Arbeitspakete je Release | Vollständig nach Teil 01, Planung in Wellen |
| Ebenen links | Eine Anforderungs- und eine Architekturebene, Architektur meist nur Passungsprüfung | Software-Anforderungen und Software-Architektur; Systemebene bei Produktsoftware | Alle Ebenen; je Teilsystem ein eigenes V unterhalb der Systemebene |
| Feinentwurf | entfällt | wo die Architektur es verlangt | für alle Komponenten mit K2 oder K3 |
| Ebenen rechts | Unit-Tests, Abnahmetest | Modul-, Integrations- und Software-Verifikation, Abnahme | Alle Ebenen, zusätzlich Systemintegration und Systemverifikation |
| Entscheidungspunkte | EP2, EP3 (vereinfacht), EP5, EP7, EP8 | EP0 bis EP3, EP5 bis EP8 | Alle, EPi je Inkrement |

## Zuschnitt nach Kritikalität

| Element | K1 normal | K2 erhöht | K3 kritisch |
| --- | --- | --- | --- |
| Prüfung durch Menschen | Stichprobe, Abnahme | Architektur, kritische Änderungen, Abnahme, Release | Jedes sicherheitsrelevante Ergebnis nach Normvorgabe, mit geforderter Unabhängigkeit |
| Sicherheit | Sicherheitsanforderungen, Scans | Bedrohungsmodell, Sicherheitstests, bei Produkten Bedrohungs- und Risikoanalyse | Zusätzlich Safety-Analysen und Bestätigungsmaßnahmen nach Norm |
| Rolle der KI | Erstellt und prüft gegenseitig nach Teil 06 | Wie K1, menschliche Prüfung an den genannten Stellen | Erstellt nur Entwürfe und Prüfhinweise; Verantwortung und Prüfung liegen bei qualifizierten Menschen; KI-Werkzeuge werden nach Norm bewertet (Teil 07) |
| Nachweise | Release-Manifest | Vollständige Nachverfolgung über alle Ebenen | Wie K2, plus Sicherheitsnachweis bzw. Safety Case nach Norm |

## Kurzweg für kleine Änderungen

Für vorab genehmigte Änderungsarten an bestehenden Systemen (Projektklasse S, K1) gilt der bewährte Ablauf: bestätigter Auftrag (G1), Passung zur freigegebenen Architektur (G2), geprüfte Integration (G3), fachliche Abnahme am konkreten Stand (G4) und Auslieferung über den Freigabedienst (G5). Er ist ein verkürztes V: Die Ebenen sind dieselben, nur zusammengefasst. Wird bei der Arbeit erkennbar, dass die Änderung eine Schnittstelle, eine Datenklasse, eine Vertrauensgrenze oder eine Sicherheitsfunktion berührt, wird sie neu eingestuft und verlässt den Kurzweg.

## Inkremente und agiles Arbeiten

Das V-Modell schreibt keine Wasserfall-Abfolge vor. Große Vorhaben laufen in Inkrementen; jedes Inkrement durchläuft das V für seinen Umfang, innerhalb eines Inkrements kann in kurzen Sprints gearbeitet werden. Verbindlich sind nicht die Reihenfolge der Tätigkeiten, sondern die Entscheidungspunkte und die Verbindung jeder Prüfung mit ihrer Vorgabe.

## Was bei einer Änderung verfällt

- Eine geänderte Anforderung erzeugt eine neue Baseline und markiert alle verbundenen Architekturelemente, Tests und Dokumente als „erneut prüfen“.
- Eine geänderte Schnittstelle markiert die Integrationstests beider Seiten.
- Ein neuer Commit entwertet das Code-Review des alten Stands.
- Ein anderer Release-Digest entwertet die darauf bezogene Verifikation und Abnahme.
- Eine geänderte Werkzeugkette, etwa ein neues Modell, eine neue Compiler-Version oder ein neuer Prompt, löst die in Teil 07 festgelegte Neubewertung aus.

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE E-02] Qualitätsmanagement und Entwicklungsleitungen legen fest, welches Referenzmodell je Domänenprofil verbindlich ist (zum Beispiel unternehmenseigenes Prozessmodell, V-Modell XT, Automotive SPICE), welche Dokumente je Ebene Pflicht sind und welche Änderungsarten den Kurzweg nutzen dürfen. Ein vorhandenes Entwicklungshandbuch geht vor und wird hier verwiesen.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Prozessmodell und Zuschnitt / Qualitätsmanagement |
| Zu ergänzen | Referenzmodell je Profil, Pflichtdokumente je Ebene, Liste der Kurzweg-Änderungsarten |
| Spätester Entscheid | Vor dem ersten Pilotprojekt der Klasse M |
| Erwarteter Abschlussbeleg | Freigegebene Zuschnittstabelle im Entwicklungshandbuch |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |
