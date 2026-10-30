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
    ai_mode: str = os.getenv("AI_MODE", "deterministic")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    ollama_timeout_seconds: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    erpnext_base_url: str = os.getenv("ERPNEXT_BASE_URL", "http://erpnext-frontend:8080")
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
    paperless_api_token: str = os.getenv("PAPERLESS_API_TOKEN", "")


settings = Settings()
