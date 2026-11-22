from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any

from .store import ScenarioStore


class WorkplaceNotFoundError(RuntimeError):
    pass


class WorkplaceService:
    """Role-aware, read-only daily cockpit used by FLOWPORTAL and MCP."""

    ROLE_PRIORITY = (
        ("platform-admin", "it"),
        ("it-user", "it"),
        ("project-user", "engineering"),
        ("finance-user", "finance"),
        ("hr-admin", "hr"),
        ("hr-user", "hr"),
        ("warehouse-user", "warehouse"),
        ("quality-user", "quality"),
        ("production-user", "production"),
        ("planning-user", "planning"),
        ("procurement-user", "procurement"),
        ("sales-user", "sales"),
    )

    ROLE_LABELS = {
        "procurement": "Einkauf",
        "engineering": "Entwicklung & Engineering",
        "production": "Produktion",
        "quality": "Qualität",
        "planning": "Disposition",
        "warehouse": "Lager",
        "sales": "Vertrieb",
        "hr": "Personal",
        "finance": "Finanzen",
        "it": "IT & Plattform",
        "general": "Mein Arbeitsplatz",
    }

    def __init__(self, store: ScenarioStore) -> None:
        self.store = store

    def daily_brief(
        self, user_id: str = "USR-006", selected_date: str = ""
    ) -> dict[str, Any]:
        state = self.store.get()
        user = self._user(state, user_id)
        work_date = self._date(selected_date)
        role = self._role(user)
        actions, kpis, insight = self._role_content(state, user, role, work_date)
        actions.extend(self._common_actions(state, user, work_date))
        actions = sorted(
            actions,
            key=lambda item: ({"critical": 0, "high": 1, "normal": 2}.get(item["priority"], 3), item["id"]),
        )[:6]
        agents = self._agents(role)
        return {
            "product": "FLOWPORTAL",
            "date": work_date,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "name": user["name"],
                "department": user["department"],
                "site_id": user["site_id"],
                "roles": user["roles"],
            },
            "role": {"key": role, "label": self.ROLE_LABELS[role]},
            "headline": self._headline(user, role, actions),
            "summary": insight,
            "kpis": kpis,
            "actions": actions,
            "schedule": self._schedule(role),
            "agents": agents,
            "suggested_prompts": self._prompts(role, actions),
            "mcp": {
                "connected_servers": [
                    {"id": "platform", "name": "Plattform & ERP", "mode": "lesen + bestätigte Testdaten"},
                    {"id": "dms", "name": "DMS", "mode": "nur lesen"},
                    {"id": "wiki", "name": "Prozess-Wiki", "mode": "nur lesen"},
                ],
                "tools": self.personal_tools(user_id),
                "identity_required": True,
                "write_policy": "Schreibaktionen nur mit Fachrolle, Vorschau und expliziter Bestätigung",
            },
            "sources": sorted({action["source"] for action in actions}),
        }

    def personal_tools(self, user_id: str = "USR-006") -> list[dict[str, Any]]:
        state = self.store.get()
        user = self._user(state, user_id)
        role = self._role(user)
        common = [
            self._tool("get_personal_daily_brief", "Persönliches Tagesbriefing", "platform", "read"),
            self._tool("get_personal_action_context", "Details zu einer Fokusaktion", "platform", "read"),
            self._tool("search_dms_documents", "Freigegebene Dokumente suchen", "dms", "read"),
            self._tool("search_process_documentation", "Prozess und Anleitung finden", "wiki", "read"),
        ]
        role_tools = {
            "procurement": [
                self._tool("list_late_purchase_orders", "Verspätete Bestellungen", "platform", "read"),
                self._tool("get_inventory", "Bestand und offene Zugänge", "platform", "read"),
                self._tool("supplier_follow_up", "Lieferantenanfrage vorbereiten", "FLOWERP", "prepare", "planned"),
            ],
            "engineering": [
                self._tool("requirements_focus", "Requirements, Reviews und Suspect Links", "platform", "read"),
                self._tool("change_impact", "Änderungsauswirkung zusammenfassen", "FLOWWORK", "prepare", "planned"),
                self._tool("review_decision", "Reviewentscheidung dokumentieren", "FLOWWORK", "confirm", "planned"),
            ],
            "production": [
                self._tool("list_production_orders", "Aktive Fertigungsaufträge", "platform", "read"),
                self._tool("next_mes_operation", "Nächsten ausführbaren Arbeitsgang zeigen", "platform", "read"),
                self._tool("book_mes_time", "Arbeitsgang starten oder Zeit buchen", "FLOWMES", "confirm", "planned"),
            ],
            "quality": [
                self._tool("quality_focus", "Offene Prüfungen und Reviews", "platform", "read"),
                self._tool("search_dms_documents", "Prüfpläne und Zertifikate", "dms", "read"),
                self._tool("release_receipt", "Lagerentscheidung bestätigen", "FLOWQ", "confirm", "planned"),
            ],
            "planning": [
                self._tool("list_production_orders", "Kapazität und Fertigungsstatus", "platform", "read"),
                self._tool("list_late_purchase_orders", "Fehlteile und Terminrisiken", "platform", "read"),
            ],
            "warehouse": [
                self._tool("warehouse_focus", "Wareneingänge, Seriennummern und Lagerplätze", "platform", "read"),
                self._tool("get_inventory", "Bestände je Lager", "platform", "read"),
            ],
            "sales": [
                self._tool("sales_focus", "Opportunities, Aufträge und Liefertermine", "platform", "read"),
                self._tool("get_order_status", "Auftragsstatus und Lieferrisiko", "platform", "read"),
            ],
            "hr": [
                self._tool("people_focus", "Anträge, Recruiting und Payroll", "platform", "read"),
                self._tool("approve_people_action", "HR-Entscheidung vorbereiten", "FLOWHR", "confirm", "planned"),
            ],
            "finance": [
                self._tool("finance_focus", "Cash, offene Posten und Budgetabweichungen", "platform", "read"),
                self._tool("prepare_datev_export", "DATEV-Export vorbereiten", "FLOWFIN", "confirm", "planned"),
            ],
            "it": [
                self._tool("platform_readiness", "Systemzustand und Integrationen", "platform", "read"),
                self._tool("access_review", "Rollen und Zugriffe prüfen", "FLOWID", "prepare", "planned"),
            ],
            "general": [],
        }
        unique: dict[str, dict[str, Any]] = {}
        for tool in common + role_tools.get(role, []):
            unique[tool["name"]] = tool
        return list(unique.values())

    def profiles(self) -> list[dict[str, str]]:
        state = self.store.get()
        return [
            {
                "id": user["id"],
                "name": user["name"],
                "department": user["department"],
                "role": self.ROLE_LABELS[self._role(user)],
            }
            for user in state["iam"]["users"]
        ]

    def future_operating_model(self) -> dict[str, Any]:
        """Return the management scenario for an exception-first workplace."""
        return {
            "product": "FLOWMANAGE",
            "horizon": "12 bis 24 Monate",
            "title": "Arbeitsplatz 2028",
            "status": "Zielbild und Pilotannahme, keine gemessene Ist-Leistung",
            "principle": (
                "KI-Agenten bearbeiten wiederkehrende Standardfälle innerhalb "
                "freigegebener Grenzen. Menschen übernehmen Ausnahmen, Beziehungen, "
                "Reviews und verantwortliche Entscheidungen."
            ),
            "scenario_mix": [
                {
                    "id": "bounded_automation",
                    "label": "Automatisch innerhalb klarer Regeln",
                    "share": 55,
                    "tone": "lime",
                    "examples": (
                        "Daten prüfen, Dokumente klassifizieren, Status nachhalten, "
                        "Standardtests ausführen und Entwürfe erzeugen"
                    ),
                },
                {
                    "id": "prepared_decision",
                    "label": "Von KI vorbereitet, vom Menschen bestätigt",
                    "share": 30,
                    "tone": "teal",
                    "examples": (
                        "Bestellungen, Terminänderungen, Qualitätsentscheidungen, "
                        "Code-Änderungen und externe Kommunikation"
                    ),
                },
                {
                    "id": "human_led",
                    "label": "Vom Menschen geführt",
                    "share": 15,
                    "tone": "dark",
                    "examples": (
                        "Verhandlungen, Kundenversprechen, Requirements-Freigaben, "
                        "Personalentscheidungen, Sicherheit und Architektur"
                    ),
                },
            ],
            "decision_inbox": [
                {
                    "id": "EXC-SUP-0088",
                    "domain": "Einkauf",
                    "title": "Lieferantentermin verbindlich klären",
                    "reason": "PO-2027-0088 gefährdet den Fertigungsplan",
                    "owner": "Felix Hoffmann",
                    "ai_prepared": "Auswirkung, Gesprächsleitfaden und zwei Terminszenarien",
                    "human_decision": "Lieferant anrufen und neuen Termin zusagen lassen",
                    "priority": "critical",
                },
                {
                    "id": "EXC-REQ-0101",
                    "domain": "Engineering",
                    "title": "System Requirement fachlich freigeben",
                    "reason": "Reviewkommentar ändert den Grenzwert im Prüfplan",
                    "owner": "Helena Friedrich",
                    "ai_prepared": "Änderungsauswirkung, betroffene Tests und Dokumente",
                    "human_decision": "Fachliche Aussage prüfen und Review signieren",
                    "priority": "high",
                },
                {
                    "id": "EXC-QA-0045",
                    "domain": "Qualität",
                    "title": "Abweichenden Messwert bewerten",
                    "reason": "Eine Stichprobe liegt außerhalb der Toleranz",
                    "owner": "Ben Schulz",
                    "ai_prepared": "Prüfplan, Historie, Messmittelstatus und Vorschlag",
                    "human_decision": "Sperren, nachprüfen oder freigeben",
                    "priority": "critical",
                },
                {
                    "id": "EXC-CUST-4711",
                    "domain": "Vertrieb",
                    "title": "Kundenzusage zum Liefertermin abstimmen",
                    "reason": "Materialrisiko verändert die belastbare Terminprognose",
                    "owner": "Anna Schneider",
                    "ai_prepared": "Auftragslage, Optionen und Gesprächsbriefing",
                    "human_decision": "Kundenkontakt führen und Zusage verantworten",
                    "priority": "high",
                },
            ],
            "autonomy_levels": [
                {
                    "level": "A0",
                    "label": "Erklären",
                    "rule": "lesen, zusammenfassen und Quellen verlinken",
                },
                {
                    "level": "A1",
                    "label": "Vorbereiten",
                    "rule": "Entwurf oder Entscheidungsvorlage erzeugen",
                },
                {
                    "level": "A2",
                    "label": "Bestätigt ausführen",
                    "rule": "Mensch prüft Ziel, Daten und Wirkung vor Ausführung",
                },
                {
                    "level": "A3",
                    "label": "Begrenzt automatisieren",
                    "rule": "nur innerhalb Policy, Limit, Evidenz und Rückfallweg",
                },
                {
                    "level": "A4",
                    "label": "Menschliche Verantwortung",
                    "rule": "Beziehung, Signatur, Haftung oder Grundsatzentscheidung",
                },
            ],
            "agent_register": [
                {
                    "id": "AG-SUPPLIER",
                    "name": "Lieferanten-Agent",
                    "owner": "Leitung Einkauf",
                    "autonomy": "A2",
                    "allowed": "Risiken erkennen, Anfrage entwerfen, bestätigte Erinnerung senden",
                    "escalation": "Terminabweichung, Vertragsfrage oder Preisänderung",
                    "evidence": "Quelle, Tool-Aufruf, Freigabe und Ergebnis",
                },
                {
                    "id": "AG-ENGINEERING",
                    "name": "Engineering-Agent",
                    "owner": "Leitung Entwicklung",
                    "autonomy": "A1",
                    "allowed": "Code, Tests, Dokumentation und Traceability vorbereiten",
                    "escalation": "Architektur, Security, Safety, Requirement oder Release",
                    "evidence": "Requirement, Diff, Testergebnis und Review",
                },
                {
                    "id": "AG-PLANNING",
                    "name": "Planungs-Agent",
                    "owner": "Leitung Operations",
                    "autonomy": "A2",
                    "allowed": "Szenarien rechnen und bestätigte Umplanung übertragen",
                    "escalation": "Kundentermin, Überlast oder Materialkonflikt",
                    "evidence": "Ausgangsdaten, Annahmen, Entscheidung und Wirkung",
                },
                {
                    "id": "AG-QUALITY",
                    "name": "Qualitäts-Agent",
                    "owner": "Leitung Qualität",
                    "autonomy": "A1",
                    "allowed": "Prüfkontext sammeln und Entscheidung vorbereiten",
                    "escalation": "Abweichung, Freigabe, Reklamation oder Safety-Bezug",
                    "evidence": "Prüfplan, Messwert, Messmittel und Signatur",
                },
            ],
            "guardrails": [
                "Jeder Agent besitzt einen fachlichen Owner und eine dokumentierte Grenze.",
                "Identität, Rolle und Projektkontext gelten bis zum letzten Tool-Aufruf.",
                "Kritische Aktionen benötigen Vorschau, Bestätigung und unveränderbare Evidenz.",
                "Qualität, Kosten, Fehlerquote und Eskalationen werden laufend gemessen.",
                "Bei Unsicherheit, Systemfehler oder Policy-Verstoß stoppt der Agent sicher.",
                "Betriebsrat, Datenschutz und Qualifizierung begleiten die Einführung.",
            ],
            "roadmap": [
                {
                    "period": "0 bis 6 Monate",
                    "focus": "Daten, Rollen, APIs und Agentenregister belastbar machen",
                },
                {
                    "period": "6 bis 12 Monate",
                    "focus": "Vorbereitung und bestätigte Aktionen in Pilotprozessen",
                },
                {
                    "period": "12 bis 18 Monate",
                    "focus": "Begrenzte Automatisierung für nachgewiesen stabile Standardfälle",
                },
                {
                    "period": "18 bis 24 Monate",
                    "focus": "Agenten koordinieren, Wirkung messen und Grenzen schrittweise erweitern",
                },
            ],
            "management_questions": [
                "Welche Entscheidungen bleiben ausdrücklich beim Menschen?",
                "Welche Agenten dürfen nachweislich auf A2 oder A3 wechseln?",
                "Welche Daten- und API-Lücken verhindern heute sichere Automatisierung?",
                "Wie messen wir Qualität, Durchlaufzeit, Fehler und Mitarbeiterentlastung?",
            ],
        }

    def action_context(
        self, action_id: str, user_id: str = "USR-006", selected_date: str = ""
    ) -> dict[str, Any]:
        brief = self.daily_brief(user_id, selected_date)
        action = next((item for item in brief["actions"] if item["id"] == action_id), None)
        if action is None:
            raise WorkplaceNotFoundError("Fokusaktion wurde für diesen Benutzer nicht gefunden")
        return {
            "tool": "get_personal_action_context",
            "user": brief["user"],
            "date": brief["date"],
            "action": action,
            "guardrail": "Die KI darf zusammenfassen und vorbereiten. Externe Kommunikation oder Buchung benötigt eine explizite Bestätigung.",
        }

    def _role_content(
        self, state: dict[str, Any], user: dict[str, Any], role: str, work_date: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
        if role == "procurement":
            history = state.get("workplace", {}).get("supplier_delivery_history", [])
            on_time = sum(item.get("status") == "on_time" for item in history)
            punctuality = round(on_time / len(history) * 100) if history else 0
            late = [item for item in state.get("purchase_orders", []) if item.get("status") == "late"]
            actions = [
                self._action(
                    f"supplier-{item['id']}", "critical", "FLOWERP", f"Liefertermin {item['id']} klären",
                    f"{item['supplier']} meldet {item['delay_days']} Tage Verzug für {item['item']}. Status anfragen und neuen Termin dokumentieren.",
                    "/work", f"Fasse das Lieferrisiko von {item['id']} zusammen und entwirf eine sachliche Lieferantenanfrage.",
                )
                for item in late[:2]
            ]
            actions.append(self._action("work-104", "high", "FLOWWORK", "Lieferantendokumente verknüpfen", "Ticket #104 ist Felix Hoffmann zugeordnet. Zertifikate mit KOM-2027-4711 verbinden.", "/work", "Zeige mir Ticket #104 und die passenden Lieferantendokumente."))
            receipts = [item for item in state["quality"]["receipts"] if item["status"] == "awaiting_inspection"]
            return actions, [
                self._kpi("Termintreue", f"{punctuality} %", "4 von 5 Lieferungen pünktlich", "warning" if punctuality < 90 else "good"),
                self._kpi("Terminrisiken", str(len(late)), "aktive Bestellungen", "critical" if late else "good"),
                self._kpi("Wareneingänge", str(len(receipts)), "warten auf Prüfung", "normal"),
            ], f"{punctuality} Prozent der letzten Lieferungen kamen pünktlich. Für {len(late)} Bestellung ist heute eine Rückfrage sinnvoll."

        if role == "engineering":
            issues = [item for item in state["work"]["issues"] if item.get("assignee") == user["name"] and item.get("status") != "Erledigt"]
            requirements = [item for item in state["work"]["requirements"] if item.get("owner") == user["name"]]
            comments = [comment for review in state["work"]["reviews"] for comment in review.get("comments", []) if user["username"].removeprefix("demo") in comment.get("mentions", []) or user["name"].split()[0].lower() in comment.get("mentions", [])]
            actions = [self._action(f"issue-{item['id']}", "high" if item.get("priority") == "Hoch" else "normal", "FLOWWORK", item["subject"], f"{item['key']} · fällig {item.get('due_date') or 'ohne Termin'} · {item.get('done_ratio', 0)} % erledigt", item["url"], f"Fasse {item['key']} mit den zugehörigen Requirements und Dokumenten zusammen.") for item in issues]
            if comments:
                actions.append(self._action("review-comment", "high", "FLOWWORK", "Reviewkommentar beantworten", comments[0]["text"], "/work?view=reviews", "Zeige den offenen Reviewkommentar und schlage eine fachliche Antwort vor."))
            return actions, [
                self._kpi("Meine Tasks", str(len(issues)), "heute im Engineering", "normal"),
                self._kpi("Requirements", str(len(requirements)), "in eigener Verantwortung", "normal"),
                self._kpi("Reviewhinweise", str(len(comments)), "offene Erwähnungen", "warning" if comments else "good"),
            ], "FLOWWORK bündelt heute Implementierungsaufgaben, Requirements und Reviewhinweise. Der KI-Agent kann den Änderungskontext quellenbasiert zusammenfassen."

        if role == "production":
            jobs = [item for item in state["mes"]["jobs"] if item["status"] in {"ready", "active", "paused"}]
            actions = [self._action(f"mes-{item['id']}", "high" if item.get("priority") == "high" else "normal", "FLOWMES", f"{item['operation']} · {item['id']}", f"{item['workstation']} · {item['target_qty']} Stück · Sollzeit {item['planned_minutes']} Minuten", f"/mes?job={item['id']}", f"Zeige Anleitung, Material und Pflichtprüfungen für {item['id']}.") for item in jobs[:3]]
            return actions, [self._kpi("Ausführbar", str(len(jobs)), "freigegebene Arbeitsgänge", "good"), self._kpi("Aktive Störung", str(sum(bool(item.get('issue')) for item in state['mes']['jobs'])), "Shopfloor", "good"), self._kpi("Schicht", state["mes"]["shift"]["name"], state["mes"]["area"], "normal")], "Das MES zeigt ausschließlich freigegebene Arbeit. FLOWAI kann Anleitung und Dokumente erklären, die Zeitbuchung bleibt eine bestätigte Bedienhandlung."

        if role == "quality":
            receipts = [item for item in state["quality"]["receipts"] if item["status"] == "awaiting_inspection"]
            actions = [self._action(f"quality-{item['id']}", "high", "FLOWQ", f"{item['item_name']} prüfen", f"{item['id']} · Charge {item['batch']} · {item['quantity_received']} {item['uom']}", f"/quality?receipt={item['id']}", f"Fasse Prüfplan, Stichprobe und Messmittel für {item['id']} zusammen.") for item in receipts]
            actions.append(self._action("quality-review-102", "high", "FLOWWORK", "EMV-Prüfplan freigeben", "Ticket #102 und REQ-SCU-003 befinden sich im Review.", "/work?view=reviews", "Zeige offene Entscheidungen zu REQ-SCU-003 und den zugehörigen Prüfplan."))
            return actions, [self._kpi("Offene Prüfungen", str(len(receipts)), "Wareneingänge", "warning"), self._kpi("Messmittel", str(len(state['quality']['instruments'])), "im Prüfmittelstamm", "good"), self._kpi("Review", "1", "EMV-Nachweis", "warning")], "Drei Wareneingänge warten auf Stichprobenprüfung. Prüfplan, Messmittel und Reviewnachweis sind direkt verknüpft."

        if role == "planning":
            late = [item for item in state["purchase_orders"] if item["status"] == "late"]
            order = state["order"]
            actions = [self._action("planning-order", "high", "FLOWERP", f"{order['work_order']} terminlich prüfen", f"Fortschritt {order['progress']} % · Liefertermin {order['delivery_date']} · Risiko {order['delivery_risk']}", "http://localhost:8081", f"Bewerte Material, Kapazität und Lieferrisiko für {order['work_order']}.")]
            actions.extend(self._action(f"planning-{item['id']}", "critical", "FLOWERP", f"Fehlteilrisiko {item['item']}", f"{item['id']} verspätet sich um {item['delay_days']} Tage.", "http://localhost:8081", f"Welche Auswirkungen hat {item['id']} auf den Produktionsplan?") for item in late)
            return actions, [self._kpi("Auftragsfortschritt", f"{order['progress']} %", order['work_order'], "normal"), self._kpi("Fehlteilrisiken", str(len(late)), "offene Bestellungen", "critical" if late else "good"), self._kpi("Kapazitätsgruppen", str(len(state['capacity'])), "Arbeitsplätze", "normal")], "Die Disposition sieht Material- und Kapazitätsrisiken gemeinsam mit dem aktuellen Fertigungsfortschritt."

        if role == "warehouse":
            receipts = [item for item in state["quality"]["receipts"] if item["status"] == "awaiting_inspection"]
            actions = [self._action(f"warehouse-{item['id']}", "high", "FLOWQ", f"Wareneingang {item['id']} übergeben", f"{item['item_name']} · Charge {item['batch']} · Ziel nach Freigabe {item['accepted_warehouse']}", f"/quality?receipt={item['id']}", f"Welche Lager- und Seriennummernaktionen sind für {item['id']} erforderlich?") for item in receipts]
            return actions, [self._kpi("Wareneingänge", str(len(receipts)), "in QS-Prüfung", "warning"), self._kpi("Lagerbereiche", str(len(state['warehouses'])), "inklusive Sperrlager", "good"), self._kpi("Seriennummern", str(len(state['serials'])), "im Demofall", "normal")], "FLOWPORTAL zeigt Wareneingang, Prüfstatus und vorgesehenes Ziellager in einer Arbeitsliste."

        if role == "sales":
            orders = state["finance"]["orders"]
            risk = [item for item in orders if item["risk"] == "at_risk"]
            actions = [self._action(f"sales-{item['id']}", "high" if item["risk"] == "at_risk" else "normal", "FLOWERP", f"{item['customer']} · {item['product']}", f"{item['stage']} · {item['progress']} % · erwartete Rechnung {item['expected_invoice_date']}", "http://localhost:8081", f"Erstelle mir eine Kundenzusammenfassung zu {item['id']} mit Termin- und Margenrisiko.") for item in orders[:3]]
            pipeline = sum(item["order_value"] * item["probability"] / 100 for item in orders)
            return actions, [self._kpi("Gewichteter Wert", f"{pipeline:,.0f} €".replace(",", "."), "aktive Aufträge", "good"), self._kpi("Terminrisiken", str(len(risk)), "Kundenaufträge", "warning" if risk else "good"), self._kpi("Aktive Kunden", str(len({item['customer'] for item in orders})), "im Forecast", "normal")], "Vertrieb sieht Kundenstatus, erwartete Rechnung und Lieferrisiko. FLOWAI erstellt daraus ein quellenbasiertes Gesprächsbriefing."

        if role == "hr":
            pending = [item for item in state["hr"]["requests"] if item["status"] == "pending"]
            applications = state["hr"]["recruiting"]["applications"]
            actions = [self._action(f"hr-{item['id']}", "high", "FLOWHR", f"{item['type']} entscheiden", f"{item['id']} · {item['reason']}", "/hr?tab=requests", f"Fasse Antrag {item['id']} und mögliche Teamkonflikte zusammen.") for item in pending]
            actions.append(self._action("hr-recruiting", "normal", "FLOWHR", "Bewerbungen sichten", f"{len(applications)} Bewerbungen im Recruiting-Workflow", "/hr?tab=recruiting", "Fasse offene Bewerbungen ohne unnötige personenbezogene Daten zusammen."))
            return actions, [self._kpi("Offene Anträge", str(len(pending)), "Entscheidung erforderlich", "warning"), self._kpi("Bewerbungen", str(len(applications)), "aktive Vorgänge", "normal"), self._kpi("Payroll", "1", "Demoperiode", "normal")], "Anträge, Recruiting und Payroll erscheinen getrennt nach Berechtigung. Die KI minimiert personenbezogene Daten in Zusammenfassungen."

        if role == "finance":
            overdue = [item for item in state["finance"]["open_items"] if item["status"] == "overdue"]
            over_budget = [item for item in state["finance"]["budgets"] if item["forecast"] > item["budget"]]
            actions = [self._action(f"finance-{item['id']}", "critical", "FLOWFIN", f"Überfälligen Posten {item['document']} klären", f"{item['partner']} · {item['amount']:,.0f} €".replace(",", "."), "/finance", f"Fasse den offenen Posten {item['id']} und den Projektbezug zusammen.") for item in overdue]
            actions.extend(self._action(f"budget-{item['id']}", "high", "FLOWFIN", f"Forecast {item['name']} prüfen", f"Prognose liegt {item['forecast'] - item['budget']:,.0f} € über Budget".replace(",", "."), "/finance", f"Erkläre die Budgetabweichung von {item['id']} und nenne die größten Treiber.") for item in over_budget)
            return actions, [self._kpi("Überfällige Posten", str(len(overdue)), "Debitoren", "critical" if overdue else "good"), self._kpi("Budgetrisiken", str(len(over_budget)), "Forecast über Budget", "warning"), self._kpi("Cash Monatsende", "303.000 €", "November 2026", "good")], "FLOWFIN priorisiert überfällige Posten und Forecastabweichungen. Externe Buchungs- oder DATEV-Schritte bleiben bestätigungspflichtig."

        if role == "it":
            actions = [self._action("it-mcp", "high", "FLOWOPS", "MCP-Zugriffe härten", "Benutzeridentität und Rollen bis zu jedem Fachwerkzeug durchreichen.", "/docs#/", "Welche MCP-Tools sind aktiv und wo fehlen noch OAuth und Rollenprüfung?"), self._action("it-readiness", "normal", "FLOWOPS", "Betriebsbereitschaft prüfen", "Container, Integrationen, Backups und Monitoring kontrollieren.", "/ready", "Fasse den aktuellen Betriebsstatus und offene Live-Gaps zusammen.")]
            return actions, [self._kpi("MCP-Server", "3", "Plattform, DMS, Wiki", "good"), self._kpi("Fachanwendungen", "10", "über Portal erreichbar", "good"), self._kpi("Live-Gaps", "4", "OAuth, TLS, Backup, HA", "warning")], "Die Plattform besitzt drei zentrale MCP-Endpunkte. Vor dem Livebetrieb müssen Benutzeridentität, Least Privilege und bestätigte Schreibaktionen durchgängig erzwungen werden."

        return [], [self._kpi("Offene Aktionen", "0", "für das gewählte Profil", "good")], "Für dieses Profil liegen heute keine priorisierten Fachaktionen vor."

    def _common_actions(
        self, state: dict[str, Any], user: dict[str, Any], work_date: str
    ) -> list[dict[str, Any]]:
        booking = next(
            (
                item
                for item in state["desksharing"]["bookings"]
                if item["user_id"] == user["id"]
                and item["date"] == work_date
                and item["status"] in {"booked", "checked_in"}
            ),
            None,
        )
        if booking:
            desk = next(item for item in state["desksharing"]["desks"] if item["id"] == booking["desk_id"])
            room = next(item for item in state["desksharing"]["rooms"] if item["id"] == desk["room_id"])
            detail = f"{room['name']} · {desk['label']} · {booking['slot']}"
            title = "Gebuchten Arbeitsplatz prüfen"
        else:
            detail = "Für heute ist noch kein Arbeitsplatz reserviert."
            title = "Arbeitsplatz wählen"
        return [self._action("common-desk", "normal", "FLOWSPACE", title, detail, f"/desksharing?date={work_date}&site={user['site_id']}", "Wo ist mein Arbeitsplatz heute und welche Kollegen sitzen im selben Raum?")]

    @staticmethod
    def _action(
        action_id: str,
        priority: str,
        source: str,
        title: str,
        detail: str,
        href: str,
        prompt: str,
    ) -> dict[str, Any]:
        return {"id": action_id, "priority": priority, "source": source, "title": title, "detail": detail, "href": href, "ai_prompt": prompt}

    @staticmethod
    def _kpi(label: str, value: str, detail: str, tone: str) -> dict[str, str]:
        return {"label": label, "value": value, "detail": detail, "tone": tone}

    @staticmethod
    def _tool(name: str, label: str, server: str, mode: str, status: str = "available") -> dict[str, str]:
        return {"name": name, "label": label, "server": server, "mode": mode, "status": status}

    def _agents(self, role: str) -> list[dict[str, str]]:
        shared = [
            {"id": "briefing", "name": "Daily-Briefing-Agent", "scope": "führt freigegebene Tagesinformationen zusammen", "status": "available"},
            {"id": "documents", "name": "Dokumenten-Agent", "scope": "findet freigegebene Unterlagen und verlinkt die Quelle", "status": "available"},
        ]
        role_agents = {
            "procurement": [("supplier", "Lieferanten-Agent", "erkennt Terminrisiken und entwirft Rückfragen")],
            "engineering": [("requirements", "Requirements-Agent", "fasst Requirements, Beziehungen und Reviews zusammen")],
            "production": [("shopfloor", "Shopfloor-Agent", "erklärt den nächsten Arbeitsgang und die Anleitung")],
            "quality": [("inspection", "Prüf-Agent", "bereitet Prüfplan, Stichprobe und Messmittelkontext auf")],
            "planning": [("planning", "Planungs-Agent", "verbindet Material, Kapazität und Liefertermin")],
            "warehouse": [("warehouse", "Lager-Agent", "ordnet Wareneingang, Seriennummer und Lagerziel zu")],
            "sales": [("customer", "Kunden-Agent", "erstellt Auftrags- und Gesprächsbriefings")],
            "hr": [("people", "People-Agent", "fasst Anträge datensparsam zusammen")],
            "finance": [("controlling", "Controlling-Agent", "erklärt Cash, Posten und Forecastabweichungen")],
            "it": [("operations", "Operations-Agent", "bewertet Integrationen und Betriebsbereitschaft")],
        }
        return shared + [
            {"id": item[0], "name": item[1], "scope": item[2], "status": "available"}
            for item in role_agents.get(role, [])
        ]

    def _prompts(self, role: str, actions: list[dict[str, Any]]) -> list[str]:
        prompts = [item["ai_prompt"] for item in actions[:2]]
        prompts.append(
            {
                "procurement": "Erstelle mein Einkaufsbriefing für heute und priorisiere Lieferantenrückfragen.",
                "engineering": "Erstelle mein Engineering-Briefing mit Tasks, Requirements und offenen Reviews.",
                "production": "Welche Arbeit kann ich als Nächstes ausführen und welche Unterlagen brauche ich?",
                "quality": "Welche Prüfungen sind heute fällig und welche Entscheidungen fehlen?",
                "planning": "Welche Material- oder Kapazitätsrisiken gefährden den Liefertermin?",
                "warehouse": "Welche Wareneingänge, Seriennummern und Lagerbewegungen sind heute offen?",
                "sales": "Welche Kunden sollte ich heute kontaktieren und warum?",
                "hr": "Welche HR-Vorgänge benötigen heute eine Entscheidung?",
                "finance": "Welche finanziellen Risiken und Abweichungen benötigen heute Aufmerksamkeit?",
                "it": "Welche Plattform- und Integrationsrisiken sind heute offen?",
            }.get(role, "Fasse meine wichtigsten Aufgaben für heute zusammen.")
        )
        return prompts

    @staticmethod
    def _schedule(role: str) -> list[dict[str, str]]:
        focus = {
            "procurement": "Lieferantenstatus und Fehlteile",
            "engineering": "Requirement- und Review-Fokus",
            "production": "Schicht- und Arbeitsgangsübergabe",
            "quality": "Wareneingangs- und Prüfplanung",
            "planning": "Material- und Kapazitätsabgleich",
            "warehouse": "Wareneingang und Lagerübergabe",
            "sales": "Kunden- und Auftragsstatus",
            "hr": "Anträge und Teamkalender",
            "finance": "Cash und Forecast",
            "it": "Betriebsstatus und Integrationen",
        }.get(role, "Tagesplanung")
        return [
            {"time": "08:00", "title": "KI-Tagesbriefing", "detail": "Prioritäten und Risiken aus freigegebenen Quellen"},
            {"time": "09:00", "title": focus, "detail": "persönlicher Fachfokus"},
            {"time": "15:30", "title": "Offene Punkte aktualisieren", "detail": "Status und nächste Schritte dokumentieren"},
        ]

    def _role(self, user: dict[str, Any]) -> str:
        roles = set(user.get("roles", []))
        return next((key for role, key in self.ROLE_PRIORITY if role in roles), "general")

    def _user(self, state: dict[str, Any], user_id: str) -> dict[str, Any]:
        user = next(
            (
                item
                for item in state["iam"]["users"]
                if user_id in {item["id"], item["username"]}
            ),
            None,
        )
        if user is None:
            raise WorkplaceNotFoundError("Benutzerprofil wurde nicht gefunden")
        return deepcopy(user)

    @staticmethod
    def _date(value: str) -> str:
        try:
            return date.fromisoformat(value).isoformat() if value else date.today().isoformat()
        except ValueError as exc:
            raise WorkplaceNotFoundError("Datum muss im Format YYYY-MM-DD vorliegen") from exc

    @staticmethod
    def _headline(user: dict[str, Any], role: str, actions: list[dict[str, Any]]) -> str:
        critical = sum(item["priority"] == "critical" for item in actions)
        suffix = f"{critical} kritischer Punkt" if critical == 1 else f"{critical} kritische Punkte"
        return f"Guten Morgen, {user['name'].split()[0]}. {len(actions)} Fokusaktionen, {suffix}."
