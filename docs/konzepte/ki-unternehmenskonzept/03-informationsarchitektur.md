# 03 Informationsarchitektur und verbindliche Ablage

Arbeitsreferenz KI-U-03 · Stand 20.11.2026 · Arbeitsentwurf zur internen Abstimmung

## Ein Verantwortlicher und eine führende Fassung je Objekt

Wer eine Entscheidung später prüfen muss, soll von der Use-Case-ID zu Original, Version, Freigabe und Beleg gelangen. Die folgende Zuordnung ist das vorgeschlagene Ablagemodell; sie übernimmt die Systemgrenzen der Referenzumgebung. Verknüpfungen verwenden stabile IDs, Versionen und bei ausgelieferten Artefakten einen Digest. Eine Kopie für die Suche oder ein Bericht aus der CI erhält ein festgelegtes Verfalls- und Wiederaufbauverfahren. Schutzklasse und zulässiger Empfängerkreis werden bei jeder Ableitung mitgeführt.

| Information | Führendes System und Pflege | Was andere Systeme erhalten |
| --- | --- | --- |
| Einsatzfall, Verbesserung, Störung | FLOWTASK (Redmine) als Einsatzregister und Arbeitsvorrat, gepflegt durch Fachbereich bzw. Service Desk [FIRMENANGABE U-03] | Use-Case-ID, Status und Link |
| Agentenregister | Versionierte Konfiguration im Git, angezeigt in FLOWMANAGE, gepflegt durch die Owner der Agenten | Agenten-ID, Stufe und Ablaufdatum |
| Anforderung, Akzeptanzkriterium, Testfall, Baseline, Risiko, Nachverfolgung | FLOWWORK (`REQ-*`, `BL-*`, `TC-*`, `RISK-*`), fachlicher Eigentümer und unabhängige Prüfung. Ist Jama oder ein anderes RM-System bereits eingeführt, bleibt es führend und FLOWWORK verweist nur [FIRMENANGABE U-03] | Anforderungs-ID und geprüfte Baseline im Merge Request |
| Code, Infrastrukturdefinition, Schnittstellen- und Promptschema, Testcode, Dokumentation | GitLab, Produktteam, Änderungen auf geprüftem Branch; Prozess-Dokumentation als Markdown mit dem Code (FLOWDOCS) | Commit-SHA und Release-Manifest |
| Build, Container, Pakete, SBOM und Modellgewichte | Interne Container- und Paket-Registry, für Modellgewichte ein zugelassenes Modellverzeichnis, Betrieb | Digest, Herkunft, Lizenzentscheidung und Prüfsumme |
| Betriebsgeheimnisse, Schlüssel und Tokens | Secret-Manager mit berechtigtem Abruf durch Dienste, Betrieb | Referenzen und Rotationsnachweis |
| Gelenkte Richtlinie, Arbeitsanweisung, Zeichnung, Prüfplan, Freigabeprotokoll | FLOWDOC (Paperless-ngx) mit Version, Status und Rechteprüfung, Dokumenteneigentümer | Freigegebene Dokument-ID und Revision |
| Kunde, Auftrag, Stückliste, Bestand, Bestellung, Materialanforderung, Buchung | FLOWERP (ERPNext) | Freigegebene Teilansicht oder Direktlink |
| Arbeitsgang, Rückmeldung, Messwert | FLOWMES und FLOWQ; technische Produktrevision gemäß interner Abgrenzung, ein PLM-System ist nicht vorhanden [FIRMENANGABE U-03] | Referenz auf Arbeitsgang bzw. Prüfung |
| CI-Ergebnis, Releasebeleg, Testausführung, Signaturnachweis, Audit von Schreibaktionen | Geschützter Nachweisspeicher mit Integritätsschutz, QA und Release. Die Protokolldatei der Referenzumgebung wird dorthin überführt. | Manifest mit Verweisen auf Originalbelege |
| Laufereignis, Diagnose, Sicherheitsalarm | Getrennte Betriebs- und Sicherheitsprotokollierung nach Zweck (Prometheus, Grafana, SIEM), Betrieb und Sicherheit | Ereignis-ID und zulässige Metadaten im Vorfall |
| Chatverlauf, persönliche Entwürfe, Warteschlangen und Cache | Befristeter Arbeitsbereich je Person und Vorgang in FLOWAI bzw. Plattform-API mit eigener Zugriffs- und Löschregel | Bewusst übernommenes Arbeitsergebnis im Fachsystem |
| Textsegmente, Embeddings, Suchindex | Abgeleiteter Suchspeicher in PostgreSQL mit pgvector, Verantwortliche für den Wissensdienst | Quell-ID, Revision und Rechtebezug gemäß Teil 08 |

## Referenzkette an einem Beispiel

KI-EK-001 führt im Einsatzregister zur Anforderung REQ-EK-017 in Baseline BL-EK-03 in FLOWWORK. Der Merge Request verweist auf REQ-EK-017, Testfall TC-EK-017 und Commit. Das Release-Manifest enthält integrierten Commit, Image-Digest, Promptversion, Modell-Digest und Richtlinienversion. Testausführung, Fachabnahme und Auslieferung verweisen auf dasselbe Manifest. Der produktive Vorgang verweist auf Lauf-ID und die Nummer der Materialanforderung in FLOWERP. Der Beleginhalt bleibt in FLOWERP. Berechtigte Prüfer können anhand dieser Verweise die Entscheidung rekonstruieren. Andere Leser sehen nur die ihnen zugänglichen Teile.

## Fristen, Sicherung und Berichtigung

Für jede Zeile legt der Eigentümer Schutzbedarf, Rechts- bzw. Geschäftszweck, Fristbeginn, Aufbewahrung, Löschverfahren, Sicherungszyklus und Wiederherstellungsziel fest. Löschung berücksichtigt Suchsegmente, Caches, Exporte und die Wiederherstellung alter Sicherungen. Bei rechtlich angeordneter Aufbewahrung prüft die befugte Stelle Umfang und Dauer, sperrt den Bestand für die Routinelöschung und dokumentiert die spätere Aufhebung. Wird eine Quelle berichtigt, werden abhängige Inhalte neu indiziert. Bereits in einen Geschäftsbeleg übernommene Angaben werden über das Berichtigungsverfahren des Fachsystems korrigiert. Aufbewahrungspflichtige Belege nach GoBD brauchen ein Archiv mit Fristen und Unveränderbarkeit; Paperless-ngx allein erfüllt das nicht (siehe IT-Zielbild, Teil 5).

Abnahmeprobe: Für einen Musterfall den Pfad vom Ticket bis zur fachlichen Abnahme verfolgen. Einen berechtigten Abruf und eine Ablehnung nachweisen. Einen abgelaufenen Testbestand löschen, aus der Sicherung getrennt wiederherstellen und prüfen, dass die Löschvermerke vor der Wiederfreigabe erneut angewendet wurden.

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE U-03] Informationsmanagement und Datenschutz ergänzen reale Instanzen, Dateneigentümer, Status der Ablagefreigabe, Klassifikationen, Fristen, Sperrverfahren und Nachweisorte. Fachbereiche bestätigen das führende System je Objekt, insbesondere: Einsatzregister in FLOWTASK, Anforderungen in FLOWWORK oder Jama, technische Produktrevision ohne PLM und die Abgrenzung zwischen FLOWERP und FLOWMES.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Ablagematrix / Informationsmanagement |
| Zu ergänzen | Produktinstanzen, führendes System je Objekt, Schutzklassen, Fristbeginn und Fristende je Datenart |
| Spätester Entscheid | Vor Datenimport |
| Erwarteter Abschlussbeleg | Freigegebener Auszug aus Ablage- und Löschplan |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |
