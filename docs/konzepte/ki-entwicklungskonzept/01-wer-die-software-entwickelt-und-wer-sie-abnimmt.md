# 01 Wer die Software entwickelt und wer sie abnimmt

Der Fachbereich beschreibt zu Beginn, welche Arbeit die Anwendung erleichtern soll. Am Ende prüft er denselben Auftrag an einem konkreten Release in Staging. Dazwischen können Agenten Anforderungen formulieren, Architektur und Code erstellen, unabhängig prüfen, testen und dokumentieren. Die IT verantwortet die Regeln, innerhalb derer dieser Ablauf selbstständig arbeiten darf.

## Wann zwei Kontakte mit dem Fachbereich reichen

Für einen zuvor genehmigten Standardfall reichen ein bestätigter Auftrag und die fachliche Endabnahme. Der Auftrag nennt Nutzergruppe, gewünschtes Verhalten, Grenzen und ein Beispiel für Erfolg. Die Ableitung der einzelnen Anforderungen darf nur so weit gehen, wie Auftrag, genehmigte Vorlagen und vorhandene Entscheidungen sie tragen. Fehlt eine fachliche Entscheidung, legt die KI eine gebündelte Rückfrage mit Optionen vor.

| Fall | Beispiel aus dem DMS | Entscheidung |
| --- | --- | --- |
| Standardänderung | Sortierung einer bestehenden Ansicht mit unveränderter Datenquelle, Zugriffslogik und genehmigtem UI-Muster. | Fachbereich bei Auftrag und Abnahme. Die IT kann den Releaseweg für diese Änderungsklasse vorab genehmigen. |
| Neue Funktion | Zusätzlicher Dokumenttyp mit neuem Workflow oder eigener Frist. | Fachverantwortlicher klärt die Regel. Tech Lead bewertet Architektur und Betrieb. Geltende Change-Vorgaben bestimmen den Releaseweg. |
| Hoher Schutzbedarf oder neuer Dienst | Erstes DMS, geänderte ACL-Vererbung, Massenexport, Migration oder endgültige Löschung. | Benannte Menschen prüfen vor Umsetzung das Konzept, vor Integration die kritische Änderung und vor Produktivsetzung den Release. |

## Verantwortung im Unternehmen

Der Product Owner verantwortet Zweck und Abnahme. Der Tech Lead verantwortet Architektur und Umsetzung. Der Service Owner stellt Betrieb, Wiederanlauf und die benannte Releasevertretung sicher. Der Risikoeigner entscheidet über Restrisiken. Der ISB berät und überwacht im Auftrag des ISMS. Bei betroffenen Personen berät der Datenschutzbeauftragte den Verantwortlichen. Die konkreten Rollenkonflikte und Vertretungen legt das Unternehmen vor dem Pilot fest.

## Elf Aufgaben im Entwicklungszyklus

Die Nummern gelten in allen zehn Teilen. Mehrere Rollen können denselben lokalen Modellserver nutzen. Jede Rolle erhält eine eigene technische Identität. Für ein Artefakt sind Ersteller und Prüfer getrennt. Getrennte Werkzeuge, Eingaben und Schreibrechte begrenzen gemeinsame Fehler. Ein zweites Modell erhöht die Vielfalt der Prüfung, ersetzt aber keine wirksamen Tests.

| Rolle | Auftrag und Ergebnis | Prüfung oder Grenze |
| --- | --- | --- |
| 1 Anforderungen | Leitet Entwürfe und Akzeptanzkriterien aus Auftrag und Katalog ab. | 2 prüft Herkunft, Testbarkeit und Lücken. |
| 2 Anforderungsprüfung | Kommentiert einzelne Kriterien und prüft die fachliche Dokumentation. | Kann Entwürfe weder ändern noch freigeben. |
| 3 Architektur | Liefert Datenflüsse, Architekturentscheidungen, Bedrohungsmodell und Betriebskonzept. | 4 prüft, Tech Lead entscheidet bei neuer Architektur. |
| 4 Sicherheitsprüfung | Bewertet Entwurf, Diff und Scannerbefunde mit Beleg. | Hohe strittige Befunde gehen an die IT-Sicherheit. |
| 5 Planung | Verknüpft Arbeitspakete und Abhängigkeiten mit der Baseline. | Der Orchestrator erzwingt Zustand und Budgets. |
| 6 Entwicklung | Liefert Code und Unit-Tests auf eigenem Branch. | 8 prüft den exakten Änderungsstand. |
| 7 Akzeptanztests | Entwirft aus Kriterien unabhängige Testfälle und prüft Staging. | Kein Zugriff auf die Implementierung, auch nicht über die Suche. |
| 8 Codeprüfung | Prüft Korrektheit, Risiken und Testabdeckung. Meldet Befunde. | Kein Schreibrecht am geprüften Artefakt, kein Merge. |
| 9 Dokumentation | Erstellt rollenbezogene Hilfe, Betriebshandbuch und Release Notes. | 2 prüft fachliche Aussagen, Betrieb prüft kritische Anleitungen. |
| 10 Nachweise | Ordnet Primärbelege zu und macht Lücken sichtbar. | CI prüft IDs und Hashes. Der Agent signiert keine Freigabe. |
| 11 Schwachstellen | Ordnet Meldungen den SBOMs ausgelieferter Versionen zu. | Feed-Abgleich und Fristen sind automatisiert. Der Service Owner verantwortet die Behandlung. |

## Lesereihenfolge

Teil 2 beschreibt den Ablauf am DMS. Teile 3 und 4 regeln Architektur und Datenrechte. Teil 5 dient ISMS und Qualitätsmanagement zur Einordnung. Teile 6 und 7 enthalten die Arbeitsaufträge, Teile 8 und 9 die technischen Verträge. Teil 10 ist der Abnahmeplan für die Plattform.
