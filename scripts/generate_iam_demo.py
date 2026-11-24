#!/usr/bin/env python3
"""Generate the deterministic IAM and desksharing demo catalog.

The script is the single source of truth for Keycloak identities and the
matching application-side catalog. It deliberately contains demo credentials;
they are never suitable for an internet-facing or productive deployment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REALM_FILE = ROOT / "deployment" / "keycloak" / "realm.json"
GROUP_ASSIGNMENTS_FILE = ROOT / "deployment" / "keycloak" / "ad-group-assignments.csv"
AD_PARTIAL_IMPORT_FILE = ROOT / "deployment" / "keycloak" / "ad-partial-import.json"
PROJECTS_FILE = ROOT / "agents" / "projects.json"
SCENARIO_FILE = ROOT / "services" / "platform_api" / "seed" / "scenario.json"
REALM = "open-manufacturing"
DEMO_USER_PASSWORD = "Demo-User-2026!"
DEMO_ADMIN_PASSWORD = "Admin-Start-2026!"
ERPNEXT_OIDC_CLIENT_SECRET = "erpnext-oidc-demo-change-me"
AGENTGATEWAY_OIDC_CLIENT_SECRET = "agentgateway-oidc-demo-change-me"

DEPARTMENTS = [
    ("Vertrieb", "sales-user", 5),
    ("Einkauf", "procurement-user", 5),
    ("Disposition", "planning-user", 5),
    ("Produktion", "production-user", 10),
    ("Qualität", "quality-user", 5),
    ("Lager", "warehouse-user", 5),
    ("Personal", "hr-user", 4),
    ("Finanzen", "finance-user", 4),
    ("Projekte & Engineering", "project-user", 5),
    ("IT", "it-user", 2),
]

NAMES = [
    ("Anna", "Schneider"), ("Jonas", "Weber"), ("Miriam", "Becker"),
    ("David", "Fischer"), ("Leonie", "Wagner"), ("Felix", "Hoffmann"),
    ("Sophie", "Koch"), ("Daniel", "Richter"), ("Nina", "Klein"),
    ("Lukas", "Wolf"), ("Clara", "Schröder"), ("Tobias", "Neumann"),
    ("Laura", "Schwarz"), ("Jan", "Zimmermann"), ("Emilia", "Braun"),
    ("Tim", "Krüger"), ("Johanna", "Hartmann"), ("Max", "Lange"),
    ("Sarah", "Schmitt"), ("Paul", "Werner"), ("Julia", "Schmitz"),
    ("Simon", "Krause"), ("Marie", "Meier"), ("Niklas", "Lehmann"),
    ("Lisa", "Schmid"), ("Ben", "Schulz"), ("Katharina", "Maier"),
    ("Moritz", "Köhler"), ("Franziska", "Herrmann"), ("Leon", "König"),
    ("Theresa", "Walter"), ("Elias", "Mayer"), ("Vanessa", "Huber"),
    ("Florian", "Kaiser"), ("Carolin", "Fuchs"), ("Noah", "Peters"),
    ("Alina", "Lang"), ("Sebastian", "Scholz"), ("Amelie", "Möller"),
    ("Philipp", "Weiß"), ("Isabel", "Jung"), ("Matteo", "Hahn"),
    ("Luisa", "Schubert"), ("Alexander", "Vogel"), ("Helena", "Friedrich"),
    ("Nico", "Günther"), ("Eva", "Frank"), ("Robert", "Berger"),
    ("Maja", "Roth"), ("Christian", "Beck"),
]

REALM_ROLES = [
    ("platform-admin", "Vollzugriff auf alle Plattformbereiche"),
    ("management-user", "Managementcockpit und Kennzahlen"),
    ("sales-user", "CRM und Vertrieb"),
    ("procurement-user", "Einkauf"),
    ("planning-user", "Disposition und Produktionsplanung"),
    ("production-user", "MES und Shopfloor"),
    ("quality-user", "Qualitätsmanagement"),
    ("warehouse-user", "Lager und Logistik"),
    ("hr-user", "HR-Self-Service"),
    ("hr-admin", "HR-Administration, Recruiting und Payroll"),
    ("finance-user", "Finanzen und Controlling"),
    ("project-user", "Projekt- und Dokumentenzugriff"),
    ("dms-user", "Freigegebene Dokumente"),
    ("desksharing-user", "Arbeitsplatz suchen und buchen"),
    ("desksharing-admin", "Standorte und Buchungen verwalten"),
    ("it-user", "Technischer Betrieb"),
    ("grafana-viewer", "Operative Dashboards"),
    ("ai-user", "Lokaler KI-Assistent"),
    ("work-user", "FLOWWORK-Projekte, Tickets und Wiki"),
    ("requirements-user", "Anforderungen, Baselines und Traceability"),
    ("work-admin", "FLOWWORK-Administration und Projektvorlagen"),
    ("flow-po", "FLOWAGENTS Product Owner: Aufträge, G1 Anforderungsbaseline, Rückfragen"),
    ("flow-techlead", "FLOWAGENTS Tech Lead: G2/G3, Blockaden, Korrekturlimit, Laufsteuerung"),
    ("flow-keyuser", "FLOWAGENTS Key User: G4 Fachabnahme in der Vorschau"),
    ("flow-release", "FLOWAGENTS Release-Verantwortung: G5 Produktionsfreigabe"),
    ("flow-isb", "FLOWAGENTS Informationssicherheit: Sicherheitsrückfragen, Audit, keine Gate-Freigabe"),
    ("flow-gf", "FLOWAGENTS Geschäftsführung: Rückfragen des Geschäftsführungs-Agenten"),
]

# Projektrechte (agents/projects.json): je Projekt eine Lese- und eine Änderungsgruppe. Lesen heißt
# Aufträge, Pakete und Entscheidungen des Projekts sehen und als Projektmitglied entscheiden; Ändern heißt
# zusätzlich Aufträge einreichen und Arbeitspakete starten (zusammen mit flow-po oder flow-techlead).
PROJECT_CATALOG: dict[str, dict[str, Any]] = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))["projects"]


def project_role(code: str, right: str) -> str:
    return f"flow-prj-{code.lower()}-{right}"


PROJECT_ROLES = [
    (project_role(code, right), f"Projekt {code} – {spec['title']}: "
     + ("lesen und als Projektmitglied entscheiden" if right == "lesen" else "Aufträge einreichen und Pakete starten"))
    for code, spec in PROJECT_CATALOG.items()
    for right in ("lesen", "aendern")
]
REALM_ROLES.extend(PROJECT_ROLES)
ALL_PROJECT_ROLES = [name for name, _ in PROJECT_ROLES]


def rights(**projects: str) -> list[str]:
    """Projektrechte je Demo-Person: aendern schließt lesen ein."""
    roles: list[str] = []
    for code, right in projects.items():
        code = code.replace("_", "-")
        roles.append(project_role(code, "lesen"))
        if right == "aendern":
            roles.append(project_role(code, "aendern"))
    return roles


# Freigaberollen der Agentenentwicklung (KI-EK Teil 05: Gruppen für PO, Tech Lead, Release, ISB und
# Key User getrennt von Datengruppen). Sie sind bewusst NICHT Teil von platform-admin: Betrieb und
# fachliche Freigabe bleiben getrennt (Funktionstrennung, ORP.1/ORP.4).
DECISION_ROLES = ["flow-po", "flow-techlead", "flow-keyuser", "flow-release", "flow-isb", "flow-gf"]
BASE_ROLE_USER = ["dms-user", "work-user", "requirements-user"]

# Je Freigaberolle eine Demo-Person (für die Vorführung des Freigabeprozesses) und eine Person mit
# allen Rechten. Sie stehen außerhalb des 50-Personen-Katalogs (kein Desksharing-Arbeitsplatz).
ROLE_DEMO_USERS = [
    ("admin.demo", "Alex", "Vollzugriff", "IT",
     ["platform-admin", *DECISION_ROLES, *ALL_PROJECT_ROLES, "it-user", "ai-user", "grafana-viewer",
      "management-user"]),
    ("po.demo", "Petra", "Ohm", "Projekte & Engineering",
     [*BASE_ROLE_USER, "flow-po", "project-user",
      *rights(FLOW_PLATFORM="lesen", FLOW_DMS="aendern", TM_100="aendern")]),
    ("po2.demo", "Paula", "Brandt", "Qualität",
     [*BASE_ROLE_USER, "flow-po", "quality-user", *rights(TM_100="lesen", PS_TM100="aendern")]),
    ("techlead.demo", "Tarek", "Lindner", "IT",
     [*BASE_ROLE_USER, "flow-techlead", "it-user", "ai-user",
      *rights(FLOW_PLATFORM="aendern", FLOW_DMS="aendern", TM_100="aendern", PS_TM100="lesen")]),
    ("keyuser.demo", "Kira", "Unger", "Qualität",
     [*BASE_ROLE_USER, "flow-keyuser", "quality-user", *rights(FLOW_DMS="lesen", TM_100="lesen", PS_TM100="lesen")]),
    ("release.demo", "Rafael", "Rehm", "IT",
     [*BASE_ROLE_USER, "flow-release", "it-user",
      *rights(FLOW_PLATFORM="lesen", FLOW_DMS="lesen", TM_100="lesen", PS_TM100="lesen")]),
    ("dev.demo", "Dennis", "Engel", "Projekte & Engineering",
     [*BASE_ROLE_USER, "project-user", "ai-user", *rights(TM_100="lesen", PS_TM100="lesen")]),
    ("isb.demo", "Ines", "Sommer", "Informationssicherheit", [*BASE_ROLE_USER, "flow-isb", "grafana-viewer"]),
    ("gf.demo", "Georg", "Falk", "Geschäftsführung", [*BASE_ROLE_USER, "flow-gf", "management-user"]),
]


FUNCTION_LABELS = [
    ("platform-admin", "Administration – alle Rechte"),
    ("flow-po", "Product Owner"),
    ("flow-techlead", "Tech Lead"),
    ("flow-keyuser", "Key User (Fachabnahme)"),
    ("flow-release", "Release-Verantwortung"),
    ("flow-isb", "Informationssicherheit (Aufsicht)"),
    ("flow-gf", "Geschäftsführung (Aufsicht)"),
]


def demo_function(role_names: list[str]) -> str:
    return next((label for role, label in FUNCTION_LABELS if role in role_names), "Entwicklung (nur lesen)")


def ad_group_name(role: str) -> str:
    if role.startswith("flow-prj-"):
        return f"AD-GG-FLOW-PRJ-{role.removeprefix('flow-prj-').upper()}"
    if role.startswith("flow-"):
        return f"AD-GG-FLOW-AGENTS-{role.removeprefix('flow-').upper()}"
    return f"AD-GG-FLOW-{role.upper()}"


def build_ad_group_catalog() -> list[dict[str, Any]]:
    return [
        {
            "name": ad_group_name(role),
            "role": role,
            "description": description,
            "source": "Active Directory (simuliert)",
            "ad_dn": (
                f"CN={ad_group_name(role)},OU=FLOW-Groups,OU=Demo,"
                "DC=flowcorp,DC=example,DC=invalid"
            ),
        }
        for role, description in REALM_ROLES
    ]


def group_assignments_text(users: list[dict[str, Any]]) -> str:
    rows = ["username;role", "platform-admin;platform-admin"]
    rows.extend(
        f"{user['username']};{role}"
        for user in users
        for role in user["roles"]
    )
    rows.extend(f"{username};{role}" for username, *_, roles in ROLE_DEMO_USERS for role in roles)
    return "\n".join(rows) + "\n"


def build_users() -> list[dict[str, Any]]:
    users: list[dict[str, Any]] = []
    department_index = 0
    department_used = 0
    for number, (first_name, last_name) in enumerate(NAMES, start=1):
        department, department_role, department_count = DEPARTMENTS[department_index]
        department_used += 1
        if department_used == department_count:
            department_index += 1
            department_used = 0

        site_id = "BER" if number <= 30 else "HAM"
        roles = ["desksharing-user", "dms-user", "work-user", department_role]
        if department in {"Vertrieb", "Finanzen", "Projekte & Engineering"}:
            roles.append("management-user")
        if department in {"Vertrieb", "Produktion", "Qualität", "Lager", "Finanzen"}:
            roles.append("grafana-viewer")
        if department in {"Projekte & Engineering", "IT"}:
            roles.append("ai-user")
        if department in {
            "Vertrieb", "Disposition", "Produktion", "Qualität", "Projekte & Engineering"
        }:
            roles.append("requirements-user")
        if department in {"Projekte & Engineering", "IT"} and number in {44, 49}:
            roles.append("work-admin")
        if department == "Personal" and number == 36:
            roles.append("hr-admin")
        if department == "IT" and number == 49:
            roles.append("desksharing-admin")
        if number == 1:
            # demo01 is the deliberate cross-application presentation account.
            # Full access remains group-derived so the AD -> Keycloak chain is visible.
            roles.append("platform-admin")

        users.append(
            {
                "id": f"USR-{number:03d}",
                "username": f"demo{number:02d}",
                "first_name": first_name,
                "last_name": last_name,
                "name": f"{first_name} {last_name}",
                "email": f"demo{number:02d}@example.invalid",
                "department": department,
                "site_id": site_id,
                "roles": roles,
                "manager": number in {1, 6, 11, 16, 26, 31, 36, 40, 44, 49},
            }
        )
    return users


def build_desks() -> list[dict[str, Any]]:
    desks: list[dict[str, Any]] = []
    for site_id in ("BER", "HAM"):
        for number in range(1, 51):
            floor = "EG" if number <= 25 else "1. OG"
            floor_number = number if number <= 25 else number - 25
            zone = (
                "Fokus"
                if floor_number <= 8
                else "Team"
                if floor_number <= 18
                else "Projekt"
            )
            floor_code = "EG" if floor == "EG" else "1OG"
            room_code = {"Fokus": "FOK", "Team": "TEAM", "Projekt": "PROJ"}[zone]
            room_id = f"{site_id}-{floor_code}-{room_code}"
            if zone == "Fokus":
                index = floor_number - 1
                map_x = 10 + (index % 2) * 12
                map_y = 14 + (index // 2) * 10
            elif zone == "Team":
                index = floor_number - 9
                map_x = 42 + (index % 5) * 11
                map_y = 20 + (index // 5) * 18
            else:
                index = floor_number - 19
                map_x = 11 + index * 12
                map_y = 74
            features = ["27-Zoll-Monitor", "USB-C-Dock"]
            if number % 3 == 0:
                features.append("Höhenverstellbar")
            if number % 10 == 0:
                features.append("Barrierearm")
            if number % 7 == 0:
                features.append("Dual-Monitor")
            desks.append(
                {
                    "id": f"{site_id}-D{number:03d}",
                    "site_id": site_id,
                    "floor": floor,
                    "zone": zone,
                    "room_id": room_id,
                    "number": number,
                    "label": f"{site_id} · {floor} · {floor_number:02d}",
                    "map_x": map_x,
                    "map_y": map_y,
                    "type": "focus" if zone == "Fokus" else "standard",
                    "features": features,
                    "accessible": "Barrierearm" in features,
                    "status": "active",
                }
            )
    return desks


def build_rooms() -> list[dict[str, Any]]:
    names = {
        "BER": {
            "EG": ("Fokusraum Spree", "Teamraum Kreuzberg", "Projektraum Tegel"),
            "1. OG": ("Fokusraum Havel", "Teamraum Mitte", "Projektraum Tempelhof"),
        },
        "HAM": {
            "EG": ("Fokusraum Alster", "Teamraum HafenCity", "Projektraum Elbe"),
            "1. OG": ("Fokusraum Fleet", "Teamraum Speicherstadt", "Projektraum Blankenese"),
        },
    }
    layouts = (
        ("FOK", "Fokus", 3, 5, 28, 46, 31, 52, 8),
        ("TEAM", "Team", 35, 5, 62, 46, 69, 52, 10),
        ("PROJ", "Projekt", 3, 57, 94, 35, 50, 92, 7),
    )
    rooms: list[dict[str, Any]] = []
    for site_id in ("BER", "HAM"):
        for floor in ("EG", "1. OG"):
            floor_code = "EG" if floor == "EG" else "1OG"
            for index, (code, zone, x, y, width, height, door_x, door_y, capacity) in enumerate(layouts):
                rooms.append(
                    {
                        "id": f"{site_id}-{floor_code}-{code}",
                        "site_id": site_id,
                        "floor": floor,
                        "name": names[site_id][floor][index],
                        "zone": zone,
                        "capacity": capacity,
                        "map": {
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                            "door_x": door_x,
                            "door_y": door_y,
                        },
                        "directions": (
                            "links vom zentralen Flur" if zone == "Fokus"
                            else "rechts vom zentralen Flur" if zone == "Team"
                            else "geradeaus hinter dem zentralen Flur"
                        ),
                    }
                )
    return rooms


def protocol_mappers() -> list[dict[str, Any]]:
    return [
        {
            "name": "realm roles",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-realm-role-mapper",
            "consentRequired": False,
            "config": {
                "multivalued": "true",
                "userinfo.token.claim": "true",
                "id.token.claim": "true",
                "access.token.claim": "true",
                "claim.name": "roles",
                "jsonType.label": "String",
            },
        },
        {
            "name": "desksharing user id",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-attribute-mapper",
            "consentRequired": False,
            "config": {
                "user.attribute": "desksharing_user_id",
                "claim.name": "desksharing_user_id",
                "jsonType.label": "String",
                "id.token.claim": "true",
                "access.token.claim": "true",
                "userinfo.token.claim": "true",
            },
        },
        {
            "name": "department",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-attribute-mapper",
            "consentRequired": False,
            "config": {
                "user.attribute": "department",
                "claim.name": "department",
                "jsonType.label": "String",
                "id.token.claim": "true",
                "access.token.claim": "true",
                "userinfo.token.claim": "true",
            },
        },
    ]


def client(
    client_id: str,
    name: str,
    redirects: list[str],
    origins: list[str],
    *,
    secret: str | None = None,
    pkce: bool = True,
) -> dict[str, Any]:
    logout_redirects = "##".join(f"{origin.rstrip('/')}/*" for origin in origins)
    result = {
        "clientId": client_id,
        "name": name,
        "enabled": True,
        "publicClient": secret is None,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False,
        "redirectUris": redirects,
        "webOrigins": origins,
        "attributes": {"post.logout.redirect.uris": logout_redirects},
        "protocolMappers": protocol_mappers(),
    }
    # Keycloak merges client attribute maps on updates. An explicit empty
    # value is therefore required to remove an earlier PKCE requirement from
    # a confidential client such as ERPNext/Frappe, which does not emit PKCE.
    result["attributes"]["pkce.code.challenge.method"] = "S256" if pkce else ""
    if secret is not None:
        result["clientAuthenticatorType"] = "client-secret"
        result["secret"] = secret
    return result


def build_realm(users: list[dict[str, Any]]) -> dict[str, Any]:
    # Freigabe- und Projektrollen sind bewusst nicht Teil von platform-admin (Funktionstrennung).
    all_roles = [name for name, _ in REALM_ROLES
                 if name != "platform-admin" and name not in DECISION_ROLES and name not in ALL_PROJECT_ROLES]
    roles = [
        {"name": name, "description": description}
        for name, description in REALM_ROLES
        if name != "platform-admin"
    ]
    roles.append(
        {
            "name": "platform-admin",
            "description": "Vollzugriff auf alle Plattformbereiche",
            "composite": True,
            "composites": {"realm": all_roles},
        }
    )
    ad_groups = build_ad_group_catalog()
    groups = [
        {
            "name": group["name"],
            "realmRoles": [group["role"]],
            "attributes": {
                "source": [group["source"]],
                "ad_dn": [group["ad_dn"]],
                "managed_by": ["AD-Simulation"],
            },
        }
        for group in ad_groups
    ]
    keycloak_users = [
        {
            "username": "platform-admin",
            "enabled": True,
            "emailVerified": True,
            "firstName": "Plattform",
            "lastName": "Administrator",
            "email": "platform-admin@example.invalid",
            "attributes": {
                "desksharing_user_id": ["platform-admin"],
                "department": ["IT"],
            },
            "groups": [f"/{ad_group_name('platform-admin')}"],
            "clientRoles": {"realm-management": ["realm-admin"]},
            "credentials": [
                {"type": "password", "value": DEMO_ADMIN_PASSWORD, "temporary": True}
            ],
        }
    ]
    for user in users:
        definition = {
                "username": user["username"],
                "enabled": True,
                "emailVerified": True,
                "firstName": user["first_name"],
                "lastName": user["last_name"],
                "email": user["email"],
                "attributes": {
                    "desksharing_user_id": [user["id"]],
                    "department": [user["department"]],
                    "home_site": [user["site_id"]],
                },
                "groups": [f"/{ad_group_name(role)}" for role in user["roles"]],
                "credentials": [
                    {"type": "password", "value": DEMO_USER_PASSWORD, "temporary": False}
                ],
            }
        if user["username"] == "demo01":
            # The guided demo account must also be able to show the Keycloak
            # group inheritance in the realm administration console.
            definition["clientRoles"] = {"realm-management": ["realm-admin"]}
        keycloak_users.append(definition)
    for username, first_name, last_name, department, role_names in ROLE_DEMO_USERS:
        definition = {
            "username": username,
            "enabled": True,
            "emailVerified": True,
            "firstName": first_name,
            "lastName": last_name,
            "email": f"{username}@example.invalid",
            "attributes": {"department": [department], "demo_purpose": ["Freigabeprozess FLOWAGENTS"]},
            "groups": [f"/{ad_group_name(role)}" for role in role_names],
            "credentials": [{"type": "password", "value": DEMO_USER_PASSWORD, "temporary": False}],
        }
        if "platform-admin" in role_names:
            definition["clientRoles"] = {"realm-management": ["realm-admin"]}
        keycloak_users.append(definition)

    return {
        "realm": REALM,
        "enabled": True,
        "displayName": "Open Manufacturing Platform",
        "sslRequired": "none",
        "registrationAllowed": False,
        "resetPasswordAllowed": True,
        "rememberMe": True,
        "loginWithEmailAllowed": True,
        "bruteForceProtected": True,
        "roles": {"realm": roles},
        "groups": groups,
        "clients": [
            client(
                "platform-portal",
                "Portal, FLOWWORK, MES, HR, FLOWFIN und Desksharing",
                ["http://localhost:8088/auth/callback", "http://127.0.0.1:8088/auth/callback"],
                ["http://localhost:8088", "http://127.0.0.1:8088"],
            ),
            client(
                "erpnext",
                "ERPNext",
                [
                    "http://localhost:8081/api/method/frappe.integrations.oauth2_logins.login_via_keycloak"
                ],
                ["http://localhost:8081"],
                secret=ERPNEXT_OIDC_CLIENT_SECRET,
                pkce=False,
            ),
            client("paperless", "Paperless-ngx", ["http://localhost:8010/*"], ["http://localhost:8010"]),
            client("grafana", "Grafana", ["http://localhost:3000/login/generic_oauth"], ["http://localhost:3000"]),
            client("open-webui", "Open WebUI", ["http://localhost:3001/oauth/oidc/callback"], ["http://localhost:3001"]),
            client(
                "agentgateway-ui",
                "FLOWGATE · KI-Gateway-Verwaltung",
                ["http://localhost:4001/oauth/callback"],
                ["http://localhost:4001"],
                secret=AGENTGATEWAY_OIDC_CLIENT_SECRET,
            ),
            client("documentation", "Prozessdokumentation", ["http://localhost:8001/*"], ["http://localhost:8001"]),
        ],
        "users": keycloak_users,
    }


def build_scenario_domains(
    users: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    iam = {
        "realm": REALM,
        "admin": {
            "username": "platform-admin",
            "name": "Plattform Administrator",
            "roles": ["platform-admin"],
        },
        "systems": ["Portal", "FLOWWORK", "Redmine", "Desksharing", "MES", "HR", "ERPNext", "DMS", "Grafana", "Open WebUI", "Agentgateway", "Dokumentation"],
        "directory": {
            "name": "FLOWCORP Active Directory",
            "domain": "flowcorp.example.invalid",
            "mode": "simulated",
            "users": len(users) + 1 + len(ROLE_DEMO_USERS),
            "groups": build_ad_group_catalog(),
            "sync": "AD/LDAP → Keycloak User Federation",
            "authorization_chain": "AD-Sicherheitsgruppe → Keycloak-Gruppe → Realm-Rolle → Anwendung",
            "production_note": "Die Demo bildet die AD-Herkunft mit deterministischen Gruppen ab; im Livebetrieb ersetzt die LDAP-Föderation diesen Import.",
        },
        "users": users,
        # Konten für den Benutzerwechsel in der Demo (Portal-Kopfzeile). Rollen kommen wie im
        # Livebetrieb aus den AD-Gruppen; das Portal zeigt sie nur an und meldet über Keycloak neu an.
        "demo_accounts": [
            {
                "username": username,
                "name": f"{first_name} {last_name}",
                "department": department,
                "function": demo_function(role_names),
                "groups": sorted(ad_group_name(role) for role in role_names),
                "roles": sorted(role_names),
                "projects": {
                    code: ("aendern" if project_role(code, "aendern") in role_names
                           else "lesen" if project_role(code, "lesen") in role_names else "")
                    for code in PROJECT_CATALOG
                },
            }
            for username, first_name, last_name, department, role_names in ROLE_DEMO_USERS
        ],
        "projects": {code: {"title": spec["title"], "domain": spec["domain"], "criticality": spec["criticality"],
                            "groups": {right: ad_group_name(project_role(code, right)) for right in ("lesen", "aendern")}}
                     for code, spec in PROJECT_CATALOG.items()},
    }
    desksharing = {
        "settings": {
            "booking_horizon_days": 180,
            "slots": ["full_day", "morning", "afternoon"],
            "checkin_grace_minutes": 60,
        },
        "sites": [
            {
                "id": "BER",
                "name": "Berlin · Werk & Büro",
                "address": "Industriestraße 24, 10587 Berlin",
                "timezone": "Europe/Berlin",
                "building_code": "BER-01",
                "entry_label": "Haupteingang am Empfang Berlin",
                "desk_count": 50,
                "floors": ["EG", "1. OG"],
            },
            {
                "id": "HAM",
                "name": "Hamburg · Projektbüro",
                "address": "Am Sandtorkai 18, 20457 Hamburg",
                "timezone": "Europe/Berlin",
                "building_code": "HAM-01",
                "entry_label": "Haupteingang am Empfang Hamburg",
                "desk_count": 50,
                "floors": ["EG", "1. OG"],
            },
        ],
        "rooms": build_rooms(),
        "desks": build_desks(),
        "bookings": [
            {"id": "DSB-0001", "user_id": "USR-001", "desk_id": "BER-D001", "date": "2026-11-05", "slot": "full_day", "status": "checked_in", "created_at": "2026-10-28T08:15:00+00:00"},
            {"id": "DSB-0002", "user_id": "USR-006", "desk_id": "BER-D012", "date": "2026-11-05", "slot": "morning", "status": "booked", "created_at": "2026-10-29T10:00:00+00:00"},
            {"id": "DSB-0003", "user_id": "USR-016", "desk_id": "BER-D029", "date": "2026-11-05", "slot": "full_day", "status": "booked", "created_at": "2026-10-30T09:30:00+00:00"},
            {"id": "DSB-0004", "user_id": "USR-021", "desk_id": "BER-D042", "date": "2026-11-05", "slot": "full_day", "status": "booked", "created_at": "2026-10-30T10:00:00+00:00"},
            {"id": "DSB-0005", "user_id": "USR-031", "desk_id": "HAM-D003", "date": "2026-11-05", "slot": "full_day", "status": "booked", "created_at": "2026-10-30T11:00:00+00:00"},
            {"id": "DSB-0006", "user_id": "USR-041", "desk_id": "HAM-D017", "date": "2026-11-05", "slot": "afternoon", "status": "booked", "created_at": "2026-10-31T07:45:00+00:00"},
            {"id": "DSB-0007", "user_id": "USR-044", "desk_id": "HAM-D032", "date": "2026-11-05", "slot": "full_day", "status": "checked_in", "created_at": "2026-11-01T08:00:00+00:00"},
            {"id": "DSB-0008", "user_id": "USR-049", "desk_id": "HAM-D046", "date": "2026-11-05", "slot": "full_day", "status": "booked", "created_at": "2026-11-01T08:20:00+00:00"},
            {"id": "DSB-0009", "user_id": "USR-003", "desk_id": "BER-D020", "date": "2026-11-06", "slot": "full_day", "status": "booked", "created_at": "2026-11-02T09:00:00+00:00"},
            {"id": "DSB-0010", "user_id": "USR-034", "desk_id": "HAM-D028", "date": "2026-11-06", "slot": "full_day", "status": "booked", "created_at": "2026-11-02T09:10:00+00:00"},
        ],
        "audit": [],
    }
    work = build_work_domain()
    return iam, desksharing, work


def build_work_domain() -> dict[str, Any]:
    timestamp = "2026-11-04T08:00:00+00:00"
    return {
        "projects": [
            {
                "id": 1,
                "identifier": "scu-100",
                "name": "SCU-100 Produktentwicklung",
                "description": "Kundenprojekt NordMarine · Kommission KOM-4711",
                "status": 1,
                "url": "http://localhost:8011/projects/scu-100",
            },
            {
                "id": 2,
                "identifier": "platform-rollout",
                "name": "Open Manufacturing Rollout",
                "description": "Einführung der integrierten Unternehmensplattform",
                "status": 1,
                "url": "http://localhost:8011/projects/platform-rollout",
            },
        ],
        "issues": [
            {
                "id": "101", "key": "#101", "subject": "CAN-Kommunikation spezifizieren",
                "description": "Schnittstellenparameter aus Kundenanforderung ableiten.",
                "status": "In Bearbeitung", "project": "SCU-100 Produktentwicklung",
                "priority": "Hoch", "assignee": "Helena Friedrich", "due_date": "2026-11-08",
                "done_ratio": 55, "updated_on": timestamp, "url": "/work#issue-101", "source": "demo",
            },
            {
                "id": "102", "key": "#102", "subject": "EMV-Prüfplan freigeben",
                "description": "Review und Freigabe des Verifikationsnachweises.",
                "status": "Prüfung", "project": "SCU-100 Produktentwicklung",
                "priority": "Normal", "assignee": "Moritz Köhler", "due_date": "2026-11-06",
                "done_ratio": 80, "updated_on": timestamp, "url": "/work#issue-102", "source": "demo",
            },
            {
                "id": "103", "key": "#103", "subject": "Seriennummern-Rückmeldung im MES",
                "description": "Pflichtprüfung und API-Mapping ergänzen.",
                "status": "Erledigt", "project": "Open Manufacturing Rollout",
                "priority": "Hoch", "assignee": "Tim Krüger", "due_date": "2026-11-02",
                "done_ratio": 100, "updated_on": timestamp, "url": "/work#issue-103", "source": "demo",
            },
            {
                "id": "104", "key": "#104", "subject": "Lieferantendokumente mit Projekt verknüpfen",
                "description": "DMS-Metadaten und Wiki-Anleitung abstimmen.",
                "status": "Neu", "project": "SCU-100 Produktentwicklung",
                "priority": "Normal", "assignee": "Felix Hoffmann", "due_date": "2026-11-15",
                "done_ratio": 0, "updated_on": timestamp, "url": "/work#issue-104", "source": "demo",
            },
        ],
        "wiki": [
            {"title": "SCU-100_Requirements", "version": 7, "project": "SCU-100 Produktentwicklung", "updated_on": timestamp, "url": "http://localhost:8011/projects/scu-100/wiki/SCU-100_Requirements"},
            {"title": "SCU-100_Verification", "version": 4, "project": "SCU-100 Produktentwicklung", "updated_on": timestamp, "url": "http://localhost:8011/projects/scu-100/wiki/SCU-100_Verification"},
            {"title": "Platform_Betrieb", "version": 3, "project": "Open Manufacturing Rollout", "updated_on": timestamp, "url": "http://localhost:8011/projects/platform-rollout/wiki/Platform_Betrieb"},
        ],
        "requirements": [
            {
                "id": "REQ-SCU-001", "title": "CAN-Bus Kommunikation", "text": "Die SCU muss Prozessdaten über CAN 2.0B mit 500 kbit/s austauschen.",
                "type": "Interface", "priority": "Must", "owner": "Helena Friedrich", "parent_id": None,
                "acceptance_criteria": "Kommunikation mit 95 % Buslast über 8 Stunden fehlerfrei.",
                "status": "approved", "version": 3, "issue_id": "#101", "wiki_title": "SCU-100_Requirements",
                "verification": "TC-CAN-042", "created_at": timestamp, "updated_at": timestamp,
                "history": [{"version": 3, "actor": "System Engineering", "at": timestamp, "note": "Review freigegeben"}],
            },
            {
                "id": "REQ-SCU-002", "title": "Eindeutige Seriennummer", "text": "Jedes ausgelieferte Gerät muss eine eindeutige, rückverfolgbare Seriennummer besitzen.",
                "type": "System", "priority": "Must", "owner": "Moritz Köhler", "parent_id": None,
                "acceptance_criteria": "Seriennummer ist in ERP, MES und Prüfprotokoll identisch.",
                "status": "verified", "version": 2, "issue_id": "#103", "wiki_title": "SCU-100_Verification",
                "verification": "E2E-SERIAL-007", "created_at": timestamp, "updated_at": timestamp,
                "history": [{"version": 2, "actor": "Qualität", "at": timestamp, "note": "E2E-Test bestanden"}],
            },
            {
                "id": "REQ-SCU-003", "title": "EMV-Störfestigkeit", "text": "Das Gerät muss die vereinbarten industriellen EMV-Grenzwerte einhalten.",
                "type": "Hardware", "priority": "Must", "owner": "Moritz Köhler", "parent_id": None,
                "acceptance_criteria": "Freigegebener Prüfbericht ohne Major-Abweichung.",
                "status": "review", "version": 4, "issue_id": "#102", "wiki_title": "SCU-100_Verification",
                "verification": "EMV-REPORT-PENDING", "created_at": timestamp, "updated_at": timestamp,
                "history": [{"version": 4, "actor": "Qualität", "at": timestamp, "note": "Prüfbericht im Review"}],
            },
            {
                "id": "REQ-SCU-004", "title": "Dokumentenlieferung zum Meilenstein", "text": "Freigegebene Produktdokumente müssen zehn Arbeitstage vor FAT vollständig vorliegen.",
                "type": "Stakeholder", "priority": "Should", "owner": "Alexander Vogel", "parent_id": None,
                "acceptance_criteria": "DMS-Dashboard zeigt 100 % termingerecht und freigegeben.",
                "status": "draft", "version": 1, "issue_id": "#104", "wiki_title": "SCU-100_Requirements",
                "verification": None, "created_at": timestamp, "updated_at": timestamp,
                "history": [{"version": 1, "actor": "Projektleitung", "at": timestamp, "note": "Anforderung angelegt"}],
            },
            {
                "id": "REQ-SCU-005", "title": "Fehlersichere Zeitbuchung", "text": "Arbeitsgänge dürfen nur auf freigegebene Aufträge und aktive Mitarbeiter gebucht werden.",
                "type": "Software", "priority": "Must", "owner": "Tim Krüger", "parent_id": "REQ-SCU-002",
                "acceptance_criteria": "Ungültige Kombinationen werden mit nachvollziehbarer Meldung abgewiesen.",
                "status": "approved", "version": 2, "issue_id": None, "wiki_title": "SCU-100_Requirements",
                "verification": "MES-TIME-012", "created_at": timestamp, "updated_at": timestamp,
                "history": [{"version": 2, "actor": "Product Owner", "at": timestamp, "note": "Akzeptanzkriterium ergänzt"}],
            },
        ],
        "baselines": [
            {
                "id": "BL-SCU-001", "name": "System Requirements Review 1", "description": "Freigegebener Stand zum SRR",
                "status": "frozen", "created_at": timestamp, "created_by": "System Engineering",
                "items": [
                    {"requirement_id": "REQ-SCU-001", "version": 3, "status": "approved", "checksum_source": "REQ-SCU-001:3"},
                    {"requirement_id": "REQ-SCU-002", "version": 2, "status": "verified", "checksum_source": "REQ-SCU-002:2"},
                ],
            }
        ],
        "activity": [
            {"actor": "Qualität", "message": "REQ-SCU-003 in Review gesetzt", "at": timestamp},
            {"actor": "System Engineering", "message": "Baseline BL-SCU-001 eingefroren", "at": timestamp},
        ],
    }


def json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def render() -> tuple[str, str, str, str]:
    users = build_users()
    scenario = json.loads(SCENARIO_FILE.read_text(encoding="utf-8"))
    iam, desksharing, _work = build_scenario_domains(users)
    scenario["iam"] = iam
    scenario["desksharing"] = desksharing
    realm = build_realm(users)
    partial_import = {
        "ifResourceExists": "OVERWRITE",
        "policy": "OVERWRITE",
        "groups": realm["groups"],
        "users": realm["users"],
    }
    return (
        json_text(realm),
        json_text(scenario),
        group_assignments_text(users),
        json_text(partial_import),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail when generated files drift")
    args = parser.parse_args()
    realm_text, scenario_text, assignments_text, partial_import_text = render()
    if args.check:
        in_sync = (
            REALM_FILE.read_text(encoding="utf-8") == realm_text
            and SCENARIO_FILE.read_text(encoding="utf-8") == scenario_text
            and GROUP_ASSIGNMENTS_FILE.read_text(encoding="utf-8") == assignments_text
            and AD_PARTIAL_IMPORT_FILE.read_text(encoding="utf-8") == partial_import_text
        )
        if not in_sync:
            print("IAM demo artifacts are out of date; run scripts/generate_iam_demo.py")
            return 1
        print("IAM demo artifacts are in sync")
        return 0
    REALM_FILE.write_text(realm_text, encoding="utf-8")
    SCENARIO_FILE.write_text(scenario_text, encoding="utf-8")
    GROUP_ASSIGNMENTS_FILE.write_text(assignments_text, encoding="utf-8")
    AD_PARTIAL_IMPORT_FILE.write_text(partial_import_text, encoding="utf-8")
    print(f"Generated 50 demo identities plus {len(ROLE_DEMO_USERS)} approval-role accounts, AD group model, "
          "100 mapped desks and Keycloak realm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
