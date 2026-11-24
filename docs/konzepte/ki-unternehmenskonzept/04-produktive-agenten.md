# 04 Betrieb produktiver KI-Agenten

Arbeitsreferenz KI-U-04 · Stand 20.11.2026 · Arbeitsentwurf zur internen Abstimmung

## Verantwortungsmodell

Ein produktiver Agent führt eine eng beschriebene Tätigkeit in genau einem genehmigten Prozess aus und steht mit Owner und Stufe im Agentenregister (Teil 02). Der Service Owner führt einen Betriebssteckbrief mit Einsatz-ID, Fachverantwortlichem, technischer Identität, Autorisierungsart, erlaubten Werkzeugen, Datenklassen, Versionsstand, Zeit- und Mengenlimit, Vertretung und Abschaltweg. Entwicklungsagenten erhalten keinen Produktionszugriff. Ein Deploymentdienst übernimmt ausschließlich einen geprüften Stand aus dem Releaseprozess.

Interaktive Agenten handeln im begrenzten Auftrag einer angemeldeten Person. Ein zeitgesteuerter Dienst, etwa zur Klassifikation neuer interner Tickets, erhält einen gesonderten genehmigten Systemauftrag mit eigenem Datenraum. Ein Wechsel zwischen beiden Betriebsarten erfordert eine eigene Autorisierung. Das Modell darf den Geltungsbereich des Auftrags, Freigaberechte und Laufbudget technisch nicht erweitern.

## Zustand des Vorgangs und Wiederanlauf

| Zustand | Verantwortlicher Schritt | Verhalten bei Fehler |
| --- | --- | --- |
| Angefordert | Orchestrator prüft aktive Einsatzfreigabe, Identität, Kontingent und aktuellen Prozessstand | Ablehnen oder Warteschlange mit Ablaufzeit |
| Vorgeschlagen | Agent liefert strukturierte Werte und Herkunft. Fachsystem validiert zulässige Felder. | Fehlende Angaben an Auftraggeber zurückgeben |
| Bestätigt | Freigabedienst bindet Person, Aktion, Objekt, Ziel, Nutzdaten-Hash, Version und Frist | Bei Änderung neu bestätigen |
| In Ausführung | Worker reserviert Vorgangs-ID, prüft Rechte und sendet mit Idempotenzschlüssel | Bei unklarem Ergebnis Statusabgleich starten |
| Abgeschlossen oder ungeklärt | Zielbeleg verknüpfen oder Fall in Klärwarteschlange übergeben | Bei ungeklärtem Status bleibt jede erneute Anlage gesperrt |
| Angehalten | Betrieb stoppt neue und wartende Aktionen. Laufende Aufrufe werden abgeglichen. | Fachbereich übernimmt manuell anhand derselben Referenzen |

Für KI-EK-001 darf der Worker nur den Entwurf einer Materialanforderung in FLOWERP erzeugen. Bei Zeitüberschreitung nach der Übertragung kann der Entwurf bereits existieren. Der Betrieb fragt mit ursprünglicher Referenz nach. Existiert der Entwurf, wird dessen ID mit dem Lauf verknüpft. Ist das Ergebnis unbestimmbar, übernimmt der Einkauf den Fall. Ein neuer Schlüssel zum Erzwingen einer Wiederholung ist unzulässig. Eine bereits entstandene fachliche Wirkung muss die zuständige Person nach den Regeln des Zielsystems korrigieren.

## Betriebsgrenzen und Übergabe

FLOWGATE (Agentgateway) vermittelt die zugelassenen Modelle. Jeder Dienst erhält einen eigenen virtuellen Schlüssel, der nur die für ihn freigegebenen Modelle erlaubt; der Modellserver Ollama ist nur im internen Netz erreichbar. Orchestrator, Warteschlange, Modellserver und Integrationsdienste liegen in getrennten Betriebsbereichen mit erlaubten Verbindungen. Jede Werkzeugidentität ist auf Zweck und Mandant begrenzt. Für jeden Lauf werden maximale Werkzeugaufrufe, Laufzeit, parallele Aufträge und Datenmenge erzwungen. Die Betriebsbereitschaft prüft verfügbare Kapazität, Alter offener Aufträge, Rückstau und Erreichbarkeit der Rechte- und Nachweisdienste. Bei fehlender Berechtigungsentscheidung oder fehlendem Pflichtbeleg unterbleibt eine neue schreibende Aktion.

Vor Bereitschaftsübernahme übt eine zweite Person am Testmandanten den Stopp, klärt eine laufende Aktion und startet aus bekanntem Stand wieder. Der Einsatzverantwortliche entscheidet über Wiederfreigabe nach Abgleich aller offenen Wirkungen. Im Runbook stehen manueller Fachweg, betroffene Rollen, Kommunikationsweg und Zeitpunkt des nächsten Statusupdates. Ein laufender Ausfall der KI darf den manuellen ERP-Prozess nicht blockieren.

## Infrastruktur, Last und Wiederherstellung

GPU-Aufträge für interaktive Auskunft und lang laufende Entwicklungsjobs werden getrennt begrenzt. Ein belegtes Entwicklungsbudget darf den manuellen Portalzugang nicht behindern. Betrieb plant Zugangskontrolle für Administrationswege, ausgehende Verbindungen, Zertifikats- und Schlüsselwechsel, Patchfenster, interne Paketspiegel und Vertretung. Daten auf Datenträgern, im Transport und in Sicherungen werden nach Schutzbedarf geschützt. Ein Wiederanlauftest prüft gemeinsam Keycloak-Konfiguration und Schlüsselzugriff, Fachsystemverbindung, Warteschlange, versionierte Richtlinien, Registry und Nachweise. Abgeleitete Suchindizes können aus freigegebenen Quellen neu entstehen. RTO (maximale Wiederanlaufzeit) und RPO (tolerierter Datenverlust) werden pro Dienst aus der Prozessauswirkung abgeleitet.

## Stand in der Referenzumgebung

Die Referenzumgebung läuft als Docker Compose auf einem Rechner. Schreibwerkzeuge der MCP-Server lassen sich global über `MCP_WRITE_ENABLED` abschalten; sie schreiben ausschließlich Testdaten und protokollieren jede Charge mit `batch_id`. FLOWAGENTS bringt inzwischen einen Stopp-Schalter je Agent und global, Laufbudgets je Änderungsklasse, eine Aktionswarteschlange mit Ablaufzeit und Fachagenten mit menschlicher Freigabe (nur Entwürfe, kein Versand). Für den Produktivbetrieb fehlen weiterhin Stopp je Werkzeug, Klärwarteschlange, TLS zwischen den Diensten, Mengenbegrenzung, Sicherung, Hochverfügbarkeit und Rufbereitschaft. Für Fachagenten mit Postfach- und Fachsystem-Anbindungen werden n8n und Dify bewertet, für die Ablaufmechanik Temporal oder LangGraph ([Orchestrierung](../../agents/plattformstrategie.md)). Die Produktivplattform folgt dem IT-Zielbild (Teil 3 dort).

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE U-04] Betrieb und Einkauf tragen tatsächliche Ruf- und Vertretungswege, Zeitlimits, Warteschlangengrenzen, zugelassene Betriebszeiten, Abschaltschalter sowie maximal tolerierbare Unterbrechung und Datenverlust ein. Den Abgleich ungeklärter Entwürfe in FLOWERP mit dem Betrieb erproben.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Betriebssteckbrief / Service Owner |
| Zu ergänzen | RTO, RPO, Mengenlimit, Stoppbefugnis und manueller Fachweg |
| Spätester Entscheid | Vor Betriebspilot |
| Erwarteter Abschlussbeleg | Geübter Stopp mit Abgleich und Wiederanlauf |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |
