from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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
    paperless_base_url: str = os.getenv(
        "PAPERLESS_BASE_URL", "http://paperless-webserver:8000"
    )
    paperless_api_token: str = os.getenv("PAPERLESS_API_TOKEN", "")


settings = Settings()
