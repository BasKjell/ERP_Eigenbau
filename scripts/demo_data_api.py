#!/usr/bin/env python3
"""API-only demo data orchestration for the local manufacturing platform.

The module deliberately does not access application databases or Docker
volumes.  Setup is idempotent.  Cleanup only addresses identifiers declared in
the repository manifests and therefore never performs an unbounded delete.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SYSTEMS = ("keycloak", "platform", "erpnext", "redmine", "paperless")
DELETE_CONFIRMATION = "DELETE-DEMO-DATA"


class DemoApiError(RuntimeError):
    """Sanitized error raised for one failed API operation."""


def load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE entries without overriding the process environment."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0:1] == value[-1:] and value.startswith(("'", '"')):
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


class HttpClient:
    """Small JSON/form/multipart client with cookie support."""

    def __init__(self, base_url: str, headers: dict[str, str] | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {"Accept": "application/json", **(headers or {})}
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def request(
        self,
        method: str,
        path: str,
        payload: Any | None = None,
        *,
        headers: dict[str, str] | None = None,
        allow_missing: bool = False,
    ) -> Any:
        url = path if path.startswith(("http://", "https://")) else f"{self.base_url}{path}"
        body = None
        request_headers = {**self.headers, **(headers or {})}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode()
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
        try:
            with self.opener.open(request, timeout=45) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            if allow_missing and exc.code == 404:
                return None
            detail = exc.read().decode("utf-8", errors="replace")[:1200]
            raise DemoApiError(
                f"{method} {urllib.parse.urlsplit(url).path} -> HTTP {exc.code}: {detail}"
            ) from exc
        except (OSError, urllib.error.URLError) as exc:
            raise DemoApiError(f"{method} {url} nicht erreichbar: {exc}") from exc
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DemoApiError(f"{method} {url} lieferte kein JSON") from exc

    def form(self, method: str, path: str, values: dict[str, str]) -> Any:
        url = path if path.startswith(("http://", "https://")) else f"{self.base_url}{path}"
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(values).encode(),
            headers={
                **self.headers,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method=method,
        )
        try:
            with self.opener.open(request, timeout=45) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1200]
            raise DemoApiError(
                f"{method} {urllib.parse.urlsplit(url).path} -> HTTP {exc.code}: {detail}"
            ) from exc
        except (OSError, urllib.error.URLError) as exc:
            raise DemoApiError(f"{method} {url} nicht erreichbar: {exc}") from exc
        return json.loads(raw) if raw else {}

    def multipart(
        self,
        path: str,
        *,
        file_field: str,
        file_path: Path,
        fields: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        boundary = f"----open-manufacturing-{uuid.uuid4().hex}"
        chunks: list[bytes] = []
        for name, value in (fields or {}).items():
            chunks.extend(
                (
                    f"--{boundary}\r\n".encode(),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                    value.encode(),
                    b"\r\n",
                )
            )
        chunks.extend(
            (
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="{file_field}"; '
                    f'filename="{file_path.name}"\r\n'
                ).encode(),
                b"Content-Type: application/pdf\r\n\r\n",
                file_path.read_bytes(),
                b"\r\n",
                f"--{boundary}--\r\n".encode(),
            )
        )
        url = f"{self.base_url}{path}"
        request = urllib.request.Request(
            url,
            data=b"".join(chunks),
            headers={
                **self.headers,
                **(headers or {}),
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with self.opener.open(request, timeout=90) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1200]
            raise DemoApiError(f"Paperless-Upload -> HTTP {exc.code}: {detail}") from exc
        except (OSError, urllib.error.URLError) as exc:
            raise DemoApiError(f"Paperless-Upload nicht erreichbar: {exc}") from exc
        return json.loads(raw) if raw else {}


@dataclass
class RunReport:
    mode: str
    dry_run: bool
    actions: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def action(self, system: str, message: str) -> None:
        self.actions.append(f"[{system}] {message}")

    def error(self, system: str, message: str) -> None:
        self.errors.append(f"[{system}] {message}")


class PlatformDemo:
    def __init__(self) -> None:
        token = os.getenv(
            "PLATFORM_DEMO_ADMIN_TOKEN",
            "local-demo-admin-token-change-before-network-use",
        )
        self.client = HttpClient(
            os.getenv(
                "PLATFORM_API_URL",
                f"http://localhost:{os.getenv('DEMO_API_PORT', '8088')}",
            ),
            {"X-Demo-Admin-Token": token},
        )

    def setup(self, report: RunReport) -> None:
        if not report.dry_run:
            self.client.request("POST", "/api/demo/reset")
        report.action(
            "platform",
            "Portal, FLOWQ, MES, HR, Desksharing, FLOWWORK und FLOWFIN zurückgesetzt",
        )

    def delete(self, report: RunReport) -> None:
        if not report.dry_run:
            self.client.request("POST", "/api/demo/purge")
        report.action("platform", "persistenter Plattform-Demozustand geleert")


class KeycloakDemo:
    def __init__(self) -> None:
        self.client = HttpClient(
            os.getenv(
                "KEYCLOAK_API_URL",
                f"http://localhost:{os.getenv('KEYCLOAK_PORT', '8082')}",
            )
        )
        self.admin_user = os.getenv("KEYCLOAK_ADMIN", "admin")
        self.admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin-demo-change-me")
        self.realm_file = ROOT / "deployment/keycloak/realm.json"
        self.realm = json.loads(self.realm_file.read_text(encoding="utf-8"))
        self.realm_name = str(self.realm["realm"])

    def _authenticate(self) -> None:
        token = self.client.form(
            "POST",
            "/realms/master/protocol/openid-connect/token",
            {
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": self.admin_user,
                "password": self.admin_password,
            },
        ).get("access_token")
        if not token:
            raise DemoApiError("Keycloak lieferte kein Admin-Token")
        self.client.headers["Authorization"] = f"Bearer {token}"

    def setup(self, report: RunReport) -> None:
        user_count = len(self.realm.get("users", []))
        if report.dry_run:
            report.action(
                "keycloak", f"{user_count} deklarierte Demo-Identitäten würden importiert"
            )
            return
        self._authenticate()
        existing = self.client.request(
            "GET", f"/admin/realms/{urllib.parse.quote(self.realm_name)}", allow_missing=True
        )
        if existing is None:
            self.client.request("POST", "/admin/realms", self.realm)
        else:
            payload = {
                key: self.realm[key]
                for key in ("roles", "clients", "clientScopes", "users", "groups")
                if key in self.realm
            }
            payload["ifResourceExists"] = "OVERWRITE"
            self.client.request(
                "POST",
                f"/admin/realms/{urllib.parse.quote(self.realm_name)}/partialImport",
                payload,
            )
        report.action("keycloak", f"{user_count} Demo-Identitäten per Admin-API importiert")

    def delete(self, report: RunReport) -> None:
        usernames = {str(user["username"]) for user in self.realm.get("users", [])}
        if report.dry_run:
            report.action(
                "keycloak", f"{len(usernames)} exakt deklarierte Benutzer würden gelöscht"
            )
            return
        self._authenticate()
        deleted = 0
        for username in sorted(usernames):
            query = urllib.parse.urlencode({"username": username, "exact": "true"})
            users = self.client.request(
                "GET",
                f"/admin/realms/{urllib.parse.quote(self.realm_name)}/users?{query}",
            )
            for user in users if isinstance(users, list) else []:
                if user.get("username") != username:
                    continue
                self.client.request(
                    "DELETE",
                    f"/admin/realms/{urllib.parse.quote(self.realm_name)}/users/{user['id']}",
                )
                deleted += 1
        report.action("keycloak", f"{deleted} exakt deklarierte Demo-Benutzer gelöscht")


class RedmineDemo:
    def __init__(self) -> None:
        self.config = json.loads(
            (ROOT / "deployment/redmine/demo_api.json").read_text(encoding="utf-8")
        )
        self.client = HttpClient(
            os.getenv(
                "REDMINE_API_URL",
                f"http://localhost:{os.getenv('REDMINE_PORT', '8011')}",
            ),
            {
                "X-Redmine-API-Key": os.getenv(
                    "REDMINE_API_KEY", "f6ab4d1c02fe9a7b3e5d8c4f1a6b9e2c7d0f3a5b"
                )
            },
        )

    def setup(self, report: RunReport) -> None:
        if report.dry_run:
            report.action(
                "redmine",
                f"{len(self.config['projects'])} Projekte würden idempotent angelegt",
            )
            return
        trackers = self.client.request("GET", "/trackers.json").get("trackers", [])
        tracker_id = trackers[0]["id"] if trackers else None
        issue_count = 0
        for project in self.config["projects"]:
            identifier = project["identifier"]
            encoded = urllib.parse.quote(identifier, safe="")
            existing = self.client.request("GET", f"/projects/{encoded}.json", allow_missing=True)
            values = {
                "name": project["name"],
                "identifier": identifier,
                "description": project["description"],
                "is_public": True,
                "enabled_module_names": [
                    "issue_tracking",
                    "time_tracking",
                    "wiki",
                    "calendar",
                    "gantt",
                ],
            }
            if existing is None:
                self.client.request("POST", "/projects.json", {"project": values})
            else:
                self.client.request("PUT", f"/projects/{encoded}.json", {"project": values})
            for page in project.get("wiki", []):
                title = urllib.parse.quote(page["title"], safe="")
                self.client.request(
                    "PUT",
                    f"/projects/{encoded}/wiki/{title}.json",
                    {"wiki_page": {"text": page["text"], "comments": "API Demo-Setup"}},
                )
            current = self.client.request(
                "GET", f"/issues.json?project_id={encoded}&status_id=*&limit=100"
            ).get("issues", [])
            by_subject = {item.get("subject"): item for item in current}
            for issue in project.get("issues", []):
                values = {
                    "project_id": identifier,
                    "subject": issue["subject"],
                    "description": issue["description"],
                    "due_date": issue["due_date"],
                    "done_ratio": issue.get("done_ratio", 0),
                }
                if tracker_id:
                    values["tracker_id"] = tracker_id
                found = by_subject.get(issue["subject"])
                if found:
                    self.client.request("PUT", f"/issues/{found['id']}.json", {"issue": values})
                else:
                    self.client.request("POST", "/issues.json", {"issue": values})
                issue_count += 1
        report.action(
            "redmine",
            f"{len(self.config['projects'])} Projekte, {issue_count} Tickets und Wiki-Seiten synchronisiert",
        )

    def delete(self, report: RunReport) -> None:
        identifiers = [item["identifier"] for item in self.config["projects"]]
        if report.dry_run:
            report.action("redmine", f"Projekte {', '.join(identifiers)} würden gelöscht")
            return
        deleted = 0
        for identifier in identifiers:
            encoded = urllib.parse.quote(identifier, safe="")
            existing = self.client.request("GET", f"/projects/{encoded}.json", allow_missing=True)
            if existing is None:
                continue
            self.client.request("DELETE", f"/projects/{encoded}.json")
            deleted += 1
        report.action("redmine", f"{deleted} deklarierte Projekte samt Tickets und Wiki gelöscht")


class PaperlessDemo:
    def __init__(self) -> None:
        sys.path.insert(0, str(ROOT / "services/platform_api"))
        from app.paperless_governance import PaperlessAdminApi, load_config

        self.api_type = PaperlessAdminApi
        self.config = load_config(str(ROOT / "deployment/paperless/governance.json"))
        self.base_url = os.getenv(
            "PAPERLESS_API_URL",
            f"http://localhost:{os.getenv('PAPERLESS_PORT', '8010')}",
        )
        self.username = os.getenv("PAPERLESS_ADMIN_USER", "admin")
        self.password = os.getenv("PAPERLESS_ADMIN_PASSWORD", "admin-demo-change-me")
        self.token = os.getenv("PAPERLESS_API_TOKEN", "")

    def _api(self) -> Any:
        return self.api_type(
            self.base_url,
            username=self.username,
            password=self.password,
            token=self.token,
        )

    def _document_specs(self) -> list[dict[str, Any]]:
        return [
            *self.config.get("demo_documents", []),
            *self.config.get("protected_documents", []),
        ]

    def setup(self, report: RunReport) -> None:
        specs = self._document_specs()
        if report.dry_run:
            report.action("paperless", f"Governance und {len(specs)} Dokumente würden angelegt")
            return
        from app.paperless_governance import GovernanceSeeder

        api = self._api()
        GovernanceSeeder(api, self.config).seed()
        documents = api.list_resource("documents", refresh=True)
        existing = {item.get("original_file_name") or item.get("filename") for item in documents}
        uploaded = 0
        upload_client = HttpClient(self.base_url)
        api.authenticate()
        upload_client.headers["Authorization"] = f"Token {api.token}"
        for spec in specs:
            filename = spec["filename"]
            if filename in existing:
                continue
            path = ROOT / "output/pdf" / filename
            if not path.exists():
                raise DemoApiError(f"DMS-Demodokument fehlt lokal: {path}")
            upload_client.multipart(
                "/api/documents/post_document/",
                file_field="document",
                file_path=path,
                fields={"title": path.stem},
            )
            uploaded += 1
        if uploaded:
            deadline = time.monotonic() + 45
            wanted = {item["filename"] for item in specs}
            while time.monotonic() < deadline:
                fresh_api = self._api()
                names = {
                    item.get("original_file_name") or item.get("filename")
                    for item in fresh_api.list_resource("documents", refresh=True)
                }
                if wanted.issubset(names):
                    break
                time.sleep(2)
        GovernanceSeeder(self._api(), self.config).seed()
        report.action("paperless", f"Governance synchronisiert, {uploaded} Dokumente hochgeladen")

    def _managed_names(self) -> dict[str, set[str]]:
        metadata = self.config["metadata"]
        projects = self.config["projects"]
        areas = self.config.get("protected_areas", [])
        role_names = {item["name"] for item in self.config["roles"]}
        groups = role_names | set(self.config["access_groups"])
        for project in projects:
            groups.update(
                f"DMS-Projekt-{project['code']}-{lane}"
                for lane in ("Lesen", "Bearbeiten", "Pruefen", "Freigeben")
            )
        return {
            "groups": groups,
            "custom_fields": {item["name"] for item in metadata["custom_fields"]},
            "document_types": {item["name"] for item in metadata["document_types"]},
            "tags": (
                {item["name"] for item in metadata["tags"]}
                | {f"Projekt/{item['code']}" for item in projects}
                | {item["tag"] for item in areas}
            ),
            "storage_paths": (
                {item["name"] for item in metadata.get("storage_paths", [])}
                | {f"Projekt/{item['code']}" for item in projects}
                | {f"Geschützt/{item['name']}" for item in areas}
            ),
        }

    def delete(self, report: RunReport) -> None:
        specs = self._document_specs()
        names = {item["filename"] for item in specs}
        if report.dry_run:
            report.action(
                "paperless", f"{len(names)} Dokumente und deklarierte Governance würden gelöscht"
            )
            return
        api = self._api()
        api.authenticate()
        deleted_docs = 0
        for item in api.list_resource("documents", refresh=True):
            original = item.get("original_file_name") or item.get("filename")
            title_match = f"{item.get('title', '')}.pdf" in names
            if original not in names and not title_match:
                continue
            api._request("DELETE", f"/api/documents/{item['id']}/")
            deleted_docs += 1
        workflows = api.list_resource("workflows", refresh=True)
        for item in workflows:
            if str(item.get("name", "")).startswith("DMS | "):
                api._request("DELETE", f"/api/workflows/{item['id']}/")
        managed = self._managed_names()
        for resource in ("tags", "storage_paths", "document_types", "custom_fields", "groups"):
            for item in api.list_resource(resource, refresh=True):
                if item.get("name") in managed[resource]:
                    api._request("DELETE", f"/api/{resource}/{item['id']}/")
        report.action("paperless", f"{deleted_docs} Demodokumente und Governance gelöscht")


class ErpNextDemo:
    def __init__(self) -> None:
        self.client = HttpClient(
            os.getenv(
                "ERPNEXT_API_URL",
                f"http://localhost:{os.getenv('ERPNEXT_PORT', '8081')}",
            )
        )
        self.username = os.getenv("ERPNEXT_USERNAME", "Administrator")
        self.password = os.getenv("ERPNEXT_ADMIN_PASSWORD", "admin-demo-change-me")
        self.records = json.loads(
            (ROOT / "deployment/erpnext/demo_api_records.json").read_text(encoding="utf-8")
        )["records"]
        api_key = os.getenv("ERPNEXT_API_KEY", "")
        api_secret = os.getenv("ERPNEXT_API_SECRET", "")
        if api_key and api_secret:
            self.client.headers["Authorization"] = f"token {api_key}:{api_secret}"

    def _authenticate(self) -> None:
        if "Authorization" not in self.client.headers:
            self.client.form(
                "POST", "/api/method/login", {"usr": self.username, "pwd": self.password}
            )

    @staticmethod
    def _resource(doctype: str, name: str | None = None) -> str:
        base = f"/api/resource/{urllib.parse.quote(doctype, safe='')}"
        return f"{base}/{urllib.parse.quote(name, safe='')}" if name else base

    def _find(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        doctype = record["doctype"]
        query = urllib.parse.urlencode(
            {
                "filters": json.dumps(
                    [[doctype, record["key_field"], "=", record["key_value"]]],
                    ensure_ascii=False,
                ),
                "fields": json.dumps(["name"]),
                "limit_page_length": 100,
            }
        )
        payload = self.client.request("GET", f"{self._resource(doctype)}?{query}")
        return payload.get("data", []) if isinstance(payload, dict) else []

    def setup(self, report: RunReport) -> None:
        if report.dry_run:
            report.action(
                "erpnext", f"{len(self.records)} deklarierte Stammdatensätze würden synchronisiert"
            )
            return
        self._authenticate()
        created = 0
        updated = 0
        for record in self.records:
            found = self._find(record)
            if found:
                update_omit = set(record.get("update_omit", []))
                update_values = {
                    key: value
                    for key, value in record["values"].items()
                    if key not in update_omit
                }
                self.client.request(
                    "PUT", self._resource(record["doctype"], found[0]["name"]), update_values
                )
                updated += 1
            else:
                self.client.request("POST", self._resource(record["doctype"]), record["values"])
                created += 1
        report.action("erpnext", f"{created} Datensätze angelegt, {updated} aktualisiert")

    def delete(self, report: RunReport) -> None:
        if report.dry_run:
            report.action(
                "erpnext", f"{len(self.records)} exakt deklarierte Datensätze würden gelöscht"
            )
            return
        self._authenticate()
        deleted = 0
        for record in reversed(self.records):
            if not record.get("delete", True):
                continue
            for found in self._find(record):
                self.client.request("DELETE", self._resource(record["doctype"], found["name"]))
                deleted += 1
        report.action("erpnext", f"{deleted} exakt deklarierte Demo-Stammdatensätze gelöscht")


HANDLERS = {
    "platform": PlatformDemo,
    "keycloak": KeycloakDemo,
    "redmine": RedmineDemo,
    "paperless": PaperlessDemo,
    "erpnext": ErpNextDemo,
}


def parse_systems(value: str) -> tuple[str, ...]:
    systems = tuple(
        dict.fromkeys(item.strip().casefold() for item in value.split(",") if item.strip())
    )
    unknown = sorted(set(systems) - set(HANDLERS))
    if unknown:
        raise argparse.ArgumentTypeError(f"Unbekannte Systeme: {', '.join(unknown)}")
    return systems


def run(mode: str, systems: Iterable[str], *, dry_run: bool) -> RunReport:
    report = RunReport(mode=mode, dry_run=dry_run)
    for system in systems:
        try:
            handler = HANDLERS[system]()
            getattr(handler, mode)(report)
        except (DemoApiError, OSError, ValueError, KeyError) as exc:
            report.error(system, str(exc))
    return report


def build_parser(mode: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Füllt alle Anwendungen idempotent über deren APIs mit Demodaten."
            if mode == "setup"
            else "Löscht ausschließlich deklarierte Demodaten über die Anwendungs-APIs."
        )
    )
    parser.add_argument(
        "--systems",
        type=parse_systems,
        default=DEFAULT_SYSTEMS,
        help=f"Kommagetrennt; Standard: {','.join(DEFAULT_SYSTEMS)}",
    )
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--dry-run", action="store_true", help="Nur geplante Aktionen anzeigen")
    if mode == "delete":
        parser.add_argument(
            "--confirm",
            default="",
            help=f"Für echte Löschung exakt {DELETE_CONFIRMATION} angeben",
        )
    return parser


def main(mode: str, argv: list[str] | None = None) -> int:
    parser = build_parser(mode)
    args = parser.parse_args(argv)
    load_dotenv(args.env_file)
    dry_run = bool(args.dry_run)
    if mode == "delete" and args.confirm != DELETE_CONFIRMATION:
        dry_run = True
        print(
            f"Sicherheitsmodus: keine Löschung ohne --confirm {DELETE_CONFIRMATION}.",
            file=sys.stderr,
        )
    report = run(mode, args.systems, dry_run=dry_run)
    for action in report.actions:
        print(action)
    for error in report.errors:
        print(f"FEHLER {error}", file=sys.stderr)
    print(
        json.dumps(
            {
                "mode": report.mode,
                "dry_run": report.dry_run,
                "systems": list(args.systems),
                "actions": len(report.actions),
                "errors": len(report.errors),
            },
            ensure_ascii=False,
        )
    )
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main("setup"))
