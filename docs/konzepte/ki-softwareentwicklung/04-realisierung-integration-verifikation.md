# 04 Spitze und rechte Seite: Realisierung, Integration und Verifikation

Arbeitsreferenz SE-04 · Stand 24.11.2026 · Arbeitsentwurf zur internen Abstimmung

Unten im V wird umgesetzt. Danach werden die Teile Ebene für Ebene zusammengesetzt und geprüft. Jede Prüfung bezieht sich auf die Vorgabe derselben Höhe auf der linken Seite und auf einen konkreten, versionierten Stand.

## Implementierung

| Merkmal | Festlegung |
| --- | --- |
| Arbeitsweise | Agent 6 setzt eine Aufgabe in einem eigenen Branch bzw. Arbeitsbereich um und schreibt Unit-Tests für Normal-, Fehler- und Grenzfälle. |
| Vorgaben | Codierrichtlinien je Sprache und Profil [FIRMENANGABE E-04]; bei Firmware zusätzlich Regeln wie MISRA C bzw. MISRA C++ in der festgelegten Fassung; freigegebene Bibliotheken aus dem Paketspiegel |
| Bauen | Reproduzierbare Builds in isolierten Runnern; bei Firmware mit festgelegter, versionierter Toolchain (Compiler, Linker, Bibliotheken) |
| Neue Abhängigkeiten | Werden mit Version, Lizenz und Grund gemeldet und freigegeben |
| Verboten | Schreiben auf geschützte Branches, Ändern von Tests anderer Rollen, von CI-Regeln oder Freigaberegeln |

## Modulverifikation

- Unit-Tests gegen den Feinentwurf bzw. die Software-Anforderungen; Abdeckung nach Vorgabe des Zuschnitts.
- Statische Analyse und Prüfung der Codierrichtlinien in der CI.
- Code-Review durch Agent 8 am exakten Commit; bei K2 kritische Pfade und bei K3 alle sicherheitsrelevanten Module zusätzlich durch einen Menschen.
- Der Ersteller kann seine eigene Änderung nicht freigeben, auch nicht über eine andere Agentenrolle derselben Identität.

## Software-Integration und Integrationstest

Agent 12 leitet Integrationstests aus der Software-Architektur ab: jede Schnittstelle, jede Datenflusskette, Zeitverhalten und Fehlerfortpflanzung. Er sieht Schnittstellenbeschreibungen, aber nicht die Implementierung. Die Tests laufen in der CI bzw. in festgelegten Testjobs.

## Software-Verifikation

Agent 7 prüft die integrierte Software als Ganzes gegen die Software-Anforderungen, als Black-Box-Test ohne Zugriff auf den Quellcode. Ergebnis ist ein Testbericht je Anforderung mit Soll, Ist, Umgebung und Version.

## Systemintegration und Systemverifikation

Bei Produkten werden Software und Hardware zusammengeführt. Agent 12 spezifiziert die Systemintegrationstests aus der Systemarchitektur, Agent 7 die Systemtests aus den Systemanforderungen. Die Tests laufen auf Prüfständen und Hardware-in-the-Loop-Plätzen.

| Testumgebung | Einsatz | Regel für Agenten |
| --- | --- | --- |
| Simulation bzw. Software-in-the-Loop | Frühe Integration ohne Hardware | Agenten dürfen festgelegte Testjobs starten |
| Hardware-in-the-Loop | Firmware auf echter Steuerelektronik mit simulierter Umgebung | Nur vordefinierte Testjobs über den Testdienst; keine direkte Ansteuerung von Hardware; Sicherheitsabschaltung des Platzes bleibt unabhängig von der KI |
| Prüfstand mit realer Mechanik bzw. Last | Systemtest, Grenzwerte, Dauerlauf | Start nur durch berechtigte Menschen; Agenten bereiten Testfälle vor und werten Berichte aus |
| Staging (IT) | Integration und Abnahme von IT-Anwendungen | Fester Testjob; dasselbe signierte Artefakt wie später in Produktion |

[HINWEIS: Arbeitsschutz und Laborsicherheit gehen allen Regeln dieses Konzepts vor. Ein KI-Agent darf keine Aktion auslösen, bei der sich Teile bewegen, Spannung anliegt oder Energie freigesetzt wird, ohne dass eine berechtigte Person vor Ort die Freigabe gibt.]

## Unabhängigkeit der Tests

- Testspezifikationen auf der rechten Seite entstehen aus der Vorgabe auf der linken Seite, nicht aus dem Code.
- Testrollen (7 und 12) haben keinen Zugriff auf Implementierung, auch nicht über Suchindex, CI-Protokolle oder gemeinsame Speicher.
- Ergebnisse kommen aus den Testsystemen selbst; ein Agent kann einen Testerfolg nicht behaupten, nur einen Bericht verlinken.
- Bei K3 gilt zusätzlich die von der Norm geforderte Unabhängigkeit menschlicher Prüfer; KI-Agenten zählen dabei nicht als unabhängige Prüfer.

## CI und Qualitätsschranken

| Schranke | Wirkung |
| --- | --- |
| Build und Unit-Tests | Kein Merge bei Fehlern |
| Statische Analyse, Codierrichtlinien | Kein Merge bei Verstößen über dem Schwellwert |
| Abhängigkeits-, Lizenz- und Schwachstellenscan | Kein Merge bei verbotenen Lizenzen oder offenen kritischen Befunden ohne Ausnahme |
| Geheimnis-Scan | Kein Merge bei gefundenen Geheimnissen |
| Review am exakten Commit | Kein Merge ohne gültiges Review des aktuellen Stands |
| Nachverfolgbarkeit | Kein Merge ohne Bezug auf Aufgabe und Anforderung |

## Rücklauf bei Befunden

Ein Befund geht an die erstellende Rolle zurück. Nach zwei erfolglosen Korrekturrunden erhält der Tech Lead den Befund mit allen Versuchen. Ein Befund auf einer höheren Ebene (etwa im Systemtest) wird auf die Ebene zurückverfolgt, auf der der Fehler entstanden ist; die dortige Vorgabe wird geprüft und gegebenenfalls geändert, mit den Folgen aus Teil 02.

## Entscheidungspunkte

- **EP5 Systemelemente realisiert und integriert:** Code geprüft, Modul- und Integrationstests bestanden, Nachverfolgung vollständig.
- **EP6 System verifiziert:** Software- und Systemverifikation bestanden, offene Befunde bewertet, Nachweise vollständig (Teil 09).

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE E-04] Entwicklungsleitungen legen Codierrichtlinien je Sprache und Profil, Abdeckungsziele je Kritikalität, Schwellwerte der CI-Schranken, verfügbare Testumgebungen mit Verantwortlichen und die Regeln für Prüfstände und Hardware-in-the-Loop-Plätze fest.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Codier- und Testvorgaben / Entwicklungsleitungen und Testmanagement |
| Zu ergänzen | Richtlinien, Abdeckungsziele, Schwellwerte, Testumgebungen, Laborregeln |
| Spätester Entscheid | Vor EP5 des ersten Pilotprojekts |
| Erwarteter Abschlussbeleg | Freigegebene Codier- und Teststrategie |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |
