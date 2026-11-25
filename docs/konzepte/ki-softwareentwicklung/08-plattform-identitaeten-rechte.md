# 08 Plattform, Identitäten und Rechte

Arbeitsreferenz SE-08 · Stand 24.11.2026 · Arbeitsentwurf zur internen Abstimmung

Alle Domänen nutzen dieselbe lokale KI-Plattform. Neu gegenüber dem bisherigen KI-Entwicklungskonzept sind das Projektmanagement-Werkzeug, Testumgebungen mit Hardware und die Trennung zwischen Projekten verschiedener Kunden. Dieser Teil enthält auch die technischen Regeln aus dem bisherigen KI-Entwicklungskonzept, die weiter gelten: Identitäten, Rechtefluss bis zur Wissenssuche, Fachmodell und MCP-Adapter des Anforderungsmanagements sowie Wiederanlauf der Plattform. Die Regeln für das KI-Gateway stehen im KI-Gateway-Konzept SEC-AI-001, Anmeldung, Tokens und Rechteentzug im IAM-Sicherheitskonzept SEC-IAM-001.

![Zugang über AD und Keycloak, KI-Plattform mit Orchestrator, Gateway und lokalen Modellen, Werkzeuge über MCP-Adapter für Projektmanagement, Anforderungen, Git, CI, Testumgebungen und Wissenssuche, getrennte Auslieferung an IT-Betrieb und Produktion.](bilder/03_Plattform.png)

*Abbildung 03: Plattform und Vertrauensgrenzen für alle Domänen*

## Zonen

| Zone | Bausteine | Grenze |
| --- | --- | --- |
| Zugang | AD als Quelle für Personen und Gruppen, Keycloak mit MFA, Portal bzw. Oberflächen der Werkzeuge | Menschen, Dienste und delegierte Aufträge sind unterscheidbar |
| KI-Plattform | Orchestrator (Läufe, Zustände, Budgets), Gateway (Modell- und Werkzeugrouten), lokale Modellserver | Keine externen Modelle, kein Cloud-Rückfall |
| Werkzeuge | MCP-Adapter zu Projektmanagement, Anforderungsmanagement, Git, CI, Paketspiegel, Testdienst, Wissenssuche, Ticket- und SBOM-System | Jeder Adapter nutzt eigene, projektgebundene Zielkonten |
| Testumgebungen | Sandbox-Runner, Simulation, Hardware-in-the-Loop-Plätze, Prüfstände, Staging | Agenten starten nur festgelegte Testjobs über den Testdienst |
| Auslieferung | Manifest-Dienst, Deploymentdienst (IT), Freigabe und Übergabe an Produktion (Produkt) | Nur deterministische Dienste außerhalb der Agentenlaufzeit; kein Agent erreicht Produktion |

## Drei Identitäten je Auftrag

1. **Person:** meldet sich über AD und Keycloak mit MFA an und startet bzw. verantwortet einen Lauf.
2. **Agentenrolle:** eigene Dienstidentität je Rolle; das Gateway prüft Rolle, Lauf, Projekt und erlaubte Werkzeuge.
3. **Zielkonto:** der Adapter nutzt für das Zielsystem ein eigenes, auf Projekt und Rolle begrenztes Konto aus dem Tresor.

Die auslösende Person kann nicht über ein Feld im Werkzeugaufruf ersetzt werden. Unbeaufsichtigte Läufe, etwa der nächtliche Schwachstellenabgleich, haben eine eigene Identität mit festem Projektkontext.

Keycloak bindet das AD lesend über LDAPS an. Gruppen für Product Owner, Tech Lead, Release, ISB und Key User werden getrennt von den Datengruppen des DMS abgebildet. Personen nutzen MFA. Dienste verwenden getrennte Schlüssel und kurze Tokenlaufzeiten. Schlüssel, Zertifikate, Realm-Konfiguration und Ausfallverhalten versioniert bzw. verwahrt der Plattformbetrieb im Tresor. Unbeaufsichtigte Läufe wie der nächtliche SBOM-Abgleich oder automatische Code-Reviews erhalten einen festen, genehmigten Projektkontext mit eigener Identität; personenbezogene DMS-Bestände bleiben für sie gesperrt. Die Lauf-ID allein verschafft keine Rechte.

## Rechtefluss bis zur Wissenssuche

| Station | Prüfung |
| --- | --- |
| Anmeldung | Keycloak bestätigt Person, Sitzung und Projektrolle; der Orchestrator speichert den Lauf serverseitig. |
| Werkzeugaufruf | Gateway prüft Agentenidentität, Zielressource und Bindung an den aktiven Lauf; frei gesetzte Identitätsangaben werden verworfen. |
| Adapter | Prüft Projekt, Aktion und Objekt; bei Aktionen im Namen einer Person auch deren Befugnis. |
| Suche im Index | Kandidaten werden serverseitig nach Projekt, Sammlung und Berechtigung eingeschränkt; vor jeder Ausgabe wird die aktuelle Berechtigung im Quellsystem geprüft. |
| Ausgabe und Ablage | Auch Titel, Trefferzahlen, Zitate und Caches unterliegen der Prüfung; Ergebnisse werden nur dort abgelegt, wo alle verwendeten Quellen sichtbar sind. |

## Indexierung, Rechteentzug und Caches

Beim Einlesen übernimmt der Indexdienst Dokument-ID, Version, Projekt, Klassifikation, ACL-Referenz und Berechtigungsstand in jedes Textstück. Geschützte Dokumente bleiben bis zur erfolgreichen Auflösung im Quellsystem gesperrt. Ein Ereignis über Löschung oder Rechteänderung sperrt den Indexeintrag zuerst; ein Abgleich erkennt verpasste Ereignisse. Der Berechtigungsentscheid vor der Ausgabe gilt auch während eines Neuaufbaus.

Ein Cache-Treffer durchläuft dieselbe Berechtigungsprüfung wie eine neue Suche. Cache-Schlüssel umfassen Projekt, Person, Rollenprofil und Berechtigungsstand. Der Betrieb löscht betroffene Textstücke, Embeddings, Vorschauen und Cache-Einträge nach dem Löschkonzept. Bei Wiederherstellung aus einer Sicherung werden aktuelle Sperren vor der erneuten Indexfreigabe angewendet. Für bereits veröffentlichte Ableitungen werden Quellenbezug, Empfänger, Sperrung und Berichtigung nachvollzogen.

![Personenauftrag und Agentenrolle begrenzen die Suche. Das Quellsystem entscheidet vor der Ausgabe über das aktuelle Dokumentrecht. Eine Übernahme ins Zielsystem erfordert einen zulässigen Empfängerkreis.](bilder/04_Dokumentrechte.png)

*Abbildung 04: Dokumentrechte bei der KI-Suche*

## Welche Rolle welche Inhalte sieht

[HINWEIS: Rollennummern nach Teil 06. Die Integrationstests (12) gelten wie die Akzeptanztests (7) als unabhängige Prüfung ohne Zugriff auf die Implementierung.]

| Inhalte | Zugelassene Rollen im Projekt | Zusätzliche Bedingung |
| --- | --- | --- |
| Projektplan und Arbeitspakete | 0, 1 bis 10 lesend, soweit für ihre Aufgabe erforderlich | Nur 0 schreibt Entwürfe; genehmigt wird an EP1 |
| Anforderungen und Baselines | 1 bis 10 und 12, soweit für ihre Aufgabe erforderlich | Für 7 und 12 nur freigegebene Kriterien und Schnittstellen; 10 erhält bevorzugt Metadaten |
| Architektur und Regeln | 1 bis 9 und 12, je nach Auftrag | Freigegebene oder ausdrücklich zur Prüfung vorgelegte Version |
| Implementierung | 4, 6 und 8; für 11 nur projektspezifische Komponentenbelege | 7 und 12 erhalten weder Quellcode noch Codeauszüge über Suchindex, CI-Protokoll oder gemeinsamen Speicher |
| Akzeptanz- und Integrationstests | 7, 8 und 12; für 10 nur Test-ID und Ergebnis | 6 erhält Fehlerbeschreibung und öffentliche Schnittstelle; der Testbestand bleibt unabhängig |
| Benutzer- und Betriebsdokumentation | 2, 6, 9 sowie 10 für Nachweisreferenzen | Leserechte am Entwurf und an eingebundenen Quellen prüfen |
| Fachwissen aus freigegebenen Quellen | 1 und 3 bei gültigem Personenauftrag | Aktuelle Quellberechtigung und Prüfung des Zielpublikums vor jeder Übernahme |

## Daten für die Entwicklung

Der Pilot nutzt ausschließlich synthetische oder eigens freigegebene Entwicklungsunterlagen. Ein späterer Produktivdienst für die KI-Suche erhält eigene Identitäten und einen eigenen Index. Entwicklungsagenten haben keinen Netzwerkpfad in produktive Fachsysteme wie das DMS.

## Fachmodell im Anforderungsmanagement

Das Anforderungsmanagement führt Anforderungen, Versionen, Beziehungen und fachliche Entscheidungen. Ein lokaler MCP-Adapter übersetzt begrenzte Fachoperationen in die Produkt-API. Für Jama, FLOWWORK oder ein anderes Werkzeug werden Statusmodell, Rechte und Versionsverhalten zunächst in einem Testprojekt nachgewiesen.

| Objekt | Pflichtinhalt | Zulässige Änderung |
| --- | --- | --- |
| Fachauftrag | Zweck, Zielgruppe, Quelle, Umfang, ausgeschlossene Funktionen, Eigentümer, Datenklasse, Erfolgsbeispiel, Projektklasse und Kritikalität | Der Product Owner bestätigt den Auftrag. Eine neue Zweckbestimmung erfordert eine neue Entscheidung. |
| Anforderung und Kriterium | Stabile ID und Version, Typ, Quelle, Muss/Soll, Begründung, Verantwortlicher, beobachtbares Ergebnis | Agent 1 schreibt im Entwurf, Agent 2 kommentiert. Nach Fixierung entsteht eine neue Version. |
| Prüfung und Test | Gegenstand und Version, Befund, Prüfer, Test-ID, Kriterium, Soll; bei Ausführung zusätzlich Ist, Umgebung, Zeit und Bericht | Testdefinition durch 7 bzw. 12, Primärergebnis aus der CI. Keine nachträgliche Änderung eines historischen Laufs. |
| Baseline und Abnahme | Snapshot der referenzierten Objektversionen; Abnahme mit Person, Entscheidung, Kandidat, Digest und Begründung | Der Ablauf friert bei erfülltem EP2 ein. Menschliche Freigaben entstehen nur in einer authentifizierten Oberfläche. |

## Zwei Arten von Baseline

Der technische Zustand „Arbeitsbaseline fixiert“ bezeichnet eine unveränderliche, zur Bearbeitung zugelassene Version. „Fachlich freigegeben“ setzt die ausdrückliche Entscheidung des Product Owners voraus. Erlaubt das Werkzeug diese Trennung nicht, bleibt die ausdrückliche Baseline-Freigabe im Anforderungsmanagement bis zu einem belastbaren Ersatz erforderlich.

## Vertrag des MCP-Adapters

| Operation | Erlaubter Aufrufer | Bedingungen am Adapter und Zielsystem |
| --- | --- | --- |
| rm.search / rm.get | Projektrollen mit sachlichem Bezug | Objekttyp, Projekt, Sichtbarkeit und zulässige Felder serverseitig begrenzen. Suchtreffer und Zähler folgen denselben Rechten. |
| rm.create_draft | 1 Anforderungen | Projekt, Fachauftrag, erlaubte Felder, Schema und Idempotenzschlüssel prüfen. Beispiel: A-17 / REQ-17 / Entwurf 1. |
| rm.update_draft | 1 Anforderungen | Nur eigener zuständiger Entwurf. expected_version ist Pflicht. Bei Konflikt aktuellen Stand zurückmelden und neu vergleichen. |
| rm.comment / rm.ask_owner | 2 prüft, 1 fragt nach | Kommentar bindet ID und Version. Fragen gehen nur an berechtigte Fachverantwortliche. Keine allgemeinen Benachrichtigungsrechte. |
| rm.link_trace | 5 für Aufgaben, 7 und 12 für Testfälle | Beziehungstyp und beide Endpunkte im selben zulässigen Projekt prüfen. Historische Baselines bleiben unverändert, spätere Links sind eigene versionierte Objekte. |
| rm.get_baseline | Rollen 0 bis 10 und 12 nach Zweck | Snapshot, Versionsliste, Status, Freigabetyp und Digest liefern. Filtern nach Projekt und tatsächlichem Auftrag. |

Weitere Ziele: Git vergibt getrennte Zielkonten für Entwicklungs-, Test- und Dokumentationsbranches. Die CI bietet nur Berichtslesezugriff und für die Testrollen einen festen Staging-Test. Der Paketspiegel erlaubt nur freigegebene Versionen. Die Sandbox führt Builds unter Ressourcenlimits aus. Ticket- und SBOM-Adapter begrenzen den Zugriff auf Projekt und Release. Die Wissenssuche prüft die Rechtekette oben. Die vollständige Werkzeugzuordnung je Rolle steht im Agentenregister (Teil 06 und Teil 10).

## Fehler und Teilabbruch

Bei gleichzeitigen Änderungen gewinnt die bestätigte Objektversion. Ein unterbrochener Schreibaufruf wird mit demselben Schlüssel abgeglichen; gleicher Schlüssel mit abweichender Nutzlast erzeugt einen Konflikt. Fehlt im Zielwerkzeug eine idempotente Anlage, speichert der Adapter Schlüssel und Zuordnung dauerhaft und gleicht den eindeutigen Fremdschlüssel vor jedem erneuten Versuch ab. Ein unklarer Ausgang hält den Schritt zur Klärung an.

Vor der Freigabe eines Werkzeugs sind Version und Lizenz, API-Limits, Rollenmodell, Feldrechte, Historienexport, unveränderliche Snapshots und Wiederherstellung zu belegen. Fehlende Produktfunktionen werden als Lücke mit Eigentümer und technischem Ersatz dokumentiert. Eine Freigabemaske allein belegt keine wirksame Sperre auf API-Ebene.

## Neu: Werkzeuge für Planung und Engineering

| Werkzeug | Zugriff der Agenten | Grenze |
| --- | --- | --- |
| Projektmanagement (zum Beispiel FLOWTASK bzw. Redmine oder OpenProject) | 0 liest Projekte und schreibt Entwürfe für Arbeitspakete und Berichte; 5 legt Aufgaben an | Keine Änderung genehmigter Pläne, Budgets oder Zuordnungen von Personen |
| Anforderungsmanagement (Jama oder FLOWWORK) | 1 schreibt Entwürfe, 2 kommentiert, 5 und 7 und 12 verknüpfen | Freigabe und Baseline-Einfrieren nur durch Workflow bzw. Menschen |
| Testdienst für Simulation und Hardware-in-the-Loop | 7 und 12 starten festgelegte Testjobs und lesen Berichte | Keine freien Befehle an Hardware, keine Änderung der Sicherheitsabschaltung |
| Toolchain für Firmware | 6 baut in der Sandbox mit festgelegter Toolchain | Keine Programmierung von Hardware außerhalb des Testdienstes |
| Wissenssuche | Rollen nach Projekt und Zweck | Kundenunterlagen nur im eigenen Kundenprojekt |

## Trennung zwischen Projekten und Kunden

- Jedes Projekt ist ein eigener Raum in Anforderungsmanagement, Git, CI, Suchindex und Projektmanagement.
- Unterlagen und Code eines Kunden sind nur in dessen Projekten sichtbar; das gilt auch für Embeddings, Caches und Agentenläufe.
- Wiederverwendung zwischen Projekten nur für freigegebene interne Bausteine.
- Vertraglich besonders geschützte oder eingestufte Unterlagen werden erst nach ausdrücklicher Freigabe des Verfahrens verarbeitet, auch bei lokaler Verarbeitung.

## Betrieb der Plattform

Die Plattform selbst wird nach dem Vorlagensatz Systemdokumentation dokumentiert. Protokolle enthalten keine Vollprompts, Antworten oder Geheimnisse (SEC-AI-001). Die Abnahmetests der Plattform stehen in Teil 11.

| Ereignis | Festgelegtes Verhalten | Nachweis für den Betreiber |
| --- | --- | --- |
| Worker oder Warteschlange fällt aus | Leases laufen ab. Ein anderer Worker übernimmt denselben Schritt mit gleichem Auftragsschlüssel. Vor erneutem Schreiben fragt er den Objektstatus ab. | Ein Auftrag erzeugt nach Neustart genau einen Entwurf und genau einen Releaseauftrag. |
| Modell oder Berechtigungsdienst fehlt | Betroffene Läufe pausieren. Der Betrieb ausgelieferter Anwendungen läuft eigenständig weiter. | Offline-Probe und manueller Wartungsweg mit benannter Vertretung. |
| Kompromittierte Identität | Der Betrieb sperrt den Lauf im Gateway, stoppt Worker und entzieht Tickets oder Zertifikate. Ausstehende Jobs werden vor Ausführung erneut autorisiert. | Zeit bis zur letzten zulässigen Aktion, betroffene Objekte und Wiederanlaufentscheidung. |
| Verlust von Plattformdaten | Der Betrieb stellt Anforderungsmanagement, Git, Register, Zustandsdaten, Signaturprüfung und Nachweisindex in einer isolierten Umgebung wieder her. | Wiederherstellungsprotokoll und Prüfung, ob sich ein vergangener Release eindeutig rekonstruieren lässt. |

Der Plattformbetrieb verantwortet Patchstand, Rotation und Netzrichtlinien. Der Service Owner vereinbart Wiederanlaufzeit und tolerierbaren Datenverlust je Dienst. Die Pilotmessung umfasst parallele Läufe, GPU-Speicher je Modell, Antwortzeiten, Warteschlange und Abbruchverhalten. Kritische Prüfläufe erhalten ein festes Budget. Neue Modelle oder Quantisierungen durchlaufen dieselbe Bewertung wie Promptänderungen (Test 34 in Teil 11).

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE E-08] Plattformbetrieb, IAM und Engineering legen die angebundenen Werkzeuge je Domäne, die Projekt- und Kundentrennung, die Anbindung von Testdienst und Hardware-in-the-Loop-Plätzen sowie die Gruppen in AD und Keycloak fest.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Werkzeuganbindung und Trennung / Plattformbetrieb mit Engineering |
| Zu ergänzen | Werkzeuge je Domäne, Projekträume, Testdienst, Gruppenmodell |
| Spätester Entscheid | Vor dem technischen Pilot |
| Erwarteter Abschlussbeleg | Freigegebene Werkzeug- und Rechtematrix, bestandene Abnahmetests |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |
