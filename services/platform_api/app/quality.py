from __future__ import annotations

import hashlib
import math
from copy import deepcopy
from datetime import UTC, date, datetime
from typing import Any, Protocol

from .config import Settings
from .erpnext_client import ERPNextClient, ERPNextError
from .store import ScenarioStore, utc_now


class QualityError(RuntimeError):
    """A validation or workflow error suitable for the FLOWQ API."""


class QualityNotFoundError(QualityError):
    """The requested FLOWQ object does not exist."""


class QualityErpClient(Protocol):
    @property
    def configured(self) -> bool: ...

    def create_document(self, doctype: str, values: dict[str, Any]) -> dict[str, Any]: ...


class QualityService:
    """Incoming inspection workflow around ERPNext, FLOWWORK and FLOWDOC.

    FLOWQ owns the operator workflow and measurement ingestion. ERPNext remains
    the system of record for the receipt and Quality Inspection. The demo keeps
    this boundary visible by preparing an ERP payload and synchronising it only
    through the explicit sync action.
    """

    SOURCES = {"manual", "rest", "mqtt", "opcua", "serial", "usb"}

    def __init__(
        self,
        store: ScenarioStore,
        settings: Settings,
        erp_client: QualityErpClient | None = None,
    ) -> None:
        self.store = store
        self.settings = settings
        self.erp_client = erp_client or ERPNextClient(settings)

    def dashboard(self, operator_id: str | None = None) -> dict[str, Any]:
        state = self.store.get()
        quality = self._domain(state)
        operator = self._operator(quality, operator_id or quality["operators"][0]["id"])
        receipts = [self._receipt_view(quality, item) for item in quality["receipts"]]
        inspections = [
            self._inspection_view(quality, item) for item in quality["inspections"]
        ]
        completed = [item for item in inspections if item["status"] == "completed"]
        accepted = [item for item in completed if item["decision"] == "accepted"]
        calibration_due = [
            item for item in quality["instruments"] if self._calibration_state(item) != "valid"
        ]
        return {
            "product": "FLOWQ",
            "operator": deepcopy(operator),
            "operators": deepcopy(quality["operators"]),
            "metrics": {
                "open_receipts": len(
                    [item for item in receipts if item["status"] in {"awaiting_inspection", "in_progress"}]
                ),
                "active_inspections": len(
                    [item for item in inspections if item["status"] == "in_progress"]
                ),
                "blocked_lots": len([item for item in receipts if item["status"] == "rejected"]),
                "acceptance_rate": round(len(accepted) / len(completed) * 100) if completed else 100,
                "calibration_due": len(calibration_due),
            },
            "receipts": receipts,
            "inspections": inspections,
            "plans": deepcopy(quality["inspection_plans"]),
            "sampling_plans": deepcopy(quality["sampling_plans"]),
            "instruments": [self._instrument_view(item) for item in quality["instruments"]],
            "adapters": deepcopy(quality.get("adapters", [])),
            "interfaces": self.interfaces(),
            "ncrs": deepcopy(quality["ncrs"]),
            "audit": list(reversed(deepcopy(quality["audit"][-20:]))),
            "erp": {
                "configured": self.erp_client.configured,
                "mode": "live-ready" if self.erp_client.configured else "demo-adapter",
            },
        }

    def interfaces(self) -> dict[str, Any]:
        return {
            "version": "v1",
            "authentication": "Keycloak OIDC oder technischer Client mit quality-user",
            "measurement_endpoint": "/api/quality/v1/measurements",
            "openapi": "/docs",
            "protocols": [
                {"key": "rest", "label": "REST / JSON", "mode": "native"},
                {"key": "mqtt", "label": "MQTT", "mode": "gateway-adapter"},
                {"key": "opcua", "label": "OPC UA", "mode": "gateway-adapter"},
                {"key": "serial", "label": "Seriell / USB", "mode": "edge-gateway"},
            ],
            "event_schema": {
                "required": [
                    "inspection_id",
                    "characteristic_id",
                    "sample_ref",
                    "instrument_id",
                    "value",
                    "unit",
                    "external_event_id",
                ],
                "idempotency": "external_event_id",
            },
        }

    def reset(self, operator_id: str | None = None) -> dict[str, Any]:
        self.store.reset_domain("quality")
        return self.dashboard(operator_id)

    def start_inspection(self, receipt_id: str, operator_id: str) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def operation(state: dict[str, Any]) -> None:
            nonlocal result
            quality = self._domain(state)
            operator = self._operator(quality, operator_id)
            receipt = self._find(quality["receipts"], receipt_id, "Wareneingang")
            existing = next(
                (
                    item
                    for item in quality["inspections"]
                    if item["receipt_id"] == receipt_id and item["status"] == "in_progress"
                ),
                None,
            )
            if existing:
                result = self._inspection_view(quality, existing)
                return
            if receipt["status"] not in {"awaiting_inspection", "reinspection"}:
                raise QualityError("Dieser Wareneingang ist nicht prüfbereit")
            plan = self._find(
                quality["inspection_plans"], receipt["inspection_plan_id"], "Prüfplan"
            )
            if plan["status"] != "approved":
                raise QualityError("Nur freigegebene Prüfpläne dürfen ausgeführt werden")
            sampling = self._find(
                quality["sampling_plans"], plan["sampling_plan_id"], "Stichprobenplan"
            )
            sample_size, acceptance_number, rejection_number = self._sample_rule(
                sampling, receipt["quantity_received"]
            )
            sequence = len(quality["inspections"]) + 1
            inspection = {
                "id": f"QI-IN-{datetime.now(UTC).year}-{sequence:04d}",
                "receipt_id": receipt_id,
                "inspection_plan_id": plan["id"],
                "plan_revision": plan["revision"],
                "work_test_plan_id": plan.get("work_test_plan_id"),
                "dms_document_id": plan.get("dms_document_id"),
                "sampling_plan_id": sampling["id"],
                "sample_size": sample_size,
                "acceptance_number": acceptance_number,
                "rejection_number": rejection_number,
                "sample_refs": self._select_samples(receipt, sample_size),
                "measurements": [],
                "operator_id": operator["id"],
                "operator_name": operator["name"],
                "status": "in_progress",
                "decision": None,
                "started_at": utc_now(),
                "completed_at": None,
                "erp_sync": {"status": "not_ready", "mode": "preview"},
            }
            quality["inspections"].append(inspection)
            receipt["status"] = "in_progress"
            self._audit(quality, operator["name"], "inspection_started", inspection["id"])
            result = self._inspection_view(quality, inspection)

        self.store.mutate(operation)
        return result

    def record_measurement(
        self,
        inspection_id: str,
        values: dict[str, Any],
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def operation(state: dict[str, Any]) -> None:
            nonlocal result
            quality = self._domain(state)
            inspection = self._find(quality["inspections"], inspection_id, "Prüfung")
            if inspection["status"] != "in_progress":
                raise QualityError("Messwerte können nur in laufenden Prüfungen erfasst werden")
            plan = self._find(
                quality["inspection_plans"], inspection["inspection_plan_id"], "Prüfplan"
            )
            characteristic = self._find(
                plan["characteristics"], values.get("characteristic_id", ""), "Prüfmerkmal"
            )
            sample_ref = str(values.get("sample_ref", "")).strip()
            if sample_ref not in inspection["sample_refs"]:
                raise QualityError("Die Probennummer gehört nicht zu dieser Stichprobe")
            source = str(values.get("source", "manual")).casefold()
            if source not in self.SOURCES:
                raise QualityError("Unbekannte Messwertquelle")
            external_event_id = str(values.get("external_event_id") or "").strip()
            if external_event_id:
                duplicate = next(
                    (
                        item
                        for item in quality["measurement_events"]
                        if item.get("external_event_id") == external_event_id
                    ),
                    None,
                )
                if duplicate:
                    result = {**deepcopy(duplicate), "idempotent_replay": True}
                    return
            instrument_id = str(values.get("instrument_id") or "").strip()
            instrument = None
            if characteristic.get("instrument_required") and not instrument_id:
                raise QualityError("Für dieses Prüfmerkmal ist ein Messmittel erforderlich")
            if instrument_id:
                instrument = self._find(quality["instruments"], instrument_id, "Messmittel")
                if self._calibration_state(instrument) != "valid":
                    raise QualityError("Das Messmittel ist gesperrt oder nicht gültig kalibriert")
                allowed = characteristic.get("instrument_types", [])
                if allowed and instrument["type"] not in allowed:
                    raise QualityError("Das Messmittel ist für dieses Prüfmerkmal nicht zugelassen")
            unit = str(values.get("unit") or characteristic.get("unit") or "").strip()
            expected_unit = str(characteristic.get("unit") or "").strip()
            if expected_unit and unit != expected_unit:
                raise QualityError(f"Einheit muss {expected_unit} sein")
            passed, normalized = self._evaluate(characteristic, values.get("value"))
            event = {
                "id": f"MEAS-{len(quality['measurement_events']) + 1:06d}",
                "external_event_id": external_event_id or None,
                "inspection_id": inspection_id,
                "characteristic_id": characteristic["id"],
                "characteristic_name": characteristic["name"],
                "sample_ref": sample_ref,
                "value": normalized,
                "unit": unit,
                "status": "passed" if passed else "failed",
                "instrument_id": instrument_id or None,
                "instrument_name": instrument.get("name") if instrument else None,
                "calibration_valid_until": instrument.get("calibration_valid_until") if instrument else None,
                "source": source,
                "measured_at": str(values.get("measured_at") or utc_now()),
                "received_at": utc_now(),
                "actor": actor_id or inspection["operator_id"],
            }
            previous = next(
                (
                    item
                    for item in reversed(inspection["measurements"])
                    if item["sample_ref"] == sample_ref
                    and item["characteristic_id"] == characteristic["id"]
                    and item.get("active", True)
                ),
                None,
            )
            if previous:
                previous["active"] = False
                event["supersedes"] = previous["id"]
            event["active"] = True
            inspection["measurements"].append(event)
            quality["measurement_events"].append(deepcopy(event))
            self._audit(quality, event["actor"], "measurement_recorded", event["id"])
            result = deepcopy(event)

        self.store.mutate(operation)
        return result

    def complete_inspection(self, inspection_id: str, actor_id: str) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def operation(state: dict[str, Any]) -> None:
            nonlocal result
            quality = self._domain(state)
            inspection = self._find(quality["inspections"], inspection_id, "Prüfung")
            if inspection["status"] != "in_progress":
                raise QualityError("Nur eine laufende Prüfung kann abgeschlossen werden")
            plan = self._find(
                quality["inspection_plans"], inspection["inspection_plan_id"], "Prüfplan"
            )
            required = [item for item in plan["characteristics"] if item.get("required", True)]
            active = [item for item in inspection["measurements"] if item.get("active", True)]
            measured = {(item["sample_ref"], item["characteristic_id"]) for item in active}
            missing = [
                f"{sample} / {item['name']}"
                for sample in inspection["sample_refs"]
                for item in required
                if (sample, item["id"]) not in measured
            ]
            if missing:
                raise QualityError(
                    f"Noch {len(missing)} Pflichtmessungen offen; zuerst {missing[0]}"
                )
            failed_samples = sorted(
                {
                    item["sample_ref"]
                    for item in active
                    if item["status"] == "failed"
                }
            )
            accepted = len(failed_samples) <= inspection["acceptance_number"]
            inspection["status"] = "completed"
            inspection["decision"] = "accepted" if accepted else "rejected"
            inspection["failed_samples"] = failed_samples
            inspection["completed_at"] = utc_now()
            inspection["completed_by"] = actor_id
            receipt = self._find(quality["receipts"], inspection["receipt_id"], "Wareneingang")
            receipt["status"] = inspection["decision"]
            receipt["target_warehouse"] = (
                receipt["accepted_warehouse"] if accepted else receipt["rejected_warehouse"]
            )
            if not accepted:
                ncr = {
                    "id": f"NCR-WE-{len(quality['ncrs']) + 1:04d}",
                    "inspection_id": inspection_id,
                    "receipt_id": receipt["id"],
                    "supplier": receipt["supplier"],
                    "item_code": receipt["item_code"],
                    "failed_samples": failed_samples,
                    "status": "open",
                    "created_at": utc_now(),
                }
                quality["ncrs"].append(ncr)
                inspection["ncr_id"] = ncr["id"]
            payload = self._erp_payload(quality, inspection, receipt, plan)
            inspection["erp_sync"] = {
                "status": "pending",
                "mode": "live-ready" if self.erp_client.configured else "simulated",
                "doctype": "Quality Inspection",
                "payload": payload,
                "target_warehouse": receipt["target_warehouse"],
                "erp_reference": None,
            }
            inspection["dms_protocol"] = {
                "status": "prepared",
                "document_type": "Wareneingangsprüfprotokoll",
                "reference": inspection_id,
                "metadata": {
                    "purchase_receipt": receipt["id"],
                    "batch": receipt.get("batch"),
                    "project": receipt.get("project_id"),
                    "plan_revision": inspection["plan_revision"],
                },
            }
            self._audit(quality, actor_id, "inspection_completed", inspection_id)
            result = self._inspection_view(quality, inspection)

        self.store.mutate(operation)
        return result

    def sync_to_erp(self, inspection_id: str, actor_id: str, confirm: bool) -> dict[str, Any]:
        state = self.store.get()
        quality = self._domain(state)
        inspection = self._find(quality["inspections"], inspection_id, "Prüfung")
        sync = inspection.get("erp_sync") or {}
        if inspection["status"] != "completed" or not sync.get("payload"):
            raise QualityError("Die Prüfung ist noch nicht für die ERP-Übergabe bereit")
        if not confirm:
            return {"status": "preview", **deepcopy(sync)}
        if sync.get("status") == "synced":
            return deepcopy(sync)
        erp_reference = f"DEMO-{inspection_id}"
        mode = "simulated"
        if self.erp_client.configured:
            try:
                document = self.erp_client.create_document("Quality Inspection", sync["payload"])
            except ERPNextError as exc:
                raise QualityError(f"ERPNext-Übergabe fehlgeschlagen: {exc}") from exc
            erp_reference = str(document["name"])
            mode = "live"

        result: dict[str, Any] = {}

        def operation(current: dict[str, Any]) -> None:
            nonlocal result
            domain = self._domain(current)
            item = self._find(domain["inspections"], inspection_id, "Prüfung")
            item["erp_sync"].update(
                {
                    "status": "synced",
                    "mode": mode,
                    "erp_reference": erp_reference,
                    "synced_at": utc_now(),
                    "synced_by": actor_id,
                }
            )
            self._audit(domain, actor_id, "erp_quality_inspection_synced", erp_reference)
            result = deepcopy(item["erp_sync"])

        self.store.mutate(operation)
        return result

    def calibrate_instrument(
        self,
        instrument_id: str,
        actor_id: str,
        calibrated_at: str,
        valid_until: str,
        certificate_document_id: str,
    ) -> dict[str, Any]:
        try:
            calibrated = date.fromisoformat(calibrated_at)
            valid = date.fromisoformat(valid_until)
        except ValueError as exc:
            raise QualityError("Kalibrierdaten müssen YYYY-MM-DD verwenden") from exc
        if valid <= calibrated:
            raise QualityError("Das Gültigkeitsende muss nach der Kalibrierung liegen")
        result: dict[str, Any] = {}

        def operation(state: dict[str, Any]) -> None:
            nonlocal result
            quality = self._domain(state)
            instrument = self._find(quality["instruments"], instrument_id, "Messmittel")
            instrument["last_calibrated_at"] = calibrated.isoformat()
            instrument["calibration_valid_until"] = valid.isoformat()
            instrument["calibration_certificate_document_id"] = certificate_document_id
            instrument["status"] = "active"
            self._audit(quality, actor_id, "instrument_calibrated", instrument_id)
            result = self._instrument_view(instrument)

        self.store.mutate(operation)
        return result

    @staticmethod
    def _sample_rule(sampling: dict[str, Any], quantity: int) -> tuple[int, int, int]:
        mode = sampling["mode"]
        if mode == "full":
            size = quantity
            acceptance = 0
        elif mode == "percentage":
            size = max(sampling.get("minimum", 1), math.ceil(quantity * sampling["percent"] / 100))
            size = min(size, sampling.get("maximum", quantity), quantity)
            acceptance = sampling.get("acceptance_number", 0)
        elif mode == "fixed":
            size = min(quantity, sampling["sample_size"])
            acceptance = sampling.get("acceptance_number", 0)
        elif mode == "aql":
            rule = next(
                (
                    item
                    for item in sampling["lot_ranges"]
                    if item["min"] <= quantity <= item["max"]
                ),
                sampling["lot_ranges"][-1],
            )
            size = min(quantity, rule["sample_size"])
            acceptance = rule["acceptance_number"]
            return size, acceptance, rule["rejection_number"]
        else:
            raise QualityError("Unbekanntes Stichprobenverfahren")
        return size, acceptance, acceptance + 1

    @staticmethod
    def _select_samples(receipt: dict[str, Any], size: int) -> list[str]:
        serials = [str(item) for item in receipt.get("serial_numbers", [])]
        if serials:
            candidates = serials
        else:
            batch = receipt.get("batch") or receipt["id"]
            candidates = [f"{batch} · Teil {index:03d}" for index in range(1, receipt["quantity_received"] + 1)]
        ranked = sorted(
            candidates,
            key=lambda item: hashlib.sha256(f"{receipt['id']}:{item}".encode()).hexdigest(),
        )
        return sorted(ranked[:size])

    @staticmethod
    def _evaluate(characteristic: dict[str, Any], value: Any) -> tuple[bool, Any]:
        kind = characteristic["type"]
        if kind == "numeric":
            try:
                normalized = float(value)
            except (TypeError, ValueError) as exc:
                raise QualityError("Für das numerische Prüfmerkmal ist eine Zahl erforderlich") from exc
            minimum = characteristic.get("min_value")
            maximum = characteristic.get("max_value")
            passed = (minimum is None or normalized >= minimum) and (
                maximum is None or normalized <= maximum
            )
            return passed, normalized
        if kind == "boolean":
            if isinstance(value, bool):
                normalized = value
            else:
                normalized = str(value).strip().casefold() in {
                    "true",
                    "1",
                    "ja",
                    "bestanden",
                    "ok",
                    "pass",
                }
            return normalized == bool(characteristic.get("expected", True)), normalized
        normalized = str(value or "").strip()
        if not normalized:
            raise QualityError("Ein Prüfergebnis ist erforderlich")
        allowed = [str(item).casefold() for item in characteristic.get("allowed_values", [])]
        return not allowed or normalized.casefold() in allowed, normalized

    def _erp_payload(
        self,
        quality: dict[str, Any],
        inspection: dict[str, Any],
        receipt: dict[str, Any],
        plan: dict[str, Any],
    ) -> dict[str, Any]:
        active = [item for item in inspection["measurements"] if item.get("active", True)]
        readings: list[dict[str, Any]] = []
        for characteristic in plan["characteristics"]:
            values = [
                item
                for sample in inspection["sample_refs"]
                for item in active
                if item["sample_ref"] == sample
                and item["characteristic_id"] == characteristic["id"]
            ]
            row: dict[str, Any] = {
                "specification": characteristic["name"],
                "status": "Accepted" if all(item["status"] == "passed" for item in values) else "Rejected",
            }
            if characteristic["type"] == "numeric":
                row.update(
                    {
                        "numeric": 1,
                        "min_value": characteristic.get("min_value"),
                        "max_value": characteristic.get("max_value"),
                    }
                )
                for index, item in enumerate(values[:10], start=1):
                    row[f"reading_{index}"] = item["value"]
            else:
                row.update({"numeric": 0, "reading_value": ", ".join(str(item["value"]) for item in values)})
            readings.append(row)
        return {
            "inspection_type": "Incoming",
            "reference_type": "Purchase Receipt",
            "reference_name": receipt["erp_reference"],
            "item_code": receipt["item_code"],
            "sample_size": inspection["sample_size"],
            "report_date": date.today().isoformat(),
            "status": "Accepted" if inspection["decision"] == "accepted" else "Rejected",
            "remarks": (
                f"FLOWQ {inspection['id']} · Prüfplan {plan['id']} Rev. {plan['revision']} · "
                f"DMS {plan.get('dms_document_id') or '-'} · FLOWWORK {plan.get('work_test_plan_id') or '-'}"
            ),
            "readings": readings,
        }

    def _inspection_view(self, quality: dict[str, Any], inspection: dict[str, Any]) -> dict[str, Any]:
        plan = self._find(quality["inspection_plans"], inspection["inspection_plan_id"], "Prüfplan")
        receipt = self._find(quality["receipts"], inspection["receipt_id"], "Wareneingang")
        active = [item for item in inspection["measurements"] if item.get("active", True)]
        required_count = len(inspection["sample_refs"]) * len(
            [item for item in plan["characteristics"] if item.get("required", True)]
        )
        return {
            **deepcopy(inspection),
            "receipt": deepcopy(receipt),
            "plan": deepcopy(plan),
            "measurements": deepcopy(active),
            "measurement_progress": {
                "completed": len(active),
                "required": required_count,
                "percent": round(len(active) / required_count * 100) if required_count else 100,
            },
        }

    def _receipt_view(self, quality: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
        plan = self._find(quality["inspection_plans"], receipt["inspection_plan_id"], "Prüfplan")
        active = next(
            (
                self._inspection_view(quality, item)
                for item in quality["inspections"]
                if item["receipt_id"] == receipt["id"] and item["status"] == "in_progress"
            ),
            None,
        )
        return {**deepcopy(receipt), "plan": deepcopy(plan), "active_inspection": active}

    def _instrument_view(self, instrument: dict[str, Any]) -> dict[str, Any]:
        return {**deepcopy(instrument), "calibration_state": self._calibration_state(instrument)}

    @staticmethod
    def _calibration_state(instrument: dict[str, Any]) -> str:
        if instrument.get("status") != "active":
            return "blocked"
        try:
            valid_until = date.fromisoformat(instrument["calibration_valid_until"])
        except (KeyError, TypeError, ValueError):
            return "missing"
        days = (valid_until - date.today()).days
        if days < 0:
            return "expired"
        if days <= 30:
            return "due"
        return "valid"

    @staticmethod
    def _operator(quality: dict[str, Any], operator_id: str) -> dict[str, Any]:
        return QualityService._find(quality["operators"], operator_id, "Prüfer")

    @staticmethod
    def _domain(state: dict[str, Any]) -> dict[str, Any]:
        quality = state.get("quality")
        if not isinstance(quality, dict):
            raise QualityError("FLOWQ-Demodaten sind nicht initialisiert")
        return quality

    @staticmethod
    def _find(items: list[dict[str, Any]], item_id: str, label: str) -> dict[str, Any]:
        item = next((candidate for candidate in items if candidate.get("id") == item_id), None)
        if item is None:
            raise QualityNotFoundError(f"{label} {item_id} wurde nicht gefunden")
        return item

    @staticmethod
    def _audit(quality: dict[str, Any], actor: str, action: str, reference: str) -> None:
        quality["audit"].append(
            {"actor": actor, "action": action, "reference": reference, "at": utc_now()}
        )
