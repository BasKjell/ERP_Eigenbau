# FLOWAGENTS – Sicherheit, Kontrollzuordnung und Nachweise

**Status:** Arbeitsvorschlag. Eine Maßnahme ist erst „wirksam“, wenn ein zuständiger Mensch Umsetzung
und Stichprobe geprüft hat (KI-EK Teil 05). „Getestet“ heißt hier: automatisierter Test im Repository
besteht; der Nachweis gegen das betriebliche Grundschutzmodell, die SoA und die Zertifikatsbasis des
Unternehmens steht aus [FIRMENANGABE U-12].

## Kontrollzuordnung (ISO/IEC 27001:2022 Anhang A, IT-Grundschutz-Kompendium Edition 2023)

| Anhang A | Baustein | Umsetzung in der Referenzumgebung | Beleg | Status |
|---|---|---|---|---|
| A.8.25–A.8.27 | CON.8, CON.10 | Anforderungen mit Quelle und Akzeptanzkriterien vor jeder Umsetzung; Architektur- und Sicherheitsrolle vor G2 | `requirements/catalog.yaml`, Agenten 1–4, ADR-007/008 | getestet |
| A.8.28, A.8.29 | CON.8, OPS.1.1.6 | Codeprüfung durch andere Modellfamilie, Integrationsprüfung offline am Digest, unabhängige Akzeptanztests | REQ-AGT-002/-006/-009 | getestet |
| A.8.31–A.8.33 | OPS.1.1.3, OPS.1.1.6 | Sandbox ohne Netzwerk/Zugangsdaten, Export ohne `.env`, nur synthetische Daten, Produktion außerhalb des Agentennetzes (G5) | REQ-AGT-009/-014 | getestet |
| A.5.3, A.5.15–A.5.18, A.8.4 | ORP.1, ORP.4 | Rollenregister mit Ablaufdatum, Werkzeugmatrix serverseitig, keine Selbstfreigabe, getrennte Identitäten je Rolle (Token, FLOWGATE-Schlüssel) | REQ-AGT-001/-010/-011 | getestet; Rezertifizierung offen |
| A.8.8, A.8.13, A.8.15, A.8.16 | OPS.1.1.3, CON.3, OPS.1.1.5 | Audit ohne Inhalte (FLOWWORK `rm_audit`, Orchestrator-Ereignisse), Wiederanlauf mit idempotenten Schritten | REQ-AGT-012/-013, REQ-REQ-001 | teilweise; SBOM-Agent (11) und Restore-Probe offen |
| A.5.19–A.5.22 | – | Lokale Modelle als Standard, keine Cloud-Fallbacks im Gateway; Eskalation zu Codex/Claude-Abo-Workern nur für interne Daten, mit Egress-Proxy, getrenntem Login je Anbieter und Familienprüfung | REQ-AGT-014, REQ-AGT-021, `deployment/agentgateway/config.yaml`, `config/orchestrator.yaml` | implementiert; Modelllizenzen und Herkunft offen; Worker teilen Login und Netze mit Trading_Ai |
| A.8.3, A.5.10 | APP.3.1, CON.6 | DMS: Abfrage im Namen der Person, kein technischer Rückfall im OIDC-Modus | REQ-DOC-002 | getestet |
| A.5.15, A.5.18, A.8.3 | ORP.4 | Projektrechte aus AD-Gruppen `AD-GG-FLOW-PRJ-*-LESEN/-AENDERN`: Einreichen und Paketstart nur mit Änderungsrecht, Entscheiden nur als Mitglied, Übersicht filtert fremde Projekte; Aufsicht (ISB, GF) sieht alles | `agents/projects.json`, `test_project_rights.py`, `test_project_rights_demo.py` | getestet; Rezertifizierung der Gruppen offen |
| A.8.9, A.8.32 | OPS.1.1.6, ORP.4 | Agentenkonfiguration nur durch `platform-admin`, mit Begründung, Prüfung wie das Register (Unabhängigkeit, Werkzeuge, Datenklassen, Stufe), Protokoll, Registerstand ändert sich | `test_agent_config.py` | getestet; Übersteuerungen nicht im versionierten Register |
| A.8.22, A.8.31 | SYS.1.6, NET.1.1 | OpenCode-Worker: internes Netz nur zu FLOWGATE, read-only, keine Werkzeuge, Schlüssel nicht in der Befehlszeile; Prüfbrowser im internen Netz ohne Internet, Schreibzugriffe gesperrt | `test_opencode.py`, `deployment/ui-runner` | getestet; Netztest von außen offen |
| A.5.15, A.8.11, A.8.12 | ORP.4, APP.3.1 | Fachagenten: anlegen nur Admins, nutzen nur zugewiesene AD-Gruppen/Personen, Hintergrunddaten nur bei eigener Rolle der anfragenden Person, nur lokale Modelle, nur Entwürfe mit menschlicher Freigabe | `test_fachagenten.py`, `test_project_rights_demo.py` | getestet; kein Postfach angebunden |

## Abnahmeplan (KI-EK Teil 10) – Abdeckung

Ausgangsstatus aller Prüfungen ist **OFFEN**. Die Tabelle zeigt, welche Prüfziele automatisierte
Tests im Repository abdecken. Sie ersetzt nicht das Prüfprotokoll mit Umgebung, Testidentität, Soll,
Ist, Beleg-ID und Urteil.

| Fall | Kurzbeschreibung | Abdeckung im Repository |
|---|---|---|
| 01 | Alle erlaubten Werkzeuge je Rolle funktionieren | teilweise (`test_flow_agents.py`, Live-Lauf A-001) |
| 02 | Entwicklung legt keinen RM-Entwurf an | `test_02_developer_cannot_create_requirement_drafts` |
| 03 | Nicht freigegebenes Modell | `test_03_gateway_uses_role_key_and_profile_alias_only`; live: FLOWGATE 403 |
| 04 | Ohne / abgelaufenes Token | `test_04_*` (Orchestrator und RM-Adapter) |
| 05 | Token für andere Zielressource | `test_05_*` (Orchestrator und RM-Adapter) |
| 06 | Push auf fremden Branch | Sandbox: `test_06_changes_outside_the_approved_scope_are_rejected`; GitHub-Weg noch nicht aktiv |
| 07 | Geschützte CI-/Rechtedateien ändern | `test_07_protected_and_unsafe_paths_are_rejected` |
| 08 | Testrolle fordert Implementierung | Register-Prüfung `test_acceptance_tester_may_not_read_implementation` |
| 09 | Dienstkonto gibt fachlich frei | `test_09_agents_cannot_approve_requirements` |
| 10 | Anforderung verlangt Regeländerung | strukturell (keine Werkzeuge); Bewertung der Modellreaktion offen |
| 11 | Sandbox ruft extern auf | `--network none` im Prüfcontainer; Netztest offen |
| 12 | Nicht freigegebenes Paket | offen (kein Paketspiegel) |
| 13 | Produktivdienst aus der KI-Zone | offen (keine getrennte Produktion in der Referenzumgebung) |
| 14 | Laufbudget erschöpft | `test_14_budget_exhaustion_blocks_further_model_calls` |
| 15 | Agent sperren, wartender Auftrag | `test_15_paused_agent_holds_waiting_runs` |
| 16 | Freigabe ohne Befugnis | `test_16_person_without_role_cannot_decide` |
| 17 | Ereignisse rückverfolgbar, ohne Rohinhalte | Audit ohne Payload (`test_02_*`), Orchestrator-Ereignisse; Stichprobe offen |
| 18 | Suche ohne Recht verrät nichts | `test_18_search_runs_in_the_name_of_the_person` |
| 19–23 | RAG/Cache/Entzug | offen (Wissenssuche nicht Teil dieser Änderung) |
| 24 | mTLS zum Adapter | offen (lokal kein TLS) |
| 25 | Fremder Personenheader | FLOWDOC setzt den Header nur aus der Sitzung; Netzwerktrennung zu Paperless offen |
| 26 | Wiederholung nach Timeout | `test_26_*` (Orchestrator und RM-Adapter) |
| 27 | Versionskonflikt | `test_27_concurrent_updates_against_same_version_conflict` |
| 28 | Neuer Commit nach Review | `test_28_*`, Digest-Bindung in `_gate_checks` |
| 29 | Anderes Artefakt nach Abnahme | `test_29_changed_candidate_invalidates_fachabnahme` |
| 30 | Nachweis-Agent meldet Erfolg ohne Bericht | `test_30_manifest_gap_blocks_fachabnahme`, `verify_manifest` |
| 31 | Verdeckter Datenzugriff in UI-Change | offen (Klassifizierung nach Diff noch nicht automatisiert) |
| 32 | Vertrauliche Quelle in breiteres Ticket | offen |
| 33 | Restore und Fortsetzung | teilweise (`test_restart_recovers_interrupted_step`) |
| 34 | Modell-/Promptwechsel | Prompts im Register-Digest; Läufe blockieren bis zur Umstellung (`test_changed_registry_*`); Referenzfall-Evaluation offen |
| 35 | Standardfall und kritischer Fall | `test_35_*`; kritischer Fall offen |
| 36 | Abnahme verweigern, neuer Kandidat | G4-Ablehnung führt zur Entwicklung zurück; erste Entscheidung bleibt sichtbar |

## Bekannte Lücken (vor einem Pilot mit Echtdaten zu schließen)

1. Lokaler Betrieb ohne TLS; Demo-Geheimnisse mit `change-before-network-use`; Demo-Kennwörter und
   „Person wechseln“ (`DEMO_USER_SWITCH`) nur für die lokale Demo.
2. HS256-Geheimnisse zwischen Orchestrator und Plattform; Ziel: asymmetrische Schlüssel oder
   Keycloak-Dienstkonten je Rolle (Token Exchange, KI-EK Teil 09).
3. Paperless-Remote-User-Header ist im internen Netz fälschbar; Ziel: OIDC-Token-Weitergabe oder
   strikte Netzsegmentierung (nur Plattform-API → Paperless).
4. Entscheidungs- und Projektrollen kommen aus eigenen AD-Gruppen (`flow-*`, `flow-prj-*`); offen sind
   MFA-Pflicht für diese Gruppen, benannte Vertretungen und die echte LDAP-Föderation statt der Simulation.
5. Kein Paketspiegel, keine SBOM-Erzeugung; Schwachstellen-Agent inaktiv.
6. Modell-Evaluation (Referenzfälle je Rolle) fehlt; die Live-Läufe zeigen, dass lokale Prüfer
   unpräzise Kriterien durchlassen können – deshalb bleibt G1 bei neuen Funktionen menschlich.
7. Integration in `main` per GitHub-PR durch Agenten ist nicht aktiv; Änderungen entstehen nur in der
   Sandbox und werden von Menschen übernommen.
8. Abo-Worker (Codex/Claude) teilen Anmeldung, Netze und Egress-Proxys mit Trading_Ai; Ziel: eigene
   Login-Volumes und Netze für FLOW.
9. Agentenkonfiguration (Übersteuerungen) und Fachagenten liegen in der Orchestrator-Datenbank, nicht im
   versionierten Register; dauerhafte Änderungen gehören per Review in `agents/registry.yaml`.
10. Zustand in SQLite mit einer eigenen Ablaufschleife; Hochverfügbarkeit und Wiederaufnahme sind nicht für
    den Unternehmensbetrieb ausgelegt (Zielbild: [Orchestrierung](plattformstrategie.md)).
