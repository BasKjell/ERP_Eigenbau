#!/usr/bin/env python3
"""Audit every user-facing local demo link without following SSO redirects."""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request


HOST = os.getenv("DEMO_HOST", "localhost")


def url(port: int, path: str = "/") -> str:
    return f"http://{HOST}:{port}{path}"


LINKS = {
    "FLOWPORTAL": url(8088),
    "FLOWMANAGE": url(8088, "/management?managementDemo=1&tourStep=0"),
    "FLOWWORK": url(8088, "/work?view=requirements"),
    "FLOWQ": url(8088, "/quality?receipt=PREC-2027-0045"),
    "FLOWMES": url(8088, "/mes"),
    "FLOWHR": url(8088, "/hr?view=calendar"),
    "FLOWSPACE": url(
        8088,
        "/desksharing?date=2026-11-05&site=BER&floor=EG&room=BER-EG-TEAM",
    ),
    "FLOWFIN": url(8088, "/finance?view=revenue"),
    "FLOWERP Opportunity": url(8081, "/app/opportunity/OPP-2027-0018"),
    "FLOWERP Work Orders": url(8081, "/app/work-order"),
    "FLOWDOC": url(8010, "/dashboard"),
    "FLOWDOCS": url(8001, "/user-guides/presentation/"),
    "FLOWTASK": url(8011, "/projects/scu-100/issues"),
    "FLOWID Konto": url(8082, "/realms/open-manufacturing/account/"),
    "FLOWID Administration": url(
        8082, "/admin/open-manufacturing/console/#/open-manufacturing/groups"
    ),
    "FLOWINSIGHT": url(3000, "/d/management-executive"),
    "FLOWAI": url(3001),
    "FLOWGATE": url(4001, "/ui/llm/models"),
    "FLOWOPS": url(9090, "/query"),
    "FLOWAPI": url(8088, "/docs"),
    "OpenAPI": url(8088, "/openapi.json"),
    "Liveness": url(8088, "/health"),
    "Readiness": url(8088, "/ready"),
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def response_code(target: str) -> int:
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(target, headers={"User-Agent": "FLOW-link-audit/1"})
    try:
        with opener.open(request, timeout=15) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def main() -> int:
    failed: list[tuple[str, str, str]] = []
    for name, target in LINKS.items():
        try:
            status = response_code(target)
            outcome = "OK" if 200 <= status < 400 else "FEHLER"
            print(f"{outcome:6} {status}  {name:24} {target}")
            if outcome == "FEHLER":
                failed.append((name, target, str(status)))
        except OSError as exc:
            print(f"FEHLER ---  {name:24} {target} ({exc})")
            failed.append((name, target, str(exc)))
    if failed:
        print(f"\n{len(failed)} von {len(LINKS)} Links sind nicht erreichbar.")
        return 1
    print(f"\n{len(LINKS)} von {len(LINKS)} zentralen Links antworten ohne 4xx/5xx.")
    print("SSO, Rollen und Seiteninhalt müssen zusätzlich mit demo01 im Browser geprüft werden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
