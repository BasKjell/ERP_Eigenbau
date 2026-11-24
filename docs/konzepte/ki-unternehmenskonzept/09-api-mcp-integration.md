# 09 Fachschnittstellen, APIs und MCP-Werkzeuge

Arbeitsreferenz KI-U-09 · Stand 20.11.2026 · Arbeitsentwurf zur internen Abstimmung

## Ein Fachvorgang pro Werkzeug

Der MCP-Server stellt einem Agenten einzelne, dokumentierte Geschäftsfunktionen bereit. Das Zielsystem verantwortet die Fachentscheidung. Der Adapter validiert Schema und Mandant, prüft Identität, Aktion und Objekt, begrenzt Datenmenge und Zeit und liefert typisierte Ergebnisse. Ein maschinenlesbarer Werkzeugkatalog führt Besitzer, API-Version, unterstützte Fachsystemversion, Ein- und Ausgabeschema, Autorisierungsart, Datenklassen, Seiteneffekte und Abschaltweg. Dynamisch gefundene Werkzeuge werden erst nach fachlicher und technischer Freigabe aktiviert.

| Werkzeug (Server) | Zulässige Eingabe und Wirkung | Rückgabe |
| --- | --- | --- |
| `get_document_revision` (DMS-MCP, neu) | Dokument-ID und Revision aus einem genehmigten Datenraum, lesend im Auftrag der Person | Autorisierter Inhalt mit Seiten- bzw. Abschnittsangabe und Revision oder neutrale Nichtverfügbarkeit |
| `create_requirement_draft` (FLOWWORK, neu, Entwicklungsrealm) | Projekt, Baseline-Bezug und strukturierter Anforderungstext | Entwurfs-ID und neue Revision, kein Baseline-Wechsel |
| `create_material_request_draft` (ERP-MCP, neu) | Gültiger Bestätigungsbezug, Artikel, Menge, Einheit, Kostenstelle und Vorgangsreferenz | Genau eine Nummer der Materialanforderung im Status Entwurf oder ein typisierter Klärstatus |
| `get_material_request_status` (ERP-MCP, neu) | Ursprüngliche Vorgangsreferenz im selben Mandanten und Berechtigungskontext | vorhanden, nachweislich nicht angelegt oder ungeklärt |

Die Namen folgen der Schreibweise der Referenzumgebung. Der Werkzeugkatalog führt zu jedem Werkzeug eine Version; eine inkompatible Änderung erhält einen neuen Namen oder eine neue Hauptversion.

## Beispielvertrag der schreibenden Operation

Beispielhafte fachliche Nutzdaten:
{"request_id":"RUN-417","article_id":"DEMO-17","quantity":4,"unit":"Stk","cost_center":"K-210","source_revision":"BED-8@2","approval_ref":"CONF-8"}
Der Server bezieht Person, Mandant und Dienst aus dem verifizierten Kontext. Der Bestätigungsdienst bindet CONF-8 an den Hash der kanonischen Nutzdaten, Aktion, Ziel, Person und Ablaufzeit. Die Schnittstelle verwirft unbekannte Felder und ungültige Werte. Erfolg liefert beispielsweise {"status":"draft_created","document_id":"MAT-MR-2026-00042","request_id":"RUN-417"}. IDs sind fiktiv. In ERPNext entspricht der Entwurf einer Materialanforderung im Dokumentstatus „Entwurf“; Einreichen und Bestellung bleiben beim Einkauf.

Vor dem Aufruf reserviert der Adapter einen eindeutigen Schlüssel je Mandant, Aktion und Vorgang. Gleicher Schlüssel und gleiche Nutzdaten liefern bei Wiederholung denselben bekannten Zustand. Gleicher Schlüssel mit anderen Daten ergibt einen Konflikt. Das Zielsystem erzwingt eine eindeutige Referenz oder unterstützt eine transaktional wirksame Idempotenzfunktion. In FLOWERP ist dafür ein eindeutiges Zusatzfeld für die Vorgangsreferenz an der Materialanforderung vorgesehen [FIRMENANGABE U-09]. Geht die Antwort nach dem Commit verloren, liest der Adapter den Status mit der ursprünglichen Referenz. Kann das ERP weder eindeutige Zuordnung noch zuverlässigen Abgleich liefern, wird diese schreibende Integration im Pilot nicht aktiviert. Eine lokale Liste gesendeter Anfragen allein schließt eine Doppelanlage nicht aus.

## Stand in der Referenzumgebung

Drei MCP-Server laufen mit dem offiziellen Python-SDK: ERP/Plattform (lesen und bestätigte Testdaten), DMS (lesen und lokalen Suchindex aktualisieren) und Prozess-Wiki (nur lesen). Lesende ERP-Abfragen nutzen feste Dokumenttypen, Felder, Filter und Mengengrenzen; freies SQL, beliebige Dokumenttypen und Shell sind gesperrt. Der Schreibvertrag für Testdaten ist eine gute Grundlage: erst Aufruf ohne Bestätigung mit normalisierter Vorschau, dann derselbe Aufruf mit `confirm=true`, Duplikate werden übersprungen oder als Fehler gemeldet, jede Charge erhält eine `batch_id` und kann gezielt zurückgenommen werden. Für produktive Schreibwerkzeuge kommen hinzu: Bindung der Bestätigung an Person und Nutzdaten-Hash, eindeutiger Vorgangsschlüssel im Zielsystem, Statusabfrage nach Abbruch und Benutzeridentität statt technischem Konto.

## Betrieb und Sicherheit der Anbindung

Für HTTP-basierte MCP-Dienste werden zielgebundene Autorisierung, verschlüsselte Kommunikation und getrennte Clientidentitäten vorgesehen. Ein Token wird nur an den vorgesehenen Empfänger gesendet. Ein nachgelagerter Fachsystemaufruf verwendet seine eigene zugelassene Autorisierung. Agenten erhalten keine allgemeinen SQL-, Shell- oder Administrationswerkzeuge. Direkte Tabellenupdates im ERP umgehen die Fachlogik und sind für diesen Weg ausgeschlossen. Bei Altsystemen werden unterstützte APIs, Importe mit Quittung oder eine manuelle Übergabe anhand ihrer Prüf- und Rückmeldefähigkeit ausgewählt.

Ereignisse enthalten Ereignis-ID, Typ, Schemaversion, Zeit, fachliche Referenz und Korrelation. Der Empfänger erkennt Duplikate und veraltete Ereignisse. Bei nicht auflösbarer Reihenfolge liest er den aktuellen Fachstand nach. Fehlerklassen sind Validierungsfehler, fehlende Berechtigung, Konflikt, vorübergehende Störung und unbekannte Fachwirkung. Der Vertrag regelt je Klasse Rückfrage, Wiederholung oder manuelle Klärung. Abnahmetests umfassen Parallelaufruf, Duplikat, Rechteentzug, verspätete Nachricht, inkompatible Version und Abbruch nach erfolgreicher Zieloperation.

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE U-09] Anwendungsverantwortliche ergänzen reale API-Dokumentation von FLOWERP, FLOWDOC und FLOWWORK, den Testmandanten in FLOWERP, das eindeutige Feld für die Vorgangsreferenz, Authentisierungswege, Rate-Limits, Änderungsankündigung und technische Ansprechpartner. Schreibrechte nur für erfolgreich geprüfte Operationen freigeben.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Fachvertrag / Integration |
| Zu ergänzen | Mandant, Endpunkt, Referenzschlüssel und Statusabfrage |
| Spätester Entscheid | Vor Schreibtest |
| Erwarteter Abschlussbeleg | Testergebnis bei paralleler und unterbrochener Anlage |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |

Quelle: MCP-Spezifikation für HTTP-Autorisierung, festgelegter Referenzstand 25.11.2025 — <https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization>
