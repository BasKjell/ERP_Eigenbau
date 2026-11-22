"""Resolve effective Keycloak realm roles for downstream provisioning."""

from __future__ import annotations

from typing import Any


def roles_for_entry(realm: dict[str, Any], entry: dict[str, Any]) -> set[str]:
    """Return direct roles plus roles inherited from imported Keycloak groups."""

    roles = set(entry.get("realmRoles", []))
    group_roles = {
        f"/{group['name']}": set(group.get("realmRoles", []))
        for group in realm.get("groups", [])
    }
    for group_path in entry.get("groups", []):
        roles.update(group_roles.get(group_path, set()))
    return roles
