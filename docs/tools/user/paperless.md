# Paperless-ngx im Unternehmensprozess

Paperless-ngx ist das führende System für freigegebene Arbeitsunterlagen und
Nachweise. ERPNext speichert nur stabile Dokumentreferenzen.

## Dokumentfluss und Benutzerhandlung

| Prozessschritt | Dokument | Vorgehen in Paperless |
|---|---|---|
| Auftrag/Fertigung | Zeichnung, Montageanweisung | nach Artikel und Revision suchen, Freigabestatus prüfen |
| Wareneingang | Lieferantenzertifikat | importieren, Charge und Bestellung taggen |
| Produktion | Arbeitsanweisung | aus Work Order öffnen, eingefrorene Revision verwenden |
| Qualitätsprüfung | Prüfplan, Messprotokoll | Seriennummer und NCR referenzieren |
| Lieferung | Abnahmeprotokoll | Auftrag, Work Order und Seriennummern verknüpfen |

## Dokument importieren

1. PDF über **Dokument hochladen** oder den Consume-Ordner einliefern.
2. OCR-Ergebnis und Dokumenttyp prüfen.
3. Einen eindeutigen Titel vergeben.
4. Artikel, Revision oder Charge sowie den Prozess als Tags ergänzen.
5. Auftragsbezogene Dokumente mit `SO-4711` bzw. `WO-2027-0042`
   kennzeichnen.
6. Freigabe durchführen und die stabile Dokument-ID in ERPNext verlinken.

## Dokument vor Verwendung prüfen

Titel, Artikel, Revision, Freigabestatus, Gültigkeit und Prozessreferenz müssen
zusammenpassen. Eine neue Revision überschreibt keine alte. Laufende Aufträge
verwenden die eingefrorene Referenz, bis ein genehmigter Änderungsprozess sie
ersetzt.

Details: [Dokumente finden und verwenden](../../user-guides/dms.md),
[Qualitätsprozess](../../processes/order-to-cash/quality.md) und
[Paperless-Administration](../admin/paperless.md).
