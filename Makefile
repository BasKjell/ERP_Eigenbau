.PHONY: agents-smoke requirements-check requirements-sync agents-up agents-down agents-restart agents-status agents-logs agents-test agents-check agents-sandbox-image help demo full work sso sso-all seed-erp seed-dms seed-dms-project dms-vector-index demo-data-setup demo-data-delete demo-data-delete-preview dms-dashboard management-dashboard docs test test-dms-reporting test-management-reporting test-integration audit-links check lint validate stop reset logs ai ai-gateway webui mcp

help:
	@echo "ERP Eigenbau - verfuegbare Befehle"
	@echo "  make demo      Startet Portal, API, Datenbank und Wiki"
	@echo "  make full      Startet zusaetzlich ERPNext und Paperless-ngx"
	@echo "  make work      Startet FLOWWORK mit Redmine und Demo-Projekten"
	@echo "  make sso       Startet Keycloak-SSO fuer Plattform und Grafana"
	@echo "  make sso-all   Startet den gesamten lokalen Stack mit den vorhandenen SSO-Adaptern"
	@echo "  make seed-erp  Legt den SCU-100-Demofall idempotent in ERPNext an"
	@echo "  make seed-dms  Legt Rollen, Projekte und Freigaben in Paperless an"
	@echo "  make seed-dms-project TEMPLATE=... CODE=... NAME=...  Legt ein DMS-Projekt an"
	@echo "  make demo-data-setup  Fuellt Plattform, IAM, ERP, DMS und Redmine ueber APIs"
	@echo "  make demo-data-delete-preview  Zeigt alle API-Loeschungen ohne Aenderung"
	@echo "  make demo-data-delete CONFIRM=DELETE-DEMO-DATA  Loescht nur deklarierte Demodaten"
	@echo "  make dms-dashboard  Startet das Dokumenten-Termin-Dashboard in Grafana"
	@echo "  make management-dashboard  Startet FLOWFIN-Reporting und Management-Dashboards"
	@echo "  make ai        Startet zusaetzlich Ollama (Modell separat laden)"
	@echo "  make ai-gateway  Startet FLOWGATE mit Keycloak-SSO und lokalem Qwen"
	@echo "  make webui     Startet FLOWAI ueber FLOWGATE fuer das Qwen-Modell auf dem Mac"
	@echo "  make mcp       Startet ERP-, DMS- und Wiki-MCP-Server"
	@echo "  make dms-vector-index  Indiziert Paperless-OCR lokal in pgvector"
	@echo "  make agents-up        Startet den FLOWAGENTS-Orchestrator (Host-Dienst, 127.0.0.1:8095)"
	@echo "  make agents-status    Zeigt Laeufe, Entscheidungen und Agentenzustand"
	@echo "  make agents-test      Prueft Agentenregister, Orchestrator und Grenzen"
	@echo "  make agents-smoke     Prueft die laufende Kette (Orchestrator, Portal, FLOWGATE, Sandbox)"
	@echo "  make agents-sandbox-image  Baut das Offline-Pruefimage fuer die Integrationspruefung"
	@echo "  make requirements-check  Prueft requirements/catalog.yaml und die Testverweise"
	@echo "  make requirements-sync   Uebertraegt den Requirements-Katalog nach FLOWWORK"
	@echo "  make test      Fuehrt Python-Tests aus"
	@echo "  make test-dms-reporting  Prueft Termin-View und DB-Berechtigungen"
	@echo "  make test-management-reporting  Prueft Management-Views und DB-Berechtigungen"
	@echo "  make test-integration  Prueft API, ERP-/DMS-Adapter, MES, HR, Desksharing, Recruiting, Payroll, MCP und Wiki"
	@echo "  make audit-links  Prueft alle zentralen Live- und Management-Demo-Links"
	@echo "  make check     Fuehrt Tests, Integration und statische Pruefungen aus"
	@echo "  make validate  Prueft Compose und baut die Dokumentation"
	@echo "  make reset     Setzt den Demo-Datensatz zurueck"
	@echo "  make stop      Stoppt alle Profile"

demo:
	AUTH_MODE=oidc docker compose --profile iam up -d --build demo-db platform-api platform-mcp docs docs-shell keycloak keycloak-shell keycloak-sync

full:
	AUTH_MODE=oidc GRAFANA_OIDC_ENABLED=true GRAFANA_OIDC_AUTO_LOGIN=true docker compose --profile full --profile webui --profile ops --profile iam up -d --build

work:
	AUTH_MODE=oidc REDMINE_API_KEY=$${REDMINE_API_KEY:-f6ab4d1c02fe9a7b3e5d8c4f1a6b9e2c7d0f3a5b} docker compose --profile work --profile iam up -d --build demo-db platform-api docs docs-shell redmine-db redmine redmine-shell redmine-seed keycloak keycloak-shell keycloak-sync

sso:
	AUTH_MODE=oidc GRAFANA_OIDC_ENABLED=true GRAFANA_OIDC_AUTO_LOGIN=true docker compose --profile iam --profile ops up -d --build keycloak keycloak-shell keycloak-sync platform-api grafana grafana-shell

sso-all:
	AUTH_MODE=oidc GRAFANA_OIDC_ENABLED=true GRAFANA_OIDC_AUTO_LOGIN=true docker compose --profile full --profile work --profile ai --profile webui --profile ops --profile iam up -d --build

seed-erp:
	docker compose --profile full run --rm erpnext-seed

seed-dms:
	docker compose --profile full run --rm paperless-governance-seed
	docker compose --profile full run --rm paperless-iam-seed
	docker compose --profile full run --rm --no-deps paperless-reporting-seed

dms-vector-index:
	docker compose --profile full run --rm dms-vector-seed

seed-dms-project:
	@test -n "$(TEMPLATE)" -a -n "$(CODE)" -a -n "$(NAME)" || (echo "TEMPLATE, CODE und NAME sind erforderlich" && exit 2)
	docker compose --profile full run --rm paperless-governance-seed \
		--config /config/governance.json \
		--project-template "$(TEMPLATE)" \
		--project-code "$(CODE)" \
		--project-name "$(NAME)"

demo-data-setup:
	python3 scripts/setup_demo_data.py

demo-data-delete-preview:
	python3 scripts/delete_demo_data.py --dry-run

demo-data-delete:
	python3 scripts/delete_demo_data.py --confirm "$(CONFIRM)"

dms-dashboard:
	docker compose --profile full run --rm paperless-reporting-seed
	docker compose --profile ops up -d prometheus prometheus-shell grafana grafana-shell

management-dashboard:
	docker compose --profile ops run --rm management-reporting-seed
	docker compose --profile ops up -d prometheus prometheus-shell grafana grafana-shell

ai:
	docker compose --profile ai up -d --build

ai-gateway:
	AUTH_MODE=oidc docker compose --profile iam --profile ai-gateway up -d keycloak keycloak-shell keycloak-sync agentgateway agentgateway-shell

webui:
	AUTH_MODE=oidc docker compose --profile iam --profile webui up -d keycloak keycloak-shell keycloak-sync agentgateway agentgateway-shell open-webui open-webui-shell

mcp:
	docker compose --profile full up -d --build platform-mcp dms-mcp knowledge-mcp

docs:
	AUTH_MODE=oidc docker compose --profile iam up docs docs-shell keycloak keycloak-shell keycloak-sync

test:
	docker build --build-context repo=. -t erp-eigenbau-api-test --target test services/platform_api
	python3 scripts/test_demo_data_api.py

test-integration:
	./scripts/run_integration_tests.sh

audit-links:
	python3 scripts/audit_live_links.py

test-dms-reporting:
	./scripts/test_dms_reporting.sh

test-management-reporting:
	./scripts/test_management_reporting.sh

check: test agents-test requirements-check validate test-dms-reporting test-management-reporting test-integration

lint:
	docker build --build-context repo=. -t erp-eigenbau-api-test --target test services/platform_api

validate:
	python3 scripts/generate_iam_demo.py --check
	python3 -m py_compile scripts/demo_data_api.py scripts/setup_demo_data.py scripts/delete_demo_data.py scripts/audit_live_links.py scripts/validate_open_webui_config.py scripts/validate_app_shell.py deployment/keycloak/sync_keycloak.py deployment/paperless/sync_keycloak_users.py services/platform_api/app/iam_roles.py services/platform_api/app/dms_vector.py services/platform_api/app/dms_vector_index.py
	python3 scripts/validate_open_webui_config.py
	python3 scripts/validate_app_shell.py
	PYTHONPATH=services/platform_api python3 -m app.paperless_governance --config deployment/paperless/governance.json --validate-only
	jq empty deployment/paperless/governance.json deployment/erpnext/demo_api_records.json deployment/redmine/demo_api.json deployment/grafana/provisioning/dashboards/json/*.json
	docker compose -f compose.yaml -f compose.ci.yaml --profile full --profile ai --profile ai-gateway --profile webui --profile ops --profile iam --profile ci config --quiet
	docker run --rm -v "$(CURDIR):/docs" squidfunk/mkdocs-material:9.8.0 build --strict

reset:
	curl --fail --silent --show-error -X POST -H "X-Demo-Admin-Token: $${PLATFORM_DEMO_ADMIN_TOKEN:-local-demo-admin-token-change-before-network-use}" http://localhost:$${DEMO_API_PORT:-8088}/api/demo/reset

logs:
	docker compose logs -f --tail=150 platform-api

stop:
	docker compose --profile full --profile work --profile ai --profile ai-gateway --profile webui --profile ops --profile iam down

agents-sandbox-image:
	docker build -t flow-agents-sandbox:1 -f services/agent_orchestrator/sandbox.Dockerfile services

agents-up:
	./scripts/flow_agents.sh start

agents-down:
	./scripts/flow_agents.sh stop

agents-restart:
	./scripts/flow_agents.sh restart

agents-status:
	./scripts/flow_agents.sh status

agents-logs:
	./scripts/flow_agents.sh logs

agents-check:
	cd services/agent_orchestrator && ../../$(PYTHON) -m flowagents check-registry --repo-root ../..

agents-test:
	cd services/agent_orchestrator && ../../$(PYTHON) -m ruff check flowagents worker tests && ../../$(PYTHON) -m pytest -q tests

PYTHON ?= $(shell test -x .venv/bin/python && echo .venv/bin/python || echo python3)

requirements-check:
	PYTHONPATH=services/platform_api $(PYTHON) -m app.requirements_catalog check --catalog requirements/catalog.yaml --repo .

requirements-sync:
	docker compose exec -T platform-api python -m app.requirements_catalog sync --catalog /app/requirements/catalog.yaml

agents-smoke:
	python3 scripts/smoke_agents.py
