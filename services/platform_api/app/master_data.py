from __future__ import annotations

import csv
import io
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .config import Settings
from .erpnext_client import ERPNextClient, ERPNextError


class MasterDataError(ValueError):
    """Validation or policy error for MCP master-data tools."""


class DocumentClient(Protocol):
    configured: bool

    def find_document(self, doctype: str, field: str, value: object) -> str | None: ...

    def create_document(self, doctype: str, values: dict[str, Any]) -> dict[str, Any]: ...

    def delete_document(self, doctype: str, name: str) -> None: ...


@dataclass(frozen=True)
class NestedSpec:
    fields: tuple[str, ...]
    required: tuple[str, ...] = ()
    one_of: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class EntitySpec:
    doctype: str
    label: str
    category: str
    identity_field: str
    required: tuple[str, ...]
    fields: tuple[str, ...]
    defaults: dict[str, Any] = field(default_factory=dict)
    nested: dict[str, NestedSpec] = field(default_factory=dict)
    integer_fields: tuple[str, ...] = ()
    float_fields: tuple[str, ...] = ()
    example: dict[str, Any] = field(default_factory=dict)


def _catalog(company: str) -> dict[str, EntitySpec]:
    return {
        "employees": EntitySpec(
            "Employee",
            "Mitarbeiter",
            "Personal",
            "employee_number",
            ("first_name", "gender", "date_of_birth", "date_of_joining", "company"),
            (
                "employee_number",
                "first_name",
                "middle_name",
                "last_name",
                "gender",
                "date_of_birth",
                "date_of_joining",
                "status",
                "company",
                "department",
                "designation",
                "company_email",
                "personal_email",
                "cell_number",
                "reports_to",
                "branch",
                "create_user_automatically",
                "create_user_permission",
            ),
            defaults={
                "company": company,
                "status": "Active",
                "create_user_automatically": 0,
                "create_user_permission": 0,
            },
            integer_fields=("create_user_automatically", "create_user_permission"),
            example={
                "employee_number": "TEST-EMP-001",
                "first_name": "Erika",
                "last_name": "Muster",
                "gender": "Female",
                "date_of_birth": "1990-05-12",
                "date_of_joining": "2026-01-01",
            },
        ),
        "timesheets": EntitySpec(
            "Timesheet",
            "Arbeitszeitnachweise",
            "Personal/Projekte",
            "",
            ("time_logs",),
            ("naming_series", "employee", "company", "time_logs", "note"),
            defaults={"naming_series": "TS-.YYYY.-", "company": company},
            nested={
                "time_logs": NestedSpec(
                    (
                        "activity_type",
                        "from_time",
                        "to_time",
                        "hours",
                        "description",
                        "project",
                        "task",
                        "completed",
                        "is_billable",
                        "billing_hours",
                        "billing_rate",
                        "costing_rate",
                    ),
                    required=("activity_type", "from_time"),
                    one_of=(("to_time", "hours"),),
                )
            },
            example={
                "employee": "HR-EMP-00001",
                "time_logs": [
                    {
                        "activity_type": "Fertigung",
                        "from_time": "2026-10-30 08:00:00",
                        "to_time": "2026-10-30 16:00:00",
                        "description": "Test-Arbeitszeit",
                    }
                ],
            },
        ),
        "workstations": EntitySpec(
            "Workstation",
            "Arbeitsplätze",
            "Fertigung",
            "workstation_name",
            ("workstation_name", "production_capacity"),
            (
                "workstation_name",
                "workstation_type",
                "plant_floor",
                "production_capacity",
                "warehouse",
                "status",
                "hour_rate",
                "description",
                "holiday_list",
                "working_hours",
                "disabled",
            ),
            defaults={"production_capacity": 1, "status": "Production", "disabled": 0},
            nested={
                "working_hours": NestedSpec(
                    ("start_time", "end_time", "hours"), required=("start_time", "end_time")
                )
            },
            integer_fields=("production_capacity", "disabled"),
            float_fields=("hour_rate",),
            example={
                "workstation_name": "TEST-MONTAGE-02",
                "production_capacity": 2,
                "working_hours": [{"start_time": "08:00:00", "end_time": "16:30:00"}],
            },
        ),
        "workstation_types": EntitySpec(
            "Workstation Type",
            "Arbeitsplatztypen",
            "Fertigung",
            "workstation_type",
            ("workstation_type",),
            ("workstation_type", "hour_rate", "description"),
            float_fields=("hour_rate",),
            example={"workstation_type": "TEST-Montage", "hour_rate": 72.5},
        ),
        "plant_floors": EntitySpec(
            "Plant Floor",
            "Werkshallen",
            "Fertigung",
            "floor_name",
            ("floor_name",),
            ("floor_name", "company", "warehouse"),
            defaults={"company": company},
            example={"floor_name": "TEST-Halle 2"},
        ),
        "operations": EntitySpec(
            "Operation",
            "Arbeitsgänge",
            "Fertigung",
            "operation",
            ("operation",),
            ("operation", "default_workstation", "workstation", "description"),
            example={"operation": "TEST-Endmontage", "default_workstation": "MONT-01"},
        ),
        "suppliers": EntitySpec(
            "Supplier",
            "Lieferanten",
            "Einkauf",
            "supplier_name",
            ("supplier_name", "supplier_type"),
            (
                "supplier_name",
                "supplier_type",
                "supplier_group",
                "country",
                "tax_id",
                "website",
                "supplier_details",
                "default_currency",
                "disabled",
            ),
            defaults={
                "supplier_type": "Company",
                "supplier_group": "All Supplier Groups",
                "disabled": 0,
            },
            integer_fields=("disabled",),
            example={
                "supplier_name": "TEST-Lieferant GmbH",
                "country": "Germany",
                "supplier_group": "All Supplier Groups",
            },
        ),
        "supplier_groups": EntitySpec(
            "Supplier Group",
            "Lieferantengruppen",
            "Einkauf",
            "supplier_group_name",
            ("supplier_group_name",),
            ("supplier_group_name", "parent_supplier_group", "is_group"),
            defaults={"parent_supplier_group": "All Supplier Groups", "is_group": 0},
            integer_fields=("is_group",),
            example={"supplier_group_name": "TEST-Elektroniklieferanten"},
        ),
        "customers": EntitySpec(
            "Customer",
            "Kunden",
            "Vertrieb",
            "customer_name",
            ("customer_name", "customer_type"),
            (
                "customer_name",
                "customer_type",
                "customer_group",
                "territory",
                "tax_id",
                "website",
                "customer_details",
                "default_currency",
                "disabled",
            ),
            defaults={
                "customer_type": "Company",
                "customer_group": "All Customer Groups",
                "territory": "All Territories",
                "disabled": 0,
            },
            integer_fields=("disabled",),
            example={"customer_name": "TEST-Kunde GmbH", "territory": "Germany"},
        ),
        "customer_groups": EntitySpec(
            "Customer Group",
            "Kundengruppen",
            "Vertrieb",
            "customer_group_name",
            ("customer_group_name",),
            ("customer_group_name", "parent_customer_group", "is_group"),
            defaults={"parent_customer_group": "All Customer Groups", "is_group": 0},
            integer_fields=("is_group",),
            example={"customer_group_name": "TEST-Industriekunden"},
        ),
        "territories": EntitySpec(
            "Territory",
            "Vertriebsgebiete",
            "Vertrieb",
            "territory_name",
            ("territory_name",),
            ("territory_name", "parent_territory", "is_group"),
            defaults={"parent_territory": "All Territories", "is_group": 0},
            integer_fields=("is_group",),
            example={"territory_name": "TEST-Nord"},
        ),
        "items": EntitySpec(
            "Item",
            "Artikel",
            "Lager/Fertigung",
            "item_code",
            ("item_code", "item_group", "stock_uom"),
            (
                "item_code",
                "item_name",
                "description",
                "item_group",
                "stock_uom",
                "is_stock_item",
                "is_sales_item",
                "is_purchase_item",
                "include_item_in_manufacturing",
                "valuation_rate",
                "disabled",
            ),
            defaults={
                "item_group": "All Item Groups",
                "stock_uom": "Nos",
                "is_stock_item": 1,
                "is_sales_item": 0,
                "is_purchase_item": 1,
                "include_item_in_manufacturing": 1,
                "disabled": 0,
            },
            integer_fields=(
                "is_stock_item",
                "is_sales_item",
                "is_purchase_item",
                "include_item_in_manufacturing",
                "disabled",
            ),
            float_fields=("valuation_rate",),
            example={"item_code": "TEST-PART-001", "item_name": "Testbauteil"},
        ),
        "item_groups": EntitySpec(
            "Item Group",
            "Artikelgruppen",
            "Lager/Fertigung",
            "item_group_name",
            ("item_group_name",),
            ("item_group_name", "parent_item_group", "is_group"),
            defaults={"parent_item_group": "All Item Groups", "is_group": 0},
            integer_fields=("is_group",),
            example={"item_group_name": "TEST-Bauteile"},
        ),
        "warehouses": EntitySpec(
            "Warehouse",
            "Lager",
            "Lager/Fertigung",
            "warehouse_name",
            ("warehouse_name", "company"),
            ("warehouse_name", "company", "parent_warehouse", "is_group", "disabled"),
            defaults={"company": company, "is_group": 0, "disabled": 0},
            integer_fields=("is_group", "disabled"),
            example={"warehouse_name": "TEST-Pufferlager"},
        ),
        "departments": EntitySpec(
            "Department",
            "Abteilungen",
            "Organisation",
            "department_name",
            ("department_name", "company"),
            ("department_name", "company", "parent_department", "is_group", "disabled"),
            defaults={
                "company": company,
                "parent_department": "All Departments",
                "is_group": 0,
                "disabled": 0,
            },
            integer_fields=("is_group", "disabled"),
            example={"department_name": "TEST-Prozessentwicklung"},
        ),
        "designations": EntitySpec(
            "Designation",
            "Stellenbezeichnungen",
            "Organisation",
            "designation_name",
            ("designation_name",),
            ("designation_name", "description"),
            example={"designation_name": "TEST-Fertigungsplaner"},
        ),
        "branches": EntitySpec(
            "Branch",
            "Niederlassungen",
            "Organisation",
            "branch",
            ("branch",),
            ("branch",),
            example={"branch": "TEST-Werk Nord"},
        ),
        "projects": EntitySpec(
            "Project",
            "Projekte",
            "Projekte",
            "project_name",
            ("naming_series", "project_name", "company"),
            (
                "naming_series",
                "project_name",
                "company",
                "status",
                "priority",
                "department",
                "expected_start_date",
                "expected_end_date",
                "customer",
                "notes",
            ),
            defaults={"naming_series": "PROJ-.####", "company": company, "status": "Open"},
            example={"project_name": "TEST-Anlauf Produkt B", "priority": "Medium"},
        ),
        "activity_types": EntitySpec(
            "Activity Type",
            "Tätigkeitsarten",
            "Projekte/Arbeitszeit",
            "activity_type",
            ("activity_type",),
            ("activity_type", "costing_rate", "billing_rate", "disabled"),
            integer_fields=("disabled",),
            float_fields=("costing_rate", "billing_rate"),
            example={"activity_type": "TEST-Fertigung", "costing_rate": 65.0},
        ),
        "holiday_lists": EntitySpec(
            "Holiday List",
            "Feiertagslisten",
            "Personal/Fertigung",
            "holiday_list_name",
            ("holiday_list_name", "from_date", "to_date"),
            ("holiday_list_name", "from_date", "to_date", "weekly_off", "holidays"),
            nested={
                "holidays": NestedSpec(("holiday_date", "description", "weekly_off"), required=("holiday_date",))
            },
            example={
                "holiday_list_name": "TEST-Feiertage 2027",
                "from_date": "2027-01-01",
                "to_date": "2027-12-31",
                "holidays": [{"holiday_date": "2027-01-01", "description": "Neujahr"}],
            },
        ),
        "uoms": EntitySpec(
            "UOM",
            "Mengeneinheiten",
            "Grunddaten",
            "uom_name",
            ("uom_name",),
            ("uom_name", "symbol", "must_be_whole_number", "enabled"),
            defaults={"enabled": 1, "must_be_whole_number": 0},
            integer_fields=("enabled", "must_be_whole_number"),
            example={"uom_name": "TEST-Pack", "symbol": "TP"},
        ),
        "genders": EntitySpec(
            "Gender",
            "Geschlechter",
            "Grunddaten",
            "gender",
            ("gender",),
            ("gender",),
            example={"gender": "TEST-Divers"},
        ),
    }


class AuditLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def append(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False, sort_keys=True)
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")

    def batch(self, batch_id: str) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        found: dict[str, Any] | None = None
        with self._lock, self.path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("batch_id") != batch_id:
                    continue
                if event.get("event") == "create_batch":
                    found = event
                elif event.get("event") == "rollback_batch" and found is not None:
                    found = {**found, "rolled_back": True, "rollback": event}
        return found


class MasterDataService:
    def __init__(
        self,
        settings: Settings,
        client: DocumentClient | None = None,
        audit: AuditLog | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or ERPNextClient(settings)
        self.catalog = _catalog(settings.mcp_default_company)
        self.audit = audit or AuditLog(settings.mcp_audit_file)

    def list_types(self) -> dict[str, Any]:
        entities = []
        for key, spec in self.catalog.items():
            entities.append(
                {
                    "entity_type": key,
                    "label": spec.label,
                    "category": spec.category,
                    "erpnext_doctype": spec.doctype,
                    "required_fields": list(spec.required),
                    "allowed_fields": list(spec.fields),
                    "defaults": spec.defaults,
                    "example": spec.example,
                }
            )
        return {
            "tool": "list_test_data_types",
            "count": len(entities),
            "write_enabled": self.settings.mcp_write_enabled,
            "max_records_per_call": self.settings.mcp_max_write_records,
            "entities": entities,
        }

    def create(
        self,
        entity_type: str,
        records: list[dict[str, Any]],
        *,
        confirm: bool = False,
        on_duplicate: str = "skip",
        atomic: bool = True,
    ) -> dict[str, Any]:
        spec = self._spec(entity_type)
        normalized = self._normalize_records(spec, records)
        if not confirm:
            return {
                "tool": "create_test_data",
                "mode": "preview",
                "entity_type": entity_type,
                "erpnext_doctype": spec.doctype,
                "count": len(normalized),
                "records": normalized,
                "requires_confirmation": True,
                "next_step": "Call again with the same records and confirm=true.",
            }
        self._check_write_policy(on_duplicate)
        return self._write(entity_type, spec, normalized, on_duplicate, atomic)

    def import_content(
        self,
        entity_type: str,
        content: str,
        *,
        data_format: str = "csv",
        confirm: bool = False,
        on_duplicate: str = "skip",
        atomic: bool = True,
    ) -> dict[str, Any]:
        if len(content.encode("utf-8")) > 1_000_000:
            raise MasterDataError("Import content exceeds the 1 MB limit")
        records = self._parse_content(content, data_format)
        result = self.create(
            entity_type,
            records,
            confirm=confirm,
            on_duplicate=on_duplicate,
            atomic=atomic,
        )
        result["tool"] = "import_test_data"
        result["data_format"] = data_format.casefold()
        return result

    def rollback(self, batch_id: str, *, confirm: bool = False) -> dict[str, Any]:
        batch = self.audit.batch(batch_id)
        if batch is None:
            raise MasterDataError("Unknown batch_id")
        if batch.get("rolled_back"):
            return {
                "tool": "rollback_test_data_batch",
                "batch_id": batch_id,
                "status": "already_rolled_back",
            }
        documents = batch.get("created", [])
        if not confirm:
            return {
                "tool": "rollback_test_data_batch",
                "mode": "preview",
                "batch_id": batch_id,
                "documents": documents,
                "requires_confirmation": True,
            }
        self._check_write_policy("skip")
        deleted: list[dict[str, str]] = []
        errors: list[dict[str, str]] = []
        for document in reversed(documents):
            try:
                self.client.delete_document(document["doctype"], document["name"])
                deleted.append(document)
            except ERPNextError as exc:
                errors.append({**document, "error": str(exc)})
        event = {
            "event": "rollback_batch",
            "batch_id": batch_id,
            "timestamp": _now(),
            "deleted": deleted,
            "errors": errors,
        }
        self.audit.append(event)
        return {
            "tool": "rollback_test_data_batch",
            "batch_id": batch_id,
            "status": "rolled_back" if not errors else "partial",
            "deleted": deleted,
            "errors": errors,
        }

    def _write(
        self,
        entity_type: str,
        spec: EntitySpec,
        records: list[dict[str, Any]],
        on_duplicate: str,
        atomic: bool,
    ) -> dict[str, Any]:
        batch_id = str(uuid.uuid4())
        created: list[dict[str, str]] = []
        skipped: list[dict[str, str]] = []
        errors: list[dict[str, Any]] = []
        for index, record in enumerate(records):
            try:
                identity = record.get(spec.identity_field)
                existing = (
                    self.client.find_document(spec.doctype, spec.identity_field, identity)
                    if identity not in (None, "")
                    else None
                )
                if existing:
                    if on_duplicate == "error":
                        raise MasterDataError(
                            f"Duplicate {spec.identity_field}={identity!r}: {existing}"
                        )
                    skipped.append(
                        {"doctype": spec.doctype, "name": existing, "reason": "duplicate"}
                    )
                    continue
                document = self.client.create_document(spec.doctype, record)
                created.append({"doctype": spec.doctype, "name": str(document["name"])})
            except (ERPNextError, MasterDataError) as exc:
                errors.append({"record_index": index, "error": str(exc)})
                if atomic:
                    break
        rollback_errors: list[dict[str, str]] = []
        if errors and atomic:
            for document in reversed(created):
                try:
                    self.client.delete_document(document["doctype"], document["name"])
                except ERPNextError as exc:
                    rollback_errors.append({**document, "error": str(exc)})
            if not rollback_errors:
                created = []
        event = {
            "event": "create_batch",
            "batch_id": batch_id,
            "timestamp": _now(),
            "entity_type": entity_type,
            "doctype": spec.doctype,
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "atomic": atomic,
            "rollback_errors": rollback_errors,
        }
        self.audit.append(event)
        status = "created"
        if errors and not created:
            status = "failed"
        elif errors:
            status = "partial"
        return {
            "tool": "create_test_data",
            "mode": "write",
            "status": status,
            "batch_id": batch_id,
            "entity_type": entity_type,
            "erpnext_doctype": spec.doctype,
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "rollback_errors": rollback_errors,
            "source": {"system": "ERPNext", "reference": spec.doctype},
        }

    def _normalize_records(
        self, spec: EntitySpec, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not isinstance(records, list) or not records:
            raise MasterDataError("records must be a non-empty list")
        if len(records) > self.settings.mcp_max_write_records:
            raise MasterDataError(
                f"At most {self.settings.mcp_max_write_records} records are allowed per call"
            )
        normalized: list[dict[str, Any]] = []
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                raise MasterDataError(f"Record {index} must be an object")
            unknown = sorted(set(record) - set(spec.fields))
            if unknown:
                raise MasterDataError(
                    f"Record {index} contains unsupported fields: {', '.join(unknown)}"
                )
            value = {**spec.defaults, **{key: item for key, item in record.items() if item != ""}}
            for field_name in spec.integer_fields:
                if field_name in value:
                    value[field_name] = _as_int(value[field_name], field_name, index)
            for field_name in spec.float_fields:
                if field_name in value:
                    value[field_name] = _as_float(value[field_name], field_name, index)
            missing = [name for name in spec.required if value.get(name) in (None, "", [])]
            if missing:
                raise MasterDataError(
                    f"Record {index} is missing required fields: {', '.join(missing)}"
                )
            self._validate_nested(spec, value, index)
            normalized.append(value)
        return normalized

    @staticmethod
    def _validate_nested(spec: EntitySpec, record: dict[str, Any], index: int) -> None:
        for field_name, nested_spec in spec.nested.items():
            rows = record.get(field_name)
            if rows is None:
                continue
            if not isinstance(rows, list):
                raise MasterDataError(f"Record {index}.{field_name} must be a list")
            for row_index, row in enumerate(rows):
                if not isinstance(row, dict):
                    raise MasterDataError(
                        f"Record {index}.{field_name}[{row_index}] must be an object"
                    )
                unknown = sorted(set(row) - set(nested_spec.fields))
                if unknown:
                    raise MasterDataError(
                        f"Record {index}.{field_name}[{row_index}] contains unsupported "
                        f"fields: {', '.join(unknown)}"
                    )
                missing = [name for name in nested_spec.required if row.get(name) in (None, "")]
                if missing:
                    raise MasterDataError(
                        f"Record {index}.{field_name}[{row_index}] is missing: "
                        f"{', '.join(missing)}"
                    )
                for choices in nested_spec.one_of:
                    if not any(row.get(choice) not in (None, "") for choice in choices):
                        raise MasterDataError(
                            f"Record {index}.{field_name}[{row_index}] needs one of: "
                            f"{', '.join(choices)}"
                        )

    @staticmethod
    def _parse_content(content: str, data_format: str) -> list[dict[str, Any]]:
        normalized_format = data_format.casefold()
        if normalized_format == "json":
            try:
                payload = json.loads(content)
            except ValueError as exc:
                raise MasterDataError(f"Invalid JSON: {exc}") from exc
            if isinstance(payload, dict):
                payload = payload.get("records")
            if not isinstance(payload, list):
                raise MasterDataError("JSON must be a list or an object with a records list")
            return payload
        if normalized_format != "csv":
            raise MasterDataError("data_format must be csv or json")
        try:
            reader = csv.DictReader(io.StringIO(content))
            rows = []
            for row in reader:
                parsed: dict[str, Any] = {}
                for key, value in row.items():
                    if key is None or value in (None, ""):
                        continue
                    clean = value.strip()
                    if clean.startswith(("[", "{")):
                        try:
                            parsed[key.strip()] = json.loads(clean)
                            continue
                        except ValueError:
                            pass
                    parsed[key.strip()] = clean
                rows.append(parsed)
        except csv.Error as exc:
            raise MasterDataError(f"Invalid CSV: {exc}") from exc
        if not rows:
            raise MasterDataError("CSV contains no data rows")
        return rows

    def _spec(self, entity_type: str) -> EntitySpec:
        try:
            return self.catalog[entity_type.casefold()]
        except KeyError as exc:
            supported = ", ".join(self.catalog)
            raise MasterDataError(
                f"Unsupported entity_type {entity_type!r}. Supported: {supported}"
            ) from exc

    def _check_write_policy(self, on_duplicate: str) -> None:
        if not self.settings.mcp_write_enabled:
            raise MasterDataError(
                "MCP writes are disabled. Set MCP_WRITE_ENABLED=true for the local demo."
            )
        if not self.client.configured:
            raise MasterDataError("ERPNext credentials are not configured for the MCP server")
        if on_duplicate not in {"skip", "error"}:
            raise MasterDataError("on_duplicate must be skip or error")


def _as_int(value: Any, field_name: str, index: int) -> int:
    if isinstance(value, str) and value.casefold() in {"true", "yes", "on"}:
        return 1
    if isinstance(value, str) and value.casefold() in {"false", "no", "off"}:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise MasterDataError(f"Record {index}.{field_name} must be an integer") from exc


def _as_float(value: Any, field_name: str, index: int) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise MasterDataError(f"Record {index}.{field_name} must be numeric") from exc


def _now() -> str:
    return datetime.now(UTC).isoformat()
