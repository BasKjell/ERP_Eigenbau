"""Maschinenlesbare Übergabe (KI-Entwicklungskonzept Teil 07) strikt prüfen.

Nur ein schema- und zustandskonformes Ergebnis darf den Ablauf fortsetzen. Unbekannte Felder,
fehlende Pflichtfelder oder ein widersprüchlicher Status sperren die Übergabe.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

STATUSES = ("fertig", "nacharbeit", "entscheidung_offen", "abgebrochen")
SEVERITIES = ("hoch", "mittel", "niedrig")
BLOCKING = frozenset({"hoch", "mittel"})
QUESTION_TARGETS = ("product-owner", "tech-lead", "geschaeftsfuehrung", "key-user", "release")
MAX_BYTES = 250_000
MAX_TEXT = 20_000
MAX_CONTENT = 80_000

# Artefakttyp je Rolle: (Pflichtfelder mit Typ, optionale Felder mit Typ, Höchstzahl)
LIST = list
ARTIFACTS: dict[str, tuple[str, dict[str, type], dict[str, type], int]] = {
    "anforderungen": (
        "anforderung",
        {"key": str, "title": str, "text": str, "priority": str, "source": str, "acceptance_criteria": LIST},
        {"rationale": str, "negative_case": str},
        12,
    ),
    "architektur": (
        "architektur",
        {"key": str, "title": str, "decision": str, "components": LIST, "data_flows": LIST, "threats": LIST},
        {"alternatives": LIST, "trust_boundaries": LIST, "new_trust_boundary": bool, "recovery": str},
        3,
    ),
    "planung": ("aufgabe", {"key": str, "title": str, "covers": LIST}, {"depends_on": LIST}, 15),
    "akzeptanztest": (
        "testfall",
        {"key": str, "title": str, "criterion": str, "steps": LIST},
        {"preconditions": str, "negative": bool},
        20,
    ),
    "entwicklung": ("dateiaenderung", {"key": str, "title": str, "content": str}, {}, 6),
    "dokumentation": ("dokument", {"key": str, "title": str, "content": str}, {"audience": str, "covers": LIST}, 6),
    "nachweise": ("nachweis", {"key": str, "title": str, "evidence": str, "state": str}, {"digest": str}, 30),
    "geschaeftsfuehrung": (
        "bewertung",
        {"key": str, "title": str, "benefit": str, "staff_effort": str, "process_fit": str,
         "risks": LIST, "recommendation": str},
        {},
        1,
    ),
}
REVIEW_ONLY = frozenset({"anforderungspruefung", "sicherheit", "codepruefung"})


class ContractError(ValueError):
    """Die Übergabe verletzt den Ergebnisvertrag."""


@dataclass(frozen=True)
class Handoff:
    status: str
    summary: str
    artifacts: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    questions: list[dict[str, Any]]

    def blocking_findings(self) -> list[dict[str, Any]]:
        return [item for item in self.findings if item["severity"] in BLOCKING]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "summary": self.summary,
            "artifacts": self.artifacts,
            "findings": self.findings,
            "questions": self.questions,
        }


THINK = re.compile(r"<think>.*?</think>", re.S | re.I)


def extract_json(text: str) -> dict[str, Any]:
    """Erstes JSON-Objekt aus einer Modellantwort lesen (Denkblöcke und Codezäune ignorieren)."""
    if len(text.encode("utf-8", "replace")) > MAX_BYTES * 2:
        raise ContractError("Antwort überschreitet das Größenlimit")
    cleaned = THINK.sub("", text)
    start = cleaned.find("{")
    if start < 0:
        raise ContractError("Antwort enthält kein JSON-Objekt")
    try:
        value, _ = json.JSONDecoder().raw_decode(cleaned[start:])
    except json.JSONDecodeError as exc:
        raise ContractError(f"Antwort ist kein gültiges JSON: {exc.msg}") from None
    if not isinstance(value, dict):
        raise ContractError("Antwort ist kein JSON-Objekt")
    return value


def _text(value: Any, label: str, limit: int = MAX_TEXT, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()) or len(value) > limit:
        raise ContractError(f"{label} muss ein nicht leerer Text bis {limit} Zeichen sein")
    if "\0" in value:
        raise ContractError(f"{label} enthält Nullbytes")
    return value.strip() if label != "content" else value


def _check_fields(item: Any, required: dict[str, type], optional: dict[str, type], label: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ContractError(f"{label} muss ein Objekt sein")
    unknown = set(item) - set(required) - set(optional) - {"type"}
    if unknown:
        raise ContractError(f"{label}: unbekannte Felder {sorted(unknown)}")
    missing = set(required) - set(item)
    if missing:
        raise ContractError(f"{label}: Pflichtfelder fehlen {sorted(missing)}")
    result: dict[str, Any] = {}
    for name, kind in {**required, **optional}.items():
        if name not in item:
            continue
        value = item[name]
        if kind is str:
            result[name] = _text(value, name, MAX_CONTENT if name == "content" else MAX_TEXT)
        elif kind is bool:
            if not isinstance(value, bool):
                raise ContractError(f"{label}.{name} muss true oder false sein")
            result[name] = value
        else:
            if not isinstance(value, list) or len(value) > 50:
                raise ContractError(f"{label}.{name} muss eine Liste mit höchstens 50 Einträgen sein")
            result[name] = value
    return result


def validate(raw: dict[str, Any], *, role: str, kind: str, limit: int | None = None) -> Handoff:
    """Prüft eine Übergabe für *role* (Art *kind*: create oder review)."""
    if len(json.dumps(raw, ensure_ascii=False).encode()) > MAX_BYTES:
        raise ContractError("Übergabe überschreitet das Größenlimit")
    unknown = set(raw) - {"status", "summary", "artifacts", "findings", "questions"}
    if unknown:
        raise ContractError(f"unbekannte Felder in der Übergabe: {sorted(unknown)}")
    status = raw.get("status")
    if status not in STATUSES:
        raise ContractError(f"status muss einer von {', '.join(STATUSES)} sein")
    summary = _text(raw.get("summary"), "summary", 2000)
    artifacts_raw = raw.get("artifacts", [])
    findings_raw = raw.get("findings", [])
    questions_raw = raw.get("questions", [])
    for name, value in (("artifacts", artifacts_raw), ("findings", findings_raw), ("questions", questions_raw)):
        if not isinstance(value, list):
            raise ContractError(f"{name} muss eine Liste sein")

    artifacts: list[dict[str, Any]] = []
    if role in REVIEW_ONLY:
        if artifacts_raw:
            raise ContractError("Prüfrollen liefern keine Artefakte, nur Befunde")
    elif role in ARTIFACTS:
        artifact_type, required, optional, maximum = ARTIFACTS[role]
        maximum = min(maximum, limit) if limit else maximum
        if len(artifacts_raw) > maximum:
            raise ContractError(f"höchstens {maximum} Artefakte vom Typ {artifact_type}")
        keys: set[str] = set()
        for index, item in enumerate(artifacts_raw):
            label = f"artifacts[{index}]"
            if isinstance(item, dict) and item.get("type", artifact_type) != artifact_type:
                raise ContractError(f"{label}: Typ muss {artifact_type} sein")
            checked = _check_fields(item, required, optional, label)
            if checked["key"] in keys:
                raise ContractError(f"{label}: Schlüssel {checked['key']} doppelt")
            keys.add(checked["key"])
            _check_items(role, checked, label)
            artifacts.append({"type": artifact_type, **checked})
    elif artifacts_raw:
        raise ContractError(f"Rolle {role} liefert keine Artefakte")

    findings = []
    for index, item in enumerate(findings_raw):
        checked = _check_fields(
            item, {"severity": str, "location": str, "impact": str}, {"recommendation": str}, f"findings[{index}]"
        )
        if checked["severity"] not in SEVERITIES:
            raise ContractError(f"findings[{index}].severity muss hoch, mittel oder niedrig sein")
        findings.append(checked)
    questions = []
    for index, item in enumerate(questions_raw):
        checked = _check_fields(item, {"to": str, "question": str}, {"impact": str}, f"questions[{index}]")
        if checked["to"] not in QUESTION_TARGETS:
            raise ContractError(f"questions[{index}].to muss einer von {', '.join(QUESTION_TARGETS)} sein")
        questions.append(checked)

    blocking = [item for item in findings if item["severity"] in BLOCKING]
    if status == "entscheidung_offen" and not questions:
        raise ContractError("entscheidung_offen braucht mindestens eine Frage")
    if kind == "review":
        if status == "fertig" and blocking:
            raise ContractError("fertig (bereit) ist mit blockierenden Befunden unzulässig")
        if status == "nacharbeit" and not blocking:
            raise ContractError("nacharbeit braucht mindestens einen Befund der Schwere hoch oder mittel")
    else:
        if status == "nacharbeit":
            raise ContractError("Ersteller melden nach einer Überarbeitung „fertig“; „nacharbeit“ ist Prüfrollen vorbehalten")
        if status == "fertig" and not artifacts:
            raise ContractError("fertig braucht mindestens ein Artefakt")
    return Handoff(status, summary, artifacts, findings, questions)


def _check_items(role: str, artifact: dict[str, Any], label: str) -> None:
    if role == "anforderungen":
        criteria = artifact["acceptance_criteria"]
        if not criteria or not all(isinstance(c, str) and c.strip() for c in criteria):
            raise ContractError(f"{label}: mindestens ein Akzeptanzkriterium als Text")
        if artifact["priority"] not in {"Muss", "Soll", "Kann"}:
            raise ContractError(f"{label}: priority muss Muss, Soll oder Kann sein")
    elif role == "architektur":
        for threat in artifact["threats"]:
            if not isinstance(threat, dict) or not {"threat", "control"} <= set(threat):
                raise ContractError(f"{label}: jede Bedrohung braucht threat und control")
    elif role == "akzeptanztest":
        steps = artifact["steps"]
        if not steps or not all(isinstance(s, dict) and {"action", "expected"} <= set(s) for s in steps):
            raise ContractError(f"{label}: jeder Schritt braucht action und expected")
    elif role == "nachweise" and artifact["state"] not in {"belegt", "luecke"}:
        raise ContractError(f"{label}: state muss belegt oder luecke sein")
    elif role == "geschaeftsfuehrung" and artifact["recommendation"] not in {"weiter", "mit Auflagen", "anhalten"}:
        raise ContractError(f"{label}: recommendation muss weiter, mit Auflagen oder anhalten sein")
    for name in ("covers", "depends_on", "components", "data_flows", "risks", "alternatives", "trust_boundaries"):
        values = artifact.get(name)
        if values is not None and not all(isinstance(v, str) and len(v) <= 2000 for v in values):
            raise ContractError(f"{label}.{name} muss eine Liste von Texten sein")
