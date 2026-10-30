const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
let state;

const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
}[char]));

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unbekannter Fehler" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

function formatTime(value) {
  return new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function render(nextState) {
  state = nextState;
  const order = state.order;
  const active = state.process.find((step) => ["active", "blocked"].includes(step.status)) || state.process.at(-1);
  $("#current-status").textContent = active.label;
  $("#order-progress").textContent = `${order.progress} %`;
  const risk = $("#order-risk");
  risk.textContent = order.delivery_risk === "at_risk" ? "Termin gefährdet" : "Im Plan";
  risk.className = `risk ${order.delivery_risk === "at_risk" ? "bad" : "good"}`;
  renderProcess(); renderMetrics(); renderTimeline(); renderIncident(); renderBom(); renderCapacity(); renderDocuments();
}

function renderProcess() {
  $("#process").innerHTML = state.process.map((step) => `
    <button class="process-step ${escapeHtml(step.status)}" data-stage="${escapeHtml(step.id)}" title="${escapeHtml(step.description)}">
      <small>${String(step.sequence).padStart(2, "0")} · ${escapeHtml(step.system.split(" ")[0])}</small>
      <b>${escapeHtml(step.short_label)}</b>
    </button>`).join("");
  $$("[data-stage]").forEach((button) => button.addEventListener("click", () => mutate(`/api/demo/stage/${button.dataset.stage}`, "Prozessstation geladen")));
}

function renderMetrics() {
  const m = state.metrics;
  const cards = [
    ["Prozessfortschritt", `${m.process_progress} %`, `${m.completed_steps} von ${m.total_steps} Schritten abgeschlossen`],
    ["Material verfügbar", `${m.materials_available} %`, m.materials_available === 100 ? "Alle Komponenten bereit" : "Mainboards werden beschafft"],
    ["Geräte fertig", `${m.finished_units} / ${m.planned_units}`, "Seriennummerngeführt"],
    ["Offene Abweichungen", String(m.open_incidents), m.open_incidents ? "Maßnahme erforderlich" : "Keine Blockade"]
  ];
  $("#metrics").innerHTML = cards.map(([label, value, sub]) => `<article class="metric"><span class="label">${label}</span><span class="value">${value}</span><span class="sub">${sub}</span></article>`).join("");
}

function renderTimeline() {
  $("#timeline").innerHTML = state.timeline.slice(0, 7).map((event) => `
    <div class="event ${escapeHtml(event.level)}"><time>${formatTime(event.timestamp)}</time><span class="event-dot"></span><div><p>${escapeHtml(event.message)}</p><small>${escapeHtml(event.system)}</small></div></div>`).join("");
}

function renderIncident() {
  const incident = state.quality_incident;
  if (!incident || incident.status === "resolved") {
    $("#incident").innerHTML = `<div class="incident-empty"><div class="shield">✓</div><h3>${incident ? "Abweichung behoben" : "Qualität im grünen Bereich"}</h3><p>${incident ? escapeHtml(incident.resolution) : "Starte den Fehlerfall, um Abweichung, Nacharbeit und erneute Freigabe live zu demonstrieren."}</p><button id="failure" class="button ghost">Fehlerfall SN-10004 starten</button></div>`;
    $("#failure").addEventListener("click", () => mutate("/api/demo/failure", "Qualitätsabweichung erzeugt"));
  } else {
    $("#incident").innerHTML = `<div class="incident-card"><span class="alert">● ABWEICHUNG OFFEN · ${escapeHtml(incident.id)}</span><h4>${escapeHtml(incident.test)} fehlgeschlagen</h4><p>Gerät ${escapeHtml(incident.serial_number)} wurde automatisch gesperrt.</p><dl><div><dt>Messwert</dt><dd>${escapeHtml(incident.measured)}</dd></div><div><dt>Maßnahme</dt><dd>${escapeHtml(incident.action)}</dd></div></dl><button id="rework" class="button">Nacharbeit abschließen & erneut prüfen</button></div>`;
    $("#rework").addEventListener("click", () => mutate("/api/demo/rework", "Nacharbeit erfolgreich abgeschlossen"));
  }
}

function renderBom() {
  $("#bom-table").innerHTML = `<div class="table-row header"><span>Artikel</span><span>Bezeichnung</span><span>Menge</span><span>Typ</span><span>Bestand</span></div>` + state.bom.map((item) => {
    const required = item.qty * state.order.quantity;
    const percent = Math.min(100, Math.round(item.available / required * 100));
    return `<div class="table-row"><b>${escapeHtml(item.item)}</b><span>${escapeHtml(item.name)}</span><span>${required}</span><span class="tag">${escapeHtml(item.source)}</span><div><small>${item.available} / ${required}</small><div class="availability ${percent < 100 ? "missing" : ""}"><i style="width:${percent}%"></i></div></div></div>`;
  }).join("");
}

function renderCapacity() {
  $("#capacity-grid").innerHTML = state.capacity.map((resource) => `<article class="capacity-card ${resource.utilization >= 85 ? "hot" : ""}"><h4>${escapeHtml(resource.name)}</h4><div class="capacity-number">${resource.utilization}<small>%</small></div><div class="bar"><i style="width:${resource.utilization}%"></i></div><dl><div><dt>Parallel</dt><dd>${resource.capacity}</dd></div><div><dt>Schicht</dt><dd>${escapeHtml(resource.shift)}</dd></div><div><dt>Vorgang</dt><dd>${resource.operation_minutes} min</dd></div></dl></article>`).join("");
}

function renderDocuments() {
  $("#document-grid").innerHTML = state.documents.map((doc) => `<a class="document-card" target="_blank" href="/api/documents/${encodeURIComponent(doc.id)}"><span class="doc-icon">PDF</span><h4>${escapeHtml(doc.title)}</h4><p>${escapeHtml(doc.revision)} · ${escapeHtml(doc.type)}</p></a>`).join("");
}

async function mutate(path, success) {
  try { render(await api(path, { method: "POST" })); toast(success); }
  catch (error) { toast(error.message, true); }
}

function toast(message, isError = false) {
  const element = $("#toast"); element.textContent = message; element.className = `toast show ${isError ? "error" : ""}`;
  window.clearTimeout(toast.timer); toast.timer = window.setTimeout(() => element.className = "toast", 2600);
}

async function ask(question) {
  const answer = $("#answer"); answer.className = "answer"; answer.textContent = "Systeme werden abgefragt …";
  try {
    const result = await api("/api/assistant/ask", { method: "POST", body: JSON.stringify({ question }) });
    answer.innerHTML = `<p>${escapeHtml(result.answer)}</p><div class="sources">${result.sources.map((source) => `<span class="source">${escapeHtml(source.system)} · ${escapeHtml(source.reference)}</span>`).join("")}</div>`;
  } catch (error) { answer.textContent = error.message; }
}

$("#advance").addEventListener("click", () => mutate("/api/demo/advance", "Nächster Prozessschritt gestartet"));
$("#reset").addEventListener("click", () => mutate("/api/demo/reset", "Demo zurückgesetzt"));
$$('.tab').forEach((tab) => tab.addEventListener("click", () => {
  $$(".tab,.tab-panel").forEach((element) => element.classList.remove("active"));
  tab.classList.add("active"); $(`#${tab.dataset.tab}`).classList.add("active");
}));
$$('.suggestions button').forEach((button) => button.addEventListener("click", () => { $("#question").value = button.textContent; ask(button.textContent); }));
$("#ask-form").addEventListener("submit", (event) => { event.preventDefault(); ask($("#question").value); });

api("/api/demo").then(render).catch((error) => toast(error.message, true));
