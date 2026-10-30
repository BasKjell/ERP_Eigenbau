# Management-Demo in 15 Minuten

## Vorbereitung

```bash
cp .env.example .env
make demo
```

Öffne das [Management-Portal](http://localhost:8088) und dieses
[Prozess-Wiki](http://localhost:8001) in getrennten Tabs. Setze die Demo vor
jedem Termin über **Demo zurücksetzen** auf den Anfang.

Soll zusätzlich der echte ERPNext-Ablauf gezeigt werden, vorher ausführen:

```bash
docker compose --profile full up -d
docker compose --profile full run --rm erpnext-seed
```

Anschließend [ERPNext](http://localhost:8081) öffnen und bei
`OPP-2027-0018` beginnen. Die Portal-Demo und die manuell erzeugten
ERPNext-Belege besitzen getrennte Zustände.

## Dramaturgie

### Minute 0-2: Das Zielbild

**Botschaft:** Nicht fünf neue Silos, sondern eine offene, API-basierte
Plattform mit einem durchgängigen Prozess.

Zeige Auftrag SO-4711, Produkt, Menge, Wert und Liefertermin. Weise darauf hin,
dass Portal und Dokumentation lokal laufen und der Eigenbau-Code Python ist.

### Minute 2-5: Vom Kunden zum Materialbedarf

1. Führe CRM, Angebot, Kundenauftrag und MRP schrittweise aus.
2. Öffne **Material & MRP**.
3. Zeige, dass die BOM automatisch fünf fehlende Mainboards erkennt.
4. Führe Einkauf und Wareneingang aus.

**Botschaft:** Vertrieb, Disposition und Einkauf arbeiten auf denselben
Auftrags- und Produktdaten.

### Minute 5-8: Kapazität und Shopfloor

1. Öffne **Kapazitätsplanung**.
2. Zeige Prüfstand A als Engpass mit 91 Prozent.
3. Springe im Prozess auf **MES**.
4. Verweise auf WO-2027-0042, Arbeitsgänge und Seriennummern.

**Botschaft:** ERPNext deckt die PoC-Planung bereits ab; ein eigenes Python-APS
kann später komplexere Optimierung ergänzen.

### Minute 8-11: Dokumente und realistischer Fehler

1. Öffne **Dokumente** und eine PDF-Arbeitsunterlage.
2. Wechsle zu **Live-Übersicht**.
3. Starte den Fehlerfall SN-10004.
4. Zeige Lieferterminrisiko, Sperre und NCR-Referenz.
5. Schließe die Nacharbeit ab.

**Botschaft:** Dokumente sind kontextbezogen auffindbar; der Prozess beherrscht
nicht nur den Happy Path.

### Minute 11-13: Lieferung und Buchhaltung

Führe die verbleibenden Schritte bis zur Rechnung aus. Erläutere, dass Lager,
Lieferung, Seriennummer und Finanzbuchung rückverfolgbar verbunden sind.

### Minute 13-15: AI und aktuelle Dokumentation

1. Öffne **AI Copilot**.
2. Frage: „Wie ist der Status von Auftrag 4711?“
3. Zeige die Quellenchips ERPNext, MES und Paperless.
4. Öffne dieses Wiki und die Definition of Done.

**Schlussbotschaft:** Die Plattform senkt nicht nur Lizenzabhängigkeit. Sie
schafft Datenkontrolle, Integrationsfähigkeit und eine belastbare Basis für
Automatisierung und lokale KI.

## Erwartbare Managementfragen

| Frage | Kurze Antwort |
|---|---|
| Ist das produktionsreif? | Nein, es ist ein entscheidungsfähiger PoC. Die fachlichen Lücken stehen transparent im Wiki. |
| Müssen wir alles selbst bauen? | Nein. Standardprozesse kommen aus ERPNext/Paperless; Eigenbau konzentriert sich auf Differenzierung und Integration. |
| Kann es deutsche Buchhaltung? | Basis ja; GoBD, DATEV und E-Rechnung werden als formaler Fit-Gap geprüft. |
| Kann es unsere Planung? | Der PoC zeigt finite Workstation-Planung. Komplexes APS wird mit echten Constraints evaluiert. |
| Wie verhindert ihr AI-Fehlaktionen? | Kein DB-Zugriff, nur freigegebene Tools, Quellen, Rollenprüfung und Bestätigung für Schreibvorgänge. |
