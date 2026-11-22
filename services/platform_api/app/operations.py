from __future__ import annotations

from typing import Any

from .config import Settings
from .integrations import integration_status
from .store import ScenarioStore


def readiness_report(store: ScenarioStore, settings: Settings) -> dict[str, Any]:
    """Check local state, referenced documents and optional external dependencies."""
    checks: list[dict[str, Any]] = []
    state: dict[str, Any] | None = None

    try:
        state = store.get()
        required_domains = {"order", "process", "documents", "mes"}
        missing_domains = sorted(required_domains - set(state))
        if missing_domains:
            raise ValueError(f"Fehlende Domaenen: {', '.join(missing_domains)}")
        checks.append(
            {
                "name": "state-store",
                "required": True,
                "ok": True,
                "detail": "Szenariodaten sind lesbar",
            }
        )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        checks.append(
            {
                "name": "state-store",
                "required": True,
                "ok": False,
                "detail": f"Szenariodaten nicht lesbar: {exc}",
            }
        )

    declared_documents = state.get("documents", []) if state else []
    missing_documents = sorted(
        str(document.get("filename", "<ohne Dateiname>"))
        for document in declared_documents
        if not (settings.document_dir / str(document.get("filename", ""))).is_file()
    )
    checks.append(
        {
            "name": "documents",
            "required": True,
            "ok": bool(declared_documents) and not missing_documents,
            "detail": (
                f"{len(declared_documents)} referenzierte Dokumente vorhanden"
                if declared_documents and not missing_documents
                else "Fehlende Dokumente: " + ", ".join(missing_documents)
                if missing_documents
                else "Keine Dokumente deklariert"
            ),
        }
    )

    integrations = integration_status(settings)
    integrations_ok = all(
        bool(item["configured"]) and bool(item["reachable"])
        for item in integrations
    )
    checks.append(
        {
            "name": "external-integrations",
            "required": settings.readiness_require_integrations,
            "ok": integrations_ok,
            "detail": ", ".join(
                f"{item['name']}: "
                f"{'verbunden' if item['reachable'] else 'nicht erreichbar'}"
                for item in integrations
            ),
        }
    )

    ready = all(check["ok"] for check in checks if check["required"])
    return {
        "status": "ready" if ready else "not_ready",
        "ready": ready,
        "checks": checks,
    }
