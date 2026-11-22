"""Idempotent Paperless governance seed for roles, projects and approvals.

The read-only DMS MCP intentionally remains separate from this administrative
client.  This module is only used by the one-shot Compose seed service.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from pathlib import Path
from typing import Any


class GovernanceError(RuntimeError):
    """Raised for invalid governance configuration or Paperless API errors."""


class PaperlessAdminApi:
    """Small write-capable client used only by the governance seed."""

    def __init__(
        self,
        base_url: str,
        username: str = "",
        password: str = "",
        token: str = "",
        timeout: float = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token = token
        self.timeout = timeout
        self._cache: dict[str, list[dict[str, Any]]] = {}

    def authenticate(self) -> None:
        if self.token:
            return
        if not self.username or not self.password:
            raise GovernanceError("Paperless username and password are required")
        response = self._request(
            "POST",
            "/api/token/",
            {"username": self.username, "password": self.password},
            authenticated=False,
        )
        token = response.get("token") if isinstance(response, dict) else None
        if not token:
            raise GovernanceError("Paperless did not return an API token")
        self.token = str(token)

    def _request(
        self,
        method: str,
        path_or_url: str,
        payload: dict[str, Any] | None = None,
        *,
        authenticated: bool = True,
    ) -> Any:
        url = (
            path_or_url
            if path_or_url.startswith(("http://", "https://"))
            else f"{self.base_url}/{path_or_url.lstrip('/')}"
        )
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if authenticated:
            if not self.token:
                self.authenticate()
            headers["Authorization"] = f"Token {self.token}"
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise GovernanceError(
                f"Paperless {method} {urllib.parse.urlsplit(url).path} failed "
                f"with HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise GovernanceError(f"Paperless is unavailable at {self.base_url}: {exc}") from exc
        return json.loads(raw) if raw else {}

    def list_resource(self, resource: str, *, refresh: bool = False) -> list[dict[str, Any]]:
        if not refresh and resource in self._cache:
            return self._cache[resource]
        page: str | None = f"/api/{resource}/?page_size=100"
        items: list[dict[str, Any]] = []
        while page:
            response = self._request("GET", page)
            if isinstance(response, list):
                items.extend(response)
                break
            if not isinstance(response, dict) or not isinstance(response.get("results"), list):
                raise GovernanceError(f"Unexpected list response for {resource}")
            items.extend(response["results"])
            page = response.get("next")
        self._cache[resource] = items
        return items

    def find(self, resource: str, key: str, value: Any) -> dict[str, Any] | None:
        return next(
            (item for item in self.list_resource(resource) if item.get(key) == value),
            None,
        )

    def upsert(
        self,
        resource: str,
        key: str,
        value: Any,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        existing = self.find(resource, key, value)
        if existing is None:
            result = self._request("POST", f"/api/{resource}/", payload)
            if not isinstance(result, dict):
                raise GovernanceError(f"Unexpected create response for {resource}")
            self.list_resource(resource).append(result)
            return result, "created"
        result = self._request("PATCH", f"/api/{resource}/{existing['id']}/", payload)
        if not isinstance(result, dict):
            raise GovernanceError(f"Unexpected update response for {resource}")
        existing.clear()
        existing.update(result)
        return existing, "updated"

    def patch(self, resource: str, object_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        result = self._request("PATCH", f"/api/{resource}/{object_id}/", payload)
        if not isinstance(result, dict):
            raise GovernanceError(f"Unexpected patch response for {resource}/{object_id}")
        return result


class GovernanceSeeder:
    """Resolve a declarative governance file to Paperless API objects."""

    PROJECT_LANES = ("Lesen", "Bearbeiten", "Pruefen", "Freigeben")

    def __init__(self, api: PaperlessAdminApi, config: dict[str, Any]) -> None:
        self.api = api
        self.config = deepcopy(config)
        self.ids: dict[str, dict[str, int]] = {}
        self.actions: list[str] = []
        self.projects: dict[str, dict[str, Any]] = {}
        self.protected_areas: dict[str, dict[str, Any]] = {}

    def validate(self) -> None:
        if self.config.get("schema_version") != 1:
            raise GovernanceError("governance schema_version must be 1")
        required = ("roles", "access_groups", "metadata", "project_templates", "projects")
        missing = [key for key in required if key not in self.config]
        if missing:
            raise GovernanceError(f"governance config is missing: {', '.join(missing)}")
        templates = self.config["project_templates"]
        project_codes: set[str] = set()
        for project in self.config["projects"]:
            code = project.get("code", "")
            if not code or code in project_codes:
                raise GovernanceError(f"project code is missing or duplicated: {code!r}")
            if project.get("template") not in templates:
                raise GovernanceError(
                    f"project {code} references unknown template {project.get('template')!r}"
                )
            project_codes.add(code)
        access_groups = set(self.config["access_groups"])
        tag_names = {item.get("name") for item in self.config["metadata"]["tags"]}
        area_names: set[str] = set()
        for area in self.config.get("protected_areas", []):
            name = area.get("name", "")
            group = area.get("access_group", "")
            if not name or group not in access_groups:
                raise GovernanceError(
                    f"protected area {name!r} references unknown access group {group!r}"
                )
            if not area.get("filename_patterns"):
                raise GovernanceError(f"protected area {name!r} has no filename patterns")
            area_names.add(name)
        if area_names and "Vertraulich/Personal" not in tag_names:
            raise GovernanceError("protected areas require tag 'Vertraulich/Personal'")
        for document in self.config.get("protected_documents", []):
            if document.get("area") not in area_names:
                raise GovernanceError(
                    f"protected document references unknown area {document.get('area')!r}"
                )

    def add_project(
        self,
        template: str,
        code: str,
        name: str,
        filename_patterns: list[str] | None = None,
    ) -> None:
        if template not in self.config.get("project_templates", {}):
            raise GovernanceError(f"unknown project template: {template}")
        projects = [project for project in self.config["projects"] if project["code"] != code]
        projects.append(
            {
                "template": template,
                "code": code,
                "name": name,
                "filename_patterns": filename_patterns or [f"*{code}*"],
            }
        )
        self.config["projects"] = projects

    def _remember(self, resource: str, name: str, result: dict[str, Any], action: str) -> int:
        object_id = result.get("id")
        if not isinstance(object_id, int):
            raise GovernanceError(f"Paperless {resource} {name!r} has no numeric id")
        self.ids.setdefault(resource, {})[name] = object_id
        self.actions.append(f"{action}: {resource}/{name}")
        return object_id

    def _upsert(self, resource: str, name: str, payload: dict[str, Any]) -> int:
        result, action = self.api.upsert(resource, "name", name, payload)
        return self._remember(resource, name, result, action)

    def _group_ids(self, names: list[str] | tuple[str, ...]) -> list[int]:
        try:
            return [self.ids["groups"][name] for name in names]
        except KeyError as exc:
            raise GovernanceError(f"unknown group in governance config: {exc.args[0]}") from exc

    def _object_permissions(
        self,
        view_groups: list[str] | tuple[str, ...],
        change_groups: list[str] | tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "view": {"users": [], "groups": self._group_ids(view_groups)},
            "change": {"users": [], "groups": self._group_ids(change_groups)},
        }

    def _seed_groups(self) -> None:
        for role in self.config["roles"]:
            # Paperless 3.4 documents permissions with their Django app label,
            # but the group serializer accepts the codename only.
            permission_codenames = [
                permission.rsplit(".", 1)[-1] for permission in role["permissions"]
            ]
            self._upsert(
                "groups",
                role["name"],
                {"name": role["name"], "permissions": permission_codenames},
            )
        for name in self.config["access_groups"]:
            self._upsert("groups", name, {"name": name, "permissions": []})

    def _admin_id(self) -> int:
        username = self.config.get("owner_username") or self.api.username
        admin = self.api.find("users", "username", username)
        if not admin or not isinstance(admin.get("id"), int):
            raise GovernanceError(f"Paperless owner user {username!r} does not exist")
        return admin["id"]

    def _metadata_permissions(self) -> dict[str, Any]:
        role_names = [role["name"] for role in self.config["roles"]]
        return self._object_permissions(role_names, ["DMS-Administration"])

    def _seed_metadata(self, owner_id: int) -> None:
        metadata = self.config["metadata"]
        permissions = self._metadata_permissions()
        for field in metadata["custom_fields"]:
            payload = {
                "name": field["name"],
                "data_type": field["data_type"],
                "extra_data": field.get("extra_data"),
            }
            self._upsert("custom_fields", field["name"], payload)
        for resource, entries in (
            ("tags", metadata["tags"]),
            ("document_types", metadata["document_types"]),
            ("storage_paths", metadata.get("storage_paths", [])),
        ):
            for entry in entries:
                payload = {**entry, "owner": owner_id, "set_permissions": permissions}
                self._upsert(resource, entry["name"], payload)

    def _project_group_name(self, code: str, lane: str) -> str:
        return f"DMS-Projekt-{code}-{lane}"

    def _project_groups(self, code: str) -> dict[str, str]:
        return {lane: self._project_group_name(code, lane) for lane in self.PROJECT_LANES}

    def _project_view_groups(self, project: dict[str, Any]) -> list[str]:
        return [*project["groups"].values(), "DMS-Administration"]

    def _project_change_groups(self, project: dict[str, Any], state: str) -> list[str]:
        groups = project["groups"]
        lanes_by_state = {
            "Entwurf": ["Bearbeiten", "Pruefen", "Freigeben"],
            "In Prüfung": ["Pruefen", "Freigeben"],
            "Zur Freigabe": ["Freigeben"],
            "Freigegeben": ["Freigeben"],
            "Abgelehnt": ["Bearbeiten", "Freigeben"],
            "Obsolet": ["Freigeben"],
        }
        return [*(groups[lane] for lane in lanes_by_state[state]), "DMS-Administration"]

    def _seed_project(self, raw: dict[str, Any], owner_id: int) -> dict[str, Any]:
        code = raw["code"]
        template = self.config["project_templates"][raw["template"]]
        groups = self._project_groups(code)
        for group_name in groups.values():
            self._upsert("groups", group_name, {"name": group_name, "permissions": []})

        view_groups = [*groups.values(), "DMS-Administration"]
        metadata_permissions = self._object_permissions(view_groups, ["DMS-Administration"])
        tag_name = f"Projekt/{code}"
        tag_id = self._upsert(
            "tags",
            tag_name,
            {
                "name": tag_name,
                "color": template["tag_color"],
                "match": code,
                "matching_algorithm": 3,
                "is_insensitive": True,
                "is_inbox_tag": False,
                "owner": owner_id,
                "set_permissions": metadata_permissions,
            },
        )
        storage_name = f"Projekt/{code}"
        storage_path = template["storage_path"].replace("{code}", code)
        storage_id = self._upsert(
            "storage_paths",
            storage_name,
            {
                "name": storage_name,
                "path": storage_path,
                "match": code,
                "matching_algorithm": 3,
                "is_insensitive": True,
                "owner": owner_id,
                "set_permissions": metadata_permissions,
            },
        )
        project = {
            **raw,
            "groups": groups,
            "tag_id": tag_id,
            "tag_name": tag_name,
            "storage_id": storage_id,
            "storage_name": storage_name,
            "template_config": template,
        }
        self.projects[code] = project
        self._seed_project_intake_workflow(project)
        self._seed_project_approval_workflows(project)
        return project

    def _seed_base_intake_workflow(self) -> None:
        draft_id = self.ids["tags"]["Status/Entwurf"]
        field_ids = list(self.ids["custom_fields"].values())
        access = ["DMS-Eingang", "DMS-Administration"]
        payload = {
            "name": "DMS | Eingang | Klassifizieren",
            "order": 10,
            "enabled": True,
            "triggers": [{"type": 2, "sources": [1, 2, 3, 4]}],
            "actions": [
                {
                    "type": 1,
                    "assign_tags": [draft_id],
                    "assign_view_groups": self._group_ids(access),
                    "assign_change_groups": self._group_ids(access),
                    "assign_custom_fields": field_ids,
                }
            ],
        }
        self._upsert("workflows", payload["name"], payload)

    def _seed_protected_area(self, raw: dict[str, Any], owner_id: int) -> None:
        name = raw["name"]
        access = [raw["access_group"], "DMS-Administration"]
        permissions = self._object_permissions(access, access)
        tag_name = raw["tag"]
        tag_id = self._upsert(
            "tags",
            tag_name,
            {
                "name": tag_name,
                "color": raw.get("tag_color", "#8a3b12"),
                "match": "",
                "matching_algorithm": 0,
                "is_insensitive": True,
                "is_inbox_tag": False,
                "owner": owner_id,
                "set_permissions": permissions,
            },
        )
        storage_name = f"Geschützt/{name}"
        storage_id = self._upsert(
            "storage_paths",
            storage_name,
            {
                "name": storage_name,
                "path": raw["storage_path"],
                "match": "",
                "matching_algorithm": 0,
                "is_insensitive": True,
                "owner": owner_id,
                "set_permissions": permissions,
            },
        )
        area = {**raw, "tag_id": tag_id, "storage_id": storage_id}
        self.protected_areas[name] = area
        confidential_id = self.ids["tags"]["Vertraulich/Personal"]
        payload = {
            "name": f"DMS | Geschützt | {name}",
            "order": int(raw.get("order", 50)),
            "enabled": True,
            "triggers": [
                {"type": 2, "sources": [1, 2, 3, 4], "filter_filename": pattern}
                for pattern in raw["filename_patterns"]
            ],
            "actions": [
                {
                    "type": 1,
                    "assign_tags": [tag_id, confidential_id],
                    "assign_storage_path": storage_id,
                    "assign_view_groups": self._group_ids(access),
                    "assign_change_groups": self._group_ids(access),
                },
                {
                    "type": 2,
                    "remove_view_groups": self._group_ids(["DMS-Eingang"]),
                    "remove_change_groups": self._group_ids(["DMS-Eingang"]),
                },
            ],
        }
        self._upsert("workflows", payload["name"], payload)

    def _seed_project_intake_workflow(self, project: dict[str, Any]) -> None:
        patterns = project.get("filename_patterns") or [f"*{project['code']}*"]
        triggers = [
            {"type": 2, "sources": [1, 2, 3, 4], "filter_filename": pattern}
            for pattern in patterns
        ]
        view_names = self._project_view_groups(project)
        change_names = self._project_change_groups(project, "Entwurf")
        project_field_id = self.ids["custom_fields"]["Projekt / Kommission"]
        payload = {
            "name": f"DMS | {project['code']} | Projekteingang",
            "order": 100,
            "enabled": True,
            "triggers": triggers,
            "actions": [
                {
                    "type": 1,
                    "assign_tags": [
                        self.ids["tags"]["Status/Entwurf"],
                        project["tag_id"],
                    ],
                    "assign_storage_path": project["storage_id"],
                    "assign_view_groups": self._group_ids(view_names),
                    "assign_change_groups": self._group_ids(change_names),
                    "assign_custom_fields": [project_field_id],
                    "assign_custom_fields_values": {
                        str(project_field_id): project["code"]
                    },
                },
                {
                    "type": 2,
                    "remove_view_groups": self._group_ids(["DMS-Eingang"]),
                    "remove_change_groups": self._group_ids(["DMS-Eingang"]),
                },
            ],
        }
        self._upsert("workflows", payload["name"], payload)

    def _seed_project_approval_workflows(self, project: dict[str, Any]) -> None:
        legacy_name = f"DMS | {project['code']} | In Prüfung -> Freigegeben"
        legacy = self.api.find("workflows", "name", legacy_name)
        if legacy and isinstance(legacy.get("id"), int):
            self.api.patch("workflows", legacy["id"], {"enabled": False})
            self.actions.append(f"disabled: workflows/{legacy_name}")

        transitions = (
            ("Entwurf", "In Prüfung"),
            ("In Prüfung", "Zur Freigabe"),
            ("In Prüfung", "Abgelehnt"),
            ("Zur Freigabe", "Freigegeben"),
            ("Zur Freigabe", "Abgelehnt"),
            ("Abgelehnt", "Entwurf"),
            ("Freigegeben", "Obsolet"),
        )
        for order, (source, target) in enumerate(transitions, start=200):
            source_id = self.ids["tags"][f"Status/{source}"]
            target_id = self.ids["tags"][f"Status/{target}"]
            view_names = self._project_view_groups(project)
            change_names = self._project_change_groups(project, target)
            all_change_names = [
                project["groups"][lane]
                for lane in ("Bearbeiten", "Pruefen", "Freigeben")
            ]
            name = f"DMS | {project['code']} | {source} -> {target}"
            payload = {
                "name": name,
                "order": order,
                "enabled": True,
                "triggers": [
                    {
                        "type": 3,
                        "filter_has_all_tags": [project["tag_id"], source_id, target_id],
                    }
                ],
                "actions": [
                    {
                        "type": 2,
                        "remove_tags": [source_id],
                        "remove_change_groups": self._group_ids(all_change_names),
                    },
                    {
                        "type": 1,
                        "assign_view_groups": self._group_ids(view_names),
                        "assign_change_groups": self._group_ids(change_names),
                    },
                ],
            }
            self._upsert("workflows", name, payload)

        self._seed_direct_approval_guard(project)

    def _seed_direct_approval_guard(self, project: dict[str, Any]) -> None:
        approved_id = self.ids["tags"]["Status/Freigegeben"]
        invalid_source_ids = [
            self.ids["tags"][f"Status/{state}"]
            for state in ("Entwurf", "In Prüfung", "Abgelehnt")
        ]
        name = f"DMS | {project['code']} | Direkte Freigabe verhindern"
        payload = {
            "name": name,
            "order": 299,
            "enabled": True,
            "triggers": [
                {
                    "type": 3,
                    "filter_has_all_tags": [project["tag_id"], source_id, approved_id],
                }
                for source_id in invalid_source_ids
            ],
            "actions": [{"type": 2, "remove_tags": [approved_id]}],
        }
        self._upsert("workflows", name, payload)

    def _document_match(self, document: dict[str, Any], filename: str) -> bool:
        original = document.get("original_file_name") or document.get("filename")
        return original == filename or document.get("title") == Path(filename).stem

    def _merge_custom_fields(
        self,
        existing: Any,
        desired: dict[str, Any],
    ) -> list[dict[str, Any]]:
        by_id: dict[int, Any] = {}
        if isinstance(existing, list):
            for item in existing:
                if isinstance(item, dict) and isinstance(item.get("field"), int):
                    by_id[item["field"]] = item.get("value")
        for name, value in desired.items():
            if name not in self.ids["custom_fields"]:
                raise GovernanceError(f"unknown custom field in demo document: {name}")
            by_id[self.ids["custom_fields"][name]] = value
        return [{"field": field, "value": value} for field, value in sorted(by_id.items())]

    def _migrate_demo_documents(self) -> None:
        migrations = self.config.get("demo_documents", [])
        if not migrations:
            return
        documents = self.api.list_resource("documents", refresh=True)
        managed_status_ids = {
            object_id
            for name, object_id in self.ids["tags"].items()
            if name.startswith("Status/")
        }
        for migration in migrations:
            matches = [
                doc
                for doc in documents
                if self._document_match(doc, migration["filename"])
            ]
            if not matches:
                self.actions.append(f"skipped: documents/{migration['filename']} (not imported)")
                continue
            project = self.projects[migration["project"]]
            status = migration.get("status", "Freigegeben")
            status_id = self.ids["tags"][f"Status/{status}"]
            document_type = migration.get("document_type")
            desired_fields = {
                "Projekt / Kommission": project["code"],
                **migration.get("custom_fields", {}),
            }
            for document in matches:
                tags = {
                    tag_id
                    for tag_id in document.get("tags", [])
                    if isinstance(tag_id, int) and tag_id not in managed_status_ids
                }
                tags.update((project["tag_id"], status_id))
                payload: dict[str, Any] = {
                    "tags": sorted(tags),
                    "storage_path": project["storage_id"],
                    "owner": self._admin_id(),
                    "custom_fields": self._merge_custom_fields(
                        document.get("custom_fields"), desired_fields
                    ),
                    "set_permissions": self._object_permissions(
                        self._project_view_groups(project),
                        self._project_change_groups(project, status),
                    ),
                }
                if document_type:
                    payload["document_type"] = self.ids["document_types"][document_type]
                self.api.patch("documents", document["id"], payload)
                self.actions.append(f"updated: documents/{migration['filename']}")

    def _migrate_protected_documents(self) -> None:
        migrations = self.config.get("protected_documents", [])
        if not migrations:
            return
        documents = self.api.list_resource("documents", refresh=True)
        project_tag_ids = {
            project["tag_id"] for project in self.projects.values()
        }
        project_field_id = self.ids["custom_fields"].get("Projekt / Kommission")
        for migration in migrations:
            area = self.protected_areas[migration["area"]]
            access = [area["access_group"], "DMS-Administration"]
            matches = [
                document
                for document in documents
                if self._document_match(document, migration["filename"])
            ]
            if not matches:
                self.actions.append(
                    f"skipped: documents/{migration['filename']} (not imported)"
                )
                continue
            desired_fields = migration.get("custom_fields", {})
            for document in matches:
                tags = {
                    tag_id
                    for tag_id in document.get("tags", [])
                    if isinstance(tag_id, int) and tag_id not in project_tag_ids
                }
                tags.add(area["tag_id"])
                tags.add(self.ids["tags"]["Vertraulich/Personal"])
                existing_fields = document.get("custom_fields")
                if project_field_id is not None and isinstance(existing_fields, list):
                    existing_fields = [
                        item
                        for item in existing_fields
                        if not (
                            isinstance(item, dict)
                            and item.get("field") == project_field_id
                        )
                    ]
                payload: dict[str, Any] = {
                    "tags": sorted(tags),
                    "storage_path": area["storage_id"],
                    "owner": self._admin_id(),
                    "custom_fields": self._merge_custom_fields(
                        existing_fields, desired_fields
                    ),
                    "set_permissions": self._object_permissions(access, access),
                }
                document_type = migration.get("document_type")
                if document_type:
                    payload["document_type"] = self.ids["document_types"][document_type]
                self.api.patch("documents", document["id"], payload)
                self.actions.append(f"updated: documents/{migration['filename']}")

    def seed(self) -> list[str]:
        self.validate()
        self.api.authenticate()
        self._seed_groups()
        owner_id = self._admin_id()
        self._seed_metadata(owner_id)
        self._seed_base_intake_workflow()
        for area in self.config.get("protected_areas", []):
            self._seed_protected_area(area, owner_id)
        for project in self.config["projects"]:
            self._seed_project(project, owner_id)
        self._migrate_demo_documents()
        self._migrate_protected_documents()
        return self.actions


def load_config(path: str) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GovernanceError(f"cannot read governance config {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise GovernanceError("governance config root must be an object")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to governance JSON")
    parser.add_argument("--project-template", help="Instantiate one additional project template")
    parser.add_argument("--project-code", help="Code for the additional project")
    parser.add_argument("--project-name", help="Display name for the additional project")
    parser.add_argument(
        "--filename-pattern",
        action="append",
        default=[],
        help="Paperless filename pattern for the additional project; repeatable",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the governance JSON without contacting Paperless",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        api = PaperlessAdminApi(
            os.getenv("PAPERLESS_BASE_URL", "http://paperless-webserver:8000"),
            username=os.getenv("PAPERLESS_ADMIN_USER", "admin"),
            password=os.getenv("PAPERLESS_ADMIN_PASSWORD", ""),
            token=os.getenv("PAPERLESS_API_TOKEN", ""),
        )
        seeder = GovernanceSeeder(api, config)
        project_args = (args.project_template, args.project_code, args.project_name)
        if any(project_args):
            if not all(project_args):
                raise GovernanceError(
                    "--project-template, --project-code and --project-name must be used together"
                )
            seeder.add_project(
                args.project_template,
                args.project_code,
                args.project_name,
                args.filename_pattern,
            )
        if args.validate_only:
            seeder.validate()
            print("DMS governance configuration is valid")
            return 0
        actions = seeder.seed()
    except GovernanceError as exc:
        print(f"DMS governance seed failed: {exc}", file=sys.stderr)
        return 1
    print(f"DMS governance seed completed with {len(actions)} actions")
    for action in actions:
        print(f"- {action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
