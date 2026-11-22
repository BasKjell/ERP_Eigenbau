# MES-Arbeitsplatz bedienen

Der FLOWMES-Arbeitsplatz unter [localhost:8088/mes](http://localhost:8088/mes)
bildet die operative Arbeit auf dem Shopfloor ab. Er ist für Touchscreen,
Notebook und Tablet ausgelegt. ERPNext bleibt führend für Work Order, BOM,
Bestand und Kosten; FLOWMES führt Arbeitsvorrat, Bedienhandlungen und
kontextbezogene Arbeitsunterlagen zusammen.

## Funktionsumfang der Demo

- persönlicher und gesamter Arbeitsvorrat,
- Fertigungsroute mit Vorgänger- und Folgeschritten,
- Start, Pause und Abschluss eines Arbeitsgangs,
- automatisch laufende Terminalzeit und manueller Zeitnachtrag,
- Gutmenge, Ausschuss und Seriennummern,
- Pflichtchecklisten und Prüfmerkmale,
- Störungsmeldung, Sperre, Nacharbeit und Wiederfreigabe,
- Material-, Chargen- und WIP-Informationen,
- eingebettete PDF-Anzeige über die Paperless-/DMS-Verknüpfung,
- Schichtkennzahlen und Ereignisverlauf.

!!! info "Demo- und Produktivgrenze"
    Die Oberfläche und MES-Geschäftsregeln sind lauffähig. Die Demo speichert
    ihre Rückmeldungen im lokalen, rücksetzbaren Szenario. Die spätere
    produktive ERPNext-Synchronisation verwendet den beschriebenen Vertrag aus
    [ERPNext zu MES](../interfaces/erpnext-mes.md).

## Bedienperson und Arbeitsvorrat

Oben rechts wird die Bedienperson ausgewählt. Für die Demo stehen fünf
Personen für Montage, Elektronik, Firmware, Test und Endprüfung bereit. Der
Filter **Meine** zeigt nur die zugeordneten Arbeitsgänge. **Alle** zeigt die
gesamte Route, **Kritisch** priorisierte oder gesperrte Vorgänge.

| Status | Bedeutung | Zulässige nächste Handlung |
|---|---|---|
| Bereit | Vorgänger ist abgeschlossen | Arbeit starten |
| In Arbeit | Zeit läuft für die aktive Bedienperson | pausieren, Störung melden, abschließen |
| Pausiert | Zeit wurde gestoppt und Grund gespeichert | erneut starten |
| Wartet | Vorgänger noch nicht vollständig | keine Bearbeitung |
| Gesperrt | offene Störung oder Abweichung | Nacharbeit dokumentieren |
| Abgeschlossen | Menge und Pflichtdaten zurückgemeldet | nur lesen |

## Arbeitsgang durchführen

1. Bedienperson auswählen und die erste bereite Aufgabe öffnen.
2. Work Order, Artikel, Revision, Arbeitsplatz, Menge und Termin prüfen.
3. die Fertigungsroute kontrollieren; ein wartender Arbeitsgang darf nicht
   vorgezogen werden.
4. unter **Anleitung & Checkliste** jeden Arbeitsschritt lesen.
5. unter **Material & Seriennummern** Material, Menge und Charge abgleichen.
6. **Arbeit starten** wählen. Ab diesem Zeitpunkt läuft die Terminalzeit.
7. Pflichtprüfungen nach der tatsächlichen Durchführung markieren.
8. mit **Abschließen** Gutmenge, Ausschuss, Seriennummern und Bemerkung
   zurückmelden.

Der Folgearbeitsgang wird erst **Bereit**, wenn die gesamte Sollmenge des
Vorgängers abgeschlossen wurde. Teilmengen lassen den Vorgang erneut bereit.

## Pause und Zeitkorrektur

**Pause** beendet die laufende Zeitzeile. Ein Grund ist verpflichtend, damit
Materialmangel, technische Klärung, Störung und normale Pausen unterscheidbar
bleiben. **Zeit nachtragen** ergänzt eine abgeschlossene Korrekturzeile mit
Bedienperson, Tätigkeit, Dauer und Begründung.

Korrekturbuchungen sind für echte Nachträge gedacht. Eine laufende
Terminalzeit wird nicht durch wiederholte manuelle Buchungen ersetzt.

## Störung und Nacharbeit

1. **Störung** wählen und Kategorie sowie konkrete Beschreibung erfassen.
2. Das MES beendet eine offene Zeitzeile, legt eine Referenz `NCR-MES-…` an
   und setzt den Arbeitsgang auf **Gesperrt**.
3. Betroffenes Material und Gerät physisch kennzeichnen und sichern.
4. Nach der Abstellmaßnahme **Nacharbeit abschließen** wählen.
5. Ursache und Maßnahme dokumentieren; der Arbeitsgang wird wieder **Bereit**.

Eine Störungsauflösung ersetzt keine erforderliche Qualitätsentscheidung. Im
Produktivbetrieb schreibt der Adapter die Abweichungsreferenz an ERPNext bzw.
das führende QMS zurück.

## Arbeitsunterlagen und DMS

Rechts werden nur die Dokumente angezeigt, die dem gewählten Arbeitsgang
zugeordnet sind. Titel, Dokumentart und Revision stammen aus der
MES-Referenz; der Inhalt wird über `/api/documents/{document_id}` geladen.

Ist Paperless per API-Token konfiguriert, führt das MES zusätzlich eine
Live-Suche nach dem Artikel aus und zeigt **DMS LIVE**. Ohne Token bleiben die
versionierten Demo-PDFs verfügbar und der Status lautet **DMS DEMO**. Ein
Dokument wird im eingebetteten PDF-Viewer geöffnet, ohne den Arbeitskontext zu
verlassen.

## Wiederholbarer Präsentationsablauf

1. bei Bedarf im Management-Cockpit **Demo zurücksetzen** wählen,
2. FLOWMES öffnen und **Emil Elektronik** auswählen,
3. `JC-2027-0130` öffnen und Arbeitsanweisung sowie Mainboard-Zertifikat
   zeigen,
4. Arbeit starten, einige Sekunden laufen lassen und 15 Minuten Rüstzeit
   nachtragen,
5. optional eine Materialstörung anlegen und nach dokumentierter Nacharbeit
   wieder freigeben,
6. erneut starten, alle vier Pflichtprüfungen markieren und fünf
   Seriennummern zurückmelden,
7. zeigen, dass `JC-2027-0131` **Bereit** wird.

Über **Demo zurücksetzen** wird auch der FLOWMES-Zustand auf den definierten
Ausgang zurückgesetzt. Für automatisierte Präsentationen kann alternativ
`POST /api/mes/reset` nur den MES-Bereich zurücksetzen; der übrige
Management-Prozessstand bleibt dabei erhalten.
