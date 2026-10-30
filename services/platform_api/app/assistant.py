from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from .business_tools import (
    list_late_purchase_orders,
    list_production_orders,
    select_read_tools,
    sources_from_results,
)
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

    if any(word in normalized for word in ("produktion", "fertigung", "work order")):
        result = list_production_orders(state)
        if result["orders"]:
            descriptions = ", ".join(
                f"{order['work_order']} fuer {order['quantity']} {order['product']} "
                f"({order['progress_percent']} %)"
                for order in result["orders"]
            )
            text = f"Aktuell in Produktion: {descriptions}."
        else:
            text = "Aktuell ist kein Fertigungsauftrag in der Produktion aktiv."
        sources = sources_from_results([result])
        tools_used = [result["tool"]]
    elif any(word in normalized for word in ("bestellung", "purchase", "lieferant")) and any(
        word in normalized for word in ("verspaet", "verspät", "ueberfaellig", "überfällig", "late")
    ):
        result = list_late_purchase_orders(state)
        if result["orders"]:
            descriptions = ", ".join(
                f"{order['id']} von {order['supplier']} ({order['delay_days']} Tage, "
                f"erwartet {order['expected_date']})"
                for order in result["orders"]
            )
            text = f"Verspaetete Bestellungen: {descriptions}."
        else:
            text = "Derzeit ist keine Bestellung als verspaetet markiert."
        sources = sources_from_results([result])
        tools_used = [result["tool"]]
    elif any(word in normalized for word in ("dokument", "revision", "zeichnung")):
        relevant = [doc for doc in documents if doc["item"] == "SCU-100"]
        names = ", ".join(f"{doc['title']} ({doc['revision']})" for doc in relevant)
        text = f"Fuer SCU-100 Revision C gelten aktuell: {names}."
        sources = [
            {"system": "Paperless", "reference": doc["id"], "label": doc["title"]}
            for doc in relevant
        ]
        tools_used = ["search_documents"]
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
        tools_used = ["get_order_status"]
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
        tools_used = ["get_order_status"]
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
        tools_used = ["get_order_status"]
    return {
        "answer": text,
        "sources": sources,
        "mode": "deterministic",
        "tools_used": tools_used,
    }


def _ask_ollama(
    question: str, state: dict[str, Any], settings: Settings
) -> dict[str, Any] | None:
    tool_results = select_read_tools(question, state)
    tools_used = [result["tool"] for result in tool_results]
    prompt = (
        "/no_think\n"
        "Du bist ein Produktionsassistent. Antworte ohne Markdown in hoechstens vier Saetzen "
        "auf Deutsch und uebersetze technische Statuswerte in verstaendliches Deutsch. "
        "Verwende ausschliesslich die folgenden Ergebnisse freigegebener Lesewerkzeuge. "
        "Wenn die Ergebnisliste leer ist, sage das klar. Erfinde keine Daten und fuehre keine "
        "Schreibaktion aus. Nenne Belegreferenzen, wenn sie in den Ergebnissen stehen.\n"
        f"Werkzeugergebnisse: {json.dumps(tool_results, ensure_ascii=False)}\n"
        f"Frage: {question}"
    )
    payload = json.dumps(
        {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 320},
        }
    ).encode()
    request = urllib.request.Request(
        f"{settings.ollama_base_url.rstrip('/')}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.ollama_timeout_seconds) as response:
            result = json.load(response)
        return {
            "answer": _clean_response(result["response"]),
            "sources": sources_from_results(tool_results),
            "mode": "ollama",
            "model": settings.ollama_model,
            "tools_used": tools_used,
        }
    except (OSError, KeyError, ValueError, urllib.error.URLError):
        return None


def _clean_response(text: str) -> str:
    without_thinking = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    without_markdown = without_thinking.replace("**", "").replace("*", "")
    return without_markdown.strip()
