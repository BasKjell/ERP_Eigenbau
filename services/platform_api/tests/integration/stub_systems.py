"""Deterministic ERPNext, Paperless and Redmine HTTP integration stubs."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse


class Handler(BaseHTTPRequestHandler):
    server_version = "ERPIntegrationStub/1.0"
    paperless_task_counter = 0

    def do_GET(self) -> None:  # noqa: N802 - method name is defined by BaseHTTPRequestHandler
        parsed = urlparse(self.path)
        decoded_path = unquote(parsed.path)
        if parsed.path == "/health":
            self._json({"status": "ok"})
            return
        if parsed.path == "/erpnext/api/method/ping":
            self._json({"message": "pong"})
            return
        if decoded_path == "/erpnext/api/resource/Work Order":
            if self.headers.get("Authorization") != "token ci-key:ci-secret":
                self._json({"message": "Not permitted"}, HTTPStatus.FORBIDDEN)
                return
            self._json(
                {
                    "data": [
                        {
                            "name": "WO-CI-0001",
                            "production_item": "SCU-100",
                            "item_name": "Smart Control Unit",
                            "qty": 5,
                            "produced_qty": 2,
                            "material_transferred_for_manufacturing": 5,
                            "status": "In Process",
                            "sales_order": "SO-4711",
                            "bom_no": "BOM-SCU-100-001",
                            "wip_warehouse": "Work In Progress - OMD",
                            "fg_warehouse": "Finished Goods - OMD",
                        }
                    ]
                }
            )
            return
        if parsed.path == "/paperless/api/":
            self._json({"status": "ok"})
            return
        if parsed.path == "/paperless/api/documents/":
            if self.headers.get("Authorization") != "Token ci-paperless-token":
                self._json(
                    {"detail": "Authentication credentials were not provided."},
                    HTTPStatus.UNAUTHORIZED,
                )
                return
            query = parse_qs(parsed.query).get("query", [""])[0]
            self._json(
                {
                    "count": 1,
                    "results": [
                        {
                            "id": 4711,
                            "title": f"{query} Montageanweisung",
                            "tags": ["Arbeitsanweisung"],
                        }
                    ],
                }
            )
            return
        if parsed.path == "/redmine/projects.json":
            if self.headers.get("X-Redmine-API-Key") != "ci-redmine-key":
                self._json({"errors": ["Unauthorized"]}, HTTPStatus.UNAUTHORIZED)
                return
            self._json(
                {
                    "projects": [
                        {
                            "id": 1,
                            "name": "SCU-100 Produktentwicklung",
                            "identifier": "scu-100",
                            "description": "CI Redmine project",
                        }
                    ],
                    "total_count": 1,
                }
            )
            return
        if parsed.path == "/redmine/issues.json":
            if self.headers.get("X-Redmine-API-Key") != "ci-redmine-key":
                self._json({"errors": ["Unauthorized"]}, HTTPStatus.UNAUTHORIZED)
                return
            self._json(
                {
                    "issues": [
                        {
                            "id": 101,
                            "project": {"id": 1, "name": "SCU-100 Produktentwicklung"},
                            "status": {"id": 2, "name": "In Bearbeitung"},
                            "priority": {"id": 3, "name": "Hoch"},
                            "assigned_to": {"id": 1, "name": "CI Engineer"},
                            "subject": "CAN-Kommunikation spezifizieren",
                            "done_ratio": 50,
                            "due_date": "2026-11-08",
                        }
                    ],
                    "total_count": 1,
                }
            )
            return
        if parsed.path == "/redmine/projects/scu-100/wiki/index.json":
            self._json(
                {
                    "wiki_pages": [
                        {
                            "title": "SCU-100_Requirements",
                            "version": 7,
                            "updated_on": "2026-11-04T08:00:00Z",
                        }
                    ]
                }
            )
            return
        self._json({"detail": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/redmine/issues.json":
            if self.headers.get("X-Redmine-API-Key") != "ci-redmine-key":
                self._json({"errors": ["Unauthorized"]}, HTTPStatus.UNAUTHORIZED)
                return
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length)).get("issue", {})
            if not payload.get("subject") or payload.get("project_id") != "scu-100":
                self._json({"errors": ["Invalid issue"]}, HTTPStatus.UNPROCESSABLE_ENTITY)
                return
            self._json(
                {
                    "issue": {
                        "id": 105,
                        "subject": payload["subject"],
                        "description": payload.get("description", ""),
                        "project": {"id": 1, "name": "SCU-100 Produktentwicklung"},
                        "status": {"id": 1, "name": "Neu"},
                        "priority": {"id": 2, "name": "Normal"},
                        "done_ratio": 0,
                    }
                },
                HTTPStatus.CREATED,
            )
            return
        if self.path == "/paperless/api/documents/post_document/":
            if self.headers.get("Authorization") != "Token ci-paperless-token":
                self._json(
                    {"detail": "Authentication credentials were not provided."},
                    HTTPStatus.UNAUTHORIZED,
                )
                return
            length = int(self.headers.get("Content-Length", "0"))
            content = self.rfile.read(length)
            if b"Entgeltabrechnung_" not in content or b"%PDF" not in content:
                self._json({"detail": "invalid payroll document"}, HTTPStatus.BAD_REQUEST)
                return
            type(self).paperless_task_counter += 1
            self._json(f"paperless-task-{type(self).paperless_task_counter:04d}")
            return
        if self.path not in {
            "/erpnext/api/resource/Timesheet",
            "/erpnext/api/resource/Journal%20Entry",
        }:
            self._json({"detail": "not found"}, HTTPStatus.NOT_FOUND)
            return
        if self.headers.get("Authorization") != "token ci-key:ci-secret":
            self._json({"message": "Not permitted"}, HTTPStatus.FORBIDDEN)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        if self.path == "/erpnext/api/resource/Journal%20Entry":
            accounts = payload.get("accounts", [])
            debit = sum(item.get("debit_in_account_currency", 0) for item in accounts)
            credit = sum(item.get("credit_in_account_currency", 0) for item in accounts)
            if not accounts or debit != credit or "FLOWHR" not in payload.get("user_remark", ""):
                self._json({"message": "Invalid payroll journal"}, HTTPStatus.BAD_REQUEST)
                return
            self._json(
                {"data": {"name": "JV-PAYROLL-CI-0001", **payload}},
                HTTPStatus.CREATED,
            )
            return
        logs = payload.get("time_logs", [])
        invalid_logs = any(
            item.get("activity_type") != "Anwesenheitszeit" for item in logs
        )
        if not logs or invalid_logs:
            self._json({"message": "Invalid HR timesheet"}, HTTPStatus.BAD_REQUEST)
            return
        self._json({"data": {"name": "TS-HR-CI-0001", **payload}}, HTTPStatus.CREATED)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(
        self, payload: object, status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9000), Handler).serve_forever()
