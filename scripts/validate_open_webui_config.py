#!/usr/bin/env python3
"""Validate Open WebUI MCP connections and the protected local model path."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATEWAY_CONFIG = ROOT / "deployment" / "agentgateway" / "config.yaml"
REALM_CONFIG = ROOT / "deployment" / "keycloak" / "realm.json"
EXPECTED = {
    "erp": "http://platform-mcp:8090/mcp",
    "dms": "http://dms-mcp:8091/mcp",
    "wiki": "http://knowledge-mcp:8092/mcp",
}


def main() -> None:
    completed = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "compose.yaml",
            "--profile",
            "webui",
            "config",
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    compose = json.loads(completed.stdout)
    raw_connections = compose["services"]["open-webui"]["environment"][
        "TOOL_SERVER_CONNECTIONS"
    ]
    environment = compose["services"]["open-webui"]["environment"]
    assert environment["ENABLE_PERSISTENT_CONFIG"] == "false"
    assert environment["ENABLE_OLLAMA_API"] == "false"
    assert environment["ENABLE_OPENAI_API"] == "true"
    assert environment["OPENAI_API_BASE_URL"] == "http://agentgateway:4000/v1"
    assert environment["OPENAI_API_KEY"]
    assert (
        environment["OPENAI_API_KEY"]
        == compose["services"]["agentgateway"]["environment"][
            "AGENTGATEWAY_OPENWEBUI_KEY"
        ]
    )
    assert compose["services"]["open-webui"]["depends_on"]["agentgateway"]
    connections = json.loads(raw_connections)
    by_id = {(item.get("info") or {}).get("id"): item for item in connections}
    assert set(by_id) == set(EXPECTED), f"unexpected MCP ids: {set(by_id)}"
    for connection_id, expected_url in EXPECTED.items():
        connection = by_id[connection_id]
        assert connection["url"] == expected_url
        assert connection["type"] == "mcp"
        assert connection["auth_type"] == "none"
        assert connection["config"]["enable"] is True
        assert connection["info"]["name"]
        assert connection["info"]["description"]
    assert "pgvector" in by_id["dms"]["info"]["description"]
    gateway = GATEWAY_CONFIG.read_text(encoding="utf-8")
    for expected in (
        "provider: ollama",
        "model: qwen3:8b",
        "model: qwen3-coder:30b",
        "mode: strict",
        "AGENTGATEWAY_OPENWEBUI_KEY",
        "allowedModels:",
        "issuer: ${ISSUER_URL}",
        "authorizationEndpoint: ${OIDC_AUTHORIZATION_ENDPOINT}",
        'jwt.roles.exists(role, role == "platform-admin")',
    ):
        assert expected in gateway, expected
    realm = json.loads(REALM_CONFIG.read_text(encoding="utf-8"))
    client = next(
        item for item in realm["clients"] if item["clientId"] == "agentgateway-ui"
    )
    assert client["publicClient"] is False
    assert client["redirectUris"] == ["http://localhost:4001/oauth/callback"]
    assert client["webOrigins"] == ["http://localhost:4001"]
    role_mapper = next(
        mapper
        for mapper in client["protocolMappers"]
        if mapper["config"].get("claim.name") == "roles"
    )
    assert role_mapper["config"]["id.token.claim"] == "true"
    demo_user = next(user for user in realm["users"] if user["username"] == "demo01")
    assert "/AD-GG-FLOW-PLATFORM-ADMIN" in demo_user["groups"]
    print("Open WebUI MCP and Agentgateway configuration: OK")


if __name__ == "__main__":
    main()
