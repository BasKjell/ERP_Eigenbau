from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass

from .config import Settings


@dataclass
class IntegrationStatus:
    name: str
    mode: str
    configured: bool
    reachable: bool
    url: str
    detail: str


def integration_status(settings: Settings) -> list[dict[str, object]]:
    integrations = [
        _probe(
            "ERPNext",
            settings.erpnext_base_url,
            bool(settings.erpnext_api_key and settings.erpnext_api_secret),
            "/api/method/ping",
        ),
        _probe(
            "Paperless-ngx",
            settings.paperless_base_url,
            bool(settings.paperless_api_token),
            "/api/",
        ),
    ]
    return [asdict(item) for item in integrations]


def paperless_search(query: str, settings: Settings) -> dict[str, object]:
    if not settings.paperless_api_token:
        return {"mode": "simulated", "query": query, "results": []}
    url = f"{settings.paperless_base_url.rstrip('/')}/api/documents/?query={query}"
    request = urllib.request.Request(
        url, headers={"Authorization": f"Token {settings.paperless_api_token}"}
    )
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            return {"mode": "live", **json.load(response)}
    except (OSError, ValueError, urllib.error.URLError) as exc:
        return {"mode": "error", "detail": str(exc), "results": []}


def _probe(name: str, base_url: str, configured: bool, path: str) -> IntegrationStatus:
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}{path}", timeout=1.5) as response:
            reachable = response.status < 500
    except (OSError, urllib.error.URLError):
        reachable = False
    return IntegrationStatus(
        name=name,
        mode="live" if configured else "demo",
        configured=configured,
        reachable=reachable,
        url=base_url,
        detail="API verbunden" if reachable else "Demo-Adapter aktiv",
    )
