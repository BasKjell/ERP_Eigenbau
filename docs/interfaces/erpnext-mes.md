# Schnittstelle ERPNext zu MES

## Ziel

Der Vertrag überträgt freigegebene Work Orders in eine Shopfloor-/MES-Schicht
und meldet Arbeitsfortschritt kontrolliert an ERPNext zurück. ERPNext bleibt
führend für BOM, Routing, Bestand und Kosten.

## Aktueller Implementierungsstand

Der lokale FLOWMES-Arbeitsplatz ist unter `/mes` lauffähig. Seine Demo-API
speichert Bedienhandlungen im rücksetzbaren Szenario und erzwingt
Vorgängerlogik, Bedienerzuordnung, Zeitabschluss, Pflichtchecklisten,
Gutmenge und eindeutige Seriennummern.

| Methode | Endpunkt | Zweck |
|---|---|---|
| `GET` | `/api/mes/dashboard?operator_id=…` | Schicht, Kennzahlen und persönlicher Arbeitsvorrat |
| `GET` | `/api/mes/jobs/{job_card}` | Arbeitsgang, Route, Material, Anleitung und Zeiten |
| `POST` | `/api/mes/jobs/{job_card}/start` | Arbeitsgang und Terminalzeit starten |
| `POST` | `/api/mes/jobs/{job_card}/pause` | offene Zeit schließen und Pausengrund buchen |
| `POST` | `/api/mes/jobs/{job_card}/time` | begründete manuelle Zeitkorrektur |
| `POST` | `/api/mes/jobs/{job_card}/complete` | Menge, Ausschuss, Seriennummern und Checkliste rückmelden |
| `POST` | `/api/mes/jobs/{job_card}/issue` | Störung anlegen und Arbeitsgang sperren |
| `POST` | `/api/mes/jobs/{job_card}/issue/resolve` | Nacharbeit dokumentieren und wieder freigeben |
| `GET` | `/api/mes/jobs/{job_card}/documents` | gültige DMS-Dokumente und Paperless-Status |
| `POST` | `/api/mes/reset` | nur den MES-Demozustand reproduzierbar zurücksetzen |

Die OpenAPI-Beschreibung ist unter `/docs` abrufbar. Der produktive Adapter
ersetzt später die Szenariospeicherung, ohne die Bedienoberfläche oder die
fachlichen Zustandsübergänge zu ändern.

## Work Order freigeben

Der folgende Endpunkt ist der **Zielvertrag des produktiven ERPNext-Adapters**;
er ist von der oben aufgeführten, bereits lauffähigen Demo-API zu
unterscheiden.

`POST /api/mes/work-orders`

```json
{
  "event_id": "evt-erp-wo-2027-0042-v1",
  "work_order": "WO-2027-0042",
  "sales_order": "SO-4711",
  "item_code": "SCU-100",
  "revision": "C",
  "quantity": 5,
  "bom": "BOM-SCU-100-C",
  "planned_start": "2027-01-08T06:00:00+01:00",
  "required_documents": ["DOC-DRW-100", "DOC-WI-100", "DOC-QP-100"]
}
```

Erwartete Antwort: `202 Accepted` mit derselben Work-Order-Referenz. Ein
wiederholtes Event mit identischer `event_id` darf keine zweite Work Order
erzeugen.

## Rückmeldung

`POST /api/erpnext/job-cards/{job_card}/completion`

Pflichtfelder: Benutzer/Servicekonto, Start, Ende, Gutmenge, Ausschuss,
Seriennummern und Quellereignis. Schreibzugriffe werden auditiert und bei
fachlichem Konflikt mit `409 Conflict` abgewiesen.

Die FLOWMES-Demo bildet diese Rückmeldung bereits fachlich ab. Im
Produktivadapter wird eine erfolgreiche MES-Rückmeldung idempotent auf die
ERPNext Job Card und die zugehörigen Stock-/Qualitätsbelege übertragen.

## Dokumentensystem

Eine Job Card enthält ausschließlich Dokument-IDs und den für den Arbeitsgang
gültigen Revisionsstand. `GET /api/mes/jobs/{job_card}/documents` löst diese
Referenzen auf und liefert lokale Vorschau-URLs. Bei konfiguriertem
Paperless-Token ergänzt der Adapter eine Live-Suche nach dem Artikel.

FLOWMES ändert keine Dokumentrevision. Freigabe, Archivierung und Versionen
bleiben Verantwortung des DMS; laufende Arbeitsgänge behalten ihre
eingefrorenen Dokumentreferenzen.

## Statuszuordnung

| ERPNext | MES | Portal |
|---|---|---|
| Draft | planned | pending |
| Submitted | released | active |
| In Process | running | active |
| Stopped | blocked | blocked |
| Completed | completed | done |

## Fehlerbehandlung

- `400`: Payload ungültig - kein Retry ohne Korrektur.
- `401/403`: Identität oder Rolle ungültig - Alarm an Plattformbetrieb.
- `409`: Fachlicher Konflikt - manuelle Klärung.
- `429/5xx`: exponentieller Retry mit maximaler Dauer und Dead-Letter-Queue.
