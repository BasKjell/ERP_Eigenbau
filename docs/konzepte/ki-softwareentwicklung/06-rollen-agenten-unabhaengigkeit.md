# 06 Rollen, Agenten und Unabhängigkeit

Arbeitsreferenz SE-06 · Stand 24.11.2026 · Arbeitsentwurf zur internen Abstimmung

## Menschliche Rollen

| Rolle | Verantwortung | Entscheidungspunkte |
| --- | --- | --- |
| Auftraggeber bzw. Lenkungsausschuss | Ziel, Budget, Priorität; bei Projektklasse L Steuerung über Lenkungsausschuss | EP0, EP1, EP9 |
| Projektleitung (bei L mit Teilprojektleitungen) | Planung, Steuerung, Arbeitspakete, Risiken, Berichte | EP1, EPi, EP9 |
| Product Owner bzw. Fachbereich, bei Kundenprojekten Kunde | Zweck, Anforderungen der Nutzer, Abnahme | EP2, EP7 |
| Systemarchitektur | Systemanforderungen und Systemarchitektur, Schnittstellen über Teilsysteme | EP2, EP3 |
| Softwarearchitektur bzw. Tech Lead | Software-Architektur, Umsetzung, technische Qualität | EP3, EP4, EP5 |
| Testmanagement | Teststrategie, Testumgebungen, Bewertung der Testergebnisse | EP5, EP6 |
| Qualitätssicherung | Einhaltung des Prozesses, Stichproben, Prozessaudits | alle als Prüfer |
| Konfigurationsmanagement | Baselines, Versionen, Änderungssteuerung | EP2 bis EP8 |
| Security-Verantwortung (IT: ISB-Beratung; Produkt: Produkt-Sicherheitsteam) | Bedrohungsanalysen, Sicherheitstests, Schwachstellen | EP3, EP6, EP8 |
| Safety-Verantwortung (nur K3) | Safety-Plan, Safety-Analysen, Bestätigungsmaßnahmen nach Norm | EP1 bis EP8 |
| Release-Verantwortung | Freigabe zur Auslieferung bzw. Serie anhand Nachweispaket | EP8 |
| Service Owner (IT) bzw. Produktverantwortung (Produkt) | Betrieb bzw. Feldbetreuung, Wiederanlauf, Unterstützungszeitraum | EP7, EP8, EP9 |
| ISB, Datenschutz, Betriebsrat | Beratung, Überwachung, Mitbestimmung nach Auftrag | nach Bedarf |

Konfliktregeln: Wer ein Ergebnis erstellt, gibt es nicht frei. Projektleitung und Qualitätssicherung sind bei Projektklasse L verschiedene Personen. Bei K3 gelten die Unabhängigkeitsstufen der jeweiligen Norm.

## Agenten

Die Nummern 1 bis 11 entsprechen dem bisherigen KI-Entwicklungskonzept; 0 und 12 sind neu. Jede Rolle hat eine eigene technische Identität, eigene Werkzeuge und eigene Schreibrechte (Teil 08). Arbeitsaufträge stehen in Teil 10.

| Nr. | Rolle | Ebene im V-Modell | Ergebnis | Geprüft durch |
| --- | --- | --- | --- | --- |
| 0 | Projektplanung (neu) | Projektplanung, Steuerung | Entwürfe für Projektauftrag, Projektstrukturplan, Arbeitspakete, Schätzspannen, Risiken, Statusberichte | Projektleitung, Lenkungsausschuss |
| 1 | Anforderungen | Nutzer-, System- und Software-Anforderungen | Anforderungsentwürfe mit Prüfkriterien | 2, dann Mensch an EP2 |
| 2 | Anforderungsprüfung | alle Anforderungsebenen, fachliche Dokumentation | Prüfkommentare | Mensch an EP2 |
| 3 | Architektur | System- und Software-Architektur, Feinentwurf | Architekturentwürfe, Entscheidungsvorlagen | 4, dann Mensch an EP3 bzw. EP4 |
| 4 | Sicherheitsanalyse | Architektur, Code, Befunde | Bedrohungsmodelle, Sicherheitsbefunde; bei K3 nur Hinweise | Sicherheits- bzw. Safety-Verantwortung |
| 5 | Aufgaben- und Iterationsplanung | Inkrement- und Aufgabenebene | Aufgaben je Arbeitspaket mit Verknüpfung zu Anforderungen und Tests | Projektleitung bzw. Tech Lead an EPi |
| 6 | Entwicklung | Implementierung | Code und Unit-Tests | 8, CI, bei K2/K3 Mensch |
| 7 | Verifikation und Abnahmetests | Software- und Systemverifikation, Abnahmeszenarien | Black-Box-Testfälle und Testberichte | Testmanagement; Abnahme durch Menschen |
| 8 | Codeprüfung | Modulverifikation | Review am exakten Commit | Tech Lead stichprobenartig; bei K2/K3 zusätzliches menschliches Review |
| 9 | Dokumentation | alle Ebenen | Benutzer-, Betriebs-, Service- und Release-Dokumentation | 2 fachlich, Betrieb bzw. Service praktisch |
| 10 | Nachweise | alle Entscheidungspunkte | Nachweisübersicht mit Lücken | Manifest-Dienst prüft; Mensch an EP6 und EP8 |
| 11 | Schwachstellen | Betrieb und Feld | Zuordnung von Meldungen zu ausgelieferten Ständen | Service Owner bzw. Produkt-Sicherheitsteam |
| 12 | Integrationstests (neu) | Software- und Systemintegration | Integrationstestfälle aus Architektur und Schnittstellen, Testberichte aus Testjobs | Testmanagement |

## Modellprofile

| Profil | Merkmal | Rollen |
| --- | --- | --- |
| Builder | Stärkstes verfügbares Modell für Code und Entwürfe | 1, 3, 6 |
| Prüfer | Andere Modellfamilie als Builder, stark im Schlussfolgern | 2, 4, 7, 8, 12 |
| Assistenz | Kleines, schnelles Modell | 0, 5, 9, 10, 11 |

Ein zweites Modell erhöht die Vielfalt der Prüfung, ersetzt aber keine wirksamen Tests und keine menschliche Prüfung, wo sie gefordert ist.

## Regeln zur Unabhängigkeit

1. Für ein Ergebnis sind Ersteller und Prüfer verschiedene Rollen mit verschiedenen Identitäten.
2. Testrollen (7, 12) sehen keine Implementierung.
3. Eine Rolle kann sich keine anderen Rechte geben und keinen Lauf mit privilegierterer Identität starten.
4. Unterschiedliche Agentennamen allein belegen keine Unabhängigkeit; wirksam sind getrennte Schreibrechte, Prüfung am konkreten Stand und Revisionshistorie.
5. KI-Agenten zählen nie als unabhängige Prüfer im Sinne von Normen der funktionalen Sicherheit oder von Kundenvorgaben, die Personen fordern.
6. Freigaben, Abnahmen und Risikoannahmen erklären nur Menschen.

## Wie viel Arbeit beim Menschen bleibt

| Vorhaben | Menschliche Kontakte |
| --- | --- |
| S, K1 im Kurzweg | Auftrag bestätigen, Abnahme am Stand; Rest vorab genehmigt |
| M, K1 bis K2 | Zusätzlich EP0/EP1 in vereinfachter Form, EP3 Architektur, kritische Reviews, EP6 und EP8 |
| L | Alle Entscheidungspunkte; laufende Steuerung durch Projektleitung; je Inkrement EPi |
| K3-Anteile | Zusätzlich alle sicherheitsrelevanten Ergebnisse nach Norm |

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE E-06] Bereichsleitungen besetzen die Rollen je Domänenprofil, benennen Vertretungen, legen Konfliktregeln fest und bestimmen, welche Rollen bei K3 welche Qualifikation brauchen.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Rollenmatrix / Bereichsleitungen mit Qualität |
| Zu ergänzen | Besetzung, Vertretung, Konfliktregeln, Qualifikationsanforderungen |
| Spätester Entscheid | Vor EP1 des ersten Pilotprojekts |
| Erwarteter Abschlussbeleg | Freigegebene Rollenmatrix |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |
