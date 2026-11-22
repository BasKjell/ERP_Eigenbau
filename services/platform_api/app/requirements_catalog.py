"""Versionierter Requirements-Katalog -> FLOWWORK (führendes Register) mit Rückverfolgbarkeit.

``check`` prüft Struktur und dass jede Verifikation auf einen existierenden Test zeigt.
``sync`` überträgt Anforderungen, automatisierte Testfälle und ``verifies``-Beziehungen
idempotent nach FLOWWORK. Geänderte Inhalte erzeugen eine neue Version; einen von Menschen
gesetzten Status (approved, verified, rejected) überschreibt der Katalog nie.

    python -m app.requirements_catalog check --catalog requirements/catalog.yaml --repo .
    python -m app.requirements_catalog sync --catalog /app/requirements/catalog.yaml
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from .store import ScenarioStore, utc_now

STATUSES = {"draft", "review", "approved", "verified", "rejected"}
HUMAN_STATUSES = {"approved", "verified", "rejected"}
TYPES = {"Stakeholder", "System", "Software", "Hardware", "Interface", "Safety"}
PRIORITIES = {"Muss": "Must", "Soll": "Should", "Kann": "Could"}
REQUIREMENT_ID = re.compile(r"REQ-[A-Z]{2,5}-\d{3}")
TEST_REF = re.compile(r"(?P<path>[A-Za-z0-9_./-]+\.py)::(?P<name>test_[A-Za-z0-9_]+)")
ACTOR = "Requirements-Katalog"


class CatalogError(ValueError):
    pass


def load(path: Path) -> dict[str, Any]:
    try:
        catalog = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise CatalogError(f"Katalog nicht lesbar: {type(exc).__name__}") from exc
    if not isinstance(catalog, dict) or catalog.get("schema") != "flow-requirements-1":
        raise CatalogError("Katalog braucht schema: flow-requirements-1")
    if not isinstance(catalog.get("requirements"), list) or not catalog["requirements"]:
        raise CatalogError("Katalog enthält keine Anforderungen")
    return catalog


def check(catalog: dict[str, Any], repo: Path | None = None) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    for item in catalog["requirements"]:
        rid = str(item.get("id", ""))
        if not REQUIREMENT_ID.fullmatch(rid):
            problems.append(f"{rid or '?'}: ungültige ID")
        if rid in seen:
            problems.append(f"{rid}: doppelt")
        seen.add(rid)
        for field in ("title", "text", "source"):
            if not str(item.get(field) or "").strip():
                problems.append(f"{rid}: {field} fehlt")
        if item.get("status") not in STATUSES:
            problems.append(f"{rid}: unbekannter Status")
        if item.get("type") not in TYPES:
            problems.append(f"{rid}: unbekannter Typ")
        if item.get("priority") not in PRIORITIES:
            problems.append(f"{rid}: Priorität muss Muss, Soll oder Kann sein")
        criteria = item.get("acceptance_criteria")
        if not isinstance(criteria, list) or not criteria or not all(str(c).strip() for c in criteria):
            problems.append(f"{rid}: mindestens ein Akzeptanzkriterium erforderlich")
        verification = item.get("verification")
        if not isinstance(verification, list) or not verification:
            problems.append(f"{rid}: keine Verifikation")
            continue
        for ref in verification:
            match = TEST_REF.fullmatch(str(ref))
            if match is None:
                problems.append(f"{rid}: Verifikation {ref!r} ist kein Testverweis")
                continue
            if repo is not None:
                path = repo / match["path"]
                if not path.is_file() or f"def {match['name']}(" not in path.read_text(encoding="utf-8"):
                    problems.append(f"{rid}: Test {ref} existiert nicht")
    return problems


def _stable(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:8].upper()}"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def sync(catalog: dict[str, Any], store: ScenarioStore) -> dict[str, int]:
    problems = check(catalog)
    if problems:
        raise CatalogError("; ".join(problems))
    project = str(catalog.get("project") or "FLOW-PLATFORM")
    counts = {"requirements_new": 0, "requirements_updated": 0, "tests_new": 0, "links_new": 0}

    def apply(state: dict[str, Any]) -> None:
        work = state["work"]
        work.setdefault("relationships", [])
        work.setdefault("test_cases", [])
        now = utc_now()
        for item in catalog["requirements"]:
            values = {
                "title": item["title"],
                "text": " ".join(str(item["text"]).split()),
                "type": item["type"],
                "priority": PRIORITIES[item["priority"]],
                "acceptance_criteria": "\n".join(str(c) for c in item["acceptance_criteria"]),
                "source": item["source"],
            }
            digest = _digest(values)
            existing = next((r for r in work["requirements"] if r.get("id") == item["id"]), None)
            tests = [str(ref) for ref in item["verification"]]
            if existing is None:
                work["requirements"].append({
                    "id": item["id"], **values, "owner": "Product Owner (Bas)", "status": item["status"],
                    "version": 1, "project": project, "parent_id": None, "issue_id": None, "wiki_title": None,
                    "verification": _stable("TC-AUTO", tests[0]), "catalog_digest": digest,
                    "created_at": now, "updated_at": now, "comments": [], "custom_fields": {},
                    "history": [{"version": 1, "actor": ACTOR, "at": now, "note": "Aus requirements/catalog.yaml übernommen"}],
                })
                counts["requirements_new"] += 1
            elif existing.get("catalog_digest") != digest:
                existing.update(values)
                existing["catalog_digest"] = digest
                existing["version"] = int(existing.get("version", 1)) + 1
                existing["updated_at"] = now
                if existing.get("status") not in HUMAN_STATUSES:
                    existing["status"] = item["status"]
                existing.setdefault("history", []).insert(0, {
                    "version": existing["version"], "actor": ACTOR, "at": now,
                    "note": "Katalogänderung übernommen; Freigaben bleiben unverändert"})
                counts["requirements_updated"] += 1
            for ref in tests:
                test_id = _stable("TC-AUTO", ref)
                if not any(t.get("id") == test_id for t in work["test_cases"]):
                    name = ref.split("::", 1)[1]
                    work["test_cases"].append({
                        "id": test_id, "title": name.replace("test_", "", 1).replace("_", " "), "type": "TestCase",
                        "status": "approved", "owner": "CI", "automated": True, "reference": ref,
                        "preconditions": "Automatisierter Test in der CI (make test / make agents-test)",
                        "steps": [{"order": 1, "action": f"pytest {ref}", "expected": "bestanden"}],
                        "expected_result": "Test bestanden", "version": 1, "project": project,
                        "created_at": now, "updated_at": now,
                    })
                    counts["tests_new"] += 1
                link_id = _stable("REL-CAT", f"{item['id']}->{test_id}")
                if not any(r.get("id") == link_id for r in work["relationships"]):
                    work["relationships"].append({
                        "id": link_id, "source_id": item["id"], "source_type": item["type"], "target_id": test_id,
                        "target_type": "TestCase", "relationship_type": "verifies", "description": "Katalog",
                        "suspect": False, "suspect_reason": None, "created_at": now, "created_by": ACTOR,
                    })
                    counts["links_new"] += 1
        work.setdefault("activity", []).insert(0, {
            "at": now, "actor": ACTOR,
            "message": f"Katalog {project} v{catalog.get('version')} abgeglichen ({counts['requirements_new']} neu, "
                       f"{counts['requirements_updated']} geändert)"})

    store.mutate(apply)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["check", "sync"])
    parser.add_argument("--catalog", type=Path, default=Path("requirements/catalog.yaml"))
    parser.add_argument("--repo", type=Path, default=None, help="Repository-Wurzel für die Testprüfung")
    args = parser.parse_args()
    try:
        catalog = load(args.catalog)
        if args.action == "check":
            problems = check(catalog, args.repo)
            for problem in problems:
                print(f"FEHLER {problem}", file=sys.stderr)
            if problems:
                return 1
            tests = sum(len(item["verification"]) for item in catalog["requirements"])
            print(f"Requirements-Katalog gültig: {len(catalog['requirements'])} Anforderungen, {tests} Testverweise")
            return 0
        from .config import settings

        counts = sync(catalog, ScenarioStore(settings.data_file, settings.seed_file))
        print(json.dumps(counts))
        return 0
    except CatalogError as exc:
        print(f"Katalog: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
