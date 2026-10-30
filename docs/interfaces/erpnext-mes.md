# Schnittstelle ERPNext zu MES

## Ziel

Der Vertrag überträgt freigegebene Work Orders in eine Shopfloor-/MES-Schicht
und meldet Arbeitsfortschritt kontrolliert an ERPNext zurück. ERPNext bleibt
führend für BOM, Routing, Bestand und Kosten.

## Work Order freigeben

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
