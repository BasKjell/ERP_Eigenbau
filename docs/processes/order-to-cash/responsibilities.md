# Rollen, Abteilungen und Stammdaten

## Zweck

Diese Seite beantwortet für jede Abteilung vier Fragen: Was ist zu tun, welche
Daten werden gepflegt, wann darf an die nächste Stelle übergeben werden und
welche Daten dürfen nicht eigenmächtig geändert werden? Die Aufteilung ist eine
übliche Zielorganisation für einen mittelständischen Fertigungsbetrieb und muss
vor Produktivstart mit der realen Organisation bestätigt werden.

## Rollenübersicht

| Abteilung / Rolle | Hauptverantwortung | Arbeitsvorrat im ERP | Übergabe an |
|---|---|---|---|
| Vertrieb | Opportunity, Angebot, Preis und Kundenkommunikation | offene Opportunities und Quotations | Auftragszentrum |
| Auftragszentrum | vollständiger, bestätigter Kundenauftrag | Sales Orders in Draft / To Deliver | Disposition |
| Disposition | Nettobedarf, Materialdeckung und Termin | Production Plans, Material Requests | Einkauf / Planung |
| Einkauf | Bestellung, Liefertermin und Lieferantenkommunikation | Material Requests, offene Purchase Orders | Lager |
| Lager | physischer Bestand, Wareneingang, Umlagerung, Kommissionierung | Purchase Receipts, Stock Entries, Pick Lists | Fertigung / Versand |
| Produktionsplanung | Work Orders, Job Cards, Arbeitsplätze und Reihenfolge | geplante/gestartete Work Orders | Fertigung |
| Fertigung | Arbeitsausführung, Zeiten, Mengen, Seriennummer und Verbrauch | zugewiesene Job Cards | Qualität / Lager |
| Qualität | Prüfung, Sperre, Abweichung und Freigabe | Quality Inspections, NCRs, DMS-Nachweise | Lager / Versand |
| Versand | Packen, Lieferschein und Warenausgang | freigegebene Sales Orders / Delivery Notes | Finanzen |
| Finanzen | Rechnung, Zahlung, Kontierung und Abschluss | unberechnete Lieferungen, offene Posten | Prozessverantwortung |
| HR / Führungskräfte | Mitarbeiter, Anwesenheit, Zeitkonten, Abwesenheiten und Genehmigungen | FLOWHR-Anträge und Teamkalender | Payroll / Controlling |

## Vertrieb und Auftragszentrum

**Tägliche Arbeit**

1. Opportunity auf Kunde, Ansprechpartner, Artikel/Revision, Menge, Zieltermin,
   Wahrscheinlichkeit und nächsten Schritt prüfen.
2. Angebot aus der Opportunity erzeugen und Preise, Rabatte, Steuern,
   Lieferbedingungen und Gültigkeit pflegen.
3. Bei Annahme eine Sales Order aus dem Angebot erzeugen; Kundenbestellnummer,
   Liefer-/Rechnungsadresse und bestätigten Termin eintragen.
4. Erst nach kaufmännischer und technischer Plausibilisierung `Submit` wählen.
5. Disposition über Sondertermine, kundenspezifische Konfigurationen und
   beizustellende Teile informieren.

**Übergabe vollständig, wenn:** Kundenauftrag submitted, Positionen und
Revision eindeutig, Liefertermin bestätigt, Preisfreigaben dokumentiert und
relevante Kundendokumente verlinkt sind.

Bei kommissionsbezogenen Aufträgen ist zusätzlich das Feld **Project** ab der
Sales Order zu setzen und auf allen Folgebelegen zu kontrollieren.

**Nicht eigenmächtig ändern:** Artikelstruktur, BOM, Lagerbestand,
Herstellkosten und Qualitätsfreigaben.

→ [Bildschirm-für-Bildschirm: CRM, Angebot und Auftrag](crm-sales.md)

## Disposition und Produktionsplanung

**Tägliche Arbeit**

1. neue Sales Orders in den Production Plan übernehmen.
2. BOM auflösen und Bedarf gegen freien Bestand, Reservierungen, offene
   Bestellungen und Wiederbeschaffungszeiten prüfen.
3. Material Requests für echte Fehlmengen erzeugen; Überbestände und
   Mehrfachanforderungen vermeiden.
4. Fertigungsstart und Liefertermin anhand Material und Kapazität abstimmen.
5. Work Order mit korrekter BOM, Menge, WIP-/Fertigwarenlager und Terminen
   erzeugen; Job Cards auf Arbeitsplätze terminieren.

**Übergabe vollständig, wenn:** Fehlmengen bestellt/terminiert, Materialstatus
transparent, Work Order freigegeben, Arbeitsunterlagen gültig und Job Cards
zugeordnet sind.

**Nicht eigenmächtig ändern:** Einkaufspreise, Lieferantenfreigabe,
Qualitätsstatus und rückgemeldete Ist-Zeiten.

→ [MRP und Beschaffung](procurement.md) · [Planung und Fertigung](production.md)
· [Ressourcen und Zeitverschreibung](resources-time.md)

## Einkauf

**Tägliche Arbeit**

1. Material Request prüfen: Artikel, Menge, Bedarfstermin, Projekt/Auftrag und
   vorgeschlagener Lieferant.
2. Bezugsquelle, Preis, Währung, Incoterm, Mindestmenge und Liefertermin
   vergleichen.
3. Purchase Order aus dem Material Request erzeugen und `Submit` buchen.
4. Auftragsbestätigung und bestätigten Termin im ERP nachpflegen.
5. Verspätungen an Disposition melden und Eskalation dokumentieren.

**Übergabe vollständig, wenn:** Bestellung submitted, bestätigter Termin
vorhanden und Wareneingang Bestellung/Position eindeutig referenzieren kann.

**Nicht eigenmächtig ändern:** Wareneingangsmenge, Prüfstatus, Lagerort und
Lieferantenbewertung der Qualität.

→ [Einkauf und Wareneingang](procurement.md)

## Lager und Intralogistik

**Tägliche Arbeit**

1. Anlieferung gegen Purchase Order identifizieren.
2. Menge, Einheit, Artikel, Charge und bei seriennummerngeführten Kaufteilen
   jede Lieferanten-Seriennummer scannen.
3. Purchase Receipt in freies Lager oder – bei fehlender/negativer Prüfung –
   in das Sperrlager buchen.
4. Material für freigegebene Work Orders per **Material Transfer for
   Manufacture** von `Stores` nach `Work In Progress` bereitstellen.
5. Nach Endfreigabe Manufacture/Fertigmeldung prüfen und Fertigware physisch
   einlagern.
6. Für Versand Pick List/Delivery Note kommissionieren und Seriennummern mit
   Gerät und Prüfstatus abgleichen.

**Übergabe vollständig, wenn:** physischer und gebuchter Bestand übereinstimmen,
Lagerplatz/Charge/Seriennummer erfasst und der Beleg submitted ist.

**Nicht eigenmächtig ändern:** Bedarf, Bestellpreis, BOM, Prüfergebnis oder
Seriennummernzuordnung nach erfolgter Buchung.

→ [Wareneingang](procurement.md) · [Materialbereitstellung](production.md) ·
[Einlagerung und Lieferung](delivery-accounting.md)

## Fertigung

**Tägliche Arbeit**

1. persönliche Job Card öffnen und Artikel, Menge, Revision, Workstation und
   verlinkte Arbeitsanweisung prüfen.
2. Arbeitsgang starten; Beginn/Ende, Gutmenge, Ausschuss und Störgrund zeitnah
   rückmelden.
3. Materialabweichungen nicht durch Ersatzartikel umgehen, sondern stoppen und
   eskalieren.
4. Geräte-Seriennummer spätestens in der Endmontage scannen/erzeugen und über
   alle Folgeprüfungen beibehalten.
5. Materialverbrauch und Fertigmenge gegen die Work Order buchen bzw. an das
   Lager zur kontrollierten Buchung übergeben.

**Übergabe vollständig, wenn:** alle Job Cards abgeschlossen, Mengen
plausibel, Materialverbrauch nachvollziehbar, Seriennummern am Gerät vorhanden
und offene Abweichungen gekennzeichnet sind.

**Nicht eigenmächtig ändern:** BOM, freigegebene Revision, Soll-Prüfgrenzen,
Lagerbestand oder Qualitätsfreigabe.

→ [Planung und Fertigung](production.md) ·
[Ressourcen und Zeitverschreibung](resources-time.md) ·
[Shopfloor](../../user-guides/shopfloor.md)

## Qualität

**Tägliche Arbeit**

1. Wareneingangs- und Fertigungsprüfungen nach freigegebenem Prüfplan ausführen.
2. Messwerte, Prüfer, Zeitpunkt, Seriennummer und Dokumentrevision erfassen.
3. Abweichungen klassifizieren; betroffene Charge/Seriennummer sperren.
4. Nacharbeit genehmigen, Wiederholprüfung durchführen und erst danach
   freigeben.
5. Zertifikate und Prüfprotokolle in Paperless ablegen und stabile Dokument-ID
   im ERP referenzieren.

**Übergabe vollständig, wenn:** jede Seriennummer eindeutigen Prüfstatus hat,
keine offene Major-Abweichung besteht und der Nachweis auffindbar ist.

**Nicht delegierbar:** finale Qualitätsfreigabe und Aufhebung einer
Qualitätssperre.

→ [Qualität, Abweichung und DMS](quality.md)

## Versand

**Tägliche Arbeit**

1. nur freigegebene, im Fertigwarenlager vorhandene Geräte kommissionieren.
2. Delivery Note aus Sales Order erzeugen; Lieferadresse, Termin, Versandart,
   Incoterm und Packstücke prüfen.
3. exakt die physisch verpackten Seriennummern auswählen/scannen.
4. Lieferschein `Submit` buchen und geforderte Dokumente beilegen.
5. Tracking-/Speditionsreferenz dokumentieren und Finanzen über die Lieferung
   informieren.

**Übergabe vollständig, wenn:** Warenausgang submitted, Seriennummern und
Packstücke stimmen und Liefernachweis vorhanden ist.

→ [Lieferung](delivery-accounting.md)

## Finanzen

**Tägliche Arbeit**

1. Sales Invoice aus der Delivery Note erzeugen.
2. Leistungsdatum, Menge, Preis, Steuer, Erlöskonto, Zahlungsziel und
   Kundenreferenz prüfen.
3. Rechnung `Submit` buchen und gesetzlich vorgesehenes Ausgabeformat prüfen.
4. Zahlungseingang per Payment Entry zuordnen; Differenzen und überfällige
   Posten bearbeiten.
5. Auftrag erst nach vollständiger Fakturierung und geklärtem Saldo
   kaufmännisch schließen.

**Nicht eigenmächtig ändern:** gelieferte Menge, Seriennummern,
Qualitätsstatus oder submitted Logistikbelege.

→ [Rechnung und Zahlung](delivery-accounting.md)

## Stammdatenverantwortung

| Stammdatum | Data Owner | Pflegt im ERP | fachliche Mitwirkung | Mindestkontrolle |
|---|---|---|---|---|
| Kunde, Kundengruppe, Gebiet, Adressen, Kontakte | Vertriebsleitung | Sales Operations | Finanzen | Dublette, USt-ID, Zahlungsbedingung, Adresse |
| Lieferant, Lieferantengruppe, Bezugsquelle | Einkaufsleitung | Einkauf | Qualität, Finanzen | Freigabestatus, Steuerdaten, Währung, Bank-/Zahlungsdaten |
| Artikelgrunddaten und Einheit | Stammdatenkoordination | Stammdatenteam | Einkauf, Produktion, Lager | eindeutiger Code, UOM, Lager-/Kauf-/Verkaufskennzeichen |
| Serien-/Chargenpflicht | Qualitätsleitung | Stammdatenteam | Lager, Produktion | Kennzeichen vor erster Bestandsbuchung |
| BOM und Revision | Engineering | Arbeitsvorbereitung | Qualität, Einkauf | freigegebene Komponenten, Mengen, Gültigkeit |
| Arbeitsgänge und Arbeitsplätze | Produktionsleitung | Arbeitsvorbereitung | Instandhaltung | Kapazität, Kalender, Kostensatz, Standardzeit |
| Lager und Lagerhierarchie | Logistikleitung | ERP-Administration | Finanzen | Firma, Typ, Buchungskonto, Sperrlogik |
| Projekt/Kommission | Auftragszentrum/Projektleitung | Auftragszentrum | Einkauf, Planung, Controlling | eindeutige KOM-Nummer, Kunde, Zeitraum, Status, Abschluss |
| Prüfplan und Grenzwerte | Qualitätsleitung | Qualität | Engineering | Revision, Freigabe, Messmittel |
| Preislisten und Konditionen | Vertriebs-/Einkaufsleitung | jeweilige Sachbearbeitung | Finanzen | Währung, Gültigkeit, Freigabegrenze |
| Konten, Steuern, Zahlungsbedingungen | Finanzleitung | Finanzen | Steuerberatung | Buchungskreis, Gültigkeit, Vier-Augen-Prinzip |
| Mitarbeiter, Abteilung, Stelle | HR-Leitung | HR | Vorgesetzte, IT | Eintritt, Status, Organisation, Datenschutz |
| Arbeitszeitmodell, Urlaub und Zeitkonto | HR-Leitung | HR / FLOWHR | Führungskräfte, Betriebsrat, Payroll | Gültigkeit, Sollzeit, Saldo, Vier-Augen-Korrektur |
| Benutzer und Rollen | IT/ERP-Administration | Administrator | Data Owner | Minimalrechte, Funktionstrennung, Rezertifizierung |
| Dokumenttypen, Tags und Aufbewahrung | Dokumentenlenkung | DMS-Administration | Qualität, Fachbereiche | Revision, Status, Aufbewahrung, Zugriff |

Der aktuelle Demoumfang und die vor Produktivbetrieb noch offenen
Stammdatenfelder sind im
[Stammdatenkatalog und der Lückenanalyse](../../demo/master-data-catalog.md)
zusammengefasst.

Die konkrete Kommissions- und Lagerlogik beschreibt
[Projekte, Kommissionen und Lagerbereiche](projects-warehouses.md).

!!! danger "Stammdatenänderung mit Bewegungsdaten"
    Serien-/Chargenpflicht, Basiseinheit, Firmenzuordnung, Lagerstruktur und
    Kontierung dürfen nach der ersten Buchung nicht ohne freigegebenen
    Änderungs- und Migrationsplan geändert werden.

## Funktionstrennung und Vertretung

- Ersteller und finale Freigabe sollen bei Preisabweichungen, Major-NCRs,
  manuellen Bestandskorrekturen und Rechnungsstornos getrennte Personen sein.
- Vertretungen verwenden ein eigenes Konto und dieselbe Rolle; Konten werden
  nicht geteilt.
- Jede Abteilung benennt einen Data Owner und einen operativen Data Steward.
- Rechte und Vertreter werden mindestens jährlich sowie bei Rollenwechsel
  geprüft.
