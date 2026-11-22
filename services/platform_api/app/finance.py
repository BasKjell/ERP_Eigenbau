from __future__ import annotations

import hashlib
import secrets
from datetime import date
from typing import Any

from .store import ScenarioStore, utc_now


class FinanceError(ValueError):
    """Raised when a finance workflow violates a business rule."""


class FinanceNotFoundError(FinanceError):
    """Raised when a finance object does not exist."""


class FinanceService:
    """Management reporting and safe demo workflows for finance operations.

    All adapters that would normally transmit data to an external provider are
    deliberately implemented as test adapters. They create an auditable preview
    and a simulated result, but never send data outside the platform.
    """

    EXTERNAL_ADAPTERS = {
        "datev": "DATEV Buchungsstapel",
        "e_invoice": "XRechnung / ZUGFeRD",
        "bank": "SEPA / Bank",
    }

    def __init__(self, store: ScenarioStore) -> None:
        self.store = store

    def dashboard(self) -> dict[str, Any]:
        state = self.store.get()
        domain = self._domain(state)
        orders = [self._order_view(item) for item in domain["orders"]]
        active_production = [
            item
            for item in orders
            if item["stage"] in {"Produktion", "Endprüfung"}
            and item["status"] not in {"cancelled", "invoiced"}
        ]
        backlog = [
            item
            for item in orders
            if item["status"] not in {"cancelled", "invoiced"}
        ]
        overdue_ar = [
            item
            for item in domain["open_items"]
            if item["type"] == "AR" and item["status"] == "overdue"
        ]
        cash = sorted(domain["cash_forecast"], key=lambda item: item["month"])
        as_of_month = str(domain["as_of"])[:7]
        current_cash = max(
            (item for item in cash if item["month"] <= as_of_month),
            key=lambda item: item["month"],
            default=cash[0] if cash else None,
        )
        latest_cash = current_cash["closing_balance"] if current_cash else 0
        forecast_cash = [item for item in cash if item["month"] >= as_of_month]
        minimum_cash = min(
            (item["closing_balance"] for item in forecast_cash), default=latest_cash
        )
        budgets = [self._budget_view(item) for item in domain["budgets"]]
        project_rows = self._project_profitability(orders)
        quality_total = sum(item["amount"] for item in domain["quality_costs"])
        warranty_total = sum(item["amount"] for item in domain["warranty_cases"])

        return {
            "as_of": domain["as_of"],
            "currency": domain["currency"],
            "data_classification": "DEMO",
            "metrics": {
                "production_order_value": sum(
                    item["order_value"] for item in active_production
                ),
                "production_weighted_revenue": sum(
                    item["weighted_revenue"] for item in active_production
                ),
                "backlog_value": sum(item["order_value"] for item in backlog),
                "weighted_backlog": sum(item["weighted_revenue"] for item in backlog),
                "expected_gross_margin": sum(
                    item["expected_margin"] for item in backlog
                ),
                "cash_balance": latest_cash,
                "minimum_forecast_cash": minimum_cash,
                "overdue_receivables": sum(item["amount"] for item in overdue_ar),
                "overdue_receivables_count": len(overdue_ar),
                "budget_variance": sum(item["variance"] for item in budgets),
                "quality_and_warranty_cost": quality_total + warranty_total,
                "active_rd_investment": sum(
                    item["forecast_cost"]
                    for item in domain["rd_projects"]
                    if item["status"] == "active"
                ),
            },
            "orders": orders,
            "revenue_by_month": self._revenue_by_month(orders),
            "project_profitability": project_rows,
            "cash_forecast": cash,
            "open_items": domain["open_items"],
            "budgets": budgets,
            "expenses": list(reversed(domain["expenses"])),
            "assets": domain["assets"],
            "subscriptions": domain["subscriptions"],
            "rd_projects": domain["rd_projects"],
            "quality_costs": domain["quality_costs"],
            "warranty_cases": domain["warranty_cases"],
            "integrations": self._integration_status(domain),
            "integration_runs": list(reversed(domain["integration_runs"][-12:])),
            "audit": list(reversed(domain["audit"][-20:])),
        }

    def update_budget(self, budget_id: str, actor_id: str, forecast: float) -> dict[str, Any]:
        if forecast < 0:
            raise FinanceError("Forecast darf nicht negativ sein")
        result: dict[str, Any] = {}

        def operation(state: dict[str, Any]) -> None:
            nonlocal result
            domain = self._domain(state)
            budget = self._find(domain["budgets"], budget_id, "Budget")
            budget["forecast"] = round(forecast, 2)
            budget["updated_at"] = utc_now()
            budget["updated_by"] = actor_id
            self._audit(domain, actor_id, "budget_forecast_updated", budget_id)
            result = self._budget_view(budget)

        self.store.mutate(operation)
        return result

    def create_expense(self, actor_id: str, values: dict[str, Any]) -> dict[str, Any]:
        amount = round(float(values.get("amount", 0)), 2)
        if amount <= 0:
            raise FinanceError("Betrag muss größer als 0 sein")
        description = str(values.get("description", "")).strip()
        if len(description) < 3:
            raise FinanceError("Beschreibung ist erforderlich")
        cost_center = str(values.get("cost_center", "")).strip()
        if not cost_center:
            raise FinanceError("Kostenstelle ist erforderlich")
        result: dict[str, Any] = {}

        def operation(state: dict[str, Any]) -> None:
            nonlocal result
            domain = self._domain(state)
            expense = {
                "id": self._next_id(domain["expenses"], "EXP"),
                "submitted_by": actor_id,
                "description": description,
                "category": str(values.get("category", "Sonstiges")).strip(),
                "cost_center": cost_center,
                "project_id": str(values.get("project_id", "")).strip(),
                "amount": amount,
                "receipt_reference": str(values.get("receipt_reference", "")).strip(),
                "status": "pending",
                "created_at": utc_now(),
                "decision": None,
            }
            domain["expenses"].append(expense)
            self._audit(domain, actor_id, "expense_submitted", expense["id"])
            result = dict(expense)

        self.store.mutate(operation)
        return result

    def decide_expense(
        self, expense_id: str, actor_id: str, decision: str, comment: str = ""
    ) -> dict[str, Any]:
        if decision not in {"approved", "rejected"}:
            raise FinanceError("Entscheidung muss approved oder rejected sein")
        result: dict[str, Any] = {}

        def operation(state: dict[str, Any]) -> None:
            nonlocal result
            domain = self._domain(state)
            expense = self._find(domain["expenses"], expense_id, "Auslage")
            if expense["status"] != "pending":
                raise FinanceError("Auslage wurde bereits entschieden")
            if expense["submitted_by"] == actor_id:
                raise FinanceError("Vier-Augen-Prinzip: Antragsteller darf nicht freigeben")
            expense["status"] = decision
            expense["decision"] = {
                "actor_id": actor_id,
                "comment": comment.strip(),
                "decided_at": utc_now(),
            }
            self._audit(domain, actor_id, f"expense_{decision}", expense_id)
            result = dict(expense)

        self.store.mutate(operation)
        return result

    def create_asset(self, actor_id: str, values: dict[str, Any]) -> dict[str, Any]:
        acquisition_cost = round(float(values.get("acquisition_cost", 0)), 2)
        useful_life_months = int(values.get("useful_life_months", 0))
        if acquisition_cost <= 0 or useful_life_months <= 0:
            raise FinanceError("Anschaffungskosten und Nutzungsdauer müssen positiv sein")
        name = str(values.get("name", "")).strip()
        if len(name) < 3:
            raise FinanceError("Anlagenbezeichnung ist erforderlich")
        result: dict[str, Any] = {}

        def operation(state: dict[str, Any]) -> None:
            nonlocal result
            domain = self._domain(state)
            asset = {
                "id": self._next_id(domain["assets"], "AST"),
                "name": name,
                "asset_class": str(values.get("asset_class", "Betriebs- und Geschäftsausstattung")),
                "cost_center": str(values.get("cost_center", "CC-IT")),
                "acquisition_date": str(values.get("acquisition_date") or date.today().isoformat()),
                "acquisition_cost": acquisition_cost,
                "useful_life_months": useful_life_months,
                "monthly_depreciation": round(acquisition_cost / useful_life_months, 2),
                "status": "active",
                "source": "FLOWFIN",
            }
            domain["assets"].append(asset)
            self._audit(domain, actor_id, "asset_created", asset["id"])
            result = dict(asset)

        self.store.mutate(operation)
        return result

    def datev_export(
        self, actor_id: str, period: str, confirm: bool, confirmation_token: str = ""
    ) -> dict[str, Any]:
        if len(period) != 7 or period[4] != "-":
            raise FinanceError("Periode muss YYYY-MM entsprechen")
        return self._external_preview_or_run(
            adapter="datev",
            actor_id=actor_id,
            key=period,
            confirm=confirm,
            confirmation_token=confirmation_token,
            record_count=8,
            amount=198750.0,
        )

    def bank_payment_run(
        self, actor_id: str, due_date: str, confirm: bool, confirmation_token: str = ""
    ) -> dict[str, Any]:
        try:
            date.fromisoformat(due_date)
        except ValueError as exc:
            raise FinanceError("Fälligkeitsdatum muss YYYY-MM-DD entsprechen") from exc
        state = self.store.get()
        items = [
            item
            for item in self._domain(state)["open_items"]
            if item["type"] == "AP" and item["due_date"] <= due_date
        ]
        return self._external_preview_or_run(
            adapter="bank",
            actor_id=actor_id,
            key=due_date,
            confirm=confirm,
            confirmation_token=confirmation_token,
            record_count=len(items),
            amount=sum(item["amount"] for item in items),
        )

    def validate_e_invoice(
        self, actor_id: str, invoice_id: str, invoice_format: str
    ) -> dict[str, Any]:
        if invoice_format not in {"xrechnung", "zugferd"}:
            raise FinanceError("Format muss xrechnung oder zugferd sein")
        if len(invoice_id.strip()) < 3:
            raise FinanceError("Rechnungsreferenz ist erforderlich")
        result: dict[str, Any] = {}

        def operation(state: dict[str, Any]) -> None:
            nonlocal result
            domain = self._domain(state)
            run = {
                "id": self._next_id(domain["integration_runs"], "INT"),
                "adapter": "e_invoice",
                "adapter_label": self.EXTERNAL_ADAPTERS["e_invoice"],
                "mode": "test",
                "status": "simulated_valid",
                "transmitted": False,
                "reference": invoice_id.strip(),
                "format": invoice_format,
                "checks": [
                    {"name": "Syntax", "status": "passed"},
                    {"name": "Pflichtfelder", "status": "passed"},
                    {"name": "Leitweg-ID", "status": "not_required_demo"},
                    {"name": "Rechenprüfung", "status": "passed"},
                ],
                "created_by": actor_id,
                "created_at": utc_now(),
                "notice": "Testvalidierung – kein Versand an Peppol oder Kundenportal.",
            }
            domain["integration_runs"].append(run)
            self._audit(domain, actor_id, "e_invoice_test_validated", run["id"])
            result = dict(run)

        self.store.mutate(operation)
        return result

    def reset(self) -> dict[str, Any]:
        self.store.reset_domain("finance")
        return self.dashboard()

    def _external_preview_or_run(
        self,
        *,
        adapter: str,
        actor_id: str,
        key: str,
        confirm: bool,
        confirmation_token: str,
        record_count: int,
        amount: float,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def operation(state: dict[str, Any]) -> None:
            nonlocal result
            domain = self._domain(state)
            if not confirm:
                token = secrets.token_urlsafe(24)
                preview = {
                    "id": self._next_id(domain["integration_previews"], "PRE"),
                    "adapter": adapter,
                    "key": key,
                    "record_count": record_count,
                    "amount": round(amount, 2),
                    "token_hash": self._token_hash(token),
                    "created_by": actor_id,
                    "created_at": utc_now(),
                    "used": False,
                }
                domain["integration_previews"].append(preview)
                self._audit(domain, actor_id, f"{adapter}_test_preview", preview["id"])
                result = {
                    "status": "preview",
                    "mode": "test",
                    "transmitted": False,
                    "adapter": adapter,
                    "adapter_label": self.EXTERNAL_ADAPTERS[adapter],
                    "key": key,
                    "record_count": record_count,
                    "amount": round(amount, 2),
                    "confirmation_token": token,
                    "notice": "Testmodus – Vorschau erzeugt, keine externe Übertragung.",
                }
                return

            preview = next(
                (
                    item
                    for item in reversed(domain["integration_previews"])
                    if item["adapter"] == adapter
                    and item["key"] == key
                    and not item["used"]
                    and secrets.compare_digest(
                        item["token_hash"], self._token_hash(confirmation_token)
                    )
                ),
                None,
            )
            if preview is None:
                raise FinanceError("Gültige Vorschau und Bestätigungstoken erforderlich")
            preview["used"] = True
            run = {
                "id": self._next_id(domain["integration_runs"], "INT"),
                "adapter": adapter,
                "adapter_label": self.EXTERNAL_ADAPTERS[adapter],
                "mode": "test",
                "status": "simulated",
                "transmitted": False,
                "key": key,
                "record_count": preview["record_count"],
                "amount": preview["amount"],
                "external_reference": f"SIM-{adapter.upper()}-{len(domain['integration_runs']) + 1:04d}",
                "created_by": actor_id,
                "created_at": utc_now(),
                "notice": "Testlauf abgeschlossen – es wurden keine Daten extern gesendet.",
            }
            domain["integration_runs"].append(run)
            self._audit(domain, actor_id, f"{adapter}_test_run", run["id"])
            result = dict(run)

        self.store.mutate(operation)
        return result

    @staticmethod
    def _order_view(order: dict[str, Any]) -> dict[str, Any]:
        item = dict(order)
        item["weighted_revenue"] = round(
            item["order_value"] * item["probability"] / 100, 2
        )
        item["expected_cost"] = max(item["actual_cost"], item["forecast_cost"])
        item["expected_margin"] = round(
            item["order_value"] - item["expected_cost"], 2
        )
        item["expected_margin_percent"] = round(
            item["expected_margin"] / item["order_value"] * 100, 1
        )
        return item

    @staticmethod
    def _revenue_by_month(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
        months: dict[str, dict[str, Any]] = {}
        for order in orders:
            month = order["expected_invoice_date"][:7]
            row = months.setdefault(
                month, {"month": month, "order_value": 0.0, "weighted_revenue": 0.0}
            )
            row["order_value"] += order["order_value"]
            row["weighted_revenue"] += order["weighted_revenue"]
        return [
            {
                **item,
                "order_value": round(item["order_value"], 2),
                "weighted_revenue": round(item["weighted_revenue"], 2),
            }
            for _, item in sorted(months.items())
        ]

    @staticmethod
    def _project_profitability(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "project_id": item["project_id"],
                "order_id": item["id"],
                "customer": item["customer"],
                "product": item["product"],
                "revenue": item["order_value"],
                "actual_cost": item["actual_cost"],
                "forecast_cost": item["expected_cost"],
                "expected_margin": item["expected_margin"],
                "expected_margin_percent": item["expected_margin_percent"],
                "progress": item["progress"],
                "risk": item["risk"],
            }
            for item in orders
        ]

    @staticmethod
    def _budget_view(budget: dict[str, Any]) -> dict[str, Any]:
        item = dict(budget)
        item["variance"] = round(item["budget"] - item["forecast"], 2)
        item["usage_percent"] = round(
            item["forecast"] / item["budget"] * 100, 1
        ) if item["budget"] else 0
        return item

    def _integration_status(self, domain: dict[str, Any]) -> list[dict[str, Any]]:
        last_runs = {
            run["adapter"]: run for run in domain["integration_runs"]
        }
        return [
            {
                "id": adapter,
                "name": label,
                "mode": "test",
                "configured": True,
                "external_connection": False,
                "last_run": last_runs.get(adapter),
                "notice": "Technischer Testadapter; keine produktive Übertragung.",
            }
            for adapter, label in self.EXTERNAL_ADAPTERS.items()
        ]

    @staticmethod
    def _domain(state: dict[str, Any]) -> dict[str, Any]:
        domain = state.get("finance")
        if not isinstance(domain, dict):
            raise FinanceError("FLOWFIN-Demodaten fehlen")
        return domain

    @staticmethod
    def _find(items: list[dict[str, Any]], item_id: str, label: str) -> dict[str, Any]:
        item = next((entry for entry in items if entry["id"] == item_id), None)
        if item is None:
            raise FinanceNotFoundError(f"{label} nicht gefunden")
        return item

    @staticmethod
    def _next_id(items: list[dict[str, Any]], prefix: str) -> str:
        numbers = []
        for item in items:
            try:
                numbers.append(int(str(item["id"]).rsplit("-", 1)[-1]))
            except (KeyError, ValueError):
                continue
        return f"{prefix}-{max(numbers, default=0) + 1:04d}"

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _audit(domain: dict[str, Any], actor_id: str, action: str, object_id: str) -> None:
        domain["audit"].append(
            {
                "actor_id": actor_id,
                "action": action,
                "object_id": object_id,
                "at": utc_now(),
            }
        )
