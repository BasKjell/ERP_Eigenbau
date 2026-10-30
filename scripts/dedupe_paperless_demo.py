#!/usr/bin/env python3
"""Preview or remove duplicate copies of this repository's Paperless demo PDFs."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Any

DEMO_FILES = {
    "Auftrag-4711_Abnahmeprotokoll.pdf",
    "Mainboard_Lieferantenzertifikat_BE-24117.pdf",
    "SCU-100_Montageanweisung_Rev-D.pdf",
    "SCU-100_Pruefplan_Rev-B.pdf",
    "SCU-100_Technische_Zeichnung_Rev-C.pdf",
}


def request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    token: str = "",
    payload: dict[str, Any] | None = None,
) -> Any:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Token {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    call = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}", data=data, method=method, headers=headers
    )
    try:
        with urllib.request.urlopen(call, timeout=20) as response:
            if response.status == 204:
                return None
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Paperless HTTP {exc.code}: {detail[:500]}") from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    base_url = os.getenv("PAPERLESS_BASE_URL", "http://paperless-webserver:8000")
    username = os.getenv("PAPERLESS_USERNAME", "admin")
    password = os.getenv("PAPERLESS_PASSWORD", "")
    token = os.getenv("PAPERLESS_API_TOKEN", "")
    if not token:
        auth = request(
            base_url,
            "/api/token/",
            method="POST",
            payload={"username": username, "password": password},
        )
        token = str(auth["token"])
    query = urllib.parse.urlencode({"page_size": 200, "ordering": "added"})
    payload = request(base_url, f"/api/documents/?{query}", token=token)
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in payload.get("results", []):
        filename = str(document.get("original_file_name") or "")
        if filename in DEMO_FILES:
            grouped[filename].append(document)
    duplicates = [
        document
        for documents in grouped.values()
        for document in sorted(documents, key=lambda row: int(row["id"]))[1:]
    ]
    print(
        json.dumps(
            {
                "mode": "delete" if args.confirm else "preview",
                "duplicate_count": len(duplicates),
                "duplicates": [
                    {
                        "id": document["id"],
                        "title": document.get("title"),
                        "original_file_name": document.get("original_file_name"),
                    }
                    for document in duplicates
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.confirm:
        for document in duplicates:
            request(
                base_url,
                f"/api/documents/{int(document['id'])}/",
                method="DELETE",
                token=token,
            )


if __name__ == "__main__":
    main()
