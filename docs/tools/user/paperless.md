# Paperless-ngx im Unternehmensprozess

Paperless-ngx ist das führende System für Arbeitsunterlagen und Nachweise.
ERPNext speichert nur die stabile Dokumentreferenz. Nach der Anmeldung zeigt
Paperless ausschließlich Dokumente, für die Funktionsrolle und Projektzugriff
zusammenpassen.

Die **neun Punkte oben links** öffnen denselben Unternehmens-App-Launcher wie
Portal, MES und ERPNext. Ein Wechsel in ein anderes Werkzeug verändert weder
Dokumentstatus noch Paperless-Berechtigungen.

## Dokumentfluss

| Prozessschritt | Dokument | Benutzeraktion |
|---|---|---|
| Auftrag/Fertigung | Zeichnung, Montageanweisung | Projekt, Artikel, Revision und Status prüfen |
| Wareneingang | Lieferantenzertifikat | Projekt, Bestellung und Charge eintragen |
| Produktion | Arbeitsanweisung | aus Work Order öffnen; nur freigegebenen Stand verwenden |
| Qualitätsprüfung | Prüfplan, Messprotokoll | Seriennummer, NCR und Ergebnis referenzieren |
| Lieferung | Abnahmeprotokoll | Auftrag, Work Order und Seriennummern verknüpfen |

## Dokument importieren

1. PDF über **Dokument hochladen** oder den Consume-Ordner einliefern.
2. Nach dem Import `Status/Entwurf` kontrollieren.
3. Dokumenttyp und einen eindeutigen Titel festlegen.
4. `Projekt / Kommission`, Artikel, Revision oder Charge pflegen.
5. Projekt-Tag und Ablagepfad kontrollieren. Nicht erkannte Dokumente bleiben
   im geschützten `DMS-Eingang`.
6. Erst nach vollständiger Prüfung den Zielstatus hinzufügen.

Dateinamen mit `KOM-2027-4711` werden automatisch der Kundenkommission
zugeordnet. Für den Demofall erkennen die Regeln außerdem `SCU-100`,
`Auftrag-4711` und `BE-24117`. Eine automatische Projektfreigabe allein aus
dem Consume-Pfad ist aus Sicherheitsgründen nicht aktiv.

## Meilensteine und Dokumentliefertermine pflegen

Für projektbezogene Lieferdokumente zusätzlich mindestens `Meilenstein`,
`Dokumentlieferobjekt`, `Dokumentverantwortung`, `Baseline-Version`,
`Baseline-Termin` und `Liefertermin` pflegen. Der Verantwortliche aktualisiert
`Forecast-Termin` und `Fortschritt (%)`; nach nachweisbarer Übergabe setzt die
Dokumentenlenkung das `Tatsächliche Lieferdatum`.

Der [Dokumentenlieferplan in Grafana](grafana.md#dokumentenlieferplan-offnen)
zeigt diese Angaben projektweise. Die Daten werden in Paperless geändert, nicht
in Grafana. Eine verspätete Prognose wird im Dashboard als **Gefährdet**, ein
überschrittener Solltermin ohne Ist-Datum als **Überfällig** angezeigt.

## Prüfen und freigeben

| Ausgang | Benutzer fügt hinzu | Ergebnis / danach änderungsberechtigt |
|---|---|---|
| Entwurf | `Status/In Prüfung` | Bearbeitung gesperrt; Projekt-Prüfer |
| In Prüfung | `Status/Zur Freigabe` | Prüfung abgeschlossen; Projekt-Freigeber |
| In Prüfung | `Status/Abgelehnt` | zurück an Projekt-Bearbeiter |
| Zur Freigabe | `Status/Freigegeben` | für Projektleser gültig; Freigeber verwaltet Lebenszyklus |
| Zur Freigabe | `Status/Abgelehnt` | zurück an Projekt-Bearbeiter |
| Abgelehnt | `Status/Entwurf` | Überarbeitung möglich |
| Freigegeben | `Status/Obsolet` | nicht mehr für neue Vorgänge verwenden |

Der Workflow entfernt den alten Status automatisch. Eine direkte Freigabe ohne
Prüfung wird entfernt. Vor der finalen Freigabe sind `Freigegeben durch` und
`Freigabedatum` zu pflegen; Kommentare und Prüfergebnis gehören in die
Dokumenthistorie beziehungsweise eine Notiz.

!!! danger "Keine Arbeit mit Entwurf oder obsoletem Stand"
    MES und Fertigung dürfen nur ein Dokument mit `Status/Freigegeben`,
    passender Revision und gültiger Projektzuordnung verwenden.

## Rechteproblem melden

Fehlt ein erwartetes Dokument, zuerst Projektcode und eigene
Gruppenzuordnungen prüfen lassen. Niemals ein Dokument duplizieren oder in ein
anderes Projekt verschieben, um eine Sperre zu umgehen. Bei zu weitreichender
Sichtbarkeit Arbeit stoppen und DMS-Administration beziehungsweise
Datenschutzkontakt informieren.

Details: [Dokumente finden und verwenden](../../user-guides/dms.md),
[Qualitätsprozess](../../processes/order-to-cash/quality.md) und
[Paperless-Administration](../admin/paperless.md).

Der DMS-MCP ist nur lesend. Fragen wie „Finde den freigegebenen Prüfplan für
SCU-100“ liefern ausschließlich Dokumente, die das technische Servicekonto
sehen darf. Binärdatei, Revision und Freigabestatus werden anschließend im
Paperless-Webclient kontrolliert.

Für ähnliche Formulierungen und Fragen nach Dokumentinhalten steht in FLOWAI
zusätzlich `search_dms_documents_semantic` zur Verfügung. OCR-Textblöcke werden
lokal in PostgreSQL/pgvector indiziert; der Trefferlink führt immer zurück zum
führenden Original in Paperless. Nach neuen Testdokumenten kann der Index mit
`make dms-vector-index` aktualisiert werden.
