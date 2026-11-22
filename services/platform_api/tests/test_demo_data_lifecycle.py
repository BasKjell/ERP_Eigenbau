from __future__ import annotations

from pathlib import Path

from app.auth import OidcAuth
from app.config import Settings
from app.store import ScenarioStore
from starlette.requests import Request

APP_ROOT = Path(__file__).resolve().parents[1]


def _request(path: str, token: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [(b"x-demo-admin-token", token.encode())],
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 1234),
            "scheme": "http",
        }
    )


def test_store_purge_removes_demo_domains_and_reset_restores_them(tmp_path: Path) -> None:
    seed = APP_ROOT / "seed/scenario.json"
    store = ScenarioStore(tmp_path / "scenario.json", seed)

    purged = store.purge()

    assert purged["scenario"]["data_status"] == "purged"
    assert purged["documents"] == []
    assert purged["projects"] == []
    assert purged["mes"]["jobs"] == []
    assert purged["hr"]["employees"] == []
    assert purged["iam"]["users"] == []
    assert purged["desksharing"]["desks"] == []
    assert purged["work"]["requirements"] == []

    restored = store.reset()

    assert restored["documents"]
    assert restored["mes"]["jobs"]
    assert restored["iam"]["users"]
    assert restored["desksharing"]["desks"]
    assert restored["work"]["requirements"]


def test_demo_service_token_is_restricted_to_lifecycle_endpoints() -> None:
    auth = OidcAuth(
        Settings(auth_mode="oidc", demo_admin_api_token="demo-lifecycle-secret")
    )

    identity = auth.current_user(_request("/api/demo/purge", "demo-lifecycle-secret"))

    assert identity is not None
    assert identity["roles"] == ["platform-admin"]
    assert auth.current_user(_request("/api/demo/reset", "wrong")) is None
    assert auth.current_user(_request("/api/hr/reset", "demo-lifecycle-secret")) is None
