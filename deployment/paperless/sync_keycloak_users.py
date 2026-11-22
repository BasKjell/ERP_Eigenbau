"""Idempotently provision the local Keycloak demo identities in Paperless."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

sys.path.insert(0, "/seed")
from iam_roles import roles_for_entry
from iam_roles import roles_for_entry


realm = json.loads(Path("/seed/realm.json").read_text(encoding="utf-8"))
users = realm["users"]
group_by_name = {group.name: group for group in Group.objects.all()}
project_read_groups = sorted(
    name
    for name in group_by_name
    if name.startswith("DMS-Projekt-") and name.endswith("-Lesen")
)

department_groups = {
    "Vertrieb": ["DMS-Bereich-Vertrieb"],
    "Einkauf": ["DMS-Bereich-Einkauf"],
    "Disposition": ["DMS-Bereich-Produktion"],
    "Produktion": ["DMS-Bereich-Produktion"],
    "Qualität": ["DMS-Bereich-Qualitaet"],
    "Lager": ["DMS-Eingang"],
    "Personal": ["DMS-Bereich-HR-Recruiting"],
    "Projekte & Engineering": [
        "DMS-Bereich-Konstruktion",
        "DMS-Bereich-Projektleitung",
    ],
}


def first_attribute(entry: dict, name: str) -> str:
    value = entry.get("attributes", {}).get(name, [""])
    return str(value[0] if isinstance(value, list) and value else value or "")


def desired_groups(entry: dict) -> set[str]:
    roles = roles_for_entry(realm, entry)
    department = first_attribute(entry, "department")
    names = {"DMS-Leser", *department_groups.get(department, [])}
    if roles.intersection(
        {
            "sales-user",
            "procurement-user",
            "planning-user",
            "production-user",
            "warehouse-user",
            "project-user",
            "hr-admin",
        }
    ):
        names.add("DMS-Bearbeiter")
    if "quality-user" in roles:
        names.add("DMS-Pruefer")
    if "hr-admin" in roles:
        names.add("DMS-Bereich-HR-Payroll")
    if roles.intersection({"project-user", "management-user"}):
        names.update(project_read_groups)
    return names


User = get_user_model()
created = 0
updated = 0
for entry in users:
    username = entry["username"]
    user, was_created = User.objects.get_or_create(username=username)
    user.email = entry.get("email", "")
    user.first_name = entry.get("firstName", "")
    user.last_name = entry.get("lastName", "")
    user.is_active = bool(entry.get("enabled", True))
    is_platform_admin = "platform-admin" in roles_for_entry(realm, entry)
    user.is_staff = is_platform_admin
    user.is_superuser = is_platform_admin
    user.set_unusable_password()
    user.save()
    if is_platform_admin:
        user.groups.set(Group.objects.all())
    else:
        names = desired_groups(entry)
        missing = sorted(names - group_by_name.keys())
        if missing:
            raise RuntimeError(f"Paperless groups missing for {username}: {missing}")
        user.groups.set(group_by_name[name] for name in sorted(names))
    created += int(was_created)
    updated += int(not was_created)

print(f"Paperless Keycloak identities synchronized: created={created}, updated={updated}")
