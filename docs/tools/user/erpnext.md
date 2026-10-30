# ERPNext im Unternehmensprozess

ERPNext ist das führende Fachsystem für Kundenauftrag, Material, Fertigung,
Lager, Lieferung, Rechnung und die dazugehörigen Buchungen.

## Vorbereitete Produkte und Demobuchungen

Das Compose-Profil `full` führt den idempotenten ERPNext-Seed beim ersten Start
aus. Manuell lässt er sich aus dem Repository-Verzeichnis erneut ausführen:

```bash
docker compose --profile full run --rm erpnext-seed
```

Der Seed legt nur Voraussetzungen und den Prozessstart an. Vorhandene Daten
werden nicht überschrieben. Erzeugt werden unter anderem:

- Firma **Open Manufacturing Demo GmbH** mit Geschäftsjahren 2026 und 2027,
- Kunde **NordMarine Systems GmbH** und zwei Lieferanten,
- vier Produkte mit freigegebenen BOMs und Arbeitsgängen:
  **SCU-100**, **IOX-24**, **HMI-070** und **GW-EDGE-200**,
- Anfangsbestände für Komponenten sowie ein Beispielzugang für `PCB-MAIN-42`,
- fünf Workstations, Qualitätsmerkmale und Prüfvorlage,
- Opportunity **OPP-2027-0018** über fünf Geräte zu je 12.500 EUR.

Zusätzlich werden idempotent gebuchte Beispiele angelegt:

- Material Receipt für 25 `PCB-MAIN-42`,
- Material Transfer der IOX-Komponenten ins WIP-Lager,
- Manufacture für 3 `IOX-24`, 2 `HMI-070` und 1 `GW-EDGE-200`,
- Material Issue für ein beschädigtes `CASE-GW-200`.

Die Belege tragen in den Bemerkungen den Marker
`[ERP-EIGENBAU-DEMO:…]`. Stücklisten stehen unter **Manufacturing > Bill of
Materials**, Bestände unter **Stock > Reports > Stock Balance** und die
Beispielbewegungen unter **Stock > Stock Entry** bzw. **Stock Ledger**.

Nach der Anmeldung unter [localhost:8081](http://localhost:8081) beginnt der
manuelle Ablauf bei **CRM > Opportunity > OPP-2027-0018**. Falls ein Workspace
in ERPNext v16 anders angeordnet ist, kann der Dokumenttyp über die globale
Suche geöffnet werden. Angebot und alle Folgebelege erhalten die vom echten
ERPNext erzeugten Nummern; die festen Referenzen wie `SO-4711` bleiben die
fachlichen Kennungen des parallelen Portal-Szenarios.

## Prozess und Bedienweg

| Phase | Rolle | Menü / Dokument | Benutzerhandlung |
|---|---|---|---|
| Anfrage | Vertrieb | **CRM > Opportunity** | Kunde, Produkt, Menge, Termin und Wahrscheinlichkeit pflegen |
| Angebot | Vertrieb | **Selling > Quotation** | Positionen und Konditionen prüfen, freigeben und senden |
| Auftrag | Auftragszentrum | **Selling > Sales Order** | Kundenreferenz und Termin prüfen, dann `Submit` |
| Materialplanung | Disposition | **Manufacturing > Production Plan** | BOM auflösen und Fehlmengen erzeugen |
| Beschaffung | Einkauf | **Buying > Purchase Order** | Lieferant und Termin wählen, Bestellung absenden |
| Wareneingang | Lager/QS | **Stock > Purchase Receipt** | Menge, Charge und Prüfstatus buchen |
| Fertigung | Planung/Produktion | **Manufacturing > Work Order / Job Card** | einplanen, starten und Ist-Daten rückmelden |
| Fertigware | Lager | **Stock Entry** | freigegebene Seriennummern einlagern |
| Lieferung | Versand | **Selling > Delivery Note** | Seriennummern und Adresse prüfen, Warenausgang buchen |
| Rechnung | Finanzen | **Accounting > Sales Invoice** | Steuer, Zahlungsziel und Referenzen prüfen, dann buchen |

## Verbindlicher Arbeitsablauf

1. Immer vom Vorgängerdokument aus weiterarbeiten, damit die Belegkette
   Opportunity → Angebot → Auftrag → Lieferung → Rechnung erhalten bleibt.
2. Vor `Submit` Pflichtfelder, Revision, Menge, Termin und Referenzen prüfen.
3. Bei einer Korrektur keinen gebuchten Beleg überschreiben; Storno- oder
   Änderungsprozess verwenden.
4. Bei Wareneingang die Paperless-Dokument-ID des Zertifikats verknüpfen.
5. Fertigungsrückmeldungen je Benutzer, Job Card und Seriennummer erfassen.
6. Eine offene Major-Abweichung sperrt Einlagerung und Lieferung.
7. Nach dem Buchen den erzeugten Bestand bzw. Hauptbuchposten kontrollieren.

## Prozessanleitungen

- [CRM, Angebot und Auftrag](../../processes/order-to-cash/crm-sales.md)
- [MRP, Einkauf und Wareneingang](../../processes/order-to-cash/procurement.md)
- [Kapazitätsplanung und Fertigung](../../processes/order-to-cash/production.md)
- [Qualität, Abweichung und DMS](../../processes/order-to-cash/quality.md)
- [Lager, Lieferung und Buchhaltung](../../processes/order-to-cash/delivery-accounting.md)

Bei fehlenden Rechten oder falschem Workflow nicht auf Datenbankebene
korrigieren. Belegnummer, erwarteten Schritt und Screenshot an den
ERPNext-Administrator melden.
