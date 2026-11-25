"""Routen für Agentenzentrale (FLOWAGENTS), RM-Adapter (FLOWWORK) und eigene DMS-Oberfläche (FLOWDOC)."""

from __future__ import annotations

import contextlib
import re
from collections.abc import Callable
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


class BusinessAgentSave(BaseModel):
    agent_id: str = Field(default="", pattern=r"^(FA-[0-9]{3,5})?$")
    spec: dict[str, Any]


class BusinessDesign(BaseModel):
    description: str = Field(min_length=15, max_length=3000)


class BusinessTask(BaseModel):
    input: dict[str, str] = Field(max_length=6)


class BusinessDecision(BaseModel):
    outcome: Literal["freigeben", "verwerfen"]
    edited: dict[str, str] = Field(default_factory=dict, max_length=10)
    comment: str = Field(default="", max_length=500)


class AgentConfigUpdate(BaseModel):
    # Feld -> neuer Wert, null setzt auf das Register zurück. Form und Inhalt prüft der Orchestrator.
    changes: dict[str, Any] = Field(min_length=1, max_length=20)
    reason: str = Field(min_length=5, max_length=500)


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
    execution: Literal["automatisch", "lokal", "abo", "opencode"] = "automatisch"
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
    # Anonyme Plattformrechte nur in der ausdrücklich gewählten lokalen Demo (Loopback, beim Start geprüft).
    return DEMO_PERSON if settings.auth_mode == "demo" else None


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


def project_visible(catalog: dict[str, Any], user: dict[str, Any], code: str, demo_mode: bool,
                    bound: bool = False) -> bool:
    """Darf die Person Läufe dieses Projekts sehen? Nur nie gebundene Altaufträge sind offen;
    eine Katalogbindung bleibt geschützt, auch wenn das Projekt im Katalog fehlt."""
    if {str(r) for r in user.get("roles", [])} & OVERSIGHT_ROLES:
        return True
    if code in catalog:
        return bool(project_rights(catalog, user, demo_mode).get(code))
    return not bound


def visible_overview(overview: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    """Alle personenbezogenen Teile der Übersicht aus derselben berechtigten Laufmenge bilden.

    Grundlage ist ``access.runs`` (Projektbindung jedes Laufs, der in der Übersicht vorkommt). Ein
    Lauf ohne Eintrag gilt als nicht sichtbar (fail closed).
    """
    catalog = overview.get("project_catalog") or {}
    demo = bool(overview.get("demo_mode"))
    access = (overview.get("access") or {}).get("runs") or {}
    project_access = (overview.get("access") or {}).get("projects") or {}

    def run_ok(run_id: Any) -> bool:
        if not run_id:
            return True  # Ereignisse ohne Lauf (Betrieb, Steuerung)
        info = access.get(str(run_id))
        return bool(info) and project_visible(catalog, user, str(info.get("project", "")), demo, bool(info.get("bound")))

    result = dict(overview)
    runs = overview.get("runs") or []
    result["runs"] = [run for run in runs if run_ok(run.get("id"))]
    result["projects"] = [p for p in overview.get("projects") or []
                          if run_ok(p.get("run_id")) and project_visible(
                              catalog, user, str(p.get("code") or ""), demo,
                              bool((project_access.get(str(p.get("id"))) or {}).get("bound")))]
    result["decisions"] = [d for d in overview.get("decisions") or [] if run_ok(d.get("run_id"))]
    result["events"] = [e for e in overview.get("events") or [] if run_ok(e.get("run_id"))]
    usage = dict(overview.get("usage") or {})
    usage["by_run"] = [u for u in usage.get("by_run") or [] if run_ok(u.get("run_id"))]
    result["usage"] = usage
    agents = []
    for agent in overview.get("agents") or []:
        agent = dict(agent)
        if agent.get("current") and not run_ok(agent["current"].get("run_id")):
            agent["current"] = None  # Agent arbeitet für ein fremdes Projekt: Zustand ja, Auftrag nein
        if agent.get("last") and not run_ok(agent["last"].get("run_id")):
            agent["last"] = None
        agents.append(agent)
    result["agents"] = agents
    result["project_catalog"] = {code: spec for code, spec in catalog.items()
                                 if project_visible(catalog, user, code, demo, True)}
    metrics = dict(overview.get("metrics") or {})
    metrics.update({
        "runs_open": sum(1 for r in result["runs"] if r.get("status") in {"aktiv", "wartet", "blockiert", "pausiert"}),
        "runs_done": sum(1 for r in result["runs"] if r.get("completion") == "produktion"),
        "decisions_open": len(result["decisions"]),
    })
    result["metrics"] = metrics
    result.pop("access", None)
    hidden = len(runs) - len(result["runs"])
    if hidden:
        result["hidden_runs"] = hidden
    return result


SERVICE_IDENTITY: dict[str, Any] = {"username": "", "roles": []}


# -- Fachagenten: Sichtbarkeit und Hintergrunddaten ------------------------------------------
def _viewer_roles(user: dict[str, Any]) -> set[str]:
    return {str(r) for r in user.get("roles", [])}


def business_for(business: dict[str, Any] | None, user: dict[str, Any]) -> dict[str, Any]:
    """Fachagenten und Aufgaben, die diese Person sehen darf: Admins alles, sonst zugewiesene Agenten und eigene Aufgaben."""
    business = dict(business or {})
    roles, username = _viewer_roles(user), str(user.get("username") or "")
    admin = "platform-admin" in roles
    agents = [a for a in business.get("agents") or []
              if admin or username in a.get("assigned_users", []) or roles & set(a.get("assigned_roles", []))]
    visible = {a["id"] for a in agents}
    jobs = []
    for job in business.get("jobs") or []:
        mine = (job.get("requested_by") or {}).get("username") == username
        if (admin and job.get("kind") == "entwurf") or (job.get("agent_id") in visible and (mine or admin)):
            jobs.append({**job, "input": {k: v for k, v in (job.get("input") or {}).items() if not k.startswith("_")}})
    if not admin:
        agents = [{k: v for k, v in a.items() if k not in {"prompt"}} for a in agents]
    return {**business, "agents": agents, "jobs": jobs, "can_admin": admin}


def business_context(sources: list[str], allowed: dict[str, Any], user: dict[str, Any],
                     scenario: Callable[[], dict[str, Any]] | None) -> dict[str, Any]:
    """Hintergrunddaten je Quelle – nur, wenn die Person selbst eine der berechtigten Rollen hat."""
    if scenario is None:
        return {}
    data, roles, context = scenario(), _viewer_roles(user), {}
    for source in sources:
        if not roles & set((allowed.get(source) or {}).get("roles", [])):
            continue
        if source == "einkauf":
            context[source] = {"bestellungen": (data.get("purchase_orders") or [])[:25],
                               "lieferhistorie": ((data.get("workplace") or {}).get("supplier_delivery_history") or [])[:25],
                               "zahlungsbedingungen": ((data.get("commercial_master_data") or {}).get("payment_terms") or [])[:10]}
        elif source == "qualitaet":
            quality = data.get("quality") or {}
            context[source] = {"wareneingang": (quality.get("receipts") or [])[:20],
                               "abweichungen": (quality.get("ncrs") or [])[:20]}
        elif source == "auftrag":
            context[source] = {"auftrag": data.get("order") or {}, "fertigung": ((data.get("mes") or {}).get("jobs") or [])[:20]}
    return context


def build_router(rm_adapter: RMAdapter, agents: AgentsHub, dms: DmsService, drafts: DraftService,
                 scenario: Callable[[], dict[str, Any]] | None = None) -> APIRouter:
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
        overview["business"] = business_for(overview.get("business"), viewer)
        return overview

    # -- Fachagenten ------------------------------------------------------------------------
    def require_admin(request: Request) -> dict[str, Any]:
        viewer = person(request)
        if viewer is None:
            raise HTTPException(status_code=401, detail="Anmeldung über FLOWID erforderlich")
        if "platform-admin" not in _viewer_roles(viewer):
            raise HTTPException(status_code=403, detail="Fachagenten legen nur Administratoren an")
        return viewer

    @router.get("/api/agents/fachagenten", tags=["agents"])
    def business_list(request: Request) -> dict[str, Any]:
        viewer = person(request) or {}
        result = business_for(agents.overview().get("business"), viewer)
        if result["can_admin"] and scenario is not None:
            iam = scenario().get("iam") or {}
            result["directory"] = {
                "groups": [{"name": g.get("name"), "role": g.get("role"), "description": g.get("description")}
                           for g in (iam.get("directory") or {}).get("groups") or []],
                "users": [{"username": u.get("username"), "name": u.get("name"), "department": u.get("department")}
                          for u in [*(iam.get("users") or []), *(iam.get("demo_accounts") or [])]],
            }
        return result

    @router.post("/api/agents/fachagenten", tags=["agents"])
    def business_save(payload: BusinessAgentSave, request: Request) -> dict[str, Any]:
        require_admin(request)
        return forward("fa_save", payload.model_dump(), request, with_person=True)

    @router.post("/api/agents/fachagenten/entwurf", tags=["agents"], status_code=201)
    def business_design(payload: BusinessDesign, request: Request) -> dict[str, Any]:
        require_admin(request)
        return forward("fa_design", payload.model_dump(), request, with_person=True)

    @router.post("/api/agents/fachagenten/{agent_id}/aufgaben", tags=["agents"], status_code=201)
    def business_task(agent_id: str, payload: BusinessTask, request: Request) -> dict[str, Any]:
        if not re.fullmatch(r"FA-[0-9]{3,5}", agent_id):
            raise HTTPException(status_code=404, detail="Fachagent nicht gefunden")
        viewer = person(request)
        if viewer is None:
            raise HTTPException(status_code=401, detail="Anmeldung über FLOWID erforderlich")
        business = agents.overview().get("business") or {}
        spec = next((a for a in business.get("agents") or [] if a.get("id") == agent_id), None)
        if spec is None:
            raise HTTPException(status_code=404, detail="Fachagent nicht gefunden")
        context = business_context(list(spec.get("context_sources") or []), business.get("sources") or {}, viewer, scenario)
        return forward("fa_task", {"agent_id": agent_id, "input": payload.input, "context": context}, request,
                       with_person=True)

    @router.post("/api/agents/fachagenten/aufgaben/{job_id}/entscheidung", tags=["agents"])
    def business_decide(job_id: str, payload: BusinessDecision, request: Request) -> dict[str, Any]:
        if not re.fullmatch(r"FJ-[0-9]{8}-[0-9A-F]{6}", job_id):
            raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden")
        return forward("fa_decide", {"job_id": job_id, **payload.model_dump()}, request, with_person=True)

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
        # Der Orchestrator prüft die Detailrechte mit der Identität der anfragenden Person.
        detail = forward("detail", {"run_id": run_id}, request, with_person=True)
        catalog = (agents.overview().get("project_catalog") or {})
        auftrag = (detail.get("run") or {}).get("auftrag") or {}
        bound = bool(auftrag.get("catalog_bound") or auftrag.get("catalog"))
        if not project_visible(catalog, person(request) or {}, str(auftrag.get("project", "")),
                               bool(agents.overview().get("demo_mode")), bound):
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
        # FLOWAI ruft mit Dienstrecht ohne Person: nur Altaufträge ohne Projektbindung, keine Projektdaten.
        full = agents.overview()
        overview = visible_overview(full, SERVICE_IDENTITY)
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
            "geschuetzte_projektauftraege": overview.get("hidden_runs", 0),
            "hinweis": "Aufträge in Katalogprojekten sieht nur, wer im Portal das Projektrecht hat.",
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

    @router.get("/api/agents/agents/{role}/config", tags=["agents"])
    def agents_config(role: str, request: Request) -> dict[str, Any]:
        """Konfiguration eines Agenten – für alle Angemeldeten lesbar."""
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,40}", role):
            raise HTTPException(status_code=404, detail="Agent nicht gefunden")
        result = forward("agent_config", {"role": role}, request, with_person=False)
        viewer = {str(r) for r in (person(request) or {}).get("roles", [])}
        result["can_edit"] = "platform-admin" in viewer
        return result

    @router.put("/api/agents/agents/{role}/config", tags=["agents"])
    def agents_config_update(role: str, payload: AgentConfigUpdate, request: Request) -> dict[str, Any]:
        """Agenteneigenschaften ändern – nur Administratoren; der Orchestrator prüft erneut."""
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,40}", role):
            raise HTTPException(status_code=404, detail="Agent nicht gefunden")
        viewer = person(request)
        if viewer is None:
            raise HTTPException(status_code=401, detail="Anmeldung über FLOWID erforderlich")
        if "platform-admin" not in {str(r) for r in viewer.get("roles", [])}:
            raise HTTPException(status_code=403, detail="Agenteneigenschaften ändern nur Administratoren")
        result = forward("agent_update", {"role": role, **payload.model_dump()}, request, with_person=True)
        result["can_edit"] = True
        return result

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
