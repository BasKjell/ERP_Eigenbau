from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .config import Settings


def answer_question(question: str, state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    if settings.ai_mode == "ollama":
        answer = _ask_ollama(question, state, settings)
        if answer:
            return answer
    return _deterministic_answer(question, state)


def _deterministic_answer(question: str, state: dict[str, Any]) -> dict[str, Any]:
    normalized = question.casefold()
    incident = state.get("quality_incident")
    open_incident = incident and incident.get("status") == "open"
    documents = state["documents"]

    if any(word in normalized for word in ("dokument", "revision", "zeichnung")):
        relevant = [doc for doc in documents if doc["item"] == "SCU-100"]
        names = ", ".join(f"{doc['title']} ({doc['revision']})" for doc in relevant)
        text = f"Fuer SCU-100 Revision C gelten aktuell: {names}."
        sources = [
            {"system": "Paperless", "reference": doc["id"], "label": doc["title"]}
            for doc in relevant
        ]
    elif any(word in normalized for word in ("kapaz", "engpass", "bottleneck", "planung")):
        bottleneck = max(state["capacity"], key=lambda resource: resource["utilization"])
        text = (
            f"Der aktuelle Engpass ist {bottleneck['name']} mit "
            f"{bottleneck['utilization']} % Auslastung. Auftrag 4711 ist eingeplant; "
            "der Liefertermin bleibt ohne weitere Stoerung erreichbar."
        )
        sources = [
            {"system": "MES", "reference": bottleneck["id"], "label": "Kapazitaetsplan"},
            {"system": "ERPNext", "reference": "WO-2027-0042", "label": "Fertigungsauftrag"},
        ]
    elif any(word in normalized for word in ("warum", "fehler", "verspaet", "abweich")):
        if open_incident:
            text = (
                f"Auftrag 4711 ist wegen {incident['id']} gefaehrdet: Beim Geraet "
                f"{incident['serial_number']} ist der {incident['test']} fehlgeschlagen. "
                f"Empfohlene Massnahme: {incident['action']}."
            )
            sources = [
                {"system": "MES", "reference": incident["id"], "label": "Qualitaetsabweichung"},
                {"system": "Paperless", "reference": "DOC-QP-100", "label": "Pruefplan"},
            ]
        else:
            text = (
                "Es besteht derzeit keine offene Abweichung. Material und Kapazitaet sind "
                "vorhanden; der Liefertermin ist nach aktuellem Stand nicht gefaehrdet."
            )
            sources = [
                {"system": "ERPNext", "reference": "SO-4711", "label": "Kundenauftrag"},
                {"system": "MES", "reference": "WO-2027-0042", "label": "Fertigungsauftrag"},
            ]
    else:
        metrics = state["metrics"]
        risk = (
            "Der Liefertermin ist durch die offene Qualitaetsabweichung gefaehrdet."
            if open_incident
            else "Der Liefertermin ist derzeit nicht gefaehrdet."
        )
        text = (
            f"Auftrag 4711 ueber {state['order']['quantity']} SCU-100 steht bei "
            f"\"{state['order']['status']}\" und ist zu {metrics['process_progress']} % "
            f"durchlaufen. {metrics['finished_units']} von {metrics['planned_units']} "
            f"Geraeten sind fertig. {risk}"
        )
        sources = [
            {"system": "ERPNext", "reference": "SO-4711", "label": "Kundenauftrag"},
            {"system": "MES", "reference": "WO-2027-0042", "label": "Fertigungsauftrag"},
            {"system": "Paperless", "reference": "DOC-QP-100", "label": "Pruefplan"},
        ]
    return {"answer": text, "sources": sources, "mode": "deterministic"}


def _ask_ollama(
    question: str, state: dict[str, Any], settings: Settings
) -> dict[str, Any] | None:
    context = {
        "order": state["order"],
        "metrics": state["metrics"],
        "process": state["process"],
        "quality_incident": state.get("quality_incident"),
        "documents": state["documents"],
    }
    prompt = (
        "Du bist ein Produktionsassistent. Antworte knapp auf Deutsch und erfinde nichts. "
        "Nenne die verwendeten Referenzen. Daten:\n"
        + json.dumps(context, ensure_ascii=False)
        + f"\nFrage: {question}"
    )
    payload = json.dumps(
        {"model": settings.ollama_model, "prompt": prompt, "stream": False}
    ).encode()
    request = urllib.request.Request(
        f"{settings.ollama_base_url.rstrip('/')}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            result = json.load(response)
        return {
            "answer": result["response"],
            "sources": [
                {"system": "ERPNext", "reference": "SO-4711", "label": "Kundenauftrag"},
                {"system": "MES", "reference": "WO-2027-0042", "label": "Fertigungsauftrag"},
            ],
            "mode": "ollama",
        }
    except (OSError, KeyError, ValueError, urllib.error.URLError):
        return None
