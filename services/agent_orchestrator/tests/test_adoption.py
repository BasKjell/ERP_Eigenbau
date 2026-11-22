"""Übernahme abgenommener Kandidaten, Vorschau für G4 und Laufbudget (REQ-AGT-015, -016, -017)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from flowagents.adoption import Adoption, slug
from flowagents.sandbox import SandboxError

from .conftest import KEY_USER, PO, TECH_LEAD, auftrag, drive, open_decision


class FakePreview:
    def __init__(self) -> None:
        self.started: list[Path] = []
        self.stopped = 0

    def start(self, workspace: Path) -> str:
        self.started.append(workspace)
        return "http://localhost:8098"

    def stop(self) -> None:
        self.stopped += 1


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def submit(engine, **overrides):  # noqa: ANN001, ANN003, ANN201
    return engine.submit(auftrag(**overrides), PO, f"adopt-{len(engine.store.runs()) + 1:04d}-key")


def test_accepted_fachabnahme_becomes_a_local_branch_without_touching_the_checkout(
    make_engine, git_repo: Path, tmp_path: Path  # noqa: ANN001
) -> None:
    head_before = git(git_repo, "rev-parse", "HEAD")
    adoption = Adoption(git_repo, tmp_path / "state", allowed_prefixes=("docs/",))
    preview = FakePreview()
    engine = make_engine(adoption=adoption, preview=preview)
    run = submit(engine)
    drive(engine)
    decision = open_decision(engine, run["id"])
    assert decision["gate"] == "G4" and decision["context"]["preview_url"] == "http://localhost:8098/dms"
    assert preview.started and engine.overview()["runs"][0]["preview_url"] == "http://localhost:8098/dms"
    task = engine.overview()["decisions"][0]
    assert task["auftrag"]["id"] == "A-001" and task["auftrag"]["title"].startswith("Verfahrensanweisungen")
    assert task["context"]["preview_url"] == "http://localhost:8098/dms"
    assert task["focus"] == ["implementierung", "dokumentation", "prozessbewertung", "nachweise"]
    engine.decide(decision["id"], KEY_USER, "annehmen", "passt")
    assert preview.stopped >= 1
    result = engine.store.latest_artifact(run["id"], "uebernahme")["content"]
    assert result["branch"].startswith("agent/A-001-verfahrensanweisungen")
    assert git(git_repo, "rev-parse", "HEAD") == head_before, "Checkout bleibt unverändert"
    assert git(git_repo, "status", "--porcelain") == ""
    assert "Änderung A-001" in git(git_repo, "show", f"{result['branch']}:docs/dms.md")
    assert "Fachabnahme G4 durch Tobias Neumann" in git(git_repo, "log", "-1", "--format=%B", result["branch"])
    assert engine.overview()["runs"][0]["branch"] == result["branch"]


def test_rejected_fachabnahme_creates_no_branch(make_engine, git_repo: Path, tmp_path: Path) -> None:  # noqa: ANN001
    engine = make_engine(adoption=Adoption(git_repo, tmp_path / "state", allowed_prefixes=("docs/",)),
                         preview=FakePreview())
    run = submit(engine)
    drive(engine)
    engine.decide(open_decision(engine, run["id"])["id"], KEY_USER, "ablehnen", "Text ist falsch")
    assert engine.store.latest_artifact(run["id"], "uebernahme") is None
    assert git(git_repo, "branch", "--list", "agent/*") == ""


def test_adoption_refuses_a_tampered_or_foreign_candidate(make_engine, git_repo: Path, tmp_path: Path) -> None:  # noqa: ANN001
    engine = make_engine()
    run = submit(engine)
    drive(engine)
    refs = engine.store.latest_artifact(run["id"], "implementierung")["refs"]
    adoption = Adoption(git_repo, tmp_path / "state", allowed_prefixes=("docs/",))
    with pytest.raises(SandboxError, match="abgenommenen Digest"):
        adoption.adopt(engine.store.run(run["id"]), refs, approved_by="x", digest="sha256:anders")
    Path(refs["workspace"], "docs", "dms.md").write_text("manipuliert", encoding="utf-8")
    with pytest.raises(SandboxError, match="weicht"):
        adoption.adopt(engine.store.run(run["id"]), refs, approved_by="x", digest=refs["digest"])


def test_budget_per_class_and_tech_lead_bonus(make_engine) -> None:  # noqa: ANN001
    engine = make_engine(budgets={"standard": {"max_model_calls": 3}})
    run = submit(engine)
    drive(engine)
    decision = open_decision(engine, run["id"])
    assert "Laufbudget" in decision["question"] and engine.store.run(run["id"])["model_calls"] == 3
    engine.decide(decision["id"], TECH_LEAD, "annehmen", "weiter")
    assert engine._budget(engine.store.run(run["id"]))["max_model_calls"] == 23
    drive(engine)
    assert open_decision(engine, run["id"])["gate"] == "G4"


def test_branch_slug_is_ascii() -> None:
    assert slug("Bedienhilfe für die Titel-Sortierung in FLOWDOC") == "bedienhilfe-fur-die-titel-sortierung-in"


def test_focus_names_what_to_review_for_each_decision(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    run = engine.submit(auftrag(change_class="neue_funktion"), PO, "focus-key-0001")
    drive(engine)
    g1 = engine.overview()["decisions"][0]
    assert g1["gate"] == "G1" and g1["focus"] == ["anforderungen", "baseline", "anforderungsbefund"]
    engine.store.update_run(run["id"], status="blockiert")
    blocked = engine._decision_summary({**engine.store.decisions(run_id=run["id"])[0], "gate": "korrekturlimit",
                                         "step_id": "anforderungspruefung", "context": {}}, {})
    assert blocked["focus"] == ["anforderungsbefund", "anforderungen"]

