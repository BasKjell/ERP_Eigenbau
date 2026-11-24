"""Routen für Agentenzentrale (FLOWAGENTS), RM-Adapter (FLOWWORK) und eigene DMS-Oberfläche (FLOWDOC)."""

from __future__ import annotations

import contextlib
import re
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from .agent_drafts import DraftError, DraftService, verify_internal
from .agent_policy import PolicyError
from .agents_bff import AgentsHub, AgentsRejected, AgentsUnavailable
from .config import settings
from .dms import DmsError, DmsService
from .rm_adapter import RMAdapter, RMConflict, RMNotFound
from .work import WorkError

APP_DIR = Path(__file__).parent
DEMO_PERSON = {"username": "demo-admin", "name": "Lokale Funktionsdemo", "roles": ["platform-admin"],
               "department": "Demo"}


class AgentRunCreate(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_.:-]+$")
    title: str = Field(min_length=5, max_length=160)
    goal: str = Field(min_length=10, max_length=2000)
    user_group: str = Field(min_length=2, max_length=160)
    behavior: str = Field(min_length=10, max_length=3000)
    exclusions: str = Field(default="", max_length=1500)
    success_example: str = Field(min_length=5, max_length=1500)
    data_class: Literal["oeffentlich", "intern", "vertraulich"] = "intern"
    # Ohne Einstufung gilt die Änderungsklasse; mit Einstufung leitet der Orchestrator sie ab und
    # eine ausdrücklich genannte Klasse darf den Weg nur verschärfen (KI-Softwareentwicklung Teil 01).
    change_class: Literal["standard", "neue_funktion", "kritisch"] | None = None
    project_class: Literal["", "S", "M", "L"] = ""
    criticality: Literal["", "K1", "K2", "K3"] = ""
    # leer = Domäne des Projekts aus dem Projektkatalog
    domain: Literal["", "it", "produkt", "pruefsoftware", "werkzeug"] = ""
    scope: str = Field(min_length=2, max_length=40)
    project: str = Field(default="FLOW-PLATFORM", pattern=r"^[A-Z][A-Z0-9-]{2,30}$")
    execution: Literal["automatisch", "lokal", "abo"] = "automatisch"
    draft_id: str = Field(default="", max_length=20, pattern=r"^(VOR-[0-9A-F]{6})?$")


class AgentPackageStart(BaseModel):
    scope: str = Field(default="", max_length=40, pattern=r"^[a-z0-9-]*$")


class AgentDraftCreate(BaseModel):
    title: str = Field(min_length=5, max_length=160)
    goal: str = Field(min_length=10, max_length=2000)
    user_group: str = Field(default="Fachbereich", min_length=2, max_length=160)
    behavior: str = Field(min_length=10, max_length=3000)
    exclusions: str = Field(default="", max_length=1500)
    success_example: str = Field(default="", max_length=1500)
    change_class: Literal["standard", "neue_funktion", "kritisch"] = "neue_funktion"
    scope: str = Field(default="", max_length=40)
    project: str = Field(default="FLOW-DMS", pattern=r"^[A-Z][A-Z0-9-]{2,30}$")
    note: str = Field(default="", max_length=1000)


class AgentDecision(BaseModel):
    outcome: Literal["annehmen", "ablehnen"]
    comment: str = Field(default="", max_length=2000)


class AgentControl(BaseModel):
    action: Literal["pause", "resume", "cancel"]
    role: str = Field(default="", max_length=64)
    run_id: str = Field(default="", max_length=64)


class DmsNote(BaseModel):
    note: str = Field(min_length=2, max_length=2000)


class DmsTransition(BaseModel):
    action: Literal["pruefen", "freigeben", "zurueckweisen"]


def person(request: Request) -> dict[str, Any] | None:
    identity = getattr(request.state, "identity", None)
    if identity:
        return identity
    return DEMO_PERSON if settings.auth_mode != "oidc" else None


# -- Projektrechte (agents/projects.json → AD-Gruppen AD-GG-FLOW-PRJ-* → Realm-Rollen flow-prj-*) -------
OVERSIGHT_ROLES = frozenset({"platform-admin", "flow-isb", "flow-gf"})


def project_rights(catalog: dict[str, Any], user: dict[str, Any], demo_mode: bool) -> dict[str, str]:
    """Recht der Person je Katalogprojekt: aendern, lesen oder leer. Die Durchsetzung macht der Orchestrator;
    die Plattform blendet nur aus, was die Person nicht sehen darf."""
    roles = {str(r) for r in user.get("roles", [])}
    result = {}
    for code, spec in catalog.items():
        names = spec.get("roles") or {}
        if (demo_mode and "platform-admin" in roles) or names.get("aendern") in roles:
            result[code] = "aendern"
        elif names.get("lesen") in roles:
            result[code] = "lesen"
        else:
            result[code] = ""
    return result


def project_visible(catalog: dict[str, Any], user: dict[str, Any], code: str, demo_mode: bool) -> bool:
    if code not in catalog:
        return True  # Altaufträge ohne Katalogprojekt bleiben für alle sichtbar
    if {str(r) for r in user.get("roles", [])} & OVERSIGHT_ROLES:
        return True
    return bool(project_rights(catalog, user, demo_mode).get(code))


def visible_overview(overview: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    catalog = overview.get("project_catalog") or {}
    if not catalog:
        return overview
    demo = bool(overview.get("demo_mode"))

    def shown(code: Any) -> bool:
        return project_visible(catalog, user, str(code or ""), demo)

    runs = overview.get("runs") or []
    hidden = {run.get("id") for run in runs if not shown(run.get("project"))}
    result = dict(overview)
    result["runs"] = [run for run in runs if run.get("id") not in hidden]
    result["projects"] = [p for p in overview.get("projects") or [] if shown(p.get("code"))]
    result["decisions"] = [d for d in overview.get("decisions") or []
                           if d.get("run_id") not in hidden and shown((d.get("auftrag") or {}).get("project"))]
    result["events"] = [e for e in overview.get("events") or [] if e.get("run_id") not in hidden]
    result["project_catalog"] = {code: spec for code, spec in catalog.items() if shown(code)}
    if hidden:
        result["hidden_runs"] = len(hidden)
    return result


def build_router(rm_adapter: RMAdapter, agents: AgentsHub, dms: DmsService, drafts: DraftService) -> APIRouter:
    router = APIRouter()

    # -- Seiten ------------------------------------------------------------------------
    @router.get("/agents", include_in_schema=False)
    def agents_page() -> FileResponse:
        return FileResponse(APP_DIR / "static" / "agents.html")

    @router.get("/dms", include_in_schema=False)
    def dms_page() -> FileResponse:
        return FileResponse(APP_DIR / "static" / "dms.html")

    # -- RM-Adapter (Agenten-Token, kein Sitzungscookie) ------------------------------------
    operations = {
        "drafts": "rm.create_draft", "drafts/update": "rm.update_draft", "comments": "rm.comment",
        "questions": "rm.ask_owner", "tests": "rm.create_test", "links": "rm.link_trace",
        "baselines": "rm.freeze_baseline", "search": "rm.search", "tasks": "ticket.create",
    }

    @router.post("/api/rm/v1/{operation:path}", tags=["rm-adapter"])
    def rm_operation(
        operation: str,
        payload: Annotated[dict[str, Any], Body()],
        authorization: Annotated[str, Header()] = "",
    ) -> dict[str, Any]:
        name = operations.get(operation)
        if name is None:
            raise HTTPException(status_code=404, detail="Unbekannte RM-Operation")
        try:
            return rm_adapter.handle(authorization, name, payload)
        except PolicyError as exc:
            raise HTTPException(status_code=exc.status, detail=str(exc)) from None
        except RMConflict as exc:
            raise HTTPException(status_code=409, detail={"message": str(exc), "current": exc.current}) from None
        except RMNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from None
        except (ValueError, WorkError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None

    # -- Abgleich mit dem Orchestrator (Pull-Modell, Dienst-Token statt Sitzung) ---------------
    def sync_auth(authorization: str) -> None:
        try:
            agents.verify(authorization)
        except AgentsRejected as exc:
            raise HTTPException(status_code=exc.status, detail=str(exc)) from None

    @router.get("/api/agents/sync/actions", include_in_schema=False)
    def sync_actions(authorization: Annotated[str, Header()] = "") -> list[dict[str, Any]]:
        sync_auth(authorization)
        return agents.pending()

    @router.post("/api/agents/sync/results", include_in_schema=False)
    def sync_results(payload: Annotated[dict[str, Any], Body()],
                     authorization: Annotated[str, Header()] = "") -> dict[str, Any]:
        sync_auth(authorization)
        results = payload.get("results")
        if not isinstance(results, list) or len(results) > 50:
            raise HTTPException(status_code=422, detail="results fehlt")
        return {"accepted": agents.complete(results)}

    @router.post("/api/agents/sync/state", include_in_schema=False)
    def sync_state(payload: Annotated[dict[str, Any], Body()],
                   authorization: Annotated[str, Header()] = "") -> dict[str, Any]:
        sync_auth(authorization)
        overview = payload.get("overview")
        if not isinstance(overview, dict) or not isinstance(overview.get("agents"), list):
            raise HTTPException(status_code=422, detail="overview fehlt")
        agents.publish(overview, payload.get("registry") if isinstance(payload.get("registry"), dict) else None)
        return {"ok": True}

    # -- Agentenzentrale ----------------------------------------------------------------
    def forward(kind: str, payload: dict[str, Any], request: Request, *, with_person: bool) -> dict[str, Any]:
        user = person(request) if with_person else None
        if with_person and user is None:
            raise HTTPException(status_code=401, detail="Anmeldung über FLOWID erforderlich")
        try:
            return agents.request(kind, payload, user)
        except AgentsRejected as exc:
            raise HTTPException(status_code=exc.status, detail=str(exc)) from None
        except AgentsUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from None

    @router.get("/api/agents/overview", tags=["agents"])
    def agents_overview(request: Request) -> dict[str, Any]:
        viewer = person(request) or {}
        overview = visible_overview(agents.overview(), viewer)
        overview["viewer"] = {k: v for k, v in viewer.items() if k in {"username", "name", "roles"}}
        overview["viewer"]["projects"] = project_rights(overview.get("project_catalog") or {}, viewer,
                                                        bool(overview.get("demo_mode")))
        return overview

    @router.get("/api/agents/registry", tags=["agents"])
    def agents_registry() -> dict[str, Any]:
        try:
            return agents.registry()
        except AgentsUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from None

    @router.get("/api/agents/runs/{run_id}", tags=["agents"])
    def agents_run(run_id: str, request: Request) -> dict[str, Any]:
        if not run_id.replace("-", "").isalnum():
            raise HTTPException(status_code=404, detail="Lauf nicht gefunden")
        detail = forward("detail", {"run_id": run_id}, request, with_person=False)
        catalog = (agents.overview().get("project_catalog") or {})
        code = str(((detail.get("run") or {}).get("auftrag") or {}).get("project", ""))
        if not project_visible(catalog, person(request) or {}, code, bool(agents.overview().get("demo_mode"))):
            raise HTTPException(status_code=404, detail="Lauf nicht gefunden")
        return detail

    @router.post("/api/agents/runs", tags=["agents"], status_code=201)
    def agents_submit(payload: AgentRunCreate, request: Request) -> dict[str, Any]:
        values = payload.model_dump()
        key = values.pop("idempotency_key")
        draft_id = values.pop("draft_id")
        result = forward("submit", {"idempotency_key": key, "auftrag": values}, request, with_person=True)
        if draft_id:
            with contextlib.suppress(KeyError, DraftError):
                drafts.close(draft_id, "eingereicht", (person(request) or {}).get("name", ""), str(result.get("id", "")))
        return result

    # -- Vorschläge aus FLOWAI (Open WebUI) --------------------------------------------------
    def internal(authorization: str) -> None:
        try:
            verify_internal(authorization)
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from None

    @router.post("/api/agents/internal/drafts", include_in_schema=False, status_code=201)
    def internal_draft(payload: AgentDraftCreate, authorization: Annotated[str, Header()] = "") -> dict[str, Any]:
        internal(authorization)
        values = payload.model_dump()
        note = values.pop("note")
        try:
            draft = drafts.create(values, "FLOWAI (Open WebUI)", note)
        except DraftError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return {**draft, "confirm_url": f"{settings.platform_public_url}/agents?draft={draft['id']}"}

    @router.get("/api/agents/internal/status", include_in_schema=False)
    def internal_status(authorization: Annotated[str, Header()] = "") -> dict[str, Any]:
        internal(authorization)
        overview = agents.overview()
        try:
            scopes = agents.registry().get("scopes", {})
        except AgentsUnavailable:
            scopes = {}
        return {
            "orchestrator_verbunden": overview.get("available", False),
            "auftraege": [{k: r.get(k) for k in ("auftrag_id", "title", "status", "step_label", "progress",
                                                  "waiting_for", "branch", "reason")} for r in overview.get("runs", [])],
            "offene_entscheidungen": [{"titel": d.get("title"), "auftrag": (d.get("auftrag") or {}).get("id"),
                                       "rolle": d.get("decider"), "vorschau": (d.get("context") or {}).get("preview_url")}
                                      for d in overview.get("decisions", [])],
            "offene_vorschlaege": [{"id": d["id"], "title": d["title"]} for d in drafts.open()],
            "aenderungsbereiche": scopes,
        }

    @router.get("/api/agents/drafts", tags=["agents"])
    def list_drafts() -> dict[str, Any]:
        return {"drafts": drafts.open()}

    @router.get("/api/agents/drafts/{draft_id}", tags=["agents"])
    def get_draft(draft_id: str) -> dict[str, Any]:
        try:
            return drafts.get(draft_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Vorschlag nicht gefunden") from None

    @router.post("/api/agents/drafts/{draft_id}/discard", tags=["agents"])
    def discard_draft(draft_id: str, request: Request) -> dict[str, Any]:
        try:
            return drafts.close(draft_id, "verworfen", (person(request) or {}).get("name", ""))
        except KeyError:
            raise HTTPException(status_code=404, detail="Vorschlag nicht gefunden") from None
        except DraftError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None

    @router.post("/api/agents/decisions/{decision_id}", tags=["agents"])
    def agents_decide(decision_id: str, payload: AgentDecision, request: Request) -> dict[str, Any]:
        if not decision_id.replace("-", "").isalnum():
            raise HTTPException(status_code=404, detail="Entscheidung nicht gefunden")
        return forward("decide", {"decision_id": decision_id, **payload.model_dump()}, request, with_person=True)

    @router.post("/api/agents/projects/{project_id}/packages/{key}/start", tags=["agents"], status_code=201)
    def agents_start_package(project_id: str, key: str, payload: AgentPackageStart, request: Request) -> dict[str, Any]:
        """EPi „Iteration geplant“: ein Arbeitspaket als eigenen Auftrag starten (Product Owner oder Tech Lead)."""
        if not re.fullmatch(r"PRJ-(?:[0-9]{3,6}|[A-Z][A-Z0-9-]{2,30})", project_id) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,40}", key):
            raise HTTPException(status_code=404, detail="Arbeitspaket nicht gefunden")
        return forward("start_package", {"project_id": project_id, "package_key": key, "scope": payload.scope},
                       request, with_person=True)

    @router.post("/api/agents/control", tags=["agents"])
    def agents_control(payload: AgentControl, request: Request) -> dict[str, Any]:
        return forward("control", payload.model_dump(), request, with_person=True)

    @router.get("/api/agents/audit", tags=["agents"])
    def agents_audit(request: Request) -> dict[str, Any]:
        roles = set((person(request) or {}).get("roles", []))
        if not roles & {"platform-admin", "it-user", "work-admin", "flow-techlead", "flow-isb"}:
            raise HTTPException(status_code=403, detail="Audit nur für Plattformbetrieb, Tech Lead und ISB")
        return {"entries": rm_adapter.audit(150)}

    # -- FLOWDOC (eigene DMS-Oberfläche) ---------------------------------------------------
    def dms_call(function, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
        try:
            return function(*args, **kwargs)
        except DmsError as exc:
            raise HTTPException(status_code=exc.status, detail=str(exc)) from None

    @router.get("/api/dms/metadata", tags=["dms"])
    def dms_metadata(request: Request) -> dict[str, Any]:
        return dms_call(dms.metadata, person(request))

    @router.get("/api/dms/documents", tags=["dms"])
    def dms_search(
        request: Request, q: str = "", document_type: int | None = None, tag: int | None = None,
        correspondent: int | None = None, status: str = "", ordering: str = "-created", page: int = 1,
    ) -> dict[str, Any]:
        return dms_call(dms.search, person(request), query=q, document_type=document_type, tag=tag,
                        correspondent=correspondent, status=status, ordering=ordering, page=page)

    @router.get("/api/dms/documents/{document_id}", tags=["dms"])
    def dms_document(document_id: int, request: Request) -> dict[str, Any]:
        return dms_call(dms.document, person(request), document_id)

    @router.get("/api/dms/documents/{document_id}/{kind}", tags=["dms"])
    def dms_binary(document_id: int, kind: Literal["thumb", "preview", "download", "original"],
                   request: Request) -> Response:
        data, content_type = dms_call(dms.binary, person(request), document_id, kind)
        disposition = "attachment" if kind in {"download", "original"} else "inline"
        filename = f"flowdoc-{document_id}"
        if kind == "original" and "name=" in content_type:
            filename = content_type.split("name=", 1)[1]
        return Response(data, media_type=content_type.split(";")[0],
                        headers={"Content-Disposition": f'{disposition}; filename="{filename}"',
                                 "Cache-Control": "private, no-store"})

    @router.post("/api/dms/upload", tags=["dms"], status_code=202)
    async def dms_upload(
        request: Request,
        document: Annotated[UploadFile, File()],
        title: Annotated[str, Form(max_length=160)] = "",
        document_type: Annotated[int | None, Form()] = None,
        tags: Annotated[str, Form(max_length=200)] = "",
    ) -> dict[str, Any]:
        content = await document.read(25 * 1024 * 1024 + 1)
        tag_ids = [int(item) for item in tags.split(",") if item.strip().isdigit()][:10]
        return dms_call(dms.upload, person(request), content, document.filename or "dokument.pdf", title,
                        document_type, tag_ids)

    @router.get("/api/dms/tasks/{task_id}", tags=["dms"])
    def dms_task(task_id: str, request: Request) -> dict[str, Any]:
        return dms_call(dms.task, person(request), task_id)

    @router.post("/api/dms/documents/{document_id}/notes", tags=["dms"])
    def dms_note(document_id: int, payload: DmsNote, request: Request) -> dict[str, Any]:
        return dms_call(dms.add_note, person(request), document_id, payload.note)

    @router.post("/api/dms/documents/{document_id}/transition", tags=["dms"])
    def dms_transition(document_id: int, payload: DmsTransition, request: Request) -> dict[str, Any]:
        return dms_call(dms.transition, person(request), document_id, payload.action)

    return router


def reject_agent_token_for_work(request: Request) -> JSONResponse | None:
    """Agenten erhalten über FLOWWORK keine Freigabe- oder Änderungswege außerhalb des Adapters (Test 09)."""
    if request.url.path.startswith("/api/work") and request.headers.get("authorization", "").startswith("Bearer "):
        return JSONResponse(status_code=403, content={"detail": "Agenten erteilen keine Freigaben; nur der RM-Adapter ist zulässig"})
    return None
