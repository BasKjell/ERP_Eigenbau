from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from flowagents import registry as registry_module
from flowagents.engine import Engine
from flowagents.providers import SimulatedProvider
from flowagents.rm import OfflineRM
from flowagents.sandbox import LocalCheck, Sandbox
from flowagents.store import Store

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS_DIR = REPO_ROOT / "agents"

PO = {"username": "demo45", "name": "Helena Friedrich", "roles": ["requirements-user", "work-user"]}
TECH_LEAD = {"username": "demo44", "name": "Alexander Vogel", "roles": ["work-admin"]}
KEY_USER = {"username": "demo12", "name": "Tobias Neumann", "roles": ["work-user"]}
RELEASE = {"username": "demo30", "name": "Leon König", "roles": ["it-user"]}
MANAGEMENT = {"username": "demo40", "name": "Philipp Weiß", "roles": ["management-user"]}
NOBODY = {"username": "demo01", "name": "Anna Schneider", "roles": ["dms-user"]}


def auftrag(**overrides: Any) -> dict[str, Any]:
    values = {
        "title": "Verfahrensanweisungen nach Titel sortieren",
        "goal": "Der Einkauf soll freigegebene Verfahrensanweisungen schneller finden.",
        "user_group": "Einkauf",
        "behavior": "Die DMS-Ansicht sortiert sichtbare, freigegebene Dokumente auf Wunsch nach Titel aufsteigend.",
        "exclusions": "Keine Änderung an Rechten oder Freigabestatus.",
        "success_example": "Bei den Titeln Beta und Alpha erscheint Alpha zuerst.",
        "data_class": "intern",
        "change_class": "standard",
        "scope": "doku",
        "project": "FLOW-DMS",
    }
    values.update(overrides)
    return values


@pytest.fixture()
def registry() -> registry_module.Registry:
    return registry_module.load(AGENTS_DIR)


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "dms.md").write_text("# DMS\n\nBedienhilfe.\n", encoding="utf-8")
    (repo / ".env").write_text("SECRET=1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A", "-f"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "init"],
                   cwd=repo, check=True)
    return repo


@pytest.fixture()
def make_engine(tmp_path: Path, registry: registry_module.Registry, git_repo: Path):
    def factory(*, check_passes: bool = True, providers: dict[str, Any] | None = None,
                profile_providers: dict[str, str] | None = None, sandbox: bool = True,
                demo_mode: bool = False) -> Engine:
        store = Store(tmp_path / "state" / "flow.sqlite")
        command = ["python3", "-c", "import sys; sys.exit(0)" if check_passes else "import sys; print('1 failed'); sys.exit(1)"]
        box = Sandbox(git_repo, tmp_path / "state", base_ref="HEAD", allowed_prefixes=("docs/",),
                      checker=LocalCheck(command)) if sandbox else None
        all_providers = {"simulated": SimulatedProvider(), **(providers or {})}
        mapping = profile_providers or {name: "simulated" for name in ("builder", "coder", "pruefer", "assistenz", "leitung")}
        return Engine(registry, store, all_providers, mapping, OfflineRM(), box,
                      scopes={"doku": {"label": "Doku", "paths": ["docs/dms.md"]}}, demo_mode=demo_mode)

    return factory


def drive(engine: Engine, limit: int = 60) -> None:
    """Bearbeitet Schritte, bis der Lauf wartet, blockiert oder fertig ist."""
    for _ in range(limit):
        if not engine.cycle():
            return
    raise AssertionError("Ablauf kommt nicht zur Ruhe")


def open_decision(engine: Engine, run_id: str) -> dict[str, Any]:
    decisions = engine.store.decisions(status="offen", run_id=run_id)
    assert len(decisions) == 1, decisions
    return decisions[0]
