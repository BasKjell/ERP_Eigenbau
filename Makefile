.PHONY: help demo full seed-erp docs test lint validate stop reset logs ai webui mcp

help:
	@echo "ERP Eigenbau - verfuegbare Befehle"
	@echo "  make demo      Startet Portal, API, Datenbank und Wiki"
	@echo "  make full      Startet zusaetzlich ERPNext und Paperless-ngx"
	@echo "  make seed-erp  Legt den SCU-100-Demofall idempotent in ERPNext an"
	@echo "  make ai        Startet zusaetzlich Ollama (Modell separat laden)"
	@echo "  make webui     Startet Open WebUI fuer das Ollama-Modell auf dem Mac"
	@echo "  make mcp       Startet ERP-, DMS- und Wiki-MCP-Server"
	@echo "  make test      Fuehrt Python-Tests aus"
	@echo "  make validate  Prueft Compose und baut die Dokumentation"
	@echo "  make reset     Setzt den Demo-Datensatz zurueck"
	@echo "  make stop      Stoppt alle Profile"

demo:
	docker compose up -d --build demo-db platform-api platform-mcp docs

full:
	docker compose --profile full --profile webui up -d --build

seed-erp:
	docker compose --profile full run --rm erpnext-seed

ai:
	docker compose --profile ai up -d --build

webui:
	docker compose --profile webui up -d open-webui

mcp:
	docker compose --profile full up -d --build platform-mcp dms-mcp knowledge-mcp

docs:
	docker compose up docs

test:
	docker build -t erp-eigenbau-api-test --target test services/platform_api

lint:
	docker build -t erp-eigenbau-api-test --target test services/platform_api

validate:
	docker compose --profile full --profile ai --profile webui --profile ops --profile iam config --quiet
	docker run --rm -v "$(CURDIR):/docs" squidfunk/mkdocs-material:9.8.0 build --strict

reset:
	curl --fail --silent --show-error -X POST http://localhost:$${DEMO_API_PORT:-8088}/api/demo/reset

logs:
	docker compose logs -f --tail=150 platform-api

stop:
	docker compose --profile full --profile ai --profile webui --profile ops --profile iam down
