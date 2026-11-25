from __future__ import annotations

import json
import time
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from app import main as main_module
from app.auth import AuthError, OidcAuth
from app.config import Settings
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from starlette.requests import Request


def oidc_settings() -> Settings:
    return Settings(
        auth_mode="oidc",
        auth_session_secret="unit-test-session-secret",
        platform_public_url="http://testserver",
        oidc_external_issuer="http://keycloak.example/realms/open-manufacturing",
        oidc_internal_issuer="http://keycloak:8080/realms/open-manufacturing",
    )


def cookie_value(response: object, name: str) -> str:
    cookie = SimpleCookie()
    for header in response.headers.getlist("set-cookie"):
        cookie.load(header)
    return cookie[name].value


def request_with(query: str = "", cookie: str = "") -> Request:
    headers = [(b"cookie", cookie.encode())] if cookie else []
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/auth/callback",
            "query_string": query.encode(),
            "headers": headers,
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 1234),
        }
    )


def test_login_uses_authorization_code_pkce_and_safe_next() -> None:
    auth = OidcAuth(oidc_settings())
    response = auth.login("//evil.example")
    location = response.headers["location"]
    query = parse_qs(urlparse(location).query)
    assert query["response_type"] == ["code"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["client_id"] == ["platform-portal"]
    flow = auth._unsign(cookie_value(response, auth.FLOW_COOKIE))
    assert flow is not None
    assert flow["next"] == "/"
    assert len(flow["verifier"]) > 40


def test_callback_builds_signed_session_from_keycloak_userinfo(monkeypatch: object) -> None:
    auth = OidcAuth(oidc_settings())
    login = auth.login("/desksharing")
    flow_cookie = cookie_value(login, auth.FLOW_COOKIE)
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]

    monkeypatch.setattr(
        auth,
        "_form_request",
        lambda *_: {"access_token": "access", "id_token": "signed-id-token"},
    )
    monkeypatch.setattr(auth, "_validate_id_token", lambda *_: {"sub": "123"})
    monkeypatch.setattr(
        auth,
        "_json_request",
        lambda *_: {
            "sub": "123",
            "preferred_username": "demo01",
            "name": "Anna Schneider",
            "email": "demo01@example.invalid",
            "roles": ["desksharing-user", "sales-user"],
            "department": "Vertrieb",
            "desksharing_user_id": "USR-001",
        },
    )
    request = request_with(
        f"code=code-123&state={state}", f"{auth.FLOW_COOKIE}={flow_cookie}"
    )
    callback = auth.callback(request)
    assert callback.headers["location"] == "/desksharing"
    session_cookie = cookie_value(callback, auth.SESSION_COOKIE)
    current = auth.current_user(
        request_with(cookie=f"{auth.SESSION_COOKIE}={session_cookie}")
    )
    assert current is not None
    assert current["desksharing_user_id"] == "USR-001"
    assert "desksharing-user" in current["roles"]


def test_id_token_signature_audience_issuer_and_nonce_are_validated(
    monkeypatch: object,
) -> None:
    auth = OidcAuth(oidc_settings())
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": "unit-key", "use": "sig", "alg": "RS256"})
    monkeypatch.setattr(auth, "_urlopen_json", lambda *_: {"keys": [public_jwk]})
    now = int(time.time())
    token = jwt.encode(
        {
            "iss": auth.settings.oidc_external_issuer,
            "aud": auth.settings.oidc_client_id,
            "sub": "user-123",
            "iat": now,
            "exp": now + 300,
            "nonce": "expected-nonce",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "unit-key"},
    )

    assert auth._validate_id_token(token, "expected-nonce")["sub"] == "user-123"
    with pytest.raises(AuthError, match="Nonce"):
        auth._validate_id_token(token, "other-nonce")


def test_oidc_middleware_requires_login_and_enforces_roles(monkeypatch: object) -> None:
    auth = OidcAuth(oidc_settings())
    monkeypatch.setattr(main_module, "oidc_auth", auth)
    client = TestClient(main_module.app)

    assert client.get("/health").status_code == 200
    assert client.get("/api/desksharing/dashboard").status_code == 401
    page = client.get("/desksharing", follow_redirects=False)
    assert page.status_code in {302, 307}
    assert page.headers["location"].startswith("/auth/login")

    session = auth._sign(
        {
            "expires_at": 4_102_444_800, "roles_checked_at": 4_102_444_800,
            "user": {
                "username": "demo01",
                "roles": ["sales-user"],
                "desksharing_user_id": "USR-001",
            },
        }
    )
    forbidden = client.get(
        "/api/desksharing/dashboard",
        cookies={auth.SESSION_COOKIE: session},
    )
    assert forbidden.status_code == 403

    portal = client.get("/", cookies={auth.SESSION_COOKIE: session})
    assert portal.status_code == 200
    assert "Meine Anwendungen" in portal.text
    assert client.get("/management", cookies={auth.SESSION_COOKIE: session}).status_code == 403
    assert client.get("/work", cookies={auth.SESSION_COOKIE: session}).status_code == 403

    work_session = auth._sign(
        {
            "expires_at": 4_102_444_800, "roles_checked_at": 4_102_444_800,
            "user": {"username": "engineer", "roles": ["work-user"]},
        }
    )
    assert client.get("/work", cookies={auth.SESSION_COOKIE: work_session}).status_code == 200
    assert (
        client.get(
            "/api/work/dashboard", cookies={auth.SESSION_COOKIE: work_session}
        ).status_code
        == 200
    )

    management_session = auth._sign(
        {
            "expires_at": 4_102_444_800, "roles_checked_at": 4_102_444_800,
            "user": {"username": "manager", "roles": ["management-user"]},
        }
    )
    assert client.get(
        "/mes", cookies={auth.SESSION_COOKIE: management_session}
    ).status_code == 200
    assert client.get(
        "/api/mes/dashboard", cookies={auth.SESSION_COOKIE: management_session}
    ).status_code == 200
    assert client.get(
        "/hr", cookies={auth.SESSION_COOKIE: management_session}
    ).status_code == 200
    assert client.post(
        "/api/mes/reset", cookies={auth.SESSION_COOKIE: management_session}
    ).status_code == 403


def test_sso_proxy_requires_session_and_maps_identity_headers(monkeypatch: object) -> None:
    auth = OidcAuth(oidc_settings())
    monkeypatch.setattr(main_module, "oidc_auth", auth)
    client = TestClient(main_module.app)

    assert client.get("/auth/proxy?app_id=paperless").status_code == 401
    session = auth._sign(
        {
            "expires_at": 4_102_444_800, "roles_checked_at": 4_102_444_800,
            "user": {
                "username": "demo01",
                "name": "Anna Schneider",
                "email": "demo01@example.invalid",
                "roles": ["dms-user", "sales-user"],
                "department": "Vertrieb",
            },
        }
    )
    response = client.get(
        "/auth/proxy?app_id=paperless",
        cookies={auth.SESSION_COOKIE: session},
    )
    assert response.status_code == 204
    assert response.headers["x-flow-sso-user"] == "demo01"
    assert response.headers["x-flow-sso-email"] == "demo01@example.invalid"
    assert response.headers["x-flow-sso-app-role"] == "user"
    assert client.get(
        "/auth/proxy?app_id=open-webui",
        cookies={auth.SESSION_COOKIE: session},
    ).status_code == 403


def test_sso_app_return_is_allowlisted_and_role_checked(monkeypatch: object) -> None:
    auth = OidcAuth(oidc_settings())
    monkeypatch.setattr(main_module, "oidc_auth", auth)
    client = TestClient(main_module.app)
    session = auth._sign(
        {
            "expires_at": 4_102_444_800, "roles_checked_at": 4_102_444_800,
            "user": {"username": "demo01", "roles": ["dms-user"]},
        }
    )

    unknown = client.get("/auth/app-return?app_id=https://evil.example", follow_redirects=False)
    assert unknown.status_code == 404
    allowed = client.get(
        "/auth/app-return?app_id=paperless",
        cookies={auth.SESSION_COOKIE: session},
        follow_redirects=False,
    )
    assert allowed.status_code in {302, 307}
    assert allowed.headers["location"] == "http://localhost:8010"
    forbidden = client.get(
        "/auth/app-return?app_id=open-webui",
        cookies={auth.SESSION_COOKIE: session},
    )
    assert forbidden.status_code == 403


def test_ad_role_revocation_takes_effect_at_the_next_role_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    """Review B5: Rollen der Portalsitzung gelten höchstens AUTH_ROLE_REFRESH_SECONDS ungeprüft. Danach lädt die
    Plattform sie über das Refresh-Token neu; ein Entzug im AD wirkt damit nicht erst am Sitzungsende."""
    auth = OidcAuth(oidc_settings())
    monkeypatch.setattr(main_module, "oidc_auth", auth)
    client = TestClient(main_module.app)
    stale = int(time.time()) - auth.settings.auth_role_refresh_seconds - 1
    session = auth._sign({"expires_at": 4_102_444_800, "roles_checked_at": stale, "refresh_token": "rt-1",
                          "user": {"sub": "u-1", "username": "engineer", "roles": ["work-user"]}})
    calls: list[dict[str, str]] = []

    def token(url: str, values: dict[str, str]) -> dict[str, str]:
        calls.append(values)
        return {"access_token": "at-2", "refresh_token": "rt-2"}

    # Im AD wurde die Gruppe entzogen: Keycloak liefert work-user nicht mehr.
    monkeypatch.setattr(auth, "_form_request", token)
    monkeypatch.setattr(auth, "_json_request", lambda url, access: {"sub": "u-1", "preferred_username": "engineer",
                                                                     "roles": ["dms-user"]})
    response = client.get("/api/work/dashboard", cookies={auth.SESSION_COOKIE: session})
    assert response.status_code == 403, "entzogene Rolle wirkt sofort nach dem Refresh"
    assert calls[0]["grant_type"] == "refresh_token" and calls[0]["refresh_token"] == "rt-1"
    renewed = auth._unsign(response.cookies.get(auth.SESSION_COOKIE) or "")
    assert renewed["user"]["roles"] == ["dms-user"] and renewed["refresh_token"] == "rt-2"
    assert renewed["roles_checked_at"] >= int(time.time()) - 5


@pytest.mark.parametrize("failure", ["gesperrt", "keycloak_weg", "fremde_person", "kein_refresh_token"])
def test_stale_session_ends_when_roles_cannot_be_confirmed(monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    auth = OidcAuth(oidc_settings())
    monkeypatch.setattr(main_module, "oidc_auth", auth)
    client = TestClient(main_module.app)
    stale = int(time.time()) - auth.settings.auth_role_refresh_seconds - 1
    payload = {"expires_at": 4_102_444_800, "roles_checked_at": stale, "refresh_token": "rt-1",
               "user": {"sub": "u-1", "username": "engineer", "roles": ["work-user"]}}
    if failure == "kein_refresh_token":
        payload.pop("refresh_token")  # Sitzung aus der Zeit vor der Rollenprüfung

    def token(url: str, values: dict[str, str]) -> dict[str, str]:
        if failure in {"gesperrt", "keycloak_weg"}:
            raise AuthError("Keycloak-Kommunikation fehlgeschlagen: HTTP 400 invalid_grant")
        return {"access_token": "at-2", "refresh_token": "rt-2"}

    monkeypatch.setattr(auth, "_form_request", token)
    monkeypatch.setattr(auth, "_json_request", lambda url, access: {"sub": "u-2", "roles": ["work-user"]})
    response = client.get("/api/work/dashboard", cookies={auth.SESSION_COOKIE: auth._sign(payload)})
    assert response.status_code == 401, "ohne bestätigte Rollen keine Rechte (fail closed)"
