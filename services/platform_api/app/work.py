from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from .config import Settings
from .redmine import RedmineClient, RedmineError
from .store import ScenarioStore, utc_now


class WorkError(RuntimeError):
    pass


class WorkNotFoundError(WorkError):
    pass


class WorkService:
    """FLOWWORK application service for Redmine plus requirements governance."""

    def __init__(self, store: ScenarioStore, settings: Settings) -> None:
        self.store = store
        self.redmine = RedmineClient(settings)

    def dashboard(self, user: dict[str, Any] | None = None) -> dict[str, Any]:
        work = deepcopy(self._work())
        self._ensure_schema(work)
        snapshot = self.redmine.snapshot()
        tasks = snapshot["issues"] if snapshot["mode"] == "live" else work["issues"]
        projects = snapshot["projects"] if snapshot["mode"] == "live" else work["projects"]
        wiki = snapshot["wiki"] if snapshot["mode"] == "live" and snapshot["wiki"] else work["wiki"]
        requirements = work["requirements"]
        open_tasks = [task for task in tasks if self._status_bucket(task.get("status", "")) != "done"]
        linked = [req for req in requirements if req.get("issue_id") and req.get("verification")]
        approved = [req for req in requirements if req.get("status") in {"approved", "verified"}]
        overdue = [
            task
            for task in open_tasks
            if task.get("due_date") and str(task["due_date"]) < "2026-11-04"
        ]
        return {
            "product": "FLOWWORK",
            "mode": snapshot["mode"],
            "integration": self.redmine.status(),
            "user": user,
            "projects": projects,
            "issues": tasks,
            "board": {
                bucket: [task for task in tasks if self._status_bucket(task.get("status", "")) == bucket]
                for bucket in ("backlog", "progress", "review", "done")
            },
            "requirements": requirements,
            "wiki": wiki,
            "baselines": work["baselines"],
            "item_types": work["item_types"],
            "field_definitions": work["field_definitions"],
            "relationship_types": work["relationship_types"],
            "relationship_rules": work["relationship_rules"],
            "relationships": work["relationships"],
            "relationship_coverage": self._relationship_coverage(work),
            "reviews": work["reviews"],
            "test_cases": work["test_cases"],
            "test_plans": work["test_plans"],
            "test_runs": work["test_runs"],
            "risks": work["risks"],
            "catalogs": work["catalogs"],
            "variants": work["variants"],
            "activity": work.get("activity", [])[:12],
            "metrics": {
                "projects": len(projects),
                "open_tasks": len(open_tasks),
                "overdue_tasks": len(overdue),
                "requirements": len(requirements),
                "approved_requirements": len(approved),
                "trace_coverage": round(len(linked) / len(requirements) * 100) if requirements else 100,
                "open_reviews": len(
                    [item for item in work["reviews"] if item.get("status") == "in_progress"]
                ),
                "suspect_links": len(
                    [item for item in work["relationships"] if item.get("suspect")]
                ),
                "test_pass_rate": self._test_pass_rate(work),
                "high_risks": len(
                    [item for item in work["risks"] if int(item.get("rating", 0)) >= 12]
                ),
            },
            "traceability": [self._trace_row(req, tasks, wiki) for req in requirements],
        }

    def create_issue(self, values: dict[str, Any], actor: str) -> dict[str, Any]:
        values = deepcopy(values)
        requirement_id = values.pop("requirement_id", None)
        if self.redmine.configured:
            priority_ids = {"Niedrig": 1, "Normal": 2, "Hoch": 3, "Dringend": 4}
            values["priority_id"] = priority_ids.get(values.pop("priority", "Normal"), 2)
            try:
                issue = self.redmine.create_issue(values)
            except RedmineError as exc:
                raise WorkError(str(exc)) from exc
        else:
            work = self._work()
            next_id = str(max((int(item["id"]) for item in work["issues"]), default=0) + 1)
            issue = {
                "id": next_id,
                "key": f"#{next_id}",
                "subject": values["subject"],
                "description": values.get("description", ""),
                "status": "Neu",
                "project": "SCU-100 Produktentwicklung",
                "priority": values.get("priority", "Normal"),
                "assignee": values.get("assignee") or "Nicht zugewiesen",
                "due_date": str(values["due_date"]) if values.get("due_date") else None,
                "done_ratio": 0,
                "updated_on": utc_now(),
                "url": f"/work#issue-{next_id}",
                "source": "demo",
            }

            def append_issue(state: dict[str, Any]) -> None:
                state["work"]["issues"].append(issue)
                self._add_activity(state["work"], actor, f"Ticket {issue['key']} angelegt")

            self.store.mutate(append_issue)
        if requirement_id:
            self.update_requirement(
                requirement_id,
                {"issue_id": issue["key"], "change_note": f"Mit {issue['key']} verknüpft"},
                actor,
            )
        return issue

    def create_requirement(self, values: dict[str, Any], actor: str) -> dict[str, Any]:
        work = self._work()
        self._ensure_schema(work)
        self._validate_item_values(work, values, creating=True)
        next_number = max(
            (int(item["id"].rsplit("-", 1)[-1]) for item in work["requirements"]),
            default=0,
        ) + 1
        requirement = {
            "id": f"REQ-SCU-{next_number:03d}",
            **deepcopy(values),
            "status": "draft",
            "version": 1,
            "issue_id": None,
            "wiki_title": "SCU-100_Requirements",
            "verification": None,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "history": [
                {"version": 1, "actor": actor, "at": utc_now(), "note": "Anforderung angelegt"}
            ],
            "custom_fields": deepcopy(values.pop("custom_fields", {})),
        }

        def append_requirement(state: dict[str, Any]) -> None:
            self._ensure_schema(state["work"])
            if requirement.get("parent_id") and not any(
                item["id"] == requirement["parent_id"]
                for item in state["work"]["requirements"]
            ):
                raise WorkNotFoundError("Übergeordnete Anforderung wurde nicht gefunden")
            state["work"]["requirements"].append(requirement)
            self._add_activity(
                state["work"], actor, f"Anforderung {requirement['id']} angelegt"
            )

        self.store.mutate(append_requirement)
        return requirement

    def update_requirement(
        self, requirement_id: str, changes: dict[str, Any], actor: str
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        allowed = {
            "title",
            "text",
            "status",
            "priority",
            "owner",
            "acceptance_criteria",
            "issue_id",
            "wiki_title",
            "verification",
            "custom_fields",
        }
        note = str(changes.pop("change_note", "Änderung über FLOWWORK"))

        def update(state: dict[str, Any]) -> None:
            requirement = next(
                (
                    item
                    for item in state["work"]["requirements"]
                    if item["id"] == requirement_id
                ),
                None,
            )
            if requirement is None:
                raise WorkNotFoundError("Anforderung wurde nicht gefunden")
            candidate = {**requirement, **changes}
            self._ensure_schema(state["work"])
            self._validate_item_values(state["work"], candidate, creating=False)
            effective = {
                key: value
                for key, value in changes.items()
                if key in allowed and value is not None and requirement.get(key) != value
            }
            if not effective:
                result.update(deepcopy(requirement))
                return
            requirement.update(effective)
            requirement["version"] = int(requirement.get("version", 1)) + 1
            requirement["updated_at"] = utc_now()
            requirement.setdefault("history", []).insert(
                0,
                {
                    "version": requirement["version"],
                    "actor": actor,
                    "at": utc_now(),
                    "note": note,
                    "fields": sorted(effective),
                },
            )
            self._mark_suspect_links(
                state["work"], requirement_id, actor, sorted(effective)
            )
            self._add_activity(
                state["work"], actor, f"{requirement_id} auf v{requirement['version']} geändert"
            )
            result.update(deepcopy(requirement))

        self.store.mutate(update)
        return result

    def create_baseline(self, values: dict[str, Any], actor: str) -> dict[str, Any]:
        work = self._work()
        requested = set(values.get("requirement_ids", []))
        selected = [
            item
            for item in work["requirements"]
            if not requested or item["id"] in requested
        ]
        if requested - {item["id"] for item in selected}:
            raise WorkNotFoundError("Mindestens eine Anforderung wurde nicht gefunden")
        if not selected:
            raise WorkError("Eine Baseline benötigt mindestens eine Anforderung")
        next_number = len(work["baselines"]) + 1
        baseline = {
            "id": f"BL-SCU-{next_number:03d}",
            "name": values["name"],
            "description": values.get("description", ""),
            "status": "frozen",
            "created_at": utc_now(),
            "created_by": actor,
            "items": [
                {
                    "requirement_id": item["id"],
                    "version": item["version"],
                    "status": item["status"],
                    "checksum_source": f"{item['id']}:{item['version']}:{item['updated_at']}",
                }
                for item in selected
            ],
        }

        def append_baseline(state: dict[str, Any]) -> None:
            state["work"]["baselines"].append(baseline)
            self._add_activity(state["work"], actor, f"Baseline {baseline['id']} eingefroren")

        self.store.mutate(append_baseline)
        return baseline

    def create_field_definition(
        self, values: dict[str, Any], actor: str
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def create(state: dict[str, Any]) -> None:
            work = state["work"]
            self._ensure_schema(work)
            key = self._slug(values.get("key") or values["name"]).upper().replace("-", "_")
            if any(item["key"] == key for item in work["field_definitions"]):
                raise WorkError(f"Das Feld {key} existiert bereits")
            field_type = values["field_type"]
            options = list(values.get("options") or [])
            if field_type in {"select", "multi_select"} and not options:
                raise WorkError("Auswahlfelder benötigen mindestens eine Option")
            definition = {
                "id": f"FLD-{len(work['field_definitions']) + 1:03d}",
                "key": key,
                "name": values["name"],
                "field_type": field_type,
                "required": bool(values.get("required")),
                "options": options,
                "applies_to": list(values.get("applies_to") or []),
                "description": values.get("description", ""),
                "created_by": actor,
                "created_at": utc_now(),
            }
            work["field_definitions"].append(definition)
            for item_type in work["item_types"]:
                if item_type["key"] in definition["applies_to"]:
                    item_type.setdefault("field_keys", []).append(key)
            self._add_activity(work, actor, f"Eigenes Feld {definition['name']} angelegt")
            result.update(deepcopy(definition))

        self.store.mutate(create)
        return result

    def create_item_type(self, values: dict[str, Any], actor: str) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def create(state: dict[str, Any]) -> None:
            work = state["work"]
            self._ensure_schema(work)
            key = self._slug(values.get("key") or values["name"])
            if any(item["key"].casefold() == key.casefold() for item in work["item_types"]):
                raise WorkError(f"Der Itemtyp {key} existiert bereits")
            item_type = {
                "id": f"TYPE-{len(work['item_types']) + 1:03d}",
                "key": key,
                "name": values["name"],
                "prefix": str(values.get("prefix") or key[:4]).upper(),
                "description": values.get("description", ""),
                "field_keys": list(values.get("field_keys") or []),
                "workflow": list(
                    values.get("workflow")
                    or ["draft", "review", "approved", "verified", "rejected"]
                ),
                "created_by": actor,
                "created_at": utc_now(),
            }
            known_fields = {item["key"] for item in work["field_definitions"]}
            if set(item_type["field_keys"]) - known_fields:
                raise WorkError("Mindestens ein zugeordnetes Feld ist nicht definiert")
            work["item_types"].append(item_type)
            self._add_activity(work, actor, f"Itemtyp {item_type['name']} angelegt")
            result.update(deepcopy(item_type))

        self.store.mutate(create)
        return result

    def create_relationship_type(
        self, values: dict[str, Any], actor: str
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def create(state: dict[str, Any]) -> None:
            work = state["work"]
            self._ensure_schema(work)
            key = self._slug(values.get("key") or values["name"])
            if any(item["key"] == key for item in work["relationship_types"]):
                raise WorkError(f"Der Beziehungstyp {key} existiert bereits")
            relationship_type = {
                "id": f"RT-{len(work['relationship_types']) + 1:03d}",
                "key": key,
                "name": values["name"],
                "reverse_name": values.get("reverse_name") or values["name"],
                "description": values.get("description", ""),
                "created_by": actor,
            }
            work["relationship_types"].append(relationship_type)
            self._add_activity(work, actor, f"Beziehungstyp {values['name']} angelegt")
            result.update(deepcopy(relationship_type))

        self.store.mutate(create)
        return result

    def create_relationship_rule(
        self, values: dict[str, Any], actor: str
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def create(state: dict[str, Any]) -> None:
            work = state["work"]
            self._ensure_schema(work)
            type_keys = {item["key"] for item in work["item_types"]} | {"*", "Requirement"}
            relationship_keys = {item["key"] for item in work["relationship_types"]}
            downstream = list(values["downstream_types"])
            if values["upstream_type"] not in type_keys or set(downstream) - type_keys:
                raise WorkError("Die Regel referenziert einen unbekannten Itemtyp")
            if values["relationship_type"] not in relationship_keys:
                raise WorkError("Die Regel referenziert einen unbekannten Beziehungstyp")
            rule = {
                "id": f"RULE-{len(work['relationship_rules']) + 1:03d}",
                "name": values["name"],
                "upstream_type": values["upstream_type"],
                "downstream_types": downstream,
                "relationship_type": values["relationship_type"],
                "min_downstream": int(values.get("min_downstream", 0)),
                "max_downstream": values.get("max_downstream"),
                "coverage": bool(values.get("coverage", True)),
                "exclusive": bool(values.get("exclusive", False)),
                "active": True,
                "created_by": actor,
            }
            work["relationship_rules"].append(rule)
            self._add_activity(work, actor, f"Relationship-Regel {rule['name']} angelegt")
            result.update(deepcopy(rule))

        self.store.mutate(create)
        return result

    def create_relationship(self, values: dict[str, Any], actor: str) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def create(state: dict[str, Any]) -> None:
            work = state["work"]
            self._ensure_schema(work)
            source = self._find_item(work, values["source_id"])
            target = self._find_item(work, values["target_id"])
            if source is None or target is None:
                raise WorkNotFoundError("Quell- oder Zielobjekt wurde nicht gefunden")
            if source[0] == target[0]:
                raise WorkError("Ein Objekt kann nicht mit sich selbst verknüpft werden")
            if any(
                item["source_id"] == source[0]
                and item["target_id"] == target[0]
                and item["relationship_type"] == values["relationship_type"]
                for item in work["relationships"]
            ):
                raise WorkError("Diese Beziehung existiert bereits")
            if not self._relationship_allowed(
                work, source[1], target[1], values["relationship_type"]
            ):
                raise WorkError("Die Beziehung ist im aktiven Relationship-Modell nicht erlaubt")
            relationship = {
                "id": f"REL-{len(work['relationships']) + 1:04d}",
                "source_id": source[0],
                "source_type": source[1],
                "target_id": target[0],
                "target_type": target[1],
                "relationship_type": values["relationship_type"],
                "description": values.get("description", ""),
                "suspect": False,
                "suspect_reason": None,
                "created_at": utc_now(),
                "created_by": actor,
            }
            work["relationships"].append(relationship)
            self._add_activity(
                work, actor, f"{source[0]} mit {target[0]} verknüpft"
            )
            result.update(deepcopy(relationship))

        self.store.mutate(create)
        return result

    def clear_suspect(self, relationship_id: str, actor: str) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def clear(state: dict[str, Any]) -> None:
            work = state["work"]
            self._ensure_schema(work)
            relationship = self._find(work["relationships"], relationship_id)
            relationship["suspect"] = False
            relationship["suspect_reason"] = None
            relationship["assessed_by"] = actor
            relationship["assessed_at"] = utc_now()
            self._add_activity(work, actor, f"Suspect Link {relationship_id} bewertet")
            result.update(deepcopy(relationship))

        self.store.mutate(clear)
        return result

    def create_review(self, values: dict[str, Any], actor: str) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def create(state: dict[str, Any]) -> None:
            work = state["work"]
            self._ensure_schema(work)
            item_ids = list(dict.fromkeys(values["item_ids"]))
            snapshots = []
            for item_id in item_ids:
                found = self._find_item(work, item_id)
                if found is None:
                    raise WorkNotFoundError(f"Review-Objekt {item_id} wurde nicht gefunden")
                snapshots.append(
                    {
                        "item_id": item_id,
                        "item_type": found[1],
                        "version": int(found[2].get("version", 1)),
                        "title": found[2].get("title", item_id),
                    }
                )
            participants = deepcopy(values["participants"])
            if not any(item.get("role") == "approver" for item in participants):
                raise WorkError("Ein Review benötigt mindestens einen Approver")
            review = {
                "id": f"REV-{len(work['reviews']) + 1:04d}",
                "title": values["title"],
                "description": values.get("description", ""),
                "status": "in_progress",
                "revision": 1,
                "moderator": actor,
                "deadline": values.get("deadline"),
                "require_signature": bool(values.get("require_signature", False)),
                "allow_comments_in_item": bool(
                    values.get("allow_comments_in_item", True)
                ),
                "items": snapshots,
                "participants": [
                    {
                        **item,
                        "decision": "pending",
                        "completed_at": None,
                        "signature": None,
                    }
                    for item in participants
                ],
                "comments": [],
                "created_at": utc_now(),
                "created_by": actor,
                "completed_at": None,
            }
            work["reviews"].append(review)
            self._add_activity(work, actor, f"Review {review['id']} gestartet")
            result.update(deepcopy(review))

        self.store.mutate(create)
        return result

    def add_review_comment(
        self, review_id: str, values: dict[str, Any], actor: str
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def add(state: dict[str, Any]) -> None:
            work = state["work"]
            self._ensure_schema(work)
            review = self._find(work["reviews"], review_id)
            if review["status"] not in {"in_progress", "changes_requested"}:
                raise WorkError("Der Review ist nicht mehr für Kommentare geöffnet")
            item_id = values.get("item_id")
            if item_id and item_id not in {item["item_id"] for item in review["items"]}:
                raise WorkError("Das kommentierte Objekt gehört nicht zum Review")
            comment = {
                "id": f"CMT-{len(review['comments']) + 1:04d}",
                "item_id": item_id,
                "author": actor,
                "text": values["text"],
                "status": "open",
                "created_at": utc_now(),
                "mentions": re.findall(r"@([\w.\-]+)", values["text"]),
            }
            review["comments"].append(comment)
            self._add_activity(work, actor, f"Kommentar in {review_id} ergänzt")
            result.update(deepcopy(comment))

        self.store.mutate(add)
        return result

    def review_decision(
        self, review_id: str, values: dict[str, Any], actor: str
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def decide(state: dict[str, Any]) -> None:
            work = state["work"]
            self._ensure_schema(work)
            review = self._find(work["reviews"], review_id)
            participant_name = values.get("participant") or actor
            if actor != "Demo Benutzer" and str(participant_name).casefold() != actor.casefold():
                raise WorkError("Review-Entscheidungen dürfen nur für die eigene Person erfolgen")
            participant = next(
                (
                    item
                    for item in review["participants"]
                    if str(item.get("name", "")).casefold()
                    == str(participant_name).casefold()
                ),
                None,
            )
            if participant is None:
                raise WorkError("Die Person ist nicht als Review-Teilnehmer eingeladen")
            decision = values["decision"]
            if decision == "approved" and participant["role"] != "approver":
                raise WorkError("Nur Approver können eine Freigabe erteilen")
            if review.get("require_signature") and decision == "approved" and not values.get(
                "signature"
            ):
                raise WorkError("Für diese Freigabe ist eine elektronische Signatur erforderlich")
            participant.update(
                {
                    "decision": decision,
                    "completed_at": utc_now(),
                    "signature": values.get("signature"),
                    "note": values.get("note", ""),
                }
            )
            approvers = [item for item in review["participants"] if item["role"] == "approver"]
            if decision in {"rejected", "changes_requested"}:
                review["status"] = "changes_requested"
            elif all(item["decision"] == "approved" for item in approvers):
                review["status"] = "approved"
                review["completed_at"] = utc_now()
                reviewed_ids = {item["item_id"] for item in review["items"]}
                for requirement in work["requirements"]:
                    if requirement["id"] in reviewed_ids and requirement["status"] in {
                        "draft",
                        "review",
                    }:
                        requirement["status"] = "approved"
            else:
                review["status"] = "in_progress"
            self._add_activity(
                work, actor, f"{participant_name}: {decision} in {review_id}"
            )
            result.update(deepcopy(review))

        self.store.mutate(decide)
        return result

    def create_test_case(self, values: dict[str, Any], actor: str) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def create(state: dict[str, Any]) -> None:
            work = state["work"]
            self._ensure_schema(work)
            test_case = {
                "id": f"TC-{len(work['test_cases']) + 1:04d}",
                "title": values["title"],
                "type": "TestCase",
                "status": values.get("status", "draft"),
                "owner": values["owner"],
                "preconditions": values.get("preconditions", ""),
                "steps": deepcopy(values["steps"]),
                "expected_result": values["expected_result"],
                "version": 1,
                "created_at": utc_now(),
                "created_by": actor,
            }
            work["test_cases"].append(test_case)
            for requirement_id in values.get("requirement_ids", []):
                self._append_relationship(
                    work,
                    requirement_id,
                    test_case["id"],
                    "verifies",
                    actor,
                )
            self._add_activity(work, actor, f"Testfall {test_case['id']} angelegt")
            result.update(deepcopy(test_case))

        self.store.mutate(create)
        return result

    def create_test_plan(self, values: dict[str, Any], actor: str) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def create(state: dict[str, Any]) -> None:
            work = state["work"]
            self._ensure_schema(work)
            known = {item["id"] for item in work["test_cases"]}
            if set(values["test_case_ids"]) - known:
                raise WorkNotFoundError("Mindestens ein Testfall wurde nicht gefunden")
            plan = {
                "id": f"TP-{len(work['test_plans']) + 1:04d}",
                "name": values["name"],
                "description": values.get("description", ""),
                "test_case_ids": list(values["test_case_ids"]),
                "owner": values["owner"],
                "status": "active",
                "created_at": utc_now(),
            }
            work["test_plans"].append(plan)
            run = {
                "id": f"RUN-{len(work['test_runs']) + 1:04d}",
                "plan_id": plan["id"],
                "name": f"{plan['name']} · Lauf 1",
                "status": "not_started",
                "executions": [
                    {
                        "test_case_id": item_id,
                        "result": "not_run",
                        "executed_by": None,
                        "executed_at": None,
                        "evidence": None,
                        "defect_issue_id": None,
                    }
                    for item_id in plan["test_case_ids"]
                ],
            }
            work["test_runs"].append(run)
            self._add_activity(work, actor, f"Testplan {plan['id']} angelegt")
            result.update({**deepcopy(plan), "run_id": run["id"]})

        self.store.mutate(create)
        return result

    def execute_test(
        self, run_id: str, test_case_id: str, values: dict[str, Any], actor: str
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def execute(state: dict[str, Any]) -> None:
            work = state["work"]
            self._ensure_schema(work)
            run = self._find(work["test_runs"], run_id)
            execution = next(
                (item for item in run["executions"] if item["test_case_id"] == test_case_id),
                None,
            )
            if execution is None:
                raise WorkNotFoundError("Der Testfall gehört nicht zu diesem Testlauf")
            execution.update(
                {
                    "result": values["result"],
                    "executed_by": actor,
                    "executed_at": utc_now(),
                    "evidence": values.get("evidence"),
                    "defect_issue_id": values.get("defect_issue_id"),
                    "note": values.get("note", ""),
                }
            )
            results = {item["result"] for item in run["executions"]}
            run["status"] = "completed" if "not_run" not in results else "in_progress"
            run["outcome"] = "failed" if "failed" in results else (
                "passed" if results == {"passed"} else "open"
            )
            self._add_activity(work, actor, f"{test_case_id}: {values['result']}")
            result.update(deepcopy(execution))

        self.store.mutate(execute)
        return result

    def create_risk(self, values: dict[str, Any], actor: str) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def create(state: dict[str, Any]) -> None:
            work = state["work"]
            self._ensure_schema(work)
            risk = {
                "id": f"RISK-{len(work['risks']) + 1:04d}",
                "title": values["title"],
                "type": "Risk",
                "description": values.get("description", ""),
                "probability": int(values["probability"]),
                "impact": int(values["impact"]),
                "rating": int(values["probability"]) * int(values["impact"]),
                "mitigation": values["mitigation"],
                "owner": values["owner"],
                "status": values.get("status", "open"),
                "version": 1,
                "created_at": utc_now(),
            }
            work["risks"].append(risk)
            for requirement_id in values.get("requirement_ids", []):
                self._append_relationship(
                    work, risk["id"], requirement_id, "mitigates", actor
                )
            self._add_activity(work, actor, f"Risiko {risk['id']} angelegt")
            result.update(deepcopy(risk))

        self.store.mutate(create)
        return result

    def branch_requirement(
        self, requirement_id: str, values: dict[str, Any], actor: str
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def branch(state: dict[str, Any]) -> None:
            work = state["work"]
            self._ensure_schema(work)
            source = self._find(work["requirements"], requirement_id)
            next_number = max(
                (int(item["id"].rsplit("-", 1)[-1]) for item in work["requirements"]),
                default=0,
            ) + 1
            cloned = deepcopy(source)
            cloned.update(
                {
                    "id": f"REQ-SCU-{next_number:03d}",
                    "title": values.get("title") or f"{source['title']} ({values['variant']})",
                    "variant": values["variant"],
                    "source_id": requirement_id,
                    "status": "draft",
                    "version": 1,
                    "created_at": utc_now(),
                    "updated_at": utc_now(),
                    "history": [
                        {
                            "version": 1,
                            "actor": actor,
                            "at": utc_now(),
                            "note": f"Aus {requirement_id} abgeleitet",
                        }
                    ],
                }
            )
            work["requirements"].append(cloned)
            work["variants"].append(
                {
                    "id": f"VAR-{len(work['variants']) + 1:03d}",
                    "name": values["variant"],
                    "source_id": requirement_id,
                    "branched_id": cloned["id"],
                    "created_at": utc_now(),
                }
            )
            self._add_activity(work, actor, f"Variante {cloned['id']} abgeleitet")
            result.update(deepcopy(cloned))

        self.store.mutate(branch)
        return result

    def compare_baseline(self, baseline_id: str) -> dict[str, Any]:
        work = deepcopy(self._work())
        self._ensure_schema(work)
        baseline = self._find(work["baselines"], baseline_id)
        current = {item["id"]: item for item in work["requirements"]}
        rows = []
        for snapshot in baseline["items"]:
            item = current.get(snapshot["requirement_id"])
            rows.append(
                {
                    **snapshot,
                    "current_version": item.get("version") if item else None,
                    "current_status": item.get("status") if item else "deleted",
                    "changed": not item
                    or int(item.get("version", 0)) != int(snapshot["version"]),
                }
            )
        baseline_ids = {item["requirement_id"] for item in baseline["items"]}
        added = [item["id"] for item in work["requirements"] if item["id"] not in baseline_ids]
        return {"baseline": baseline, "comparison": rows, "added": added}

    def export_package(self) -> dict[str, Any]:
        work = deepcopy(self._work())
        self._ensure_schema(work)
        return {
            "schema": "flowwork-interchange-1.0",
            "exported_at": utc_now(),
            "item_types": work["item_types"],
            "field_definitions": work["field_definitions"],
            "relationship_types": work["relationship_types"],
            "relationship_rules": work["relationship_rules"],
            "requirements": work["requirements"],
            "relationships": work["relationships"],
            "test_cases": work["test_cases"],
            "risks": work["risks"],
            "baselines": work["baselines"],
        }

    def import_package(self, values: dict[str, Any], actor: str) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def import_data(state: dict[str, Any]) -> None:
            work = state["work"]
            self._ensure_schema(work)
            counts: dict[str, int] = {}
            supported = (
                "item_types",
                "field_definitions",
                "relationship_types",
                "relationship_rules",
                "requirements",
                "relationships",
                "test_cases",
                "risks",
                "baselines",
            )
            for collection in supported:
                existing = {item.get("id") for item in work[collection]}
                incoming = [
                    deepcopy(item)
                    for item in values.get(collection, [])
                    if item.get("id") not in existing
                ]
                work[collection].extend(incoming)
                counts[collection] = len(incoming)
            self._add_activity(work, actor, "Requirements-Paket importiert")
            result.update({"status": "imported", "counts": counts})

        self.store.mutate(import_data)
        return result

    def reset(self) -> dict[str, Any]:
        return self.store.reset_domain("work")["work"]

    def _work(self) -> dict[str, Any]:
        state = self.store.get()
        work = state.get("work")
        if not isinstance(work, dict):
            raise WorkError("FLOWWORK-Domäne fehlt im Szenariodatensatz")
        return work

    @staticmethod
    def _ensure_schema(work: dict[str, Any]) -> None:
        defaults: dict[str, list[dict[str, Any]]] = {
            "item_types": [
                {"id": "TYPE-001", "key": "Stakeholder", "name": "Stakeholder-Anforderung", "prefix": "STK", "field_keys": ["SOURCE"], "workflow": ["draft", "review", "approved", "verified", "rejected"]},
                {"id": "TYPE-002", "key": "System", "name": "Systemanforderung", "prefix": "SYS", "field_keys": ["RELEASE"], "workflow": ["draft", "review", "approved", "verified", "rejected"]},
                {"id": "TYPE-003", "key": "Software", "name": "Softwareanforderung", "prefix": "SWR", "field_keys": ["RELEASE", "ESTIMATE"], "workflow": ["draft", "review", "approved", "verified", "rejected"]},
                {"id": "TYPE-004", "key": "Hardware", "name": "Hardwareanforderung", "prefix": "HWR", "field_keys": ["RELEASE"], "workflow": ["draft", "review", "approved", "verified", "rejected"]},
                {"id": "TYPE-005", "key": "Interface", "name": "Schnittstellenanforderung", "prefix": "IF", "field_keys": ["INTERFACE_PROTOCOL"], "workflow": ["draft", "review", "approved", "verified", "rejected"]},
                {"id": "TYPE-006", "key": "Safety", "name": "Safety-Anforderung", "prefix": "SAFE", "field_keys": ["SAFETY_LEVEL"], "workflow": ["draft", "review", "approved", "verified", "rejected"]},
                {"id": "TYPE-007", "key": "TestCase", "name": "Testfall", "prefix": "TC", "field_keys": [], "workflow": ["draft", "approved", "retired"]},
                {"id": "TYPE-008", "key": "Risk", "name": "Risiko", "prefix": "RISK", "field_keys": [], "workflow": ["open", "mitigated", "accepted", "closed"]},
            ],
            "field_definitions": [
                {"id": "FLD-001", "key": "SOURCE", "name": "Quelle", "field_type": "text", "required": False, "options": [], "applies_to": ["Stakeholder"]},
                {"id": "FLD-002", "key": "RELEASE", "name": "Zielrelease", "field_type": "select", "required": False, "options": ["SCU 1.0", "SCU 1.1", "SCU Next"], "applies_to": ["System", "Software", "Hardware"]},
                {"id": "FLD-003", "key": "ESTIMATE", "name": "Aufwand (h)", "field_type": "integer", "required": False, "options": [], "applies_to": ["Software"]},
                {"id": "FLD-004", "key": "INTERFACE_PROTOCOL", "name": "Protokoll", "field_type": "select", "required": False, "options": ["CAN", "Ethernet", "OPC UA", "REST"], "applies_to": ["Interface"]},
                {"id": "FLD-005", "key": "SAFETY_LEVEL", "name": "Safety Level", "field_type": "select", "required": True, "options": ["QM", "SIL 1", "SIL 2", "SIL 3"], "applies_to": ["Safety"]},
            ],
            "relationship_types": [
                {"id": "RT-001", "key": "derives", "name": "leitet ab", "reverse_name": "wird abgeleitet aus"},
                {"id": "RT-002", "key": "implements", "name": "implementiert", "reverse_name": "wird implementiert durch"},
                {"id": "RT-003", "key": "verifies", "name": "wird verifiziert durch", "reverse_name": "verifiziert"},
                {"id": "RT-004", "key": "mitigates", "name": "wird mitigiert durch", "reverse_name": "mitigiert"},
                {"id": "RT-005", "key": "references", "name": "referenziert", "reverse_name": "wird referenziert von"},
            ],
            "relationship_rules": [
                {"id": "RULE-001", "name": "Stakeholder zu System", "upstream_type": "Stakeholder", "downstream_types": ["System"], "relationship_type": "derives", "min_downstream": 1, "max_downstream": None, "coverage": True, "exclusive": False, "active": True},
                {"id": "RULE-002", "name": "Systemzerlegung", "upstream_type": "System", "downstream_types": ["Software", "Hardware", "Interface", "Safety"], "relationship_type": "derives", "min_downstream": 1, "max_downstream": None, "coverage": True, "exclusive": False, "active": True},
                {"id": "RULE-003", "name": "Anforderung zu Testfall", "upstream_type": "Requirement", "downstream_types": ["TestCase"], "relationship_type": "verifies", "min_downstream": 1, "max_downstream": None, "coverage": True, "exclusive": False, "active": True},
                {"id": "RULE-004", "name": "Risiko zu Anforderung", "upstream_type": "Risk", "downstream_types": ["Stakeholder", "System", "Software", "Hardware", "Interface", "Safety"], "relationship_type": "mitigates", "min_downstream": 1, "max_downstream": None, "coverage": False, "exclusive": False, "active": True},
                {"id": "RULE-005", "name": "Freie Referenz", "upstream_type": "*", "downstream_types": ["*"], "relationship_type": "references", "min_downstream": 0, "max_downstream": None, "coverage": False, "exclusive": False, "active": True},
            ],
            "relationships": [],
            "reviews": [],
            "test_cases": [],
            "test_plans": [],
            "test_runs": [],
            "risks": [],
            "catalogs": [],
            "variants": [],
        }
        for key, value in defaults.items():
            work.setdefault(key, deepcopy(value))

    def _validate_item_values(
        self, work: dict[str, Any], values: dict[str, Any], *, creating: bool
    ) -> None:
        item_type = str(values.get("type", ""))
        definition = next(
            (item for item in work["item_types"] if item["key"] == item_type), None
        )
        if definition is None:
            raise WorkError(f"Der Itemtyp {item_type} ist nicht konfiguriert")
        custom = values.get("custom_fields") or {}
        if not isinstance(custom, dict):
            raise WorkError("Eigene Felder müssen als Objekt übergeben werden")
        field_map = {item["key"]: item for item in work["field_definitions"]}
        allowed = set(definition.get("field_keys", []))
        if set(custom) - allowed:
            raise WorkError("Mindestens ein eigenes Feld ist für diesen Itemtyp nicht erlaubt")
        for key in allowed:
            field = field_map.get(key)
            if not field:
                continue
            value = custom.get(key)
            if creating and field.get("required") and value in (None, "", []):
                raise WorkError(f"Das Pflichtfeld {field['name']} fehlt")
            if value in (None, "", []):
                continue
            if field["field_type"] == "integer" and (
                isinstance(value, bool) or not isinstance(value, int)
            ):
                raise WorkError(f"{field['name']} muss eine Ganzzahl sein")
            if field["field_type"] == "flag" and not isinstance(value, bool):
                raise WorkError(f"{field['name']} muss wahr oder falsch sein")
            if field["field_type"] == "select" and value not in field.get("options", []):
                raise WorkError(f"{value} ist keine gültige Option für {field['name']}")
            if field["field_type"] == "multi_select" and (
                not isinstance(value, list)
                or set(value) - set(field.get("options", []))
            ):
                raise WorkError(f"Mindestens eine Auswahl für {field['name']} ist ungültig")

    @classmethod
    def _find_item(
        cls, work: dict[str, Any], item_id: str
    ) -> tuple[str, str, dict[str, Any]] | None:
        for collection in ("requirements", "test_cases", "risks"):
            item = next((row for row in work[collection] if row.get("id") == item_id), None)
            if item is not None:
                return item_id, str(item.get("type") or collection), item
        return None

    @staticmethod
    def _find(items: list[dict[str, Any]], item_id: str) -> dict[str, Any]:
        item = next((row for row in items if row.get("id") == item_id), None)
        if item is None:
            raise WorkNotFoundError(f"{item_id} wurde nicht gefunden")
        return item

    @staticmethod
    def _relationship_allowed(
        work: dict[str, Any], source_type: str, target_type: str, relationship_type: str
    ) -> bool:
        requirement_types = {
            item["key"]
            for item in work["item_types"]
            if item["key"] not in {"TestCase", "Risk"}
        }
        return any(
            rule.get("active", True)
            and rule["relationship_type"] == relationship_type
            and (
                rule["upstream_type"] in {"*", source_type}
                or (
                    rule["upstream_type"] == "Requirement"
                    and source_type in requirement_types
                )
            )
            and ("*" in rule["downstream_types"] or target_type in rule["downstream_types"])
            for rule in work["relationship_rules"]
        )

    @classmethod
    def _append_relationship(
        cls,
        work: dict[str, Any],
        source_id: str,
        target_id: str,
        relationship_type: str,
        actor: str,
    ) -> None:
        source = cls._find_item(work, source_id)
        target = cls._find_item(work, target_id)
        if source is None or target is None:
            raise WorkNotFoundError("Quell- oder Zielobjekt wurde nicht gefunden")
        if not cls._relationship_allowed(work, source[1], target[1], relationship_type):
            raise WorkError("Die Beziehung ist im aktiven Relationship-Modell nicht erlaubt")
        if any(
            item["source_id"] == source_id
            and item["target_id"] == target_id
            and item["relationship_type"] == relationship_type
            for item in work["relationships"]
        ):
            return
        work["relationships"].append(
            {
                "id": f"REL-{len(work['relationships']) + 1:04d}",
                "source_id": source_id,
                "source_type": source[1],
                "target_id": target_id,
                "target_type": target[1],
                "relationship_type": relationship_type,
                "description": "",
                "suspect": False,
                "suspect_reason": None,
                "created_at": utc_now(),
                "created_by": actor,
            }
        )

    @staticmethod
    def _mark_suspect_links(
        work: dict[str, Any], source_id: str, actor: str, fields: list[str]
    ) -> None:
        ignored = {"status", "issue_id", "wiki_title", "verification"}
        relevant = [field for field in fields if field not in ignored]
        if not relevant:
            return
        for relationship in work["relationships"]:
            if relationship["source_id"] == source_id:
                relationship["suspect"] = True
                relationship["suspect_reason"] = (
                    f"{source_id} wurde von {actor} geändert: {', '.join(relevant)}"
                )
                relationship["suspect_at"] = utc_now()

    @classmethod
    def _relationship_coverage(cls, work: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        all_items = [
            item
            for collection in ("requirements", "test_cases", "risks")
            for item in work[collection]
        ]
        for item in all_items:
            item_type = str(item.get("type") or "")
            requirement_types = {
                definition["key"]
                for definition in work["item_types"]
                if definition["key"] not in {"TestCase", "Risk"}
            }
            for rule in work["relationship_rules"]:
                if not rule.get("active", True) or not rule.get("coverage"):
                    continue
                if rule["upstream_type"] not in {"*", item_type} and not (
                    rule["upstream_type"] == "Requirement"
                    and item_type in requirement_types
                ):
                    continue
                matching = [
                    relation
                    for relation in work["relationships"]
                    if relation["source_id"] == item["id"]
                    and relation["relationship_type"] == rule["relationship_type"]
                    and (
                        "*" in rule["downstream_types"]
                        or relation["target_type"] in rule["downstream_types"]
                    )
                ]
                minimum = int(rule.get("min_downstream", 0))
                maximum = rule.get("max_downstream")
                compliant = len(matching) >= minimum and (
                    maximum is None or len(matching) <= int(maximum)
                )
                rows.append(
                    {
                        "item_id": item["id"],
                        "item_type": item_type,
                        "rule_id": rule["id"],
                        "rule": rule["name"],
                        "actual": len(matching),
                        "required": minimum,
                        "compliant": compliant,
                        "suspect": any(link.get("suspect") for link in matching),
                    }
                )
        return rows

    @staticmethod
    def _test_pass_rate(work: dict[str, Any]) -> int:
        executed = [
            execution
            for run in work["test_runs"]
            for execution in run.get("executions", [])
            if execution.get("result") not in {None, "not_run", "blocked"}
        ]
        return (
            round(
                len([item for item in executed if item["result"] == "passed"])
                / len(executed)
                * 100
            )
            if executed
            else 0
        )

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", str(value)).strip("-").lower()
        if not slug:
            raise WorkError("Ein technischer Schlüssel konnte nicht gebildet werden")
        return slug

    @staticmethod
    def _status_bucket(status: str) -> str:
        value = status.casefold()
        if any(token in value for token in ("erledigt", "closed", "geschlossen", "done")):
            return "done"
        if any(token in value for token in ("prüfung", "review", "feedback")):
            return "review"
        if any(token in value for token in ("bearbeitung", "progress", "umsetzung")):
            return "progress"
        return "backlog"

    @staticmethod
    def _trace_row(
        requirement: dict[str, Any], tasks: list[dict[str, Any]], wiki: list[dict[str, Any]]
    ) -> dict[str, Any]:
        issue_ref = str(requirement.get("issue_id") or "")
        issue = next(
            (
                task
                for task in tasks
                if str(task.get("key")) == issue_ref
                or str(task.get("id")) == issue_ref.removeprefix("#")
            ),
            None,
        )
        wiki_title = str(requirement.get("wiki_title") or "")
        wiki_page = next((page for page in wiki if page.get("title") == wiki_title), None)
        return {
            "requirement_id": requirement["id"],
            "requirement": requirement["title"],
            "status": requirement["status"],
            "parent_id": requirement.get("parent_id"),
            "issue": issue or ({"key": issue_ref} if issue_ref else None),
            "wiki": wiki_page or ({"title": wiki_title} if wiki_title else None),
            "verification": requirement.get("verification"),
            "complete": bool(issue_ref and wiki_title and requirement.get("verification")),
        }

    @staticmethod
    def _add_activity(work: dict[str, Any], actor: str, message: str) -> None:
        work.setdefault("activity", []).insert(
            0, {"actor": actor, "message": message, "at": utc_now()}
        )
        work["activity"] = work["activity"][:50]
