# 11 Qualitätssicherung, Überwachung und Störungen

Arbeitsreferenz KI-U-11 · Stand 20.11.2026 · Arbeitsentwurf zur internen Abstimmung

## Messbare Abnahme je Einsatzfall

Der fachliche Eigentümer benennt typische, schwierige und unzulässige Fälle. QA hält einen vom Entwicklungssatz getrennten Prüfsatz zurück, versioniert die Sollantworten und lässt strittige Referenzen fachlich klären. Die regelbasierten Antworten der Demo-Betriebsart der Referenzumgebung eignen sich als reproduzierbare Vergleichsbasis. Getestet werden insbesondere Abteilungen, unterschiedliche Rechtestufen, Sprache, Dokumentqualität, seltene Fehler und zulässige Enthaltungen. Das Protokoll nennt Nenner, Auswahlverfahren, Version der gesamten Verarbeitungskette sowie die Entscheidung je Abweichung. Durchschnittswerte dürfen schwerwiegende Einzelfehler einer Berechtigungsgruppe nicht überdecken.

| Pilot | Beispiel für einen Mindesttest vor Freigabe | Auswertung |
| --- | --- | --- |
| DMS-Suche | 30 beantwortbare und 10 unbeantwortbare Fragen sowie 20 Rechte- und Entzugsfälle | Beleg und Revision fachlich richtig bei mindestens 27/30, kontrollierte Enthaltung bei mindestens 9/10, keine Offenlegung in 20/20 Rechtefällen |
| ERP-Entwürfe | 20 gültige Datensätze, 10 fehlerhafte oder unberechtigte Fälle und 10 Wiederholungs-/Timeoutfälle | Alle Pflichtfelder in 20/20 korrekt, null unerlaubte Schreibaktionen, genau ein Entwurf je bestätigtem eindeutigem Auftrag trotz Wiederholung |
| KI-Entwicklung | Eine vollständige Funktionsänderung und je ein Fall mit geändertem Kandidaten, fehlendem Test und unberechtigter Selbstfreigabe | Nachweiskette für positiven Fall geschlossen, veraltete oder fehlende Freigaben blockiert |

Zahlen sind Startvorschläge für begrenzte Pilotprüfungen. Vor Beginn werden Stichprobe, Akzeptanzgrenzen und Sperrkriterien genehmigt. Erfolgreiche Stichproben erlauben keine Aussage über eine absolute Fehlerfreiheit. Fehler mit unberechtigter Offenlegung, unbestätigter Fachwirkung oder fehlender Pflichtfreigabe führen im Konzept zum Stopp des betroffenen Pfads, auch wenn ein Mittelwert erreicht wurde.

## Überwachung, Datenschutz und Eskalation

Betrieb beobachtet Latenz, Rückstau, Fehlerklasse, Auslastung, abgewiesene Schreibaktionen und ungeklärte Aufträge. Der Fachbereich erhebt die Kennzahlen aus dem Zielbild 2028: Durchlaufzeit, Anteil fehlerfrei beim ersten Mal, Korrekturen, Eskalationen, vermiedene Suchzeit, Akzeptanz und Fehlerfolgekosten, dazu den Anteil belastbarer Quellen. Technische Messwerte laufen über Prometheus und Grafana, fachliche Kennzahlen in FLOWMANAGE. Ein neuer Rollout wird zunächst nur einer benannten Gruppe freigegeben. Vergleich mit Ausgangswert und vorheriger Version erfolgt je Prozess und Rolle. Für Sicherheitskritisches gilt eine Ereignisregel unabhängig von der Stichprobenquote.

Standardlogs führen Ereigniszeit, pseudonyme Akteursreferenz soweit erforderlich, Lauf-ID, Werkzeug, Richtlinienversion, Entscheidung und Fehlerklasse. Vollprompts, Quelleninhalte und Zugangsdaten gehören nicht in Standardlogs. Diagnosemitschnitte brauchen Zweck, Berechtigung, Begrenzung, Redigierung und Löschtermin. Technische Messwerte werden zur Prozessverbesserung aggregiert. Eine personenbezogene Leistungsbewertung ist aus diesem Betriebszweck ausgeschlossen.

## Beispiel eines Vorfalls und Wiederfreigabe

Meldet ein Nutzer ein fremdes DMS-Zitat, sperrt der Service Desk den betroffenen Ausgabepfad über den Bereitschaftsdienst. Betrieb sichert erforderliche Belege zugriffsbeschränkt und prüft Index, Quellen-ACL, Cache und Antwortversion. ISB und Datenschutz beurteilen Empfänger, Reichweite und Meldepflichten nach den einschlägigen Fristen. Bereits übernommene Inhalte werden mit den Empfängern korrigiert. Der Fachbereich informiert Betroffene über den vorgesehenen Weg. Wiederanlauf erfordert nachgewiesene Korrektur, gezielte Wiederholung der Rechteprüfungen, unabhängige Prüfung und dokumentierte Freigabe. Der Fall erhält Ursachenanalyse, Korrekturmaßnahme, Verantwortlichen und Wirksamkeitstermin.

Der gleiche Ablauf unterstützt Qualitätsfehler ohne Datenoffenlegung. Bei falscher Mengeneinheit im Einkauf wird zunächst das Schreibwerkzeug gestoppt, der ERP-Bestand anhand bestätigter Referenzen abgeglichen und die manuelle Bearbeitung aufgenommen. Die Fachseite entscheidet über Korrektur bereits vorhandener Entwürfe. Beim Fehler eines Modells bleibt die letzte funktionierende Kombination aus Modell, Prompt und Richtlinie verfügbar.

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE U-11] QA, Fachbereiche und Betrieb genehmigen Prüfdaten, Grenzwerte, Meldekanal, Rufbereitschaft, Alarmfristen und Zuständigkeit für externe Meldungen. Vor Produktivfreigabe einen Vorfall üben und gemessene Wiederanlaufzeit protokollieren.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Prüf- und Meldeplan / QA und Betrieb |
| Zu ergänzen | Sollwerte je Gruppe, Alarmempfänger, Meldeweg und Vertretung |
| Spätester Entscheid | Vor Produktiventscheidung |
| Erwarteter Abschlussbeleg | Ausgefülltes Testprotokoll und Vorfallübung |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |
