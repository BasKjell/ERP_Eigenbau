# Rückmeldung zum Review „FLOWAGENTS Sicherheit und Rechte“ (Basis 879043a, Head d9b7fa1)

Stand: 2026-11-25 · Bearbeitung: Claude · Freigabe und Merge: Codex/Bas

Die Befunde A1–A6 und B1–B5 sind behoben. Der Text von B5 lag nur abgeschnitten vor („Ein
AD-Rechteentzug kann bis zum Ende der Portalsitz…“); die Behebung folgt den genannten Fundstellen.
Weitere Befunde nach B5 sind hier nicht bekannt.

## Die drei wichtigsten Regressionstests

| Nr. | Anforderung aus dem Review | Test |
|---|---|---|
| 1 | Projektfremder PO erhält beim erneuten Start weder Laufdaten noch Abhängigkeiten | `tests/test_review_hardening.py::test_foreign_po_gets_neither_run_nor_dependency_information` |
| 2 | Vor einer Registeränderung geöffnete G4/G5-Entscheidung löst weder Übernahme noch Abschluss aus | `…::test_gate_decision_opened_before_a_registry_change_cannot_adopt_or_finish[G4]` und `[G5]` |
| 3 | Grüner CI-Lauf genügt an G3 nicht ohne Ergebnis je vorgeschriebenem Integrationstest am Kandidaten | `…::test_green_ci_without_case_results_does_not_pass_g3` |

Alle Pfade relativ zu `services/agent_orchestrator/`.

## A · Ablauf und Gates

| Befund | Behebung | Code | Tests |
|---|---|---|---|
| A1 Einstufung | Ohne Projektklasse bleibt `neue_funktion`; `criticality=K1` allein schwächt nicht mehr ab. Ausdrückliche Änderungsklasse wird als `change_class_explicit` gespeichert und an Arbeitspakete vererbt; Paket-Kritikalität ist mindestens die des Projekts. | `engine.py` `_classify`, `_validated_auftrag`, `start_package`, `_strictest` | `test_classification_without_partial_and_full` (7 Fälle), `test_explicitly_critical_l_project_passes_strictness_to_its_packages`, `test_package_cannot_lower_the_project_criticality` |
| A2 Registerbindung | Läufe tragen eine stabile Schritt-ID (`runs.step_id`), Entscheidungen den Registerstand (`decisions.registry_digest`). Eine Entscheidung unter altem Regelstand oder an einem anderen Schritt verfällt und blockiert den Lauf; die Neubewertung rechnet den Index über die Schritt-ID um (fail closed, wenn der Schritt fehlt). Offene Altaufträge werden beim Start migriert. | `store.py` `MIGRATIONS`; `engine.py` `decide`, `_rebind_index`, `_current_step_id`, `_migrate_step_ids`, `_update_run`, `_open_decision` | Regression 2, `test_open_legacy_runs_get_a_stable_step_id_on_start`, `test_rebinding_fails_closed_when_the_step_no_longer_exists`, bestehend `test_changed_registry_blocks_running_run_until_a_human_rebinds_it` |
| A3 Integrationstests | Der Prüfjob liefert die vollständige Ausgabe (`CheckResult.output`, `pytest -rA`); je Fall-ID wird das Ergebnis am Kandidaten-Digest gespeichert (`integration.cases`). G3 und Manifest verlangen je Fall ein gültiges Baseline-Kriterium (`covers`) und „bestanden“. Akzeptanztests zählen nur mit bekanntem Kriterium. Für L: EP1 verlangt ein Integrationspaket; es durchläuft den Schritt `integrationstests` (`when.flag: integration_required`); ohne fertiges Integrationspaket ist ein Projekt nicht abgeschlossen (`nachweis_offen`). | `engine.py` `_check_step`, `_integration_gaps`, `verify_manifest`, `_case_results`, `_criteria`, `project_summary`; `sandbox.py`; `registry.py` `Step.applies`; `agents/workflow.yaml`; Entwicklung liest `integrationstests` | Regression 3, `test_m_run_with_named_case_tests_passes_g3`, `test_case_results_need_an_explicit_pass_per_id`, `test_integration_case_must_cover_a_valid_baseline_criterion`, `test_manifest_ignores_acceptance_tests_with_unknown_criteria`, `test_ep1_for_l_needs_an_integration_package`, `test_l_project_needs_the_integration_package_before_it_counts_as_done` |
| A4 EP1 | EP1 erkennt Zyklen und prüft Paketbereiche gegen die Bereiche des Projekts. Beim Paketstart wird ein genehmigter Bereich nicht ersetzt, nur ein offen gelassener ergänzt (und gegen das Projekt geprüft). | `engine.py` `_gate_checks` (EP1), `_cycles`, `_project_scope_set`, `start_package` | `test_cycles_are_detected`, `test_ep1_rejects_cyclic_dependencies`, `test_ep1_checks_scopes_against_the_project_not_the_global_list`, `test_approved_package_scope_cannot_be_replaced_at_start` |
| A5 Atomarität | Paketlauf anlegen und binden in einer Transaktion (`create_package_run`, bindet einen verwaisten Lauf statt ihn zu doppeln). EP1-Abschluss und Projektanlage in einer Transaktion (`complete_with_project`, auch für Katalogprojekte). `recover()` plant wartende Läufe ohne offene Entscheidung neu ein. | `store.py`; `engine.py` `_on_project_defined`, `seed_projects`, `recover` | `test_package_run_left_without_binding_is_bound_instead_of_duplicated`, `test_ep1_completion_and_project_creation_are_one_transaction` |
| A6 Abschlussart | `runs.completion`: `produktion` (G5), `projektplanung` (EP1/L), `katalog`, `ende`. `runs_done` zählt nur Produktion; Planung und Katalog getrennt. Katalog- und Planungsläufe ohne Release-Manifestprüfung. EP1 löst keine Übernahme aus. | `engine.py` `_completion`, `overview` (metrics), `run_detail`, `_run_summary` | `test_completion_kinds_are_kept_apart` |

## B · Projektrechte und Identität

| Befund | Behebung | Code | Tests |
|---|---|---|---|
| B1 Auskunft vor Recht | `start_package` prüft das Projektrecht vor jeder Auskunft und Zustandsänderung. Einzelabbruch nur mit Projektrecht; projektübergreifend nur `CROSS_PROJECT_OPERATIONS` (platform-admin). | `engine.py` `start_package`, `control` | Regression 1, `test_cancel_needs_the_project_right_or_cross_project_operations`, `test_platform_operations_may_cancel_across_projects` |
| B2 Leck über Nebenansichten | Die Übersicht liefert `access.runs` (Projektbindung jedes referenzierten Laufs). Die Plattform bildet Läufe, Entscheidungen, Ereignisse, `usage.by_run`, `agents[].current/last` und Kennzahlen aus derselben berechtigten Laufmenge; unbekannte Läufe sind verborgen. FLOWAI (Dienstrecht ohne Person) sieht nur ungebundene Altaufträge. | `engine.py` `overview`, `_access_map`; `platform_api/app/flow_routes.py` `visible_overview`, `internal_status` | `test_overview_names_the_project_binding_of_every_referenced_run`; Plattform: `test_foreign_run_details_do_not_leak_through_agents_usage_or_older_events`, `test_flowai_service_status_contains_no_project_runs` |
| B3 Altauftragsregel | Aufträge unter einem Katalog werden als `catalog_bound` gekennzeichnet (Pakete erben). Gebundene Läufe bleiben geschützt, wenn Katalogdatei, Projekte oder Projektcode fehlen; offen sind nur nie gebundene Altaufträge. Details prüft der Orchestrator mit der Identität der anfragenden Person. | `engine.py` `auftrag_access`, `can_see_run`, `run_detail(user)`; `sync.py` (detail mit Person); `flow_routes.py` `project_visible`, `agents_run` | `test_bound_runs_stay_protected_when_the_catalog_loses_the_project`, `test_true_legacy_runs_stay_open`, `test_run_detail_needs_the_project_right`, `test_sync.py` (b0); Plattform: `test_bound_runs_stay_protected_when_the_catalog_loses_the_project` |
| B5 Rechteentzug wirkt erst am Sitzungsende | Die Portalsitzung speichert Refresh-Token und Zeitpunkt der Rollenprüfung. Rollen gelten höchstens `AUTH_ROLE_REFRESH_SECONDS` (300 s) ungeprüft; danach lädt die Middleware sie über Keycloak (Refresh-Token, userinfo) neu und setzt das Cookie neu, auch bei 403. Gesperrtes Konto, beendete Keycloak-Sitzung, andere Person, Keycloak nicht erreichbar oder Altsitzung ohne Refresh-Token: Sitzung endet (fail closed, 401). `AUTH_SESSION_MINUTES` bleibt die SSO-Bequemlichkeit, nicht mehr die Rechtegültigkeit. | `platform_api/app/auth.py` `refresh_session`, `_roles_stale`, `_user_from`; `main.py` `enforce_oidc`; `config.py`; `compose.yaml` | `test_auth.py::test_ad_role_revocation_takes_effect_at_the_next_role_refresh`, `test_stale_session_ends_when_roles_cannot_be_confirmed` (4 Fälle) |
| B4 Demo und Bindung | Compose bindet die Plattform an `${PLATFORM_BIND:-127.0.0.1}` und setzt standardmäßig `AUTH_MODE=oidc`. Die Demo ohne Anmeldung muss ausdrücklich gewählt werden; die Plattform startet nicht mit `AUTH_MODE=demo` an einer Nicht-Loopback-Adresse oder mit unbekanntem Modus. Anonyme Plattformrechte nur bei `AUTH_MODE=demo`. | `compose.yaml`; `platform_api/app/config.py` `check_auth_exposure`; `main.py`; `flow_routes.py` `person` | `test_demo_without_login_only_on_loopback`, `test_compose_binds_the_platform_to_loopback_and_defaults_to_oidc` |

## Hinweise

- Registeränderung durch diesen Commit (`workflow.yaml`, Entwicklung liest `integrationstests`): offene
  Läufe werden einmal blockiert und vom Tech Lead neu bewertet – genau der Ablauf aus A2.
