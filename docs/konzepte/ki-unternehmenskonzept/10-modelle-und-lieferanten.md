# 10 Lebenszyklus von Modellen, Werkzeugen und Lieferanten

Arbeitsreferenz KI-U-10 · Stand 20.11.2026 · Arbeitsentwurf zur internen Abstimmung

## Aufnahme und Herkunft

Das Plattformteam führt für jedes Modell, Embeddingmodell, Laufzeitsystem, Plug-in und Werkzeug ein Blatt mit eindeutiger Komponenten-ID. Es enthält Herkunft und Hersteller, Bezugsdatum, Lizenztext der konkreten Version, Integritätsnachweis, Datenfluss, Abhängigkeiten, Betriebsanforderungen, Wartungsstatus, Ansprechpartner und Ersatzoption. Auch Modellgewichte, Tokenizer, Quantisierung, Adapter und Inferenzparameter werden erfasst. Öffentlich verfügbare Gewichte allein begründen keine Freigabe für einen bestimmten betrieblichen Verwendungszweck.

Beim Bezug prüft der Einkauf kommerzielle Nutzung, Nutzungsbeschränkungen, Weitergabe, Support, Unterauftragnehmer und End-of-Life. Recht und gegebenenfalls Exportkontrolle prüfen die tatsächlich geplante Branche, Verwendung, Empfänger und Vertragsauflagen. Externe Telemetrie, Cloud-Fallback und Supportzugriff benötigen eine eigene Datenflussentscheidung. Der lokale Standardpfad benötigt keinen externen Modellaufruf. Der Import erfolgt über einen kontrollierten Beschaffungsweg, prüft Herkunft und Digest und legt freigegebene Artefakte in der internen Registry ab.

## Auswahl im realen Arbeitsprofil

| Entscheidung | Messung und Entscheidungskriterium |
| --- | --- |
| Eignung für die Rolle | Gleicher eingefrorener Aufgabensatz pro Modellprofil, deutschsprachige Fachbegriffe, Belegqualität, begründete Enthaltung, gültige strukturierte Ausgabe |
| Kapazität | Gleichzeitige aktive Nutzer, reale Kontext- und Ausgabelängen, Warteschlangenzeit und Antwortzeit als Verteilungen. Last von Langläufen und interaktiver Suche getrennt betrachten. |
| Betriebskosten | Energie und Auslastung unter realer Last, Reserve bei Ausfall, Lizenz, Pflege und Support pro abgeschlossenem Vorgang |
| Wechselbarkeit | Gleicher Rollenvertrag mit Ersatzmodell, Neuaufbau des Suchindex bei neuem Embeddingmodell, Export von Registern und Nachweisen |
| Sicherheits- und Rechtsrisiko | Geprüfter Lizenzentscheid, keine ungeklärte externe Übermittlung, bekannte Schwachstellen bewertet, relevanter Schutzbedarf beherrscht |

## Freigabe, Änderungen und Rückzug

Der Status durchläuft Kandidat, isoliert evaluiert, für benannte Rollen freigegeben, gesperrt und archiviert. Eine Modellfreigabe gilt für definierte Hardware-/Softwarekonfiguration, Sprache, Datenklasse und Rolle. Ein kleineres Modell kann für Extraktion geeignet sein und bei fachlichen Entscheidungen durchfallen. Geänderte Quantisierung, Kontextfenster, Tokenizer, Werkzeugbeschreibung, Systemprompt und Inferenzsoftware können Ergebnisse verändern. Vor Austausch führt QA mindestens die betroffenen Regressionstests aus. Bei geändertem Embeddingmodell werden Indexversion und Einbettungsraum gemeinsam umgestellt. Ein gemischter Index bleibt bis zum reproduzierbaren Vergleich gesperrt.

Beispiel für die Modellkarte: `qwen3:8b` ist Kandidat für den Einkaufsassistenten EK-VORSCHLAG in Stufe A1. Eingabe sind strukturierte Testdaten ohne Kundennamen. Bewertung erfolgt gegen Pflichtfelder, Einheiten, Herkunft und korrektes Abbrechen bei fehlender Kostenstelle. Die Freigabe für diese Rolle erfordert dokumentierte Ergebnisse und eine benannte Entscheidung. Für andere Fachbereiche entsteht daraus kein Freigabestatus.

Bei kompromittierter Komponente, aufgehobenem Support oder ungeklärter Lizenz stoppt der Owner die betroffenen Rollen und ermittelt abhängige Releases über das Manifest. Er entscheidet zwischen vorheriger freigegebener Kombination, manueller Arbeit oder befristeter Aussetzung. Vor Stilllegung werden Schlüssel entzogen, aktive Referenzen entfernt und Nachweise nach Ablageregel erhalten. Die Fähigkeit zum Anbieterwechsel wird mit einem echten Export und Wiederanlauf im Testbetrieb belegt.

## Stand in der Referenzumgebung

| Komponente | Heute | Offen bis zur Freigabe |
| --- | --- | --- |
| Modellserver | Ollama, nur im internen Netz erreichbar | Hardware- und Kapazitätsplanung für die erwartete Nutzerzahl |
| Modelle | `qwen3:8b` für Dialog und Zusammenfassung, `qwen3-coder:30b` für Code; Lizenz nach Herstellerangabe Apache-2.0 | Lizenz der konkreten Version, Herkunft und Digest prüfen; Evaluation je Rolle |
| Modell-Gateway | FLOWGATE (Agentgateway, Apache-2.0); ein virtueller Schlüssel erlaubt dem Dienstkonto von FLOWAI nur diese zwei Modelle | Schlüssel je Dienst und Agent, Mengen- und Kostengrenzen |
| Embedding | Lokale Demo-Kodierung ohne Modell | Embedding-Modell auswählen, freigeben und den Index damit neu aufbauen |
| KI-Oberfläche | FLOWAI (Open WebUI), direkter Zugang zu Ollama abgeschaltet | Lizenz und Versionsstand der eingesetzten Fassung prüfen |

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE U-10] Plattform, Einkauf und Recht ergänzen zugelassene Bezugsquellen, konkrete Modelllizenzen und Nutzung, interne Hardware, gleichzeitig aktive Nutzer, Kostenrahmen, Vertretung und Mindestankündigung für Abkündigungen. Prüfung vor Übernahme produktiver Gewichte wiederholen.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Komponentenblatt / Plattform und Einkauf |
| Zu ergänzen | Konkrete Version, Herkunft, Lizenz, erlaubter Einsatz und Ersatzmodell |
| Spätester Entscheid | Vor Komponentenfreigabe |
| Erwarteter Abschlussbeleg | Lizenzentscheid und Evaluation im geplanten Einsatz |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |
