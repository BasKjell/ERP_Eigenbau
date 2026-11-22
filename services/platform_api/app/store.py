from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class ScenarioStore:
    """Tiny JSON-backed state store for a durable, resettable management demo."""

    def __init__(self, data_file: Path, seed_file: Path) -> None:
        self.data_file = data_file
        self.seed_file = seed_file
        self._lock = RLock()
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_file.exists():
            self.reset()
        else:
            self._upgrade_schema()

    def _read(self) -> dict[str, Any]:
        with self.data_file.open(encoding="utf-8") as stream:
            return json.load(stream)

    def _seed(self) -> dict[str, Any]:
        with self.seed_file.open(encoding="utf-8") as stream:
            return json.load(stream)

    def _upgrade_schema(self) -> None:
        """Add newly introduced demo domains without resetting user progress."""
        with self._lock:
            state = self._read()
            seed = self._seed()
            changed = False
            for key in (
                "mes",
                "quality",
                "hr",
                "iam",
                "desksharing",
                "work",
                "finance",
                "workplace",
            ):
                if key not in state and key in seed:
                    state[key] = deepcopy(seed[key])
                    changed = True
            if isinstance(state.get("hr"), dict) and isinstance(seed.get("hr"), dict):
                for key in ("admin_users", "recruiting", "payroll"):
                    if key not in state["hr"] and key in seed["hr"]:
                        state["hr"][key] = deepcopy(seed["hr"][key])
                        changed = True
            if isinstance(state.get("work"), dict) and isinstance(seed.get("work"), dict):
                for key in (
                    "catalogs",
                    "field_definitions",
                    "item_types",
                    "relationship_rules",
                    "relationship_types",
                    "relationships",
                    "reviews",
                    "risks",
                    "test_cases",
                    "test_plans",
                    "test_runs",
                    "variants",
                ):
                    if key not in state["work"] and key in seed["work"]:
                        state["work"][key] = deepcopy(seed["work"][key])
                        changed = True
            if isinstance(state.get("desksharing"), dict) and isinstance(
                seed.get("desksharing"), dict
            ):
                if "rooms" not in state["desksharing"]:
                    state["desksharing"]["rooms"] = deepcopy(
                        seed["desksharing"].get("rooms", [])
                    )
                    changed = True
                seed_sites = {
                    item["id"]: item for item in seed["desksharing"].get("sites", [])
                }
                for site in state["desksharing"].get("sites", []):
                    reference = seed_sites.get(site.get("id"), {})
                    for key in ("building_code", "entry_label"):
                        if key not in site and key in reference:
                            site[key] = deepcopy(reference[key])
                            changed = True
                seed_desks = {
                    item["id"]: item for item in seed["desksharing"].get("desks", [])
                }
                for desk in state["desksharing"].get("desks", []):
                    reference = seed_desks.get(desk.get("id"), {})
                    for key in ("room_id", "map_x", "map_y"):
                        if key not in desk and key in reference:
                            desk[key] = deepcopy(reference[key])
                            changed = True
            if isinstance(state.get("documents"), list) and isinstance(
                seed.get("documents"), list
            ):
                existing_ids = {item.get("id") for item in state["documents"]}
                for document in seed["documents"]:
                    if document.get("id") not in existing_ids:
                        state["documents"].append(deepcopy(document))
                        changed = True
            if changed:
                self._write(state)

    def _write(self, state: dict[str, Any]) -> None:
        state["updated_at"] = utc_now()
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.data_file.parent, prefix="scenario-", suffix=".json"
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(state, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            os.replace(temporary_name, self.data_file)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    def get(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._read())

    def mutate(self, operation: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        """Apply one validated domain operation and persist it atomically."""
        with self._lock:
            state = self._read()
            operation(state)
            self._recalculate(state)
            self._write(state)
            return deepcopy(state)

    def reset(self) -> dict[str, Any]:
        with self._lock:
            state = self._seed()
            self._recalculate(state)
            self._write(state)
            return deepcopy(state)

    def purge(self) -> dict[str, Any]:
        """Remove seeded demo records while retaining a readable empty schema."""
        with self._lock:
            state = self._seed()
            state["scenario"] = {
                **state.get("scenario", {}),
                "name": "Leerer Demodatenbestand",
                "description": "Demodaten wurden über die API gelöscht.",
                "data_status": "purged",
            }
            for key in (
                "bom",
                "capacity",
                "documents",
                "projects",
                "purchase_orders",
                "serials",
                "timeline",
                "warehouses",
            ):
                state[key] = []
            for values in state.get("commercial_master_data", {}).values():
                if isinstance(values, list):
                    values.clear()
            state["order"] = {
                "id": "",
                "opportunity": "",
                "quotation": "",
                "work_order": "",
                "customer": "",
                "product": "",
                "product_name": "",
                "quantity": 0,
                "unit_price": 0,
                "total": 0,
                "delivery_date": "",
                "revision": "",
                "status": "Keine Demodaten",
                "progress": 0,
                "delivery_risk": "none",
            }
            for step in state.get("process", []):
                step["status"] = "pending"
                step["progress"] = 0
            state["quality_incident"] = None
            state["metrics"] = {
                "process_progress": 0,
                "completed_steps": 0,
                "total_steps": len(state.get("process", [])),
                "materials_available": 0,
                "finished_units": 0,
                "planned_units": 0,
                "open_incidents": 0,
            }
            workforce = state.get("workforce", {})
            workforce["employees"] = []
            workforce["activity_types"] = []
            mes = state.get("mes", {})
            for key in ("operators", "jobs", "events"):
                mes[key] = []
            quality = state.get("quality", {})
            for key in (
                "audit",
                "adapters",
                "inspection_plans",
                "inspections",
                "instruments",
                "measurement_events",
                "ncrs",
                "operators",
                "receipts",
                "sampling_plans",
            ):
                quality[key] = []
            hr = state.get("hr", {})
            for key in (
                "admin_users",
                "attendance",
                "audit",
                "employees",
                "erp_exports",
                "export_previews",
                "holidays",
                "requests",
            ):
                hr[key] = []
            hr["manager_id"] = ""
            for key in ("applications", "vacancies"):
                hr.get("recruiting", {})[key] = []
            for key in ("periods", "previews", "profiles", "runs"):
                hr.get("payroll", {})[key] = []
            iam = state.get("iam", {})
            iam["users"] = []
            iam["admin"] = {}
            desksharing = state.get("desksharing", {})
            for key in ("audit", "bookings", "desks", "rooms", "sites"):
                desksharing[key] = []
            work = state.get("work", {})
            for key in (
                "activity",
                "baselines",
                "catalogs",
                "field_definitions",
                "issues",
                "item_types",
                "projects",
                "relationship_rules",
                "relationship_types",
                "relationships",
                "requirements",
                "reviews",
                "risks",
                "test_cases",
                "test_plans",
                "test_runs",
                "variants",
                "wiki",
            ):
                work[key] = []
            finance = state.get("finance", {})
            for key in (
                "assets",
                "audit",
                "budgets",
                "cash_forecast",
                "expenses",
                "integration_previews",
                "integration_runs",
                "open_items",
                "orders",
                "quality_costs",
                "rd_projects",
                "subscriptions",
                "warranty_cases",
            ):
                finance[key] = []
            workplace = state.get("workplace", {})
            workplace["supplier_delivery_history"] = []
            self._write(state)
            return deepcopy(state)

    def reset_domain(self, key: str) -> dict[str, Any]:
        """Reset one demo domain while preserving all unrelated progress."""
        with self._lock:
            state = self._read()
            seed = self._seed()
            if key not in seed:
                raise KeyError(key)
            state[key] = deepcopy(seed[key])
            self._recalculate(state)
            self._write(state)
            return deepcopy(state)

    def set_stage(self, stage_id: str) -> dict[str, Any]:
        with self._lock:
            state = self._read()
            ids = [step["id"] for step in state["process"]]
            if stage_id not in ids:
                raise KeyError(stage_id)
            target = ids.index(stage_id)
            for index, step in enumerate(state["process"]):
                step["status"] = "done" if index < target else "pending"
                step["progress"] = 100 if index < target else 0
            state["process"][target]["status"] = "active"
            state["process"][target]["progress"] = 60 if stage_id == "production" else 35
            state["quality_incident"] = None
            self._add_event(
                state,
                f"Praesentationssprung zu: {state['process'][target]['label']}",
                state["process"][target]["system"],
            )
            self._recalculate(state)
            self._write(state)
            return deepcopy(state)

    def advance(self) -> dict[str, Any]:
        with self._lock:
            state = self._read()
            incident = state.get("quality_incident")
            if incident and incident["status"] == "open":
                raise RuntimeError("Qualitaetsabweichung muss zuerst behoben werden")
            active_index = next(
                (i for i, step in enumerate(state["process"]) if step["status"] == "active"),
                None,
            )
            if active_index is None:
                active_index = next(
                    (i for i, step in enumerate(state["process"]) if step["status"] != "done"),
                    None,
                )
            if active_index is None:
                return deepcopy(state)
            completed = state["process"][active_index]
            completed["status"] = "done"
            completed["progress"] = 100
            self._add_event(state, f"{completed['label']} abgeschlossen", completed["system"])
            if active_index + 1 < len(state["process"]):
                following = state["process"][active_index + 1]
                following["status"] = "active"
                following["progress"] = 25
                self._add_event(state, f"{following['label']} gestartet", following["system"])
            self._recalculate(state)
            self._write(state)
            return deepcopy(state)

    def inject_failure(self) -> dict[str, Any]:
        with self._lock:
            state = self._read()
            quality_index = next(
                i for i, step in enumerate(state["process"]) if step["id"] == "quality"
            )
            for index, step in enumerate(state["process"]):
                if index < quality_index:
                    step["status"] = "done"
                    step["progress"] = 100
                elif index > quality_index:
                    step["status"] = "pending"
                    step["progress"] = 0
            quality = state["process"][quality_index]
            quality["status"] = "blocked"
            quality["progress"] = 80
            state["quality_incident"] = {
                "id": "NCR-2027-0017",
                "serial_number": "SN-10004",
                "status": "open",
                "severity": "major",
                "test": "Kommunikationstest",
                "measured": "Keine Antwort auf CAN-Bus nach 3 Versuchen",
                "action": "Steckverbinder J4 pruefen und Funktionstest wiederholen",
            }
            self._add_event(
                state,
                "NCR-2027-0017: Kommunikationstest bei SN-10004 fehlgeschlagen",
                "Qualitaet",
                level="warning",
            )
            self._recalculate(state)
            self._write(state)
            return deepcopy(state)

    def resolve_failure(self) -> dict[str, Any]:
        with self._lock:
            state = self._read()
            incident = state.get("quality_incident")
            if not incident or incident["status"] != "open":
                raise RuntimeError("Keine offene Qualitaetsabweichung")
            incident["status"] = "resolved"
            incident["resolution"] = "Steckverbinder J4 neu verriegelt; Wiederholtest bestanden"
            quality = next(step for step in state["process"] if step["id"] == "quality")
            quality["status"] = "active"
            quality["progress"] = 95
            self._add_event(
                state,
                "SN-10004 nach Nacharbeit erneut geprueft und freigegeben",
                "Qualitaet",
            )
            self._recalculate(state)
            self._write(state)
            return deepcopy(state)

    @staticmethod
    def _add_event(
        state: dict[str, Any], message: str, system: str, level: str = "info"
    ) -> None:
        state["timeline"].insert(
            0,
            {
                "timestamp": utc_now(),
                "message": message,
                "system": system,
                "level": level,
            },
        )
        state["timeline"] = state["timeline"][:12]

    @staticmethod
    def _recalculate(state: dict[str, Any]) -> None:
        process = state["process"]
        done = sum(step["status"] == "done" for step in process)
        progress = round(sum(step["progress"] for step in process) / len(process))
        incident_open = bool(
            state.get("quality_incident")
            and state["quality_incident"].get("status") == "open"
        )
        active = next(
            (step for step in process if step["status"] in {"active", "blocked"}),
            process[-1],
        )
        state["order"]["status"] = active["label"] if done < len(process) else "Abgeschlossen"
        state["order"]["progress"] = progress
        state["order"]["delivery_risk"] = "at_risk" if incident_open else "on_track"
        state["metrics"] = {
            "process_progress": progress,
            "completed_steps": done,
            "total_steps": len(process),
            "materials_available": 100 if done >= 5 else 76,
            "finished_units": 4 if done >= 7 else 0,
            "planned_units": state["order"]["quantity"],
            "open_incidents": 1 if incident_open else 0,
        }
