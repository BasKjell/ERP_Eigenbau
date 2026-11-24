"""Führt geprüfte Klickpfade (siehe flowagents/uicheck.py) gegen die Vorschau aus.

Eingabe (stdin): {"base_url": "...", "scenarios": [{"key", "title", "steps": [...]}]}
Ausgabe (stdout): {"scenarios": [{"key", "title", "passed", "steps": [{do, ok, note}], "screenshots": [...]}]}
Nur Adressen unter base_url werden geladen; alle anderen Anfragen blockiert der Browser.
"""

from __future__ import annotations

import base64
import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Error, Page, sync_playwright

STEP_TIMEOUT = 10_000
STL = "solid wuerfel\n" + "".join(
    f"facet normal 0 0 0\n outer loop\n  vertex {a}\n  vertex {b}\n  vertex {c}\n endloop\nendfacet\n"
    for a, b, c in [("0 0 0", "1 0 0", "1 1 0"), ("0 0 0", "1 1 0", "0 1 0")]
) + "endsolid wuerfel\n"
PDF = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
       b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def fixtures(root: Path) -> dict[str, Path]:
    files = {"beispiel.stl": STL.encode(), "beispiel.pdf": PDF, "beispiel.png": PNG, "beispiel.txt": b"Testdatei\n"}
    paths = {}
    for name, data in files.items():
        path = root / name
        path.write_bytes(data)
        paths[name] = path
    return paths


def locate(page: Page, step: dict[str, str]):  # noqa: ANN201
    if step.get("role"):
        return page.get_by_role(step["role"], name=step["name"]).first
    if step.get("label"):
        return page.get_by_label(step["label"]).first
    if step.get("placeholder"):
        return page.get_by_placeholder(step["placeholder"]).first
    return page.get_by_text(step["text"]).first


def shot(page: Page, name: str) -> dict[str, str]:
    data = page.screenshot(type="jpeg", quality=60, full_page=False)
    return {"name": name, "data": base64.b64encode(data).decode()}


def run_scenario(page: Page, base: str, scenario: dict, files: dict[str, Path]) -> dict:
    results, shots, passed = [], [], True
    for step in scenario["steps"]:
        action, note = step["do"], ""
        try:
            if action == "goto":
                page.goto(base + step["path"], wait_until="networkidle", timeout=STEP_TIMEOUT * 2)
            elif action == "click":
                locate(page, step).click(timeout=STEP_TIMEOUT)
                page.wait_for_load_state("networkidle", timeout=STEP_TIMEOUT)
            elif action == "fill":
                target = locate(page, step)
                if target.evaluate("e => e.tagName", timeout=STEP_TIMEOUT) == "SELECT":
                    # Kleine lokale Modelle verwechseln Auswahllisten mit Textfeldern: Option wählen.
                    target.select_option(label=step["value"], timeout=STEP_TIMEOUT)
                    note = "Auswahlliste: Option gewählt"
                else:
                    target.fill(step["value"], timeout=STEP_TIMEOUT)
            elif action == "select":
                locate(page, step).select_option(label=step["value"], timeout=STEP_TIMEOUT)
            elif action == "upload":
                locate(page, step).set_input_files(str(files[step["fixture"]]), timeout=STEP_TIMEOUT)
            elif action == "expect_text":
                option = page.locator("select option", has_text=step["text"])
                if option.count():
                    # Optionen einer Auswahlliste sind nie „sichtbar“; vorhanden genügt.
                    note = "Option der Auswahlliste vorhanden"
                else:
                    page.get_by_text(step["text"]).first.wait_for(state="visible", timeout=STEP_TIMEOUT)
            elif action == "expect_visible":
                locate(page, step).wait_for(state="visible", timeout=STEP_TIMEOUT)
            elif action == "screenshot":
                shots.append(shot(page, step.get("name", "bild")))
            ok = True
        except (Error, KeyError) as exc:
            ok, passed = False, False
            note = str(exc).splitlines()[0][:200]
        results.append({"do": action, "ok": ok, "note": note})
        if not ok:
            shots.append(shot(page, "fehler"))
            break
    if passed and not shots:
        shots.append(shot(page, "ende"))
    return {"key": scenario.get("key", ""), "title": scenario.get("title", ""), "passed": passed,
            "steps": results, "screenshots": shots}


def main() -> int:
    job = json.loads(sys.stdin.read())
    base = str(job["base_url"]).rstrip("/")
    origin = urlparse(base)
    report = []
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as playwright:
        files = fixtures(Path(tmp))
        browser = playwright.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        for scenario in job["scenarios"]:
            context = browser.new_context(viewport={"width": 1280, "height": 800}, locale="de-DE")

            blocked: list[str] = []

            def guard(route, request, blocked=blocked):  # noqa: ANN001, ANN202
                target = urlparse(request.url)
                same = (target.scheme, target.netloc) == (origin.scheme, origin.netloc) or target.scheme == "data"
                if not same:
                    return route.abort()
                if request.method not in {"GET", "HEAD", "OPTIONS"} and not job.get("allow_writes"):
                    # Die Vorschau spricht mit dem echten Paperless: Schreiben bleibt gesperrt.
                    blocked.append(f"{request.method} {target.path}")
                    return route.fulfill(status=423, content_type="application/json",
                                         body='{"detail":"Klickprüfung: Schreibzugriff in der Vorschau gesperrt"}')
                return route.continue_()

            context.route("**/*", guard)
            page = context.new_page()
            result = run_scenario(page, base, scenario, files)
            if blocked:
                result["steps"].append({"do": "hinweis", "ok": True,
                                        "note": "Schreibzugriffe gesperrt: " + ", ".join(sorted(set(blocked)))[:180]})
            report.append(result)
            context.close()
        browser.close()
    print(json.dumps({"scenarios": report}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
