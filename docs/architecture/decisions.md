# Architekturentscheidungen

## ADR-001: ERPNext als ERP-Kern

**Status:** für den PoC angenommen

ERPNext vereint CRM, Vertrieb, Einkauf, Lager, Fertigung und Buchhaltung auf
dem Python-basierten Frappe Framework. Für den PoC vermeiden wir getrennte CRM-
und Accounting-Systeme. Vor einer Einführung müssen deutsche Lokalisierung,
GoBD, DATEV, XRechnung, ZUGFeRD, UStVA und der benötigte Kontenrahmen bewertet
werden.

## ADR-002: Paperless-ngx als DMS

**Status:** für den PoC angenommen

Paperless-ngx bietet OCR, Suche, Tags und eine gute Bedienoberfläche. Dokumente
werden nicht als Binärdatei im ERP dupliziert; das ERP hält Dokument-ID,
Revision und einen stabilen Link.

## ADR-003: Python Integration Layer

**Status:** umgesetzt

FastAPI kapselt Systemzugriffe und stellt ausschließlich fachliche, prüfbare
Werkzeuge bereit. Das schützt vor direktem Datenbankzugriff durch Portal oder
LLM und ermöglicht Auditierung, Tests und spätere Adapterwechsel.

## ADR-004: Prozesszentrierte Docs as Code

**Status:** umgesetzt

Markdown und Mermaid liegen mit dem Code in Git. Die führende Navigation ist
der Prozess. Systemsichten ergänzen ihn. Eine Änderung gilt nur dann als
fertig, wenn betroffene Prozess-, User-, Admin- und Schnittstellenseiten im
selben Pull Request aktualisiert wurden.

## ADR-005: Deterministische Demo vor lokalem LLM

**Status:** umgesetzt

Die Demo muss auch ohne Modell-Download reproduzierbar antworten. Deshalb
liefert der Standardmodus regelbasierte Antworten mit Quellen. Ollama ist ein
optionales Profil und darf nur denselben freigegebenen Kontext verarbeiten.

## ADR-006: MkDocs Material im PoC, Migration vor Produktion

**Status:** zeitlich befristet angenommen

Das Wiki verwendet für den PoC Material for MkDocs 9.8.0. Das Projekt erhält
laut Maintainer nur noch bis 5. Mai 2027 kritische Korrekturen. Vor einem
produktiven Rollout wird deshalb entweder ein gepflegtes MkDocs-Theme gewählt
oder die Kompatibilität mit dem Open-Source-Nachfolger
[Zensical](https://zensical.org/docs/compatibility/mkdocs/migration/) geprüft.
Die Markdown-Inhalte und Mermaid-Diagramme bleiben dabei portabel.

## ADR-007: Eigene Oberfläche über die APIs der Fachsysteme („Headless“)

**Status:** vorgeschlagen, für FLOWPORTAL, Agentenzentrale und FLOWDOC umgesetzt (2026-11-22)

**Frage:** Sollen wir weiter die Oberflächen der Open-Source-Werkzeuge anpassen oder eine eigene
Oberfläche bauen und die Werkzeuge nur noch über ihre APIs anbinden?

**Entscheidung:** Für die tägliche Arbeit der Beschäftigten bauen wir eine eigene, einheitliche
Oberfläche (FLOWPORTAL und Fachansichten wie FLOWDOC, FLOWWORK, FLOWQ, FLOWMES). Die Fachsysteme
(ERPNext, Paperless-ngx, Redmine, Keycloak) bleiben **führende Systeme** für Daten, Rechte, Historie
und Geschäftslogik und werden ausschließlich über ihre unterstützten APIs angebunden. Die
Administrationsoberflächen der Werkzeuge bleiben für Betrieb und seltene Sonderfälle erreichbar.

**Gründe:**

- „Eine Oberfläche für alles“ ist das Zielbild (KI-U-00 Arbeitsplatz 2028). Angepasste Fremd-UIs
  bleiben uneinheitlich, brechen bei Updates und lassen sich kaum mit Agenten, Entscheidungs-Inbox
  und Tagesbriefing verbinden.
- Updates der Fachsysteme bleiben einfach, weil wir ihren Code und ihre Templates nicht verändern.
- Agenten und Menschen nutzen dieselben fachlichen API-Werkzeuge (ADR-003), dadurch sind Rechte,
  Audit und Tests an einer Stelle.

**Leitplanken (verbindlich):**

1. Das Quellsystem entscheidet über Objektrechte. Die eigene Oberfläche fragt **im Namen der
   angemeldeten Person** (FLOWDOC: Paperless-Remote-User aus der FLOWID-Sitzung) und baut keine
   eigene Rechtelogik nach. Technische Konten nur im gekennzeichneten Demo-Modus.
2. Keine Schattendatenhaltung: Die Oberfläche speichert keine Fachobjekte; Caches unterliegen
   derselben Rechteprüfung (KI-EK Teil 04).
3. Nur unterstützte, versionierte APIs; Abhängigkeiten von internen Endpunkten werden als Risiko
   dokumentiert und getestet.
4. Ein Werkzeug wird nur dann „headless“ genutzt, wenn seine API den Fachprozess abdeckt. Seltene
   Expertenfunktionen (z. B. Paperless-Ablageregeln, ERPNext-Customizing) bleiben in der
   Werkzeug-Oberfläche.

**Folgen und Risiken:** Höherer Entwicklungsaufwand für die Oberfläche; Funktionen der Werkzeuge
müssen bewusst nachgezogen werden; die Plattform-API wird zur zentralen Komponente und braucht
Betrieb, Monitoring und Tests wie ein Fachsystem. Paperless-ngx ist kein revisionssicheres Archiv
(KI-U-03); GoBD-Archivierung wird gesondert gelöst. Die Remote-User-Anbindung setzt voraus, dass
Paperless nur aus dem Plattformnetz erreichbar ist (offener Punkt für den Produktivbetrieb:
OIDC-Token-Weitergabe statt Header).

## ADR-008: Rollengetrennte Agentenplattform FLOWAGENTS

**Status:** implementiert und getestet, Betriebsfreigabe durch Bas offen (2026-11-22)

**Entscheidung:** Die Entwicklung eigener Fachsoftware läuft über einen deterministischen
Orchestrator (`services/agent_orchestrator`) mit elf Entwicklungsrollen und einem
Geschäftsführungs-Agenten aus dem versionierten Register `agents/registry.yaml`. Der Ablauf
(`agents/workflow.yaml`) führt vom Fachauftrag über die Gates G1–G5; Menschen entscheiden in der
Entscheidungs-Inbox des FLOWPORTAL. Anforderungen, Baselines und Testfälle liegen in FLOWWORK.

**Wesentliche Eigenschaften:**

- Modelle erhalten keine Werkzeuge. Der Orchestrator führt erlaubte FLOWWORK-Operationen mit einem
  kurzlebigen, rollen- und laufgebundenen Token aus; der RM-Adapter prüft Register und Operation
  serverseitig erneut.
- Ersteller und Prüfer gehören zu verschiedenen Modellfamilien; Review, Integrationsprüfung und
  Abnahme binden sich an den Digest des Änderungsstands.
- Lokale Modelle über FLOWGATE mit einem virtuellen Schlüssel je Rolle, der nur das Modellprofil
  der Rolle erlaubt. Die Codex-/Claude-Abo-Worker aus `Trading_Ai` sind übernommen, aber technisch
  gesperrt, bis Isolation und Betrieb freigegeben sind.
- Der Orchestrator läuft als Host-Dienst (Sandbox-Prüfungen brauchen Docker), öffnet aber keinen
  aus dem Plattformnetz erreichbaren Port: Er holt Aufträge und Entscheidungen bei der Plattform-API
  ab und meldet dorthin seinen Zustand (Pull-Modell).

**Abweichung zum Trading-Orchestrator:** Dort arbeitet ein Autor-Reviewer-Paar auf GitHub-Issues
und -PRs. Hier steuert der Orchestrator den vollständigen Fachprozess mit FLOWWORK als Register und
Entscheidungen im Portal. Ein GitHub-PR-Weg für echte Code-Änderungen folgt nach Freigabe der
Abo-Worker (siehe `docs/agents/betrieb.md`).
