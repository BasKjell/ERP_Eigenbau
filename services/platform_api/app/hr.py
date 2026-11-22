from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from .config import Settings
from .erpnext_client import ERPNextClient, ERPNextError
from .store import ScenarioStore


class HrError(ValueError):
    """Raised when a time-management business rule is violated."""


class HrNotFoundError(HrError):
    """Raised when an HR object does not exist."""


class TimesheetClient(Protocol):
    configured: bool

    def create_document(self, doctype: str, values: dict[str, Any]) -> dict[str, Any]: ...


class HrService:
    REQUEST_TYPES = {
        "vacation",
        "sick",
        "time_off",
        "overtime",
        "remote_work",
        "business_trip",
        "correction",
    }
    ABSENCE_TYPES = {"vacation", "sick", "time_off", "business_trip"}
    STATUS_LABELS = {
        "present": "Anwesend",
        "remote": "Mobiles Arbeiten",
        "vacation": "Urlaub",
        "time_off": "Überstundenabbau",
        "business_trip": "Dienstreise",
        "absent": "Abwesend",
        "left": "Feierabend",
        "planned": "Nicht eingestempelt",
    }

    def __init__(
        self,
        store: ScenarioStore,
        settings: Settings,
        erp_client: TimesheetClient | None = None,
    ) -> None:
        self.store = store
        self.settings = settings
        self.erp_client = erp_client or ERPNextClient(settings)

    def dashboard(
        self,
        employee_id: str,
        selected_date: str | None = None,
    ) -> dict[str, Any]:
        state = self.store.get()
        hr = self._hr(state)
        employee = self._employee(hr, employee_id)
        day = self._parse_date(selected_date) if selected_date else self._today(hr)
        attendance = self._attendance_summary(hr, employee_id, day)
        target = self._target_minutes(hr, employee, day)
        credit = self._credit_minutes(hr, employee_id, day, target)
        balance = self._balance_minutes(hr, employee, day)
        is_manager = self._is_manager(hr, employee_id)
        requests = [
            self._request_view(hr, item, employee_id)
            for item in hr.get("requests", [])
            if item["employee_id"] == employee_id
            or (is_manager and item.get("status") == "pending")
        ]
        requests.sort(key=lambda item: (item["status"] != "pending", item["start_date"]))
        return {
            "site": hr["site"],
            "timezone": hr["timezone"],
            "date": day.isoformat(),
            "employee": self._employee_view(employee),
            "employees": [self._employee_view(item) for item in hr["employees"]],
            "is_manager": is_manager,
            "work_rules": hr["work_rules"],
            "attendance": attendance,
            "metrics": {
                "worked_minutes": attendance["worked_minutes"],
                "credited_minutes": credit,
                "target_minutes": target,
                "day_delta_minutes": attendance["worked_minutes"] + credit - target,
                "overtime_balance_minutes": balance,
                "leave_entitlement_days": employee["annual_leave_days"],
                "leave_used_days": employee["leave_used_days"],
                "leave_remaining_days": self._leave_remaining(hr, employee),
                "pending_requests": sum(
                    item["status"] == "pending"
                    for item in hr.get("requests", [])
                    if item["employee_id"] == employee_id
                ),
                "team_pending_approvals": sum(
                    item["status"] == "pending"
                    and self._can_approve(hr, employee_id, item["employee_id"])
                    for item in hr.get("requests", [])
                ),
            },
            "team": self._team_status(hr, day, employee_id),
            "requests": requests,
            "calendar": self.calendar(employee_id, day.strftime("%Y-%m"), "team" if is_manager else "self"),
            "erp": {
                "configured": self.erp_client.configured,
                "exports": [
                    item
                    for item in hr.get("erp_exports", [])
                    if item["employee_id"] == employee_id
                ][-10:],
            },
            "audit": [
                item
                for item in hr.get("audit", [])
                if item.get("employee_id") == employee_id or is_manager
            ][-12:][::-1],
        }

    def calendar(self, employee_id: str, month: str, scope: str = "self") -> dict[str, Any]:
        state = self.store.get()
        hr = self._hr(state)
        self._employee(hr, employee_id)
        try:
            month_start = datetime.strptime(month, "%Y-%m").date().replace(day=1)
        except ValueError as exc:
            raise HrError("month must use YYYY-MM") from exc
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        if scope not in {"self", "team"}:
            raise HrError("scope must be self or team")
        if scope == "team" and not self._is_manager(hr, employee_id):
            raise HrError("Nur Führungskräfte dürfen den Teamkalender öffnen")
        employee_ids = (
            {item["id"] for item in hr["employees"]}
            if scope == "team"
            else {employee_id}
        )
        events: list[dict[str, Any]] = []
        for item in hr.get("requests", []):
            if item["employee_id"] not in employee_ids or item["status"] == "rejected":
                continue
            start = self._parse_date(item["start_date"])
            end = self._parse_date(item.get("end_date") or item["start_date"])
            if end < month_start or start >= next_month:
                continue
            request_type = item["type"]
            private = scope == "team" and item["employee_id"] != employee_id
            if request_type == "sick" and private:
                display_type = "absence"
                label = "Abwesend"
            else:
                display_type = request_type
                label = self._request_label(request_type)
            events.append(
                {
                    "id": item["id"],
                    "employee_id": item["employee_id"],
                    "employee_name": self._employee(hr, item["employee_id"])["name"],
                    "type": display_type,
                    "label": label,
                    "start_date": item["start_date"],
                    "end_date": item.get("end_date") or item["start_date"],
                    "status": item["status"],
                    "minutes": item.get("minutes"),
                    "reason": "" if private else item.get("reason", ""),
                }
            )
        for holiday in hr.get("holidays", []):
            holiday_date = self._parse_date(holiday["date"])
            if month_start <= holiday_date < next_month:
                events.append(
                    {
                        "id": f"HOL-{holiday['date']}",
                        "employee_id": None,
                        "employee_name": "",
                        "type": "holiday",
                        "label": holiday["name"],
                        "start_date": holiday["date"],
                        "end_date": holiday["date"],
                        "status": "approved",
                        "reason": "Gesetzlicher Feiertag",
                    }
                )
        events.sort(key=lambda item: (item["start_date"], item.get("employee_name", "")))
        return {
            "month": month,
            "scope": scope,
            "events": events,
            "employees": [self._employee_view(item) for item in hr["employees"]],
        }

    def punch(
        self,
        employee_id: str,
        direction: str,
        occurred_at: str | None = None,
        source: str = "web",
        terminal: str = "FLOWHR Web",
    ) -> dict[str, Any]:
        normalized = direction.strip().upper()
        if normalized not in {"IN", "OUT"}:
            raise HrError("direction must be IN or OUT")

        def operation(state: dict[str, Any]) -> None:
            hr = self._hr(state)
            employee = self._employee(hr, employee_id)
            timestamp = self._parse_datetime(occurred_at, hr)
            active_absence = self._active_request(hr, employee_id, timestamp.date())
            if normalized == "IN" and active_absence and active_absence["type"] in {
                "vacation",
                "sick",
            }:
                raise HrError("Für diesen Tag ist eine ganztägige Abwesenheit genehmigt")
            events = sorted(
                (item for item in hr["attendance"] if item["employee_id"] == employee_id),
                key=lambda item: item["timestamp"],
            )
            latest = events[-1] if events else None
            if normalized == "IN" and latest and latest["direction"] == "IN":
                raise HrError("Es besteht bereits eine offene Kommen-Buchung")
            if normalized == "OUT" and (not latest or latest["direction"] != "IN"):
                raise HrError("Vor Gehen muss zuerst Kommen gebucht werden")
            event = {
                "id": self._next_id(hr["attendance"], "HR-ATT"),
                "employee_id": employee_id,
                "direction": normalized,
                "timestamp": timestamp.isoformat(timespec="seconds"),
                "source": source,
                "terminal": terminal,
                "erp_status": "pending",
            }
            hr["attendance"].append(event)
            self._audit(
                hr,
                employee_id,
                "attendance.punch",
                f"{employee['name']}: {'Kommen' if normalized == 'IN' else 'Gehen'} gebucht",
            )

        state = self.store.mutate(operation)
        hr = self._hr(state)
        day = self._parse_datetime(occurred_at, hr).date()
        return self.dashboard(employee_id, day.isoformat())

    def create_request(self, employee_id: str, values: dict[str, Any]) -> dict[str, Any]:
        request_type = str(values.get("type", ""))
        if request_type not in self.REQUEST_TYPES:
            raise HrError("Unbekannter Antragstyp")
        start = self._parse_date(str(values.get("start_date", "")))
        end = self._parse_date(str(values.get("end_date") or values.get("start_date", "")))
        if end < start:
            raise HrError("Das Enddatum darf nicht vor dem Startdatum liegen")
        minutes = int(values.get("minutes") or 0)
        reason = str(values.get("reason") or "").strip()
        if len(reason) < 3:
            raise HrError("Eine kurze Begründung ist erforderlich")
        if request_type in {"overtime", "time_off"} and not 15 <= minutes <= 720:
            raise HrError("Für Mehrarbeit oder Abbau sind 15 bis 720 Minuten erforderlich")
        if request_type == "correction":
            if not values.get("from_time") or not values.get("to_time"):
                raise HrError("Eine Korrektur benötigt Von- und Bis-Zeit")
            self._parse_time(str(values["from_time"]))
            self._parse_time(str(values["to_time"]))

        created: dict[str, Any] = {}

        def operation(state: dict[str, Any]) -> None:
            hr = self._hr(state)
            employee = self._employee(hr, employee_id)
            if request_type == "vacation":
                requested_days = self._working_days(start, end)
                if requested_days > self._leave_remaining(hr, employee):
                    raise HrError("Der Urlaubsanspruch reicht für diesen Zeitraum nicht aus")
            if request_type == "time_off" and minutes > self._balance_minutes(hr, employee, start):
                raise HrError("Das Zeitkonto reicht für diesen Überstundenabbau nicht aus")
            for item in hr["requests"]:
                if item["employee_id"] != employee_id or item["status"] == "rejected":
                    continue
                existing_start = self._parse_date(item["start_date"])
                existing_end = self._parse_date(item.get("end_date") or item["start_date"])
                if (
                    request_type in self.ABSENCE_TYPES
                    and item["type"] in self.ABSENCE_TYPES
                    and start <= existing_end
                    and end >= existing_start
                ):
                    raise HrError(f"Der Zeitraum überschneidet sich mit {item['id']}")
            created.update(
                {
                    "id": self._next_id(hr["requests"], "HR-REQ"),
                    "type": request_type,
                    "employee_id": employee_id,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "minutes": minutes or None,
                    "from_time": values.get("from_time"),
                    "to_time": values.get("to_time"),
                    "reason": reason,
                    "status": "pending",
                    "approver_id": employee.get("manager_id") or hr["manager_id"],
                    "created_at": self._now(hr).isoformat(timespec="seconds"),
                    "decided_at": None,
                    "decision_comment": "",
                }
            )
            hr["requests"].append(created.copy())
            self._audit(
                hr,
                employee_id,
                "request.created",
                f"{created['id']} · {self._request_label(request_type)} beantragt",
            )

        self.store.mutate(operation)
        return created

    def decide_request(
        self,
        request_id: str,
        approver_id: str,
        decision: str,
        comment: str = "",
    ) -> dict[str, Any]:
        normalized = decision.strip().lower()
        if normalized not in {"approved", "rejected"}:
            raise HrError("decision must be approved or rejected")
        decided: dict[str, Any] = {}

        def operation(state: dict[str, Any]) -> None:
            hr = self._hr(state)
            self._employee(hr, approver_id)
            item = self._find_request(hr, request_id)
            if item["status"] != "pending":
                raise HrError("Der Antrag wurde bereits entschieden")
            if approver_id == item["employee_id"]:
                raise HrError("Eigene Anträge dürfen nicht selbst genehmigt werden")
            if not self._can_approve(hr, approver_id, item["employee_id"]):
                raise HrError("Für diesen Antrag besteht keine Genehmigungsberechtigung")
            item["status"] = normalized
            item["approver_id"] = approver_id
            item["decided_at"] = self._now(hr).isoformat(timespec="seconds")
            item["decision_comment"] = comment.strip()
            if normalized == "approved" and item["type"] == "vacation":
                employee = self._employee(hr, item["employee_id"])
                employee["leave_used_days"] += self._working_days(
                    self._parse_date(item["start_date"]),
                    self._parse_date(item["end_date"]),
                )
            if normalized == "approved" and item["type"] == "correction":
                correction_date = self._parse_date(item["start_date"])
                timezone = ZoneInfo(hr["timezone"])
                start = datetime.combine(
                    correction_date, self._parse_time(item["from_time"]), timezone
                )
                end = datetime.combine(
                    correction_date, self._parse_time(item["to_time"]), timezone
                )
                if end <= start:
                    raise HrError("Die Korrektur-Endzeit muss nach der Startzeit liegen")
                existing = [
                    event
                    for event in hr["attendance"]
                    if event["employee_id"] == item["employee_id"]
                    and self._parse_datetime(event["timestamp"], hr).date() == correction_date
                ]
                if existing:
                    raise HrError("Für diesen Tag bestehen bereits Buchungen; manuelle Prüfung nötig")
                for direction, stamp in (("IN", start), ("OUT", end)):
                    hr["attendance"].append(
                        {
                            "id": self._next_id(hr["attendance"], "HR-ATT"),
                            "employee_id": item["employee_id"],
                            "direction": direction,
                            "timestamp": stamp.isoformat(timespec="seconds"),
                            "source": "approved_correction",
                            "terminal": item["id"],
                            "erp_status": "pending",
                        }
                    )
            self._audit(
                hr,
                item["employee_id"],
                "request.decided",
                f"{item['id']} · {'genehmigt' if normalized == 'approved' else 'abgelehnt'}",
                actor_id=approver_id,
            )
            decided.update(item)

        self.store.mutate(operation)
        return decided

    def export_to_erp(
        self,
        employee_id: str,
        selected_date: str,
        *,
        confirm: bool = False,
        confirmation_token: str = "",
    ) -> dict[str, Any]:
        state = self.store.get()
        hr = self._hr(state)
        employee = self._employee(hr, employee_id)
        day = self._parse_date(selected_date)
        existing = next(
            (
                item
                for item in hr.get("erp_exports", [])
                if item["employee_id"] == employee_id
                and item["date"] == day.isoformat()
                and item["status"] == "success"
            ),
            None,
        )
        if existing:
            return {"status": "already_exported", "export": existing}
        intervals = self._completed_intervals(hr, employee_id, day)
        if not intervals:
            raise HrError("Für diesen Tag gibt es keine abgeschlossenen Anwesenheitsintervalle")
        payload = self._timesheet_payload(employee, day, intervals)
        if not confirm:
            token = uuid.uuid4().hex

            def remember(state_to_change: dict[str, Any]) -> None:
                hr_to_change = self._hr(state_to_change)
                hr_to_change.setdefault("export_previews", []).append(
                    {
                        "token": token,
                        "employee_id": employee_id,
                        "date": day.isoformat(),
                        "payload": payload,
                        "created_at": self._now(hr_to_change).isoformat(timespec="seconds"),
                    }
                )

            self.store.mutate(remember)
            return {
                "status": "preview",
                "confirmation_token": token,
                "mode": "live" if self.erp_client.configured else "simulated",
                "payload": payload,
                "interval_count": len(intervals),
            }
        preview = next(
            (
                item
                for item in hr.get("export_previews", [])
                if item["token"] == confirmation_token
                and item["employee_id"] == employee_id
                and item["date"] == day.isoformat()
            ),
            None,
        )
        if not preview:
            raise HrError("Ungültige oder abgelaufene Exportbestätigung")
        mode = "live" if self.erp_client.configured else "simulated"
        try:
            if self.erp_client.configured:
                result = self.erp_client.create_document("Timesheet", preview["payload"])
                reference = str(result["name"])
            else:
                reference = f"SIM-TS-{employee_id}-{day.strftime('%Y%m%d')}"
        except ERPNextError as exc:
            raise HrError(f"ERPNext-Übergabe fehlgeschlagen: {exc}") from exc
        exported: dict[str, Any] = {
            "id": "",
            "employee_id": employee_id,
            "date": day.isoformat(),
            "status": "success",
            "mode": mode,
            "doctype": "Timesheet",
            "erp_reference": reference,
            "interval_count": len(intervals),
            "exported_at": "",
        }

        def record(state_to_change: dict[str, Any]) -> None:
            hr_to_change = self._hr(state_to_change)
            exported["id"] = self._next_id(hr_to_change["erp_exports"], "HR-EXP")
            exported["exported_at"] = self._now(hr_to_change).isoformat(timespec="seconds")
            hr_to_change["erp_exports"].append(exported.copy())
            hr_to_change["export_previews"] = [
                item
                for item in hr_to_change.get("export_previews", [])
                if item["token"] != confirmation_token
            ]
            for event in hr_to_change["attendance"]:
                if event["employee_id"] == employee_id and self._parse_datetime(
                    event["timestamp"], hr_to_change
                ).date() == day:
                    event["erp_status"] = "exported"
                    event["erp_reference"] = reference
            self._audit(
                hr_to_change,
                employee_id,
                "erp.export",
                f"Anwesenheit {day.isoformat()} an {reference} übergeben",
            )

        self.store.mutate(record)
        return {"status": "success", "export": exported}

    def reset(self, employee_id: str) -> dict[str, Any]:
        state = self.store.reset_domain("hr")
        self._employee(self._hr(state), employee_id)
        return self.dashboard(employee_id)

    def _team_status(self, hr: dict[str, Any], day: date, viewer_id: str) -> list[dict[str, Any]]:
        result = []
        for employee in hr["employees"]:
            summary = self._attendance_summary(hr, employee["id"], day)
            active = self._active_request(hr, employee["id"], day)
            if active and active["status"] == "approved":
                status = {
                    "vacation": "vacation",
                    "sick": "absent",
                    "time_off": "time_off",
                    "remote_work": "remote",
                    "business_trip": "business_trip",
                }.get(active["type"], "planned")
            elif summary["is_present"]:
                status = "present"
            elif summary["events"]:
                status = "left"
            else:
                status = "planned"
            result.append(
                {
                    **self._employee_view(employee),
                    "status": status,
                    "status_label": self.STATUS_LABELS[status],
                    "since": summary.get("last_timestamp"),
                    "worked_minutes": summary["worked_minutes"],
                    "location": "Mobiles Arbeiten" if status == "remote" else employee["location"],
                    "detail": (
                        "Abwesend"
                        if active and active["type"] == "sick" and employee["id"] != viewer_id
                        else self.STATUS_LABELS[status]
                    ),
                }
            )
        return result

    def _attendance_summary(self, hr: dict[str, Any], employee_id: str, day: date) -> dict[str, Any]:
        events = sorted(
            (
                item
                for item in hr.get("attendance", [])
                if item["employee_id"] == employee_id
                and self._parse_datetime(item["timestamp"], hr).date() == day
            ),
            key=lambda item: item["timestamp"],
        )
        worked = 0
        breaks = 0
        open_in: datetime | None = None
        previous_out: datetime | None = None
        now = self._now(hr)
        for item in events:
            stamp = self._parse_datetime(item["timestamp"], hr)
            if item["direction"] == "IN":
                if previous_out:
                    breaks += max(0, int((stamp - previous_out).total_seconds() // 60))
                open_in = stamp
            elif open_in:
                worked += max(0, int((stamp - open_in).total_seconds() // 60))
                open_in = None
                previous_out = stamp
        if open_in and day == now.date():
            worked += max(0, int((now - open_in).total_seconds() // 60))
        minimum_break = int(hr["work_rules"]["minimum_break_minutes"])
        threshold = int(hr["work_rules"]["break_threshold_minutes"])
        warnings = []
        if worked > threshold and breaks < minimum_break:
            warnings.append(f"Mindestpause von {minimum_break} Minuten noch nicht erreicht")
        maximum_daily = int(hr["work_rules"]["maximum_daily_minutes"])
        if worked > maximum_daily:
            warnings.append(
                f"Tägliche Höchstarbeitszeit von {maximum_daily // 60} Stunden überschritten"
            )
        return {
            "events": events,
            "is_present": bool(open_in),
            "worked_minutes": worked,
            "break_minutes": breaks,
            "last_direction": events[-1]["direction"] if events else None,
            "last_timestamp": events[-1]["timestamp"] if events else None,
            "warnings": warnings,
        }

    def _completed_intervals(
        self, hr: dict[str, Any], employee_id: str, day: date
    ) -> list[tuple[datetime, datetime]]:
        events = sorted(
            (
                item
                for item in hr["attendance"]
                if item["employee_id"] == employee_id
                and self._parse_datetime(item["timestamp"], hr).date() == day
            ),
            key=lambda item: item["timestamp"],
        )
        intervals: list[tuple[datetime, datetime]] = []
        start: datetime | None = None
        for event in events:
            stamp = self._parse_datetime(event["timestamp"], hr)
            if event["direction"] == "IN":
                start = stamp
            elif start:
                intervals.append((start, stamp))
                start = None
        if start:
            raise HrError("Die Anwesenheit ist noch offen; zuerst Gehen buchen")
        return intervals

    def _timesheet_payload(
        self,
        employee: dict[str, Any],
        day: date,
        intervals: list[tuple[datetime, datetime]],
    ) -> dict[str, Any]:
        return {
            "naming_series": "TS-.YYYY.-",
            "employee": employee["id"],
            "company": self.settings.mcp_default_company,
            "time_logs": [
                {
                    "activity_type": "Anwesenheitszeit",
                    "from_time": start.strftime("%Y-%m-%d %H:%M:%S"),
                    "to_time": end.strftime("%Y-%m-%d %H:%M:%S"),
                    "hours": round((end - start).total_seconds() / 3600, 4),
                    "description": f"FLOWHR Anwesenheit {day.strftime('%d.%m.%Y')}",
                    "completed": 1,
                    "is_billable": 0,
                }
                for start, end in intervals
            ],
            "note": (
                "Automatisch aus bestätigten FLOWHR Kommen-/Gehen-Buchungen. "
                "Keine Fertigungs- oder Projektzeit."
            ),
        }

    def _balance_minutes(self, hr: dict[str, Any], employee: dict[str, Any], until: date) -> int:
        balance = int(employee["overtime_opening_minutes"])
        dates = {
            self._parse_datetime(item["timestamp"], hr).date()
            for item in hr.get("attendance", [])
            if item["employee_id"] == employee["id"]
            and self._parse_datetime(item["timestamp"], hr).date() <= until
        }
        for day in dates:
            summary = self._attendance_summary(hr, employee["id"], day)
            target = self._target_minutes(hr, employee, day)
            balance += summary["worked_minutes"] + self._credit_minutes(
                hr, employee["id"], day, target
            ) - target
        balance -= sum(
            int(item.get("minutes") or 0)
            for item in hr.get("requests", [])
            if item["employee_id"] == employee["id"]
            and item["type"] == "time_off"
            and item["status"] == "approved"
            and self._parse_date(item["start_date"]) <= until
        )
        return balance

    def _credit_minutes(
        self, hr: dict[str, Any], employee_id: str, day: date, target: int
    ) -> int:
        item = self._active_request(hr, employee_id, day)
        if not item or item["status"] != "approved":
            return 0
        if item["type"] in {"vacation", "sick", "business_trip"}:
            return target
        if item["type"] == "time_off":
            return min(target, int(item.get("minutes") or target))
        return 0

    def _active_request(
        self, hr: dict[str, Any], employee_id: str, day: date
    ) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in hr.get("requests", [])
                if item["employee_id"] == employee_id
                and item["status"] == "approved"
                and self._parse_date(item["start_date"])
                <= day
                <= self._parse_date(item.get("end_date") or item["start_date"])
            ),
            None,
        )

    def _leave_remaining(self, hr: dict[str, Any], employee: dict[str, Any]) -> int:
        pending = sum(
            self._working_days(
                self._parse_date(item["start_date"]), self._parse_date(item["end_date"])
            )
            for item in hr.get("requests", [])
            if item["employee_id"] == employee["id"]
            and item["type"] == "vacation"
            and item["status"] == "pending"
        )
        return max(0, int(employee["annual_leave_days"]) - int(employee["leave_used_days"]) - pending)

    def _target_minutes(
        self, hr: dict[str, Any], employee: dict[str, Any], day: date
    ) -> int:
        if any(item["date"] == day.isoformat() for item in hr.get("holidays", [])):
            return 0
        return int(employee["schedule_minutes"].get(str(day.weekday()), 0))

    def _request_view(
        self, hr: dict[str, Any], item: dict[str, Any], viewer_id: str
    ) -> dict[str, Any]:
        employee = self._employee(hr, item["employee_id"])
        private = item["type"] == "sick" and viewer_id != item["employee_id"]
        return {
            **item,
            "employee_name": employee["name"],
            "type_label": "Abwesenheit" if private else self._request_label(item["type"]),
            "reason": "" if private else item.get("reason", ""),
            "can_decide": item["status"] == "pending"
            and self._can_approve(hr, viewer_id, item["employee_id"])
            and viewer_id != item["employee_id"],
        }

    @staticmethod
    def _request_label(request_type: str) -> str:
        return {
            "vacation": "Urlaub",
            "sick": "Arbeitsunfähigkeit",
            "time_off": "Überstundenabbau",
            "overtime": "Mehrarbeit",
            "remote_work": "Mobiles Arbeiten",
            "business_trip": "Dienstreise",
            "correction": "Zeitkorrektur",
        }.get(request_type, request_type)

    @staticmethod
    def _employee_view(employee: dict[str, Any]) -> dict[str, Any]:
        return {
            key: employee[key]
            for key in (
                "id",
                "name",
                "initials",
                "department",
                "role",
                "manager_id",
                "location",
            )
        }

    def _is_manager(self, hr: dict[str, Any], employee_id: str) -> bool:
        return employee_id == hr["manager_id"] or any(
            item.get("manager_id") == employee_id for item in hr["employees"]
        )

    def _can_approve(self, hr: dict[str, Any], approver_id: str, employee_id: str) -> bool:
        employee = self._employee(hr, employee_id)
        return approver_id == (employee.get("manager_id") or hr["manager_id"])

    @staticmethod
    def _working_days(start: date, end: date) -> int:
        return sum(
            (start + timedelta(days=offset)).weekday() < 5
            for offset in range((end - start).days + 1)
        )

    @staticmethod
    def _next_id(items: list[dict[str, Any]], prefix: str) -> str:
        numbers = []
        for item in items:
            try:
                numbers.append(int(str(item.get("id", "")).rsplit("-", 1)[-1]))
            except ValueError:
                continue
        return f"{prefix}-{max(numbers, default=0) + 1:04d}"

    def _find_request(self, hr: dict[str, Any], request_id: str) -> dict[str, Any]:
        item = next((item for item in hr["requests"] if item["id"] == request_id), None)
        if not item:
            raise HrNotFoundError(f"Antrag {request_id} wurde nicht gefunden")
        return item

    @staticmethod
    def _employee(hr: dict[str, Any], employee_id: str) -> dict[str, Any]:
        employee = next((item for item in hr["employees"] if item["id"] == employee_id), None)
        if not employee:
            raise HrNotFoundError(f"Mitarbeiter {employee_id} wurde nicht gefunden")
        return employee

    @staticmethod
    def _hr(state: dict[str, Any]) -> dict[str, Any]:
        hr = state.get("hr")
        if not isinstance(hr, dict):
            raise HrError("HR-Demodaten fehlen")
        return hr

    @staticmethod
    def _parse_date(value: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise HrError("Datum muss YYYY-MM-DD verwenden") from exc

    @staticmethod
    def _parse_time(value: str) -> time:
        try:
            return time.fromisoformat(value)
        except ValueError as exc:
            raise HrError("Uhrzeit muss HH:MM verwenden") from exc

    def _parse_datetime(self, value: str | None, hr: dict[str, Any]) -> datetime:
        if not value:
            return self._now(hr)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HrError("Zeitpunkt muss ISO-8601 verwenden") from exc
        timezone = ZoneInfo(hr["timezone"])
        return parsed.replace(tzinfo=timezone) if parsed.tzinfo is None else parsed.astimezone(timezone)

    @staticmethod
    def _now(hr: dict[str, Any]) -> datetime:
        return datetime.now(ZoneInfo(hr["timezone"]))

    def _today(self, hr: dict[str, Any]) -> date:
        return self._now(hr).date()

    def _audit(
        self,
        hr: dict[str, Any],
        employee_id: str,
        action: str,
        message: str,
        actor_id: str | None = None,
    ) -> None:
        hr.setdefault("audit", []).append(
            {
                "id": self._next_id(hr.get("audit", []), "HR-AUD"),
                "timestamp": self._now(hr).isoformat(timespec="seconds"),
                "actor_id": actor_id or employee_id,
                "employee_id": employee_id,
                "action": action,
                "message": message,
            }
        )
