# Live-Readiness, Tests und Release-Gates

Das produktive Zielbild mit AD-Föderation, MFA, Token-Delegation,
Objektberechtigungen und Abnahmekriterien regelt
[SEC-IAM-001: IAM-Sicherheitskonzept](../architecture/iam-security-concept.md).
Es ist ein Konzeptentwurf; die produktive Umsetzung ist gesondert nachzuweisen.

## Ergebnis vorweg

Der Stack besitzt jetzt automatisierte Unit-, Komponenten- und
systemübergreifende Integrationstests. Das macht Änderungen belastbarer, ersetzt
aber keine produktive Härtung. Der aktuelle Stand bleibt ein PoC, bis die
blockierenden Punkte aus der Go-live-Liste umgesetzt und fachlich abgenommen
sind.

## Betriebsendpunkte

| Endpunkt | Zweck | Darf externe Systeme prüfen? | Verwendung |
|---|---|---:|---|
| `/health` | Prozess lebt und HTTP antwortet | nein | Liveness/Container-Neustart |
| `/ready` | Statusdatei, referenzierte PDFs und optional ERP/DMS/Redmine sind nutzbar | ja | Readiness, Deployment-Freigabe |
| `/metrics` | Prometheus-Metriken | nein | Monitoring und Alarmierung |

Für einen integrierten Betrieb wird gesetzt:

```dotenv
READINESS_REQUIRE_INTEGRATIONS=true
```

Dann liefert `/ready` HTTP 503, solange ERPNext, Paperless oder Redmine nicht mit
Credentials konfiguriert und erreichbar sind. In der lokalen Demo bleiben diese
beiden Prüfungen informativ, damit ERP- und DMS-Ausfälle das Portal nicht
grundlos als unbenutzbar markieren.

## Automatische Teststufen

| Stufe | Umfang | Ausführung | Merge-Gate |
|---|---|---|---:|
| Lint | Python-Code und Tests mit Ruff | Pull Request, Merge Queue, Hauptbranch | ja |
| Unit/Komponente | Store, FLOWWORK-Requirements/Versionen/Baselines, Redmine-Client, MES-/HR-Regeln, Desksharing, FLOWFIN-Budgets/Auslagen/Anlagen/Testadapter, OIDC/PKCE/Rollen, Recruiting, Payroll, PDF, Stammdaten, API und MCP-Verträge | Pull Request, Merge Queue, Hauptbranch | ja |
| Coverage | Branch-Coverage über `app` mit mindestens 75 % | zusammen mit Unit-Tests | ja |
| Dokumentation | MkDocs `--strict`, einschließlich Links und Navigation | Pull Request, Merge Queue, Hauptbranch | ja |
| DMS-/Dashboard-Artefakte | Governance- und Grafana-JSON syntaktisch gültig | Pull Request, Merge Queue, Hauptbranch | ja |
| IAM-Seed-Drift | Keycloak-Realm, 50 Identitäten und 100 Plätze stimmen mit dem Generator überein | Pull Request, Merge Queue, Hauptbranch | ja |
| DMS-Reportingvertrag | echte PostgreSQL-View, Statuslogik und negativer Tabellenzugriff | Pull Request, Merge Queue, Hauptbranch | ja |
| Management-Reportingvertrag | KPI-Views, Forecast-Summen und negativer Zugriff auf nicht freigegebene Tabellen | Pull Request, Merge Queue, Hauptbranch | ja |
| Deployment-Vertrag | vollständige Compose-Konfiguration einschließlich CI-Overlay | Pull Request, Merge Queue, Hauptbranch | ja |
| Container | reproduzierbarer Build des Test-/Produktionsunterbaus | Pull Request, Merge Queue, Hauptbranch | ja |
| Systemintegration | echte Containergrenzen: FLOWWORK ↔ Redmine-Stub, FLOWHR-Zeit/Payroll ↔ ERP-Stub, Recruiting/Payroll ↔ DMS-Stub, Desksharing, FLOWFIN/Testadapter, Inline-PDFs, MES, MCP und Wiki | Pull Request, Merge Queue, Hauptbranch | ja |
| Live-Link-Audit | 23 zentrale Oberflächen und tiefe Ziele der Management-Demo antworten ohne 4xx/5xx | nach Start des vollständigen lokalen oder Staging-Stacks | manuelle Abnahme |

Die Stubs bilden Netzwerk, URLs, ERP-/DMS-/Redmine-Token-Header und Antwortverträge
deterministisch ab. Der Test ruft die ERP-, DMS- und Wiki-Werkzeuge über das
echte Streamable-HTTP-MCP-Protokoll auf. Er ersetzt nicht den Abnahmetest gegen
die produktiv verwendeten Versionen von ERPNext, Paperless und Redmine. Dieser reale
End-to-End-Test gehört in eine getrennte Staging-Umgebung mit anonymisierten
Daten.

## Wann die Pipeline läuft

Die Quality-Pipeline wird ausgelöst:

1. bei jeder Erstellung und jeder Aktualisierung eines Pull Requests,
2. für eine GitHub Merge Queue über `merge_group`,
3. nach jedem Push auf `main` oder `master` – damit also auch nach jedem Merge,
4. manuell über `workflow_dispatch`.

Ein Lauf bei **jedem lokalen Commit** ist nicht erforderlich und kann ohne Push
auch nicht durch GitHub Actions erfolgen. Sinnvoll ist:

- während der Entwicklung gezielte Unit-Tests,
- vor dem Push mindestens `make test`,
- vor einem Release oder bei Schnittstellenänderungen `make check`,
- der vollständige verpflichtende Lauf auf jedem Pull-Request-Stand.

Im Repository-Hosting müssen die fünf Jobs der Workflow-Datei als **Required
Status Checks** für den geschützten Hauptbranch aktiviert werden. Direkte Pushes
auf den Hauptbranch sollten gesperrt und mindestens ein Review verlangt werden.

## Lokal ausführen

```bash
make test              # Unit-/Komponententests, Lint und Coverage-Gate im Image
make validate          # Compose-Vertrag und Dokumentation
make test-dms-reporting # Termin-View und eingeschränkten Grafana-DB-Zugriff prüfen
make test-management-reporting # Management-Views und getrennten DB-Zugriff prüfen
make test-integration  # isolierter Containerverbund, anschließend automatischer Abbau
make audit-links       # alle zentralen Live- und Rundgangslinks ohne Redirect-Folgen
make check             # alle drei Stufen
```

`make audit-links` erkennt nicht nur tote Links, sondern auch 502/503-Fehler
zwischen vorgeschaltetem Webserver und Anwendung. Danach wird der komplette
25-Schritte-Rundgang einmal mit `demo01` im Browser durchgeführt, weil nur so
SSO, Rollen, JavaScript-Inhalte und die tatsächliche Zielseite gemeinsam
geprüft werden.

Bei einem fehlgeschlagenen Integrationstest gibt das Skript vor dem Abbau den
Containerstatus und die letzten Logs aus. Die Testvolumes werden danach
entfernt; produktive oder lokale Demo-Volumes sind nicht Teil des CI-Projekts.

## Go-live-Gates

### Technisch blockierend

- [x] Plattform-API, FLOWWORK, MES, HR, Desksharing und Dokumentabruf können mit
  `AUTH_MODE=oidc` OIDC-Anmeldung und serverseitige Realm-Rollen erzwingen.
- [ ] MCP sowie die produktspezifischen Adapter von ERPNext, Paperless, Redmine,
  Open WebUI und Wiki erzwingen in Staging dieselbe Identität und Rollenmatrix.
- [ ] TLS-Termination, sichere Cookies, erlaubte Origins und Netzwerksegmentierung
  sind in der Zielumgebung eingerichtet.
- [ ] Demo-Passwörter sind durch externe Secrets ersetzt, rotiert und nicht in
  Logs oder Backups sichtbar.
- [ ] Persistente Daten liegen nicht nur in lokalen Docker-Volumes; Backup,
  Restore und Recovery-Zeit wurden praktisch getestet.
- [ ] Datenbankschema und API-Verträge haben versionierte Vorwärts-/Rollback-
  Migrationen.
- [ ] Monitoring besitzt Alarmregeln für Readiness, Fehlerrate, Latenz,
  Plattenplatz, Queue-Rückstand und fehlgeschlagene Backups.
- [ ] Staging testet die konkret freigegebenen ERPNext-, Paperless-, Keycloak-
  und Container-Versionen – einschließlich realer Authentifizierung.
- [ ] Last-, Parallelitäts- und Langzeittests decken die erwartete Zahl an
  Terminals, Zeit- und Arbeitsplatzbuchungen und Dokumentabrufen ab.

### Fachlich und organisatorisch blockierend

- [ ] Rollen- und Funktionstrennung sind durch Process Owner, Datenschutz und
  Informationssicherheit freigegeben.
- [ ] HR, Datenschutz, Betriebsrat und Payroll haben Arbeitszeitregeln,
  Korrekturweg, Aufbewahrung, Schicht-/Zuschlagslogik und Export freigegeben.
- [ ] Bewerberlöschung/-sperre, Zweckbindung und getrennte DMS-ACLs wurden mit
  realen Identitäten als positive und negative Zugriffstests abgenommen.
- [ ] Ein zertifizierter Payroll-Provider übernimmt Steuer-/SV-Berechnung,
  ELStAM, DEÜV, eAU, Bescheinigungen und Zahlungen; die Demorechnung ist im
  Liveprofil technisch deaktiviert.
- [ ] Datenschutz und Betriebsrat haben Zweck, Sichtbarkeit, Aufbewahrung und
  Ausschluss einer Leistungs-/Verhaltenskontrolle für Desksharing freigegeben.
- [ ] Aufbewahrung, Löschung, Audit, GoBD sowie XRechnung/ZUGFeRD sind geklärt.
- [ ] DATEV-, Bank-/SEPA- und E-Rechnungs-Testadapter wurden durch produktive,
  getrennt berechtigte Adapter ersetzt; Summenabstimmung und Wiederholschutz
  sind fachlich abgenommen.
- [ ] Management-Reporting wird inkrementell aus den führenden Systemen beladen;
  Datenalter, fehlgeschlagene Läufe und Quellsummen werden überwacht.
- [ ] Stammdatenmigration besitzt Summen-/Mengenabstimmung und fachliche
  Freigabeprotokolle.
- [ ] Notbetrieb, Wiederanlauf, Support, Verantwortlichkeiten und
  Eskalationswege wurden geprobt.
- [ ] Maschinen-/Prüfmittelanbindung und Seriennummernfluss wurden mit realen
  Geräten abgenommen.

## Release-Entscheidung

Ein grüner CI-Lauf bedeutet: Der geprüfte Code erfüllt die automatisierten
Verträge. Er bedeutet nicht automatisch „produktionsfreigegeben“. Go-live wird
erst erteilt, wenn die blockierenden Checklistenpunkte belegt, der Restore-Test
bestanden und die reale Staging-Abnahme protokolliert sind.
