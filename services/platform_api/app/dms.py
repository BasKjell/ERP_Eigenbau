"""FLOWDOC – eigene DMS-Oberfläche über die Paperless-ngx-API (ADR-007 „Eigene Oberfläche“).

Grundsatz: Paperless-ngx bleibt führendes System für Ablage, Texterkennung, Versionen und
Objektrechte. Die Plattform-API fragt Paperless im Namen der angemeldeten Person ab
(Remote-User-Header aus der geprüften FLOWID-Sitzung). Paperless entscheidet damit selbst,
welche Dokumente, Titel, Trefferzahlen und Vorschauen eine Person sieht (Teil 04, Test 18).

Ohne Anmeldung (lokaler Demo-Modus) nutzt der Dienst das technische Konto und kennzeichnet die
Antwort mit ``access: "technisches Konto (Demo)"``. Im OIDC-Modus gibt es diesen Rückfall nicht.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

from .config import Settings
from .paperless_client import PaperlessClient, PaperlessError, _multipart_body

ORDERINGS = {
    "title": "title", "-title": "-title", "created": "created", "-created": "-created",
    "added": "added", "-added": "-added", "correspondent": "correspondent__name",
    "document_type": "document_type__name",
}
STATUS_TAGS = ("Status/Entwurf", "Status/In Prüfung", "Status/Freigegeben", "Status/Ungültig")
TRANSITIONS = {
    "pruefen": ("Status/Entwurf", "Status/In Prüfung"),
    "freigeben": ("Status/In Prüfung", "Status/Freigegeben"),
    "zurueckweisen": ("Status/In Prüfung", "Status/Entwurf"),
}
MAX_UPLOAD = 25 * 1024 * 1024
ALLOWED_UPLOAD = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".txt", ".docx", ".xlsx", ".odt"}


class DmsError(RuntimeError):
    def __init__(self, message: str, status: int = 502) -> None:
        super().__init__(message)
        self.status = status


class DmsService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.paperless_base_url.rstrip("/")
        self.public_url = settings.paperless_public_url.rstrip("/")
        self.header = os.getenv("PAPERLESS_REMOTE_USER_HEADER", "X-Flow-Sso-User")
        self.delegated = settings.auth_mode == "oidc"
        self.technical = PaperlessClient(settings)

    # -- Zugriff -------------------------------------------------------------------------
    def _auth(self, person: dict[str, Any] | None) -> tuple[dict[str, str], str]:
        if self.delegated:
            username = str((person or {}).get("username") or "")
            if not re.fullmatch(r"[A-Za-z0-9_.@-]{2,150}", username):
                raise DmsError("Anmeldung über FLOWID erforderlich", 401)
            return {self.header: username}, f"im Namen von {username}"
        if not self.technical.configured:
            raise DmsError("FLOWDOC ist nicht verbunden (Paperless-Zugang fehlt)", 503)
        if not self.technical.token:
            try:
                self.technical._authenticate()
            except PaperlessError as exc:
                raise DmsError(str(exc), 503) from exc
        return {"Authorization": f"Token {self.technical.token}"}, "technisches Konto (Demo)"

    def _call(
        self, method: str, path: str, person: dict[str, Any] | None, *, params: dict[str, Any] | None = None,
        body: bytes | None = None, content_type: str = "application/json", raw: bool = False,
    ) -> Any:
        headers, _ = self._auth(person)
        headers["Accept"] = "*/*" if raw else "application/json"
        if body is not None:
            headers["Content-Type"] = content_type
        query = f"?{urllib.parse.urlencode(params, doseq=True)}" if params else ""
        request = urllib.request.Request(f"{self.base_url}{path}{query}", data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read(60 * 1024 * 1024)
                if raw:
                    return data, response.headers.get("Content-Type", "application/octet-stream")
                return json.loads(data or b"null")
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise DmsError("Keine Berechtigung im DMS für diese Aktion", 403) from None
            if exc.code == 404:
                raise DmsError("Dokument nicht gefunden", 404) from None
            raise DmsError(f"FLOWDOC antwortete mit HTTP {exc.code}", 502) from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise DmsError(f"FLOWDOC nicht erreichbar ({type(exc).__name__})", 503) from None

    # -- Lesen ---------------------------------------------------------------------------
    def metadata(self, person: dict[str, Any] | None) -> dict[str, Any]:
        _, access = self._auth(person)
        result: dict[str, Any] = {"access": access}
        for key, path in (("document_types", "/api/document_types/"), ("tags", "/api/tags/"),
                          ("correspondents", "/api/correspondents/"), ("storage_paths", "/api/storage_paths/")):
            payload = self._call("GET", path, person, params={"page_size": 500, "ordering": "name"})
            result[key] = [
                {"id": row["id"], "name": row["name"], "count": row.get("document_count", 0),
                 **({"color": _color(row.get("color"))} if key == "tags" else {})}
                for row in (payload or {}).get("results", [])
            ]
        return result

    def search(
        self, person: dict[str, Any] | None, *, query: str = "", document_type: int | None = None,
        tag: int | None = None, correspondent: int | None = None, status: str = "", ordering: str = "-created",
        page: int = 1,
    ) -> dict[str, Any]:
        if ordering not in ORDERINGS:
            raise DmsError("Unbekannte Sortierung", 422)
        meta = self.metadata(person)
        params: dict[str, Any] = {"page": max(1, min(page, 500)), "page_size": 25, "ordering": ORDERINGS[ordering],
                                  "truncate_content": "true"}
        if query.strip():
            params["query"] = query.strip()[:200]
        if document_type:
            params["document_type__id"] = int(document_type)
        if correspondent:
            params["correspondent__id"] = int(correspondent)
        tag_ids = [int(tag)] if tag else []
        if status:
            status_tag = next((t for t in meta["tags"] if t["name"] == status), None)
            if status_tag is None:
                return {"access": meta["access"], "count": 0, "page": params["page"], "results": [], "facets": meta}
            tag_ids.append(status_tag["id"])
        if tag_ids:
            params["tags__id__all"] = ",".join(str(t) for t in tag_ids)
        payload = self._call("GET", "/api/documents/", person, params=params) or {}
        rows = [self._summary(row, meta) for row in payload.get("results", [])]
        return {"access": meta["access"], "count": int(payload.get("count", len(rows))), "page": params["page"],
                "page_size": 25, "ordering": ordering, "results": rows, "facets": meta}

    def document(self, person: dict[str, Any] | None, document_id: int) -> dict[str, Any]:
        meta = self.metadata(person)
        row = self._call("GET", f"/api/documents/{int(document_id)}/", person)
        notes = self._call("GET", f"/api/documents/{int(document_id)}/notes/", person) or []
        detail = self._summary(row, meta)
        detail.update({
            "content": str(row.get("content") or "")[:6000],
            "original_file_name": row.get("original_file_name"),
            "archive_serial_number": row.get("archive_serial_number"),
            "page_count": row.get("page_count"),
            "custom_fields": row.get("custom_fields", []),
            "user_can_change": bool(row.get("user_can_change", False)),
            "notes": [{"id": n.get("id"), "note": n.get("note"), "created": n.get("created"),
                       "user": (n.get("user") or {}).get("username") if isinstance(n.get("user"), dict) else n.get("user")}
                      for n in (notes if isinstance(notes, list) else notes.get("results", []))],
            "transitions": [name for name, (source, _) in TRANSITIONS.items() if detail["status"] == source],
            "source_url": f"{self.public_url}/documents/{int(document_id)}/details",
        })
        return detail

    def binary(self, person: dict[str, Any] | None, document_id: int, kind: str) -> tuple[bytes, str]:
        if kind not in {"thumb", "preview", "download"}:
            raise DmsError("Unbekannte Darstellung", 404)
        return self._call("GET", f"/api/documents/{int(document_id)}/{kind}/", person, raw=True)

    # -- Schreiben (nur ausdrückliche Benutzeraktionen) -----------------------------------------
    def upload(
        self, person: dict[str, Any] | None, content: bytes, filename: str, title: str,
        document_type: int | None = None, tags: list[int] | None = None,
    ) -> dict[str, Any]:
        clean = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        suffix = ("." + clean.rsplit(".", 1)[-1].lower()) if "." in clean else ""
        if not content or len(content) > MAX_UPLOAD:
            raise DmsError("Datei fehlt oder ist größer als 25 MB", 422)
        if suffix not in ALLOWED_UPLOAD or not re.fullmatch(r"[^\r\n\"]{1,180}", clean):
            raise DmsError("Dateityp oder Dateiname ist nicht zulässig", 422)
        title = title.strip() or clean.rsplit(".", 1)[0]
        if len(title) > 160:
            raise DmsError("Titel ist zu lang", 422)
        fields: dict[str, str] = {"title": title}
        if document_type:
            fields["document_type"] = str(int(document_type))
        boundary = f"flowdoc-{uuid.uuid4().hex}"
        body = _multipart_body(boundary, fields=fields, file_field="document", filename=clean, content=content)
        if tags:
            extra = "".join(f'--{boundary}\r\nContent-Disposition: form-data; name="tags"\r\n\r\n{int(t)}\r\n' for t in tags)
            body = extra.encode() + body
        task = self._call("POST", "/api/documents/post_document/", person, body=body,
                          content_type=f"multipart/form-data; boundary={boundary}")
        task_id = task if isinstance(task, str) else (task or {}).get("task_id")
        if not task_id:
            raise DmsError("FLOWDOC lieferte keine Verarbeitungs-ID")
        return {"task_id": str(task_id), "status": "in Verarbeitung"}

    def task(self, person: dict[str, Any] | None, task_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9-]{8,64}", task_id):
            raise DmsError("Ungültige Verarbeitungs-ID", 422)
        rows = self._call("GET", "/api/tasks/", person, params={"task_id": task_id}) or []
        row = rows[0] if isinstance(rows, list) and rows else {}
        return {"task_id": task_id, "status": row.get("status", "UNBEKANNT"), "document_id": row.get("related_document"),
                "result": str(row.get("result") or "")[:300]}

    def add_note(self, person: dict[str, Any] | None, document_id: int, note: str) -> dict[str, Any]:
        text = note.strip()
        if not 2 <= len(text) <= 2000:
            raise DmsError("Notiz muss 2 bis 2000 Zeichen haben", 422)
        self._call("POST", f"/api/documents/{int(document_id)}/notes/", person,
                   body=json.dumps({"note": text}).encode())
        return self.document(person, document_id)

    def transition(self, person: dict[str, Any] | None, document_id: int, action: str) -> dict[str, Any]:
        if action not in TRANSITIONS:
            raise DmsError("Unbekannter Statuswechsel", 422)
        source, target = TRANSITIONS[action]
        meta = self.metadata(person)
        by_name = {t["name"]: t["id"] for t in meta["tags"]}
        if target not in by_name:
            raise DmsError(f"Status-Tag {target} ist im DMS nicht angelegt", 409)
        row = self._call("GET", f"/api/documents/{int(document_id)}/", person)
        tags = set(row.get("tags") or [])
        if by_name.get(source) not in tags:
            raise DmsError(f"Dokument steht nicht im Status {source.split('/', 1)[1]}", 409)
        tags.discard(by_name[source])
        tags.add(by_name[target])
        self._call("PATCH", f"/api/documents/{int(document_id)}/", person,
                   body=json.dumps({"tags": sorted(tags)}).encode())
        return self.document(person, document_id)

    # -- Hilfen --------------------------------------------------------------------------
    @staticmethod
    def _summary(row: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
        def name(key: str, value: Any) -> str | None:
            return next((item["name"] for item in meta[key] if item["id"] == value), None)

        # Tags ohne Leserecht (Paperless liefert nur die ID) werden nicht angezeigt.
        visible_tags = {t["id"]: t for t in meta["tags"]}
        tags = [{"id": tag_id, "name": visible_tags[tag_id]["name"], "color": visible_tags[tag_id].get("color")}
                for tag_id in row.get("tags") or [] if tag_id in visible_tags]
        status = next((t["name"] for t in tags if t["name"] in STATUS_TAGS), "ohne Status")
        hit = row.get("__search_hit__") or {}
        return {
            "id": row.get("id"),
            "title": row.get("title") or "Ohne Titel",
            "created": row.get("created_date") or str(row.get("created") or "")[:10],
            "added": str(row.get("added") or "")[:10],
            "document_type": name("document_types", row.get("document_type")),
            "correspondent": name("correspondents", row.get("correspondent")),
            "storage_path": name("storage_paths", row.get("storage_path")),
            "tags": [t for t in tags if not t["name"].startswith("Status/")],
            "status": status,
            "mime_type": row.get("mime_type"),
            "highlight": str(hit.get("highlights") or "")[:400],
        }


def _color(value: Any) -> str | None:
    """Nur echte Hex-Farben gelangen in style-Attribute der Oberfläche."""
    text = str(value or "")
    return text if re.fullmatch(r"#[0-9A-Fa-f]{3,8}", text) else None

