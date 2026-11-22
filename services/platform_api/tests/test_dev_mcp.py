"""FLOWAI-Werkzeuge „Entwicklung & Repository“ (REQ-AGT-018, REQ-AGT-019)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from app.agent_drafts import dev_mcp_token
from app.main import app, store
from app.repo_access import RepoAccess, RepoError
from fastapi.testclient import TestClient

client = TestClient(app)


def setup_function() -> None:
    store.reset()


@pytest.fixture()
def repo(tmp_path: Path) -> RepoAccess:
    (tmp_path / "services" / "app").mkdir(parents=True)
    (tmp_path / "services" / "app" / "dms.py").write_text("ALLOWED = {'.pdf'}\ntoken = 'ghp_" + "a" * 36 + "'\n")
    (tmp_path / "services" / ".env").write_text("SECRET=1\n")
    (tmp_path / ".env").write_text("SECRET=1\n")
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / "x.txt").write_text("geheim\n")
    os.symlink(tmp_path / ".env", tmp_path / "services" / "link.txt")
    return RepoAccess(tmp_path)


def test_reads_with_line_numbers_and_redacts_secrets(repo: RepoAccess) -> None:
    result = repo.read_file("services/app/dms.py")
    assert result["content"].startswith("    1  ALLOWED")
    assert "ghp_" not in result["content"] and "[GESCHWÄRZT]" in result["content"]
    hits = repo.search("allowed")["hits"]
    assert hits[0]["path"] == "services/app/dms.py" and hits[0]["line"] == 1


@pytest.mark.parametrize("path", [".env", "services/.env", "../etc/passwd", "private/x.txt", "services/link.txt"])
def test_secrets_and_unreleased_areas_are_blocked(repo: RepoAccess, path: str) -> None:
    with pytest.raises(RepoError):
        repo.read_file(path)
    listed = {f["path"] for f in repo.list_files(".")["files"]}
    assert listed == {"services/app/dms.py"}


def test_internal_endpoints_require_the_service_token() -> None:
    assert client.get("/api/agents/internal/status").status_code == 401
    body = {"title": "Titel lang genug", "goal": "Zweck lang genug", "behavior": "Verhalten lang genug"}
    bad = client.post("/api/agents/internal/drafts", json=body, headers={"Authorization": "Bearer falsch"})
    assert bad.status_code == 401


def test_flowai_can_only_propose_and_the_person_submits() -> None:
    body = {"title": "STL-Dateien ablegen", "goal": "Engineering legt 3D-Modelle im DMS ab",
            "behavior": "Upload akzeptiert .stl mit Dokumenttyp 3D-Modell STL", "success_example": "teil.stl hochladen",
            "scope": "dms-komplett", "note": "aus dem Chat"}
    created = client.post("/api/agents/internal/drafts", json=body,
                          headers={"Authorization": f"Bearer {dev_mcp_token()}"})
    assert created.status_code == 201, created.text
    draft = created.json()
    assert draft["status"] == "offen" and draft["confirm_url"].endswith(f"/agents?draft={draft['id']}")
    assert [d["id"] for d in client.get("/api/agents/drafts").json()["drafts"]] == [draft["id"]]
    assert client.get(f"/api/agents/drafts/{draft['id']}").json()["scope"] == "dms-komplett"
    status = client.get("/api/agents/internal/status", headers={"Authorization": f"Bearer {dev_mcp_token()}"}).json()
    assert status["offene_vorschlaege"][0]["id"] == draft["id"]
    discarded = client.post(f"/api/agents/drafts/{draft['id']}/discard")
    assert discarded.status_code == 200 and discarded.json()["status"] == "verworfen"
    assert client.get("/api/agents/drafts").json()["drafts"] == []
    assert client.post(f"/api/agents/drafts/{draft['id']}/discard").status_code == 409
