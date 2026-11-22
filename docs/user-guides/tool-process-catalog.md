# Prozesskatalog je Anwendung

Diese Seite ist der kurze Einstieg für Anwender. Sie beschreibt pro sichtbarer
FLOW-Anwendung mindestens einen typischen Ablauf und nennt das erwartete
Ergebnis. Der vollständige Auftrag bleibt über Kunde, Auftrag, Projekt/
Kommission, Artikel, Revision und Dokument-ID verbunden.

## Durchgängiger Geschäftsvorgang

```text
Opportunity → Auftrag → Spezifikation → Planung → Einkauf → Wareneingang
→ Prüfung → Fertigung → Rückmeldung → Dokumentation → Lieferung → Auswertung
```

| Anwendung | Typischer Anwenderprozess | Ergebnis / Nachweis |
|---|---|---|
| **FLOWPORTAL** | Anmelden → persönliche Prioritäten prüfen → Aufgabe oder Anwendung öffnen → Status zurückmelden | rollenabhängiger Tagesarbeitsplatz mit eindeutiger Quelle |
| **FLOWMANAGE** | Rundgang starten → 25 Stationen mit **Weiter** durchlaufen → Fit-Gaps und Pilotentscheidung festhalten | gemeinsames Managementbild und dokumentierte nächste Entscheidung |
| **FLOWERP** | Kundenstamm prüfen/anlegen → Opportunity qualifizieren → Angebot → Auftrag → Projekt/Kommission zuordnen | kaufmännische Belegkette als führende Wahrheit |
| **FLOWWORK** | Anforderung erfassen → Felder und Beziehungen pflegen → Review starten → Kommentare bearbeiten → Baseline freigeben → Testnachweis verknüpfen | versionierte, nachvollziehbare Spezifikation |
| **FLOWTASK** | Ticket aus Anforderung oder Ausnahme erzeugen → Verantwortlichen und Termin setzen → Arbeit dokumentieren → Ticket abschließen | ausführbare Aufgabe mit Status, Zeit und Rückverweis |
| **FLOWQ** | Wareneingang scannen → freigegebenen Prüfplan laden → Stichprobe ziehen → Messwerte erfassen/übernehmen → Annahme oder Sperre entscheiden | Prüfprotokoll, Messmittelnachweis und Lagerentscheidung |
| **FLOWMES** | nächsten freigegebenen Arbeitsgang wählen → Anleitung/Pflichtprüfung lesen → starten → Zeit, Material und Seriennummer buchen → Qualität bestätigen → fertigmelden | belastbare Ist-Daten zur Job Card und zum Auftrag |
| **FLOWDOC** | Dokument hochladen → Projekt, Typ, Revision und Liefertermin pflegen → Prüfer zuweisen → Review → Freigabe → gültige Revision veröffentlichen | freigegebene, berechtigte und terminierte Dokumentrevision |
| **FLOWDOCS** | Prozess oder Begriff suchen → Anleitung öffnen → verlinkte Fachanwendung aufrufen → Verbesserung an den Dokument-Owner melden | eine lesbare Prozessquelle für Anwender und KI |
| **FLOWHR** | Kommen/Gehen oder Abwesenheit erfassen → Teamkalender prüfen → Genehmigung durch Vorgesetzten → Saldo an ERP übergeben | Anwesenheit, Urlaub und Mehrarbeit mit Freigabestatus |
| **FLOWSPACE** | Standort → Etage → Raum wählen → freien Platz im Grundriss wählen → Zeitraum buchen; bei Kollegensuche Platz markieren | Arbeitsplatzbuchung und sichtbarer Kollegenplatz |
| **FLOWFIN** | Live-Forecast öffnen → Umsatz, Cash und Marge prüfen → Abweichung bis Auftrag/Projekt zurückverfolgen → Maßnahme zuweisen | entscheidbare Finanz- und Projektausnahme |
| **FLOWINSIGHT** | Dashboard öffnen → Zeitraum/Projekt filtern → Kennzahl bis Arbeitsgang oder Beleg auflösen → Quelle in FLOWERP/FLOWDOC prüfen | visualisierte Live-Daten ohne zweite Datenerfassung |
| **FLOWAI** | Frage mit Projekt-/Auftragskontext stellen → Wiki und DMS-Vektorsuche auswählen → Treffer und Originaldokumente prüfen → vorgeschlagene Aktion bewerten → schreibende Aktion ausdrücklich bestätigen | quellenbasierte Antwort mit Paperless-/Wiki-Links und menschlicher Freigabe |
| **FLOWGATE** | Modell freigeben → virtuellen Schlüssel und Quote zuordnen → Richtlinie testen → Nutzung und Fehler prüfen | zentral kontrollierter Zugriff auf lokale Qwen-Modelle |
| **FLOWID** | AD-Benutzer einer freigegebenen Gruppe zuordnen → Synchronisation prüfen → Keycloak-Rolle kontrollieren → SSO-Zugriff testen | nachvollziehbare Kette AD-Gruppe → Rolle → Anwendung |
| **FLOWAPI** | Importpaket validieren → Dry-Run prüfen → freigegebenen Import starten → Ergebnis und Fehlerliste archivieren | wiederholbarer Migrationslauf mit Audit-Trail |
| **FLOWOPS** | Alarm oder Readiness öffnen → betroffenen Dienst bestimmen → Protokoll/Metrik prüfen → Maßnahme ausführen → Wiederherstellung bestätigen | dokumentierte Störung und nachgewiesene Betriebsbereitschaft |

## Beispiel: DMS-Freigabe mit Workflow

1. Der Ersteller lädt das Dokument in **FLOWDOC** hoch und pflegt Projekt,
   Dokumenttyp, Revision, Meilenstein, Liefertermin und Vertraulichkeit.
2. Der Workflow prüft Pflichtfelder und weist den fachlichen Prüfer zu.
3. Der Prüfer kommentiert oder setzt den Status auf **fachlich geprüft**.
4. Der Freigabeverantwortliche bestätigt die gültige Revision. Ersteller und
   Freigeber dürfen in kritischen Workflows nicht dieselbe Person sein.
5. Die freigegebene Revision wird für berechtigte Benutzer und FLOWAI
   sichtbar; die Vorversion bleibt als Baseline und Auditnachweis erhalten.
6. Änderungen erzeugen eine neue Revision und durchlaufen den Workflow erneut.

## Beispiel: Auftrag in FLOWERP anlegen

1. Kunden-, Adress-, Kontakt-, Zahlungs- und Lieferbedingungen prüfen.
2. Opportunity mit Menge, Artikelrevision, Wahrscheinlichkeit und Zieltermin
   qualifizieren.
3. Angebot aus der Opportunity und Auftrag aus dem Angebot erzeugen; nicht
   ohne Vorgänger frei neu erfassen.
4. Projekt/Kommission, Preis, Steuer, Incoterm und Liefertermin kontrollieren.
5. Auftrag freigeben. Danach werden MRP, Einkauf, Work Orders und Lieferung
   aus dieser Belegkette erzeugt.

## Beispiel: Wareneingang bis freier Bestand

1. Lager erfasst Purchase Receipt, Menge, Charge/Seriennummer und
   QS-Zwischenlager.
2. FLOWQ lädt Bestellung und freigegebenen Testplan, bestimmt die Stichprobe
   und prüft den Kalibrierstatus des Messmittels.
3. Bei bestandenem Prüflos bucht FLOWERP in den vorgesehenen freien Bestand.
   Bei Abweichung folgen Sperrlager, NCR und Lieferantenmaßnahme.
4. FLOWDOC archiviert das Prüfprotokoll; FLOWINSIGHT zeigt Termin- und
   Qualitätswirkung.

## Beispiel: Fertigungsarbeitsgang rückmelden

1. Mitarbeiter und Arbeitsplatz in FLOWMES wählen; nur freigegebene nächste
   Arbeitsgänge werden angeboten.
2. Anleitung und Checkliste öffnen, Job starten und Material/Charge
   bestätigen.
3. Zeit, Unterbrechung, Ausschuss/Nacharbeit und erzeugte Seriennummer buchen.
4. Prüfmerkmale bestätigen und Arbeitsgang fertigmelden.
5. FLOWERP erhält Job-Card-, Mengen- und Zeitstatus; FLOWFIN und
   FLOWINSIGHT lesen die aktualisierten Werte live aus.

## Technische Werkzeuge ohne täglichen Fachprozess

PostgreSQL/pgvector, Docker Compose und Ollama sind Betriebsbausteine. Sie
werden nicht von Fachanwendern bedient. Ihr Standardablauf lautet Änderung in
Staging testen, Backup/Restore nachweisen, Freigabe dokumentieren, kontrolliert
ausrollen und Healthchecks sowie Rollback prüfen. Die Administrationsseiten im
Werkzeugkatalog enthalten die jeweiligen Befehle und Abnahmekriterien.
