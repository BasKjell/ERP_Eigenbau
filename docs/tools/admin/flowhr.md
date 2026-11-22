# FLOWHR administrieren

FLOWHR läuft als Modul des FastAPI-Integrationsdienstes auf Port `8088`. Sein
versionierter Ausgangszustand liegt im Abschnitt `hr` von
`services/platform_api/seed/scenario.json`; der veränderliche Demozustand wird
über denselben Store wie Portal und MES persistiert.

## Konfigurationsobjekte

| Objekt | Inhalt | fachlicher Owner |
|---|---|---|
| Employee | ID, Name, Organisation, Funktion, Standort, Manager | HR |
| Schedule | Sollminuten je Wochentag | HR / Betriebsrat |
| Work rules | Wochenzeit, Pause, Tagesmaximum, Kernzeit | HR / Arbeitsrecht |
| Leave balance | Jahresanspruch und verbrauchte Tage | HR |
| Overtime opening | freigegebener Eröffnungssaldo | HR / Payroll |
| Holiday | Datum und Bezeichnung | HR |
| Attendance | IN/OUT, Zeitpunkt, Quelle, Terminal, ERP-Status | System / Beschäftigte |
| Request | Typ, Zeitraum, Umfang, Grund, Genehmiger, Entscheidung | Beschäftigte / Führungskraft |
| Vacancy / Application | Stelle, Bewerberreferenz, Phase, Verlauf, Prüffrist | Recruiting |
| Candidate document | DMS-Task/-Dokument, Dokumentart, ACL, Verknüpfung | Recruiting / DMS |
| Payroll profile | Personalnummer, maskierte Bankdaten, Prüfstatus, versionierte Demo-Lohnarten | Payroll |
| Payroll period / run | Zeitabschluss, Vorschau-Token, getrennte Freigabe, DMS-/ERP-Referenzen | Payroll / Finance |

Änderungen an Regeln oder Eröffnungssalden dürfen nicht rückwirkend ohne
fachlichen Migrations- und Freigabeplan erfolgen.

## Rollen im Zielbetrieb

| Rolle | Rechte |
|---|---|
| `hr-employee` | eigene Zeit, eigener Kalender, eigene Anträge |
| `hr-manager` | zusätzlich Teamstatus, Teamkalender, Anträge direkter Mitarbeitender entscheiden |
| `hr-specialist` | Personalstamm, Regeln, Feiertage und fachliche Korrekturen |
| `recruiter` | Stellen, Bewerbungen, Phasen und geschützte Bewerberakte |
| `payroll-preparer` | Stammdatenprüfung und Abrechnungsvorschau |
| `payroll-approver` | getrennte Freigabe, DMS-Archivierung und ERP-Buchungsübergabe |
| `hr-auditor` | unveränderliche Leseansicht von Buchungen und Entscheidungen |
| `hr-admin` | technische Konfiguration, aber keine fachliche Selbstfreigabe |

Die Demo implementiert die Geschäftsregeln und Teamprüfung, noch nicht die
produktive Authentifizierung. Vor Go-live ist die Person aus einem geprüften
OIDC-Token abzuleiten; `employee_id` aus Browserparametern darf dann nicht als
Identität akzeptiert werden.

## Datenschutz und Betrieb

- Krankheitsdaten sind besonders schutzwürdig. Teamansichten zeigen nur
  `Abwesend`; Diagnose oder Freitext gehören nicht in den Kalender.
- Aufbewahrungs- und Löschfristen für Zeitbuchungen, Anträge und Audit sind mit
  Datenschutz, HR und Betriebsrat festzulegen.
- Terminals benötigen Geräteidentität, Manipulationsschutz und eine
  Offline-/Nachlieferstrategie.
- Korrekturen erfolgen über Antrag und Freigabe, nicht durch stilles Ändern
  vorhandener Ereignisse.
- Backup und Restore müssen HR-Store, Audit und ERP-Referenzen konsistent
  wiederherstellen.
- Bewerber- und Payroll-Dokumente besitzen getrennte Paperless-Objekt-ACLs;
  allgemeine DMS-Leser dürfen sie nicht sehen.
- Abrechnungs-PDF und Buchungslauf müssen gemeinsam wiederholbar sein. Die
  gespeicherte DMS-Task- bzw. ERP-Referenz verhindert eine erneute Übergabe.

## Abgrenzung zu Sage HR

Enthalten sind präsentier- und testbare Zeitwirtschaft, Recruiting-Pipeline,
geschützte Bewerberakte und ein kontrollierter Demo-Abrechnungslauf. Die
Abrechnung verwendet bewusst feste Testwerte und beweist keine gesetzliche
Rechenrichtigkeit.

Vor einem produktiven Ersatz eines HR-/Payroll-Systems fehlen insbesondere:

- zertifizierter Lohn- und Gehaltsrechenkern, Tarife, Rückrechnungen und
  Arbeitgeberanteile,
- eAU, Krankenkassen-, DEÜV- und weitere Sozialversicherungsmeldungen,
- ELStAM, Lohnsteuerbescheinigung, Bescheinigungen und Zahlungsdateien,
- Vertrags-/Onboarding-Workflow, Reisekosten und vollständige digitale
  Personalakte,
- tarifliche Zuschläge, komplexe Schichtmodelle und Betriebsvereinbarungen.

Diese Funktionen benötigen einen freigegebenen Payroll-/HR-Provider. Der
technische Vertrag einschließlich DMS- und ERP-Übergabe steht unter
[Recruiting, Payroll, DMS und ERP](../../interfaces/hr-dms-payroll.md).

## Prüfung

```bash
make test
make test-integration
```

Die Komponententests decken Regeln, Datenschutz, Bewerbungsphasen, geschützte
DMS-ACLs, Stammdatenvollständigkeit, Vier-Augen-Freigabe, PDF-Erzeugung,
ausgeglichenen Buchungsbeleg, Wiederholung und ERP-Export ab. Der Systemtest
prüft FLOWHR über die echte Containergrenze gemeinsam mit ERP-, DMS-, MES-,
MCP- und Wiki-Adaptern.
