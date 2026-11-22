# Architektur und Systemgrenzen

## Zielbild

```mermaid
flowchart TB
  USER[Browser / Rollen] --> IAM[Keycloak / OIDC]
  USER --> PORTAL[Unternehmensportal / App-Launcher]
  USER --> WORK[FLOWWORK]
  USER --> QUALITY[FLOWQ Wareneingangsprüfung]
  USER --> HR[FLOWHR]
  USER --> DESK[FLOWSPACE Desksharing]
  USER --> FIN[FLOWFIN Management und Finanzen]
  USER --> WIKI[MkDocs Wiki]
  USER --> SHELL[Unternehmens-Shell / 9-Punkte-Launcher]
  SHELL --> ERP
  SHELL --> DMS
  SHELL --> WIKI
  SHELL --> REDMINE
  SHELL --> IAM
  SHELL --> AI
  SHELL --> GRAF
  SHELL --> PROM

  PORTAL --> API[Python Integration Layer / FastAPI]
  WORK --> API
  QUALITY --> API
  HR --> API
  DESK --> API
  FIN --> API
  USER --> MCP[ERP-, DMS- und Wiki-MCP]
  MCP --> ERP
  MCP --> DMS
  MCP --> WIKI
  API --> ERP[ERPNext / Frappe]
  API --> DMS[Paperless-ngx]
  API --> REDMINE[Redmine / Tickets und Wiki]
  API --> AI[Ollama - optional]
  API --> VDB[(PostgreSQL + pgvector)]
  API --> HRSTATE[(FLOWHR Fachzustand)]
  API --> DESKSTATE[(Standorte, Plätze, Buchungen)]
  API --> FINSTATE[(FLOWFIN Fachzustand)]
  API --> QSTATE[(FLOWQ Prüfungen und Messwerte)]

  ERP --> CRM[CRM / Vertrieb]
  ERP --> MRP[MRP / Einkauf / Lager]
  ERP --> MAN[Manufacturing]
  MAN --> MES[MES / Shopfloor-Erweiterung]
  MRP --> QUALITY
  QUALITY --> DEVICE[Messgeräte-Gateway]
  DMS --> DOCS[Zeichnungen / Prüfpläne / Zertifikate]
  MES --> MACHINE[OPC-UA / MQTT - später]

  PROM[Prometheus] --> API
  GRAF[Grafana] --> PROM
  ERP --> RPT[(Management Reporting)]
  FIN --> RPT
  GRAF --> RPT
```

## Verantwortlichkeiten

| Baustein | Führende Daten | Nicht verantwortlich für |
|---|---|---|
| ERPNext | Kunde, Auftrag, BOM, Bestand, Bestellung, Buchung | Binärarchiv, freie LLM-Aktionen |
| MES-Schicht | Arbeitsgang, Rückmeldung, Messwert, Maschinenstatus | Finanzbuchung, Dokumentenrevision |
| FLOWQ | Stichprobenauswahl, operative Wareneingangsprüfung, Messwert und Integrationsstatus | Bestellung, Bestandsledger, Prüfplanfreigabe und revisionssicheres Archiv |
| FLOWHR | Anwesenheit, Abwesenheiten, Bewerbungsworkflow, Payroll-Freigabe und Übergabestatus | gesetzliche Lohnberechnung, ELStAM, DEÜV, eAU und Zahlung |
| FLOWSPACE | Standorte, Arbeitsplatzmerkmale, Buchung, Check-in/-out und Audit | Gebäudezutritt, Sensorik und reale Raumverwaltung |
| FLOWFIN | Management-Views, Budget-Forecast, Auslagenfreigabe, Anlagen-Demo und Testadapter | rechtsverbindliche Finanzbuchhaltung, Steuerlogik, Bank-/DATEV-/Peppol-Übertragung |
| Redmine | Projekt, Ticket, Status, Termin, Zeitbuchung und Projekt-Wiki | versionierte Requirements-Baselines |
| FLOWWORK | Requirement, eigene Elementtypen/Felder, Beziehungen, Review, Baseline, Testplan, Risiko und Traceability-Referenz | Redmine-Ticketstatus, operative Lagerentscheidung, DMS-Binärarchiv |
| Paperless-ngx | Dokument, OCR, Tags, Archiv | Produktstruktur, Fertigungsstatus |
| Integration Layer | Verträge, Orchestrierung, freigegebene AI-Tools | Schattenstammdaten |
| Keycloak | Identität, Gruppen, Realm-Rollen und OIDC-SSO | anwendungsspezifische Fachlogik |
| MkDocs | Freigegebene Prozess-, User- und Admin-Doku | Laufzeitdaten |
| Unternehmens-Shell | App-Wechsel, Design-Tokens und Produktkontext vor allen externen Weboberflächen | Login, Fachrechte oder Änderung von Upstream-Inhalten |
| Management Reporting | freigegebene, read-only Kennzahlenmodelle und Datenalter | fachliche Belegpflege und unkontrollierter Direktzugriff auf Quellsystemtabellen |
| Agentenregister | fachlicher Owner, erlaubte Tools, Autonomiestufe, Limits, Eskalation und Evidenz | freie Selbsterweiterung von Rechten oder unkontrollierte Modellaktionen |
| Policy- und Tool-Gateway | Identität, Projektkontext, Vorschau, Bestätigung, Betragsgrenze und Audit | fachliche Entscheidung, Signatur oder Haftungsübernahme |

## Zielarchitektur für den ausnahmeorientierten Arbeitsplatz

Das 12- bis 24-Monats-Zielbild ergänzt die drei vorhandenen MCP-Server um ein
kontrolliertes Agenten-Betriebsmodell. Agenten reagieren auf freigegebene
Fachereignisse, verwenden ausschließlich registrierte Werkzeuge und liefern
Standardfälle entweder als Entwurf, bestätigte Aktion oder begrenzte
Automatisierung. Ausnahmen landen mit Quellen, Vorschlag und Wirkung in der
persönlichen Entscheidungs-Inbox.

Für den Produktivbetrieb fehlen insbesondere durchgängige Benutzerdelegation,
eine zentrale Policy Engine, Fachereignisse, Evaluation, Kosten- und
Qualitätsmetriken, unveränderbare Evidenz sowie Sandbox, Rollback und Kill
Switch. Die Stufen A2 und A3 werden nur für nachweislich stabile Prozesse
freigegeben.

## Demo- und Vollmodus

Der **Demo-Modus** startet Portal, API, Wiki und pgvector. Alle fachlichen
Antworten stammen aus einem versionierten Szenario. Dadurch ist eine
Management-Präsentation ohne Netz und ohne Wartezeit möglich.

Das Compose-Profil **full** startet zusätzlich echte ERPNext-, Paperless-ngx-
und Redmine-Container. Alle öffentlichen Webports liegen auf schlanken
Nginx-Shells, die ausschließlich HTML um gemeinsame Shell-, Theme- und
Launcher-Assets ergänzen und alle Fachanfragen an die internen Upstreams
weiterreichen. Das
Profil **work** startet Redmine auch
separat. Die API-Adapter schalten auf Live-Zugriff um, sobald
API-Zugänge konfiguriert sind. Bis dahin bleibt die simulierte Darstellung
transparent als `demo` gekennzeichnet.

Mit `make sso` wird zusätzlich der Realm `open-manufacturing` gestartet und
die Plattform auf erzwungenes OIDC umgeschaltet. Der Demo-Modus ohne OIDC
bleibt bewusst für Offline-Präsentationen verfügbar und ist nicht als
produktive Zugriffskontrolle gedacht.

## Personalprozesse und Systemübergaben

```mermaid
flowchart LR
  VAC[Stelle] --> APP[Bewerbung]
  APP --> PIPE[Vorauswahl, Gespräch, Angebot]
  APP --> RDMS[(Paperless Recruiting-Akte)]
  PIPE --> EMP[Employee / Vertrag]
  TIME[FLOWHR Anwesenheit] --> LOCK[Zeitabschluss]
  LOCK --> PREP[Payroll-Vorschau]
  PREP --> APPROVE[separate Freigabe]
  APPROVE --> PDMS[(Paperless Abrechnung)]
  APPROVE --> JE[ERPNext Journal Entry]
```

FLOWHR orchestriert Rollen, Status, Prüfungen und Übergaben. Paperless bleibt
führend für Bewerbungs- und Abrechnungsdokumente, ERPNext für den
Buchungsbeleg. Die Demo berechnet keine gesetzlichen Steuer- oder
Sozialversicherungswerte; diese Grenze und die produktiven Adapter sind unter
[Recruiting, Entgeltabrechnung, DMS und ERP](../interfaces/hr-dms-payroll.md)
dokumentiert.

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
