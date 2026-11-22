from __future__ import annotations

import io
import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFError, TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .config import Settings
from .erpnext_client import ERPNextClient, ERPNextError
from .paperless_client import PaperlessClient, PaperlessError
from .store import ScenarioStore


class PeopleError(ValueError):
    """Business-rule violation in recruiting or payroll."""


class PeopleNotFoundError(PeopleError):
    """Requested people object does not exist."""


class DocumentArchive(Protocol):
    configured: bool

    def upload_document(
        self, content: bytes, filename: str, title: str
    ) -> dict[str, Any]: ...


class AccountingTarget(Protocol):
    configured: bool

    def create_document(self, doctype: str, values: dict[str, Any]) -> dict[str, Any]: ...


class PeopleService:
    """Privacy-aware recruiting and controlled payroll workflow for the demo.

    The payroll calculation deliberately uses versioned demonstration input values.
    It proves workflow, controls, documents and interfaces, but is not a certified
    German payroll calculation engine.
    """

    RECRUITING_ROLES = {"recruiter", "hr_admin"}
    PAYROLL_READ_ROLES = {"payroll_preparer", "payroll_approver", "hr_admin"}
    STAGE_ORDER = ("new", "screening", "interview", "offer", "hired")
    STAGE_LABELS = {
        "new": "Neu",
        "screening": "Vorauswahl",
        "interview": "Gespräch",
        "offer": "Angebot",
        "hired": "Eingestellt",
        "rejected": "Abgelehnt",
    }

    def __init__(
        self,
        store: ScenarioStore,
        settings: Settings,
        dms_client: DocumentArchive | None = None,
        erp_client: AccountingTarget | None = None,
        pdf_renderer: Callable[[dict[str, Any], dict[str, Any], str], bytes] | None = None,
    ) -> None:
        self.store = store
        self.settings = settings
        self.dms_client = dms_client or PaperlessClient(settings)
        self.erp_client = erp_client or ERPNextClient(settings)
        self.pdf_renderer = pdf_renderer or render_payslip_pdf

    def recruiting_dashboard(self, actor_id: str) -> dict[str, Any]:
        state = self.store.get()
        hr = self._hr(state)
        actor = self._require_role(hr, actor_id, self.RECRUITING_ROLES)
        recruiting = self._recruiting(hr)
        today = self._now(hr).date()
        applications = [
            self._application_view(state, item, today) for item in recruiting["applications"]
        ]
        open_applications = [
            item for item in applications if item["stage"] not in {"hired", "rejected"}
        ]
        return {
            "actor": self._actor_view(actor),
            "actors": [self._actor_view(item) for item in hr["admin_users"]],
            "vacancies": recruiting["vacancies"],
            "applications": applications,
            "stage_labels": self.STAGE_LABELS,
            "metrics": {
                "open_vacancies": sum(
                    item["status"] == "open" for item in recruiting["vacancies"]
                ),
                "active_applications": len(open_applications),
                "interviews": sum(item["stage"] == "interview" for item in applications),
                "retention_due": sum(item["retention_status"] == "due" for item in applications),
            },
            "dms": {
                "mode": "live" if self.dms_client.configured else "simulated",
                "access_group": "DMS-Bereich-HR-Recruiting",
                "retention_policy": recruiting["retention_policy"],
            },
        }

    def create_application(self, actor_id: str, values: dict[str, Any]) -> dict[str, Any]:
        state = self.store.get()
        hr = self._hr(state)
        self._require_role(hr, actor_id, self.RECRUITING_ROLES)
        recruiting = self._recruiting(hr)
        vacancy_id = str(values.get("vacancy_id") or "").strip()
        vacancy = next(
            (item for item in recruiting["vacancies"] if item["id"] == vacancy_id), None
        )
        if not vacancy or vacancy["status"] != "open":
            raise PeopleError("Die ausgewählte Stelle ist nicht zur Bewerbung geöffnet")
        candidate_name = str(values.get("candidate_name") or "").strip()
        email = str(values.get("email") or "").strip().casefold()
        if len(candidate_name) < 3 or "@" not in email:
            raise PeopleError("Name und gültige E-Mail-Adresse sind erforderlich")
        duplicate = next(
            (
                item
                for item in recruiting["applications"]
                if item["vacancy_id"] == vacancy_id
                and item["email"].casefold() == email
                and item["stage"] not in {"hired", "rejected"}
            ),
            None,
        )
        if duplicate:
            raise PeopleError(f"Für diese Stelle besteht bereits Bewerbung {duplicate['id']}")
        created: dict[str, Any] = {}

        def operation(state_to_change: dict[str, Any]) -> None:
            hr_to_change = self._hr(state_to_change)
            recruiting_to_change = self._recruiting(hr_to_change)
            now = self._now(hr_to_change)
            retention_days = int(recruiting_to_change["retention_policy"]["days_after_close"])
            application_id = self._next_id(recruiting_to_change["applications"], "APP")
            item = {
                "id": application_id,
                "vacancy_id": vacancy_id,
                "candidate_name": candidate_name,
                "email": email,
                "phone": str(values.get("phone") or "").strip(),
                "source": str(values.get("source") or "Direktbewerbung").strip(),
                "stage": "new",
                "created_at": now.isoformat(timespec="seconds"),
                "updated_at": now.isoformat(timespec="seconds"),
                "retention_until": (now.date() + timedelta(days=retention_days)).isoformat(),
                "privacy_notice_version": recruiting_to_change["privacy_notice_version"],
                "documents": [],
                "history": [
                    {
                        "timestamp": now.isoformat(timespec="seconds"),
                        "actor_id": actor_id,
                        "stage": "new",
                        "note": "Bewerbung erfasst",
                    }
                ],
            }
            recruiting_to_change["applications"].append(item)
            self._audit(
                hr_to_change,
                actor_id,
                application_id,
                "recruiting.application.created",
                f"{application_id} für {vacancy_id} angelegt",
            )
            created.update(item)

        self.store.mutate(operation)
        return created

    def move_application(
        self,
        application_id: str,
        actor_id: str,
        target_stage: str,
        note: str = "",
    ) -> dict[str, Any]:
        state = self.store.get()
        hr = self._hr(state)
        self._require_role(hr, actor_id, self.RECRUITING_ROLES)
        normalized = target_stage.strip().casefold()
        if normalized not in self.STAGE_LABELS:
            raise PeopleError("Unbekannte Bewerbungsphase")
        changed: dict[str, Any] = {}

        def operation(state_to_change: dict[str, Any]) -> None:
            hr_to_change = self._hr(state_to_change)
            item = self._application(self._recruiting(hr_to_change), application_id)
            current = item["stage"]
            if current in {"hired", "rejected"}:
                raise PeopleError("Eine abgeschlossene Bewerbung kann nicht verschoben werden")
            if normalized != "rejected":
                expected_index = self.STAGE_ORDER.index(current) + 1
                if expected_index >= len(self.STAGE_ORDER):
                    raise PeopleError("Die Bewerbung ist bereits abgeschlossen")
                expected = self.STAGE_ORDER[expected_index]
                if normalized != expected:
                    raise PeopleError(
                        f"Nächste zulässige Phase ist {self.STAGE_LABELS[expected]}"
                    )
            now = self._now(hr_to_change)
            item["stage"] = normalized
            item["updated_at"] = now.isoformat(timespec="seconds")
            if normalized in {"hired", "rejected"}:
                item["closed_at"] = now.isoformat(timespec="seconds")
                days = int(
                    self._recruiting(hr_to_change)["retention_policy"]["days_after_close"]
                )
                item["retention_until"] = (now.date() + timedelta(days=days)).isoformat()
            item.setdefault("history", []).append(
                {
                    "timestamp": now.isoformat(timespec="seconds"),
                    "actor_id": actor_id,
                    "stage": normalized,
                    "note": note.strip()[:500],
                }
            )
            self._audit(
                hr_to_change,
                actor_id,
                application_id,
                "recruiting.stage.changed",
                f"{application_id}: {self.STAGE_LABELS[current]} -> {self.STAGE_LABELS[normalized]}",
            )
            changed.update(item)

        self.store.mutate(operation)
        return changed

    def link_application_document(
        self,
        application_id: str,
        actor_id: str,
        document_id: str,
        document_type: str,
    ) -> dict[str, Any]:
        state = self.store.get()
        hr = self._hr(state)
        self._require_role(hr, actor_id, self.RECRUITING_ROLES)
        document = next(
            (item for item in state.get("documents", []) if item["id"] == document_id), None
        )
        if not document:
            raise PeopleNotFoundError(f"Dokument {document_id} wurde nicht gefunden")
        if document.get("type") != "Bewerbungsunterlage" and "HR-Recruiting" not in document.get(
            "tags", []
        ):
            raise PeopleError("Nur Dokumente der geschützten Bewerberakte dürfen verknüpft werden")
        linked: dict[str, Any] = {}

        def operation(state_to_change: dict[str, Any]) -> None:
            hr_to_change = self._hr(state_to_change)
            item = self._application(self._recruiting(hr_to_change), application_id)
            if any(doc["document_id"] == document_id for doc in item["documents"]):
                raise PeopleError("Das Dokument ist bereits mit der Bewerbung verknüpft")
            linked.update(
                {
                    "id": self._next_id(item["documents"], "APP-DOC"),
                    "document_id": document_id,
                    "title": document["title"],
                    "document_type": document_type.strip() or document["type"],
                    "status": "archived",
                    "access_group": "DMS-Bereich-HR-Recruiting",
                    "linked_at": self._now(hr_to_change).isoformat(timespec="seconds"),
                    "linked_by": actor_id,
                }
            )
            item["documents"].append(linked.copy())
            self._audit(
                hr_to_change,
                actor_id,
                application_id,
                "recruiting.document.linked",
                f"{document_id} mit {application_id} verknüpft",
            )

        self.store.mutate(operation)
        return linked

    def upload_application_document(
        self,
        application_id: str,
        actor_id: str,
        content: bytes,
        filename: str,
        document_type: str,
    ) -> dict[str, Any]:
        state = self.store.get()
        hr = self._hr(state)
        self._require_role(hr, actor_id, self.RECRUITING_ROLES)
        self._application(self._recruiting(hr), application_id)
        if not self.dms_client.configured:
            raise PeopleError("Paperless ist nicht konfiguriert; Datei wurde nicht gespeichert")
        if not content or len(content) > 10 * 1024 * 1024:
            raise PeopleError("Die Datei muss zwischen 1 Byte und 10 MB groß sein")
        safe_name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        if not safe_name.casefold().endswith((".pdf", ".png", ".jpg", ".jpeg")):
            raise PeopleError("Zulässig sind PDF-, PNG- und JPEG-Dateien")
        archive_filename = f"Bewerbung_{application_id}_{safe_name}"
        title = f"Bewerbung {application_id} - {document_type.strip() or 'Unterlage'}"
        try:
            result = self.dms_client.upload_document(content, archive_filename, title)
        except PaperlessError as exc:
            raise PeopleError(f"DMS-Upload fehlgeschlagen: {exc}") from exc
        uploaded: dict[str, Any] = {}

        def operation(state_to_change: dict[str, Any]) -> None:
            hr_to_change = self._hr(state_to_change)
            item = self._application(self._recruiting(hr_to_change), application_id)
            uploaded.update(
                {
                    "id": self._next_id(item["documents"], "APP-DOC"),
                    "document_id": None,
                    "title": title,
                    "document_type": document_type.strip() or "Bewerbungsunterlage",
                    "filename": archive_filename,
                    "status": "processing",
                    "dms_task_id": result["task_id"],
                    "access_group": "DMS-Bereich-HR-Recruiting",
                    "linked_at": self._now(hr_to_change).isoformat(timespec="seconds"),
                    "linked_by": actor_id,
                }
            )
            item["documents"].append(uploaded.copy())
            self._audit(
                hr_to_change,
                actor_id,
                application_id,
                "recruiting.document.uploaded",
                f"{archive_filename} an Paperless übergeben",
            )

        self.store.mutate(operation)
        return uploaded

    def payroll_dashboard(self, actor_id: str, period_id: str | None = None) -> dict[str, Any]:
        state = self.store.get()
        hr = self._hr(state)
        actor = self._require_role(hr, actor_id, self.PAYROLL_READ_ROLES)
        payroll = self._payroll(hr)
        period = self._period(payroll, period_id or payroll["periods"][0]["id"])
        preview = next(
            (
                item
                for item in reversed(payroll.get("previews", []))
                if item["period_id"] == period["id"]
            ),
            None,
        )
        run = next(
            (
                item
                for item in reversed(payroll.get("runs", []))
                if item["period_id"] == period["id"]
            ),
            None,
        )
        profiles = [self._profile_view(hr, item) for item in payroll["profiles"]]
        return {
            "actor": self._actor_view(actor),
            "actors": [self._actor_view(item) for item in hr["admin_users"]],
            "periods": payroll["periods"],
            "period": period,
            "profiles": profiles,
            "preview": preview,
            "run": run,
            "mode": payroll["calculation_mode"],
            "legal_notice": payroll["legal_notice"],
            "interfaces": {
                "dms": "live" if self.dms_client.configured else "simulated",
                "erp": "live" if self.erp_client.configured else "simulated",
                "elstam": period["elstam_status"],
                "social_insurance": period["social_insurance_status"],
            },
            "permissions": {
                "can_prepare": "payroll_preparer" in actor["roles"],
                "can_approve": "payroll_approver" in actor["roles"],
            },
        }

    def prepare_payroll(self, period_id: str, actor_id: str) -> dict[str, Any]:
        state = self.store.get()
        hr = self._hr(state)
        actor = self._require_role(hr, actor_id, {"payroll_preparer"})
        payroll = self._payroll(hr)
        period = self._period(payroll, period_id)
        if period["status"] != "open":
            raise PeopleError("Nur ein offener Abrechnungszeitraum kann vorbereitet werden")
        if period["attendance_status"] != "locked":
            raise PeopleError("Die Anwesenheitsdaten müssen vor der Abrechnung gesperrt sein")
        invalid = [
            profile["employee_id"]
            for profile in payroll["profiles"]
            if not all(profile["checks"].values())
        ]
        if invalid:
            raise PeopleError(f"Unvollständige Abrechnungsstammdaten: {', '.join(invalid)}")
        rows = [self._calculate_profile(hr, profile) for profile in payroll["profiles"]]
        token = uuid.uuid4().hex
        preview = {
            "token": token,
            "period_id": period_id,
            "prepared_by": actor_id,
            "prepared_by_name": actor["name"],
            "prepared_at": self._now(hr).isoformat(timespec="seconds"),
            "employee_count": len(rows),
            "gross_cents": sum(row["gross_cents"] for row in rows),
            "deduction_cents": sum(row["deduction_cents"] for row in rows),
            "net_cents": sum(row["net_cents"] for row in rows),
            "rows": rows,
            "calculation_mode": payroll["calculation_mode"],
        }

        def operation(state_to_change: dict[str, Any]) -> None:
            hr_to_change = self._hr(state_to_change)
            payroll_to_change = self._payroll(hr_to_change)
            payroll_to_change.setdefault("previews", []).append(preview)
            payroll_to_change["previews"] = payroll_to_change["previews"][-20:]
            self._audit(
                hr_to_change,
                actor_id,
                period_id,
                "payroll.preview.created",
                f"{period_id}: Vorschau für {len(rows)} Beschäftigte erstellt",
            )

        self.store.mutate(operation)
        return preview

    def approve_payroll(
        self, period_id: str, actor_id: str, confirmation_token: str
    ) -> dict[str, Any]:
        state = self.store.get()
        hr = self._hr(state)
        actor = self._require_role(hr, actor_id, {"payroll_approver"})
        payroll = self._payroll(hr)
        period = self._period(payroll, period_id)
        existing = next(
            (item for item in payroll.get("runs", []) if item["period_id"] == period_id), None
        )
        if existing:
            return {"status": "already_approved", "run": existing}
        preview = next(
            (
                item
                for item in payroll.get("previews", [])
                if item["token"] == confirmation_token and item["period_id"] == period_id
            ),
            None,
        )
        if not preview:
            raise PeopleError("Ungültige oder abgelaufene Abrechnungsbestätigung")
        if preview["prepared_by"] == actor_id:
            raise PeopleError("Vorbereitung und Freigabe müssen durch verschiedene Personen erfolgen")
        if period["status"] != "open":
            raise PeopleError("Der Abrechnungszeitraum ist nicht mehr offen")
        run_id = self._next_id(payroll.get("runs", []), "PAYRUN")
        approved_at = self._now(hr).isoformat(timespec="seconds")
        run = {
            "id": run_id,
            "period_id": period_id,
            "status": "approved_pending_delivery",
            "prepared_by": preview["prepared_by"],
            "approved_by": actor_id,
            "approved_by_name": actor["name"],
            "approved_at": approved_at,
            "employee_count": preview["employee_count"],
            "gross_cents": preview["gross_cents"],
            "deduction_cents": preview["deduction_cents"],
            "net_cents": preview["net_cents"],
            "rows": preview["rows"],
            "erp_reference": None,
            "outputs": [
                {
                    "employee_id": row["employee_id"],
                    "document_id": f"{run_id}-{row['employee_id']}",
                    "filename": f"Entgeltabrechnung_{period_id}_{row['employee_id']}.pdf",
                    "dms_status": "queued",
                    "dms_task_id": None,
                    "access_group": "DMS-Bereich-HR-Payroll",
                }
                for row in preview["rows"]
            ],
        }

        def operation(state_to_change: dict[str, Any]) -> None:
            hr_to_change = self._hr(state_to_change)
            payroll_to_change = self._payroll(hr_to_change)
            target_period = self._period(payroll_to_change, period_id)
            target_period["status"] = "approved"
            payroll_to_change.setdefault("runs", []).append(run)
            payroll_to_change["previews"] = [
                item
                for item in payroll_to_change.get("previews", [])
                if item["token"] != confirmation_token
            ]
            self._audit(
                hr_to_change,
                actor_id,
                period_id,
                "payroll.run.approved",
                f"{run_id} im Vier-Augen-Prinzip freigegeben",
            )

        self.store.mutate(operation)
        return {"status": "approved", "run": run}

    def deliver_payroll(self, run_id: str, actor_id: str) -> dict[str, Any]:
        state = self.store.get()
        hr = self._hr(state)
        self._require_role(hr, actor_id, {"payroll_approver"})
        payroll = self._payroll(hr)
        run = self._run(payroll, run_id)
        period = self._period(payroll, run["period_id"])
        if run["status"] == "delivered":
            return {"status": "already_delivered", "run": run}
        if run["status"] != "approved_pending_delivery":
            raise PeopleError("Nur eine freigegebene Abrechnung kann übergeben werden")

        for output in run["outputs"]:
            if output.get("dms_task_id"):
                continue
            row = next(
                item for item in run["rows"] if item["employee_id"] == output["employee_id"]
            )
            if self.dms_client.configured:
                try:
                    content = self.pdf_renderer(run, row, self.settings.mcp_default_company)
                    result = self.dms_client.upload_document(
                        content,
                        output["filename"],
                        f"Entgeltabrechnung {period['label']} - {row['employee_name']}",
                    )
                    task_id = result["task_id"]
                    dms_status = "processing"
                except PaperlessError as exc:
                    raise PeopleError(f"DMS-Archivierung fehlgeschlagen: {exc}") from exc
            else:
                task_id = f"SIM-DMS-{output['document_id']}"
                dms_status = "simulated"
            self._record_output_delivery(run_id, output["employee_id"], task_id, dms_status)

        current = self._run(self._payroll(self._hr(self.store.get())), run_id)
        if not current.get("erp_reference"):
            if self.erp_client.configured:
                try:
                    result = self.erp_client.create_document(
                        "Journal Entry", self._journal_entry(period, current)
                    )
                    erp_reference = str(result["name"])
                except ERPNextError as exc:
                    raise PeopleError(f"ERPNext-Buchungsübergabe fehlgeschlagen: {exc}") from exc
            else:
                erp_reference = f"SIM-JE-{run_id}"
            self._record_erp_delivery(run_id, erp_reference)

        delivered: dict[str, Any] = {}

        def finalize(state_to_change: dict[str, Any]) -> None:
            hr_to_change = self._hr(state_to_change)
            payroll_to_change = self._payroll(hr_to_change)
            run_to_change = self._run(payroll_to_change, run_id)
            run_to_change["status"] = "delivered"
            run_to_change["delivered_at"] = self._now(hr_to_change).isoformat(
                timespec="seconds"
            )
            self._period(payroll_to_change, run_to_change["period_id"])["status"] = "closed"
            self._audit(
                hr_to_change,
                actor_id,
                run_id,
                "payroll.run.delivered",
                f"{run_id} an DMS und ERP übergeben",
            )
            delivered.update(run_to_change)

        self.store.mutate(finalize)
        return {"status": "delivered", "run": delivered}

    def payslip_pdf(self, run_id: str, employee_id: str, actor_id: str) -> bytes:
        state = self.store.get()
        hr = self._hr(state)
        if actor_id != employee_id:
            self._require_role(hr, actor_id, self.PAYROLL_READ_ROLES)
        payroll = self._payroll(hr)
        run = self._run(payroll, run_id)
        row = next(
            (item for item in run["rows"] if item["employee_id"] == employee_id), None
        )
        if not row:
            raise PeopleNotFoundError("Entgeltabrechnung wurde nicht gefunden")
        return self.pdf_renderer(run, row, self.settings.mcp_default_company)

    def _record_output_delivery(
        self, run_id: str, employee_id: str, task_id: str, status: str
    ) -> None:
        def operation(state_to_change: dict[str, Any]) -> None:
            run = self._run(self._payroll(self._hr(state_to_change)), run_id)
            output = next(
                item for item in run["outputs"] if item["employee_id"] == employee_id
            )
            output["dms_task_id"] = task_id
            output["dms_status"] = status

        self.store.mutate(operation)

    def _record_erp_delivery(self, run_id: str, reference: str) -> None:
        def operation(state_to_change: dict[str, Any]) -> None:
            run = self._run(self._payroll(self._hr(state_to_change)), run_id)
            run["erp_reference"] = reference

        self.store.mutate(operation)

    def _application_view(
        self, state: dict[str, Any], item: dict[str, Any], today: date
    ) -> dict[str, Any]:
        vacancy = next(
            entry
            for entry in self._recruiting(self._hr(state))["vacancies"]
            if entry["id"] == item["vacancy_id"]
        )
        retention_until = date.fromisoformat(item["retention_until"])
        days = (retention_until - today).days
        return {
            **item,
            "vacancy_title": vacancy["title"],
            "stage_label": self.STAGE_LABELS[item["stage"]],
            "retention_status": "due" if days <= 30 else "ok",
            "retention_days": days,
        }

    def _calculate_profile(
        self, hr: dict[str, Any], profile: dict[str, Any]
    ) -> dict[str, Any]:
        employee = next(
            item for item in hr["employees"] if item["id"] == profile["employee_id"]
        )
        earnings = [dict(item) for item in profile["earnings"]]
        deductions = [dict(item) for item in profile["deductions"]]
        gross = sum(int(item["amount_cents"]) for item in earnings)
        deduction = sum(int(item["amount_cents"]) for item in deductions)
        if gross < deduction:
            raise PeopleError(f"Abzüge überschreiten Brutto für {profile['employee_id']}")
        return {
            "employee_id": profile["employee_id"],
            "employee_name": employee["name"],
            "department": employee["department"],
            "tax_class": profile["tax_class"],
            "health_insurance": profile["health_insurance"],
            "bank_account_masked": profile["bank_account_masked"],
            "earnings": earnings,
            "deductions": deductions,
            "gross_cents": gross,
            "deduction_cents": deduction,
            "net_cents": gross - deduction,
        }

    def _profile_view(self, hr: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        row = self._calculate_profile(hr, profile)
        return {
            **row,
            "checks": profile["checks"],
            "master_data_status": "complete" if all(profile["checks"].values()) else "incomplete",
        }

    def _journal_entry(
        self, period: dict[str, Any], run: dict[str, Any]
    ) -> dict[str, Any]:
        gross = run["gross_cents"] / 100
        net = run["net_cents"] / 100
        liabilities = run["deduction_cents"] / 100
        company = self.settings.mcp_default_company
        return {
            "voucher_type": "Journal Entry",
            "company": company,
            "posting_date": period["end_date"],
            "user_remark": f"FLOWHR Abrechnung {run['id']} ({period['label']})",
            "accounts": [
                {
                    "account": "Payroll Expense - OMD",
                    "debit_in_account_currency": gross,
                    "credit_in_account_currency": 0,
                },
                {
                    "account": "Payroll Payable - OMD",
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": net,
                },
                {
                    "account": "Payroll Deductions Payable - OMD",
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": liabilities,
                },
            ],
        }

    def _require_role(
        self, hr: dict[str, Any], actor_id: str, required: set[str]
    ) -> dict[str, Any]:
        actor = next(
            (item for item in hr.get("admin_users", []) if item["id"] == actor_id), None
        )
        if not actor:
            raise PeopleNotFoundError(f"HR-Benutzer {actor_id} wurde nicht gefunden")
        if not required.intersection(actor["roles"]):
            raise PeopleError("Für diese Funktion fehlt die erforderliche HR-Rolle")
        return actor

    @staticmethod
    def _actor_view(actor: dict[str, Any]) -> dict[str, Any]:
        return {key: actor[key] for key in ("id", "name", "initials", "roles")}

    @staticmethod
    def _hr(state: dict[str, Any]) -> dict[str, Any]:
        hr = state.get("hr")
        if not isinstance(hr, dict):
            raise PeopleError("HR-Demodaten fehlen")
        return hr

    @staticmethod
    def _recruiting(hr: dict[str, Any]) -> dict[str, Any]:
        recruiting = hr.get("recruiting")
        if not isinstance(recruiting, dict):
            raise PeopleError("Recruiting-Demodaten fehlen")
        return recruiting

    @staticmethod
    def _payroll(hr: dict[str, Any]) -> dict[str, Any]:
        payroll = hr.get("payroll")
        if not isinstance(payroll, dict):
            raise PeopleError("Payroll-Demodaten fehlen")
        return payroll

    @staticmethod
    def _application(recruiting: dict[str, Any], application_id: str) -> dict[str, Any]:
        item = next(
            (entry for entry in recruiting["applications"] if entry["id"] == application_id),
            None,
        )
        if not item:
            raise PeopleNotFoundError(f"Bewerbung {application_id} wurde nicht gefunden")
        return item

    @staticmethod
    def _period(payroll: dict[str, Any], period_id: str) -> dict[str, Any]:
        item = next(
            (entry for entry in payroll["periods"] if entry["id"] == period_id), None
        )
        if not item:
            raise PeopleNotFoundError(f"Abrechnungszeitraum {period_id} wurde nicht gefunden")
        return item

    @staticmethod
    def _run(payroll: dict[str, Any], run_id: str) -> dict[str, Any]:
        item = next((entry for entry in payroll.get("runs", []) if entry["id"] == run_id), None)
        if not item:
            raise PeopleNotFoundError(f"Abrechnungslauf {run_id} wurde nicht gefunden")
        return item

    @staticmethod
    def _next_id(items: list[dict[str, Any]], prefix: str) -> str:
        numbers = []
        for item in items:
            try:
                numbers.append(int(str(item.get("id", "")).rsplit("-", 1)[-1]))
            except ValueError:
                continue
        return f"{prefix}-{max(numbers, default=0) + 1:04d}"

    @staticmethod
    def _now(hr: dict[str, Any]) -> datetime:
        return datetime.now(ZoneInfo(hr["timezone"]))

    def _audit(
        self,
        hr: dict[str, Any],
        actor_id: str,
        subject_id: str,
        action: str,
        message: str,
    ) -> None:
        hr.setdefault("audit", []).append(
            {
                "id": self._next_id(hr.get("audit", []), "HR-AUD"),
                "timestamp": self._now(hr).isoformat(timespec="seconds"),
                "actor_id": actor_id,
                "employee_id": subject_id,
                "action": action,
                "message": message,
            }
        )


def render_payslip_pdf(run: dict[str, Any], row: dict[str, Any], company: str) -> bytes:
    """Create a readable, inline-safe demo payslip PDF."""

    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    normal = styles["BodyText"]
    normal.fontName = _pdf_font()
    normal.fontSize = 9
    normal.leading = 12
    heading = ParagraphStyle(
        "Heading",
        parent=styles["Heading1"],
        fontName=_pdf_font(),
        fontSize=19,
        leading=23,
        textColor=colors.HexColor("#173f5f"),
        spaceAfter=3 * mm,
    )
    right = ParagraphStyle("Right", parent=normal, alignment=TA_RIGHT)
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=17 * mm,
        title=f"Entgeltabrechnung {run['period_id']} {row['employee_name']}",
        author=company,
    )
    story: list[Any] = [
        Table(
            [
                [Paragraph(company, heading), Paragraph("FLOWHR", right)],
                [
                    Paragraph("Entgeltabrechnung - Demonstrationsbeleg", heading),
                    Paragraph(f"Lauf {run['id']}", right),
                ],
            ],
            colWidths=[125 * mm, 45 * mm],
        ),
        Spacer(1, 4 * mm),
        Table(
            [
                ["Abrechnungszeitraum", run["period_id"], "Mitarbeiter-Nr.", row["employee_id"]],
                ["Beschäftigte/r", row["employee_name"], "Abteilung", row["department"]],
                ["Steuerklasse", row["tax_class"], "Krankenkasse", row["health_insurance"]],
                ["Bankverbindung", row["bank_account_masked"], "Währung", "EUR"],
            ],
            colWidths=[37 * mm, 48 * mm, 37 * mm, 48 * mm],
            style=_detail_style(),
        ),
        Spacer(1, 7 * mm),
        Paragraph("Bezüge", styles["Heading2"]),
        _money_table(row["earnings"], "Gesamtbrutto", row["gross_cents"]),
        Spacer(1, 6 * mm),
        Paragraph("Abzüge", styles["Heading2"]),
        _money_table(row["deductions"], "Abzüge gesamt", row["deduction_cents"]),
        Spacer(1, 7 * mm),
        Table(
            [["Auszahlungsbetrag", _euro(row["net_cents"])]],
            colWidths=[125 * mm, 45 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#173f5f")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                    ("FONTNAME", (0, 0), (-1, -1), _pdf_font()),
                    ("FONTSIZE", (0, 0), (-1, -1), 13),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ]
            ),
        ),
        Spacer(1, 12 * mm),
        Paragraph(
            "Demonstrationsbeleg - nicht zur Auszahlung oder für gesetzliche Meldungen. "
            "Die Beträge stammen aus versionierten Testwerten; ELStAM-, DEÜV-, eAU- und "
            "Zahlungsübergaben sind in dieser Demo nicht produktiv freigeschaltet.",
            ParagraphStyle(
                "Notice",
                parent=normal,
                borderColor=colors.HexColor("#d59f00"),
                borderWidth=0.7,
                borderPadding=8,
                backColor=colors.HexColor("#fff8df"),
                textColor=colors.HexColor("#5c4300"),
            ),
        ),
        Spacer(1, 5 * mm),
        Paragraph(
            f"Vorbereitet durch {run['prepared_by']} · freigegeben durch "
            f"{run['approved_by']} am {run['approved_at']}",
            normal,
        ),
    ]

    def footer(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont(_pdf_font(), 8)
        canvas.setFillColor(colors.HexColor("#65717b"))
        canvas.drawString(18 * mm, 10 * mm, f"{company} · vertraulich · {run['id']}")
        canvas.drawRightString(192 * mm, 10 * mm, f"Seite {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


@lru_cache(maxsize=1)
def _pdf_font() -> str:
    name = "Helvetica"
    try:
        pdfmetrics.getFont("DejaVuSans")
        return "DejaVuSans"
    except KeyError:
        pass
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ):
        try:
            pdfmetrics.registerFont(TTFont("DejaVuSans", path))
            return "DejaVuSans"
        except (OSError, TTFError, ValueError):
            continue
    return name


def _detail_style() -> TableStyle:
    return TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, -1), _pdf_font()),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#56616a")),
            ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#56616a")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d9dee2")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f5f7")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f2f5f7")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )


def _money_table(lines: list[dict[str, Any]], total_label: str, total_cents: int) -> Table:
    rows = [["Lohnart", "Bezeichnung", "Betrag"]]
    rows.extend(
        [[item["code"], item["label"], _euro(item["amount_cents"])] for item in lines]
    )
    rows.append(["", total_label, _euro(total_cents)])
    return Table(
        rows,
        colWidths=[30 * mm, 95 * mm, 45 * mm],
        repeatRows=1,
        style=TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), _pdf_font()),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#173f5f")),
                ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, -2), 0.35, colors.HexColor("#d9dee2")),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#173f5f")),
                ("FONTNAME", (0, -1), (-1, -1), _pdf_font()),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        ),
    )


def _euro(cents: int) -> str:
    value = cents / 100
    return f"{value:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")
