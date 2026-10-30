#!/usr/bin/env python3
"""Minimal HTTP smoke test for a running local demo."""

from __future__ import annotations

import json
import os
import urllib.request

BASE_URL = os.getenv("DEMO_BASE_URL", "http://localhost:8088").rstrip("/")


def request(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


health = request("/health")
assert health["status"] == "ok"
state = request("/api/demo")
assert state["order"]["id"] == "SO-4711"
answer = request("/api/assistant/ask", "POST", {"question": "Wie ist der Status von Auftrag 4711?"})
assert answer["sources"]
print("Smoke test passed: portal, scenario and assistant are healthy")
