"""Fachagenten: von Administratoren angelegte Agenten für Fachaufgaben außerhalb des V-Modells.

Beispiel: ein Einkaufs-Agent, der Lieferantenmails beantwortet. Grundsätze (KI-U-02, KI-U-05):

- Nur lokale Modelle über FLOWGATE (eigener Schlüssel „fachagenten“); kein Abo-Worker, kein Internet.
- Keine Werkzeuge: Fachagenten lesen nur, was die Plattform ihnen für die berechtigte Person mitgibt
  (Eingang und freigegebene Datenquellen), und liefern ausschließlich Entwürfe (Stufe A1).
- Ein Mensch gibt jeden Entwurf frei oder verwirft ihn; alles wird protokolliert.
- Anlegen, Ändern und Pausieren nur durch Administratoren; nutzen dürfen die zugewiesenen
  AD-Gruppen (Realm-Rollen) und Personen.
"""

from __future__ import annotations

import json
import re
from typing import Any

ADMIN_ROLES = frozenset({"platform-admin"})
DATA_CLASSES = ("oeffentlich", "intern", "vertraulich")
STATUSES = ("aktiv", "pausiert")
SAFE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.@:-]{0,79}")
CONTEXT_LIMIT = 14000  # Zeichen Hintergrunddaten je Aufgabe (lokale Modelle)

# Vorlagen bestimmen Eingang und Ergebnisform; die Rollenanweisung schreibt der Administrator.
TEMPLATES: dict[str, dict[str, Any]] = {
    "mail_antwort": {
        "label": "E-Mails beantworten",
        "inputs": {"absender": "Absender", "betreff": "Betreff", "text": "Text der E-Mail"},
        "output": {"kategorie": "str", "zusammenfassung": "str", "antwort_betreff": "str", "antwort_text": "str",
                   "rueckfragen": "list", "risiko": "str"},
        "hint": ('Antworte als JSON: {"kategorie": "z. B. Lieferterminverschiebung, Preisanfrage, Reklamation", '
                 '"zusammenfassung": "1–2 Sätze", "antwort_betreff": "Re: …", "antwort_text": "vollständige Antwort '
                 'in der Sprache der E-Mail, höflich, ohne erfundene Zusagen", "rueckfragen": ["was ein Mensch vor dem '
                 'Versand klären muss"], "risiko": "niedrig|mittel|hoch"}. Sage nie Preise, Termine oder Mengen zu, die '
                 "nicht in den Hintergrunddaten stehen; markiere sie dann als Rückfrage."),
    },
    "zusammenfassen": {
        "label": "Text zusammenfassen und Aufgaben ableiten",
        "inputs": {"titel": "Titel", "text": "Text"},
        "output": {"zusammenfassung": "str", "aufgaben": "list", "offene_fragen": "list"},
        "hint": ('Antworte als JSON: {"zusammenfassung": "…", "aufgaben": ["Wer macht was bis wann"], '
                 '"offene_fragen": ["…"]}.'),
    },
    "assistent": {
        "label": "Fachassistent (Fragen beantworten)",
        "inputs": {"frage": "Frage"},
        "output": {"antwort": "str", "quellen": "list", "naechste_schritte": "list"},
        "hint": ('Antworte als JSON: {"antwort": "…", "quellen": ["welche Hintergrunddaten du genutzt hast"], '
                 '"naechste_schritte": ["…"]}. Wenn die Daten nicht reichen, sage das.'),
    },
}

# Datenquellen: die Plattform liest sie für die anfragende Person und gibt sie nur mit, wenn die Person
# eine der Rollen hat. Der Agent selbst hat keinen Zugriff auf Fachsysteme.
CONTEXT_SOURCES: dict[str, dict[str, Any]] = {
    "einkauf": {"label": "Einkauf: Bestellungen, Lieferantentermine, Zahlungsbedingungen",
                "roles": ["procurement-user", "management-user", "platform-admin"]},
    "qualitaet": {"label": "Qualität: Wareneingangsprüfungen und Abweichungen",
                  "roles": ["quality-user", "management-user", "platform-admin"]},
    "auftrag": {"label": "Kundenauftrag und Fertigungsstand",
                "roles": ["sales-user", "planning-user", "management-user", "platform-admin"]},
}

COMMON = (
    "Du bist ein Fachagent eines Industrieunternehmens und arbeitest nur mit dem lokalen Modell. Du lieferst "
    "ausschließlich einen Entwurf, den ein Mensch prüft und freigibt; du versendest, buchst oder genehmigst nichts. "
    "Nutze nur den Eingang und die mitgegebenen Hintergrunddaten. Erfinde keine Fakten. Antworte nur mit JSON."
)

DESIGN_PROMPT = (
    "Du hilfst einem Administrator, einen Fachagenten anzulegen. Aus der Beschreibung erzeugst du einen Vorschlag "
    'als JSON: {"name": "kurzer Name, z. B. Einkaufs-Mail-Agent", "purpose": "Zweck in einem Satz", '
    '"template": "mail_antwort|zusammenfassen|assistent", "context_sources": ["einkauf|qualitaet|auftrag"], '
    '"data_class": "oeffentlich|intern|vertraulich", "prompt": "Rollenanweisung in der Du-Form, 5–12 Sätze: '
    'Aufgabe, Ton, was er nie tun darf, wann er Rückfragen stellt", "suggested_roles": ["Realm-Rollen wie '
    'procurement-user"]}. Der Agent liefert immer nur Entwürfe zur Freigabe durch einen Menschen.'
)


class SpecError(ValueError):
    """Ungültige Definition eines Fachagenten."""


def _text(spec: dict[str, Any], name: str, low: int, high: int) -> str:
    value = " ".join(str(spec.get(name) or "").split()) if name != "prompt" else str(spec.get(name) or "").strip()
    if not low <= len(value) <= high:
        raise SpecError(f"{name}: {low} bis {high} Zeichen")
    return value


def validate_spec(spec: dict[str, Any], profiles: dict[str, Any]) -> dict[str, Any]:
    """Definition prüfen und normalisieren (fail closed)."""
    template = str(spec.get("template") or "")
    if template not in TEMPLATES:
        raise SpecError(f"Vorlage muss eine von {', '.join(TEMPLATES)} sein")
    profile = str(spec.get("model_profile") or "assistenz")
    if profile not in profiles:
        raise SpecError(f"Modellprofil muss eines von {', '.join(profiles)} sein")
    sources = [str(s) for s in spec.get("context_sources") or []]
    if not set(sources) <= set(CONTEXT_SOURCES):
        raise SpecError(f"Datenquellen nur aus {', '.join(CONTEXT_SOURCES)}")
    data_class = str(spec.get("data_class") or "intern")
    if data_class not in DATA_CLASSES:
        raise SpecError("Datenklasse muss oeffentlich, intern oder vertraulich sein")
    status = str(spec.get("status") or "aktiv")
    if status not in STATUSES:
        raise SpecError("Status muss aktiv oder pausiert sein")
    roles = sorted({str(r).strip() for r in spec.get("assigned_roles") or [] if str(r).strip()})
    users = sorted({str(u).strip() for u in spec.get("assigned_users") or [] if str(u).strip()})
    for value in [*roles, *users]:
        if not SAFE.fullmatch(value):
            raise SpecError(f"ungültige Zuweisung {value!r}")
    if not roles and not users:
        raise SpecError("Bitte mindestens eine AD-Gruppe (Rolle) oder Person zuweisen")
    return {
        "name": _text(spec, "name", 3, 80), "purpose": _text(spec, "purpose", 10, 500),
        "template": template, "model_profile": profile, "context_sources": sources, "data_class": data_class,
        "prompt": _text(spec, "prompt", 20, 8000), "assigned_roles": roles, "assigned_users": users,
        "status": status, "autonomy": "A1",
    }


def validate_input(template: str, values: dict[str, Any]) -> dict[str, str]:
    fields = TEMPLATES[template]["inputs"]
    clean = {name: str(values.get(name) or "").strip()[:12000] for name in fields}
    main = list(fields)[-1]
    if len(clean[main]) < 5:
        raise SpecError(f"{fields[main]} fehlt")
    return clean


def may_use(spec: dict[str, Any], user: dict[str, Any]) -> bool:
    roles = {str(r) for r in user.get("roles", [])}
    return bool(roles & ADMIN_ROLES) or str(user.get("username", "")) in spec.get("assigned_users", []) or \
        bool(roles & set(spec.get("assigned_roles", [])))


def is_admin(user: dict[str, Any]) -> bool:
    return bool({str(r) for r in user.get("roles", [])} & ADMIN_ROLES)


def task_prompt(spec: dict[str, Any], values: dict[str, str], context: dict[str, Any]) -> tuple[str, str]:
    template = TEMPLATES[spec["template"]]
    system = f"{COMMON}\n\n# Rolle: {spec['name']}\n{spec['prompt']}\n\n# Ergebnisform\n{template['hint']}"
    lines = [f"## {template['inputs'][name]}\n{value}" for name, value in values.items() if value]
    background = ""
    if context:
        background = "\n\n# Hintergrunddaten (nur lesen)\n" + json.dumps(context, ensure_ascii=False)[:CONTEXT_LIMIT]
    return system, "# Eingang\n" + "\n\n".join(lines) + background


def normalize_output(template: str, result: dict[str, Any]) -> dict[str, Any]:
    """Ergebnis in die Form der Vorlage bringen; fehlende Pflichttexte sind ein Fehler."""
    shape = TEMPLATES[template]["output"]
    clean: dict[str, Any] = {}
    for name, kind in shape.items():
        value = result.get(name)
        if kind == "list":
            clean[name] = [str(v)[:500] for v in value] if isinstance(value, list) else ([str(value)] if value else [])
        else:
            clean[name] = str(value or "").strip()[:8000]
    texts = [clean[n] for n, k in shape.items() if k == "str" and n not in {"kategorie", "risiko"}]
    if not any(texts):
        raise SpecError("Antwort des Modells ist leer")
    if "risiko" in clean and clean["risiko"] not in {"niedrig", "mittel", "hoch"}:
        clean["risiko"] = "mittel"
    return clean


def normalize_design(result: dict[str, Any]) -> dict[str, Any]:
    """Vorschlag der lokalen KI für den Dialog (wird erst nach Prüfung durch den Admin gespeichert)."""
    template = str(result.get("template") or "assistent")
    sources = [s for s in result.get("context_sources") or [] if s in CONTEXT_SOURCES]
    data_class = str(result.get("data_class") or "intern")
    roles = [str(r) for r in result.get("suggested_roles") or [] if SAFE.fullmatch(str(r))]
    return {
        "name": " ".join(str(result.get("name") or "").split())[:80],
        "purpose": " ".join(str(result.get("purpose") or "").split())[:500],
        "template": template if template in TEMPLATES else "assistent",
        "context_sources": sources, "data_class": data_class if data_class in DATA_CLASSES else "intern",
        "prompt": str(result.get("prompt") or "").strip()[:8000], "assigned_roles": roles[:6],
    }


def public_templates() -> dict[str, Any]:
    return {
        "templates": {key: {"label": spec["label"], "inputs": spec["inputs"], "output": list(spec["output"])}
                      for key, spec in TEMPLATES.items()},
        "sources": {key: {"label": spec["label"], "roles": spec["roles"]} for key, spec in CONTEXT_SOURCES.items()},
        "data_classes": list(DATA_CLASSES),
    }
