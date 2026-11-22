"""Routen für Agentenzentrale (FLOWAGENTS), RM-Adapter (FLOWWORK) und eigene DMS-Oberfläche (FLOWDOC)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

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
    change_class: Literal["standard", "neue_funktion", "kritisch"] = "neue_funktion"
    scope: str = Field(min_length=2, max_length=40)
    project: str = Field(default="FLOW-PLATFORM", pattern=r"^[A-Z][A-Z0-9-]{2,30}$")


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


def build_router(rm_adapter: RMAdapter, agents: AgentsHub, dms: DmsService) -> APIRouter:
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
        overview = agents.overview()
        overview["viewer"] = {k: v for k, v in (person(request) or {}).items() if k in {"username", "name", "roles"}}
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
        return forward("detail", {"run_id": run_id}, request, with_person=False)

    @router.post("/api/agents/runs", tags=["agents"], status_code=201)
    def agents_submit(payload: AgentRunCreate, request: Request) -> dict[str, Any]:
        values = payload.model_dump()
        key = values.pop("idempotency_key")
        return forward("submit", {"idempotency_key": key, "auftrag": values}, request, with_person=True)

    @router.post("/api/agents/decisions/{decision_id}", tags=["agents"])
    def agents_decide(decision_id: str, payload: AgentDecision, request: Request) -> dict[str, Any]:
        if not decision_id.replace("-", "").isalnum():
            raise HTTPException(status_code=404, detail="Entscheidung nicht gefunden")
        return forward("decide", {"decision_id": decision_id, **payload.model_dump()}, request, with_person=True)

    @router.post("/api/agents/control", tags=["agents"])
    def agents_control(payload: AgentControl, request: Request) -> dict[str, Any]:
        return forward("control", payload.model_dump(), request, with_person=True)

    @router.get("/api/agents/audit", tags=["agents"])
    def agents_audit(request: Request) -> dict[str, Any]:
        roles = set((person(request) or {}).get("roles", []))
        if not roles & {"platform-admin", "it-user", "work-admin"}:
            raise HTTPException(status_code=403, detail="Audit nur für Plattformbetrieb")
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
    def dms_binary(document_id: int, kind: Literal["thumb", "preview", "download"], request: Request) -> Response:
        data, content_type = dms_call(dms.binary, person(request), document_id, kind)
        disposition = "attachment" if kind == "download" else "inline"
        return Response(data, media_type=content_type.split(";")[0],
                        headers={"Content-Disposition": f'{disposition}; filename="flowdoc-{document_id}"',
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
