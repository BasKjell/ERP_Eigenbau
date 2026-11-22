/* FLOWAGENTS · Agentenzentrale
 * Zeigt live, welche Agenten arbeiten, wie sie Arbeit übergeben, zurückgeben und Menschen
 * einbeziehen. Datenquelle: /api/agents/overview (Plattform-API -> Orchestrator).
 * Eine Instanz je Element mit [data-agent-center]; data-mode="compact" (Portal) oder "full" (/agents).
 */
(function () {
  "use strict";

  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const SVG = "http://www.w3.org/2000/svg";
  const POLL_MS = 3000;
  const POS = {
    geschaeftsfuehrung: [540, 56],
    anforderungen: [110, 160], anforderungspruefung: [265, 160], G1: [415, 160], architektur: [565, 160], sicherheit: [720, 160], G2: [870, 160],
    planung: [870, 280], akzeptanztest: [720, 280], entwicklung: [565, 280], integration: [415, 280], codepruefung: [265, 280], G3: [110, 280],
    dokumentation: [110, 400], nachweise: [265, 400], G4: [565, 400], G5: [720, 400], schwachstellen: [870, 400],
    flowwork: [1015, 280],
    "mensch:product-owner": [150, 498], "mensch:tech-lead": [330, 498], "mensch:key-user": [510, 498],
    "mensch:release": [690, 498], "mensch:geschaeftsfuehrung": [870, 498],
  };
  const SHORT = {
    geschaeftsfuehrung: "Geschäftsführung", anforderungen: "Anforderungen", anforderungspruefung: "Anf.-Prüfung",
    architektur: "Architektur", sicherheit: "Sicherheit", planung: "Planung", entwicklung: "Entwicklung",
    akzeptanztest: "Akzeptanztest", codepruefung: "Codeprüfung", dokumentation: "Dokumentation", nachweise: "Nachweise",
    schwachstellen: "Schwachstellen", integration: "Integration", flowwork: "FLOWWORK",
  };
  const HUMAN_CODES = { "product-owner": "PO", "tech-lead": "TL", "key-user": "KU", release: "RL", geschaeftsfuehrung: "GF" };
  const STATE_LABEL = { arbeitet: "arbeitet", als_naechstes: "als Nächstes", wartet: "wartet auf Mensch", bereit: "bereit", pausiert: "pausiert", inaktiv: "nicht freigegeben", unbekannt: "—" };
  const KIND_LABEL = { uebergabe: "übergibt", ruecklauf: "gibt zurück", entscheidung_offen: "fragt", entscheidung: "entscheidet", werkzeug: "schreibt", start: "beginnt", ergebnis: "liefert", gate: "Gate", baseline: "fixiert", auftrag: "beauftragt", vertrag: "Vertrag", pausiert: "pausiert", abschluss: "Abschluss", abbruch: "Abbruch", steuerung: "Steuerung", wiederanlauf: "Wiederanlauf" };

  const previewUrl = (d) => {
    const url = d?.context?.preview_url || "";
    return /^http:\/\/localhost:\d+(\/[a-z]*)?$/.test(url) ? url : "";
  };
  const changeUrl = (d) => `/agents?run=${encodeURIComponent(d.run_id)}&focus=${encodeURIComponent((d.focus || []).join(","))}`;
  window.FlowAgents = { previewUrl, changeUrl, esc };

  const KIND_LABEL_DE = {
    ui_pruefung: "Klickprüfung im Browser",
    auftrag: "Fachauftrag", geschaeftsbewertung: "Bewertung Geschäftsführung", anforderungen: "Anforderungen",
    anforderungsbefund: "Prüfbefund Anforderungen", baseline: "Arbeitsbaseline", architektur: "Architektur",
    sicherheitsbefund: "Sicherheitsbefund", plan: "Arbeitspakete", akzeptanztests: "Akzeptanztests",
    implementierung: "Code-Änderung", integration: "Integrationsprüfung", codebefund: "Codeprüfung",
    dokumentation: "Dokumentation", nachweise: "Nachweise", prozessbewertung: "Prozessbewertung Geschäftsführung",
    uebernahme: "Übernahme als Branch",
  };

  function artifactText(artifact) {
    const c = artifact.content || {};
    const lines = [];
    for (const item of c.items || []) {
      lines.push(`${item.key || ""} · ${item.title || ""}${item.priority ? ` [${item.priority}]` : ""}`);
      for (const field of ["text", "decision", "benefit", "staff_effort", "process_fit", "recommendation", "criterion", "negative_case", "state", "evidence"]) {
        if (item[field]) lines.push(`  ${field}: ${item[field]}`);
      }
      for (const ac of item.acceptance_criteria || []) lines.push(`  ${ac}`);
      for (const listField of ["components", "data_flows", "risks", "covers"]) for (const v of item[listField] || []) lines.push(`  ${listField}: ${v}`);
      for (const t of item.threats || []) lines.push(`  Bedrohung: ${t.threat} → ${t.control}`);
      for (const st of item.steps || []) lines.push(`  Schritt: ${st.action} → ${st.expected}`);
      if (item.content) item.content.split("\n").forEach((l) => lines.push(`  ${l}`));
    }
    for (const f of c.findings || []) lines.push(`Befund [${f.severity}] ${f.location}: ${f.impact}`);
    if (!lines.length) JSON.stringify(c, null, 1).split("\n").forEach((l) => lines.push(l));
    return lines;
  }

  function lineDiff(before, after) {
    const a = before.slice(0, 400), b = after.slice(0, 400);
    const dp = Array.from({ length: a.length + 1 }, () => new Array(b.length + 1).fill(0));
    for (let i = a.length - 1; i >= 0; i -= 1) for (let j = b.length - 1; j >= 0; j -= 1) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
    const out = [];
    let i = 0, j = 0;
    while (i < a.length || j < b.length) {
      if (i < a.length && j < b.length && a[i] === b[j]) { out.push(["same", a[i]]); i += 1; j += 1; }
      else if (j < b.length && (i >= a.length || dp[i][j + 1] >= dp[i + 1][j])) { out.push(["add", b[j]]); j += 1; }
      else { out.push(["del", a[i]]); i += 1; }
    }
    return out.map(([kind, line]) => `<div class="dl ${kind}">${kind === "add" ? "+" : kind === "del" ? "−" : "\u00a0"} ${esc(line)}</div>`).join("");
  }

  function uiCheckLine(check) {
    if (!check) return "";
    if (check.status === "laeuft") return `<small>Klickprüfung läuft: ${esc(check.total)} Testfälle im Prüfbrowser …</small>`;
    if (check.status === "fehler") return `<small>Klickprüfung nicht möglich: ${esc(check.error)}</small>`;
    const ok = check.passed === check.total;
    return `<small><span class="ac-chip ${ok ? "lime" : "red"}">Klickprüfung ${esc(check.passed)}/${esc(check.total)}</span>${ok ? "" : ` fehlgeschlagen: ${esc((check.failed || []).join(", "))}`} – Bildschirmfotos unter „Änderung ansehen“</small>`;
  }

  function renderFocus(detail, focus) {
    if (!focus.length) return "";
    const byKind = new Map();
    for (const artifact of detail.artifacts) {
      if (!byKind.has(artifact.kind)) byKind.set(artifact.kind, []);
      byKind.get(artifact.kind).push(artifact);
    }
    const blocks = focus.map((kind) => {
      const versions = (byKind.get(kind) || []).sort((x, y) => x.version - y.version);
      if (!versions.length) return `<div class="focus-block"><h5>${esc(KIND_LABEL_DE[kind] || kind)}</h5><p class="muted">Noch kein Ergebnis.</p></div>`;
      const latest = versions.at(-1);
      const previous = versions.length > 1 ? versions.at(-2) : null;
      const change = previous && kind !== "implementierung"
        ? `<details open class="change"><summary>Änderung v${esc(previous.version)} → v${esc(latest.version)}</summary><div class="linediff">${lineDiff(artifactText(previous), artifactText(latest))}</div></details>`
        : "";
      return `<div class="focus-block"><h5>${esc(KIND_LABEL_DE[kind] || kind)} <small>v${esc(latest.version)} · ${esc(latest.digest.slice(0, 19))}</small></h5>${change}<details ${change ? "" : "open"} class="artifact"><summary>Aktueller Stand</summary>${renderArtifact(latest)}</details></div>`;
    }).join("");
    return `<section class="focus" data-focus><h4>Zur Entscheidung ansehen</h4>${blocks}</section>`;
  }

  function nodeLabel(id, data) {
    if (id.startsWith("mensch:")) return data.human_roles?.[id.slice(7)]?.label || id.slice(7);
    if (/^G[1-5]$/.test(id)) return (data.pipeline || []).find((s) => s.id === id)?.label || id;
    return SHORT[id] || id;
  }

  function routeText(event, data) {
    const from = nodeLabel(event.actor, data);
    const to = event.target && event.target !== event.actor ? ` → ${nodeLabel(event.target, data)}` : "";
    return `${from}${to}`;
  }

  function time(value) {
    if (!value) return "";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  function curve(a, b, bend) {
    const [x1, y1] = a, [x2, y2] = b;
    const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
    const dx = x2 - x1, dy = y2 - y1, length = Math.hypot(dx, dy) || 1;
    const cx = mx - (dy / length) * bend, cy = my + (dx / length) * bend;
    return `M${x1},${y1} Q${cx},${cy} ${x2},${y2}`;
  }

  // Projektkürzel: FLOWWORK erwartet z. B. FLOW-DMS. Eingaben wie „flow doc“ werden zu FLOW-DOC.
const PROJECTS = ["FLOW-DMS", "FLOW-PLATFORM", "FLOW-PORTAL", "FLOW-AGENTS", "FLOW-ERP", "FLOW-HR", "FLOW-FIN",
  "FLOW-MES", "FLOW-QM", "FLOW-WORK", "FLOW-SPACE", "FLOW-DOCS"];
const SCOPE_PROJECTS = { dms: "FLOW-DMS", portal: "FLOW-PORTAL", erp: "FLOW-ERP", hr: "FLOW-HR", finance: "FLOW-FIN",
  mes: "FLOW-MES", flowq: "FLOW-QM", work: "FLOW-WORK", desksharing: "FLOW-SPACE", doku: "FLOW-DOCS",
  plattform: "FLOW-PLATFORM", agenten: "FLOW-AGENTS", prozess: "FLOW-PROZESSE" };
const FIELD_LABELS = { title: "Titel", goal: "Zweck", user_group: "Nutzergruppe", behavior: "Gewünschtes Verhalten",
  success_example: "Erfolgsbeispiel", exclusions: "Ausgeschlossen", project: "Projekt", scope: "Änderungsbereich",
  change_class: "Änderungsklasse", data_class: "Datenklasse", execution: "Umsetzung" };

function normalizeProject(value) {
  const key = String(value || "").trim().toUpperCase().replace(/[ÄÖÜ]/g, (c) => ({ Ä: "AE", Ö: "OE", Ü: "UE" })[c])
    .replace(/ß/g, "SS").replace(/[\s_./]+/g, "-").replace(/[^A-Z0-9-]/g, "").replace(/-+/g, "-").replace(/^[^A-Z]+|-+$/g, "");
  return key.length >= 3 ? key.slice(0, 31) : (key ? `FLOW-${key}` : "FLOW-PLATFORM");
}

function projectForScope(scope) {
  return SCOPE_PROJECTS[String(scope || "").split("-")[0]] || "FLOW-PLATFORM";
}

function fieldError(detail) {
  const field = Array.isArray(detail.loc) ? detail.loc[detail.loc.length - 1] : "";
  const label = FIELD_LABELS[field] || field || "Eingabe";
  if (field === "project") return "Projekt: Kürzel wie FLOW-DMS verwenden (Großbuchstaben, Ziffern, Bindestrich)";
  if (detail.type === "string_too_short") return `${label}: zu kurz (mindestens ${detail.ctx?.min_length} Zeichen)`;
  if (detail.type === "string_too_long") return `${label}: zu lang (höchstens ${detail.ctx?.max_length} Zeichen)`;
  return `${label}: ${detail.msg}`;
}

class AgentCenter {
    constructor(root) {
      this.root = root;
      this.full = root.dataset.mode === "full";
      this.data = null;
      this.lastEvent = 0;
      this.selected = null;
      this.timer = null;
      this.render();
      this.poll();
      document.addEventListener("visibilitychange", () => { if (!document.hidden) this.poll(); });
    }

    render() {
      this.root.classList.add("ac");
      this.root.innerHTML = `
        <div class="ac-head">
          <div>
            <div class="ac-eyebrow"><span class="ac-live" data-live></span><span data-live-text>AGENTENZENTRALE · VERBINDE …</span></div>
            <h2>Was dein digitales Team gerade tut</h2>
            <p>Jede Rolle arbeitet getrennt: Agenten erstellen und prüfen sich gegenseitig, der Orchestrator erzwingt den Ablauf, und an den Gates entscheiden Menschen. Freigaben erteilt nie ein Agent.</p>
          </div>
          <div class="ac-actions">
            <button class="ac-btn primary" type="button" data-new-run>＋ Fachauftrag starten</button>
            ${this.full ? "" : '<a class="ac-btn" href="/agents">Vollansicht →</a>'}
          </div>
        </div>
        <div class="ac-metrics" data-metrics></div>
        <div class="ac-body">
          <div class="ac-map-card">
            <div class="ac-map-head"><b>Zusammenarbeit live</b>
              <div class="ac-legend"><span><i style="background:#6fd1c0"></i>Übergabe</span><span><i style="background:#ff8a80"></i>Rücklauf</span><span><i style="background:#ffc46b"></i>Frage an Mensch</span><span><i style="background:#c8f04a"></i>Entscheidung</span><span><i style="background:#8aa4ff"></i>FLOWWORK</span></div>
            </div>
            <svg class="ac-map" viewBox="0 0 1080 540" role="img" aria-label="Interaktionen zwischen Agenten, Gates und Menschen" data-map></svg>
            <div class="ac-detail" data-detail><small>Klicke auf einen Agenten, ein Gate oder eine Entscheidungsrolle, um Auftrag, Grenzen und aktuelle Arbeit zu sehen.</small></div>
          </div>
          <aside class="ac-side">
            <section class="ac-panel" id="meine-entscheidungen"><h3>Deine Entscheidungen <span data-inbox-count></span></h3><div class="ac-inbox" data-inbox></div></section>
            <section class="ac-panel"><h3>Live-Protokoll <span>NEUESTE ZUERST</span></h3><div class="ac-feed" data-feed></div></section>
          </aside>
        </div>
        <div class="ac-runs" data-runs></div>
        <div data-offline></div>
        ${this.full ? '<div data-full-extra></div>' : ""}
        ${this.dialogMarkup()}`;
      this.$ = (selector) => this.root.querySelector(selector);
      this.$("[data-new-run]").addEventListener("click", () => this.openRunDialog());
      this.bindDialog();
    }

    async poll() {
      clearTimeout(this.timer);
      try {
        const response = await fetch("/api/agents/overview", { headers: { Accept: "application/json" } });
        if (response.status === 401) throw new Error("Anmeldung über FLOWID erforderlich");
        if (!response.ok) throw new Error(`Agentenzentrale nicht verfügbar (${response.status})`);
        this.update(await response.json());
      } catch (error) {
        this.$("[data-live]").classList.add("off");
        this.$("[data-live-text]").textContent = "AGENTENZENTRALE · NICHT VERBUNDEN";
        this.$("[data-offline]").innerHTML = `<div class="ac-offline">${esc(error.message)}</div>`;
      }
      if (!document.hidden) this.timer = setTimeout(() => this.poll(), POLL_MS);
    }

    update(data) {
      const previous = this.lastEvent;
      this.data = data;
      const online = data.available !== false;
      this.$("[data-live]").classList.toggle("off", !online || data.control === "pausiert");
      const providers = Object.values(data.providers || {});
      const mode = providers.length && providers.every((p) => p === "simulated") ? "SIMULATION" : providers.includes("gateway") ? "LOKALE MODELLE ÜBER FLOWGATE" : "";
      this.$("[data-live-text]").textContent = online
        ? `AGENTENZENTRALE · ${data.control === "pausiert" ? "PAUSIERT" : "LIVE"}${mode ? ` · ${mode}` : ""}`
        : "AGENTENZENTRALE · ORCHESTRATOR OFFLINE";
      this.$("[data-offline]").innerHTML = online ? "" : `<div class="ac-offline">${esc(data.reason || "Orchestrator nicht erreichbar")}. Angezeigt wird nur das Agentenregister. Start: <code>make agents-up</code></div>`;
      this.renderMetrics(data);
      this.renderMap(data, previous);
      this.renderInbox(data);
      this.renderFeed(data, previous);
      this.renderRuns(data);
      if (this.selected) this.showDetail(this.selected);
      if (this.full) this.renderFull(data);
      const newest = Math.max(0, ...(data.events || []).map((e) => e.id));
      this.lastEvent = Math.max(this.lastEvent, newest);
    }

    myDecisions(data) {
      const roles = new Set(data.viewer?.roles || []);
      return (data.decisions || []).map((decision) => {
        const allowed = data.human_roles?.[decision.decider]?.keycloak_roles || [];
        const can = allowed.some((r) => roles.has(r)) || (data.demo_mode && roles.has("platform-admin"));
        return { ...decision, can };
      });
    }

    renderMetrics(data) {
      const m = data.metrics || {};
      const mine = this.myDecisions(data).filter((d) => d.can).length;
      const items = [
        ["Agenten im Register", (data.agents || []).length, ""],
        ["Arbeiten gerade", m.agents_working ?? 0, m.agents_working ? "attention" : ""],
        ["Offene Aufträge", m.runs_open ?? 0, ""],
        ["Warten auf dich", mine, mine ? "attention" : ""],
        ["Rückläufe (Prüfung)", m.reworks ?? 0, ""],
      ];
      this.$("[data-metrics]").innerHTML = items.map(([label, value, tone]) => `<div class="ac-metric ${tone}"><small>${esc(label)}</small><b>${esc(value)}</b></div>`).join("");
    }

    nodes(data) {
      const nodes = new Map();
      const runs = (data.runs || []).filter((r) => ["aktiv", "wartet", "blockiert"].includes(r.status));
      for (const agent of data.agents || []) {
        if (!POS[agent.role]) continue;
        nodes.set(agent.role, { id: agent.role, type: "agent", code: agent.role === "geschaeftsfuehrung" ? "GF" : String(agent.number).padStart(2, "0"), state: agent.state || "unbekannt", agent });
      }
      const integrationActive = runs.some((r) => r.step === "integrationspruefung" && r.status === "aktiv");
      nodes.set("integration", { id: "integration", type: "system", code: "CI", state: integrationActive ? "arbeitet" : "bereit" });
      nodes.set("flowwork", { id: "flowwork", type: "system", code: "FW", state: data.rm_connected === false ? "inaktiv" : "bereit" });
      for (const gate of ["G1", "G2", "G3", "G4", "G5"]) {
        const waiting = (data.decisions || []).some((d) => d.gate === gate);
        nodes.set(gate, { id: gate, type: "gate", code: gate, state: waiting ? "wartet" : "bereit" });
      }
      for (const [name, role] of Object.entries(data.human_roles || {})) {
        nodes.set(`mensch:${name}`, { id: `mensch:${name}`, type: "human", code: HUMAN_CODES[name] || name.slice(0, 2).toUpperCase(), state: role.open ? "wartet" : "bereit", open: role.open || 0, role });
      }
      return nodes;
    }

    renderMap(data, previousEvent) {
      const svg = this.$("[data-map]");
      const nodes = this.nodes(data);
      const parts = [];
      parts.push('<text class="lane-label" x="16" y="24">GESCHÄFTSFÜHRUNGS-SICHT</text>');
      parts.push('<text class="lane-label" x="16" y="122">ANFORDERUNG &amp; ARCHITEKTUR</text>');
      parts.push('<text class="lane-label" x="16" y="242">UMSETZUNG &amp; PRÜFUNG</text>');
      parts.push('<text class="lane-label" x="16" y="362">NACHWEIS &amp; ABNAHME</text>');
      parts.push('<line x1="16" x2="1064" y1="452" y2="452" stroke="rgba(255,255,255,.1)"/><text class="lane-label" x="16" y="472">MENSCHEN ENTSCHEIDEN</text>');
      // Ablauf laut workflow.yaml als gestrichelte Grundlinie
      const steps = (data.pipeline || []).map((s) => s.role || (s.kind === "check" ? "integration" : s.id));
      for (let i = 0; i < steps.length - 1; i += 1) {
        const a = POS[steps[i]], b = POS[steps[i + 1]];
        if (a && b) parts.push(`<path class="flow" d="${curve(a, b, steps[i] === "nachweise" || steps[i + 1] === "anforderungen" ? 60 : 0)}"/>`);
      }
      // Tatsächliche Interaktionen aus den Ereignissen
      const now = Date.now();
      for (const edge of data.interactions || []) {
        const a = POS[edge.from], b = POS[edge.to];
        if (!a || !b || edge.from === edge.to) continue;
        const bend = { uebergabe: 14, ruecklauf: -46, entscheidung_offen: 30, entscheidung: -30, werkzeug: 22 }[edge.kind] ?? 0;
        const recent = edge.last_at && now - new Date(edge.last_at).getTime() < 90_000;
        const width = Math.min(6, 1.4 + Math.log2(1 + edge.count));
        parts.push(`<path class="edge ${esc(edge.kind)}" d="${curve(a, b, bend)}" stroke-width="${width.toFixed(1)}" style="opacity:${recent ? 1 : 0.45}"><title>${esc(nodeLabel(edge.from, data))} → ${esc(nodeLabel(edge.to, data))}: ${esc(KIND_LABEL[edge.kind] || edge.kind)} (${edge.count}×)</title></path>`);
      }
      for (const node of nodes.values()) {
        const [x, y] = POS[node.id] || [0, 0];
        const label = nodeLabel(node.id, data);
        const selected = this.selected === node.id ? " selected" : "";
        if (node.type === "gate") {
          parts.push(`<g class="node gate ${esc(node.state)}${selected}" data-node="${esc(node.id)}" tabindex="0"><rect x="${x - 17}" y="${y - 17}" width="34" height="34" rx="5" transform="rotate(45 ${x} ${y})"/><text class="code" x="${x}" y="${y}">${esc(node.code)}</text><text class="label" x="${x}" y="${y + 38}">${esc(label)}</text></g>`);
          continue;
        }
        const r = node.type === "human" ? 19 : 24;
        const sub = node.type === "agent" ? STATE_LABEL[node.state] || node.state : node.type === "human" ? (node.open ? `${node.open} offen` : "") : node.state === "arbeitet" ? "prüft" : "";
        parts.push(`<g class="node ${node.type} ${esc(node.state)}${selected}" data-node="${esc(node.id)}" tabindex="0">${node.state === "arbeitet" ? `<circle class="halo" cx="${x}" cy="${y}" r="${r + 4}"/>` : ""}<circle class="ring" cx="${x}" cy="${y}" r="${r}"/><text class="code" x="${x}" y="${y}">${esc(node.code)}</text><text class="label" x="${x}" y="${y + r + 14}">${esc(label)}</text>${sub ? `<text class="sub" x="${x}" y="${y + r + 25}">${esc(sub)}</text>` : ""}${node.open ? `<g class="badge"><circle cx="${x + 15}" cy="${y - 15}" r="8"/><text x="${x + 15}" y="${y - 15}">${node.open}</text></g>` : ""}</g>`);
      }
      svg.innerHTML = parts.join("");
      svg.querySelectorAll("[data-node]").forEach((element) => {
        const select = () => { this.selected = element.dataset.node; this.renderMap(this.data, Infinity); this.showDetail(this.selected); };
        element.addEventListener("click", select);
        element.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); select(); } });
      });
      // Neue Ereignisse als wandernde Impulse animieren
      if (previousEvent && previousEvent !== Infinity && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        const fresh = (data.events || []).filter((e) => e.id > previousEvent && ["uebergabe", "ruecklauf", "entscheidung_offen", "entscheidung", "werkzeug"].includes(e.kind)).slice(-8);
        fresh.forEach((event, index) => {
          const a = POS[event.actor], b = POS[event.target];
          if (!a || !b) return;
          const bend = { uebergabe: 14, ruecklauf: -46, entscheidung_offen: 30, entscheidung: -30, werkzeug: 22 }[event.kind] ?? 0;
          const dot = document.createElementNS(SVG, "circle");
          dot.setAttribute("r", "6");
          dot.setAttribute("class", `pulse ${event.kind}`);
          const motion = document.createElementNS(SVG, "animateMotion");
          motion.setAttribute("dur", "1.5s");
          motion.setAttribute("begin", `${index * 0.35}s`);
          motion.setAttribute("fill", "freeze");
          motion.setAttribute("path", curve(a, b, bend));
          dot.appendChild(motion);
          svg.appendChild(dot);
          setTimeout(() => dot.remove(), 1700 + index * 350);
        });
      }
    }

    showDetail(id) {
      const data = this.data;
      const panel = this.$("[data-detail]");
      if (!data || !id) return;
      const isAdmin = (data.viewer?.roles || []).some((r) => ["platform-admin", "it-user", "work-admin"].includes(r));
      if (id.startsWith("mensch:")) {
        const name = id.slice(7);
        const role = data.human_roles?.[name] || {};
        const open = (data.decisions || []).filter((d) => d.decider === name);
        panel.innerHTML = `<b>${esc(role.label || name)}</b> <small>· Mensch · FLOWID-Rollen: ${esc((role.keycloak_roles || []).join(", "))}</small><div class="chips">${open.length ? open.map((d) => `<span class="ac-chip amber">${esc(d.title)}</span>`).join("") : '<span class="ac-chip">keine offene Entscheidung</span>'}</div>`;
        return;
      }
      if (/^G[1-5]$/.test(id)) {
        const step = (data.pipeline || []).find((s) => s.id === id) || {};
        const open = (data.decisions || []).filter((d) => d.gate === id);
        panel.innerHTML = `<b>${esc(id)} · ${esc(step.label || "")}</b> <small>· Gate · entscheidet: ${esc(data.human_roles?.[step.decider]?.label || step.decider || "")}</small><div class="ac-hint">Standardänderungen passieren G1–G3 im genehmigten Standardweg (protokolliert). G4 Fachabnahme und G5 Produktion entscheidet immer ein Mensch, gebunden an den Digest des Kandidaten.</div><div class="chips">${open.map((d) => `<span class="ac-chip amber">${esc(d.run_id)} wartet</span>`).join("")}</div>`;
        return;
      }
      if (id === "integration" || id === "flowwork") {
        panel.innerHTML = id === "integration"
          ? "<b>Integrationsprüfung</b> <small>· deterministischer Dienst</small><div class=\"ac-hint\">Führt Lint und Tests am exakten Änderungsstand in einem Container ohne Netzwerk und ohne Zugangsdaten aus. Das Ergebnis gilt nur für diesen Digest.</div>"
          : `<b>FLOWWORK</b> <small>· Anforderungen, Baselines, Tests (Jama-Nachbau)</small><div class="ac-hint">Agenten schreiben nur über den RM-Adapter mit rollengebundenem Kurzzeit-Token. Freigaben gibt es dort nur für Menschen. ${data.rm_connected === false ? "Derzeit nicht verbunden." : ""}</div><div class="chips"><a class="ac-chip lime" href="/work?view=requirements">Anforderungen öffnen ↗</a></div>`;
        return;
      }
      const agent = (data.agents || []).find((a) => a.role === id);
      if (!agent) return;
      const paused = data.agent_controls?.[agent.role] === "pausiert";
      panel.innerHTML = `<b>${esc(agent.name)}</b> <small>· ${esc(agent.id)} · Stufe ${esc(agent.autonomy)} · Owner: ${esc(agent.owner)} · Profil ${esc(agent.model_profile || "")}${agent.family ? ` (${esc(agent.family)})` : ""}</small>
        <div class="ac-hint">${esc(agent.mission || "")}</div>
        <div class="chips"><span class="ac-chip ${agent.state === "arbeitet" ? "lime" : agent.state === "wartet" ? "amber" : agent.state === "pausiert" ? "red" : ""}">${esc(STATE_LABEL[agent.state] || agent.state)}</span>${agent.current ? `<span class="ac-chip">${esc(agent.current.auftrag_id || "")} · ${esc(agent.current.label || "")}</span>` : ""}${(agent.tools || []).map((t) => `<span class="ac-chip">${esc(t)}</span>`).join("")}</div>
        ${agent.last ? `<div class="ac-hint">Zuletzt (${esc(time(agent.last.at))}): ${esc(agent.last.message)}</div>` : ""}
        ${this.full && isAdmin && data.available !== false ? `<div class="chips"><button class="ac-btn small ${paused ? "" : "danger"}" type="button" data-agent-control="${paused ? "resume" : "pause"}" data-role="${esc(agent.role)}">${paused ? "Agent fortsetzen" : "Agent pausieren (Stopp-Schalter)"}</button></div>` : ""}`;
      panel.querySelector("[data-agent-control]")?.addEventListener("click", (event) => this.control(event.currentTarget.dataset.agentControl, event.currentTarget.dataset.role));
    }

    renderInbox(data) {
      const decisions = this.myDecisions(data);
      const mine = decisions.filter((d) => d.can);
      this.$("[data-inbox-count]").textContent = decisions.length ? `${mine.length} VON ${decisions.length}` : "";
      const box = this.$("[data-inbox]");
      const focused = box.contains(document.activeElement) && document.activeElement.tagName === "TEXTAREA";
      if (focused) return; // Eingabe nicht durch die Aktualisierung zerstören
      const signature = JSON.stringify([decisions.map((d) => [d.id, d.can, d.context?.preview_url, d.context?.ui_check?.status]), data.available]);
      if (signature === this.inboxSignature) return;
      this.inboxSignature = signature;
      if (!decisions.length) {
        box.innerHTML = `<div class="ac-empty">${data.available === false ? "Orchestrator nicht verbunden." : "Keine offene Entscheidung. Routine läuft im Hintergrund."}</div>`;
        return;
      }
      box.innerHTML = decisions.slice(0, this.full ? 20 : 4).map((d) => `
        <article class="ac-decision" data-decision="${esc(d.id)}">
          <header><b>${esc(d.title)}</b><span class="ac-chip ${d.can ? "lime" : ""}">${esc(data.human_roles?.[d.decider]?.label || d.decider)}</span></header>
          ${d.auftrag ? `<div class="ac-task-ref"><span class="ac-chip lime">${esc(d.auftrag.id)}</span> <b>${esc(d.auftrag.title)}</b><small>beauftragt von ${esc(d.auftrag.requested_by || "–")} · ${esc(d.auftrag.scope_label || "")}</small>${d.gate === "G4" && d.auftrag.success_example ? `<small>Prüfe: ${esc(d.auftrag.success_example)}</small>` : ""}</div>` : ""}
          <p>${esc(d.question)}</p>
          <p class="ac-links">${previewUrl(d) ? `<a class="ac-btn small primary" href="${esc(previewUrl(d))}" target="_blank" rel="noopener">Ergebnis in der Vorschau ↗</a> ` : ""}<a class="ac-btn small ${previewUrl(d) ? "" : "primary"}" href="${esc(changeUrl(d))}" data-change="${esc(d.run_id)}" data-focus-kinds="${esc((d.focus || []).join(","))}">Änderung ansehen</a>${d.gate === "G1" ? ' <a class="ac-btn small" href="/work?view=baselines" target="_blank" rel="noopener">Baseline in FLOWWORK ↗</a>' : ""}</p>
          ${d.context?.preview_error ? `<small>Vorschau nicht verfügbar: ${esc(d.context.preview_error)}</small>` : ""}
          ${uiCheckLine(d.context?.ui_check)}
          <small>${esc(d.run_id)}${d.digest ? ` · gebunden an ${esc(d.digest.slice(0, 23))}…` : ""}</small>
          ${d.can ? `<textarea placeholder="Begründung (bei Ablehnung Pflicht)" maxlength="2000"></textarea>
          <div class="row"><button class="ac-btn small primary" type="button" data-outcome="annehmen">Annehmen</button><button class="ac-btn small danger" type="button" data-outcome="ablehnen">Ablehnen</button><a class="ac-btn small" href="/agents?run=${encodeURIComponent(d.run_id)}">Details</a></div><div class="error" data-error></div>`
            : '<small>Nicht deine Entscheidungsrolle. Die Befugnis prüft der Orchestrator serverseitig.</small>'}
        </article>`).join("");
      box.querySelectorAll("[data-outcome]").forEach((button) => button.addEventListener("click", () => this.decide(button)));
      if (this.full) {
        box.querySelectorAll("[data-change]").forEach((link) => link.addEventListener("click", (event) => {
          event.preventDefault();
          this.openRun(link.dataset.change, link.dataset.focusKinds.split(",").filter(Boolean));
        }));
      }
    }

    async decide(button) {
      const card = button.closest("[data-decision]");
      const comment = card.querySelector("textarea")?.value || "";
      card.querySelectorAll("button").forEach((b) => { b.disabled = true; });
      try {
        const response = await fetch(`/api/agents/decisions/${encodeURIComponent(card.dataset.decision)}`, {
          method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ outcome: button.dataset.outcome, comment }),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(result.detail || `Entscheidung abgelehnt (${response.status})`);
        card.innerHTML = `<div class="ac-empty">Entscheidung „${esc(button.dataset.outcome)}“ protokolliert.</div>`;
        this.inboxSignature = "";
        setTimeout(() => this.poll(), 400);
      } catch (error) {
        card.querySelectorAll("button").forEach((b) => { b.disabled = false; });
        card.querySelector("[data-error]").textContent = error.message;
      }
    }

    renderFeed(data, previous = 0) {
      const events = [...(data.events || [])].reverse().slice(0, this.full ? 60 : 16);
      const feed = this.$("[data-feed]");
      const newest = events.length ? events[0].id : 0;
      if (newest && newest === this.feedNewest) return; // nichts Neues: Lese- und Scrollposition behalten
      this.feedNewest = newest;
      const scrolled = feed.scrollTop;
      feed.innerHTML = events.length ? events.map((e) => `<div class="ac-event ${esc(e.kind)}${previous && e.id > previous ? " new" : ""}"><time>${esc(time(e.at))}</time><div><span class="route">${esc(routeText(e, data))}</span> · ${esc(e.message)}</div></div>`).join("") : '<div class="ac-empty">Noch keine Aktivität.</div>';
      if (scrolled > 0) feed.scrollTop = scrolled + feed.querySelectorAll(".ac-event.new").length * 30;
    }

    renderRuns(data) {
      const runs = (data.runs || []).slice(0, this.full ? 30 : 4);
      const signature = JSON.stringify(runs.map((r) => [r.id, r.status, r.step, r.model_calls, r.waiting_for, r.branch]));
      if (signature === this.runsSignature) return;
      this.runsSignature = signature;
      this.$("[data-runs]").innerHTML = runs.length ? runs.map((run) => `
        <button class="ac-run" type="button" data-run="${esc(run.id)}">
          <span><span class="key">${esc(run.auftrag_id)}</span><br><small>${esc(run.change_class.replace("_", " "))}</small></span>
          <span><b>${esc(run.title)}</b><small>${esc(run.step_label)}${run.waiting_for ? ` · wartet auf ${esc(data.human_roles?.[run.waiting_for]?.label || run.waiting_for)}` : ""}${run.reason && run.status === "blockiert" ? ` · ${esc(run.reason)}` : ""}${run.branch ? ` · Branch ${esc(run.branch)}` : ""}</small></span>
          <span class="ac-progress-cell"><div class="ac-progress"><i style="width:${Number(run.progress) || 0}%"></i></div><small>${Number(run.progress) || 0} % · ${esc(run.model_calls)} Modellaufrufe</small></span>
          <span class="ac-status ${esc(run.status)}">${esc(run.status)}</span>
        </button>`).join("") : "";
      this.$("[data-runs]").querySelectorAll("[data-run]").forEach((element) => element.addEventListener("click", () => {
        if (this.full) this.openRun(element.dataset.run);
        else window.location.href = `/agents?run=${encodeURIComponent(element.dataset.run)}`;
      }));
    }

    async control(action, role = "", runId = "") {
      const response = await fetch("/api/agents/control", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, role, run_id: runId }) });
      if (!response.ok) {
        const result = await response.json().catch(() => ({}));
        window.alert(result.detail || "Steuerung abgelehnt");
      }
      this.poll();
    }

    // -- Fachauftrag --------------------------------------------------------------------
    dialogMarkup() {
      return `<dialog class="ac-dialog" data-run-dialog><form method="dialog" data-run-form>
        <h3>Fachauftrag an das Agententeam</h3>
        <p class="lead">Beschreibe, welche Arbeit leichter werden soll. Die Agenten leiten daraus Anforderungen in FLOWWORK ab, entwerfen, entwickeln, prüfen und dokumentieren – du entscheidest an den Gates und nimmst am Ende fachlich ab.</p>
        <div class="ac-form">
          <label class="wide">Titel<input name="title" required minlength="5" maxlength="160" placeholder="z. B. Verfahrensanweisungen nach Titel sortieren"></label>
          <label class="wide">Zweck – was soll leichter werden?<textarea name="goal" required minlength="10" maxlength="2000"></textarea></label>
          <label>Nutzergruppe<input name="user_group" required minlength="2" maxlength="160" placeholder="z. B. Einkauf"></label>
          <label>Projekt<input name="project" required list="ac-projects" maxlength="31" value="FLOW-DMS" title="Projektkürzel, z. B. FLOW-DMS – Kleinbuchstaben und Leerzeichen werden automatisch umgewandelt"></label>
          <datalist id="ac-projects">${PROJECTS.map((p) => `<option value="${p}">`).join("")}</datalist>
          <label class="wide">Gewünschtes Verhalten<textarea name="behavior" required minlength="10" maxlength="3000"></textarea></label>
          <label class="wide">Erfolgsbeispiel<input name="success_example" required minlength="5" maxlength="1500" placeholder="z. B. Bei Beta und Alpha erscheint Alpha zuerst"></label>
          <label class="wide">Ausgeschlossen (optional)<input name="exclusions" maxlength="1500" placeholder="z. B. keine Änderung an Rechten"></label>
          <label>Änderungsklasse<select name="change_class"><option value="standard">Standardänderung</option><option value="neue_funktion" selected>Neue Funktion</option><option value="kritisch">Hoher Schutzbedarf / neuer Dienst</option></select></label>
          <label>Datenklasse<select name="data_class"><option value="intern" selected>intern</option><option value="oeffentlich">öffentlich</option><option value="vertraulich">vertraulich</option></select></label>
          <label>Umsetzung<select name="execution"><option value="automatisch" selected>automatisch (komplex → Codex/Claude)</option><option value="lokal">nur lokale Modelle</option><option value="abo">Codex/Claude (Abo)</option></select></label>
          <label class="wide">Freigegebener Änderungsbereich<select name="scope" required data-scopes><option value="">wird geladen …</option></select></label>
          <input type="hidden" name="draft_id" value="">
        </div>
        <div class="ac-form-actions"><span class="msg" data-run-msg>Pflichtfelder laut KI-Entwicklungskonzept Teil 08 „Fachauftrag“.</span><span><button class="ac-btn" value="cancel" formnovalidate type="submit">Abbrechen</button> <button class="ac-btn primary" type="button" data-run-submit>Auftrag einreichen</button></span></div>
      </form></dialog>
      <dialog class="ac-dialog" data-run-detail-dialog><div class="content" data-run-detail></div></dialog>`;
    }

    bindDialog() {
      this.$("[data-run-submit]").addEventListener("click", () => this.submitRun());
    }

    async openRunDialog(draft = null) {
      this.bindProjectField();
      const dialog = this.$("[data-run-dialog]");
      const select = this.$("[data-scopes]");
      const form = this.$("[data-run-form]");
      form.reset();
      form.draft_id.value = draft?.id || "";
      this.$("[data-run-msg]").className = "msg";
      try {
        const response = await fetch("/api/agents/registry", { headers: { Accept: "application/json" } });
        if (!response.ok) throw new Error("Orchestrator nicht erreichbar – Aufträge sind derzeit nicht möglich");
        const registry = await response.json();
        select.innerHTML = Object.entries(registry.scopes || {}).map(([id, scope]) => `<option value="${esc(id)}">${esc(scope.label)}</option>`).join("");
      } catch (error) {
        select.innerHTML = '<option value="">nicht verfügbar</option>';
        this.$("[data-run-msg]").textContent = error.message;
        this.$("[data-run-msg]").className = "msg error";
      }
      if (draft) {
        for (const name of ["title", "goal", "user_group", "behavior", "success_example", "exclusions", "project", "change_class", "data_class", "execution"]) {
          if (draft[name] && form.elements[name]) form.elements[name].value = draft[name];
        }
        if (draft.scope && [...select.options].some((o) => o.value === draft.scope)) select.value = draft.scope;
        this.$("[data-run-msg]").textContent = `Vorschlag ${draft.id} aus FLOWAI${draft.note ? `: ${draft.note}` : ""}. Bitte prüfen, ergänzen und einreichen.`;
      }
      dialog.showModal();
    }

    bindProjectField() {
      const form = this.$("[data-run-form]");
      if (form.dataset.projectBound) return;
      form.dataset.projectBound = "1";
      const field = form.elements.project;
      field.addEventListener("input", () => { field.dataset.touched = "1"; });
      field.addEventListener("blur", () => { field.value = normalizeProject(field.value); });
      this.$("[data-scopes]").addEventListener("change", (event) => {
        if (!field.dataset.touched) field.value = projectForScope(event.target.value);
      });
    }

    async submitRun() {
      const form = this.$("[data-run-form]");
      const message = this.$("[data-run-msg]");
      form.elements.project.value = normalizeProject(form.elements.project.value);
      if (!form.reportValidity()) return;
      const values = Object.fromEntries(new FormData(form).entries());
      values.idempotency_key = `portal-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
      message.textContent = "Wird eingereicht …";
      message.className = "msg";
      try {
        const response = await fetch("/api/agents/runs", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(values) });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(Array.isArray(result.detail) ? result.detail.map(fieldError).join("; ") : result.detail || `Abgelehnt (${response.status})`);
        message.textContent = `Auftrag ${result.auftrag_id} angelegt (${result.id}). Der Geschäftsführungs-Agent bewertet ihn zuerst.`;
        form.reset();
        setTimeout(() => { this.$("[data-run-dialog]").close(); this.poll(); }, 1400);
      } catch (error) {
        message.textContent = error.message;
        message.className = "msg error";
      }
    }

    // -- Vollansicht ----------------------------------------------------------------------
    renderFull(data) {
      const extra = this.$("[data-full-extra]");
      if (!extra) return;
      const isAdmin = (data.viewer?.roles || []).some((r) => ["platform-admin", "it-user", "work-admin"].includes(r));
      extra.innerHTML = `
        <section class="ac-panel" style="margin-top:14px"><h3>Agentenregister <span>${esc(data.registry?.id || "")} · ${esc(data.registry?.policy_version || "")}</span></h3>
          <div class="agent-grid">${(data.agents || []).map((a) => `<article class="agent-card ${esc(a.state)}" data-card="${esc(a.role)}"><header><span class="code">${a.role === "geschaeftsfuehrung" ? "GF" : String(a.number).padStart(2, "0")}</span><div><b>${esc(a.name)}</b><small>${esc(a.id)} · ${esc(a.owner)}</small></div><span class="ac-chip ${a.state === "arbeitet" ? "lime" : a.state === "wartet" ? "amber" : ""}">${esc(STATE_LABEL[a.state] || a.state)}</span></header><p>${esc(a.mission || a.scope || "")}</p><div class="chips"><span class="ac-chip">Stufe ${esc(a.autonomy)}</span><span class="ac-chip">${esc(a.model_profile || "")} ${a.family ? `/ ${esc(a.family)}` : ""}</span><span class="ac-chip">${esc(a.status)}</span></div></article>`).join("")}</div>
          ${(data.productive_agents || []).length ? `<h3 style="margin-top:14px">Produktive Fachagenten <span>STARTBESTAND KI-U-02</span></h3><div class="agent-grid">${data.productive_agents.map((a) => `<article class="agent-card"><header><span class="code">${esc(a.autonomy)}</span><div><b>${esc(a.name)}</b><small>${esc(a.id)} · ${esc(a.owner)}</small></div><span class="ac-chip">${esc(a.status)}</span></header><p>${esc(a.scope)}</p></article>`).join("")}</div>` : ""}
        </section>
        ${isAdmin && data.available !== false ? `<section class="ac-panel" style="margin-top:14px"><h3>Betrieb <span>STOPP-SCHALTER</span></h3><div class="chips"><button class="ac-btn small ${data.control === "pausiert" ? "" : "danger"}" type="button" data-global="${data.control === "pausiert" ? "resume" : "pause"}">${data.control === "pausiert" ? "Alle Agenten fortsetzen" : "Alle Agenten anhalten"}</button><a class="ac-btn small" href="#" data-audit>FLOWWORK-Audit anzeigen</a></div><div data-audit-table></div></section>` : ""}`;
      extra.querySelector("[data-global]")?.addEventListener("click", (event) => this.control(event.currentTarget.dataset.global));
      extra.querySelector("[data-audit]")?.addEventListener("click", (event) => { event.preventDefault(); this.loadAudit(); });
      extra.querySelectorAll("[data-card]").forEach((card) => card.addEventListener("click", () => { this.selected = card.dataset.card; this.renderMap(this.data, Infinity); this.showDetail(this.selected); this.root.scrollIntoView({ behavior: "smooth" }); }));
    }

    async loadAudit() {
      const target = this.$("[data-audit-table]");
      const response = await fetch("/api/agents/audit");
      const result = await response.json().catch(() => ({}));
      if (!response.ok) { target.innerHTML = `<div class="ac-empty">${esc(result.detail || "Audit nicht verfügbar")}</div>`; return; }
      target.innerHTML = `<table class="ac-table"><thead><tr><th>Zeit</th><th>Rolle</th><th>Lauf</th><th>Operation</th><th>Objekt</th><th>Entscheidung</th></tr></thead><tbody>${(result.entries || []).map((e) => `<tr class="${e.decision === "abgelehnt" ? "denied" : ""}"><td>${esc(time(e.at))}</td><td>${esc(e.role)}</td><td>${esc(e.run)}</td><td>${esc(e.operation)}</td><td>${esc(e.object)}</td><td>${esc(e.decision)}${e.reason ? ` (${esc(e.reason)})` : ""}</td></tr>`).join("")}</tbody></table>`;
    }

    async openRun(runId, focus = []) {
      const dialog = this.$("[data-run-detail-dialog]");
      const target = this.$("[data-run-detail]");
      target.innerHTML = "<p>Lauf wird geladen …</p>";
      dialog.showModal();
      try {
        const response = await fetch(`/api/agents/runs/${encodeURIComponent(runId)}`);
        const detail = await response.json();
        if (!response.ok) throw new Error(detail.detail || "Lauf nicht verfügbar");
        target.innerHTML = renderRunDetail(detail, this.data, focus);
        target.querySelector("[data-focus]")?.scrollIntoView({ block: "start" });
        target.querySelector("[data-close]")?.addEventListener("click", () => dialog.close());
        target.querySelector("[data-cancel-run]")?.addEventListener("click", async () => { if (window.confirm("Lauf wirklich abbrechen?")) { await this.control("cancel", "", runId); dialog.close(); } });
      } catch (error) {
        target.innerHTML = `<p>${esc(error.message)}</p><button class="ac-btn" data-close>Schließen</button>`;
        target.querySelector("[data-close]")?.addEventListener("click", () => dialog.close());
      }
    }
  }

  function renderArtifact(artifact) {
    const c = artifact.content || {};
    const items = c.items || [];
    switch (artifact.kind) {
      case "auftrag":
        return `<dl class="kv"><dt>Zweck</dt><dd>${esc(c.goal)}</dd><dt>Nutzergruppe</dt><dd>${esc(c.user_group)}</dd><dt>Verhalten</dt><dd>${esc(c.behavior)}</dd><dt>Erfolgsbeispiel</dt><dd>${esc(c.success_example)}</dd><dt>Bereich</dt><dd>${esc(c.scope_label)} (${esc((c.paths || []).join(", "))})</dd></dl>`;
      case "anforderungen":
      case "baseline":
        return `${c.state ? `<p><span class="ac-chip lime">${esc(c.state)}</span> FLOWWORK ${esc(c.rm_id || "")}</p>` : ""}${items.map((r) => `<div class="req"><b>${esc(r.key)} · ${esc(r.title)}</b> <span class="ac-chip">${esc(r.priority)}</span><p>${esc(r.text)}</p><ul>${(r.acceptance_criteria || []).map((ac) => `<li>${esc(ac)}</li>`).join("")}</ul>${r.negative_case ? `<small>Negativfall: ${esc(r.negative_case)}</small>` : ""}</div>`).join("")}`;
      case "implementierung":
        return `<p>Digest <code>${esc(c.digest)}</code> · Basis <code>${esc((c.base || "").slice(0, 12))}</code></p><pre class="diff">${esc(c.diff || "")}</pre>`;
      case "ui_pruefung":
        return `<p><span class="ac-chip ${c.passed === c.total ? "lime" : "red"}">${esc(c.passed)} von ${esc(c.total)} Testfällen bestanden</span> ${esc(c.seconds)} s · Prüfbrowser gegen die Vorschau</p>${(c.scenarios || []).map((s) => `<div class="req"><b>${esc(s.key)} · ${esc(s.title)}</b> <span class="ac-chip ${s.passed ? "lime" : "red"}">${s.passed ? "bestanden" : "fehlgeschlagen"}</span><ol>${(s.steps || []).map((st) => `<li>${st.ok ? "✓" : "✗"} ${esc(st.do)}${st.note ? ` – <small>${esc(st.note)}</small>` : ""}</li>`).join("")}</ol>${(s.screenshots || []).map((img) => `<figure class="ui-shot"><img alt="${esc(img.name)}" loading="lazy" style="max-width:100%;border:1px solid var(--line, #ccc);border-radius:8px" src="data:image/jpeg;base64,${esc(img.data)}"><figcaption><small>${esc(img.name)}</small></figcaption></figure>`).join("")}</div>`).join("")}`;
      case "integration":
        return `<p><span class="ac-chip ${c.passed ? "lime" : "red"}">${c.passed ? "bestanden" : "nicht bestanden"}</span> ${esc(c.seconds)} s · Digest <code>${esc(c.digest)}</code></p><pre class="diff">${esc(c.summary || "")}</pre>`;
      default:
        return `${c.summary ? `<p>${esc(c.summary)}</p>` : ""}${(c.findings || []).length ? `<ul>${c.findings.map((f) => `<li><span class="ac-chip ${f.severity === "hoch" ? "red" : f.severity === "mittel" ? "amber" : ""}">${esc(f.severity)}</span> ${esc(f.location)}: ${esc(f.impact)}${f.recommendation ? ` – ${esc(f.recommendation)}` : ""}</li>`).join("")}</ul>` : ""}${items.length ? `<ul>${items.map((item) => `<li><b>${esc(item.key)}</b> ${esc(item.title)}${item.state ? ` <span class="ac-chip ${item.state === "luecke" ? "amber" : "lime"}">${esc(item.state)}</span>` : ""}${item.recommendation ? ` <span class="ac-chip">${esc(item.recommendation)}</span>` : ""}${item.benefit ? `<br><small>Nutzen: ${esc(item.benefit)} · Aufwand: ${esc(item.staff_effort)}</small>` : ""}${item.content ? `<pre class="diff">${esc(item.content)}</pre>` : ""}</li>`).join("")}</ul>` : ""}`;
    }
  }

  function renderRunDetail(detail, data, focus = []) {
    const run = detail.run;
    const latest = new Map();
    for (const artifact of detail.artifacts) latest.set(artifact.kind, artifact);
    const label = (role) => (data?.agents || []).find((a) => a.role === role)?.name || role || "Orchestrator";
    return `<header class="run-head"><div><span class="ac-chip lime">${esc(run.auftrag_id)}</span> <span class="ac-status ${esc(run.status)}">${esc(run.status)}</span><h3>${esc(run.title)}</h3><p class="lead">${esc(run.id)} · ${esc(run.change_class)} · beauftragt von ${esc(run.requested_by?.name)} · ${esc(run.model_calls)} Modellaufrufe${run.reason ? ` · ${esc(run.reason)}` : ""}</p></div><div><button class="ac-btn" data-close type="button">Schließen</button> ${["aktiv", "wartet", "blockiert", "pausiert"].includes(run.status) ? '<button class="ac-btn danger" data-cancel-run type="button">Lauf abbrechen</button>' : ""}</div></header>
      ${detail.manifest_gaps?.length ? `<p class="gaps">Nachweislücken: ${detail.manifest_gaps.map((g) => esc(g)).join(" · ")}</p>` : ""}
      ${renderFocus(detail, focus)}
      <h4>Verlauf</h4><ol class="timeline">${detail.steps.map((s) => `<li class="${esc(s.status)}"><b>${esc(label(s.role))}</b> <small>${esc(s.step_id)} · Versuch ${esc(s.attempt)} · ${esc(s.status)} · ${esc(s.provider)} ${esc(s.model)}</small><p>${esc(s.summary || s.error)}</p>${(s.findings || []).length ? `<small>${s.findings.length} Befund(e)</small>` : ""}</li>`).join("")}</ol>
      <h4>Entscheidungen</h4>${detail.decisions.length ? `<ul>${detail.decisions.map((d) => `<li><b>${esc(d.title)}</b> · ${esc(d.status)}${d.decided_by?.name ? ` durch ${esc(d.decided_by.name)}` : ""}${d.comment ? ` – „${esc(d.comment)}“` : ""}</li>`).join("")}</ul>` : "<p>Keine.</p>"}
      <h4>Ergebnisse (jeweils aktuelle Version)</h4>${[...latest.values()].map((a) => `<details class="artifact"><summary><b>${esc(a.kind)}</b> v${esc(a.version)} · ${esc(label(a.role))} · <code>${esc(a.digest.slice(0, 19))}</code></summary>${renderArtifact(a)}</details>`).join("")}`;
  }

  document.querySelectorAll("[data-agent-center]").forEach((element) => {
    element.agentCenter = new AgentCenter(element);
    const params = new URLSearchParams(window.location.search);
    const run = params.get("run");
    const focus = (params.get("focus") || "").split(",").filter((k) => /^[a-z]+$/.test(k));
    if (run && element.dataset.mode === "full") setTimeout(() => element.agentCenter.openRun(run, focus), 600);
    const draft = params.get("draft");
    if (draft && /^VOR-[0-9A-F]{6}$/.test(draft) && element.dataset.mode === "full") {
      fetch(`/api/agents/drafts/${draft}`).then((r) => (r.ok ? r.json() : null)).then((d) => {
        if (d && d.status === "offen") element.agentCenter.openRunDialog(d);
      });
    }
  });
})();
