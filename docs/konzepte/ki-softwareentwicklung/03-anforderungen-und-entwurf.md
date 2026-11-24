# 03 Linke Seite: Anforderungen und Entwurf

Arbeitsreferenz SE-03 · Stand 24.11.2026 · Arbeitsentwurf zur internen Abstimmung

Die linke Seite des V-Modells legt fest, was gebaut wird und wie es aufgebaut ist. Jede Ebene liefert eine Vorgabe, gegen die auf der rechten Seite geprüft wird. Deshalb entsteht zu jeder Vorgabe sofort ein Prüfgedanke: Jede Anforderung hat ein Abnahme- bzw. Prüfkriterium, jede Schnittstelle einen Integrationstest.

## Anforderungen der Nutzer bzw. Kunden

| Merkmal | Festlegung |
| --- | --- |
| Quelle | Fachauftrag, Lastenheft, Kundenspezifikation, Normen, Prüfpläne, Gesetze |
| Ergebnis | Nutzeranforderungen mit Abnahmekriterien; bei Kundenprojekten Abgleich mit dem Lastenheft |
| Agenten | 1 analysiert Quellen und schreibt Entwürfe; 2 prüft gegen Quelle und auf Lücken |
| Entscheidet | Product Owner bzw. Fachbereich; bei Kundenprojekten zusätzlich Abstimmung mit dem Kunden |

Bei Lastenheften von Kunden markiert Agent 1 jede Stelle als „übernommen“, „abweichend“ oder „offen“. Abweichungen und offene Punkte gehen gebündelt an die Projektleitung; Zusagen an den Kunden machen nur Menschen.

## Systemanforderungen

Aus den Nutzeranforderungen entstehen überprüfbare Systemanforderungen. Sie decken neben der Funktion auch Leistung, Schnittstellen, Sicherheit (Security und gegebenenfalls Safety), Datenschutz, Betrieb, Wartung, Update, Umgebungsbedingungen und Normvorgaben ab.

Qualitätsregeln für jede Anforderung (in Anlehnung an ISO/IEC/IEEE 29148):

- eindeutig, einzeln prüfbar, widerspruchsfrei und umsetzbar;
- mit stabiler ID, Version, Quelle, Begründung, Priorität und verantwortlicher Person;
- mit mindestens einem beobachtbaren Prüfkriterium, bei Sicherheitsanforderungen auch mit Negativfall;
- ohne versteckte Lösung, sofern die Lösung nicht selbst Vorgabe ist.

Agent 2 prüft jede Anforderung mit der Frage: Könnte eine falsche Umsetzung das Kriterium trotzdem erfüllen? Dann ist das Kriterium zu schwach.

## Systemarchitektur

| Inhalt | Beschreibung |
| --- | --- |
| Zerlegung | Teilsysteme bzw. Systemelemente mit Verantwortung; bei Produkten Aufteilung auf Hardware, Software, Mechanik |
| Schnittstellen | Jede Schnittstelle mit Protokoll, Datenformat, Zeitverhalten, Fehlerverhalten und Eigentümer; Hardware-Software-Schnittstellen besonders genau |
| Zuordnung | Jede Systemanforderung ist mindestens einem Systemelement zugeordnet |
| Sicherheit | Bedrohungsmodell; bei Produkten Bedrohungs- und Risikoanalyse; bei K3 Ergebnisse der Safety-Analysen |
| Entscheidungen | Architekturentscheidungen mit Alternativen, Begründung und Folgen |
| Teststrategie | Wie jede Ebene rechts geprüft wird und welche Testumgebung sie braucht (Simulation, Prüfstand, Hardware-in-the-Loop, Staging) |

Agent 3 entwirft, Agent 4 prüft die Sicherheit, die System- bzw. Software-Architektin entscheidet. Bei Projektklasse L passt die Projektleitung nach EP3 den Projektstrukturplan an die Architektur an (Teil 01).

## Software-Anforderungen und Software-Architektur

Für jedes Softwareteilsystem wiederholt sich das Muster eine Ebene tiefer: Software-Anforderungen aus den zugeordneten Systemanforderungen, dann Software-Architektur mit Komponenten, Schnittstellen, Datenflüssen, Speicher- und Zeitverhalten. Bei Firmware gehören dazu Ressourcenbudgets (Speicher, Laufzeit, Bus-Last), Start- und Updateverhalten und das Verhalten bei Fehlern der Hardware.

## Feinentwurf

Der Feinentwurf beschreibt einzelne Module so genau, dass sie unabhängig umgesetzt und geprüft werden können: Aufgabe, Schnittstelle, Algorithmus, Fehlerbehandlung, Grenzwerte. Er ist nach Teil 02 nur Pflicht, wo der Zuschnitt es vorsieht. Bei K3-Komponenten ist er immer Pflicht.

## Sicherheitsanalysen

| Analyse | Wann | Rolle der KI |
| --- | --- | --- |
| Bedrohungsmodell (IT-Anwendungen) | ab K1 bei neuen Vertrauensgrenzen, immer ab K2 | Agent 4 erstellt Entwurf und prüft Vollständigkeit; Sicherheitsverantwortliche entscheiden |
| Bedrohungs- und Risikoanalyse für Produkte (zum Beispiel nach IEC 62443-4-1 oder ISO/SAE 21434) | Produktsoftware ab K2 | Agent 4 erstellt Entwürfe für Bedrohungen und Angriffspfade; Bewertung und Entscheidung durch Menschen |
| Safety-Analysen (zum Beispiel FMEA, FTA) | K3 | KI darf Vorschläge für mögliche Fehlerarten liefern; Analyse, Bewertung und Freigabe nur durch qualifizierte Menschen nach Norm |
| Datenschutz (Privacy by Design, gegebenenfalls DSFA) | bei personenbezogenen Daten | Agent 1 markiert betroffene Anforderungen; Bewertung durch Datenschutz |

## Baselines und Freigaben auf der linken Seite

- Jede Ebene endet mit einer Baseline im Anforderungsmanagement bzw. im Architektur-Repository.
- „Arbeitsbaseline fixiert“ (technisch eingefroren) und „fachlich freigegeben“ (Entscheidung eines Menschen) sind getrennte Zustände.
- Agenten schreiben nur Entwürfe; das Einfrieren übernimmt der Workflow, die Freigabe ein Mensch in einer angemeldeten Oberfläche.
- Kundendaten und Kundenunterlagen bleiben im Projekt des jeweiligen Kunden. Agenten eines anderen Projekts sehen sie nicht (Teil 08).

## Beispiele

**IT (Kurzweg):** Auftrag „Der Einkauf soll freigegebene Verfahrensanweisungen nach Titel sortieren können.“ Eine Anforderung REQ-17 mit zwei Kriterien: Sortierung nach Titel und unveränderte Sichtbarkeit gesperrter Dokumente. Architektur: Passungsprüfung gegen die bestehende Anwendung, keine neue Vertrauensgrenze.

**Engineering (Projektklasse L, SCU-200):** Systemanforderung SYS-CAN-004 „Das Steuergerät beantwortet Diagnoseanfragen auf dem CAN-Bus innerhalb von 50 ms.“ Zuordnung zur Firmware-Komponente Kommunikation, Software-Anforderung SW-CAN-011 mit Zeit- und Fehlerverhalten, Integrationstest am Hardware-in-the-Loop-Platz, Systemtest am Prüfstand. Die Anforderung SYS-SAF-001 „sicherer Halt“ ist K3: Agent 3 darf einen Architekturvorschlag machen, die Sicherheitsarchitektur verantwortet und prüft die Safety-Verantwortliche nach Norm.

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE E-03] Entwicklungsleitungen legen das führende Werkzeug für Anforderungen (zum Beispiel Jama oder FLOWWORK), Dokumentvorlagen für Lastenheft, Pflichtenheft und Architektur, die Methode für Bedrohungsanalysen je Domänenprofil und die Freigaberollen je Ebene fest.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Anforderungs- und Architekturvorgaben / Entwicklungsleitungen |
| Zu ergänzen | RM-Werkzeug, Vorlagen, Analysemethoden, Freigaberollen |
| Spätester Entscheid | Vor EP2 des ersten Pilotprojekts |
| Erwarteter Abschlussbeleg | Freigegebene Vorlagen und Rollenliste |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |
