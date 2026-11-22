from __future__ import annotations

from app.iam_roles import roles_for_entry


def test_paperless_resolves_keycloak_group_inherited_roles() -> None:
    realm = {
        "groups": [
            {
                "name": "AD-GG-FLOW-PLATFORM-ADMIN",
                "realmRoles": ["platform-admin"],
            },
            {
                "name": "AD-GG-FLOW-PROCUREMENT-USER",
                "realmRoles": ["procurement-user"],
            },
        ]
    }
    demo_admin = {
        "username": "demo01",
        "groups": ["/AD-GG-FLOW-PLATFORM-ADMIN"],
    }
    purchaser = {
        "username": "demo06",
        "groups": ["/AD-GG-FLOW-PROCUREMENT-USER"],
    }

    assert "platform-admin" in roles_for_entry(realm, demo_admin)
    assert "procurement-user" in roles_for_entry(realm, purchaser)
    assert "platform-admin" not in roles_for_entry(realm, purchaser)


def test_direct_and_unknown_group_roles_are_safe() -> None:
    realm = {"groups": []}
    entry = {
        "realmRoles": ["dms-user"],
        "groups": ["/GROUP-NOT-IMPORTED"],
    }
    assert roles_for_entry(realm, entry) == {"dms-user"}
