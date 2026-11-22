from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from .config import Settings
from .integrations import integration_status, paperless_search
from .store import ScenarioStore, utc_now


class MesError(RuntimeError):
    """A conflict or validation error suitable for an MES API response."""


class MesNotFoundError(MesError):
    """The requested MES object does not exist."""


class MesService:
    def __init__(self, store: ScenarioStore, settings: Settings) -> None:
        self.store = store
        self.settings = settings

    def dashboard(self, operator_id: str | None = None) -> dict[str, Any]:
        state = self.store.get()
        mes = state.get("mes")
        if not mes:
            raise MesError("MES-Demodaten sind nicht initialisiert")
        self._validate_operator(mes, operator_id)
        return self._view(mes, operator_id)

    def reset(self, operator_id: str | None = None) -> dict[str, Any]:
        state = self.store.reset_domain("mes")
        self._validate_operator(state["mes"], operator_id)
        return self._view(state["mes"], operator_id)

    def job(self, job_id: str) -> dict[str, Any]:
        state = self.store.get()
        mes = state.get("mes") or {}
        job = self._find_job(mes, job_id)
        return self._job_view(mes, job)

    def start(self, job_id: str, operator_id: str) -> dict[str, Any]:
        def operation(state: dict[str, Any]) -> None:
            mes = self._mes(state)
            operator = self._validate_operator(mes, operator_id)
            job = self._find_job(mes, job_id)
            if job["status"] not in {"ready", "paused"}:
                raise MesError("Nur bereite oder pausierte Arbeitsgänge können gestartet werden")
            running = next(
                (
                    candidate
                    for candidate in mes["jobs"]
                    if candidate["status"] == "in_progress"
                    and candidate.get("active_operator") == operator_id
                    and candidate["id"] != job_id
                ),
                None,
            )
            if running:
                raise MesError(f"{operator['name']} bearbeitet bereits {running['id']}")
            if job.get("assigned_operator") and job["assigned_operator"] != operator_id:
                raise MesError("Der Arbeitsgang ist einer anderen Person zugeordnet")
            job["status"] = "in_progress"
            job["active_operator"] = operator_id
            job.setdefault("time_logs", []).append(
                {
                    "operator_id": operator_id,
                    "operator_name": operator["name"],
                    "activity": "Fertigungszeit",
                    "started_at": utc_now(),
                    "ended_at": None,
                    "minutes": None,
                    "source": "terminal",
                    "note": "Arbeitsgang gestartet",
                }
            )
            self._event(mes, job, f"{operator['name']} hat den Arbeitsgang gestartet")

        state = self.store.mutate(operation)
        return self._job_view(state["mes"], self._find_job(state["mes"], job_id))

    def pause(self, job_id: str, operator_id: str, reason: str, note: str = "") -> dict[str, Any]:
        def operation(state: dict[str, Any]) -> None:
            mes = self._mes(state)
            self._validate_operator(mes, operator_id)
            job = self._find_job(mes, job_id)
            if job["status"] != "in_progress":
                raise MesError("Nur ein laufender Arbeitsgang kann pausiert werden")
            if job.get("active_operator") != operator_id:
                raise MesError("Nur die aktive Bedienperson kann den Arbeitsgang pausieren")
            self._close_open_log(job)
            job["status"] = "paused"
            job["pause_reason"] = reason.strip()
            job["note"] = note.strip()
            job["active_operator"] = None
            self._event(mes, job, f"Arbeitsgang pausiert: {reason.strip()}", "warning")

        if not reason.strip():
            raise MesError("Ein Pausengrund ist erforderlich")
        state = self.store.mutate(operation)
        return self._job_view(state["mes"], self._find_job(state["mes"], job_id))

    def book_time(
        self,
        job_id: str,
        operator_id: str,
        minutes: int,
        activity: str,
        note: str = "",
    ) -> dict[str, Any]:
        def operation(state: dict[str, Any]) -> None:
            mes = self._mes(state)
            operator = self._validate_operator(mes, operator_id)
            job = self._find_job(mes, job_id)
            if job["status"] == "completed":
                raise MesError("Auf abgeschlossene Arbeitsgänge kann keine Zeit gebucht werden")
            ended = datetime.now(UTC).replace(microsecond=0)
            started = ended - timedelta(minutes=minutes)
            job.setdefault("time_logs", []).append(
                {
                    "operator_id": operator_id,
                    "operator_name": operator["name"],
                    "activity": activity,
                    "started_at": started.isoformat(),
                    "ended_at": ended.isoformat(),
                    "minutes": minutes,
                    "source": "manual",
                    "note": note.strip(),
                }
            )
            self._event(mes, job, f"{minutes} Minuten {activity} nachgebucht")

        if minutes < 1 or minutes > 720:
            raise MesError("Die Zeitbuchung muss zwischen 1 und 720 Minuten liegen")
        state = self.store.mutate(operation)
        return self._job_view(state["mes"], self._find_job(state["mes"], job_id))

    def complete(
        self,
        job_id: str,
        operator_id: str,
        completed_qty: int,
        scrap_qty: int,
        serial_numbers: list[str],
        checklist: list[str],
        note: str = "",
    ) -> dict[str, Any]:
        def operation(state: dict[str, Any]) -> None:
            mes = self._mes(state)
            self._validate_operator(mes, operator_id)
            job = self._find_job(mes, job_id)
            if job["status"] != "in_progress":
                raise MesError("Der Arbeitsgang muss vor dem Abschluss gestartet werden")
            if job.get("active_operator") != operator_id:
                raise MesError("Nur die aktive Bedienperson kann den Arbeitsgang abschließen")
            required = {item["id"] for item in job.get("checklist", []) if item.get("required")}
            missing = required - set(checklist)
            if missing:
                raise MesError("Alle Pflichtprüfungen müssen bestätigt werden")
            remaining = job["target_qty"] - job.get("completed_qty", 0)
            if completed_qty < 1 or completed_qty > remaining:
                raise MesError(f"Die Gutmenge muss zwischen 1 und {remaining} liegen")
            if scrap_qty < 0:
                raise MesError("Die Ausschussmenge darf nicht negativ sein")
            serials = [value.strip().upper() for value in serial_numbers if value.strip()]
            if job.get("serial_tracking") and len(set(serials)) != completed_qty:
                raise MesError(
                    "Für jedes Gutteil ist genau eine eindeutige Seriennummer erforderlich"
                )
            already_used = set(job.get("serial_numbers", []))
            if already_used.intersection(serials):
                raise MesError("Eine Seriennummer wurde in diesem Arbeitsgang bereits verwendet")
            self._close_open_log(job)
            job["completed_qty"] = job.get("completed_qty", 0) + completed_qty
            job["scrap_qty"] = job.get("scrap_qty", 0) + scrap_qty
            job.setdefault("serial_numbers", []).extend(serials)
            job["checklist_completed"] = sorted(set(checklist))
            job["note"] = note.strip()
            job["active_operator"] = None
            fully_completed = job["completed_qty"] >= job["target_qty"]
            job["status"] = "completed" if fully_completed else "ready"
            message = f"{completed_qty} Gutteil(e) und {scrap_qty} Ausschussteil(e) zurückgemeldet"
            self._event(mes, job, message)
            if fully_completed:
                self._release_successors(mes, job_id)

        state = self.store.mutate(operation)
        return self._job_view(state["mes"], self._find_job(state["mes"], job_id))

    def report_issue(
        self, job_id: str, operator_id: str, category: str, description: str
    ) -> dict[str, Any]:
        def operation(state: dict[str, Any]) -> None:
            mes = self._mes(state)
            operator = self._validate_operator(mes, operator_id)
            job = self._find_job(mes, job_id)
            if job["status"] == "completed":
                raise MesError("Für abgeschlossene Arbeitsgänge kann keine Störung eröffnet werden")
            if job["status"] == "in_progress":
                self._close_open_log(job)
            sequence = 1 + sum(bool(candidate.get("issue")) for candidate in mes["jobs"])
            issue_id = f"NCR-MES-{sequence:04d}"
            job["issue"] = {
                "id": issue_id,
                "category": category,
                "description": description.strip(),
                "status": "open",
                "reported_by": operator["name"],
                "reported_at": utc_now(),
            }
            job["status"] = "blocked"
            job["active_operator"] = None
            self._event(mes, job, f"{issue_id} eröffnet: {category}", "critical")

        if not description.strip():
            raise MesError("Eine Störungsbeschreibung ist erforderlich")
        state = self.store.mutate(operation)
        return self._job_view(state["mes"], self._find_job(state["mes"], job_id))

    def resolve_issue(self, job_id: str, operator_id: str, resolution: str) -> dict[str, Any]:
        def operation(state: dict[str, Any]) -> None:
            mes = self._mes(state)
            operator = self._validate_operator(mes, operator_id)
            job = self._find_job(mes, job_id)
            issue = job.get("issue")
            if not issue or issue.get("status") != "open":
                raise MesError("Der Arbeitsgang hat keine offene Störung")
            issue["status"] = "resolved"
            issue["resolution"] = resolution.strip()
            issue["resolved_by"] = operator["name"]
            issue["resolved_at"] = utc_now()
            job["status"] = "ready"
            self._event(mes, job, f"{issue['id']} behoben; Arbeitsgang wieder freigegeben")

        if not resolution.strip():
            raise MesError("Eine Lösungsbeschreibung ist erforderlich")
        state = self.store.mutate(operation)
        return self._job_view(state["mes"], self._find_job(state["mes"], job_id))

    def documents(self, job_id: str) -> dict[str, Any]:
        state = self.store.get()
        mes = self._mes(state)
        job = self._find_job(mes, job_id)
        linked = self._linked_documents(state, job)
        dms_search = paperless_search(job["item_code"], self.settings)
        paperless_status = next(
            (
                item
                for item in integration_status(self.settings)
                if item["name"] == "Paperless-ngx"
            ),
            None,
        )
        return {
            "job_id": job_id,
            "item_code": job["item_code"],
            "linked_documents": linked,
            "dms_search": dms_search,
            "integration": paperless_status,
            "source": {"system": "Paperless-ngx", "reference": job["item_code"]},
        }

    def _view(self, mes: dict[str, Any], operator_id: str | None) -> dict[str, Any]:
        jobs = [self._job_view(mes, job) for job in mes["jobs"]]
        if operator_id:
            own = [job for job in jobs if job.get("assigned_operator") == operator_id]
        else:
            own = jobs
        actionable = [job for job in own if job["status"] in {"in_progress", "ready", "paused", "blocked"}]
        actionable.sort(key=self._job_sort_key)
        return {
            "site": mes["site"],
            "area": mes["area"],
            "shift": mes["shift"],
            "server_time": utc_now(),
            "operators": mes["operators"],
            "jobs": jobs,
            "my_jobs": own,
            "next_job": actionable[0] if actionable else None,
            "metrics": self._metrics(jobs),
            "events": mes.get("events", [])[:12],
            "status_labels": {
                "ready": "Bereit",
                "in_progress": "In Arbeit",
                "paused": "Pausiert",
                "waiting": "Wartet",
                "blocked": "Gesperrt",
                "completed": "Abgeschlossen",
            },
        }

    def _job_view(self, mes: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
        result = deepcopy(job)
        result["booked_minutes"] = sum(self._log_minutes(log) for log in job.get("time_logs", []))
        result["remaining_qty"] = max(0, job["target_qty"] - job.get("completed_qty", 0))
        result["progress_percent"] = round(
            100 * job.get("completed_qty", 0) / max(1, job["target_qty"])
        )
        result["route"] = [
            {
                "id": candidate["id"],
                "sequence": candidate["sequence"],
                "operation": candidate["operation"],
                "workstation": candidate["workstation"],
                "status": candidate["status"],
            }
            for candidate in sorted(mes["jobs"], key=lambda row: row["sequence"])
            if candidate["work_order"] == job["work_order"]
        ]
        result["operator"] = next(
            (
                operator
                for operator in mes["operators"]
                if operator["id"] == job.get("assigned_operator")
            ),
            None,
        )
        return result

    @staticmethod
    def _metrics(jobs: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "total": len(jobs),
            "ready": sum(job["status"] == "ready" for job in jobs),
            "running": sum(job["status"] == "in_progress" for job in jobs),
            "blocked": sum(job["status"] == "blocked" for job in jobs),
            "completed": sum(job["status"] == "completed" for job in jobs),
            "booked_minutes": sum(int(job["booked_minutes"]) for job in jobs),
            "good_quantity": sum(int(job.get("completed_qty", 0)) for job in jobs),
            "scrap_quantity": sum(int(job.get("scrap_qty", 0)) for job in jobs),
        }

    @staticmethod
    def _job_sort_key(job: dict[str, Any]) -> tuple[int, int]:
        order = {"in_progress": 0, "blocked": 1, "paused": 2, "ready": 3, "waiting": 4, "completed": 5}
        return order.get(job["status"], 9), int(job["sequence"])

    @staticmethod
    def _mes(state: dict[str, Any]) -> dict[str, Any]:
        mes = state.get("mes")
        if not mes:
            raise MesError("MES-Demodaten sind nicht initialisiert")
        return mes

    @staticmethod
    def _find_job(mes: dict[str, Any], job_id: str) -> dict[str, Any]:
        job = next((item for item in mes.get("jobs", []) if item["id"] == job_id), None)
        if not job:
            raise MesNotFoundError(f"Arbeitsgang {job_id} wurde nicht gefunden")
        return job

    @staticmethod
    def _validate_operator(mes: dict[str, Any], operator_id: str | None) -> dict[str, Any] | None:
        if operator_id is None:
            return None
        operator = next(
            (item for item in mes.get("operators", []) if item["id"] == operator_id), None
        )
        if not operator:
            raise MesNotFoundError(f"Bedienperson {operator_id} wurde nicht gefunden")
        return operator

    @staticmethod
    def _close_open_log(job: dict[str, Any]) -> None:
        log = next(
            (item for item in reversed(job.get("time_logs", [])) if not item.get("ended_at")),
            None,
        )
        if not log:
            raise MesError("Für den laufenden Arbeitsgang wurde keine offene Zeit gefunden")
        ended = datetime.now(UTC).replace(microsecond=0)
        started = datetime.fromisoformat(log["started_at"].replace("Z", "+00:00"))
        log["ended_at"] = ended.isoformat()
        log["minutes"] = max(1, round((ended - started).total_seconds() / 60))

    @staticmethod
    def _log_minutes(log: dict[str, Any]) -> int:
        if log.get("minutes") is not None:
            return int(log["minutes"])
        started = datetime.fromisoformat(str(log["started_at"]).replace("Z", "+00:00"))
        return max(0, round((datetime.now(UTC) - started).total_seconds() / 60))

    @staticmethod
    def _release_successors(mes: dict[str, Any], job_id: str) -> None:
        for candidate in mes["jobs"]:
            if candidate.get("predecessor") == job_id and candidate["status"] == "waiting":
                candidate["status"] = "ready"

    @staticmethod
    def _event(
        mes: dict[str, Any], job: dict[str, Any], message: str, level: str = "info"
    ) -> None:
        mes.setdefault("events", []).insert(
            0,
            {
                "timestamp": utc_now(),
                "job_id": job["id"],
                "work_order": job["work_order"],
                "message": message,
                "level": level,
            },
        )
        mes["events"] = mes["events"][:50]

    @staticmethod
    def _linked_documents(state: dict[str, Any], job: dict[str, Any]) -> list[dict[str, Any]]:
        document_ids = set(job.get("documents", []))
        return [
            {
                **deepcopy(document),
                "url": f"/api/documents/{document['id']}",
                "source": "Paperless-ngx",
                "valid_for_job": True,
            }
            for document in state.get("documents", [])
            if document["id"] in document_ids
        ]
