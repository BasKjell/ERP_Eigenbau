"""Requirements-Katalog und Rückverfolgbarkeit in FLOWWORK (REQ-REQ-001, AGENTS.md §1)."""

from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest
from app.main import store
from app.requirements_catalog import CatalogError, check, load, sync


def _locate() -> tuple[Path, Path | None]:
    configured = os.getenv("REQUIREMENTS_CATALOG")
    for parent in Path(__file__).resolve().parents:
        if (parent / "requirements" / "catalog.yaml").is_file() and (parent / "services" / "agent_orchestrator").is_dir():
            return parent / "requirements" / "catalog.yaml", parent
    if configured and Path(configured).is_file():
        return Path(configured), None  # Container-Build: Struktur prüfen, Testverweise prüft die CI
    pytest.skip("requirements/catalog.yaml nicht verfügbar", allow_module_level=True)
    raise AssertionError


CATALOG, ROOT = _locate()


def setup_function() -> None:
    store.reset()


def test_catalog_is_complete_and_every_verification_points_to_a_test() -> None:
    catalog = load(CATALOG)
    assert check(catalog, ROOT) == []
    ids = {item["id"] for item in catalog["requirements"]}
    assert {"REQ-AGT-007", "REQ-PRT-001", "REQ-PRT-002", "REQ-DOC-001", "REQ-REQ-001"} <= ids
    assert all(item["status"] == "review" for item in catalog["requirements"]), "Freigaben setzt nur ein Mensch"


def test_check_reports_missing_tests_and_bad_entries(tmp_path: Path) -> None:
    catalog = load(CATALOG)
    broken = copy.deepcopy(catalog)
    broken["requirements"][0]["verification"] = ["services/platform_api/tests/test_dms.py::test_gibt_es_nicht"]
    broken["requirements"][1]["acceptance_criteria"] = []
    broken["requirements"][2]["id"] = broken["requirements"][3]["id"]
    problems = check(broken, ROOT)
    if ROOT is not None:
        assert any("existiert nicht" in p for p in problems)
    assert any("Akzeptanzkriterium" in p for p in problems)
    assert any("doppelt" in p for p in problems)
    with pytest.raises(CatalogError):
        sync(broken, store)


def test_sync_is_idempotent_and_versions_changes_without_overwriting_approvals() -> None:
    catalog = load(CATALOG)
    first = sync(catalog, store)
    assert first["requirements_new"] == len(catalog["requirements"]) and first["links_new"] > 0
    assert sync(catalog, store) == {"requirements_new": 0, "requirements_updated": 0, "tests_new": 0, "links_new": 0}
    work = store.get()["work"]
    item = next(r for r in work["requirements"] if r["id"] == "REQ-DOC-003")
    assert item["project"] == "FLOW-PLATFORM" and item["status"] == "review"
    links = [r for r in work["relationships"] if r["source_id"] == "REQ-DOC-003"]
    assert links and all(r["relationship_type"] == "verifies" for r in links)

    def approve(state: dict) -> None:
        next(r for r in state["work"]["requirements"] if r["id"] == "REQ-DOC-003")["status"] = "approved"

    store.mutate(approve)
    changed = copy.deepcopy(catalog)
    next(r for r in changed["requirements"] if r["id"] == "REQ-DOC-003")["title"] = "Sortierung (präzisiert)"
    assert sync(changed, store)["requirements_updated"] == 1
    item = next(r for r in store.get()["work"]["requirements"] if r["id"] == "REQ-DOC-003")
    assert item["version"] == 2 and item["status"] == "approved"
