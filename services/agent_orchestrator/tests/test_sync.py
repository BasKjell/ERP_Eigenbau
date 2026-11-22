"""Abgleich mit FLOWPORTAL im Pull-Modell (REQ-AGT-013)."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import jwt

from flowagents.sync import AUDIENCE, PlatformSync

from .conftest import KEY_USER, NOBODY, PO, auftrag, drive

SECRET = "sync-secret-0123456789-0123456789-abcd"


class FakePortal(BaseHTTPRequestHandler):
    actions: list[dict] = []
    results: list[dict] = []
    states: list[dict] = []
    tokens: list[dict] = []

    def _auth(self) -> bool:
        header = self.headers.get("Authorization", "")
        try:
            FakePortal.tokens.append(jwt.decode(header[7:], SECRET, algorithms=["HS256"], audience=AUDIENCE))
            return True
        except jwt.PyJWTError:
            self.send_response(401)
            self.end_headers()
            return False

    def _json(self, payload: object) -> None:
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self._auth():
            actions, FakePortal.actions = FakePortal.actions, []
            self._json(actions)

    def do_POST(self) -> None:  # noqa: N802
        if not self._auth():
            return
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        (FakePortal.results if self.path.endswith("/results") else FakePortal.states).append(body)
        self._json({"ok": True})

    def log_message(self, *args) -> None:  # noqa: ANN002
        return


def test_sync_pulls_actions_and_publishes_state(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    server = HTTPServer(("127.0.0.1", 0), FakePortal)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        sync = PlatformSync(engine, f"http://127.0.0.1:{server.server_port}", SECRET)
        FakePortal.actions = [
            {"id": "a1", "kind": "submit", "person": PO, "payload": {"idempotency_key": "sync-key-0001", "auftrag": auftrag()}},
            {"id": "a2", "kind": "submit", "person": NOBODY, "payload": {"idempotency_key": "sync-key-0002", "auftrag": auftrag()}},
            {"id": "a3", "kind": "submit", "person": None, "payload": {"idempotency_key": "sync-key-0003", "auftrag": auftrag()}},
            {"id": "a4", "kind": "delete", "person": PO, "payload": {}},
        ]
        assert sync.once() == 4
        results = {r["id"]: r for r in FakePortal.results[-1]["results"]}
        assert results["a1"]["status"] == 201 and results["a1"]["body"]["auftrag_id"] == "A-001"
        assert results["a2"]["status"] == 403 and results["a3"]["status"] == 403 and results["a4"]["status"] == 400
        state = FakePortal.states[-1]
        assert state["overview"]["runs"][0]["auftrag_id"] == "A-001"
        assert state["registry"]["scopes"]["doku"]["label"] == "Doku"
        assert all(token["iss"] == "flow-agents" and token["exp"] - token["iat"] <= 60 for token in FakePortal.tokens)

        run_id = results["a1"]["body"]["id"]
        drive(engine)
        decision = engine.store.decisions(status="offen", run_id=run_id)[0]
        FakePortal.actions = [
            {"id": "b1", "kind": "detail", "person": None, "payload": {"run_id": run_id}},
            {"id": "b2", "kind": "decide", "person": NOBODY, "payload": {"decision_id": decision["id"], "outcome": "annehmen"}},
            {"id": "b3", "kind": "decide", "person": KEY_USER,
             "payload": {"decision_id": decision["id"], "outcome": "annehmen", "comment": "geprüft"}},
            {"id": "b4", "kind": "detail", "person": None, "payload": {"run_id": "RUN-unbekannt"}},
        ]
        sync.once()
        results = {r["id"]: r for r in FakePortal.results[-1]["results"]}
        assert results["b1"]["status"] == 200 and results["b1"]["body"]["run"]["id"] == run_id
        assert results["b2"]["status"] == 403
        assert results["b3"]["status"] == 200 and results["b3"]["body"]["status"] == "angenommen"
        assert results["b4"]["status"] == 404
    finally:
        server.shutdown()


def test_sync_reports_unreachable_portal_without_crashing(make_engine) -> None:  # noqa: ANN001
    engine = make_engine()
    sync = PlatformSync(engine, "http://127.0.0.1:9", SECRET, timeout=1)
    stop = threading.Event()
    thread = threading.Thread(target=sync.run, args=(stop, 0.05))
    thread.start()
    stop.wait(0.3)
    stop.set()
    thread.join(3)
    assert not sync.connected and "nicht erreichbar" in sync.last_error
    assert any(e["kind"] == "fehler" for e in engine.store.events())
