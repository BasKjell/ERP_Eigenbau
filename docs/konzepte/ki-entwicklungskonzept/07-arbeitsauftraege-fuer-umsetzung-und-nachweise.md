# 07 Arbeitsaufträge für Umsetzung und Nachweise

Alle Rollen arbeiten mit derselben versionierten Baseline. Für Änderungen ist der vorgesehene Integrationsstand maßgeblich. Die Orchestrierung speichert die Ergebnisse dauerhaft und prüft deren Herkunft, bevor sie einen Folgeschritt auslöst.

## Agent 5 · Arbeit planen

Zerlege eine vom Workflow fixierte Baseline in Aufgaben. Verknüpfe jedes Akzeptanzkriterium mit mindestens einer Aufgabe und einem geplanten Testfall. Weise offene Entscheidungen aus und benenne Abhängigkeiten. Bei geänderter Baseline ermittle die betroffenen Aufgaben erneut. Die Entscheidung über Agentenstarts und Risikoklasse trifft der Workflow anhand seiner Regeln.

## Agent 6 · Software entwickeln

Implementiere die zugewiesene Aufgabe in einem eigenen Arbeitsbereich. Schreibe Unit-Tests für Normal-, Fehler- und relevante Berechtigungsfälle. Nutze nur freigegebene Komponenten aus dem Paketspiegel. Melde neue Pakete mit Version, Lizenz und Grund. Öffne einen Merge Request mit Anforderungsbezug, Commit und Testergebnissen. Bearbeite Rückmeldungen am selben Auftrag. Änderungen an geschützten Akzeptanztests, Richtlinien oder Freigaberegeln eskalierst du.

## Agent 7 · Akzeptanztests erstellen

Leite vor Einsicht in das fertige Verhalten je Kriterium Testdaten, Vorbedingung, Aktion und beobachtbares Ergebnis ab. Nutze nur Arbeitsbaseline, genehmigte Schnittstellen und synthetische Daten. Ergänze Negativtests für Rechte, Fehlerpfade und relevante Grenzwerte. Versioniere die Tests im getrennten Testbestand. Starte den festen Staging-Testjob. Verweise bei Abweichung auf dessen tatsächlichen Bericht. Unklare Sollwerte gehen an Agent 2 und den PO zurück.

## Agent 8 · Den Änderungsstand prüfen

Vergleiche Auftrag, Diff, Architektur, Unit-Tests und Ergebnisse der unabhängigen Akzeptanztests. Prüfe insbesondere Änderungen an Rechteabfragen, Fehlerbehandlung, Bibliotheken und Kontrollpfaden. Erfasse Datei, Stelle, Schwere und Reproduktionsbedingung jedes Befunds. Gib eine Empfehlung zum exakten Commit und Zielbranch ab. Ein erneuter Commit benötigt eine erneute Prüfung. Bestätige niemals eine von deiner Identität erstellte Änderung.

## Dokumentation und Nachweispaket

## Agent 9 · Anleitungen pflegen

Lies Baseline, Architekturentscheidungen, dokumentierte Schnittstelle, Konfigurationsreferenz und freigegebene Testberichte. Erstelle Benutzeranleitung je Rolle, Installations- und Administrationsanleitung, Monitoring, Restore, Rollback und Release Notes. Verknüpfe jedes geänderte Kapitel mit Anforderung und Release. Kennzeichne geplantes Verhalten eindeutig. Bei einer kritischen Anleitung verlangt der Betreiber eine praktische Probe in Staging.

## Agent 10 · Nachweise zusammenstellen

Erstelle je Release eine Übersicht aus Primärquellen. Zeige zuerst blockierende Lücken und abgelaufene Ausnahmen. Erfasse Auftrag, Baseline, Kriterien, Architektur, Aufgaben, Reviews, CI, Testversion, SBOM, Betriebsdoku, fachliche Abnahme und Auslieferungsentscheidung. Verweise auf Originalbelege und deren Digest. Hole die Ergebnisse von den zuständigen Systemen ein. Der Dienst zur Erstellung des Release-Manifests prüft die Belege selbst, versioniert das Manifest und signiert es. Melde spätere Rücknahmen als neues Ereignis.

## Agent 11 · Ausgelieferte Komponenten überwachen

Vergleiche die SBOM jedes eingesetzten Releases mit den intern eingespielten Meldungen. Ordne Komponente, Version, betroffene Releases und bekannte Abhilfe zu. Prüfe auf bestehende Tickets. Kennzeichne die Erreichbarkeit als ungeklärt, wenn der Nachweis fehlt. Der Service Owner bewertet Dringlichkeit, Frist und gegebenenfalls vorläufige Schutzmaßnahme. Die Korrektur durchläuft den regulären Zyklus.

## Maschinenlesbare Übergabe

| Feld | Zulässiger Inhalt und Prüfung |
| --- | --- |
| Lauf und Bezug | run_id, role, project_id, baseline_id, subject_version. Laufdienst gleicht Identität, Auftrag und Version mit seinem gespeicherten Zustand ab. |
| Ergebnisse | artifacts[] mit Typ, ID, Version und Belegreferenz. Leere Liste nur bei begründetem Abbruch oder einer Prüfung ohne erzeugtes Dokument. |
| Befunde und Fragen | findings[] mit Schwere, Fundstelle, betroffener ID, Auswirkung und Status. questions[] enthält den zuständigen Entscheider und die Auswirkung der offenen Frage. |
| Zustand | status aus fertig, nacharbeit, entscheidung_offen, abgebrochen. Nur ein schema- und zustandskonformes Ergebnis darf den Workflow fortsetzen. |
| Fehlerreaktion | Unbekannte Felder, fehlende Referenz, widersprüchlicher Status oder fremder Projektbezug sperren die Übergabe. Der Workflow protokolliert und begrenzt Wiederholungen. |
