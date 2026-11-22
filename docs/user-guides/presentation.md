# Management-Demo in 15 Minuten

Diese Präsentation richtet sich an technisch affine Entscheider. Sie zeigt den
kompletten Auftragsprozess vom Kundenstamm und der Opportunity bis zum MES,
zum DMS, zur Lieferung, Rechnung und Migrationsschnittstelle. Details bleiben
in den jeweiligen Prozess- und Benutzeranleitungen; die Live-Demo konzentriert
sich auf Datenfluss, Verantwortlichkeiten und Systemgrenzen.

Das editierbare PowerPoint-Deck liegt im Repository unter:

```text
output/presentation/Open_Manufacturing_Management_Demo_15min_v10_final.pptx
```

Die Sprechernotizen des Decks enthalten Zeitbudget, Live-Aktion, Kernbotschaft
und Quellen für jede Folie.

Die Folien 17 und 18 bilden einen Management-Anhang zur Migration. Der Plan
beginnt nach dem Aufbau der lokalen Betriebsbasis mit einem DMS-Pilot, führt
das DMS anschließend in den Regelbetrieb und startet danach den
Requirements-Pilot. Als Planungsrahmen gelten etwa vier Monate bis zum ersten
produktiven DMS-Nutzen, neun bis zwölf Monate für DMS plus Requirements und
18 bis 24 Monate für die gesamte Plattform. Hardware und Dauer werden vor der
Beschaffung durch Datenprofiling und einen Lasttest bestätigt.

Die Titelfolie enthält den Button **LIVE-RUNDGANG STARTEN**. Er öffnet
FLOWMANAGE mit einer festen Demonstrationsleiste. **Weiter** führt in 25
Schritten durch alle Programme, **Zurück** wiederholt einen Schritt und **×**
kehrt jederzeit zu FLOWMANAGE zurück. Die Leiste bleibt auch beim Wechsel zu
ERPNext, Paperless-ngx, Grafana, Redmine, Keycloak, Wiki, API und Prometheus
sichtbar. Der Rundgang selbst verändert keine Geschäftsdaten; nur zusätzlich
ausgelöste Fachaktionen schreiben Daten.

## Vorbereitung

```bash
cp .env.example .env
make demo
docker compose --profile full up -d
docker compose --profile full run --rm erpnext-seed
```

Vor dem Termin prüfen:

| Oberfläche | URL | Vorbereitung |
|---|---|---|
| FLOWPORTAL | [localhost:8088](http://localhost:8088) | App-Launcher und Rollensicht prüfen |
| FLOWMANAGE | [Rundgang starten](http://localhost:8088/management?managementDemo=1&tourStep=0) | **Demo zurücksetzen**, danach Rundgang starten |
| FLOWID | [AD-/SSO-Zielbild](http://localhost:8088/management#iam-sso) | AD-Simulation, Gruppenvererbung und SSO-Kette zeigen |
| Keycloak | [Gruppenverwaltung](http://localhost:8082/admin/open-manufacturing/console/#/open-manufacturing/groups) | `AD-GG-FLOW-*`, geerbte Realm-Rolle und nahtlosen App-Wechsel zeigen |
| FLOWWORK | [localhost:8088/work](http://localhost:8088/work) | Traceability und Baseline öffnen |
| FLOWQ | [localhost:8088/quality](http://localhost:8088/quality?receipt=PREC-2027-0045) | `PREC-2027-0045` und Messgeräte-Gateway bereithalten |
| FLOWMES | [localhost:8088/mes](http://localhost:8088/mes) | Bedienperson `Emil Elektronik` wählen |
| FLOWHR | [localhost:8088/hr](http://localhost:8088/hr) | `Paula Planung`, Datum 3. November 2026 wählen |
| FLOWSPACE | [Gebäudeplan Berlin](http://localhost:8088/desksharing?date=2026-11-05&site=BER&floor=EG&room=BER-EG-TEAM&colleague=Felix%20Hoffmann) | Teamraum Kreuzberg und Kollegensuche `Felix Hoffmann` öffnen |
| FLOWPORTAL | [Persönlicher KI-Arbeitsplatz](http://localhost:8088/?user_id=USR-006&date=2026-11-05) | Einkaufsprofil mit Tagesbriefing und Agenten öffnen |
| FLOWERP · ERPNext | [localhost:8081](http://localhost:8081) | Opportunity `OPP-2027-0018` öffnen |
| FLOWDOCS · Wiki | [localhost:8001](http://localhost:8001) | Gesamtprozess bereithalten |
| FLOWDOC · Paperless-ngx | [localhost:8010](http://localhost:8010) | Dokumentenlenkung und Freigaben prüfen |
| FLOWGATE · Agentgateway | [localhost:4001/ui](http://localhost:4001/ui/) | mit `demo01` anmelden; Qwen-Modelle und virtuellen FLOWAI-Schlüssel zeigen |

Die Portal-Demo und die echten ERPNext-Belege besitzen im PoC getrennte
Zustände. Diese Grenze wird offen benannt; eine produktive Kopplung läuft über
den dokumentierten ERPNext-MES-Adapter.

## Geführte Route durch alle Programme

| Schritt | Produkt | Typischer Arbeitsschritt |
|---:|---|---|
| 1-2 | FLOWMANAGE, FLOWPORTAL | Auftrag und persönlicher KI-Arbeitsplatz mit rollenabhängigem Tagesbriefing |
| 3-4 | FLOWMANAGE, FLOWID | Arbeitsplatz 2028 sowie AD-Simulation, Gruppenvererbung und SSO-Kette |
| 5-6 | FLOWERP | Kunde/Opportunity; Projekt, Lager, BOM und Fertigung |
| 7 | FLOWQ | Wareneingang scannen, Stichprobe bestimmen, Messwert übernehmen und Lagerentscheid vorbereiten |
| 8-9 | FLOWWORK | Requirements/Tickets sowie Jama-ähnliche Felder, Beziehungen, Reviews, Baselines, Tests und Risiken |
| 10-11 | FLOWMES | nächste Arbeit; Zeit, Material, Seriennummer und Qualität |
| 12 | FLOWDOC | Metadaten, Liefertermin, Baseline, Rechte und Freigabe |
| 13-14 | FLOWHR | Anwesenheit/Abwesenheit; Recruiting und Payroll-Demo |
| 15 | FLOWSPACE | Gebäude und Etage wählen, Raum im Plan öffnen, Platz buchen und Kollegenplatz markieren |
| 16-17 | FLOWFIN, FLOWINSIGHT | Umsatz/Marge/Cash; Fertigungsstatus je Arbeitsgang; CRM-Pipeline 2027–2031 |
| 18-20 | FLOWGATE, FLOWAI, FLOWDOCS | SSO-geschütztes Modell-Gateway; persönliches MCP-Briefing; semantische Suche in lokalen DMS-Vektoren mit Link zum Original; Prozess- und Migrationsdokumentation |
| 21-24 | FLOWTASK, FLOWID, FLOWAPI, FLOWOPS | Aufgaben; Keycloak-Gruppen und SSO; API/Migration; Monitoring |
| 25 | FLOWMANAGE | Entscheidungsstand, Fit-Gaps, Aufwandskorridor und Pilotfreigabe |

Die technischen Standardprodukte bleiben transparent: FLOWERP basiert auf
ERPNext, FLOWDOC auf Paperless-ngx, FLOWTASK auf Redmine, FLOWID auf Keycloak,
FLOWINSIGHT auf Grafana, FLOWAI auf Open WebUI und FLOWOPS auf Prometheus.
FLOWGATE basiert auf Agentgateway und schützt das lokale Qwen-Routing mit
virtuellen Schlüsseln und Keycloak-SSO.

Für die Vorbereitung der einzelnen Stationen dient der
[Prozesskatalog je Anwendung](tool-process-catalog.md). Er enthält für jede
sichtbare Oberfläche mindestens einen typischen Anwenderablauf einschließlich
DMS-Freigabe, ERP-Auftragsanlage, Wareneingangsprüfung und MES-Rückmeldung.

## Entstehungsaufwand und Messgrenze

Der bisherige Dialog enthält ungefähr 70 Arbeitsaufträge, Ergänzungen und
Fortsetzungsanweisungen. Aus dem sichtbaren Gespräch ergibt sich folgender
Planungskorridor; es handelt sich ausdrücklich nicht um Abrechnungs- oder
GPU-Telemetrie:

| Größe | Plausibler Korridor | Einordnung |
|---|---:|---|
| vom Benutzer formulierter Text | ca. 2.500 bis 4.000 Wörter | inklusive kurzer „weiter“-Anweisungen, ohne Bildinhalt |
| reine Schreibzeit | ca. 1 bis 2,5 Stunden | bei etwa 25 bis 45 Wörtern pro Minute |
| Schreiben einschließlich Nachdenken, Prüfen und Screenshots | ca. 3 bis 6 Stunden | realistischere menschliche Arbeitszeit |
| aktive Agenten-Bearbeitungszeit | grob 8 bis 20 Stunden | einschließlich Analyse, Codeänderungen, Builds, Daten-Seeds, Tests und Wartezeit |
| exakte Modell-/GPU-Rechenzeit | nicht verfügbar | die verwendete Oberfläche stellt keine historische Compute- oder Tokenabrechnung für diesen Gesamtchat bereit |

Der Korridor ist eine rückblickende Schätzung und kein belastbarer ROI-Wert.
Für die Pilotphase werden deshalb ab Start automatisch Zeitstempel für Auftrag,
erste Antwort, Tool-Laufzeit, Review, Korrektur und Abnahme erfasst. Erst diese
Messwerte erlauben einen seriösen Vergleich von menschlichem Aufwand,
KI-Laufzeit und eingesparter Durchlaufzeit.

## Ablauf und Zeitbudget

| Zeit | Folie / Thema | Live-Aktion | Managementbotschaft |
|---:|---|---|---|
| 0:00-0:30 | Zielbild | Titelfolie | Ein Fertigungsauftrag läuft durch mehrere spezialisierte Oberflächen, aber über gemeinsame Referenzen. |
| 0:30-1:20 | Persönlicher KI-Arbeitsplatz | Auf **LIVE-RUNDGANG STARTEN** klicken; Einkaufsbriefing mit 80 % Termintreue, Lieferantenrisiko und Agenten zeigen | Jeder Mitarbeiter erhält priorisierte Aufgaben und passende KI-Werkzeuge statt einer allgemeinen Startseite. |
| 1:20-2:20 | Arbeitsplatz 2028 | Szenarioanteile, Entscheidungs-Inbox, Agentenregister, Stufen A0 bis A4 und Vier-Stufen-Roadmap zeigen | Agenten bearbeiten Standardfälle. Menschen verantworten Ausnahmen, Beziehungen, Reviews und Freigaben. |
| 2:20-3:00 | Zwölf Prozessschritte | Prozessleiste im Portal zeigen | Die Kommission `KOM-2027-4711` verbindet Verkauf, Einkauf, Fertigung, Lager, Zeit, Lieferung und Rechnung. |
| 3:00-4:30 | Kunde und Opportunity | **New Customer** öffnen, danach `OPP-2027-0018` | Saubere Partner- und Konditionsdaten sind Voraussetzung für eine belastbare Opportunity und Belegkette. |
| 4:30-6:00 | Konditionen, Projekt, Lager | Zahlungsbedingungen, Projekt und Warehouse Tree öffnen | Projekt sagt, für welche Kommission gebucht wird; Lager sagt, wo das Material liegt. |
| 6:00-7:30 | BOM und Ressourcen | BOM Operations, `WS-MECH` und Job Card zeigen | Material und Arbeitsgänge gehören zur BOM; Arbeitsplätze und Mitarbeiter werden über Job Cards zugeordnet. |
| 7:30-8:20 | FLOWQ Wareneingangsprüfung | `PREC-2027-0045` laden, acht Proben und einen Gateway-Messwert zeigen | Prüfplanrevision, Messmittel und Lagerentscheid sind ohne ERP-Komplexität nachvollziehbar. |
| 8:20-9:10 | FLOWWORK / Jama-Nachbau | Requirement, Beziehung, Review mit Signatur und Testnachweis zeigen | Engineering-Änderungen und Verifikation bleiben versioniert und auditierbar. |
| 9:10-10:15 | MES-Arbeitsvorrat und Zeit | FLOWMES öffnen, Route, Anleitung, Zeit und Qualität zeigen | Das MES zeigt nur ausführbare Arbeit und erzeugt belastbare Rückmeldedaten. |
| 10:15-11:10 | HR, Recruiting und Payroll | Teamkalender, Bewerbung mit DMS-Akte und Payroll-Vier-Augen-Demo | Personalprozesse sind verbunden; gesetzliche Payroll bleibt klar abgegrenzt. |
| 11:10-11:40 | FLOWSPACE Gebäudeplan | Teamraum öffnen, freien Platz zeigen, Felix Hoffmann suchen und seinen Platz im Grundriss markieren | Raum, Platz und sichtbare Kollegenbuchung sind in einer Ansicht verbunden. |
| 11:40-12:10 | Dokumente | freigegebene Anweisung direkt im Browser öffnen | Dokument-ID, Revision, Termin und Gültigkeit bleiben sichtbar. |
| 12:10-13:15 | FLOWFIN und FLOWINSIGHT | Produktionsumsatz, Arbeitsgänge und CRM-Pipeline zeigen | Operative Fertigung und Vertriebsvorschau werden read-only verdichtet. |
| 13:15-14:00 | KI, API und Betrieb | In FLOWAI semantisch nach dem SCU-100-Prüfplan suchen, Paperless-Original öffnen, danach OpenAPI und Monitoring anreißen | Dokumenttexte und Vektoren bleiben lokal; KI und Integrationen nutzen begrenzte Schnittstellen und verlinken die führende Quelle. |
| 14:00-15:00 | Entscheidungsstand | Pilotvorschlag und offene Fit-Gaps | Der PoC ist entscheidungsfähig, aber noch nicht produktionsreif. |

## Live-Demo im Detail

### 0. Identität, AD-Gruppen und SSO

Im FLOWID-Abschnitt des Management-Cockpits zunächst den vollständigen Weg
zeigen:

1. Die AD-Simulation liefert 51 Identitäten und 21 Sicherheitsgruppen.
2. Beispielnutzer `demo06` gehört unter anderem zu
   `AD-GG-FLOW-PROCUREMENT-USER`, `AD-GG-FLOW-DMS-USER` und
   `AD-GG-FLOW-WORK-USER`.
3. Keycloak übernimmt die Gruppen, vererbt daraus Realm-Rollen und stellt die
   OIDC-Sitzung bereit.
4. Anschließend in Keycloak die Gruppenansicht öffnen und danach ohne zweite
   Passworteingabe zu FLOWINSIGHT oder FLOWDOC wechseln.

Dabei klar sagen: Das Repository simuliert den AD-Import. Im Livebetrieb wird
Keycloak read-only per LDAPS an das Unternehmens-AD angebunden; Passwörter
bleiben im AD, Rechte kommen ausschließlich aus freigegebenen Gruppen.

### 1. Kunde anlegen

**Navigation:** `Selling > Customer > Add Customer`

Zeigen, aber für eine reine Präsentation nicht zwingend speichern:

- Customer Name und Customer Type,
- Customer Group und Territory,
- Billing Currency und Price List,
- Payment Terms Template,
- Accounting-, Tax-, Sales-Team- und Portal-User-Reiter.

Kunden, Adressen und Kontakte besitzen getrennte Stammdatensätze. Vor dem
Speichern wird auf Dubletten, USt-ID, Zahlungsbedingungen und vollständige
Rechnungs- und Lieferadressen geprüft.

### 2. Opportunity qualifizieren

`OPP-2027-0018` öffnen und folgende Felder zeigen:

- Kunde `NordMarine Systems GmbH`,
- Opportunity Type `Sales` und Sales Stage `Prospecting`,
- Expected Closing Date und Probability,
- fünf `SCU-100`, Revision C, Zielpreis und Gesamtwert,
- Aktivitäten, Kontakte, Anhänge und Folgebelege.

Danach die Belegkette knapp erläutern:

```text
Opportunity > Quotation > Sales Order > MRP > Einkauf / Fertigung
```

Quotation und Sales Order werden aus dem Vorgänger erzeugt. Freies
Neuerfassen würde Mengenstatus, Preisübernahme und Audit-Trail unterbrechen.

### 3. Konditionen und Kommission

Zeigen:

- Incoterms `EXW`, `FCA` und `DAP`,
- Zahlungsbedingungen `30 Tage netto` sowie `14 Tage 2 Prozent Skonto`,
- Preislisten, Steuern und Liefertexte,
- Projekt `KOM-2027-4711` als Kundenkommission,
- Projektzuordnung auf Sales Order, Einkauf, Work Order, Zeit und Lieferung.

Das Projekt ist keine eigene Firma und kein Lager. Es dient als durchgängige
Auswertungs- und Referenzdimension.

### 4. Lager und Seriennummern

Im Warehouse Tree die vorbereiteten Bereiche zeigen:

- Wareneingang und QS-Prüfung,
- Kleinteile- und Palettenlager,
- Montagebereitstellung und Work in Progress,
- Sperr- und Nacharbeitslager,
- Fertigwaren-, Verpackungs- und Versandbereitstellungslager.

Verantwortung für Seriennummern:

| Vorgang | Erfassung | Kontrolle |
|---|---|---|
| Lieferantencharge oder Kaufteil-Seriennummer | Lager beim Purchase Receipt | Qualität |
| Geräte-Seriennummer | Fertigung vor oder bei Fertigmeldung | Qualität |
| auszuliefernde Seriennummer | Versand in der Delivery Note | Lager / Vier-Augen-Prüfung |

### 5. BOM, Arbeitsplätze und Mitarbeiter

Die BOM enthält Materialpositionen und eine separate Operationsliste. Damit
entspricht ERPNext fachlich einer Ressourcenliste, zeigt Material und
Arbeitsgänge jedoch nicht als gemischte Zeilen in einer einzigen Tabelle.

Vorbereitet sind:

- fünf Arbeitsplätze einschließlich Montage, Elektronik, Firmware, Test und QS,
- sechs Testmitarbeiter mit Arbeitsplatz- und Arbeitsgangzuordnung,
- Arbeitsgänge mit Reihenfolge und Sollzeit,
- Job Cards mit Employee, Workstation, Mengen- und Zeitrückmeldung,
- Activity Types für Fertigung, Rüsten, Qualitätsprüfung, Nacharbeit und Planung,
- Timesheets für Projekt-, Planungs- und Engineering-Zeiten.

### 6. MRP, Einkauf und Wareneingang

Im Portal die Schritte MRP, Einkauf und Wareneingang ausführen:

1. BOM auflösen und Fehlmenge erkennen.
2. Material Request erzeugen.
3. Purchase Order mit Lieferant, Preis, Incoterm und Termin erläutern.
4. Purchase Receipt mit Menge, Charge beziehungsweise Seriennummer und Lagerort erläutern.
5. Material in WIP bereitstellen.

Der Demofall erkennt fünf fehlende Mainboards. Negative oder ungeklärte
Wareneingangsprüfungen buchen in das Sperrlager statt in freien Bestand.

### 6a. FLOWQ-Wareneingangsprüfung

[FLOWQ mit Demobeleg öffnen](http://localhost:8088/quality?receipt=PREC-2027-0045)
und folgende Punkte zeigen:

1. `PREC-2027-0045`, Bestellung, Lieferant, Charge und QS-Zwischenlager sind
   aus dem ERP-Kontext sichtbar.
2. Prüfplan `IP-PCB-MAIN-42` Revision C ist mit FLOWWORK `TP-0001` und
   FLOWDOC `DOC-QP-100` verknüpft.
3. **Stichprobe ermitteln** wählt bei 120 Teilen acht reproduzierbare Proben.
4. Bei `Leiterplattenbreite` **Vom Messgerät** wählen. Der Wert durchläuft
   denselben versionierten REST-Endpunkt wie ein reales Gateway.
5. Kalibrierstatus und erlaubter Messmitteltyp werden vor der Übernahme
   geprüft; das abgelaufene Reservemessmittel ist sichtbar gesperrt.
6. Nach allen Merkmalen bereitet FLOWQ Annahme oder Sperrlager, NCR,
   ERP-Quality-Inspection und DMS-Prüfprotokoll vor.

Kernbotschaft: Für die Bedienperson bleibt es bei „scannen, prüfen,
abschließen“. Bestellung und Bestand bleiben in FLOWERP, Prüfplanfreigabe in
FLOWWORK und Nachweis in FLOWDOC. FLOWQ ist eine updatefeste Erweiterung und
kein ERPNext-Fork.

### 6b. FLOWWORK als Jama-Connect-Nachbau

Im Rundgang zunächst **Anforderungen**, danach **Review Center**, **Tests &
Nachweise** und **Konfiguration** öffnen. Demonstrierbar sind:

- eigene Elementtypen, Workflows und benutzerdefinierte Felder,
- eigene Relationship-Typen und Regeln einschließlich Suspect Links,
- versionierte Anforderungen, Varianten, Kataloge und Baselines,
- moderierte Reviews mit Kommentaren, Rollen und elektronischer Signatur,
- Testfälle, Testpläne, Testläufe, Evidence und Defect-Verknüpfung,
- Risiken sowie Ende-zu-Ende-Traceability zu Redmine-Ticket und Wiki.

Die Wareneingangsprüfung verwendet einen freigegebenen FLOWWORK-Testplan als
Spezifikation, führt Messwerte und Lagerentscheidung aber bewusst in FLOWQ und
FLOWERP aus.

### 7. MES-Arbeit ausführen

FLOWMES zeigt je Bedienperson:

- persönlichen Arbeitsvorrat und nächsten freigegebenen Job,
- Work Order, Sales Order und Kommission,
- Fertigungsroute mit Vorgänger- und Folgeschritten,
- Arbeitsplatz, Planzeit, Menge und Termin,
- Arbeitsanweisung und Pflichtcheckliste,
- Material, Chargen und Seriennummern,
- Prüfmerkmale und Messwerte,
- Zeitbuchungen und Plan-Ist-Abweichung,
- Live-Meldungen und verknüpfte Dokumente.

Bedienhandlungen:

| Aktion | Wirkung |
|---|---|
| **Arbeit starten** | prüft Bedienperson, Arbeitsplatz und Vorgänger; öffnet Zeitlog |
| **Pause** | beendet offenen Zeitlog und speichert Grund sowie Notiz |
| **+ Zeit** | erfasst Korrektur-, Rüst- oder sonstige Zeit |
| **Störung** | blockiert Job und dokumentiert Kategorie sowie Beschreibung |
| **Störung lösen** | dokumentiert Maßnahme und gibt Job wieder frei |
| **Abschließen** | prüft Checkliste, Gut-/Ausschussmenge und Seriennummern; gibt Folgejob frei |

### 8. HR-Zeit und Abwesenheiten

FLOWHR mit `Paula Planung` öffnen und knapp zeigen:

- persönlicher Anwesenheitsstatus mit Kommen/Gehen und Tageszeitleiste,
- Soll-/Ist, Tagessaldo, Zeitkonto und Resturlaub,
- Teamdisplay mit Anwesenheit, mobilem Arbeiten und datenschutzreduzierter
  Abwesenheit,
- Monatskalender für Urlaub, Überstundenabbau, Mehrarbeit und Dienstreise,
- offene Genehmigung eines Mitarbeiters,
- ERP-Übergabe mit Vorschau, Bestätigung und Idempotenz,
- unter **Bewerbungen** `APP-0001`, Phasen, Löschtermin und das fiktive
  Bewerberprofil direkt im Browser,
- unter **Lohnabrechnung** die Vorschau als `Helena Personal`, danach Wechsel
  auf `Konrad Kontrolle` für die getrennte Freigabe und das PDF.

Kernbotschaft: FLOWHR misst Anwesenheit und führt Konten; MES/Job Card misst die
Zeit am konkreten Arbeitsgang. Beides darf verglichen, aber nicht ungeprüft
gleichgesetzt werden. Recruiting- und Payroll-Workflow sind PoC-Funktionen;
die Abrechnung nutzt aber feste Testwerte. eAU, ELStAM, DEÜV, Zahlungen und
gesetzlich validierte Berechnung benötigen einen freigegebenen Provider.

### 8b. FLOWSPACE Gebäudeplan und Kollegensuche

[FLOWSPACE mit Berlin-Demoplan öffnen](http://localhost:8088/desksharing?date=2026-11-05&site=BER&floor=EG&room=BER-EG-TEAM&colleague=Felix%20Hoffmann).

1. Standort **Berlin · Werk & Büro**, Erdgeschoss und **Teamraum Kreuzberg**
   sind bereits gewählt. Der Plan zeigt Räume, Türen, Flur und die einzelnen
   Arbeitsplätze mit Live-Belegung.
2. Einen weißen Platz anklicken. Ausstattung, Raum, Datum und Zeitfenster
   prüfen und die Buchung bestätigen.
3. Auf **Kollegen finden** wechseln und nach `Felix Hoffmann` suchen.
4. Das Ergebnis auswählen. FLOWSPACE wechselt zur richtigen Etage, markiert
   Arbeitsplatz `BER-D012` blau im Grundriss.
5. Die Platzinformation nennt Etage, Raum, Arbeitsplatz und Buchungszeitraum.
   Eine Weg- oder Laufwegfunktion ist nicht Bestandteil von FLOWSPACE.

Nur Personen mit einer aktiven Buchung am gewählten Standort, Datum und
Zeitfenster erscheinen in der Suche. Im Livebetrieb müssen Betriebsrat,
Datenschutz, Sichtbarkeitsoptionen und Löschfristen verbindlich geregelt werden.

### 9. Dokumente direkt öffnen

Unter **Arbeitsunterlagen** die Montageanweisung öffnen. Der API-Endpunkt
liefert PDFs mit `Content-Disposition: inline`; deshalb zeigt der Browser das
Dokument im eingebetteten Viewer statt einen Download zu starten.

Verfügbar sind im Demofall unter anderem:

- technische Zeichnung SCU-100,
- Montageanweisung Revision D,
- Prüfplan Revision B,
- Lieferantenzertifikat Mainboard,
- Abnahmeprotokoll Auftrag 4711.
- fiktives Bewerberprofil und Muster-Entgeltabrechnung mit jeweils eigener
  geschützter DMS-ACL.

Paperless-ngx bleibt das führende DMS. ERP und MES speichern stabile
Dokument-IDs, Revision und Gültigkeit, nicht unkontrollierte Dateikopien.

Anschließend kurz den
[DMS-Dokumentenlieferplan](http://localhost:3000/d/dms-document-deliveries/dms-e28093-dokumentenlieferplan)
zeigen: Projekt `KOM-2027-4711` wählen und an Baseline, Liefertermin, Forecast
und Ist-Datum erläutern, welche Dokumente geliefert sind, in 14 Tagen fällig
werden oder terminlich gefährdet sind. Ein Klick auf den Titel führt zurück in
den Paperless-Datensatz.

### 10. Qualität, Lieferung und Buchhaltung

Den Fehlerfall nur knapp erläutern oder bei verfügbarer Zeit live starten:

1. Abweichung für eine Seriennummer melden.
2. Job und betroffene Einheit sperren.
3. NCR und Nacharbeit dokumentieren.
4. Wiederholprüfung und Freigabe durchführen.
5. Fertigware einlagern.
6. Delivery Note aus Sales Order erzeugen und freigegebene Seriennummern wählen.
7. Sales Invoice aus der Lieferung erzeugen und Zahlung zuordnen.

### 11. API, Migration und lokale KI

Bereits lesbar über API/MCP:

- persönliches Tagesbriefing, rollenabhängiger Werkzeugkatalog und Kontext einer Fokusaktion,
- Fertigungsaufträge und überfällige Bestellungen,
- Auftragsstatus, Produkte und BOM-Details,
- Bestand, Lagerbewegungen und Materialverbrauch,
- DMS-Dokumente und Metadaten,
- Abschnitte und Seiten der Prozessdokumentation.

Kontrolliert schreibbar sind mehr als 22 Stammdatentypen, darunter Kunden,
Lieferanten, Artikel, BOMs, Arbeitsplätze, Mitarbeiter, Projekte, Lager und
Zeitdaten. Schreibvorgänge verwenden erlaubte Feldlisten, Preview,
Bestätigungstoken, Mengenlimit und Audit-Log.

Die lokale KI erhält keine freie Datenbankverbindung. Drei MCP-Server liefern
Plattform-/ERP-Daten, DMS-Metadaten und Prozesswissen. Der Plattform-MCP führt
diese Quellen zu persönlichen Briefings zusammen. Fachliche Schreibaktionen
bleiben bis zur rollenbezogenen OAuth-, Vorschau- und Bestätigungslogik im
jeweiligen System.

## Abgedeckte Funktionen auf einen Blick

| Bereich | Im PoC demonstrierbar |
|---|---|
| Persönlicher KI-Arbeitsplatz | 50 Rollenprofile, Tagesbriefing, Prioritäten, Fachagenten, KI-Prompts, Fachlinks und persönlicher MCP-Werkzeugkatalog |
| CRM / Vertrieb | Kunde, Kontakt, Opportunity, Quotation, Sales Order, Konditionen |
| Projekt / Controlling | Kommission, Project-Feld, Kosten- und Zeitbezug |
| Projektarbeit / Requirements | Redmine-Tickets, Board, Wiki, eigene Typen/Felder/Beziehungen, Reviews, Signatur, Requirement-Versionen, Varianten, Baselines, Tests, Risiken und Traceability |
| Disposition / Einkauf | BOM-Auflösung, MRP, Material Request, Purchase Order, Termin |
| Lager | Wareneingang, Charge, Seriennummer, Lagerhierarchie, WIP, Sperre, Versand |
| Produktion | BOM, Operations, Work Order, Job Cards, Arbeitsplätze, Mitarbeiter |
| MES | Queue, Route, Anleitung, Checkliste, Material, Prüfen, Zeit, Störung, Abschluss |
| HR / Zeitwirtschaft | Anwesenheit, Zeitkonto, Urlaub, Abbau, Mehrarbeit, Kalender, Team, Freigabe, ERP-Export |
| Recruiting / Payroll | Stellen, Bewerbungsphasen, DMS-Akte, Löschprüfung, Stammdatencheck, Vier-Augen-Demolauf, Inline-PDF, DMS-/ERP-Übergabe |
| Desksharing / IAM | 2 Standorte, 100 Plätze, Gebäude-/Etagenplan, Raumauswahl, Buchung/Check-in, markierter Kollegenplatz, 50 Fachkonten, zentraler Admin und Keycloak-SSO |
| Qualität / Wareneingang | FLOWQ-Scanarbeitsplatz, feste/prozentuale/AQL-/100-%-Stichprobe, Messmittelkalibrierung, REST-/MQTT-/OPC-UA-/Seriell-Gateway, ERP-Quality-Inspection, NCR, Sperre und Freigabe |
| DMS | Suche, Metadaten, Revision, direkte PDF-Anzeige, Meilensteine und Dokumentlieferdashboard |
| Lieferung / Finanzen | Delivery Note, Serienauswahl, Sales Invoice, Payment Entry |
| Integration | REST, MCP, ERPNext-, Paperless-, Redmine- und Wiki-Adapter |
| Migration | kontrollierter Stammdatenimport mit Preview, Bestätigung und Audit |
| KI / Betrieb | lokale KI, Quellen, Keycloak-OIDC/PKCE, zentrale Rollen, Prometheus und Grafana |

## Entscheidungsstand

Bereits belastbar demonstriert:

- durchgängige Beleg- und Projektreferenz,
- Ressourcen, Zeiten, Seriennummern und Qualitätslogik,
- MES-Bedienablauf mit eingebetteten Arbeitsunterlagen,
- HR-Anwesenheit, Abwesenheitsplanung und Führungskräftefreigabe,
- API-, MCP- und lokale KI-Basis.
- persönlicher KI-Arbeitsplatz für Einkauf, Engineering, Produktion, Qualität, Planung, Lager, Vertrieb, HR, Finanzen und IT.

Im Pilot zu beweisen:

- produktive Synchronisation zwischen ERPNext und MES,
- Upstream-SSO-Adapter, MFA, Betriebsvereinbarung, komplexe Schichtregeln und validierter
  Payroll-/ELStAM-/DEÜV-/eAU-Provider,
- Rollen, SSO, Freigaben, Audit und Betriebskonzept,
- GoBD, DATEV, E-Rechnung und reale Kontierung,
- Migration echter Stamm- und Bewegungsdaten,
- Schicht-, Skill- und Maschinenlogik mit realen Randbedingungen.

**Empfehlung:** einen begrenzten Pilot mit repräsentativen Artikeln, zwei
Kundenaufträgen und einem echten Schichtablauf durchführen. Erfolgskriterien
sind vollständige Rückverfolgung, stabile Schnittstellen, belastbare Zeiten und
Bestände sowie dokumentierte Fit-Gaps.

## Erwartbare Managementfragen

| Frage | Kurze Antwort |
|---|---|
| Ist das produktionsreif? | Nein. Der PoC ist entscheidungsfähig; der Pilot muss Betrieb, Rollen, Integration und Accounting-Fit nachweisen. |
| Müssen wir alles selbst bauen? | Nein. ERPNext und Paperless liefern Standardfunktionen; Eigenbau konzentriert sich auf MES-/HR-Bedienung, Integration, Migration und lokale KI. |
| Kann das System unsere Ressourcenliste abbilden? | Ja, fachlich über BOM-Materialien, BOM-Operations, Workstations und Job Cards; die Darstellung ist getrennt und nicht als eine gemischte Liste aufgebaut. |
| Wie funktioniert die Zeitverschreibung? | Anwesenheit und Abwesenheiten laufen in FLOWHR, Fertigungszeit über Job Card/MES und Projekt-/Engineeringzeit über Timesheets. |
| Ersetzt FLOWHR Sage HR vollständig? | Nein. Zeitwirtschaft, Recruiting und ein Payroll-Demolauf sind demonstrierbar; gesetzliche Berechnung, eAU, DEÜV/ELStAM, Zahlungen und Tariflogik benötigen einen validierten Provider. |
| Sind Projekte und Kommissionen möglich? | Ja. Das Project-Feld verbindet Verkaufs-, Einkaufs-, Fertigungs-, Zeit-, Lager-, Liefer- und Rechnungsbelege. |
| Können Dokumente direkt geöffnet werden? | Ja. Das MES zeigt freigegebene PDFs inline; Paperless bleibt führendes DMS. |
| Kann es deutsche Buchhaltung? | Die ERP-Basis ist vorhanden; GoBD, DATEV, E-Rechnung und reale Kontierung bleiben formaler Fit-Gap. |
| Wie verhindert ihr KI-Fehlaktionen? | Kein freier DB-Zugriff, nur freigegebene Tools, Quellen, Rollenprüfung und Bestätigung für Schreibvorgänge. |
