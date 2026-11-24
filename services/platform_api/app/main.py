from __future__ import annotations

import csv
import functools
import hmac
import io
import json
from collections.abc import Callable
from datetime import date, datetime
from html import escape
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, Counter, generate_latest
from pydantic import BaseModel, Field

from .agent_drafts import DraftService
from .agents_bff import AgentsHub, AgentUsageCollector
from .assistant import answer_question
from .auth import AuthError, OidcAuth
from .config import settings
from .desksharing import (
    DesksharingError,
    DesksharingNotFoundError,
    DesksharingService,
)
from .dms import DmsService
from .finance import FinanceError, FinanceNotFoundError, FinanceService
from .flow_routes import build_router, reject_agent_token_for_work
from .hr import HrError, HrNotFoundError, HrService
from .integrations import integration_status, paperless_search
from .mes import MesError, MesNotFoundError, MesService
from .operations import readiness_report
from .people import PeopleError, PeopleNotFoundError, PeopleService
from .quality import QualityError, QualityNotFoundError, QualityService
from .reporting import LiveReportingService
from .rm_adapter import RMAdapter
from .store import ScenarioStore
from .work import WorkError, WorkNotFoundError, WorkService
from .workplace import WorkplaceNotFoundError, WorkplaceService

APP_DIR = Path(__file__).parent
store = ScenarioStore(settings.data_file, settings.seed_file)
mes_service = MesService(store, settings)
hr_service = HrService(store, settings)
people_service = PeopleService(store, settings)
desksharing_service = DesksharingService(store)
work_service = WorkService(store, settings)
finance_service = FinanceService(store)
reporting_service = LiveReportingService(finance_service, mes_service, settings)
quality_service = QualityService(store, settings)
workplace_service = WorkplaceService(store)
oidc_auth = OidcAuth(settings)
rm_adapter = RMAdapter(store, work_service)
agents_hub = AgentsHub()
REGISTRY.register(AgentUsageCollector(agents_hub))
dms_service = DmsService(settings)
agent_drafts = DraftService(store)
action_counter = Counter("demo_actions_total", "Management demo actions", ["action"])

app = FastAPI(
    title="FLOWAPI",
    version="1.0.0",
    description="Integrationsschicht für FLOWERP, FLOWDOC, FLOWMES, FLOWQ und FLOWMANAGE.",
    docs_url=None,
    redoc_url=None,
)
app.mount("/assets", StaticFiles(directory=APP_DIR / "static"), name="assets")
app.include_router(build_router(rm_adapter, agents_hub, dms_service, agent_drafts, scenario=store.get))


@app.get("/docs", include_in_schema=False)
def company_swagger_ui() -> HTMLResponse:
    response = get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title} · API",
    )
    html = response.body.decode("utf-8").replace(
        "</head>",
        """<meta name="company-shell-app" content="api">
        <link rel="stylesheet" href="/assets/app-launcher.css">
        <link rel="stylesheet" href="/assets/company-theme.css">
        <script src="/assets/company-shell.js" defer></script>
        <script src="/assets/app-launcher.js" defer></script></head>""",
    )
    return HTMLResponse(html)


@app.middleware("http")
async def add_security_headers(request: Request, call_next: Callable[..., Any]) -> Response:
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )
    if request.url.path.startswith("/api/") or request.url.path in {
        "/",
        "/health",
        "/ready",
        "/management",
        "/mes",
        "/quality",
        "/hr",
        "/desksharing",
        "/work",
        "/finance",
        "/agents",
        "/dms",
    }:
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.middleware("http")
async def enforce_oidc(request: Request, call_next: Callable[..., Any]) -> Response:
    rejected = reject_agent_token_for_work(request)
    if rejected is not None:
        return rejected
    if not oidc_auth.enabled or oidc_auth.public_path(request.url.path):
        return await call_next(request)
    user = oidc_auth.current_user(request)
    if user is None:
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"detail": "Anmeldung über Keycloak erforderlich"},
            )
        next_path = request.url.path
        if request.url.query:
            next_path += f"?{request.url.query}"
        return RedirectResponse(f"/auth/login?next={next_path}")
    request.state.identity = user
    required_roles = oidc_auth.required_roles(request.url.path)
    roles = set(user.get("roles", []))
    management_read_only = (
        "management-user" in roles
        and request.method == "GET"
        and (
            request.url.path in {"/mes", "/quality", "/hr"}
            or request.url.path.startswith(("/api/mes", "/api/quality", "/api/hr"))
        )
    )
    if (
        required_roles
        and "platform-admin" not in roles
        and not required_roles.intersection(roles)
        and not management_read_only
    ):
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=403,
                content={"detail": "Für diesen Bereich fehlt die erforderliche Rolle"},
            )
        return Response("Zugriff verweigert", status_code=403, media_type="text/plain")
    return await call_next(request)


class Question(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class MesOperatorAction(BaseModel):
    operator_id: str = Field(min_length=3, max_length=80)


class MesPause(MesOperatorAction):
    reason: str = Field(min_length=2, max_length=120)
    note: str = Field(default="", max_length=500)


class MesTimeBooking(MesOperatorAction):
    minutes: int = Field(ge=1, le=720)
    activity: str = Field(default="Fertigungszeit", min_length=2, max_length=80)
    note: str = Field(default="", max_length=500)


class MesCompletion(MesOperatorAction):
    completed_qty: int = Field(ge=1, le=10000)
    scrap_qty: int = Field(default=0, ge=0, le=10000)
    serial_numbers: list[str] = Field(default_factory=list, max_length=1000)
    checklist: list[str] = Field(default_factory=list, max_length=100)
    note: str = Field(default="", max_length=1000)


class MesIssue(MesOperatorAction):
    category: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=3, max_length=1000)


class MesIssueResolution(MesOperatorAction):
    resolution: str = Field(min_length=3, max_length=1000)


class HrPunch(BaseModel):
    employee_id: str = Field(min_length=3, max_length=80)
    direction: Literal["IN", "OUT"]
    occurred_at: datetime | None = None
    source: Literal["web", "terminal", "mobile"] = "web"
    terminal: str = Field(default="FLOWHR Web", min_length=2, max_length=120)


class HrRequestCreate(BaseModel):
    employee_id: str = Field(min_length=3, max_length=80)
    type: Literal[
        "vacation",
        "sick",
        "time_off",
        "overtime",
        "remote_work",
        "business_trip",
        "correction",
    ]
    start_date: date
    end_date: date | None = None
    minutes: int | None = Field(default=None, ge=0, le=720)
    from_time: str | None = Field(default=None, max_length=5)
    to_time: str | None = Field(default=None, max_length=5)
    reason: str = Field(min_length=3, max_length=500)


class HrRequestDecision(BaseModel):
    approver_id: str = Field(min_length=3, max_length=80)
    decision: Literal["approved", "rejected"]
    comment: str = Field(default="", max_length=500)


class HrErpExport(BaseModel):
    employee_id: str = Field(min_length=3, max_length=80)
    date: date
    confirm: bool = False
    confirmation_token: str = Field(default="", max_length=100)


class RecruitingApplicationCreate(BaseModel):
    actor_id: str = Field(min_length=3, max_length=80)
    vacancy_id: str = Field(min_length=3, max_length=80)
    candidate_name: str = Field(min_length=3, max_length=160)
    email: str = Field(min_length=5, max_length=254)
    phone: str = Field(default="", max_length=80)
    source: str = Field(default="Direktbewerbung", max_length=120)


class RecruitingStageChange(BaseModel):
    actor_id: str = Field(min_length=3, max_length=80)
    stage: Literal["new", "screening", "interview", "offer", "hired", "rejected"]
    note: str = Field(default="", max_length=500)


class RecruitingDocumentLink(BaseModel):
    actor_id: str = Field(min_length=3, max_length=80)
    document_id: str = Field(min_length=3, max_length=100)
    document_type: str = Field(default="Bewerbungsunterlage", min_length=2, max_length=120)


class PayrollAction(BaseModel):
    actor_id: str = Field(min_length=3, max_length=80)


class PayrollApproval(PayrollAction):
    confirmation_token: str = Field(min_length=10, max_length=100)


class DeskBookingCreate(BaseModel):
    user_id: str = Field(default="USR-001", min_length=3, max_length=80)
    desk_id: str = Field(min_length=3, max_length=80)
    date: date
    slot: Literal["full_day", "morning", "afternoon"] = "full_day"
    note: str = Field(default="", max_length=300)


class DeskBookingAction(BaseModel):
    actor_id: str = Field(default="USR-001", min_length=3, max_length=80)


class QualityInspectionStart(BaseModel):
    receipt_id: str = Field(min_length=3, max_length=100)
    operator_id: str = Field(default="QOP-001", min_length=3, max_length=80)


class QualityMeasurementCreate(BaseModel):
    characteristic_id: str = Field(min_length=2, max_length=100)
    sample_ref: str = Field(min_length=2, max_length=160)
    value: Any
    unit: str = Field(default="", max_length=40)
    instrument_id: str | None = Field(default=None, max_length=100)
    source: Literal["manual", "rest", "mqtt", "opcua", "serial", "usb"] = "manual"
    external_event_id: str | None = Field(default=None, max_length=160)
    measured_at: datetime | None = None
    actor_id: str = Field(default="QOP-001", min_length=3, max_length=100)


class QualityGatewayMeasurement(QualityMeasurementCreate):
    inspection_id: str = Field(min_length=3, max_length=100)


class QualityInspectionAction(BaseModel):
    actor_id: str = Field(default="QOP-001", min_length=3, max_length=100)


class QualityErpSync(QualityInspectionAction):
    confirm: bool = False


class QualityInstrumentCalibration(QualityInspectionAction):
    calibrated_at: date
    valid_until: date
    certificate_document_id: str = Field(min_length=3, max_length=120)


class WorkIssueCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=4000)
    priority: Literal["Niedrig", "Normal", "Hoch", "Dringend"] = "Normal"
    assignee: str = Field(default="", max_length=120)
    due_date: date | None = None
    requirement_id: str | None = Field(default=None, max_length=80)


class RequirementCreate(BaseModel):
    title: str = Field(min_length=5, max_length=220)
    text: str = Field(min_length=5, max_length=5000)
    type: str = Field(min_length=2, max_length=80)
    priority: Literal["Must", "Should", "Could"] = "Must"
    owner: str = Field(min_length=2, max_length=120)
    parent_id: str | None = Field(default=None, max_length=80)
    acceptance_criteria: str = Field(default="", max_length=3000)
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class RequirementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=220)
    text: str | None = Field(default=None, min_length=5, max_length=5000)
    status: Literal["draft", "review", "approved", "verified", "rejected"] | None = None
    priority: Literal["Must", "Should", "Could"] | None = None
    owner: str | None = Field(default=None, min_length=2, max_length=120)
    acceptance_criteria: str | None = Field(default=None, max_length=3000)
    issue_id: str | None = Field(default=None, max_length=80)
    wiki_title: str | None = Field(default=None, max_length=160)
    verification: str | None = Field(default=None, max_length=160)
    custom_fields: dict[str, Any] | None = None
    change_note: str = Field(default="Änderung über FLOWWORK", max_length=500)


class BaselineCreate(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=1000)
    requirement_ids: list[str] = Field(default_factory=list, max_length=500)


class WorkFieldCreate(BaseModel):
    key: str = Field(default="", max_length=80)
    name: str = Field(min_length=2, max_length=120)
    field_type: Literal[
        "text", "rich_text", "integer", "decimal", "date", "flag", "url", "select", "multi_select"
    ]
    required: bool = False
    options: list[str] = Field(default_factory=list, max_length=200)
    applies_to: list[str] = Field(default_factory=list, max_length=100)
    description: str = Field(default="", max_length=500)


class WorkItemTypeCreate(BaseModel):
    key: str = Field(default="", max_length=80)
    name: str = Field(min_length=2, max_length=120)
    prefix: str = Field(default="", max_length=12)
    description: str = Field(default="", max_length=500)
    field_keys: list[str] = Field(default_factory=list, max_length=100)
    workflow: list[str] = Field(default_factory=list, max_length=30)


class WorkRelationshipTypeCreate(BaseModel):
    key: str = Field(default="", max_length=80)
    name: str = Field(min_length=2, max_length=120)
    reverse_name: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=500)


class WorkRelationshipRuleCreate(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    upstream_type: str = Field(min_length=1, max_length=80)
    downstream_types: list[str] = Field(min_length=1, max_length=100)
    relationship_type: str = Field(min_length=2, max_length=80)
    min_downstream: int = Field(default=0, ge=0, le=1000)
    max_downstream: int | None = Field(default=None, ge=1, le=1000)
    coverage: bool = True
    exclusive: bool = False


class WorkRelationshipCreate(BaseModel):
    source_id: str = Field(min_length=3, max_length=100)
    target_id: str = Field(min_length=3, max_length=100)
    relationship_type: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=500)


class WorkReviewParticipant(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    role: Literal["reviewer", "approver"]
    email: str = Field(default="", max_length=200)


class WorkReviewCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=1000)
    item_ids: list[str] = Field(min_length=1, max_length=500)
    participants: list[WorkReviewParticipant] = Field(min_length=1, max_length=100)
    deadline: date | None = None
    require_signature: bool = False
    allow_comments_in_item: bool = True


class WorkReviewComment(BaseModel):
    item_id: str | None = Field(default=None, max_length=100)
    text: str = Field(min_length=2, max_length=4000)


class WorkReviewDecision(BaseModel):
    participant: str = Field(default="", max_length=120)
    decision: Literal["approved", "completed", "rejected", "changes_requested"]
    signature: str | None = Field(default=None, max_length=300)
    note: str = Field(default="", max_length=1000)


class WorkTestCaseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=220)
    owner: str = Field(min_length=2, max_length=120)
    preconditions: str = Field(default="", max_length=2000)
    steps: list[dict[str, Any]] = Field(min_length=1, max_length=200)
    expected_result: str = Field(min_length=2, max_length=3000)
    status: Literal["draft", "approved", "retired"] = "draft"
    requirement_ids: list[str] = Field(default_factory=list, max_length=500)


class WorkTestPlanCreate(BaseModel):
    name: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=1000)
    owner: str = Field(min_length=2, max_length=120)
    test_case_ids: list[str] = Field(min_length=1, max_length=1000)


class WorkTestExecution(BaseModel):
    result: Literal["passed", "failed", "blocked"]
    evidence: str | None = Field(default=None, max_length=500)
    defect_issue_id: str | None = Field(default=None, max_length=100)
    note: str = Field(default="", max_length=1000)


class WorkRiskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=220)
    description: str = Field(default="", max_length=2000)
    probability: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    mitigation: str = Field(min_length=3, max_length=3000)
    owner: str = Field(min_length=2, max_length=120)
    status: Literal["open", "mitigated", "accepted", "closed"] = "open"
    requirement_ids: list[str] = Field(default_factory=list, max_length=500)


class WorkBranchCreate(BaseModel):
    variant: str = Field(min_length=2, max_length=120)
    title: str | None = Field(default=None, min_length=5, max_length=220)


class WorkImportPackage(BaseModel):
    schema_name: str = Field(default="flowwork-interchange-1.0", alias="schema")
    item_types: list[dict[str, Any]] = Field(default_factory=list)
    field_definitions: list[dict[str, Any]] = Field(default_factory=list)
    relationship_types: list[dict[str, Any]] = Field(default_factory=list)
    relationship_rules: list[dict[str, Any]] = Field(default_factory=list)
    requirements: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    test_cases: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    baselines: list[dict[str, Any]] = Field(default_factory=list)


class FinanceBudgetForecast(BaseModel):
    actor_id: str = Field(default="demo36", min_length=3, max_length=80)
    forecast: float = Field(ge=0, le=1_000_000_000)


class FinanceExpenseCreate(BaseModel):
    actor_id: str = Field(default="demo37", min_length=3, max_length=80)
    description: str = Field(min_length=3, max_length=300)
    category: str = Field(default="Sonstiges", min_length=2, max_length=120)
    cost_center: str = Field(min_length=2, max_length=80)
    project_id: str = Field(default="", max_length=80)
    amount: float = Field(gt=0, le=1_000_000)
    receipt_reference: str = Field(default="", max_length=160)


class FinanceExpenseDecision(BaseModel):
    actor_id: str = Field(default="demo40", min_length=3, max_length=80)
    decision: Literal["approved", "rejected"]
    comment: str = Field(default="", max_length=500)


class FinanceAssetCreate(BaseModel):
    actor_id: str = Field(default="demo36", min_length=3, max_length=80)
    name: str = Field(min_length=3, max_length=180)
    asset_class: str = Field(default="Betriebs- und Geschäftsausstattung", max_length=160)
    cost_center: str = Field(default="CC-IT", min_length=2, max_length=80)
    acquisition_date: date
    acquisition_cost: float = Field(gt=0, le=100_000_000)
    useful_life_months: int = Field(gt=0, le=600)


class FinanceExternalRun(BaseModel):
    actor_id: str = Field(default="demo36", min_length=3, max_length=80)
    key: str = Field(min_length=7, max_length=40)
    confirm: bool = False
    confirmation_token: str = Field(default="", max_length=120)


class FinanceInvoiceValidation(BaseModel):
    actor_id: str = Field(default="demo36", min_length=3, max_length=80)
    invoice_id: str = Field(min_length=3, max_length=120)
    invoice_format: Literal["xrechnung", "zugferd"] = "xrechnung"


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(APP_DIR / "static" / "portal.html")


@app.get("/management", include_in_schema=False)
def management_index() -> FileResponse:
    return FileResponse(APP_DIR / "static" / "index.html")


@app.get("/mes", include_in_schema=False)
def mes_index() -> FileResponse:
    return FileResponse(APP_DIR / "static" / "mes.html")


@app.get("/quality", include_in_schema=False)
def quality_index() -> FileResponse:
    return FileResponse(APP_DIR / "static" / "quality.html")


@app.get("/hr", include_in_schema=False)
def hr_index() -> FileResponse:
    return FileResponse(APP_DIR / "static" / "hr.html")


@app.get("/desksharing", include_in_schema=False)
def desksharing_index() -> FileResponse:
    return FileResponse(APP_DIR / "static" / "desksharing.html")


@app.get("/work", include_in_schema=False)
def work_index() -> FileResponse:
    return FileResponse(APP_DIR / "static" / "work.html")


@app.get("/finance", include_in_schema=False)
def finance_index() -> FileResponse:
    return FileResponse(APP_DIR / "static" / "finance.html")


@app.get("/auth/login", include_in_schema=False)
def auth_login(next: str = "/", login_hint: str = "") -> Response:
    hint = login_hint if login_hint in _demo_usernames() else ""
    return oidc_auth.login(next, login_hint=hint)


@functools.cache
def _demo_catalog() -> dict[str, Any]:
    try:
        iam = json.loads(settings.seed_file.read_text(encoding="utf-8")).get("iam") or {}
    except (OSError, ValueError):
        return {"accounts": [], "projects": {}}
    return {"accounts": list(iam.get("demo_accounts") or []), "projects": dict(iam.get("projects") or {})}


def _demo_usernames() -> set[str]:
    return {str(a.get("username")) for a in _demo_catalog()["accounts"]} if settings.demo_user_switch else set()


@app.get("/api/auth/demo-accounts", tags=["authentication"])
def auth_demo_accounts(request: Request) -> dict[str, Any]:
    """Demo-Konten für den Benutzerwechsel mit Funktion, AD-Gruppen und Projektrechten."""
    if not settings.demo_user_switch:
        raise HTTPException(status_code=404, detail="Benutzerwechsel ist nicht aktiviert")
    user = oidc_auth.current_user(request) or {}
    return {"enabled": oidc_auth.enabled, "current": user.get("username"), **_demo_catalog()}


@app.get("/auth/switch", include_in_schema=False)
def auth_switch(request: Request, user: str = "", next: str = "/") -> Response:
    if user not in _demo_usernames():
        raise HTTPException(status_code=404, detail="Unbekanntes Demo-Konto")
    if not oidc_auth.enabled:
        raise HTTPException(status_code=409, detail="Benutzerwechsel braucht die Anmeldung über FLOWID (AUTH_MODE=oidc)")
    return oidc_auth.switch(request, user, next)


@app.get("/auth/callback", include_in_schema=False)
def auth_callback(request: Request) -> Response:
    try:
        return oidc_auth.callback(request)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/auth/logout", include_in_schema=False)
def auth_logout(request: Request) -> Response:
    return oidc_auth.logout(request)


@app.get("/auth/me", tags=["authentication"])
def auth_me(request: Request) -> dict[str, object]:
    user = oidc_auth.current_user(request)
    return {
        "mode": settings.auth_mode,
        "authenticated": user is not None,
        "user": user,
        "login_url": "/auth/login",
        "logout_url": "/auth/logout",
    }


SSO_APPS: dict[str, tuple[str, set[str]]] = {
    "docs": (settings.documentation_public_url, set()),
    "erpnext": (
        settings.erpnext_public_url,
        {
            "sales-user",
            "procurement-user",
            "planning-user",
            "production-user",
            "quality-user",
            "warehouse-user",
            "finance-user",
            "project-user",
            "it-user",
        },
    ),
    "paperless": (settings.paperless_public_url, {"dms-user"}),
    "redmine": (
        settings.redmine_public_url,
        {"work-user", "requirements-user", "work-admin"},
    ),
    "open-webui": (settings.open_webui_public_url, {"ai-user"}),
    "prometheus": (settings.prometheus_public_url, {"it-user"}),
    "grafana": (
        settings.grafana_public_url,
        {"grafana-viewer", "management-user"},
    ),
}


def _sso_user(request: Request) -> dict[str, Any] | None:
    user = oidc_auth.current_user(request)
    if user is not None or oidc_auth.enabled:
        return user
    return {
        "username": "demo-admin",
        "name": "Lokale Funktionsdemo",
        "email": "demo-admin@example.invalid",
        "roles": ["platform-admin"],
        "department": "Demo",
    }


@app.get("/auth/proxy", include_in_schema=False)
def auth_proxy(request: Request, app_id: str = "") -> Response:
    target = SSO_APPS.get(app_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Unbekannte SSO-Anwendung")
    user = _sso_user(request)
    if user is None:
        return Response(status_code=401)
    roles = {str(role) for role in user.get("roles", [])}
    required_roles = target[1]
    if required_roles and "platform-admin" not in roles and not required_roles.intersection(roles):
        return Response(status_code=403)
    headers = {
        "X-Flow-Sso-User": str(user.get("username") or user.get("email") or ""),
        "X-Flow-Sso-Email": str(user.get("email") or ""),
        "X-Flow-Sso-Name": str(user.get("name") or user.get("username") or ""),
        "X-Flow-Sso-Roles": ",".join(sorted(roles)),
        "X-Flow-Sso-Department": str(user.get("department") or ""),
        "X-Flow-Sso-App-Role": "admin" if "platform-admin" in roles else "user",
    }
    return Response(status_code=204, headers=headers)


@app.get("/auth/app-login", include_in_schema=False)
def auth_app_login(request: Request, app_id: str = "") -> Response:
    if app_id not in SSO_APPS:
        raise HTTPException(status_code=404, detail="Unbekannte SSO-Anwendung")
    if _sso_user(request) is not None:
        return RedirectResponse(f"/auth/app-return?app_id={app_id}")
    return oidc_auth.login(f"/auth/app-return?app_id={app_id}")


@app.get("/auth/app-return", include_in_schema=False)
def auth_app_return(request: Request, app_id: str = "") -> Response:
    target = SSO_APPS.get(app_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Unbekannte SSO-Anwendung")
    user = _sso_user(request)
    if user is None:
        return oidc_auth.login(f"/auth/app-return?app_id={app_id}")
    roles = {str(role) for role in user.get("roles", [])}
    if target[1] and "platform-admin" not in roles and not target[1].intersection(roles):
        return Response("Zugriff verweigert", status_code=403, media_type="text/plain")
    return RedirectResponse(target[0])


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "platform-api"}


@app.get("/ready", tags=["operations"])
def ready(response: Response) -> dict[str, object]:
    report = readiness_report(store, settings)
    if not report["ready"]:
        response.status_code = 503
    return report


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/reporting/live", include_in_schema=False)
def live_reporting(request: Request) -> dict[str, object]:
    supplied = request.headers.get("X-Flow-Reporting-Token", "")
    expected = settings.reporting_api_token
    if not supplied or not expected or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Ungültiger Reporting-Zugriff")
    return reporting_service.snapshot()


@app.get("/api/demo", tags=["demo"])
def get_demo() -> dict[str, object]:
    return store.get()


@app.get("/api/workplace/today", tags=["workplace"])
def workplace_today(
    request: Request,
    user_id: str = "USR-006",
    selected_date: str = "",
) -> dict[str, object]:
    identity = getattr(request.state, "identity", None)
    resolved_user = (
        str(identity.get("desksharing_user_id"))
        if identity and identity.get("desksharing_user_id")
        else user_id
    )
    try:
        return workplace_service.daily_brief(resolved_user, selected_date)
    except WorkplaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/workplace/tools", tags=["workplace"])
def workplace_tools(request: Request, user_id: str = "USR-006") -> dict[str, object]:
    identity = getattr(request.state, "identity", None)
    resolved_user = (
        str(identity.get("desksharing_user_id"))
        if identity and identity.get("desksharing_user_id")
        else user_id
    )
    try:
        return {"user_id": resolved_user, "tools": workplace_service.personal_tools(resolved_user)}
    except WorkplaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/workplace/profiles", tags=["workplace"])
def workplace_profiles() -> dict[str, object]:
    profiles = workplace_service.profiles()
    return {"count": len(profiles), "profiles": profiles}


@app.get("/api/workplace/future-model", tags=["workplace"])
def workplace_future_model() -> dict[str, object]:
    return workplace_service.future_operating_model()


@app.post("/api/demo/reset", tags=["demo"])
def reset_demo() -> dict[str, object]:
    action_counter.labels("reset").inc()
    return store.reset()


@app.post("/api/demo/purge", tags=["demo"])
def purge_demo() -> dict[str, object]:
    action_counter.labels("purge").inc()
    return store.purge()


@app.post("/api/demo/advance", tags=["demo"])
def advance_demo() -> dict[str, object]:
    try:
        result = store.advance()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    action_counter.labels("advance").inc()
    return result


@app.post("/api/demo/stage/{stage_id}", tags=["demo"])
def set_demo_stage(stage_id: str) -> dict[str, object]:
    try:
        result = store.set_stage(stage_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unbekannter Prozessschritt") from exc
    action_counter.labels("stage").inc()
    return result


@app.post("/api/demo/failure", tags=["demo"])
def inject_failure() -> dict[str, object]:
    action_counter.labels("failure").inc()
    return store.inject_failure()


@app.post("/api/demo/rework", tags=["demo"])
def resolve_failure() -> dict[str, object]:
    try:
        result = store.resolve_failure()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    action_counter.labels("rework").inc()
    return result


@app.post("/api/assistant/ask", tags=["assistant"])
def ask_assistant(question: Annotated[Question, Body()]) -> dict[str, object]:
    action_counter.labels("assistant").inc()
    return answer_question(question.question, store.get(), settings)


@app.get("/api/integrations", tags=["integrations"])
def get_integrations() -> list[dict[str, object]]:
    return integration_status(settings)


@app.get("/api/documents/search", tags=["integrations"])
def search_documents(q: str = "SCU-100") -> dict[str, object]:
    return paperless_search(q, settings)


@app.get("/api/quality/dashboard", tags=["quality"])
def quality_dashboard(operator_id: str = "QOP-001") -> dict[str, object]:
    return _quality_call(quality_service.dashboard, operator_id)


@app.get("/api/quality/v1/interfaces", tags=["quality-integration"])
def quality_interfaces() -> dict[str, object]:
    return quality_service.interfaces()


@app.post("/api/quality/inspections", tags=["quality"])
def quality_start_inspection(payload: QualityInspectionStart) -> dict[str, object]:
    action_counter.labels("quality_inspection_start").inc()
    return _quality_call(
        quality_service.start_inspection, payload.receipt_id, payload.operator_id
    )


@app.post(
    "/api/quality/inspections/{inspection_id}/measurements",
    tags=["quality"],
)
def quality_record_measurement(
    inspection_id: str, payload: QualityMeasurementCreate
) -> dict[str, object]:
    action_counter.labels("quality_measurement").inc()
    values = payload.model_dump(mode="json", exclude={"actor_id"})
    return _quality_call(
        quality_service.record_measurement,
        inspection_id,
        values,
        payload.actor_id,
    )


@app.post("/api/quality/v1/measurements", tags=["quality-integration"])
def quality_ingest_measurement(
    payload: QualityGatewayMeasurement,
) -> dict[str, object]:
    """Ingest one idempotent reading from a measurement gateway."""
    action_counter.labels("quality_gateway_measurement").inc()
    values = payload.model_dump(
        mode="json", exclude={"inspection_id", "actor_id"}
    )
    return _quality_call(
        quality_service.record_measurement,
        payload.inspection_id,
        values,
        payload.actor_id,
    )


@app.post(
    "/api/quality/inspections/{inspection_id}/complete",
    tags=["quality"],
)
def quality_complete_inspection(
    inspection_id: str, payload: QualityInspectionAction
) -> dict[str, object]:
    action_counter.labels("quality_inspection_complete").inc()
    return _quality_call(
        quality_service.complete_inspection, inspection_id, payload.actor_id
    )


@app.post(
    "/api/quality/inspections/{inspection_id}/erp-sync",
    tags=["quality-integration"],
)
def quality_sync_to_erp(
    inspection_id: str, payload: QualityErpSync
) -> dict[str, object]:
    action_counter.labels("quality_erp_sync").inc()
    return _quality_call(
        quality_service.sync_to_erp,
        inspection_id,
        payload.actor_id,
        payload.confirm,
    )


@app.post(
    "/api/quality/instruments/{instrument_id}/calibration",
    tags=["quality"],
)
def quality_calibrate_instrument(
    instrument_id: str, payload: QualityInstrumentCalibration
) -> dict[str, object]:
    action_counter.labels("quality_instrument_calibration").inc()
    return _quality_call(
        quality_service.calibrate_instrument,
        instrument_id,
        payload.actor_id,
        payload.calibrated_at.isoformat(),
        payload.valid_until.isoformat(),
        payload.certificate_document_id,
    )


@app.post("/api/quality/reset", tags=["quality"])
def quality_reset(operator_id: str = "QOP-001") -> dict[str, object]:
    action_counter.labels("quality_reset").inc()
    return _quality_call(quality_service.reset, operator_id)


@app.get("/api/desksharing/dashboard", tags=["desksharing"])
def desksharing_dashboard(
    request: Request,
    user_id: str = "USR-001",
    booking_date: date | None = None,
    site_id: str | None = None,
    slot: Literal["full_day", "morning", "afternoon"] = "full_day",
) -> dict[str, object]:
    actor = _desksharing_actor(request, user_id)
    return _desksharing_call(
        desksharing_service.dashboard,
        actor,
        booking_date.isoformat() if booking_date else None,
        site_id,
        slot,
    )


@app.post("/api/desksharing/bookings", tags=["desksharing"])
def create_desk_booking(request: Request, payload: DeskBookingCreate) -> dict[str, object]:
    actor = _desksharing_actor(request, payload.user_id)
    action_counter.labels("desksharing_book").inc()
    return _desksharing_call(
        desksharing_service.create_booking,
        actor,
        payload.desk_id,
        payload.date.isoformat(),
        payload.slot,
        payload.note,
    )


@app.post("/api/desksharing/bookings/{booking_id}/cancel", tags=["desksharing"])
def cancel_desk_booking(
    booking_id: str, request: Request, payload: DeskBookingAction
) -> dict[str, object]:
    actor = _desksharing_actor(request, payload.actor_id)
    action_counter.labels("desksharing_cancel").inc()
    return _desksharing_call(desksharing_service.cancel_booking, booking_id, actor)


@app.post("/api/desksharing/bookings/{booking_id}/check-in", tags=["desksharing"])
def check_in_desk_booking(
    booking_id: str, request: Request, payload: DeskBookingAction
) -> dict[str, object]:
    actor = _desksharing_actor(request, payload.actor_id)
    action_counter.labels("desksharing_checkin").inc()
    return _desksharing_call(desksharing_service.check_in, booking_id, actor)


@app.post("/api/desksharing/bookings/{booking_id}/check-out", tags=["desksharing"])
def check_out_desk_booking(
    booking_id: str, request: Request, payload: DeskBookingAction
) -> dict[str, object]:
    actor = _desksharing_actor(request, payload.actor_id)
    action_counter.labels("desksharing_checkout").inc()
    return _desksharing_call(desksharing_service.check_out, booking_id, actor)


@app.get("/api/desksharing/admin", tags=["desksharing"])
def desksharing_admin(request: Request, actor_id: str = "USR-049") -> dict[str, object]:
    actor = _desksharing_actor(request, actor_id)
    return _desksharing_call(desksharing_service.admin_dashboard, actor)


@app.post("/api/desksharing/reset", tags=["desksharing"])
def reset_desksharing(request: Request, user_id: str = "USR-001") -> dict[str, object]:
    actor = _desksharing_actor(request, user_id)
    action_counter.labels("desksharing_reset").inc()
    return _desksharing_call(desksharing_service.reset, actor)


@app.get("/api/work/dashboard", tags=["work"])
def work_dashboard(request: Request) -> dict[str, object]:
    identity = getattr(request.state, "identity", None)
    return _work_call(work_service.dashboard, identity)


@app.post("/api/work/issues", tags=["work"])
def work_create_issue(request: Request, payload: WorkIssueCreate) -> dict[str, object]:
    action_counter.labels("work_issue_create").inc()
    return _work_call(
        work_service.create_issue,
        payload.model_dump(mode="json"),
        _work_actor(request),
    )


@app.post("/api/work/requirements", tags=["requirements"])
def work_create_requirement(
    request: Request, payload: RequirementCreate
) -> dict[str, object]:
    action_counter.labels("requirement_create").inc()
    return _work_call(
        work_service.create_requirement,
        payload.model_dump(mode="json"),
        _work_actor(request),
    )


@app.patch("/api/work/requirements/{requirement_id}", tags=["requirements"])
def work_update_requirement(
    requirement_id: str, request: Request, payload: RequirementUpdate
) -> dict[str, object]:
    action_counter.labels("requirement_update").inc()
    return _work_call(
        work_service.update_requirement,
        requirement_id,
        payload.model_dump(exclude_none=True),
        _work_actor(request),
    )


@app.post("/api/work/baselines", tags=["requirements"])
def work_create_baseline(
    request: Request, payload: BaselineCreate
) -> dict[str, object]:
    action_counter.labels("baseline_create").inc()
    return _work_call(
        work_service.create_baseline,
        payload.model_dump(),
        _work_actor(request),
    )


@app.get("/api/work/baselines/{baseline_id}/compare", tags=["requirements"])
def work_compare_baseline(baseline_id: str) -> dict[str, object]:
    return _work_call(work_service.compare_baseline, baseline_id)


@app.post("/api/work/admin/fields", tags=["requirements-admin"])
def work_create_field(request: Request, payload: WorkFieldCreate) -> dict[str, object]:
    action_counter.labels("work_field_create").inc()
    return _work_call(
        work_service.create_field_definition,
        payload.model_dump(),
        _work_actor(request),
    )


@app.post("/api/work/admin/item-types", tags=["requirements-admin"])
def work_create_item_type(
    request: Request, payload: WorkItemTypeCreate
) -> dict[str, object]:
    action_counter.labels("work_item_type_create").inc()
    return _work_call(
        work_service.create_item_type,
        payload.model_dump(),
        _work_actor(request),
    )


@app.post("/api/work/admin/relationship-types", tags=["requirements-admin"])
def work_create_relationship_type(
    request: Request, payload: WorkRelationshipTypeCreate
) -> dict[str, object]:
    action_counter.labels("work_relationship_type_create").inc()
    return _work_call(
        work_service.create_relationship_type,
        payload.model_dump(),
        _work_actor(request),
    )


@app.post("/api/work/admin/relationship-rules", tags=["requirements-admin"])
def work_create_relationship_rule(
    request: Request, payload: WorkRelationshipRuleCreate
) -> dict[str, object]:
    action_counter.labels("work_relationship_rule_create").inc()
    return _work_call(
        work_service.create_relationship_rule,
        payload.model_dump(),
        _work_actor(request),
    )


@app.post("/api/work/relationships", tags=["requirements"])
def work_create_relationship(
    request: Request, payload: WorkRelationshipCreate
) -> dict[str, object]:
    action_counter.labels("work_relationship_create").inc()
    return _work_call(
        work_service.create_relationship,
        payload.model_dump(),
        _work_actor(request),
    )


@app.post("/api/work/relationships/{relationship_id}/clear-suspect", tags=["requirements"])
def work_clear_suspect(relationship_id: str, request: Request) -> dict[str, object]:
    action_counter.labels("work_relationship_assess").inc()
    return _work_call(
        work_service.clear_suspect, relationship_id, _work_actor(request)
    )


@app.post("/api/work/reviews", tags=["requirements-reviews"])
def work_create_review(request: Request, payload: WorkReviewCreate) -> dict[str, object]:
    action_counter.labels("work_review_create").inc()
    return _work_call(
        work_service.create_review,
        payload.model_dump(mode="json"),
        _work_actor(request),
    )


@app.post("/api/work/reviews/{review_id}/comments", tags=["requirements-reviews"])
def work_review_comment(
    review_id: str, request: Request, payload: WorkReviewComment
) -> dict[str, object]:
    action_counter.labels("work_review_comment").inc()
    return _work_call(
        work_service.add_review_comment,
        review_id,
        payload.model_dump(exclude_none=True),
        _work_actor(request),
    )


@app.post("/api/work/reviews/{review_id}/decisions", tags=["requirements-reviews"])
def work_review_decision(
    review_id: str, request: Request, payload: WorkReviewDecision
) -> dict[str, object]:
    action_counter.labels("work_review_decision").inc()
    return _work_call(
        work_service.review_decision,
        review_id,
        payload.model_dump(exclude_none=True),
        _work_actor(request),
    )


@app.post("/api/work/tests/cases", tags=["requirements-tests"])
def work_create_test_case(
    request: Request, payload: WorkTestCaseCreate
) -> dict[str, object]:
    action_counter.labels("work_test_case_create").inc()
    return _work_call(
        work_service.create_test_case,
        payload.model_dump(),
        _work_actor(request),
    )


@app.post("/api/work/tests/plans", tags=["requirements-tests"])
def work_create_test_plan(
    request: Request, payload: WorkTestPlanCreate
) -> dict[str, object]:
    action_counter.labels("work_test_plan_create").inc()
    return _work_call(
        work_service.create_test_plan,
        payload.model_dump(),
        _work_actor(request),
    )


@app.post(
    "/api/work/tests/runs/{run_id}/cases/{test_case_id}",
    tags=["requirements-tests"],
)
def work_execute_test(
    run_id: str,
    test_case_id: str,
    request: Request,
    payload: WorkTestExecution,
) -> dict[str, object]:
    action_counter.labels("work_test_execute").inc()
    return _work_call(
        work_service.execute_test,
        run_id,
        test_case_id,
        payload.model_dump(exclude_none=True),
        _work_actor(request),
    )


@app.post("/api/work/risks", tags=["requirements-risk"])
def work_create_risk(request: Request, payload: WorkRiskCreate) -> dict[str, object]:
    action_counter.labels("work_risk_create").inc()
    return _work_call(
        work_service.create_risk,
        payload.model_dump(),
        _work_actor(request),
    )


@app.post("/api/work/requirements/{requirement_id}/branch", tags=["requirements"])
def work_branch_requirement(
    requirement_id: str, request: Request, payload: WorkBranchCreate
) -> dict[str, object]:
    action_counter.labels("work_requirement_branch").inc()
    return _work_call(
        work_service.branch_requirement,
        requirement_id,
        payload.model_dump(exclude_none=True),
        _work_actor(request),
    )


@app.get("/api/work/export", tags=["requirements-interchange"])
def work_export(format: Literal["json", "csv", "reqif"] = "json") -> Response:
    package = _work_call(work_service.export_package)
    if format == "json":
        return JSONResponse(
            package,
            headers={"Content-Disposition": 'attachment; filename="flowwork-export.json"'},
        )
    if format == "csv":
        stream = io.StringIO()
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(
            ["ID", "Typ", "Titel", "Status", "Version", "Owner", "Text", "Akzeptanzkriterien"]
        )
        for item in package["requirements"]:
            writer.writerow(
                [
                    item.get("id"),
                    item.get("type"),
                    item.get("title"),
                    item.get("status"),
                    item.get("version"),
                    item.get("owner"),
                    item.get("text"),
                    item.get("acceptance_criteria"),
                ]
            )
        return Response(
            stream.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="flowwork-requirements.csv"'},
        )
    spec_objects = "".join(
        f'<SPEC-OBJECT IDENTIFIER="{escape(str(item["id"]))}"><LONG-NAME>{escape(str(item.get("title", "")))}</LONG-NAME><DESC>{escape(str(item.get("text", "")))}</DESC></SPEC-OBJECT>'
        for item in package["requirements"]
    )
    relations = "".join(
        f'<SPEC-RELATION IDENTIFIER="{escape(str(item["id"]))}" SOURCE="{escape(str(item["source_id"]))}" TARGET="{escape(str(item["target_id"]))}" TYPE="{escape(str(item["relationship_type"]))}" />'
        for item in package["relationships"]
    )
    reqif = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<REQ-IF xmlns="http://www.omg.org/spec/ReqIF/20110401/reqif.xsd">'
        f"<THE-HEADER><REQ-IF-HEADER IDENTIFIER=\"FLOWWORK\"><TITLE>FLOWWORK Export</TITLE></REQ-IF-HEADER></THE-HEADER><CORE-CONTENT><REQ-IF-CONTENT><SPEC-OBJECTS>{spec_objects}</SPEC-OBJECTS><SPEC-RELATIONS>{relations}</SPEC-RELATIONS></REQ-IF-CONTENT></CORE-CONTENT></REQ-IF>"
    )
    return Response(
        reqif,
        media_type="application/xml",
        headers={"Content-Disposition": 'attachment; filename="flowwork-export.reqif"'},
    )


@app.post("/api/work/import", tags=["requirements-interchange"])
def work_import(
    request: Request, payload: WorkImportPackage
) -> dict[str, object]:
    action_counter.labels("work_import").inc()
    values = payload.model_dump(by_alias=True)
    values.pop("schema", None)
    return _work_call(work_service.import_package, values, _work_actor(request))


@app.post("/api/work/reset", tags=["work"])
def work_reset() -> dict[str, object]:
    action_counter.labels("work_reset").inc()
    return _work_call(work_service.reset)


@app.get("/api/finance/dashboard", tags=["finance"])
def finance_dashboard() -> dict[str, object]:
    return _finance_call(finance_service.dashboard)


@app.post("/api/finance/budgets/{budget_id}/forecast", tags=["finance"])
def finance_update_budget(
    budget_id: str, payload: FinanceBudgetForecast
) -> dict[str, object]:
    action_counter.labels("finance_budget_forecast").inc()
    return _finance_call(
        finance_service.update_budget, budget_id, payload.actor_id, payload.forecast
    )


@app.post("/api/finance/expenses", tags=["finance"])
def finance_create_expense(payload: FinanceExpenseCreate) -> dict[str, object]:
    action_counter.labels("finance_expense_create").inc()
    return _finance_call(
        finance_service.create_expense,
        payload.actor_id,
        payload.model_dump(exclude={"actor_id"}, mode="json"),
    )


@app.post("/api/finance/expenses/{expense_id}/decision", tags=["finance"])
def finance_decide_expense(
    expense_id: str, payload: FinanceExpenseDecision
) -> dict[str, object]:
    action_counter.labels("finance_expense_decision").inc()
    return _finance_call(
        finance_service.decide_expense,
        expense_id,
        payload.actor_id,
        payload.decision,
        payload.comment,
    )


@app.post("/api/finance/assets", tags=["finance"])
def finance_create_asset(payload: FinanceAssetCreate) -> dict[str, object]:
    action_counter.labels("finance_asset_create").inc()
    return _finance_call(
        finance_service.create_asset,
        payload.actor_id,
        payload.model_dump(exclude={"actor_id"}, mode="json"),
    )


@app.post("/api/finance/integrations/datev", tags=["finance-integrations"])
def finance_datev_export(payload: FinanceExternalRun) -> dict[str, object]:
    action_counter.labels("finance_datev_test").inc()
    return _finance_call(
        finance_service.datev_export,
        payload.actor_id,
        payload.key,
        payload.confirm,
        payload.confirmation_token,
    )


@app.post("/api/finance/integrations/bank", tags=["finance-integrations"])
def finance_bank_run(payload: FinanceExternalRun) -> dict[str, object]:
    action_counter.labels("finance_bank_test").inc()
    return _finance_call(
        finance_service.bank_payment_run,
        payload.actor_id,
        payload.key,
        payload.confirm,
        payload.confirmation_token,
    )


@app.post("/api/finance/integrations/e-invoice/validate", tags=["finance-integrations"])
def finance_validate_e_invoice(
    payload: FinanceInvoiceValidation,
) -> dict[str, object]:
    action_counter.labels("finance_einvoice_test").inc()
    return _finance_call(
        finance_service.validate_e_invoice,
        payload.actor_id,
        payload.invoice_id,
        payload.invoice_format,
    )


@app.post("/api/finance/reset", tags=["finance"])
def finance_reset() -> dict[str, object]:
    action_counter.labels("finance_reset").inc()
    return _finance_call(finance_service.reset)


@app.get("/api/mes/dashboard", tags=["mes"])
def mes_dashboard(operator_id: str | None = None) -> dict[str, object]:
    try:
        return mes_service.dashboard(operator_id)
    except MesNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MesError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/mes/reset", tags=["mes"])
def reset_mes(operator_id: str | None = None) -> dict[str, object]:
    action_counter.labels("mes_reset").inc()
    return _mes_call(mes_service.reset, operator_id)


@app.get("/api/mes/jobs/{job_id}", tags=["mes"])
def mes_job(job_id: str) -> dict[str, object]:
    return _mes_call(mes_service.job, job_id)


@app.post("/api/mes/jobs/{job_id}/start", tags=["mes"])
def start_mes_job(job_id: str, payload: MesOperatorAction) -> dict[str, object]:
    action_counter.labels("mes_start").inc()
    return _mes_call(mes_service.start, job_id, payload.operator_id)


@app.post("/api/mes/jobs/{job_id}/pause", tags=["mes"])
def pause_mes_job(job_id: str, payload: MesPause) -> dict[str, object]:
    action_counter.labels("mes_pause").inc()
    return _mes_call(
        mes_service.pause, job_id, payload.operator_id, payload.reason, payload.note
    )


@app.post("/api/mes/jobs/{job_id}/time", tags=["mes"])
def book_mes_time(job_id: str, payload: MesTimeBooking) -> dict[str, object]:
    action_counter.labels("mes_time").inc()
    return _mes_call(
        mes_service.book_time,
        job_id,
        payload.operator_id,
        payload.minutes,
        payload.activity,
        payload.note,
    )


@app.post("/api/mes/jobs/{job_id}/complete", tags=["mes"])
def complete_mes_job(job_id: str, payload: MesCompletion) -> dict[str, object]:
    action_counter.labels("mes_complete").inc()
    return _mes_call(
        mes_service.complete,
        job_id,
        payload.operator_id,
        payload.completed_qty,
        payload.scrap_qty,
        payload.serial_numbers,
        payload.checklist,
        payload.note,
    )


@app.post("/api/mes/jobs/{job_id}/issue", tags=["mes"])
def report_mes_issue(job_id: str, payload: MesIssue) -> dict[str, object]:
    action_counter.labels("mes_issue").inc()
    return _mes_call(
        mes_service.report_issue,
        job_id,
        payload.operator_id,
        payload.category,
        payload.description,
    )


@app.post("/api/mes/jobs/{job_id}/issue/resolve", tags=["mes"])
def resolve_mes_issue(job_id: str, payload: MesIssueResolution) -> dict[str, object]:
    action_counter.labels("mes_resolve").inc()
    return _mes_call(
        mes_service.resolve_issue,
        job_id,
        payload.operator_id,
        payload.resolution,
    )


@app.get("/api/mes/jobs/{job_id}/documents", tags=["mes"])
def mes_documents(job_id: str) -> dict[str, object]:
    return _mes_call(mes_service.documents, job_id)


@app.get("/api/hr/dashboard", tags=["hr"])
def hr_dashboard(
    employee_id: str = "DEMO-EMP-006", selected_date: date | None = None
) -> dict[str, object]:
    return _hr_call(
        hr_service.dashboard,
        employee_id,
        selected_date.isoformat() if selected_date else None,
    )


@app.get("/api/hr/calendar", tags=["hr"])
def hr_calendar(
    employee_id: str = "DEMO-EMP-006",
    month: str = "2026-11",
    scope: Literal["self", "team"] = "self",
) -> dict[str, object]:
    return _hr_call(hr_service.calendar, employee_id, month, scope)


@app.post("/api/hr/punch", tags=["hr"])
def hr_punch(payload: HrPunch) -> dict[str, object]:
    action_counter.labels("hr_punch").inc()
    return _hr_call(
        hr_service.punch,
        payload.employee_id,
        payload.direction,
        payload.occurred_at.isoformat() if payload.occurred_at else None,
        payload.source,
        payload.terminal,
    )


@app.post("/api/hr/requests", tags=["hr"])
def hr_create_request(payload: HrRequestCreate) -> dict[str, object]:
    action_counter.labels("hr_request").inc()
    values = payload.model_dump(mode="json", exclude={"employee_id"})
    return _hr_call(hr_service.create_request, payload.employee_id, values)


@app.post("/api/hr/requests/{request_id}/decision", tags=["hr"])
def hr_decide_request(
    request_id: str, payload: HrRequestDecision
) -> dict[str, object]:
    action_counter.labels("hr_decision").inc()
    return _hr_call(
        hr_service.decide_request,
        request_id,
        payload.approver_id,
        payload.decision,
        payload.comment,
    )


@app.post("/api/hr/export/erp", tags=["hr"])
def hr_export_erp(payload: HrErpExport) -> dict[str, object]:
    action_counter.labels("hr_erp_export").inc()
    return _hr_call(
        hr_service.export_to_erp,
        payload.employee_id,
        payload.date.isoformat(),
        confirm=payload.confirm,
        confirmation_token=payload.confirmation_token,
    )


@app.post("/api/hr/reset", tags=["hr"])
def hr_reset(employee_id: str = "DEMO-EMP-006") -> dict[str, object]:
    action_counter.labels("hr_reset").inc()
    return _hr_call(hr_service.reset, employee_id)


@app.get("/api/hr/recruiting", tags=["hr-recruiting"])
def recruiting_dashboard(actor_id: str = "HR-USER-001") -> dict[str, object]:
    return _people_call(people_service.recruiting_dashboard, actor_id)


@app.post("/api/hr/recruiting/applications", tags=["hr-recruiting"])
def create_recruiting_application(
    payload: RecruitingApplicationCreate,
) -> dict[str, object]:
    action_counter.labels("recruiting_create").inc()
    values = payload.model_dump(exclude={"actor_id"})
    return _people_call(people_service.create_application, payload.actor_id, values)


@app.post(
    "/api/hr/recruiting/applications/{application_id}/stage",
    tags=["hr-recruiting"],
)
def move_recruiting_application(
    application_id: str, payload: RecruitingStageChange
) -> dict[str, object]:
    action_counter.labels("recruiting_stage").inc()
    return _people_call(
        people_service.move_application,
        application_id,
        payload.actor_id,
        payload.stage,
        payload.note,
    )


@app.post(
    "/api/hr/recruiting/applications/{application_id}/documents/link",
    tags=["hr-recruiting"],
)
def link_recruiting_document(
    application_id: str, payload: RecruitingDocumentLink
) -> dict[str, object]:
    action_counter.labels("recruiting_document_link").inc()
    return _people_call(
        people_service.link_application_document,
        application_id,
        payload.actor_id,
        payload.document_id,
        payload.document_type,
    )


@app.post(
    "/api/hr/recruiting/applications/{application_id}/documents/upload",
    tags=["hr-recruiting"],
)
async def upload_recruiting_document(
    application_id: str,
    file: Annotated[UploadFile, File()],
    actor_id: Annotated[str, Form()],
    document_type: Annotated[str, Form()] = "Bewerbungsunterlage",
) -> dict[str, object]:
    content = await file.read(10 * 1024 * 1024 + 1)
    action_counter.labels("recruiting_document_upload").inc()
    return _people_call(
        people_service.upload_application_document,
        application_id,
        actor_id,
        content,
        file.filename or "bewerbungsunterlage.pdf",
        document_type,
    )


@app.get("/api/hr/payroll", tags=["hr-payroll"])
def payroll_dashboard(
    actor_id: str = "HR-USER-001", period_id: str | None = None
) -> dict[str, object]:
    return _people_call(people_service.payroll_dashboard, actor_id, period_id)


@app.post("/api/hr/payroll/{period_id}/prepare", tags=["hr-payroll"])
def prepare_payroll(period_id: str, payload: PayrollAction) -> dict[str, object]:
    action_counter.labels("payroll_prepare").inc()
    return _people_call(people_service.prepare_payroll, period_id, payload.actor_id)


@app.post("/api/hr/payroll/{period_id}/approve", tags=["hr-payroll"])
def approve_payroll(period_id: str, payload: PayrollApproval) -> dict[str, object]:
    action_counter.labels("payroll_approve").inc()
    return _people_call(
        people_service.approve_payroll,
        period_id,
        payload.actor_id,
        payload.confirmation_token,
    )


@app.post("/api/hr/payroll/runs/{run_id}/deliver", tags=["hr-payroll"])
def deliver_payroll(run_id: str, payload: PayrollAction) -> dict[str, object]:
    action_counter.labels("payroll_deliver").inc()
    return _people_call(people_service.deliver_payroll, run_id, payload.actor_id)


@app.get(
    "/api/hr/payroll/runs/{run_id}/payslips/{employee_id}", tags=["hr-payroll"]
)
def payroll_payslip(
    run_id: str, employee_id: str, actor_id: str = "HR-USER-001"
) -> Response:
    content = _people_call(people_service.payslip_pdf, run_id, employee_id, actor_id)
    filename = f"Entgeltabrechnung_{run_id}_{employee_id}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@app.get("/api/documents/{document_id}", tags=["documents"])
def get_document(document_id: str) -> FileResponse:
    state = store.get()
    document = next((doc for doc in state["documents"] if doc["id"] == document_id), None)
    if document is None:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    path = settings.document_dir / document["filename"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF wurde noch nicht erzeugt")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=path.name,
        content_disposition_type="inline",
    )


def _mes_call(function: Callable[..., dict[str, Any]], *args: Any) -> dict[str, Any]:
    try:
        return function(*args)
    except MesNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MesError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _hr_call(
    function: Callable[..., dict[str, Any]], *args: Any, **kwargs: Any
) -> dict[str, Any]:
    try:
        return function(*args, **kwargs)
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HrError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _people_call(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return function(*args, **kwargs)
    except PeopleNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PeopleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _desksharing_actor(request: Request, fallback: str) -> str:
    identity = getattr(request.state, "identity", None)
    if identity and identity.get("desksharing_user_id"):
        return str(identity["desksharing_user_id"])
    return fallback


def _desksharing_call(
    function: Callable[..., dict[str, Any]], *args: Any, **kwargs: Any
) -> dict[str, Any]:
    try:
        return function(*args, **kwargs)
    except DesksharingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DesksharingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _work_actor(request: Request) -> str:
    identity = getattr(request.state, "identity", None)
    if identity:
        return str(identity.get("name") or identity.get("username") or "Keycloak-Benutzer")
    return "Demo Benutzer"


def _work_call(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return function(*args, **kwargs)
    except WorkNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _quality_call(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return function(*args, **kwargs)
    except QualityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except QualityError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _finance_call(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return function(*args, **kwargs)
    except FinanceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FinanceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
