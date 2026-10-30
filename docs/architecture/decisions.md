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
