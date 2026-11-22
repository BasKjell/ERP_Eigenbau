from __future__ import annotations

import json
import urllib.error
import urllib.request
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from app.paperless_governance import (
    GovernanceError,
    GovernanceSeeder,
    PaperlessAdminApi,
    load_config,
    main,
)


def governance_config() -> dict[str, Any]:
    view_permissions = ["documents.view_document", "documents.view_tag"]
    return {
        "schema_version": 1,
        "owner_username": "admin",
        "roles": [
            {"name": "DMS-Leser", "permissions": view_permissions},
            {
                "name": "DMS-Bearbeiter",
                "permissions": [*view_permissions, "documents.change_document"],
            },
            {
                "name": "DMS-Pruefer",
                "permissions": [*view_permissions, "documents.change_document"],
            },
            {
                "name": "DMS-Freigeber",
                "permissions": [*view_permissions, "documents.change_document"],
            },
            {
                "name": "DMS-Administration",
                "permissions": [*view_permissions, "documents.change_document"],
            },
        ],
        "access_groups": ["DMS-Eingang"],
        "metadata": {
            "custom_fields": [
                {"name": "Projekt / Kommission", "data_type": "string"},
                {"name": "Revision", "data_type": "string"},
            ],
            "tags": [
                {
                    "name": f"Status/{state}",
                    "color": "#000000",
                    "match": "",
                    "matching_algorithm": 0,
                    "is_insensitive": True,
                    "is_inbox_tag": False,
                }
                for state in (
                    "Entwurf",
                    "In Prüfung",
                    "Zur Freigabe",
                    "Freigegeben",
                    "Abgelehnt",
                    "Obsolet",
                )
            ],
            "document_types": [
                {
                    "name": "Zeichnung",
                    "match": "Zeichnung",
                    "matching_algorithm": 3,
                    "is_insensitive": True,
                }
            ],
            "storage_paths": [],
        },
        "project_templates": {
            "Kundenkommission": {
                "tag_color": "#123456",
                "storage_path": "Projekte/{code}/{{ document_type }}",
            }
        },
        "projects": [
            {
                "template": "Kundenkommission",
                "code": "KOM-1",
                "name": "Testprojekt",
                "filename_patterns": ["*KOM-1*"],
            }
        ],
        "demo_documents": [
            {
                "filename": "KOM-1_Zeichnung.pdf",
                "project": "KOM-1",
                "document_type": "Zeichnung",
                "status": "Freigegeben",
                "custom_fields": {"Revision": "C"},
            }
        ],
    }


class FakePaperlessApi:
    def __init__(self) -> None:
        self.username = "admin"
        self.authenticated = False
        self.next_id = 10
        self.resources: dict[str, list[dict[str, Any]]] = {
            "users": [{"id": 1, "username": "admin"}],
            "documents": [
                {
                    "id": 2,
                    "title": "KOM-1_Zeichnung",
                    "original_file_name": "KOM-1_Zeichnung.pdf",
                    "tags": [999],
                    "custom_fields": [],
                }
            ],
        }
        self.patches: list[tuple[str, int, dict[str, Any]]] = []

    def authenticate(self) -> None:
        self.authenticated = True

    def list_resource(self, resource: str, *, refresh: bool = False) -> list[dict[str, Any]]:
        return self.resources.setdefault(resource, [])

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
        if existing:
            existing.update(deepcopy(payload))
            return existing, "updated"
        self.next_id += 1
        created = {"id": self.next_id, **deepcopy(payload)}
        self.list_resource(resource).append(created)
        return created, "created"

    def patch(self, resource: str, object_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self.patches.append((resource, object_id, deepcopy(payload)))
        existing = next(item for item in self.list_resource(resource) if item["id"] == object_id)
        existing.update(deepcopy(payload))
        return existing


class JsonResponse:
    def __init__(self, payload: Any) -> None:
        self.payload = json.dumps(payload).encode()

    def __enter__(self) -> JsonResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def workflow(api: FakePaperlessApi, name: str) -> dict[str, Any]:
    item = api.find("workflows", "name", name)
    assert item is not None
    return item


def group_id(api: FakePaperlessApi, name: str) -> int:
    group = api.find("groups", "name", name)
    assert group is not None
    return group["id"]


def test_seed_builds_roles_project_workflows_and_document_acl() -> None:
    api = FakePaperlessApi()
    actions = GovernanceSeeder(api, governance_config()).seed()

    assert api.authenticated
    assert len(api.resources["groups"]) == 10
    assert len(api.resources["workflows"]) == 10
    assert any(action.startswith("created: workflows/") for action in actions)
    reader = api.find("groups", "name", "DMS-Leser")
    assert reader is not None
    assert reader["permissions"] == ["view_document", "view_tag"]

    intake = workflow(api, "DMS | KOM-1 | Projekteingang")
    assignment, removal = intake["actions"]
    assert all("filter_path" not in trigger for trigger in intake["triggers"])
    project_group_ids = {
        group_id(api, f"DMS-Projekt-KOM-1-{lane}")
        for lane in GovernanceSeeder.PROJECT_LANES
    }
    assert project_group_ids <= set(assignment["assign_view_groups"])
    assert group_id(api, "DMS-Eingang") in removal["remove_view_groups"]

    review = workflow(api, "DMS | KOM-1 | Entwurf -> In Prüfung")
    assert group_id(api, "DMS-Projekt-KOM-1-Bearbeiten") in review["actions"][0][
        "remove_change_groups"
    ]
    assert group_id(api, "DMS-Projekt-KOM-1-Pruefen") in review["actions"][1][
        "assign_change_groups"
    ]

    ready = workflow(api, "DMS | KOM-1 | In Prüfung -> Zur Freigabe")
    ready_changes = set(ready["actions"][1]["assign_change_groups"])
    assert group_id(api, "DMS-Projekt-KOM-1-Freigeben") in ready_changes
    assert group_id(api, "DMS-Projekt-KOM-1-Pruefen") not in ready_changes

    approved = workflow(api, "DMS | KOM-1 | Zur Freigabe -> Freigegeben")
    approval_changes = set(approved["actions"][1]["assign_change_groups"])
    assert group_id(api, "DMS-Projekt-KOM-1-Freigeben") in approval_changes
    assert group_id(api, "DMS-Projekt-KOM-1-Bearbeiten") not in approval_changes

    guard = workflow(api, "DMS | KOM-1 | Direkte Freigabe verhindern")
    assert len(guard["triggers"]) == 3
    assert guard["actions"][0]["remove_tags"]

    _, document_id, document_patch = api.patches[-1]
    assert document_id == 2
    assert 999 in document_patch["tags"]
    assert document_patch["set_permissions"]["view"]["groups"]
    assert set(document_patch["set_permissions"]["change"]["groups"]) == approval_changes
    field_values = {item["field"]: item["value"] for item in document_patch["custom_fields"]}
    revision = api.find("custom_fields", "name", "Revision")
    assert revision is not None
    assert field_values[revision["id"]] == "C"


def test_seed_is_repeatable_without_duplicate_objects() -> None:
    api = FakePaperlessApi()
    config = governance_config()
    GovernanceSeeder(api, config).seed()
    counts = {resource: len(items) for resource, items in api.resources.items()}

    second_actions = GovernanceSeeder(api, config).seed()

    assert {resource: len(items) for resource, items in api.resources.items()} == counts
    assert any(action.startswith("updated: groups/") for action in second_actions)
    assert any(action.startswith("updated: workflows/") for action in second_actions)


def test_protected_hr_areas_assign_exclusive_acl_and_migrate_documents() -> None:
    config = governance_config()
    config["access_groups"].extend(
        ["DMS-Bereich-HR-Recruiting", "DMS-Bereich-HR-Payroll"]
    )
    config["metadata"]["tags"].append(
        {
            "name": "Vertraulich/Personal",
            "color": "#8a3b12",
            "match": "",
            "matching_algorithm": 0,
            "is_insensitive": True,
            "is_inbox_tag": False,
        }
    )
    config["metadata"]["document_types"].append(
        {
            "name": "Bewerbungsunterlage",
            "match": "Bewerbung",
            "matching_algorithm": 1,
            "is_insensitive": True,
        }
    )
    config["metadata"]["custom_fields"].append(
        {"name": "Bewerbungsnummer", "data_type": "string"}
    )
    config["protected_areas"] = [
        {
            "name": "HR-Recruiting",
            "access_group": "DMS-Bereich-HR-Recruiting",
            "tag": "Bereich/HR-Recruiting",
            "storage_path": "Personal/Bewerbungen/{{ created_year }}",
            "filename_patterns": ["Bewerbung_*"],
        }
    ]
    config["protected_documents"] = [
        {
            "filename": "Bewerbung_APP-0001.pdf",
            "area": "HR-Recruiting",
            "document_type": "Bewerbungsunterlage",
            "custom_fields": {"Bewerbungsnummer": "APP-0001"},
        }
    ]
    api = FakePaperlessApi()
    api.resources["documents"].append(
        {
            "id": 3,
            "title": "Bewerbung_APP-0001",
            "original_file_name": "Bewerbung_APP-0001.pdf",
            "tags": [],
            "custom_fields": [],
        }
    )

    GovernanceSeeder(api, config).seed()

    protected = workflow(api, "DMS | Geschützt | HR-Recruiting")
    assignment, removal = protected["actions"]
    recruiting_group = group_id(api, "DMS-Bereich-HR-Recruiting")
    admin_group = group_id(api, "DMS-Administration")
    assert set(assignment["assign_view_groups"]) == {recruiting_group, admin_group}
    assert group_id(api, "DMS-Eingang") in removal["remove_view_groups"]
    assert group_id(api, "DMS-Leser") not in assignment["assign_view_groups"]
    _, _, document_patch = next(
        item for item in reversed(api.patches) if item[0] == "documents" and item[1] == 3
    )
    assert set(document_patch["set_permissions"]["view"]["groups"]) == {
        recruiting_group,
        admin_group,
    }
    assert len(document_patch["tags"]) == 2


def test_unknown_project_template_is_rejected_before_api_changes() -> None:
    config = governance_config()
    config["projects"][0]["template"] = "Unbekannt"
    api = FakePaperlessApi()

    with pytest.raises(GovernanceError, match="unknown template"):
        GovernanceSeeder(api, config).seed()

    assert not api.authenticated


def test_add_project_uses_template_and_default_filename_pattern() -> None:
    api = FakePaperlessApi()
    seeder = GovernanceSeeder(api, governance_config())
    seeder.add_project("Kundenkommission", "KOM-2", "Zweites Projekt")

    seeder.seed()

    intake = workflow(api, "DMS | KOM-2 | Projekteingang")
    assert intake["triggers"][0]["filter_filename"] == "*KOM-2*"


def test_add_project_rejects_unknown_template() -> None:
    seeder = GovernanceSeeder(FakePaperlessApi(), governance_config())

    with pytest.raises(GovernanceError, match="unknown project template"):
        seeder.add_project("Nicht vorhanden", "KOM-2", "Projekt")


def test_validate_only_checks_file_without_contacting_api(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = tmp_path / "governance.json"
    config_path.write_text(json.dumps(governance_config()), encoding="utf-8")

    result = main(["--config", str(config_path), "--validate-only"])

    assert result == 0
    assert "configuration is valid" in capsys.readouterr().out


def test_admin_api_authenticates_lists_and_creates(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[urllib.request.Request] = []

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> JsonResponse:
        assert timeout == 5
        requests.append(request)
        if request.full_url.endswith("/api/token/"):
            return JsonResponse({"token": "admin-token"})
        if "/api/groups/?" in request.full_url:
            return JsonResponse({"results": [], "next": None})
        assert request.get_header("Authorization") == "Token admin-token"
        return JsonResponse({"id": 42, "name": "DMS-Test", "permissions": []})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    api = PaperlessAdminApi(
        "http://paperless.test", username="admin", password="secret", timeout=5
    )

    result, action = api.upsert(
        "groups", "name", "DMS-Test", {"name": "DMS-Test", "permissions": []}
    )

    assert action == "created"
    assert result["id"] == 42
    assert [request.method for request in requests] == ["POST", "GET", "POST"]


def test_admin_api_follows_pagination_and_updates(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: float) -> JsonResponse:
        assert timeout == 30
        if "page=2" in request.full_url:
            return JsonResponse(
                {"results": [{"id": 8, "name": "DMS-Test"}], "next": None}
            )
        if request.method == "PATCH":
            return JsonResponse({"id": 8, "name": "DMS-Test", "permissions": ["view_document"]})
        return JsonResponse(
            {
                "results": [{"id": 7, "name": "Andere Gruppe"}],
                "next": "http://paperless.test/api/groups/?page=2",
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    api = PaperlessAdminApi("http://paperless.test", token="token")

    result, action = api.upsert(
        "groups",
        "name",
        "DMS-Test",
        {"name": "DMS-Test", "permissions": ["view_document"]},
    )

    assert action == "updated"
    assert result["permissions"] == ["view_document"]
    assert len(api.list_resource("groups")) == 2


def test_admin_api_reports_http_error_body(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_urlopen(request: urllib.request.Request, timeout: float) -> JsonResponse:
        raise urllib.error.HTTPError(
            request.full_url,
            403,
            "Forbidden",
            hdrs=None,
            fp=BytesIO(b'{"detail":"denied"}'),
        )

    monkeypatch.setattr(urllib.request, "urlopen", fail_urlopen)
    api = PaperlessAdminApi("http://paperless.test", token="token")

    with pytest.raises(GovernanceError, match='HTTP 403.*denied'):
        api.list_resource("groups")


def test_load_config_rejects_non_object(tmp_path: Path) -> None:
    config_path = tmp_path / "governance.json"
    config_path.write_text("[]", encoding="utf-8")

    with pytest.raises(GovernanceError, match="root must be an object"):
        load_config(str(config_path))
