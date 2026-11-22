from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .config import Settings


class RedmineError(RuntimeError):
    pass


class RedmineClient:
    """Small Redmine REST adapter used by FLOWWORK.

    Redmine remains the system of record for projects, issues, time entries and
    wiki pages. Requirements and baselines are deliberately managed by the
    platform because Redmine has no native, versioned requirements domain.
    """

    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.redmine_base_url.rstrip("/")
        self.public_url = settings.redmine_public_url.rstrip("/")
        self.api_key = settings.redmine_api_key

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def status(self) -> dict[str, Any]:
        if not self.configured:
            return {
                "name": "Redmine",
                "mode": "simulated",
                "configured": False,
                "reachable": False,
                "url": self.public_url,
                "detail": "FLOWWORK-Demodaten aktiv",
            }
        try:
            self._request("GET", "/projects.json?limit=1")
        except RedmineError as exc:
            return {
                "name": "Redmine",
                "mode": "error",
                "configured": True,
                "reachable": False,
                "url": self.public_url,
                "detail": str(exc),
            }
        return {
            "name": "Redmine",
            "mode": "live",
            "configured": True,
            "reachable": True,
            "url": self.public_url,
            "detail": "REST-API verbunden",
        }

    def snapshot(self) -> dict[str, Any]:
        if not self.configured:
            return {"mode": "simulated", "projects": [], "issues": [], "wiki": []}
        try:
            projects_payload = self._request("GET", "/projects.json?limit=100")
            issues_payload = self._request(
                "GET", "/issues.json?status_id=*&limit=100&sort=updated_on:desc"
            )
            projects = projects_payload.get("projects", [])
            issues = [self._normalise_issue(issue) for issue in issues_payload.get("issues", [])]
            wiki: list[dict[str, Any]] = []
            for project in projects[:10]:
                identifier = urllib.parse.quote(str(project.get("identifier", "")), safe="")
                if not identifier:
                    continue
                try:
                    pages = self._request(
                        "GET", f"/projects/{identifier}/wiki/index.json"
                    ).get("wiki_pages", [])
                except RedmineError:
                    pages = []
                for page in pages:
                    title = str(page.get("title", ""))
                    wiki.append(
                        {
                            **page,
                            "project": project.get("name"),
                            "url": f"{self.public_url}/projects/{identifier}/wiki/{urllib.parse.quote(title)}",
                        }
                    )
            return {
                "mode": "live",
                "projects": projects,
                "issues": issues,
                "wiki": wiki,
            }
        except RedmineError as exc:
            return {
                "mode": "error",
                "detail": str(exc),
                "projects": [],
                "issues": [],
                "wiki": [],
            }

    def create_issue(self, values: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            raise RedmineError("Redmine-API ist nicht konfiguriert")
        payload: dict[str, Any] = {
            "project_id": values.get("project_id", "scu-100"),
            "subject": values["subject"],
            "description": values.get("description", ""),
            "priority_id": values.get("priority_id"),
            "due_date": values.get("due_date"),
            "assigned_to_id": values.get("assigned_to_id"),
        }
        payload = {key: value for key, value in payload.items() if value not in (None, "")}
        result = self._request("POST", "/issues.json", {"issue": payload})
        issue = result.get("issue", result)
        return self._normalise_issue(issue)

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["X-Redmine-API-Key"] = self.api_key
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=data, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=4) as response:
                body = response.read()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            raise RedmineError(f"Redmine antwortet mit HTTP {exc.code}: {detail}") from exc
        except (OSError, ValueError, urllib.error.URLError) as exc:
            raise RedmineError(f"Redmine ist nicht erreichbar: {exc}") from exc

    def _normalise_issue(self, issue: dict[str, Any]) -> dict[str, Any]:
        issue_id = str(issue.get("id", ""))
        status = issue.get("status", {})
        project = issue.get("project", {})
        priority = issue.get("priority", {})
        assigned = issue.get("assigned_to", {})
        return {
            "id": issue_id,
            "key": f"#{issue_id}" if issue_id else "#–",
            "subject": issue.get("subject", "Ohne Titel"),
            "description": issue.get("description", ""),
            "status": str(status.get("name", "Neu")),
            "status_id": status.get("id"),
            "project": project.get("name", ""),
            "project_id": project.get("id"),
            "priority": priority.get("name", "Normal"),
            "assignee": assigned.get("name", "Nicht zugewiesen"),
            "due_date": issue.get("due_date"),
            "done_ratio": issue.get("done_ratio", 0),
            "updated_on": issue.get("updated_on"),
            "url": f"{self.public_url}/issues/{issue_id}" if issue_id else self.public_url,
            "source": "redmine",
        }
