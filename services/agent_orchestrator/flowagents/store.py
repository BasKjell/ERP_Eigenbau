"""Dauerhafter Zustand des Orchestrators (SQLite, ein Schreiber, WAL).

Gespeichert werden Läufe, Schritte, versionierte Artefakte mit Digest, Entscheidungen und
Ereignisse. Standardereignisse enthalten keine Vollprompts, Modellantworten oder Zugangsdaten
(Teil 09 „Modellbetrieb und Protokolle“); Ergebnisse liegen als geprüfte Artefakte vor.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY, auftrag_id TEXT UNIQUE NOT NULL, title TEXT NOT NULL, change_class TEXT NOT NULL,
    status TEXT NOT NULL, step_index INTEGER NOT NULL DEFAULT 0, auftrag TEXT NOT NULL,
    requested_by TEXT NOT NULL, corrections TEXT NOT NULL DEFAULT '{}', model_calls INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0, reason TEXT NOT NULL DEFAULT '', registry_digest TEXT NOT NULL,
    idempotency_key TEXT UNIQUE NOT NULL, created REAL NOT NULL, updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, step_id TEXT NOT NULL, attempt INTEGER NOT NULL,
    role TEXT, status TEXT NOT NULL, provider TEXT NOT NULL DEFAULT '', model TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '', findings TEXT NOT NULL DEFAULT '[]', questions TEXT NOT NULL DEFAULT '[]',
    error TEXT NOT NULL DEFAULT '', started REAL NOT NULL, finished REAL
);
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, kind TEXT NOT NULL, version INTEGER NOT NULL,
    role TEXT NOT NULL, step_id TEXT NOT NULL, content TEXT NOT NULL, digest TEXT NOT NULL,
    refs TEXT NOT NULL DEFAULT '{}', created REAL NOT NULL, UNIQUE(run_id, kind, version)
);
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY, run_id TEXT NOT NULL, step_id TEXT NOT NULL, gate TEXT NOT NULL,
    decider TEXT NOT NULL, status TEXT NOT NULL, title TEXT NOT NULL, question TEXT NOT NULL,
    context TEXT NOT NULL DEFAULT '{}', digest TEXT NOT NULL DEFAULT '', decided_by TEXT NOT NULL DEFAULT '{}',
    outcome TEXT NOT NULL DEFAULT '', comment TEXT NOT NULL DEFAULT '', created REAL NOT NULL, decided REAL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY, stamp REAL NOT NULL, run_id TEXT, kind TEXT NOT NULL, actor TEXT NOT NULL,
    target TEXT NOT NULL DEFAULT '', message TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS controls (name TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS model_usage (
    id INTEGER PRIMARY KEY, stamp REAL NOT NULL, run_id TEXT NOT NULL, step_id TEXT NOT NULL, role TEXT NOT NULL,
    provider TEXT NOT NULL, model TEXT NOT NULL, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
    seconds REAL NOT NULL
);
-- Projekte mit Arbeitspaketen (KI-Softwareentwicklung Teil 01): ein L-Lauf plant, jedes Paket
-- läuft danach als eigener Auftrag durch das V. Status von Paket und Projekt ergeben sich aus den Läufen.
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY, run_id TEXT UNIQUE NOT NULL, title TEXT NOT NULL, auftrag TEXT NOT NULL,
    defined_by TEXT NOT NULL DEFAULT '{}', created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS work_packages (
    project_id TEXT NOT NULL, key TEXT NOT NULL, position INTEGER NOT NULL, spec TEXT NOT NULL,
    run_id TEXT NOT NULL DEFAULT '', started_by TEXT NOT NULL DEFAULT '{}', started REAL,
    PRIMARY KEY (project_id, key)
);
-- Übersteuerungen der Agenteneigenschaften aus der Agentenzentrale (nur Administratoren) mit Protokoll.
CREATE TABLE IF NOT EXISTS agent_settings (
    role TEXT PRIMARY KEY, settings TEXT NOT NULL, updated REAL NOT NULL, updated_by TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS agent_settings_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL, changes TEXT NOT NULL, reason TEXT NOT NULL,
    person TEXT NOT NULL, digest TEXT NOT NULL DEFAULT '', created REAL NOT NULL
);
-- Fachagenten (von Administratoren angelegt) und ihre Aufgaben/Entwürfe.
CREATE TABLE IF NOT EXISTS business_agents (
    id TEXT PRIMARY KEY, spec TEXT NOT NULL, created_by TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS business_jobs (
    id TEXT PRIMARY KEY, agent_id TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL, input TEXT NOT NULL,
    output TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL, error TEXT NOT NULL DEFAULT '',
    requested_by TEXT NOT NULL, decided_by TEXT NOT NULL DEFAULT '{}', model TEXT NOT NULL DEFAULT '',
    seconds REAL NOT NULL DEFAULT 0, created REAL NOT NULL, updated REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS business_jobs_status ON business_jobs(status, created);
CREATE INDEX IF NOT EXISTS events_run ON events(run_id, id);
CREATE INDEX IF NOT EXISTS decisions_open ON decisions(status, created);
"""

RUN_STATES = ("aktiv", "wartet", "blockiert", "pausiert", "abgeschlossen", "abgelehnt", "abgebrochen")
OPEN_RUN_STATES = ("aktiv", "wartet", "blockiert", "pausiert")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_of(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode()).hexdigest()


def iso(stamp: float | None) -> str | None:
    return datetime.fromtimestamp(stamp, UTC).isoformat(timespec="seconds") if stamp else None


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._lock = threading.RLock()
        self.db = sqlite3.connect(path, timeout=15, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self._lock:
            self.db.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self.db.close()

    # -- Steuerung ---------------------------------------------------------------------
    def control(self, name: str, default: str = "") -> str:
        with self._lock:
            row = self.db.execute("SELECT value FROM controls WHERE name=?", (name,)).fetchone()
        return row["value"] if row else default

    def set_control(self, name: str, value: str, actor: str) -> None:
        with self._lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO controls VALUES (?, ?)", (name, value))
            self._event(None, "steuerung", actor, name, f"{name} = {value}", {})

    def controls(self) -> dict[str, str]:
        with self._lock:
            return {row["name"]: row["value"] for row in self.db.execute("SELECT * FROM controls")}

    # -- Läufe ---------------------------------------------------------------------------
    def create_run(
        self,
        *,
        title: str,
        change_class: str,
        auftrag: dict[str, Any],
        requested_by: dict[str, Any],
        registry_digest: str,
        idempotency_key: str,
        announce: bool = True,
    ) -> dict[str, Any]:
        with self._lock, self.db:
            existing = self.db.execute(
                "SELECT * FROM runs WHERE idempotency_key=?", (idempotency_key,)
            ).fetchone()
            if existing:
                previous = {k: v for k, v in json.loads(existing["auftrag"]).items() if k != "id"}
                if previous != auftrag:
                    raise ValueError("Idempotenzschlüssel bereits mit anderem Auftrag verwendet")
                return self._run(existing)
            number = self.db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] + 1
            now = time.time()
            run_id = f"RUN-{datetime.fromtimestamp(now, UTC):%Y%m%d}-{secrets.token_hex(3).upper()}"
            auftrag_id = f"A-{number:03d}"
            stored = {**auftrag, "id": auftrag_id}
            self.db.execute(
                "INSERT INTO runs(id, auftrag_id, title, change_class, status, auftrag, requested_by,"
                " registry_digest, idempotency_key, created, updated) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (run_id, auftrag_id, title, change_class, "aktiv", canonical(stored), canonical(requested_by),
                 registry_digest, idempotency_key, now, now),
            )
            self._add_artifact(run_id, "auftrag", "auftraggeber", "eingang", stored, {})
            if announce:  # Katalogprojekte gehen nicht durch die Geschäftsführung
                self._event(run_id, "auftrag", str(requested_by.get("username") or "mensch"), "geschaeftsfuehrung",
                            f"Fachauftrag {auftrag_id} „{title}“ eingereicht ({change_class})", {})
            return self.run(run_id)

    def run(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            row = self.db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return self._run(row)

    def runs(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.db.execute("SELECT * FROM runs ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
        return [self._run(row) for row in rows]

    def next_active(self) -> dict[str, Any] | None:
        with self._lock:
            row = self.db.execute(
                "SELECT * FROM runs WHERE status='aktiv' ORDER BY updated, created LIMIT 1"
            ).fetchone()
        return self._run(row) if row else None

    def update_run(self, run_id: str, **fields: Any) -> None:
        allowed = {"status", "step_index", "corrections", "model_calls", "output_tokens", "reason", "registry_digest"}
        if set(fields) - allowed:
            raise ValueError("unzulässige Laufspalte")
        values = {k: canonical(v) if k == "corrections" else v for k, v in fields.items()}
        values["updated"] = time.time()
        columns = ", ".join(f"{name}=?" for name in values)  # Spalten nur aus der Positivliste
        with self._lock, self.db:
            self.db.execute(f"UPDATE runs SET {columns} WHERE id=?", (*values.values(), run_id))

    @staticmethod
    def _run(row: sqlite3.Row) -> dict[str, Any]:
        value = dict(row)
        value["auftrag"] = json.loads(value["auftrag"])
        value["requested_by"] = json.loads(value["requested_by"])
        value["corrections"] = json.loads(value["corrections"])
        value["created_at"] = iso(value["created"])
        value["updated_at"] = iso(value["updated"])
        value.pop("idempotency_key", None)
        return value

    # -- Fachagenten ---------------------------------------------------------------------
    def save_business_agent(self, agent_id: str, spec: dict[str, Any], person: dict[str, Any]) -> dict[str, Any]:
        now = time.time()
        with self._lock, self.db:
            if not agent_id:
                number = self.db.execute("SELECT COUNT(*) FROM business_agents").fetchone()[0] + 1
                agent_id = f"FA-{number:03d}"
                while self.db.execute("SELECT 1 FROM business_agents WHERE id=?", (agent_id,)).fetchone():
                    number += 1
                    agent_id = f"FA-{number:03d}"
                self.db.execute("INSERT INTO business_agents VALUES (?,?,?,?,?)",
                                (agent_id, canonical(spec), canonical(person), now, now))
            else:
                changed = self.db.execute("UPDATE business_agents SET spec=?, updated=? WHERE id=?",
                                          (canonical(spec), now, agent_id)).rowcount
                if not changed:
                    raise KeyError(agent_id)
        return self.business_agent(agent_id)

    def business_agent(self, agent_id: str) -> dict[str, Any]:
        with self._lock:
            row = self.db.execute("SELECT * FROM business_agents WHERE id=?", (agent_id,)).fetchone()
        if row is None:
            raise KeyError(agent_id)
        return {"id": row["id"], **json.loads(row["spec"]), "created_by": json.loads(row["created_by"]).get("name", ""),
                "created_at": iso(row["created"]), "updated_at": iso(row["updated"])}

    def business_agents(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.db.execute("SELECT id FROM business_agents ORDER BY id").fetchall()
        return [self.business_agent(row["id"]) for row in rows]

    def add_business_job(self, kind: str, agent_id: str, values: dict[str, Any], person: dict[str, Any]) -> dict[str, Any]:
        now = time.time()
        job_id = f"FJ-{datetime.fromtimestamp(now, UTC):%Y%m%d}-{secrets.token_hex(3).upper()}"
        with self._lock, self.db:
            self.db.execute("INSERT INTO business_jobs(id, agent_id, kind, input, status, requested_by, created, updated)"
                            " VALUES (?,?,?,?,?,?,?,?)", (job_id, agent_id, kind, canonical(values), "wartend",
                                                          canonical(person), now, now))
        return self.business_job(job_id)

    def update_business_job(self, job_id: str, **fields: Any) -> None:
        allowed = {"status", "output", "error", "decided_by", "model", "seconds"}
        values = {k: canonical(v) if k in {"output", "decided_by"} else v for k, v in fields.items() if k in allowed}
        if not values:
            return
        with self._lock, self.db:
            self.db.execute(f"UPDATE business_jobs SET {', '.join(f'{k}=?' for k in values)}, updated=? WHERE id=?",
                            (*values.values(), time.time(), job_id))

    def business_job(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            row = self.db.execute("SELECT * FROM business_jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._business_job(row)

    def business_jobs(self, *, status: str | None = None, limit: int = 60) -> list[dict[str, Any]]:
        query, args = "SELECT * FROM business_jobs", []
        if status:
            query, args = query + " WHERE status=?", [status]
        with self._lock:
            rows = self.db.execute(query + (" ORDER BY created" if status else " ORDER BY created DESC") + " LIMIT ?",
                                   [*args, limit]).fetchall()
        return [self._business_job(row) for row in rows]

    @staticmethod
    def _business_job(row: sqlite3.Row) -> dict[str, Any]:
        value = dict(row)
        for key in ("input", "output", "requested_by", "decided_by"):
            value[key] = json.loads(value[key])
        value["created_at"], value["updated_at"] = iso(value.pop("created")), iso(value.pop("updated"))
        return value

    # -- Agenteneinstellungen (Übersteuerungen) -------------------------------------------
    def agent_overrides(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            rows = self.db.execute("SELECT role, settings FROM agent_settings").fetchall()
        return {row["role"]: json.loads(row["settings"]) for row in rows if json.loads(row["settings"])}

    def save_agent_override(self, role: str, settings: dict[str, Any], changes: dict[str, Any], reason: str,
                            person: dict[str, Any], digest: str) -> None:
        """Übersteuerung einer Rolle ersetzen und die Änderung (alt/neu je Feld) protokollieren."""
        now = time.time()
        with self._lock, self.db:
            if settings:
                self.db.execute("INSERT INTO agent_settings VALUES (?,?,?,?) ON CONFLICT(role) DO UPDATE SET "
                                "settings=excluded.settings, updated=excluded.updated, updated_by=excluded.updated_by",
                                (role, canonical(settings), now, canonical(person)))
            else:
                self.db.execute("DELETE FROM agent_settings WHERE role=?", (role,))
            self.db.execute("INSERT INTO agent_settings_log(role, changes, reason, person, digest, created) "
                            "VALUES (?,?,?,?,?,?)", (role, canonical(changes), reason, canonical(person), digest, now))

    def agent_settings_log(self, role: str, *, limit: int = 30) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.db.execute("SELECT * FROM agent_settings_log WHERE role=? ORDER BY id DESC LIMIT ?",
                                   (role, limit)).fetchall()
        return [{"id": row["id"], "changes": json.loads(row["changes"]), "reason": row["reason"],
                 "person": json.loads(row["person"]).get("name", ""), "digest": row["digest"][:12],
                 "at": iso(row["created"])} for row in rows]

    # -- Projekte und Arbeitspakete -------------------------------------------------------
    def create_project(self, run: dict[str, Any], packages: list[dict[str, Any]],
                       defined_by: dict[str, Any], *, project_id: str = "") -> dict[str, Any]:
        """Legt zu einem Projektlauf genau ein Projekt an (idempotent über die Lauf-ID)."""
        with self._lock, self.db:
            existing = self.db.execute("SELECT id FROM projects WHERE run_id=?", (run["id"],)).fetchone()
            if existing:
                return self.project(existing["id"])
            project_id = project_id or "PRJ-" + run["auftrag_id"].split("-", 1)[-1]
            self.db.execute("INSERT INTO projects VALUES (?,?,?,?,?,?)",
                            (project_id, run["id"], run["title"], canonical(run["auftrag"]), canonical(defined_by),
                             time.time()))
            for position, spec in enumerate(packages):
                self.db.execute("INSERT INTO work_packages(project_id, key, position, spec) VALUES (?,?,?,?)",
                                (project_id, str(spec["key"]), position, canonical(spec)))
        return self.project(project_id)

    def project(self, project_id: str) -> dict[str, Any]:
        with self._lock:
            row = self.db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
            if row is None:
                raise KeyError(project_id)
            packages = self.db.execute("SELECT * FROM work_packages WHERE project_id=? ORDER BY position",
                                       (project_id,)).fetchall()
        value = dict(row)
        value["auftrag"] = json.loads(value["auftrag"])
        value["defined_by"] = json.loads(value["defined_by"])
        value["created_at"] = iso(value.pop("created"))
        value["packages"] = [{**json.loads(p["spec"]), "run_id": p["run_id"], "started_by": json.loads(p["started_by"]),
                              "started_at": iso(p["started"])} for p in packages]
        return value

    def projects(self, *, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.db.execute("SELECT id FROM projects ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
        return [self.project(row["id"]) for row in rows]

    def project_for_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.db.execute(
                "SELECT id FROM projects WHERE run_id=? UNION SELECT project_id FROM work_packages WHERE run_id=?",
                (run_id, run_id)).fetchone()
        return self.project(row[0]) if row else None

    def attach_package_run(self, project_id: str, key: str, run_id: str, person: dict[str, Any]) -> None:
        """Bindet einen Lauf genau einmal an ein Arbeitspaket."""
        with self._lock, self.db:
            changed = self.db.execute(
                "UPDATE work_packages SET run_id=?, started_by=?, started=? WHERE project_id=? AND key=? AND run_id=''",
                (run_id, canonical(person), time.time(), project_id, key)).rowcount
            if changed != 1:
                raise ValueError("Arbeitspaket ist bereits gestartet")

    # -- Schritte ------------------------------------------------------------------------
    def start_step(self, run_id: str, step_id: str, role: str | None, provider: str = "", model: str = "") -> int:
        with self._lock, self.db:
            attempt = self.db.execute(
                "SELECT COUNT(*) FROM steps WHERE run_id=? AND step_id=?", (run_id, step_id)
            ).fetchone()[0] + 1
            cursor = self.db.execute(
                "INSERT INTO steps(run_id, step_id, attempt, role, status, provider, model, started)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (run_id, step_id, attempt, role, "laeuft", provider, model, time.time()),
            )
            return int(cursor.lastrowid)

    def finish_step(
        self,
        step_row: int,
        status: str,
        *,
        summary: str = "",
        findings: list[dict[str, Any]] | None = None,
        questions: list[dict[str, Any]] | None = None,
        error: str = "",
    ) -> None:
        with self._lock, self.db:
            self.db.execute(
                "UPDATE steps SET status=?, summary=?, findings=?, questions=?, error=?, finished=? WHERE id=?",
                (status, summary[:2000], canonical(findings or []), canonical(questions or []), error[:2000],
                 time.time(), step_row),
            )

    def steps(self, run_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.db.execute("SELECT * FROM steps WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
        result = []
        for row in rows:
            value = dict(row)
            value["findings"] = json.loads(value["findings"])
            value["questions"] = json.loads(value["questions"])
            value["started_at"] = iso(value["started"])
            value["finished_at"] = iso(value["finished"])
            result.append(value)
        return result

    def running_steps(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.db.execute("SELECT * FROM steps WHERE status='laeuft'").fetchall()
        return [dict(row) for row in rows]

    def last_step(self, run_id: str, step_id: str) -> dict[str, Any] | None:
        steps = [step for step in self.steps(run_id) if step["step_id"] == step_id]
        return steps[-1] if steps else None

    # -- Artefakte -----------------------------------------------------------------------
    def add_artifact(
        self, run_id: str, kind: str, role: str, step_id: str, content: Any, refs: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        with self._lock, self.db:
            return self._add_artifact(run_id, kind, role, step_id, content, refs or {})

    def _add_artifact(
        self, run_id: str, kind: str, role: str, step_id: str, content: Any, refs: dict[str, Any]
    ) -> dict[str, Any]:
        version = self.db.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 FROM artifacts WHERE run_id=? AND kind=?", (run_id, kind)
        ).fetchone()[0]
        digest = digest_of(content)
        self.db.execute(
            "INSERT INTO artifacts(run_id, kind, version, role, step_id, content, digest, refs, created)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (run_id, kind, version, role, step_id, canonical(content), digest, canonical(refs), time.time()),
        )
        return {"kind": kind, "version": version, "digest": digest, "role": role, "refs": refs}

    def latest_artifact(self, run_id: str, kind: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.db.execute(
                "SELECT * FROM artifacts WHERE run_id=? AND kind=? ORDER BY version DESC LIMIT 1", (run_id, kind)
            ).fetchone()
        return self._artifact(row) if row else None

    def artifacts(self, run_id: str, kinds: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.db.execute(
                "SELECT * FROM artifacts WHERE run_id=? ORDER BY kind, version", (run_id,)
            ).fetchall()
        return [self._artifact(row) for row in rows if kinds is None or row["kind"] in kinds]

    @staticmethod
    def _artifact(row: sqlite3.Row) -> dict[str, Any]:
        value = dict(row)
        value["content"] = json.loads(value["content"])
        value["refs"] = json.loads(value["refs"])
        value["created_at"] = iso(value["created"])
        return value

    # -- Entscheidungen ------------------------------------------------------------------
    def open_decision(
        self,
        run_id: str,
        step_id: str,
        gate: str,
        decider: str,
        title: str,
        question: str,
        context: dict[str, Any],
        digest: str = "",
        actor: str = "orchestrator",
    ) -> dict[str, Any]:
        decision_id = f"ENT-{secrets.token_hex(4).upper()}"
        with self._lock, self.db:
            self.db.execute(
                "INSERT INTO decisions(id, run_id, step_id, gate, decider, status, title, question, context,"
                " digest, created) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (decision_id, run_id, step_id, gate, decider, "offen", title, question, canonical(context),
                 digest, time.time()),
            )
            self._event(run_id, "entscheidung_offen", actor, f"mensch:{decider}",
                        f"{title}: Entscheidung durch {decider} erforderlich", {"decision": decision_id, "gate": gate})
        return self.decision(decision_id)

    def decision(self, decision_id: str) -> dict[str, Any]:
        with self._lock:
            row = self.db.execute("SELECT * FROM decisions WHERE id=?", (decision_id,)).fetchone()
        if row is None:
            raise KeyError(decision_id)
        return self._decision(row)

    def decisions(self, *, status: str | None = None, run_id: str | None = None) -> list[dict[str, Any]]:
        query, args = "SELECT * FROM decisions WHERE 1=1", []
        if status:
            query, args = query + " AND status=?", [*args, status]
        if run_id:
            query, args = query + " AND run_id=?", [*args, run_id]
        with self._lock:
            rows = self.db.execute(query + " ORDER BY created", args).fetchall()
        return [self._decision(row) for row in rows]

    def close_decision(
        self, decision_id: str, status: str, outcome: str, decided_by: dict[str, Any], comment: str
    ) -> None:
        with self._lock, self.db:
            changed = self.db.execute(
                "UPDATE decisions SET status=?, outcome=?, decided_by=?, comment=?, decided=?"
                " WHERE id=? AND status='offen'",
                (status, outcome, canonical(decided_by), comment[:2000], time.time(), decision_id),
            ).rowcount
            if changed != 1:
                raise ValueError("Entscheidung ist nicht mehr offen")

    @staticmethod
    def _decision(row: sqlite3.Row) -> dict[str, Any]:
        value = dict(row)
        value["context"] = json.loads(value["context"])
        value["decided_by"] = json.loads(value["decided_by"])
        value["created_at"] = iso(value["created"])
        value["decided_at"] = iso(value["decided"])
        return value

    # -- Ereignisse ----------------------------------------------------------------------
    def event(
        self, run_id: str | None, kind: str, actor: str, target: str, message: str, detail: dict[str, Any] | None = None
    ) -> None:
        with self._lock, self.db:
            self._event(run_id, kind, actor, target, message, detail or {})

    def _event(
        self, run_id: str | None, kind: str, actor: str, target: str, message: str, detail: dict[str, Any]
    ) -> None:
        self.db.execute(
            "INSERT INTO events(stamp, run_id, kind, actor, target, message, detail) VALUES (?,?,?,?,?,?,?)",
            (time.time(), run_id, kind, actor, target, message[:500], canonical(detail)),
        )

    def events(self, *, after: int = 0, run_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query, args = "SELECT * FROM events WHERE id>?", [after]
        if run_id:
            query, args = query + " AND run_id=?", [*args, run_id]
        with self._lock:
            rows = self.db.execute(query + " ORDER BY id DESC LIMIT ?", [*args, limit]).fetchall()
        result = []
        for row in reversed(rows):
            value = dict(row)
            value["detail"] = json.loads(value["detail"])
            value["at"] = iso(value["stamp"])
            result.append(value)
        return result

    # -- Modellnutzung (Token-Tracker) ---------------------------------------------------
    def record_usage(self, run_id: str, step_id: str, role: str, provider: str, model: str,
                     input_tokens: int, output_tokens: int, seconds: float) -> None:
        with self._lock, self.db:
            self.db.execute(
                "INSERT INTO model_usage(stamp, run_id, step_id, role, provider, model, input_tokens, output_tokens,"
                " seconds) VALUES (?,?,?,?,?,?,?,?,?)",
                (time.time(), run_id, step_id, role, provider, model, int(input_tokens), int(output_tokens),
                 float(seconds)),
            )

    def usage_totals(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.db.execute(
                "SELECT role, provider, model, COUNT(*) AS calls, SUM(input_tokens) AS input_tokens,"
                " SUM(output_tokens) AS output_tokens, SUM(seconds) AS seconds FROM model_usage"
                " GROUP BY role, provider, model ORDER BY role"
            ).fetchall()
        return [dict(row) for row in rows]

    def usage_by_run(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.db.execute(
                "SELECT u.run_id, r.auftrag_id, r.title, COUNT(*) AS calls, SUM(u.input_tokens) AS input_tokens,"
                " SUM(u.output_tokens) AS output_tokens, SUM(u.seconds) AS seconds FROM model_usage u"
                " LEFT JOIN runs r ON r.id = u.run_id GROUP BY u.run_id ORDER BY MAX(u.stamp) DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def failed_attempts(self, run_id: str, step_id: str, provider: str) -> int:
        """Gescheiterte (nicht unterbrochene) Versuche eines Schritts mit einem Provider."""
        with self._lock:
            row = self.db.execute(
                "SELECT COUNT(*) FROM steps WHERE run_id=? AND step_id=? AND provider=? AND status='abgebrochen'",
                (run_id, step_id, provider),
            ).fetchone()
        return int(row[0])

    def update_decision_context(self, decision_id: str, patch: dict[str, Any]) -> None:
        """Ergänzt den Kontext einer offenen Entscheidung (z. B. Ergebnis der Klickprüfung)."""
        with self._lock, self.db:
            row = self.db.execute("SELECT context, status FROM decisions WHERE id=?", (decision_id,)).fetchone()
            if row is None or row["status"] != "offen":
                return
            context = {**json.loads(row["context"]), **patch}
            self.db.execute("UPDATE decisions SET context=? WHERE id=?", (canonical(context), decision_id))

