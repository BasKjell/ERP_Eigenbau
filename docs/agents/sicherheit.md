# FLOWAGENTS – Sicherheit (Systemdokumentation)

**Stand:** 2026-11-24 · **Status:** Arbeitsentwurf, Freigabe durch Informationssicherheit und Bas offen

Diese Seite beschreibt, wie FLOWAGENTS abgesichert ist – als Grunddokumentation wie für jedes andere System
(Aufbau nach den [Vorlagen Systemdokumentation](../konzepte/vorlagen-systemdokumentation/00-wegweiser.md)).
Sie enthält bewusst **keine Zuordnung zu einzelnen Anforderungen** aus IT-Grundschutz oder ISO/IEC 27001
und **keine Tests je Anforderung**. Welche Anforderungen diese Dokumentation erfüllt, ordnet der ISB im
Anforderungs- bzw. ISMS-System zu [FIRMENANGABE U-12]. Regeln und Begründungen stehen im
[Sicherheitskonzept](sicherheitskonzept.md).

## Steckbrief

| Feld | Eintrag |
|---|---|
| System | FLOWAGENTS – Agentenplattform für die Entwicklung eigener Fachsoftware und für Fachagenten |
| Komponenten | Orchestrator (Host-Dienst), Plattform-API mit Agentenzentrale, FLOWGATE (agentgateway), lokale Modelle (Ollama), Prüf-Sandbox, Vorschau und Prüfbrowser, Worker (OpenCode lokal; Codex/Claude über Abo), FLOWWORK (Anforderungen), Keycloak/AD |
| Betriebsort | Referenzumgebung: ein Rechner mit Docker Compose; Produktivbetrieb nach IT-Zielbild offen |
| Verantwortlich | Teamleitung Business Applications [FIRMENANGABE U-04] |
| Schutzbedarf | festzulegen durch ISB [FIRMENANGABE U-01] |
| Verweis Anforderungssystem | [FIRMENANGABE U-12] |

## Sicherheitsmaßnahmen

| Thema | Umsetzung | Festgelegt in |
|---|---|---|
| Anmeldung und Rechte von Personen | Anmeldung über Keycloak (OIDC); Freigaberollen `flow-*` und Projektrollen `flow-prj-*` aus AD-Gruppen; Entscheiden nur in der eigenen Rolle und als Projektmitglied, Einreichen und Paketstart nur mit Änderungsrecht im Projekt; Übersicht zeigt nur eigene Projekte | `scripts/generate_iam_demo.py`, `agents/projects.json`, `agents/registry.yaml` (`human_roles`) |
| Rollen der Agenten | Nur Agenten mit gültigem Registereintrag (Owner, Stufe, Ablaufdatum) arbeiten; Werkzeuge je Rolle, serverseitig im RM-Adapter erneut geprüft; kein Agent hat Freigabe-, Merge-, Lösch- oder Deploy-Werkzeuge | `agents/registry.yaml`, `flowagents/registry.py`, `app/rm_adapter.py` |
| Unabhängigkeit und Freigaben | Prüfer aus anderer Modellfamilie als Ersteller; Testagenten ohne Zugriff auf die Implementierung; Gates EP1 und G1–G5 durch Menschen je nach Einstufung; G4 und G5 immer menschlich; Review, Integrationsprüfung und Abnahme an den Digest des Stands gebunden | `agents/workflow.yaml`, `flowagents/engine.py` |
| Änderungen an Agenten | Übersteuerungen nur durch `platform-admin`, mit Begründung, geprüft wie das Register, protokolliert; der Registerstand ändert sich, offene Läufe halten bis zur Umstellung | `flowagents/registry.py`, `flowagents/engine.py` |
| Modelle | Nur lokale Modelle über FLOWGATE; je Rolle bzw. Dienst ein virtueller Schlüssel, der nur das freigegebene Modell erlaubt; kein Cloud-Rückfall im Gateway | `deployment/agentgateway/config.yaml` |
| Externe Modelle | Codex/Claude nur für komplexe, nicht vertrauliche Aufträge; eigenes internes Netz je Anbieter mit Egress-Proxy, Anmeldedaten schreibgeschützt, kein Repository | `config/orchestrator.yaml` (`escalation`, `container`), `flowagents/container.py` |
| Isolation | Prüf-Sandbox ohne Netz und Zugangsdaten, nur freigegebene Pfade; OpenCode-Worker im internen Netz nur zu FLOWGATE, ohne Werkzeuge; Prüfbrowser im internen Netz nur mit der Vorschau, Schreibzugriffe gesperrt | `flowagents/sandbox.py`, `flowagents/opencode.py`, `deployment/ui-runner` |
| Daten | Nur synthetische oder freigegebene Entwicklungsdaten; vertrauliche Aufträge nur lokal; Agenten lesen nur die Ergebnisarten ihres Registereintrags; Fachagenten bekommen Hintergrunddaten nur, wenn die anfragende Person selbst berechtigt ist | `flowagents/engine.py`, `flowagents/fachagenten.py`, `app/flow_routes.py` |
| Fachagenten | Anlegen nur durch Administratoren, Nutzung nur durch zugewiesene AD-Gruppen oder Personen, nur lokale Modelle, nur Entwürfe mit menschlicher Freigabe | `flowagents/fachagenten.py` |
| Schnittstelle Plattform – Orchestrator | Orchestrator öffnet keinen Port zu den Containern; Aktionen und Zustand per Pull mit kurzlebigem Dienst-Token | `app/agents_bff.py`, `flowagents/sync.py` |
| Protokollierung | Ereignisse und Audit ohne Inhalte (Lauf, Rolle, Operation, Objekt, Entscheidung); Modellnutzung je Rolle ohne Prompts | `flowagents/store.py`, FLOWWORK `rm_audit` |
| Anhalten und Wiederanlauf | Stopp-Schalter je Agent und global; Laufbudget; Blockade bei ungültiger Antwort, Fehler oder geänderten Regeln; unterbrochene Schritte werden nach Neustart idempotent wiederholt | `flowagents/engine.py`, [Betrieb](betrieb.md) |
| Übernahme von Ergebnissen | Nur nach G4 als lokaler Branch mit Integritätsprüfung; Merge und Auslieferung durch Menschen | `flowagents/adoption.py` |

Automatisierte Tests im Repository (`services/agent_orchestrator/tests`, `services/platform_api/tests`)
sichern diese Maßnahmen bei jeder Änderung ab; sie sind Entwicklungsnachweis, kein Prüfprotokoll.

## Bekannte Abweichungen

| Abweichung | Behandlung |
|---|---|
| Lokaler Betrieb ohne TLS; Demo-Geheimnisse (`change-before-network-use`); Demo-Kennwörter und „Person wechseln“ nur für die lokale Demo | vor jeder Netzwerknutzung beheben |
| Symmetrische Tokens zwischen Orchestrator und Plattform statt Keycloak-Dienstkonten mit Token Exchange | Ziel nach KI-EK Teil 09 |
| Paperless-Remote-User-Header im internen Netz fälschbar | Netzsegmentierung oder OIDC-Weitergabe |
| AD-Anbindung simuliert; MFA-Pflicht für Freigabe- und Projektgruppen und benannte Vertretungen offen | mit echter LDAP-Föderation |
| Kein Paketspiegel, keine SBOM; Schwachstellen-Agent inaktiv | offen |
| Keine Modell-Evaluation je Rolle; lokale Prüfer können unpräzise Kriterien durchlassen | G1 bei neuen Funktionen bleibt menschlich |
| Kein automatischer PR-Weg; Ergebnisse nur als lokaler Branch | bewusst |
| Abo-Worker teilen Anmeldung, Netze und Egress-Proxys mit Trading_Ai | eigene Volumes und Netze für FLOW |
| Übersteuerungen der Agentenkonfiguration und Fachagenten nicht im versionierten Register | dauerhafte Änderungen per Review in `agents/registry.yaml` |
| Zustand in SQLite mit eigener Ablaufschleife, keine Hochverfügbarkeit | Zielbild [Orchestrierung](plattformstrategie.md) |

Für die Produktivsetzung wird FLOWAGENTS wie jedes System mit den Vorlagen V01 bis V13 dokumentiert und
freigegeben.
