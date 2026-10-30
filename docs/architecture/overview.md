# Architektur und Systemgrenzen

## Zielbild

```mermaid
flowchart TB
  USER[Browser / Rollen] --> IAM[Keycloak / OIDC]
  USER --> PORTAL[Management Portal]
  USER --> WIKI[MkDocs Wiki]

  PORTAL --> API[Python Integration Layer / FastAPI]
  USER --> MCP[ERP-, DMS- und Wiki-MCP]
  MCP --> ERP
  MCP --> DMS
  MCP --> WIKI
  API --> ERP[ERPNext / Frappe]
  API --> DMS[Paperless-ngx]
  API --> AI[Ollama - optional]
  API --> VDB[(PostgreSQL + pgvector)]

  ERP --> CRM[CRM / Vertrieb]
  ERP --> MRP[MRP / Einkauf / Lager]
  ERP --> MAN[Manufacturing]
  MAN --> MES[MES / Shopfloor-Erweiterung]
  DMS --> DOCS[Zeichnungen / Prüfpläne / Zertifikate]
  MES --> MACHINE[OPC-UA / MQTT - später]

  PROM[Prometheus] --> API
  GRAF[Grafana] --> PROM
```

## Verantwortlichkeiten

| Baustein | Führende Daten | Nicht verantwortlich für |
|---|---|---|
| ERPNext | Kunde, Auftrag, BOM, Bestand, Bestellung, Buchung | Binärarchiv, freie LLM-Aktionen |
| MES-Schicht | Arbeitsgang, Rückmeldung, Messwert, Maschinenstatus | Finanzbuchung, Dokumentenrevision |
| Paperless-ngx | Dokument, OCR, Tags, Archiv | Produktstruktur, Fertigungsstatus |
| Integration Layer | Verträge, Orchestrierung, freigegebene AI-Tools | Schattenstammdaten |
| Keycloak | Identität, Gruppen, OIDC | Fachberechtigung ohne Systemmapping |
| MkDocs | Freigegebene Prozess-, User- und Admin-Doku | Laufzeitdaten |

## Demo- und Vollmodus

Der **Demo-Modus** startet Portal, API, Wiki und pgvector. Alle fachlichen
Antworten stammen aus einem versionierten Szenario. Dadurch ist eine
Management-Präsentation ohne Netz und ohne Wartezeit möglich.

Das Compose-Profil **full** startet zusätzlich echte ERPNext- und
Paperless-ngx-Container. Die API-Adapter schalten auf Live-Zugriff um, sobald
API-Zugänge konfiguriert sind. Bis dahin bleibt die simulierte Darstellung
transparent als `demo` gekennzeichnet.

## Datenfluss bei einer Statusfrage

```mermaid
sequenceDiagram
  actor User
  participant Portal
  participant API as AI Gateway
  participant ERP as ERPNext Tool
  participant MES as MES Tool
  participant DMS as Paperless Tool
  User->>Portal: Wie ist Auftrag 4711?
  Portal->>API: POST /api/assistant/ask
  API->>ERP: get_sales_order(SO-4711)
  API->>MES: get_work_order(WO-2027-0042)
  API->>DMS: search_documents(SCU-100, Rev C)
  API-->>Portal: Antwort + Quellenreferenzen
```
