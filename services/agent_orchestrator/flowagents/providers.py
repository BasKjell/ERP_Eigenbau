"""Modellanbindungen für die Agentenrollen.

- ``gateway``: lokale Modelle über FLOWGATE (agentgateway, OpenAI-kompatibel). Jede Rolle nutzt
  ihren eigenen virtuellen Schlüssel; FLOWGATE erlaubt je Schlüssel nur den Alias des Profils.
- ``simulated``: deterministische, regelbasierte Ergebnisse für Tests, CI und Vorführungen
  ohne Modellserver. Alle Ergebnisse sind als „simuliert“ gekennzeichnet.
- ``codex`` / ``claude``: Abo-CLIs in isolierten Containern (siehe ``container.py``), technisch
  gesperrt bis zur ausdrücklichen Betriebsfreigabe.

Kein Provider erhält Werkzeuge oder Zugangsdaten der Fachsysteme.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

from .registry import Agent


class ProviderError(RuntimeError):
    """Modellaufruf fehlgeschlagen (Netz, Zeitlimit, ungültige Antwort)."""


class _Transient(Exception):
    """Vorübergehender Fehler (Modellwechsel, Überlast); wird begrenzt wiederholt."""


@dataclass(frozen=True)
class AgentRequest:
    run_id: str
    step_id: str
    agent: Agent
    system: str
    user: str
    max_tokens: int
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentReply:
    text: str
    provider: str
    model: str
    output_tokens: int
    input_tokens: int = 0
    seconds: float = 0.0
    first_token_seconds: float = 0.0  # Einlesezeit bis zum ersten Token (nur bei gestreamten Antworten)


class Provider(Protocol):
    name: str

    def generate(self, request: AgentRequest) -> AgentReply: ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        return None


class GatewayProvider:
    """OpenAI-kompatibler Aufruf an FLOWGATE mit rollengebundenem virtuellem Schlüssel."""

    name = "gateway"

    def __init__(
        self, base_url: str, keys: dict[str, str], *, timeout: float = 900, no_think: bool = True,
        retries: int = 2, backoff: float = 8.0,
    ) -> None:
        if not re.fullmatch(r"https?://[A-Za-z0-9_.:-]+(/[A-Za-z0-9_./-]*)?", base_url):
            raise ValueError("ungültige Gateway-URL")
        self.base_url = base_url.rstrip("/")
        self.keys = keys
        self.timeout = timeout
        self.no_think = no_think
        self.retries = retries
        self.backoff = backoff
        self._opener = urllib.request.build_opener(_NoRedirect())

    def generate(self, request: AgentRequest) -> AgentReply:
        key = self.keys.get(request.agent.role)
        if not key:
            raise ProviderError(f"kein FLOWGATE-Schlüssel für Rolle {request.agent.role}")
        system = request.system
        if self.no_think and request.agent.family == "qwen":
            system = "/no_think\n" + system  # qwen3: Denkmodus aus, strukturierte Antwort
        body: dict[str, Any] = {
            "model": request.agent.gateway_alias,
            "temperature": 0.2,
            "max_tokens": request.max_tokens,
            # Gestreamt, damit FLOWGATE Einlesezeit (Zeit bis zum ersten Token) und reine
            # Schreibgeschwindigkeit je Modell misst; die Nutzung kommt im letzten Abschnitt.
            "stream": True,
            "stream_options": {"include_usage": True},
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": request.user},
            ],
        }
        if self.no_think:
            # Ollama (OpenAI-kompatibel): schaltet den Denkmodus von qwen3 ab, andere Modelle ignorieren es.
            body["reasoning_effort"] = "none"
        last_error = "unbekannt"
        for attempt in range(self.retries + 1):
            try:
                return self._send(request, key, body)
            except _Transient as exc:
                last_error = str(exc)
                if attempt < self.retries:
                    time.sleep(self.backoff * (attempt + 1))
        raise ProviderError(f"FLOWGATE vorübergehend nicht verfügbar: {last_error}")

    def _send(self, request: AgentRequest, key: str, body: dict[str, Any]) -> AgentReply:
        started = time.monotonic()
        http_request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                "X-Flow-Run": request.run_id,
                "X-Flow-Agent": request.agent.id,
            },
            method="POST",
        )
        first_token, streamed = 0.0, False
        text_parts: list[str] = []
        usage: dict[str, Any] = {}
        model = ""
        try:
            with self._opener.open(http_request, timeout=self.timeout) as response:
                if "event-stream" in str(response.headers.get("Content-Type", "")):
                    text_parts, usage, model, first_token = self._read_stream(response, started)
                    streamed, raw = True, b""
                else:
                    raw = response.read(4_000_000)
        except urllib.error.HTTPError as exc:
            if exc.code in {429, 500, 502, 503, 504}:
                raise _Transient(f"HTTP {exc.code}") from None
            raise ProviderError(f"FLOWGATE lehnte ab: HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if isinstance(exc, urllib.error.URLError) and isinstance(exc.reason, ConnectionRefusedError):
                raise ProviderError("FLOWGATE nicht erreichbar: ConnectionRefusedError") from None
            raise _Transient(type(exc).__name__) from None
        if streamed:
            text = "".join(text_parts)
            if not text.strip():
                raise _Transient("leere Antwort")
            return AgentReply(text=text, provider=self.name, model=model or request.agent.gateway_alias,
                              output_tokens=int(usage.get("completion_tokens") or len(text) // 4),
                              input_tokens=int(usage.get("prompt_tokens") or 0),
                              seconds=round(time.monotonic() - started, 2), first_token_seconds=first_token)
        if not raw.strip():
            raise _Transient("leere Antwort")
        try:
            payload = json.loads(raw)
        except ValueError:
            raise _Transient("keine JSON-Antwort") from None
        try:
            text = payload["choices"][0]["message"]["content"] or ""
            model = str(payload.get("model") or request.agent.gateway_alias)
            usage = payload.get("usage") or {}
            tokens = int(usage.get("completion_tokens") or len(text) // 4)
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderError("FLOWGATE lieferte keine Chat-Antwort") from None
        return AgentReply(text=text, provider=self.name, model=model, output_tokens=tokens,
                          input_tokens=prompt_tokens, seconds=round(time.monotonic() - started, 2))

    @staticmethod
    def _read_stream(response: Any, started: float) -> tuple[list[str], dict[str, Any], str, float]:
        """Server-Sent Events (OpenAI-Format) lesen: Text, Nutzung, Modell, Sekunden bis zum ersten Token."""
        parts: list[str] = []
        usage: dict[str, Any] = {}
        model, first_token, total = "", 0.0, 0
        for line in response:
            total += len(line)
            if total > 4_000_000:
                raise ProviderError("FLOWGATE-Antwort zu groß")
            line = line.strip()
            if not line.startswith(b"data:"):
                continue
            data = line[5:].strip()
            if data == b"[DONE]":
                break
            try:
                chunk = json.loads(data)
            except ValueError:
                raise _Transient("ungültiger Stream-Abschnitt") from None
            if chunk.get("error"):
                raise ProviderError(f"FLOWGATE meldet Fehler: {str(chunk['error'])[:200]}")
            model = str(chunk.get("model") or model)
            usage = chunk.get("usage") or usage
            for choice in chunk.get("choices") or []:
                piece = (choice.get("delta") or {}).get("content") or ""
                if piece and not first_token:
                    first_token = max(round(time.monotonic() - started, 3), 0.001)
                parts.append(piece)
        return parts, usage, model, first_token


class SimulatedProvider:
    """Regelbasierte Rollen für Tests und Vorführungen ohne Modellserver.

    Steuermarken im Auftragstext erzeugen gezielt Rückläufe:
    ``[sim:nacharbeit]`` – erste Anforderungsfassung ohne Negativfall (Prüfung schickt zurück),
    ``[sim:gf-bedenken]`` – Geschäftsführungs-Agent meldet Bedenken zum Auftrag,
    ``[sim:frage]`` – Anforderungs-Agent stellt eine Frage an den Product Owner.
    """

    name = "simulated"

    def generate(self, request: AgentRequest) -> AgentReply:
        handler = getattr(self, f"_{request.agent.role}", None)
        if handler is None:
            raise ProviderError(f"keine Simulation für Rolle {request.agent.role}")
        result = handler(request.context)
        text = json.dumps(result, ensure_ascii=False)
        return AgentReply(text=text, provider=self.name, model="simuliert", output_tokens=len(text) // 4)

    # -- Hilfen -------------------------------------------------------------------------
    @staticmethod
    def _auftrag(context: dict[str, Any]) -> dict[str, Any]:
        return context.get("auftrag") or {}

    @staticmethod
    def _flag(context: dict[str, Any], name: str) -> bool:
        auftrag = context.get("auftrag") or {}
        return f"[sim:{name}]" in " ".join(str(auftrag.get(key, "")) for key in ("goal", "behavior", "title"))

    @staticmethod
    def _requirements(context: dict[str, Any]) -> list[dict[str, Any]]:
        content = (context.get("artifacts") or {}).get("anforderungen") or {}
        return list(content.get("items") or [])

    # -- Rollen -------------------------------------------------------------------------
    def _geschaeftsfuehrung(self, context: dict[str, Any]) -> dict[str, Any]:
        auftrag = self._auftrag(context)
        final = context.get("subject_kind") == "nachweise"
        if not final and self._flag(context, "gf-bedenken") and not context.get("decisions"):
            return {
                "status": "nacharbeit",
                "summary": "Nutzen und Mehraufwand für Beschäftigte sind im Auftrag nicht erkennbar.",
                "artifacts": [self._bewertung(auftrag, "anhalten")],
                "findings": [{"severity": "mittel", "location": auftrag.get("id", "Auftrag"),
                              "impact": "Ohne messbares Ziel lässt sich der Nutzen nicht nachweisen.",
                              "recommendation": "Erfolgsbeispiel und Kennzahl ergänzen."}],
                "questions": [],
            }
        gaps = [item for item in ((context.get("artifacts") or {}).get("nachweise") or {}).get("items", [])
                if item.get("state") == "luecke"]
        findings = [{"severity": "niedrig", "location": auftrag.get("id", "Auftrag"),
                     "impact": "Nutzen ist eine Annahme bis zur Messung im Pilot.",
                     "recommendation": "Durchlaufzeit und Rückfragen vor und nach Einführung messen."}]
        if final and gaps:
            findings.append({"severity": "niedrig", "location": "Nachweise",
                             "impact": f"{len(gaps)} Nachweis(e) offen.",
                             "recommendation": "Lücken vor der Produktionsfreigabe schließen."})
        return {
            "status": "fertig",
            "summary": ("Ergebnis passt zu Zielbild und Abläufen; Fachabnahme kann erfolgen." if final
                        else "Auftrag passt zum Zielbild „eine Oberfläche“; weiter mit Auflagen."),
            "artifacts": [self._bewertung(auftrag, "mit Auflagen")],
            "findings": findings,
            "questions": [],
        }

    @staticmethod
    def _bewertung(auftrag: dict[str, Any], recommendation: str) -> dict[str, Any]:
        group = auftrag.get("user_group") or "Fachbereich"
        return {
            "type": "bewertung",
            "key": "GF-1",
            "title": f"Bewertung {auftrag.get('id', '')}: {auftrag.get('title', '')}".strip(),
            "benefit": f"{group} spart Such- und Abstimmungszeit: {auftrag.get('success_example') or 'Ziel laut Auftrag'}",
            "staff_effort": "Kein zusätzlicher Arbeitsschritt; Bedienung in FLOWPORTAL.",
            "process_fit": "Führendes System bleibt unverändert; Entscheidung bleibt beim Fachbereich.",
            "risks": ["Rechteprüfung muss im Quellsystem bleiben", "Nutzen erst nach Messung belegt"],
            "recommendation": recommendation,
        }

    def _projektplanung(self, context: dict[str, Any]) -> dict[str, Any]:
        auftrag = self._auftrag(context)
        scope = auftrag.get("scope") or ""
        packages = [
            ("AP-1", "Anforderungen festlegen", "Anforderungs-Baseline mit Prüfkriterien", "anforderungen", 1, []),
            ("AP-2", "Architektur und Schnittstellen", "Architektur mit Bedrohungsmodell", "software_architektur", 1, ["AP-1"]),
            ("AP-3", "Umsetzung im freigegebenen Bereich", "Geprüfter Änderungsstand mit Unit-Tests", "implementierung", 1, ["AP-2"]),
            ("AP-4", "Integration und Verifikation", "Bestandene Integrations- und Software-Tests", "software_verifikation", 2, ["AP-3"]),
            ("AP-5", "Abnahme durch den Fachbereich", "Dokumentierte Fachabnahme am Digest", "abnahme", 2, ["AP-4"]),
        ]
        artifacts = [
            {"type": "arbeitspaket", "key": key, "title": f"{title} ({auftrag.get('title', '')[:60]})", "result": result,
             "v_level": level, "acceptance": f"{result} liegt mit Nachweis vor", "wave": wave,
             "effort": "2–4 PT, Annahme: bestehende Plattform-API", "depends_on": deps,
             **({"scope": scope} if scope and level in {"implementierung", "anforderungen"} else {}),
             "owner_role": "Tech Lead" if level != "abnahme" else "Product Owner"}
            for key, title, result, level, wave, deps in packages
        ]
        return {"status": "fertig", "summary": f"{len(artifacts)} Arbeitspakete in 2 Wellen geschnitten.",
                "artifacts": artifacts, "findings": [], "questions": []}

    def _integrationstest(self, context: dict[str, Any]) -> dict[str, Any]:
        architecture = (context.get("artifacts") or {}).get("architektur") or {}
        tests = []
        for item in architecture.get("items", []):
            for index, flow in enumerate(item.get("data_flows") or ["Komponenten tauschen Daten aus"], start=1):
                tests.append({
                    "type": "integrationstestfall", "key": f"IT-{item.get('key', 'ADR')}-{index}",
                    "title": f"Schnittstelle prüfen: {flow}"[:150], "interface": flow.split(":")[0][:200],
                    "covers": ["R2/AC-2"], "preconditions": "Synthetische Testdaten, zwei Testprofile",
                    "steps": [{"action": f"Aufruf über {flow.split(':')[0]}",
                               "expected": "Antwort nur mit berechtigten Objekten; Fehler ohne Objektnamen"}],
                    "negative": True,
                })
        return {"status": "fertig", "summary": f"{len(tests)} Integrationstests aus der Architektur abgeleitet.",
                "artifacts": tests, "findings": [], "questions": []}

    def _anforderungen(self, context: dict[str, Any]) -> dict[str, Any]:
        auftrag = self._auftrag(context)
        source = auftrag.get("id", "A-?")
        rework = bool(context.get("findings_to_fix"))
        if self._flag(context, "frage") and not context.get("decisions"):
            return {
                "status": "entscheidung_offen",
                "summary": "Für die Aufbewahrung fehlt eine fachliche Vorgabe.",
                "artifacts": [],
                "findings": [],
                "questions": [{"to": "product-owner", "question": "Welche Aufbewahrungsfrist gilt für den Dokumenttyp?",
                               "impact": "Ohne Frist bleibt die Löschfunktion gesperrt."}],
            }
        behavior = auftrag.get("behavior") or auftrag.get("goal") or auftrag.get("title")
        main = {
            "type": "anforderung",
            "key": "R1",
            "title": auftrag.get("title", "Anforderung")[:120],
            "text": f"Das System muss: {behavior}",
            "priority": "Muss",
            "source": source,
            "rationale": auftrag.get("goal", ""),
            "acceptance_criteria": [f"AC-1: {auftrag.get('success_example') or 'Das gewünschte Verhalten ist beobachtbar.'}"],
        }
        rights = {
            "type": "anforderung",
            "key": "R2",
            "title": "Rechte und Freigabestatus bleiben wirksam",
            "text": "Vorhandene Rechte und der Freigabestatus gelten unverändert; das Quellsystem entscheidet.",
            "priority": "Muss",
            "source": source,
            "rationale": "KI-Entwicklungskonzept Teil 04: das Quellsystem entscheidet über Sichtbarkeit.",
            "acceptance_criteria": ["AC-2: Ein für die Nutzergruppe gesperrtes Objekt bleibt in jeder Ansicht unsichtbar."],
        }
        if not self._flag(context, "nacharbeit") or rework:
            main["negative_case"] = "Entwürfe und gesperrte Objekte erscheinen nicht."
            rights["negative_case"] = "Auch Titel, Trefferzahl und Vorschau verraten das Objekt nicht."
        return {
            "status": "fertig",
            "summary": f"{2} Anforderungen aus {source} abgeleitet" + (" und Befunde behoben." if rework else "."),
            "artifacts": [main, rights],
            "findings": [],
            "questions": [],
        }

    def _anforderungspruefung(self, context: dict[str, Any]) -> dict[str, Any]:
        findings = [
            {"severity": "mittel", "location": item.get("key", "?"),
             "impact": "Ohne Negativfall kann eine falsche Implementierung das Kriterium erfüllen.",
             "recommendation": "Negativfall für gesperrte oder unvollständige Objekte ergänzen."}
            for item in self._requirements(context)
            if item.get("priority") == "Muss" and not item.get("negative_case")
        ]
        return {
            "status": "nacharbeit" if findings else "fertig",
            "summary": ("Negativfälle fehlen." if findings else "Alle Muss-Anforderungen sind prüfbar und belegt."),
            "artifacts": [],
            "findings": findings,
            "questions": [],
        }

    def _architektur(self, context: dict[str, Any]) -> dict[str, Any]:
        auftrag = self._auftrag(context)
        return {
            "status": "fertig",
            "summary": "Änderung bleibt im zugelassenen Muster „eigene Oberfläche über Plattform-API“.",
            "artifacts": [{
                "type": "architektur",
                "key": "ADR-1",
                "title": f"Umsetzung von {auftrag.get('id', '')} im bestehenden Muster",
                "decision": "FLOWPORTAL-Oberfläche ruft die Plattform-API; die API fragt das Quellsystem im Namen der Person.",
                "alternatives": ["Anpassung der Oberfläche des Quellsystems", "eigene Datenhaltung (verworfen)"],
                "components": ["FLOWPORTAL", "Plattform-API", "Quellsystem (z. B. FLOWDOC)"],
                "data_flows": ["Browser -> Plattform-API: Anfrage mit Sitzung", "Plattform-API -> Quellsystem: Anfrage im Namen der Person"],
                "trust_boundaries": ["Browser / Plattform-API", "Plattform-API / Quellsystem"],
                "threats": [{"threat": "Umgehung der Objektrechte durch technisches Konto",
                             "control": "Delegierte Abfrage mit Benutzeridentität", "test": "AC-2",
                             "residual_risk": "niedrig"}],
                "new_trust_boundary": False,
                "recovery": "Zustandslos; Wiederanlauf durch Neustart, kein Datenverlust.",
            }],
            "findings": [],
            "questions": [],
        }

    def _sicherheit(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "fertig",
            "summary": "Keine neue Vertrauensgrenze; Rechteentscheidung bleibt im Quellsystem.",
            "artifacts": [],
            "findings": [{"severity": "niedrig", "location": "ADR-1",
                          "impact": "Fehlerseiten dürfen keine Objektnamen enthalten.",
                          "recommendation": "Negativtest für Fehlertexte aufnehmen."}],
            "questions": [],
        }

    def _planung(self, context: dict[str, Any]) -> dict[str, Any]:
        tasks = [
            {"type": "aufgabe", "key": f"DEV-{index}", "title": f"{item['key']} umsetzen: {item['title']}",
             "covers": [f"{item['key']}/{c.split(':')[0]}" for c in item.get("acceptance_criteria", [])],
             "depends_on": [] if index == 1 else ["DEV-1"]}
            for index, item in enumerate(self._requirements(context), start=1)
        ]
        return {"status": "fertig", "summary": f"{len(tasks)} Aufgaben geplant.", "artifacts": tasks,
                "findings": [], "questions": []}

    def _akzeptanztest(self, context: dict[str, Any]) -> dict[str, Any]:
        baseline = (context.get("artifacts") or {}).get("baseline") or {}
        tests = []
        for item in baseline.get("items", []):
            for criterion in item.get("acceptance_criteria", []):
                ac = criterion.split(":")[0]
                tests.append({
                    "type": "testfall", "key": f"AT-{item['key']}-{ac}", "title": f"Prüfung {item['key']} {ac}",
                    "criterion": f"{item['key']}/{ac}", "preconditions": "Synthetische Testdaten, Testprofil angemeldet",
                    "steps": [{"action": "Szenario laut Kriterium ausführen", "expected": criterion.split(":", 1)[-1].strip()}],
                    "negative": item["key"] != "R1",
                })
        return {"status": "fertig", "summary": f"{len(tests)} Akzeptanztests aus der Baseline abgeleitet.",
                "artifacts": tests, "findings": [], "questions": []}

    def _entwicklung(self, context: dict[str, Any]) -> dict[str, Any]:
        paths = [p for p in context.get("allowed_paths", []) if p.endswith(".md")]
        files = context.get("files") or {}
        if not paths:
            return {"status": "entscheidung_offen", "summary": "Der Simulationsmodus erzeugt keinen Programmcode.",
                    "artifacts": [], "findings": [],
                    "questions": [{"to": "tech-lead", "question": "Entwicklung mit FLOWGATE-Modell oder manuell durchführen?",
                                   "impact": "Ohne Implementierung bleibt G3 gesperrt."}]}
        auftrag = self._auftrag(context)
        changes = []
        for path in paths[:1]:
            original = files.get(path) or f"# {auftrag.get('title', 'Änderung')}\n"
            note = (f"\n\n## Änderung {auftrag.get('id', '')}: {auftrag.get('title', '')}\n\n"
                    f"{auftrag.get('behavior') or auftrag.get('goal', '')}\n\n"
                    "Rechte und Freigabestatus des Quellsystems gelten unverändert (R2).\n")
            changes.append({"type": "dateiaenderung", "key": path, "title": "Bedienhinweis ergänzt",
                            "content": original.rstrip("\n") + note})
        return {"status": "fertig", "summary": "Bedienhinweis im freigegebenen Pfad ergänzt.", "artifacts": changes,
                "findings": [], "questions": []}

    def _codepruefung(self, context: dict[str, Any]) -> dict[str, Any]:
        integration = (context.get("artifacts") or {}).get("integration") or {}
        if not integration.get("passed"):
            return {"status": "nacharbeit", "summary": "Integrationsprüfung am Digest nicht bestanden.", "artifacts": [],
                    "findings": [{"severity": "hoch", "location": "integration",
                                  "impact": "Pflichtprüfungen sind rot.", "recommendation": "Fehlschlag beheben."}],
                    "questions": []}
        return {"status": "fertig", "summary": f"Änderungsstand {integration.get('digest', '')[:19]} geprüft.",
                "artifacts": [], "findings": [], "questions": []}

    def _dokumentation(self, context: dict[str, Any]) -> dict[str, Any]:
        auftrag = self._auftrag(context)
        keys = [item.get("key") for item in self._requirements(context)]
        return {"status": "fertig", "summary": "Bedienhinweis und Release Notes erstellt.", "artifacts": [{
            "type": "dokument", "key": "DOC-1", "title": f"Release Notes {auftrag.get('id', '')}",
            "audience": auftrag.get("user_group") or "Fachbereich", "covers": keys,
            "content": f"### {auftrag.get('title', '')}\n\n- Neu: {auftrag.get('behavior') or auftrag.get('goal', '')}\n"
                       "- Unverändert: Rechte und Freigabestatus.\n- Rückfall: vorherige Version erneut ausliefern.",
        }], "findings": [], "questions": []}

    def _nachweise(self, context: dict[str, Any]) -> dict[str, Any]:
        digests = context.get("digests") or {}
        wanted = ["auftrag", "anforderungen", "anforderungsbefund", "baseline", "architektur", "sicherheitsbefund",
                  "akzeptanztests", "implementierung", "integration", "codebefund", "dokumentation"]
        items = [{"type": "nachweis", "key": f"N-{index}", "title": kind,
                  "evidence": f"{kind}@v{digests[kind]['version']}" if kind in digests else "fehlt",
                  "digest": digests.get(kind, {}).get("digest", ""),
                  "state": "belegt" if kind in digests else "luecke"}
                 for index, kind in enumerate(wanted, start=1)]
        gaps = sum(item["state"] == "luecke" for item in items)
        return {"status": "fertig", "summary": f"{len(items) - gaps} Belege zugeordnet, {gaps} Lücken.",
                "artifacts": items, "findings": [], "questions": []}
