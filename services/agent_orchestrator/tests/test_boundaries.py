"""Vertrauensgrenzen: Sandbox, API-Token, Gateway und gesperrte CLI-Worker (REQ-AGT-009 bis -012)."""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from flowagents.api import create_app
from flowagents.config import Runtime
from flowagents.container import ContainerProvider, validate_settings
from flowagents.providers import AgentRequest, GatewayProvider, ProviderError
from flowagents.rm import mint
from flowagents.sandbox import LocalCheck, Sandbox, SandboxError, validate_path

from .conftest import PO, auftrag

SECRET = "test-secret-with-enough-length-0123456789"


# -- Sandbox ---------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "path",
    ["agents/registry.yaml", ".github/workflows/quality.yml", "AGENTS.md", "compose.yaml", "../etc/passwd",
     "/etc/passwd", "docs/.env", "services/platform_api/app/auth.py", "services/platform_api/app/rm_adapter.py"],
)
def test_07_protected_and_unsafe_paths_are_rejected(path: str) -> None:
    with pytest.raises(SandboxError):
        validate_path(path, ("docs/", "services/platform_api/app/", "agents/", ".github/", ""))


def test_06_changes_outside_the_approved_scope_are_rejected(git_repo: Path, tmp_path: Path) -> None:
    box = Sandbox(git_repo, tmp_path / "state", base_ref="HEAD", allowed_prefixes=("docs/",),
                  checker=LocalCheck(["true"]))
    base = box.base_commit()
    with pytest.raises(SandboxError, match="außerhalb"):
        box.apply("RUN-1", base, ["docs/dms.md"], {"docs/other.md": "x"})
    result = box.apply("RUN-1", base, ["docs/dms.md"], {"docs/dms.md": "# Neu\n"})
    workspace = Path(str(result["workspace"]))
    assert (workspace / "docs" / "dms.md").read_text() == "# Neu\n"
    assert not (workspace / ".env").exists(), "Zugangsdaten dürfen nie in die Sandbox gelangen"
    assert str(result["digest"]).startswith("sha256:")
    again = box.apply("RUN-1", base, ["docs/dms.md"], {"docs/dms.md": "# Neu\n"})
    assert again["digest"] == result["digest"], "gleicher Stand ergibt denselben Digest"
    other = box.apply("RUN-1", base, ["docs/dms.md"], {"docs/dms.md": "# Anders\n"})
    assert other["digest"] != result["digest"]
    with pytest.raises(SandboxError, match="nicht in der Sandbox"):
        box.check(str(tmp_path))


# -- API-Token ---------------------------------------------------------------------------------
@pytest.fixture()
def client(make_engine):  # noqa: ANN001, ANN201
    engine = make_engine()
    runtime = Runtime(engine, engine.store, {}, SECRET, "127.0.0.1", 0, 0.1)
    return TestClient(create_app(runtime, start_worker=False)), engine


def token(*, audience: str = "flow-agents-api", ttl: int = 120, user: dict | None = None, secret: str = SECRET,
          issuer: str = "flow-platform-api") -> str:
    now = int(time.time())
    claims = {"iss": issuer, "aud": audience, "iat": now, "exp": now + ttl, "sub": "platform-api"}
    if user:
        claims["user"] = user
    return jwt.encode(claims, secret, algorithm="HS256")


def test_04_missing_or_expired_token_is_rejected(client) -> None:  # noqa: ANN001
    api, _ = client
    assert api.get("/health").status_code == 200
    assert api.get("/v1/overview").status_code == 401
    assert api.get("/v1/overview", headers={"Authorization": f"Bearer {token(ttl=-5)}"}).status_code == 401
    assert api.get("/v1/overview", headers={"Authorization": f"Bearer {token(secret='x' * 40)}"}).status_code == 401
    assert api.get("/v1/overview", headers={"Authorization": f"Bearer {token(ttl=3600)}"}).status_code == 401


def test_05_token_for_another_audience_is_rejected(client) -> None:  # noqa: ANN001
    api, _ = client
    wrong = mint(SECRET, role="anforderungen", agent_id="AG-ENG-01", run_id="RUN-1")  # aud=flowwork-rm
    assert api.get("/v1/overview", headers={"Authorization": f"Bearer {wrong}"}).status_code == 401
    assert api.get("/v1/overview", headers={"Authorization": f"Bearer {token(issuer='jemand')}"}).status_code == 401


def test_api_submit_and_decide_require_a_person(client) -> None:  # noqa: ANN001
    api, engine = client
    body = {"idempotency_key": "api-key-00001", "auftrag": auftrag()}
    assert api.post("/v1/runs", json=body, headers={"Authorization": f"Bearer {token()}"}).status_code == 403
    created = api.post("/v1/runs", json=body, headers={"Authorization": f"Bearer {token(user=PO)}"})
    assert created.status_code == 201, created.text
    overview = api.get("/v1/overview", headers={"Authorization": f"Bearer {token()}"}).json()
    assert overview["runs"][0]["auftrag_id"] == "A-001"
    detail = api.get(f"/v1/runs/{created.json()['id']}", headers={"Authorization": f"Bearer {token()}"})
    assert detail.status_code == 200 and detail.json()["artifacts"][0]["kind"] == "auftrag"
    unknown = api.post("/v1/decisions/ENT-NICHT", json={"outcome": "annehmen"},
                       headers={"Authorization": f"Bearer {token(user=PO)}"})
    assert unknown.status_code == 409


# -- FLOWGATE ---------------------------------------------------------------------------------
class FakeGateway(BaseHTTPRequestHandler):
    seen: list[dict] = []

    def do_POST(self) -> None:  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeGateway.seen.append({"auth": self.headers.get("Authorization"), "body": body,
                                 "run": self.headers.get("X-Flow-Run")})
        if self.headers.get("Authorization") != "Bearer key-pruefer":
            self.send_response(401)
            self.end_headers()
            return
        payload = {"model": body["model"], "choices": [{"message": {"content": '{"status":"fertig"}'}}],
                   "usage": {"completion_tokens": 7}}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args) -> None:  # noqa: ANN002
        return


def test_03_gateway_uses_role_key_and_profile_alias_only(registry) -> None:  # noqa: ANN001
    server = HTTPServer(("127.0.0.1", 0), FakeGateway)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        provider = GatewayProvider(f"http://127.0.0.1:{server.server_port}",
                                   {"codepruefung": "key-pruefer", "entwicklung": "key-coder"})
        reviewer = registry.agent("codepruefung")
        reply = provider.generate(AgentRequest("RUN-1", "codepruefung", reviewer, "sys", "user", 100))
        assert reply.output_tokens == 7
        sent = FakeGateway.seen[-1]
        assert sent["body"]["model"] == "flow-reviewer" and sent["run"] == "RUN-1"
        assert sent["body"]["reasoning_effort"] == "none" and sent["body"]["response_format"]["type"] == "json_object"
        developer = registry.agent("entwicklung")
        with pytest.raises(ProviderError, match="401"):
            provider.generate(AgentRequest("RUN-1", "entwicklung", developer, "sys", "user", 100))
        assert FakeGateway.seen[-1]["body"]["model"] == "flow-coder"
        assert FakeGateway.seen[-1]["body"]["messages"][0]["content"].startswith("/no_think")
        with pytest.raises(ProviderError, match="kein FLOWGATE-Schlüssel"):
            provider.generate(AgentRequest("RUN-1", "x", registry.agent("planung"), "s", "u", 10))
    finally:
        server.shutdown()


def test_gateway_unreachable_is_a_provider_error(registry) -> None:  # noqa: ANN001
    provider = GatewayProvider("http://127.0.0.1:9", {"planung": "k"}, timeout=1, backoff=0)
    with pytest.raises(ProviderError, match="nicht erreichbar|nicht verfügbar"):
        provider.generate(AgentRequest("RUN-1", "planung", registry.agent("planung"), "s", "u", 10))


# -- Gesperrte CLI-Worker -----------------------------------------------------------------------
ACCOUNTS = {
    "codex": {"model": "gpt-6.2-sol", "proxy": "http://egress-codex:3128", "network": "flow-dev-codex",
              "auth_volume": "flow-dev-codex-auth"},
    "claude": {"model": "claude-opus-5-5", "proxy": "http://egress-claude:3128", "network": "flow-dev-claude",
               "auth_volume": "flow-dev-claude-auth"},
}


def test_cli_workers_are_technically_locked_by_default(registry) -> None:  # noqa: ANN001
    provider = ContainerProvider("claude", {"execution_enabled": False, **ACCOUNTS})
    with pytest.raises(ProviderError, match="technisch gesperrt"):
        provider.generate(AgentRequest("RUN-1", "codepruefung", registry.agent("codepruefung"), "s", "u", 10))
    with pytest.raises(ProviderError, match="technisch gesperrt"):
        provider.preflight()


def test_cli_worker_settings_fail_closed() -> None:
    with pytest.raises(ValueError, match="Digest|unveränderliches"):
        validate_settings({"execution_enabled": True, "image": "flow-worker:latest", **ACCOUNTS})
    shared = {**ACCOUNTS, "claude": {**ACCOUNTS["claude"], "auth_volume": "flow-dev-codex-auth"}}
    with pytest.raises(ValueError, match="getrennte"):
        validate_settings({"execution_enabled": False, **shared})
    with pytest.raises(ValueError, match="internes Docker-Netz"):
        validate_settings({"execution_enabled": False, "codex": {**ACCOUNTS["codex"], "network": "host"}})
    with pytest.raises(ValueError, match="Forward-Proxy"):
        validate_settings({"execution_enabled": False, "codex": {**ACCOUNTS["codex"], "proxy": "socks5://x:1"}})


def test_cli_worker_container_is_isolated() -> None:
    provider = ContainerProvider("codex", {"execution_enabled": False, **ACCOUNTS})
    args = provider.docker_args("flow-agents-test")
    joined = " ".join(args)
    for flag in ("--read-only", "--cap-drop ALL", "no-new-privileges", "--network flow-dev-codex",
                 "target=/auth,readonly", "--log-driver none", "--pull never"):
        assert flag in joined
    assert "docker.sock" not in joined and ".env" not in joined and "/Users" not in joined
