from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel, Field

from .assistant import answer_question
from .config import settings
from .integrations import integration_status, paperless_search
from .store import ScenarioStore

APP_DIR = Path(__file__).parent
store = ScenarioStore(settings.data_file, settings.seed_file)
action_counter = Counter("demo_actions_total", "Management demo actions", ["action"])

app = FastAPI(
    title="Open Manufacturing Platform API",
    version="1.0.0",
    description="Integration Layer fuer ERPNext, Paperless, MES und Management-Demo.",
)
app.mount("/assets", StaticFiles(directory=APP_DIR / "static"), name="assets")


class Question(BaseModel):
    question: str = Field(min_length=2, max_length=500)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(APP_DIR / "static" / "index.html")


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "platform-api"}


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/demo", tags=["demo"])
def get_demo() -> dict[str, object]:
    return store.get()


@app.post("/api/demo/reset", tags=["demo"])
def reset_demo() -> dict[str, object]:
    action_counter.labels("reset").inc()
    return store.reset()


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


@app.get("/api/documents/{document_id}", tags=["documents"])
def get_document(document_id: str) -> FileResponse:
    state = store.get()
    document = next((doc for doc in state["documents"] if doc["id"] == document_id), None)
    if document is None:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    path = settings.document_dir / document["filename"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF wurde noch nicht erzeugt")
    return FileResponse(path, media_type="application/pdf", filename=path.name)
