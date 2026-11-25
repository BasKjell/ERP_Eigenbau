from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import jwt
from fastapi import Request
from fastapi.responses import RedirectResponse, Response
from jwt.exceptions import InvalidTokenError

from .config import Settings


class AuthError(RuntimeError):
    pass


class OidcAuth:
    """Small OIDC authorization-code client with PKCE and signed local sessions."""

    SESSION_COOKIE = "platform_session"
    FLOW_COOKIE = "platform_oidc_flow"
    # ID-Token nur als Hinweis für die Abmeldung bei Keycloak (id_token_hint), getrennt von der Sitzung.
    ID_TOKEN_COOKIE = "platform_id_token"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return self.settings.auth_mode == "oidc"

    def current_user(self, request: Request) -> dict[str, Any] | None:
        service_user = self._demo_service_user(request)
        if service_user is not None:
            return service_user
        raw = request.cookies.get(self.SESSION_COOKIE)
        if not raw:
            return None
        payload = self._unsign(raw)
        if not payload or int(payload.get("expires_at", 0)) <= int(time.time()):
            return None
        if self._roles_stale(payload):
            return None  # ungeprüfte Rollen nie verwenden; refresh_session() erneuert sie
        return payload.get("user")

    def _roles_stale(self, payload: dict[str, Any]) -> bool:
        return int(time.time()) - int(payload.get("roles_checked_at", 0)) >= self.settings.auth_role_refresh_seconds

    def refresh_session(self, request: Request) -> tuple[dict[str, Any] | None, str | None]:
        """Rollen einer Sitzung spätestens nach ``auth_role_refresh_seconds`` bei Keycloak neu laden.

        Liefert (Person, neuer Cookie-Wert). Ein AD-Rechteentzug, ein gesperrtes Konto oder eine beendete
        Keycloak-Sitzung beenden damit auch die Portalsitzung. Ist Keycloak nicht erreichbar, endet die
        Sitzung ebenfalls (fail closed); eine erneute Anmeldung ist bei laufender SSO-Sitzung sofort möglich.
        """
        payload = self._unsign(request.cookies.get(self.SESSION_COOKIE, ""))
        if not payload or int(payload.get("expires_at", 0)) <= int(time.time()):
            return None, None
        if not self._roles_stale(payload):
            return payload.get("user"), None
        refresh_token = str(payload.get("refresh_token") or "")
        if not refresh_token:
            return None, None  # Sitzung aus der Zeit vor der Rollenprüfung: neu anmelden
        issuer = self.settings.oidc_internal_issuer.rstrip("/")
        try:
            token = self._form_request(f"{issuer}/protocol/openid-connect/token", {
                "grant_type": "refresh_token", "client_id": self.settings.oidc_client_id,
                "refresh_token": refresh_token})
            userinfo = self._json_request(f"{issuer}/protocol/openid-connect/userinfo", str(token["access_token"]))
        except (AuthError, KeyError):
            return None, None
        previous = payload.get("user") or {}
        if not hmac.compare_digest(str(previous.get("sub", "")), str(userinfo.get("sub", ""))):
            return None, None
        user = self._user_from(userinfo)
        payload.update({"user": user, "roles_checked_at": int(time.time()),
                        "refresh_token": str(token.get("refresh_token") or refresh_token)})
        return user, self._sign(payload)

    def session_cookie(self, response: Response, value: str) -> None:
        response.set_cookie(self.SESSION_COOKIE, value, max_age=self.settings.auth_session_minutes * 60,
                            httponly=True, secure=self.settings.auth_cookie_secure, samesite="lax", path="/")

    @staticmethod
    def _user_from(userinfo: dict[str, Any]) -> dict[str, Any]:
        roles = userinfo.get("roles", [])
        if isinstance(roles, str):
            roles = [roles]
        if not roles and isinstance(userinfo.get("realm_access"), dict):
            roles = userinfo["realm_access"].get("roles", [])
        user = {
            "sub": userinfo.get("sub"),
            "username": userinfo.get("preferred_username"),
            "name": userinfo.get("name")
            or " ".join(
                part for part in (userinfo.get("given_name"), userinfo.get("family_name")) if part
            ),
            "email": userinfo.get("email"),
            "roles": roles,
            "department": userinfo.get("department"),
            "desksharing_user_id": userinfo.get("desksharing_user_id"),
        }
        return user

    def _demo_service_user(self, request: Request) -> dict[str, Any] | None:
        """Authorize only the two deterministic demo lifecycle endpoints."""
        if request.url.path not in {"/api/demo/reset", "/api/demo/purge"}:
            return None
        expected = self.settings.demo_admin_api_token
        supplied = request.headers.get("X-Demo-Admin-Token", "")
        if not expected or not supplied or not hmac.compare_digest(supplied, expected):
            return None
        return {
            "sub": "demo-data-api",
            "username": "demo-data-api",
            "name": "Demo Data API",
            "email": None,
            "roles": ["platform-admin"],
            "department": "IT",
            "desksharing_user_id": None,
        }

    def login(self, next_path: str = "/", *, login_hint: str = "") -> Response:
        if not self.enabled:
            return RedirectResponse(next_path if self._safe_next(next_path) else "/")
        extra = {"login_hint": login_hint, "prompt": "login"} if login_hint else {}
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")
        redirect_uri = f"{self.settings.platform_public_url.rstrip('/')}/auth/callback"
        query = urllib.parse.urlencode(
            {
                "client_id": self.settings.oidc_client_id,
                "response_type": "code",
                "scope": "openid profile email",
                "redirect_uri": redirect_uri,
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                **extra,
            }
        )
        response = RedirectResponse(
            f"{self.settings.oidc_external_issuer.rstrip('/')}/protocol/openid-connect/auth?{query}"
        )
        response.set_cookie(
            self.FLOW_COOKIE,
            self._sign(
                {
                    "state": state,
                    "nonce": nonce,
                    "verifier": verifier,
                    "next": next_path if self._safe_next(next_path) else "/",
                    "expires_at": int(time.time()) + 600,
                }
            ),
            max_age=600,
            httponly=True,
            secure=self.settings.auth_cookie_secure,
            samesite="lax",
            path="/",
        )
        return response

    def callback(self, request: Request) -> Response:
        error = request.query_params.get("error")
        if error:
            raise AuthError(f"Keycloak-Anmeldung abgebrochen: {error}")
        code = request.query_params.get("code", "")
        state = request.query_params.get("state", "")
        flow = self._unsign(request.cookies.get(self.FLOW_COOKIE, ""))
        if (
            not flow
            or int(flow.get("expires_at", 0)) <= int(time.time())
            or not hmac.compare_digest(str(flow.get("state", "")), state)
            or not code
        ):
            raise AuthError("OIDC-Status ist ungültig oder abgelaufen")

        redirect_uri = f"{self.settings.platform_public_url.rstrip('/')}/auth/callback"
        token = self._form_request(
            f"{self.settings.oidc_internal_issuer.rstrip('/')}/protocol/openid-connect/token",
            {
                "grant_type": "authorization_code",
                "client_id": self.settings.oidc_client_id,
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": str(flow["verifier"]),
            },
        )
        access_token = token.get("access_token")
        id_token = token.get("id_token")
        if not access_token or not id_token:
            raise AuthError("Keycloak lieferte nicht alle erforderlichen Token")
        id_claims = self._validate_id_token(str(id_token), str(flow["nonce"]))
        userinfo = self._json_request(
            f"{self.settings.oidc_internal_issuer.rstrip('/')}/protocol/openid-connect/userinfo",
            access_token,
        )
        if not hmac.compare_digest(str(id_claims.get("sub", "")), str(userinfo.get("sub", ""))):
            raise AuthError("OIDC-Identitäten in ID-Token und UserInfo stimmen nicht überein")
        user = self._user_from(userinfo)
        response = RedirectResponse(str(flow.get("next", "/")))
        response.set_cookie(
            self.SESSION_COOKIE,
            self._sign(
                {
                    "user": user,
                    "expires_at": int(time.time())
                    + self.settings.auth_session_minutes * 60,
                    "roles_checked_at": int(time.time()),
                    "refresh_token": str(token.get("refresh_token") or ""),
                }
            ),
            max_age=self.settings.auth_session_minutes * 60,
            httponly=True,
            secure=self.settings.auth_cookie_secure,
            samesite="lax",
            path="/",
        )
        response.delete_cookie(self.FLOW_COOKIE, path="/")
        response.set_cookie(
            self.ID_TOKEN_COOKIE,
            str(id_token),
            max_age=self.settings.auth_session_minutes * 60,
            httponly=True,
            secure=self.settings.auth_cookie_secure,
            samesite="lax",
            path="/auth",
        )
        return response

    def switch(self, request: Request, username: str, next_path: str = "/") -> Response:
        """Demo-Benutzerwechsel: bei Keycloak abmelden und mit vorbelegtem Konto neu anmelden.

        Kein Kennwort und keine Rolle kommt aus dem Browser; Keycloak prüft die Anmeldung, die Rollen
        stammen wie sonst aus den AD-Gruppen.
        """
        next_path = next_path if self._safe_next(next_path) else "/"
        login = (f"{self.settings.platform_public_url.rstrip('/')}/auth/login?"
                 + urllib.parse.urlencode({"next": next_path, "login_hint": username}))
        return self.logout(request, target=login)

    def logout(self, request: Request | None = None, *, target: str = "") -> Response:
        target = target or f"{self.settings.platform_public_url.rstrip('/')}/"
        values = {"client_id": self.settings.oidc_client_id, "post_logout_redirect_uri": target}
        id_token = request.cookies.get(self.ID_TOKEN_COOKIE, "") if request is not None else ""
        if id_token:
            values["id_token_hint"] = id_token
        query = urllib.parse.urlencode(values)
        location = (
            f"{self.settings.oidc_external_issuer.rstrip('/')}/protocol/openid-connect/logout?{query}"
            if self.enabled
            else target
        )
        response = RedirectResponse(location)
        response.delete_cookie(self.SESSION_COOKIE, path="/")
        response.delete_cookie(self.FLOW_COOKIE, path="/")
        response.delete_cookie(self.ID_TOKEN_COOKIE, path="/auth")
        return response

    @staticmethod
    def required_roles(path: str) -> set[str]:
        if path.startswith("/api/finance") or path == "/finance":
            return {"finance-user", "management-user"}
        if path.startswith("/api/work") or path == "/work":
            return {"work-user", "requirements-user", "work-admin"}
        if path.startswith("/api/desksharing") or path == "/desksharing":
            return {"desksharing-user", "desksharing-admin"}
        if path.startswith("/api/mes") or path == "/mes":
            return {"production-user", "planning-user", "quality-user"}
        if path.startswith("/api/quality") or path == "/quality":
            return {"quality-user", "warehouse-user", "procurement-user"}
        if path.startswith("/api/hr") or path == "/hr":
            return {"hr-user", "hr-admin"}
        if path.startswith(("/api/documents", "/api/dms")) or path == "/dms":
            return {"dms-user"}
        if (
            path.startswith("/api/demo")
            or path.startswith("/api/assistant")
            or path == "/management"
        ):
            return {"management-user"}
        return set()

    @staticmethod
    def public_path(path: str) -> bool:
        # /api/rm/v1/ und /api/agents/sync/ authentifizieren Agenten bzw. den Orchestrator selbst
        # per kurzlebigem Dienst-Token (agent_policy, agents_bff).
        return path in {"/health", "/ready", "/metrics", "/favicon.ico", "/api/reporting/live"} or path.startswith(
            ("/auth/", "/assets/", "/api/rm/v1/", "/api/agents/sync/", "/api/agents/internal/")
        )

    def _sign(self, value: dict[str, Any]) -> str:
        payload = base64.urlsafe_b64encode(
            json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()
        ).decode().rstrip("=")
        signature = hmac.new(
            self.settings.auth_session_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return f"{payload}.{signature}"

    def _unsign(self, value: str) -> dict[str, Any] | None:
        try:
            payload, signature = value.rsplit(".", 1)
            expected = hmac.new(
                self.settings.auth_session_secret.encode(), payload.encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return None
            padding = "=" * (-len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload + padding)
            result = json.loads(decoded)
            return result if isinstance(result, dict) else None
        except (ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def _safe_next(value: str) -> bool:
        return value.startswith("/") and not value.startswith("//")

    def _validate_id_token(self, id_token: str, expected_nonce: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(id_token)
            algorithm = str(header.get("alg", ""))
            key_id = str(header.get("kid", ""))
            if algorithm not in {"RS256", "RS384", "RS512"} or not key_id:
                raise AuthError("OIDC-ID-Token verwendet keinen erlaubten Signaturschlüssel")
            certs_request = urllib.request.Request(
                f"{self.settings.oidc_internal_issuer.rstrip('/')}/protocol/openid-connect/certs",
                headers={"Accept": "application/json"},
            )
            jwks = self._urlopen_json(certs_request)
            key_data = next(
                (
                    item
                    for item in jwks.get("keys", [])
                    if isinstance(item, dict) and hmac.compare_digest(str(item.get("kid", "")), key_id)
                ),
                None,
            )
            if key_data is None:
                raise AuthError("OIDC-Signaturschlüssel wurde nicht im Keycloak-JWKS gefunden")
            public_key = jwt.PyJWK.from_dict(key_data, algorithm=algorithm).key
            claims = jwt.decode(
                id_token,
                public_key,
                algorithms=[algorithm],
                audience=self.settings.oidc_client_id,
                issuer=self.settings.oidc_external_issuer.rstrip("/"),
                leeway=30,
                options={"require": ["exp", "iat", "iss", "aud", "sub", "nonce"]},
            )
            nonce = str(claims.get("nonce", ""))
            if not nonce or not hmac.compare_digest(nonce, expected_nonce):
                raise AuthError("OIDC-Nonce im ID-Token ist ungültig")
            return claims
        except AuthError:
            raise
        except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
            raise AuthError(f"OIDC-ID-Token konnte nicht validiert werden: {exc}") from exc

    @staticmethod
    def _form_request(url: str, values: dict[str, str]) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(values).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        return OidcAuth._urlopen_json(request)

    @staticmethod
    def _json_request(url: str, access_token: str) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        return OidcAuth._urlopen_json(request)

    @staticmethod
    def _urlopen_json(request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                value = json.loads(response.read())
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise AuthError(f"Keycloak-Kommunikation fehlgeschlagen: {exc}") from exc
        if not isinstance(value, dict):
            raise AuthError("Keycloak-Antwort hat ein unerwartetes Format")
        return value
