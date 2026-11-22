#!/usr/bin/env python3
"""Synchronize the deterministic AD group simulation through Keycloak's Admin API."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE_URL = os.getenv("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080").rstrip("/")
REALM = "open-manufacturing"
ADMIN = os.environ["KEYCLOAK_ADMIN"]
ADMIN_PASSWORD = os.environ["KEYCLOAK_ADMIN_PASSWORD"]
ERP_SECRET = os.environ["ERPNEXT_OIDC_CLIENT_SECRET"]
AGENTGATEWAY_SECRET = os.environ["AGENTGATEWAY_OIDC_CLIENT_SECRET"]
REALM_FILE = Path("/sync/realm.json")


def token() -> str:
    payload = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": ADMIN,
            "password": ADMIN_PASSWORD,
        }
    ).encode()
    request = urllib.request.Request(
        f"{BASE_URL}/realms/master/protocol/openid-connect/token",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return str(json.load(response)["access_token"])


def wait_for_token() -> str:
    for _ in range(30):
        try:
            return token()
        except (OSError, KeyError, urllib.error.HTTPError):
            time.sleep(2)
    raise RuntimeError("Keycloak admin API did not become ready")


ACCESS_TOKEN = wait_for_token()


def api(
    method: str,
    path: str,
    value: Any | None = None,
    expected: tuple[int, ...] = (200, 201, 204),
) -> Any:
    data = None if value is None else json.dumps(value).encode()
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read()
            if response.status not in expected:
                raise RuntimeError(f"Unexpected Keycloak response {response.status} for {path}")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        if exc.code in expected:
            return None
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Keycloak {method} {path} failed: {exc.code} {detail}") from exc


realm = json.loads(REALM_FILE.read_text(encoding="utf-8"))
role_definitions = {item["name"]: item for item in realm["roles"]["realm"]}
app_role_names = set(role_definitions)

for role in role_definitions.values():
    existing = api("GET", f"/admin/realms/{REALM}/roles/{urllib.parse.quote(role['name'])}", expected=(200, 404))
    if existing is None:
        api("POST", f"/admin/realms/{REALM}/roles", role)

platform_admin = api("GET", f"/admin/realms/{REALM}/roles/platform-admin")
composite_roles = [
    api("GET", f"/admin/realms/{REALM}/roles/{name}")
    for name in ("work-user", "requirements-user", "work-admin")
]
api(
    "POST",
    f"/admin/realms/{REALM}/roles-by-id/{platform_admin['id']}/composites",
    composite_roles,
)

group_ids: dict[str, str] = {}
for definition in realm["groups"]:
    name = definition["name"]
    query = urllib.parse.urlencode({"search": name, "exact": "true"})
    matches = api("GET", f"/admin/realms/{REALM}/groups?{query}")
    group = next((item for item in matches if item.get("name") == name), None)
    if group is None:
        api("POST", f"/admin/realms/{REALM}/groups", definition)
        matches = api("GET", f"/admin/realms/{REALM}/groups?{query}")
        group = next(item for item in matches if item.get("name") == name)
    group_ids[name] = str(group["id"])
    api(
        "PUT",
        f"/admin/realms/{REALM}/groups/{group['id']}",
        {
            "id": group["id"],
            "name": name,
            "attributes": definition.get("attributes", {}),
        },
    )
    mappings = [
        api("GET", f"/admin/realms/{REALM}/roles/{urllib.parse.quote(role)}")
        for role in definition.get("realmRoles", [])
    ]
    if mappings:
        api(
            "POST",
            f"/admin/realms/{REALM}/groups/{group['id']}/role-mappings/realm",
            mappings,
        )


client_cache: dict[str, dict[str, Any]] = {}


def client(client_id: str) -> dict[str, Any]:
    if client_id not in client_cache:
        query = urllib.parse.urlencode({"clientId": client_id})
        matches = api("GET", f"/admin/realms/{REALM}/clients?{query}")
        if not matches:
            raise RuntimeError(f"Keycloak client {client_id} does not exist")
        client_cache[client_id] = matches[0]
    return client_cache[client_id]


def client_role(client_id: str, role_name: str) -> dict[str, Any]:
    record = client(client_id)
    role = urllib.parse.quote(role_name, safe="")
    return api("GET", f"/admin/realms/{REALM}/clients/{record['id']}/roles/{role}")


def synchronize_user_client_roles(user_id: str, definition: dict[str, Any]) -> None:
    # These are Keycloak's normal account-console permissions. They are
    # synchronized explicitly because Admin-API-created users do not inherit
    # the realm's default client-role composites automatically.
    desired: dict[str, set[str]] = {
        "account": {"manage-account", "manage-account-links", "view-profile"}
    }
    for client_id, role_names in definition.get("clientRoles", {}).items():
        desired.setdefault(client_id, set()).update(role_names)
    for client_id, role_names in desired.items():
        record = client(client_id)
        current = api(
            "GET",
            f"/admin/realms/{REALM}/users/{user_id}/role-mappings/clients/{record['id']}",
        )
        current_names = {str(role["name"]) for role in current}
        missing = [
            client_role(client_id, role_name)
            for role_name in sorted(role_names - current_names)
        ]
        if missing:
            api(
                "POST",
                f"/admin/realms/{REALM}/users/{user_id}/role-mappings/clients/{record['id']}",
                missing,
            )

user_count = 0
for definition in realm["users"]:
    username = definition["username"]
    query = urllib.parse.urlencode({"username": username, "exact": "true"})
    matches = api("GET", f"/admin/realms/{REALM}/users?{query}")
    if not matches:
        create_value = {key: value for key, value in definition.items() if key != "groups"}
        api("POST", f"/admin/realms/{REALM}/users", create_value)
        matches = api("GET", f"/admin/realms/{REALM}/users?{query}")
    user_id = str(matches[0]["id"])
    desired = {path.rsplit("/", 1)[-1] for path in definition.get("groups", [])}
    current = api("GET", f"/admin/realms/{REALM}/users/{user_id}/groups")
    for membership in current:
        name = str(membership["name"])
        if name.startswith("AD-GG-FLOW-") and name not in desired:
            api("DELETE", f"/admin/realms/{REALM}/users/{user_id}/groups/{membership['id']}")
    for name in desired:
        api("PUT", f"/admin/realms/{REALM}/users/{user_id}/groups/{group_ids[name]}")
    direct_roles = api("GET", f"/admin/realms/{REALM}/users/{user_id}/role-mappings/realm")
    legacy = [role for role in direct_roles if role.get("name") in app_role_names]
    if legacy:
        api("DELETE", f"/admin/realms/{REALM}/users/{user_id}/role-mappings/realm", legacy)
    synchronize_user_client_roles(user_id, definition)
    user_count += 1

def sync_client(client_id: str, secret: str) -> None:
    desired = next(
        item for item in realm["clients"] if item.get("clientId") == client_id
    )
    desired = {**desired, "secret": secret}
    query = urllib.parse.urlencode({"clientId": client_id})
    clients = api("GET", f"/admin/realms/{REALM}/clients?{query}")
    if not clients:
        api("POST", f"/admin/realms/{REALM}/clients", desired)
        clients = api("GET", f"/admin/realms/{REALM}/clients?{query}")
    if not clients:
        raise RuntimeError(f"Keycloak client {client_id} could not be created")
    current = clients[0]
    current.update(desired)
    api("PUT", f"/admin/realms/{REALM}/clients/{current['id']}", current)


sync_client("erpnext", ERP_SECRET)
sync_client("agentgateway-ui", AGENTGATEWAY_SECRET)

print(
    f"AD demo synchronized in Keycloak: users={user_count}, groups={len(group_ids)}, "
    "authorization=group-inherited"
)
