# Management-Portal bedienen

## Einsatz im Unternehmensprozess

Das Portal ist das gemeinsame Cockpit für den Demofall SCU-100. Es zeigt den
End-to-End-Status, führt durch die Prozessstufen und bündelt Dokumente,
Qualitätsereignisse sowie die quellenbasierte Auskunft. Im PoC sind Aktionen
simuliert; in einer echten Integration bleiben ERPNext und Paperless die
führenden Systeme.

| Prozessmoment | Aktion im Portal | Ergebnis |
|---|---|---|
| Auftragsbesprechung | **Live-Übersicht** öffnen | Status, Termin, Wert und Engpass sind sichtbar |
| Prozessdurchlauf | **Nächster Schritt** wählen | nächste Demo-Stufe wird aktiviert |
| Abweichung | **Fehlerfall starten** | SN-10004 wird gesperrt, NCR wird angelegt |
| Nacharbeit | **Nacharbeit abschließen** | Wiederholtest und Freigabe werden dokumentiert |
| Dokumentprüfung | **Dokumente** öffnen | gültige PDF-Nachweise sind erreichbar |
| Statusfrage | **AI Copilot** öffnen | Antwort mit Systemquellen wird angezeigt |

## Auftrag durchspielen

1. `http://localhost:8088` öffnen.
2. Auftragskopf `SO-4711`, Revision, Menge und Liefertermin prüfen.
3. Die Kacheln von CRM bis Rechnung in fachlicher Reihenfolge durchgehen.
4. Nach jeder Aktion Ergebnis und Nachweis kontrollieren; nicht nur den
   Fortschrittsbalken betrachten.
5. Für Qualität den Fehlerfall auslösen, die Sperre prüfen und erst danach die
   Nacharbeit abschließen.
6. Unter **Dokumente** Zeichnung, Prüfplan, Zertifikat und Abnahmeprotokoll
   anhand ihrer Revision bzw. Referenz öffnen.
7. Im Copilot eine Statusfrage stellen und die Quellenchips kontrollieren.

## Zurücksetzen und Grenzen

**Demo zurücksetzen** stellt nur den reproduzierbaren Portalzustand wieder her.
Es löscht keine ERPNext- oder Paperless-Daten. Portalaktionen sind kein Ersatz
für Freigaben im führenden Fachsystem. Vor einer realen Lieferung müssen
Auftrag, Seriennummern, Qualitätsstatus und Dokumente dort geprüft sein.

Weiterführend: [Gesamtprozess](../../processes/order-to-cash/overview.md),
[Management-Demo](../../user-guides/presentation.md) und
[Portal-Administration](../admin/portal.md).
