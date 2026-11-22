"""HTTP-Schnittstelle des Orchestrators für FLOWPORTAL (nur über die Plattform-API erreichbar).

Jeder Aufruf außer ``/health`` braucht ein kurzlebiges HS256-Token der Plattform-API
(``aud=flow-agents-api``). Für Aufträge, Entscheidungen und Steuerung trägt es die geprüfte
Identität der angemeldeten Person (``user``). Die Engine prüft die Befugnis erneut.
"""


import threading
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .config import Runtime
from .engine import EngineError

AUDIENCE = "flow-agents-api"


class SubmitBody(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=80)
    auftrag: dict[str, Any]


class DecisionBody(BaseModel):
    outcome: str = Field(pattern="^(annehmen|ablehnen)$")
    comment: str = Field(default="", max_length=2000)


class ControlBody(BaseModel):
    action: str = Field(pattern="^(pause|resume|cancel)$")
    role: str = Field(default="", max_length=64)
    run_id: str = Field(default="", max_length=64)


def create_app(runtime: Runtime, *, start_worker: bool = True) -> FastAPI:
    engine = runtime.engine
    stop = threading.Event()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if start_worker:
            threading.Thread(target=worker, name="flow-agents-engine", daemon=True).start()
        yield
        stop.set()

    app = FastAPI(title="FLOWAGENTS Orchestrator", version="0.1.0", docs_url=None, redoc_url=None, lifespan=lifespan)

    def caller(authorization: str = Header(default="")) -> dict[str, Any]:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Token fehlt")
        try:
            claims = jwt.decode(authorization[7:], runtime.api_secret, algorithms=["HS256"], audience=AUDIENCE,
                                options={"require": ["exp", "iat", "aud", "iss"]})
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Token ungültig") from None
        if claims.get("iss") != "flow-platform-api" or claims["exp"] - claims["iat"] > 600:
            raise HTTPException(status_code=401, detail="Token ungültig")
        return claims

    Caller = Annotated[dict[str, Any], Depends(caller)]

    def person(claims: dict[str, Any]) -> dict[str, Any]:
        user = claims.get("user")
        if not isinstance(user, dict) or not user.get("username"):
            raise HTTPException(status_code=403, detail="Aktion braucht eine angemeldete Person")
        return user

    def worker() -> None:
        engine.recover()
        while not stop.is_set():
            try:
                worked = engine.cycle()
            except Exception as exc:  # noqa: BLE001 - der Dienst bleibt stehen, nicht der Prozess
                runtime.store.event(None, "fehler", "orchestrator", "orchestrator",
                                    f"Unerwarteter Fehler: {type(exc).__name__}", {})
                worked = False
            if not worked:
                stop.wait(runtime.poll_seconds)

    @app.middleware("http")
    async def _headers(request: Request, call_next):  # noqa: ANN001, ANN202
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "service": "flow-agents", "control": runtime.store.control("global", "bereit"),
                "time": time.time()}

    @app.get("/v1/overview")
    def overview(_: Caller) -> dict[str, Any]:
        return engine.overview()

    @app.get("/v1/registry")
    def registry(_: Caller) -> dict[str, Any]:
        return {**engine.registry.public(), "scopes": {k: {"label": v.get("label", k)} for k, v in engine.scopes.items()}}

    @app.get("/v1/runs/{run_id}")
    def run(run_id: str, _: Caller) -> dict[str, Any]:
        try:
            return engine.run_detail(run_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Lauf nicht gefunden") from None

    @app.get("/v1/events")
    def events(_: Caller, after: int = 0, run_id: str | None = None) -> dict[str, Any]:
        return {"events": runtime.store.events(after=after, run_id=run_id, limit=200)}

    @app.post("/v1/runs", status_code=201)
    def submit(body: SubmitBody, claims: Caller) -> dict[str, Any]:
        try:
            return engine.submit(body.auftrag, person(claims), body.idempotency_key)
        except EngineError as exc:
            raise HTTPException(status_code=403 if "Befugnis" in str(exc) else 422, detail=str(exc)) from None

    @app.post("/v1/decisions/{decision_id}")
    def decide(decision_id: str, body: DecisionBody, claims: Caller) -> dict[str, Any]:
        try:
            return engine.decide(decision_id, person(claims), body.outcome, body.comment)
        except EngineError as exc:
            raise HTTPException(status_code=403 if "Befugnis" in str(exc) else 409, detail=str(exc)) from None

    @app.post("/v1/control")
    def control(body: ControlBody, claims: Caller) -> dict[str, Any]:
        try:
            engine.control(body.action, person(claims), role=body.role, run_id=body.run_id)
        except (EngineError, KeyError) as exc:
            raise HTTPException(status_code=403 if "Steuerung" in str(exc) else 409, detail=str(exc)) from None
        return {"ok": True, "controls": runtime.store.controls()}

    return app
