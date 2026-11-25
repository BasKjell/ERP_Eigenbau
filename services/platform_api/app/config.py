from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    data_file: Path = Path(os.getenv("DEMO_DATA_FILE", "/data/scenario.json"))
    seed_file: Path = Path(os.getenv("DEMO_SEED_FILE", "/app/seed/scenario.json"))
    document_dir: Path = Path(os.getenv("DOCUMENT_DIR", "/app/documents"))
    documentation_dir: Path = Path(os.getenv("DOCUMENTATION_DIR", "/docs"))
    documentation_public_url: str = os.getenv(
        "DOCUMENTATION_PUBLIC_URL", "http://localhost:8001"
    )
    ai_mode: str = os.getenv("AI_MODE", "deterministic")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    ollama_timeout_seconds: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    erpnext_base_url: str = os.getenv("ERPNEXT_BASE_URL", "http://erpnext-frontend:8080")
    erpnext_public_url: str = os.getenv("ERPNEXT_PUBLIC_URL", "http://localhost:8081")
    erpnext_api_key: str = os.getenv("ERPNEXT_API_KEY", "")
    erpnext_api_secret: str = os.getenv("ERPNEXT_API_SECRET", "")
    erpnext_username: str = os.getenv("ERPNEXT_USERNAME", "")
    erpnext_password: str = os.getenv("ERPNEXT_PASSWORD", "")
    mcp_write_enabled: bool = _env_bool("MCP_WRITE_ENABLED")
    mcp_max_write_records: int = int(os.getenv("MCP_MAX_WRITE_RECORDS", "100"))
    mcp_audit_file: Path = Path(
        os.getenv("MCP_AUDIT_FILE", "/data/mcp-write-audit.jsonl")
    )
    mcp_default_company: str = os.getenv(
        "MCP_DEFAULT_COMPANY", "Open Manufacturing Demo GmbH"
    )
    paperless_base_url: str = os.getenv(
        "PAPERLESS_BASE_URL", "http://paperless-webserver:8000"
    )
    paperless_public_url: str = os.getenv(
        "PAPERLESS_PUBLIC_URL", "http://localhost:8010"
    )
    paperless_api_token: str = os.getenv("PAPERLESS_API_TOKEN", "")
    paperless_username: str = os.getenv("PAPERLESS_USERNAME", "")
    paperless_password: str = os.getenv("PAPERLESS_PASSWORD", "")
    knowledge_database_url: str = os.getenv(
        "KNOWLEDGE_DATABASE_URL",
        "postgresql://platform:platform-demo-change-me@demo-db:5432/platform_demo",
    )
    dms_embedding_dimensions: int = int(
        os.getenv("DMS_EMBEDDING_DIMENSIONS", "768")
    )
    dms_embedding_model: str = os.getenv(
        "DMS_EMBEDDING_MODEL", "flow-hash-de-768-v1"
    )
    redmine_base_url: str = os.getenv("REDMINE_BASE_URL", "http://redmine:3000")
    redmine_api_key: str = os.getenv("REDMINE_API_KEY", "")
    redmine_public_url: str = os.getenv(
        "REDMINE_PUBLIC_URL", "http://localhost:8011"
    )
    open_webui_public_url: str = os.getenv(
        "OPEN_WEBUI_PUBLIC_URL", "http://localhost:3001"
    )
    prometheus_public_url: str = os.getenv(
        "PROMETHEUS_PUBLIC_URL", "http://localhost:9090"
    )
    grafana_public_url: str = os.getenv(
        "GRAFANA_PUBLIC_URL", "http://localhost:3000"
    )
    readiness_require_integrations: bool = _env_bool(
        "READINESS_REQUIRE_INTEGRATIONS"
    )
    auth_mode: str = os.getenv("AUTH_MODE", "demo").strip().casefold()
    # Adresse, an die Compose den Port der Plattform bindet. Der Demo-Modus ohne Anmeldung ist nur an
    # Loopback zulässig; gemeinsam erreichbare Instanzen setzen OIDC voraus (siehe check_auth_exposure).
    platform_bind: str = os.getenv("PLATFORM_BIND", "127.0.0.1").strip()
    auth_session_secret: str = os.getenv(
        "AUTH_SESSION_SECRET", "local-session-secret-change-before-network-use"
    )
    auth_session_minutes: int = int(os.getenv("AUTH_SESSION_MINUTES", "480"))
    # Rollen der Sitzung höchstens so lange ungeprüft: danach Refresh bei Keycloak (AD-Rechteentzug wirkt).
    auth_role_refresh_seconds: int = int(os.getenv("AUTH_ROLE_REFRESH_SECONDS", "300"))
    auth_cookie_secure: bool = _env_bool("AUTH_COOKIE_SECURE")
    demo_admin_api_token: str = os.getenv("PLATFORM_DEMO_ADMIN_TOKEN", "")
    # Benutzerwechsel in der Demo: Kopfzeile listet die Demo-Konten; der Wechsel meldet über Keycloak
    # neu an (prompt=login), die Rechte kommen weiter aus den AD-Gruppen. Vor jeder Netzwerknutzung aus.
    demo_user_switch: bool = _env_bool("DEMO_USER_SWITCH")
    reporting_api_token: str = os.getenv(
        "REPORTING_API_TOKEN", "local-reporting-token-change-before-network-use"
    )
    platform_public_url: str = os.getenv(
        "PLATFORM_PUBLIC_URL", "http://localhost:8088"
    )
    oidc_client_id: str = os.getenv("OIDC_CLIENT_ID", "platform-portal")
    oidc_external_issuer: str = os.getenv(
        "OIDC_EXTERNAL_ISSUER", "http://localhost:8082/realms/open-manufacturing"
    )
    oidc_internal_issuer: str = os.getenv(
        "OIDC_INTERNAL_ISSUER", "http://keycloak:8080/realms/open-manufacturing"
    )


settings = Settings()


LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


def check_auth_exposure(current: Settings) -> None:
    """Fail closed: ohne Anmeldung (AUTH_MODE=demo) erhält jede Anfrage Plattformrechte. Das ist nur für eine
    lokale Demo an Loopback vertretbar. Unbekannte Modi und Demo an einer erreichbaren Adresse starten nicht."""
    if current.auth_mode not in {"oidc", "demo"}:
        raise RuntimeError(f"AUTH_MODE={current.auth_mode!r} unbekannt (oidc oder demo)")
    if current.auth_mode == "demo" and current.platform_bind not in LOOPBACK:
        raise RuntimeError(f"AUTH_MODE=demo ist nur an Loopback zulässig, nicht an {current.platform_bind!r}; "
                           "für gemeinsam erreichbare Instanzen AUTH_MODE=oidc setzen")
