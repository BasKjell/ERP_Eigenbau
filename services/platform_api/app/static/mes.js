const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

let dashboard;
let selectedJobId;
let selectedJob;
let documents = [];
let currentFilter = "mine";
let activeTab = "instructions";
let timerHandle;

const STATUS = {
  ready: "Bereit",
  in_progress: "In Arbeit",
  paused: "Pausiert",
  waiting: "Wartet",
  blocked: "Gesperrt",
  completed: "Abgeschlossen"
};

const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
}[character]));

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

function operatorId() { return $("#operator").value || "DEMO-EMP-002"; }
function formatMinutes(value) { const minutes = Number(value || 0); return `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, "0")} h`; }
function formatDateTime(value) { if (!value) return "–"; return new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(value)); }
function formatClock(seconds) { return [Math.floor(seconds / 3600), Math.floor(seconds % 3600 / 60), seconds % 60].map((part) => String(part).padStart(2, "0")).join(":"); }

async function loadDashboard(preferredJob = selectedJobId) {
  const result = await api(`/api/mes/dashboard?operator_id=${encodeURIComponent(operatorId())}`);
  dashboard = result;
  renderHeader();
  renderMetrics();
  renderQueue();
  renderEvents();
  const visibleIds = queueJobs().map((job) => job.id);
  selectedJobId = preferredJob && dashboard.jobs.some((job) => job.id === preferredJob)
    ? preferredJob
    : (dashboard.next_job?.id || visibleIds[0] || dashboard.jobs[0]?.id);
  await selectJob(selectedJobId, false);
}

function renderHeader() {
  $("#plant-area").textContent = `${dashboard.site} · ${dashboard.area}`;
  $("#shift-name").textContent = dashboard.shift.name;
  $("#shift-time").textContent = `${dashboard.shift.starts_at}–${dashboard.shift.ends_at}`;
  const select = $("#operator");
  const previous = select.value || "DEMO-EMP-002";
  select.innerHTML = dashboard.operators.map((operator) => `<option value="${escapeHtml(operator.id)}">${escapeHtml(operator.name)}</option>`).join("");
  select.value = dashboard.operators.some((operator) => operator.id === previous) ? previous : dashboard.operators[0].id;
  const active = dashboard.operators.find((operator) => operator.id === select.value);
  $("#operator-avatar").textContent = active.initials;
  $("#operator-first-name").textContent = active.name.split(" ")[0];
  const next = dashboard.next_job;
  $("#overview-copy").textContent = next
    ? `${next.operation} an ${next.workstation} ist dein nächster Arbeitsschritt.`
    : "Für deine Auswahl sind aktuell keine offenen Arbeitsgänge vorhanden.";
}

function renderMetrics() {
  const metrics = dashboard.metrics;
  const cards = [
    ["Bereit", metrics.ready, ""],
    ["In Arbeit", metrics.running, ""],
    ["Zeit gebucht", formatMinutes(metrics.booked_minutes), ""],
    ["Störungen", metrics.blocked, metrics.blocked ? "alert" : ""]
  ];
  $("#mes-metrics").innerHTML = cards.map(([label, value, extra]) => `<article class="mes-metric ${extra}"><small>${label}</small><b>${value}</b></article>`).join("");
}

function queueJobs() {
  if (!dashboard) return [];
  if (currentFilter === "mine") return dashboard.my_jobs;
  if (currentFilter === "critical") return dashboard.jobs.filter((job) => job.status === "blocked" || job.priority === "high");
  return dashboard.jobs;
}

function renderQueue() {
  const jobs = queueJobs().slice().sort((a, b) => {
    const order = { in_progress: 0, blocked: 1, paused: 2, ready: 3, waiting: 4, completed: 5 };
    return (order[a.status] - order[b.status]) || a.sequence - b.sequence;
  });
  $("#queue-count").textContent = jobs.length;
  $("#job-queue").innerHTML = jobs.length ? jobs.map((job) => `
    <button class="job-card ${job.id === selectedJobId ? "active" : ""}" data-job="${escapeHtml(job.id)}" data-status="${escapeHtml(job.status)}" type="button">
      <span class="job-card-top"><small>${escapeHtml(job.id)} · ${escapeHtml(job.item_code)}</small><span class="status-pill ${escapeHtml(job.status)}">${STATUS[job.status]}</span></span>
      <h3>${escapeHtml(job.operation)}</h3>
      <span class="job-card-meta"><span>${escapeHtml(job.workstation)}</span><span>${job.completed_qty}/${job.target_qty} Stk</span></span>
      <span class="job-card-progress"><i style="width:${job.progress_percent}%"></i></span>
    </button>`).join("") : `<div class="queue-empty"><b>Keine Aufgaben</b><p>Für diesen Filter gibt es keine Arbeitsgänge.</p></div>`;
  $$('[data-job]').forEach((button) => button.addEventListener("click", () => selectJob(button.dataset.job)));
}

async function selectJob(jobId, rerenderQueue = true) {
  if (!jobId) return;
  selectedJobId = jobId;
  selectedJob = await api(`/api/mes/jobs/${encodeURIComponent(jobId)}`);
  if (rerenderQueue) renderQueue();
  renderJob();
  await loadDocuments();
  renderNextStep();
}

function renderJob() {
  const job = selectedJob;
  const issue = job.issue?.status === "open" ? `
    <div class="issue-banner"><span><b>${escapeHtml(job.issue.id)} · ${escapeHtml(job.issue.category)}</b><small>${escapeHtml(job.issue.description)}</small></span><button id="resolve-issue" type="button">Nacharbeit abschließen</button></div>` : "";
  $("#job-workspace").innerHTML = `
    <header class="job-header">
      <div class="job-breadcrumb"><b>${escapeHtml(job.work_order)}</b><span>›</span><span>${escapeHtml(job.sales_order)}</span><span>›</span><span>${escapeHtml(job.project)}</span><span class="status-pill ${escapeHtml(job.status)}">${STATUS[job.status]}</span></div>
      <div class="job-title-row"><div><h2>${escapeHtml(job.operation)}</h2><p>${escapeHtml(job.item_name)} · ${escapeHtml(job.item_code)} · Revision ${escapeHtml(job.revision)}</p></div><div class="job-timer"><small>Aktuelle Arbeitszeit</small><b id="job-timer">${formatMinutes(job.booked_minutes)}</b></div></div>
      <div class="job-facts">
        <div class="job-fact"><small>Arbeitsplatz</small><b>${escapeHtml(job.workstation)}</b></div>
        <div class="job-fact"><small>Bedienperson</small><b>${escapeHtml(job.operator?.name || "Nicht zugeordnet")}</b></div>
        <div class="job-fact"><small>Planzeit</small><b>${job.planned_minutes} min</b></div>
        <div class="job-fact"><small>Menge</small><b>${job.completed_qty} / ${job.target_qty} Stk</b></div>
        <div class="job-fact"><small>Fällig</small><b>${formatDateTime(job.due_at)}</b></div>
      </div>
    </header>
    ${renderRoute(job)}
    ${issue}
    <nav class="job-tabs" aria-label="Arbeitsgang-Details">
      <button class="job-tab ${activeTab === "instructions" ? "active" : ""}" data-tab="instructions" type="button">Anleitung & Checkliste</button>
      <button class="job-tab ${activeTab === "material" ? "active" : ""}" data-tab="material" type="button">Material & Seriennummern</button>
      <button class="job-tab ${activeTab === "quality" ? "active" : ""}" data-tab="quality" type="button">Prüfmerkmale</button>
      <button class="job-tab ${activeTab === "time" ? "active" : ""}" data-tab="time" type="button">Zeitbuchungen</button>
    </nav>
    <div id="job-content" class="job-content">${renderActiveTab()}</div>
    ${renderActions(job)}`;
  $$('.job-tab').forEach((button) => button.addEventListener("click", () => { activeTab = button.dataset.tab; renderJob(); }));
  bindJobActions();
  startTimer();
}

function renderRoute(job) {
  return `<section class="route"><div class="route-title"><span>Fertigungsroute</span><span>${job.route.filter((step) => step.status === "completed").length} / ${job.route.length} abgeschlossen</span></div><div class="route-flow">${job.route.map((step) => {
    const current = step.id === job.id;
    const css = step.status === "completed" ? "done" : step.status === "blocked" ? "blocked" : current ? "current" : "";
    return `<div class="route-step ${css}" title="${escapeHtml(STATUS[step.status])}"><b>${String(step.sequence).padStart(2, "0")} · ${escapeHtml(step.operation)}</b><small>${escapeHtml(step.workstation)}</small></div>`;
  }).join("")}</div></section>`;
}

function renderActiveTab() {
  if (activeTab === "material") return renderMaterial();
  if (activeTab === "quality") return renderQuality();
  if (activeTab === "time") return renderTime();
  return renderInstructions();
}

function renderInstructions() {
  const job = selectedJob;
  return `<div class="content-heading"><div><h3>Arbeitsanweisung</h3><p>Schritte in der angegebenen Reihenfolge ausführen.</p></div><span class="revision-badge">✓ FREIGEGEBEN · REV. ${escapeHtml(job.revision)}</span></div>
    <ol class="instruction-list">${job.instructions.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>
    <section class="checklist"><h4>Pflichtprüfungen <span class="required-dot">*</span></h4>${job.checklist.map((item) => `<label class="check-row"><input type="checkbox" data-check="${escapeHtml(item.id)}" ${job.checklist_completed.includes(item.id) ? "checked" : ""} ${job.status === "completed" ? "disabled" : ""} /><span>${escapeHtml(item.label)}${item.required ? ' <span class="required-dot">*</span>' : ""}</span></label>`).join("")}</section>`;
}

function renderMaterial() {
  const job = selectedJob;
  const materials = job.materials.length ? `<table class="material-table"><thead><tr><th>Material</th><th>Soll</th><th>Bereit</th><th>Charge</th><th>Status</th></tr></thead><tbody>${job.materials.map((item) => `<tr><td><b>${escapeHtml(item.item)}</b><small>${escapeHtml(item.name)}</small></td><td>${item.planned} ${escapeHtml(item.unit)}</td><td>${item.issued} ${escapeHtml(item.unit)}</td><td>${escapeHtml(item.lot)}</td><td class="material-ok">✓ Verfügbar</td></tr>`).join("")}</tbody></table>` : `<div class="empty-content">Für diesen Arbeitsgang wird kein zusätzliches Material entnommen.</div>`;
  const serials = job.serial_numbers.length ? job.serial_numbers.map((serial) => `<span class="serial-tag">${escapeHtml(serial)}</span>`).join("") : `<span class="muted">Noch keine Seriennummer zurückgemeldet.</span>`;
  return `<div class="content-heading"><div><h3>Materialbereitstellung</h3><p>Ausgegebene Komponenten und Chargen aus dem WIP-Lager.</p></div><span class="revision-badge">✓ VOLLSTÄNDIG</span></div>${materials}<section class="serial-summary"><h4>Geräte-Seriennummern</h4><div class="serial-tags">${serials}</div></section>`;
}

function renderQuality() {
  const characteristics = selectedJob.quality_characteristics || [];
  return `<div class="content-heading"><div><h3>Prüfmerkmale</h3><p>Vorgaben aus dem freigegebenen Prüfplan.</p></div><span class="revision-badge">DMS VERKNÜPFT</span></div>${characteristics.length ? `<div class="characteristics">${characteristics.map((item) => `<article class="characteristic"><small>${escapeHtml(item.name)}</small><b>${item.target} ${escapeHtml(item.unit)}</b><span class="muted">Toleranz ${escapeHtml(item.tolerance)}</span></article>`).join("")}</div>` : `<div class="empty-content">Für diesen Arbeitsgang gelten die Pflichtprüfungen der Checkliste. Detaillierte Merkmale enthält die verlinkte Arbeitsunterlage.</div>`}`;
}

function renderTime() {
  const job = selectedJob;
  return `<div class="content-heading"><div><h3>Zeitbuchungen</h3><p>Terminal- und Korrekturbuchungen für diesen Arbeitsgang.</p></div><button id="open-time-inline" class="button secondary" type="button">+ Zeit nachtragen</button></div>
    <div class="time-summary"><div><small>Plan</small><b>${formatMinutes(job.planned_minutes)}</b></div><div><small>Ist</small><b>${formatMinutes(job.booked_minutes)}</b></div><div><small>Abweichung</small><b>${job.booked_minutes - job.planned_minutes > 0 ? "+" : ""}${job.booked_minutes - job.planned_minutes} min</b></div></div>
    ${job.time_logs.length ? `<table class="time-table"><thead><tr><th>Bedienperson</th><th>Tätigkeit</th><th>Von</th><th>Bis</th><th>Dauer</th><th>Quelle</th></tr></thead><tbody>${job.time_logs.map((log) => `<tr><td>${escapeHtml(log.operator_name)}</td><td>${escapeHtml(log.activity)}</td><td>${formatDateTime(log.started_at)}</td><td>${log.ended_at ? formatDateTime(log.ended_at) : "läuft"}</td><td>${log.minutes ?? "–"} min</td><td>${log.source === "manual" ? "Korrektur" : "Terminal"}</td></tr>`).join("")}</tbody></table>` : `<div class="empty-content">Noch keine Zeit gebucht.</div>`}`;
}

function renderActions(job) {
  const canStart = ["ready", "paused"].includes(job.status);
  const canPause = job.status === "in_progress" && job.active_operator === operatorId();
  const canComplete = job.status === "in_progress" && job.active_operator === operatorId();
  return `<footer class="action-bar">
    <button id="start-job" class="button primary" type="button" ${canStart ? "" : "disabled"}>▶ Arbeit starten</button>
    <button id="pause-job" class="button warning" type="button" ${canPause ? "" : "disabled"}>Ⅱ Pause</button>
    <button id="time-job" class="button secondary" type="button" ${job.status === "completed" ? "disabled" : ""}>＋ Zeit</button>
    <span class="action-spacer"></span>
    <button id="issue-job" class="button danger-outline" type="button" ${["completed", "blocked", "waiting"].includes(job.status) ? "disabled" : ""}>! Störung</button>
    <button id="complete-job" class="button success" type="button" ${canComplete ? "" : "disabled"}>✓ Abschließen</button>
  </footer>`;
}

function bindJobActions() {
  $("#start-job")?.addEventListener("click", () => mutate(`/api/mes/jobs/${selectedJob.id}/start`, { operator_id: operatorId() }, "Arbeitsgang gestartet"));
  $("#pause-job")?.addEventListener("click", () => $("#pause-dialog").showModal());
  $("#time-job")?.addEventListener("click", () => $("#time-dialog").showModal());
  $("#open-time-inline")?.addEventListener("click", () => $("#time-dialog").showModal());
  $("#issue-job")?.addEventListener("click", () => $("#issue-dialog").showModal());
  $("#complete-job")?.addEventListener("click", openCompletion);
  $("#resolve-issue")?.addEventListener("click", () => $("#resolve-dialog").showModal());
}

function startTimer() {
  window.clearInterval(timerHandle);
  const openLog = selectedJob.time_logs.find((log) => !log.ended_at);
  if (!openLog) return;
  const started = new Date(openLog.started_at).getTime();
  const update = () => { const timer = $("#job-timer"); if (timer) timer.textContent = formatClock(Math.max(0, Math.floor((Date.now() - started) / 1000))); };
  update(); timerHandle = window.setInterval(update, 1000);
}

async function loadDocuments() {
  const result = await api(`/api/mes/jobs/${encodeURIComponent(selectedJob.id)}/documents`);
  documents = result.linked_documents;
  const dms = $("#dms-state");
  dms.textContent = result.dms_search.mode === "live" ? "DMS LIVE" : "DMS DEMO";
  dms.className = `dms-state ${result.dms_search.mode === "live" ? "live" : ""}`;
  $("#mes-documents").innerHTML = documents.length ? documents.map((document) => `<button class="mes-document" type="button" data-document="${escapeHtml(document.id)}"><span class="doc-symbol">PDF</span><span><b>${escapeHtml(document.title)}</b><small>${escapeHtml(document.revision)} · ${escapeHtml(document.type)}</small></span><span class="open-arrow">↗</span></button>`).join("") : `<p class="muted">Keine Arbeitsunterlage zugeordnet.</p>`;
  $$('[data-document]').forEach((button) => button.addEventListener("click", () => openDocument(button.dataset.document)));
}

function renderNextStep() {
  const route = selectedJob.route;
  const currentIndex = route.findIndex((step) => step.id === selectedJob.id);
  const next = route[currentIndex + 1];
  $("#next-step").innerHTML = next ? `<h3>${escapeHtml(next.operation)}</h3><p>${STATUS[next.status]} · nach Abschluss von ${escapeHtml(selectedJob.operation)}</p><div class="next-meta"><span>${escapeHtml(next.workstation)}</span><span>Folge ${next.sequence}</span></div>` : `<h3>Fertigmeldung</h3><p>Nach Qualitätsfreigabe in das Fertigwarenlager buchen.</p><div class="next-meta"><span>ERPNext Stock</span><span>Übergabe</span></div>`;
}

function renderEvents() {
  $("#mes-events").innerHTML = dashboard.events.slice(0, 4).map((event) => `<article class="mes-event ${escapeHtml(event.level)}"><p>${escapeHtml(event.message)}</p><small>${escapeHtml(event.job_id)} · ${formatDateTime(event.timestamp)}</small></article>`).join("");
}

function openCompletion() {
  $("#complete-qty").max = selectedJob.remaining_qty;
  $("#complete-qty").value = selectedJob.remaining_qty;
  $("#serial-field").hidden = !selectedJob.serial_tracking;
  const planned = Array.from({ length: selectedJob.remaining_qty }, (_, index) => `SN-${String(10001 + selectedJob.completed_qty + index)}`);
  $("#complete-serials").value = selectedJob.serial_tracking ? planned.join("\n") : "";
  $("#complete-dialog").showModal();
}

async function mutate(path, payload, success) {
  try {
    await api(path, { method: "POST", body: JSON.stringify(payload) });
    closeDialogs();
    toast(success);
    await loadDashboard(selectedJobId);
  } catch (error) { toast(error.message, true); }
}

function checklistSelection() { return $$('[data-check]:checked').map((input) => input.dataset.check); }

$("#pause-form").addEventListener("submit", (event) => { event.preventDefault(); const data = new FormData(event.currentTarget); mutate(`/api/mes/jobs/${selectedJob.id}/pause`, { operator_id: operatorId(), reason: data.get("reason"), note: data.get("note") }, "Pause gebucht"); });
$("#time-form").addEventListener("submit", (event) => { event.preventDefault(); const data = new FormData(event.currentTarget); mutate(`/api/mes/jobs/${selectedJob.id}/time`, { operator_id: operatorId(), minutes: Number(data.get("minutes")), activity: data.get("activity"), note: data.get("note") }, "Zeitbuchung gespeichert"); });
$("#issue-form").addEventListener("submit", (event) => { event.preventDefault(); const data = new FormData(event.currentTarget); mutate(`/api/mes/jobs/${selectedJob.id}/issue`, { operator_id: operatorId(), category: data.get("category"), description: data.get("description") }, "Arbeitsgang gesperrt und Störung angelegt"); });
$("#resolve-form").addEventListener("submit", (event) => { event.preventDefault(); const data = new FormData(event.currentTarget); mutate(`/api/mes/jobs/${selectedJob.id}/issue/resolve`, { operator_id: operatorId(), resolution: data.get("resolution") }, "Störung behoben; Arbeitsgang wieder freigegeben"); });
$("#complete-form").addEventListener("submit", (event) => { event.preventDefault(); const data = new FormData(event.currentTarget); mutate(`/api/mes/jobs/${selectedJob.id}/complete`, { operator_id: operatorId(), completed_qty: Number(data.get("completed_qty")), scrap_qty: Number(data.get("scrap_qty")), serial_numbers: String(data.get("serial_numbers") || "").split(/[\n,;]+/).map((value) => value.trim()).filter(Boolean), checklist: checklistSelection(), note: data.get("note") }, "Arbeitsgang erfolgreich zurückgemeldet"); });

function closeDialogs() { $$('.mes-dialog[open]').forEach((dialog) => dialog.close()); }
function openDocument(documentId) { const document = documents.find((item) => item.id === documentId); if (!document) return; $("#document-title").textContent = `${document.title} · ${document.revision}`; $("#document-frame").src = document.url; $("#document-dialog").showModal(); }
$("#close-document").addEventListener("click", () => { $("#document-dialog").close(); $("#document-frame").src = "about:blank"; });

function toast(message, isError = false) { const element = $("#mes-toast"); element.textContent = message; element.className = `mes-toast show ${isError ? "error" : ""}`; window.clearTimeout(toast.timer); toast.timer = window.setTimeout(() => { element.className = "mes-toast"; }, 3200); }
function updateClock() { $("#clock").textContent = new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date()); }
window.setInterval(updateClock, 1000); updateClock();

$$('.filter').forEach((button) => button.addEventListener("click", async () => { currentFilter = button.dataset.filter; $$('.filter').forEach((item) => item.classList.toggle("active", item === button)); renderQueue(); const jobs = queueJobs(); if (jobs.length && !jobs.some((job) => job.id === selectedJobId)) await selectJob(jobs[0].id); }));
$("#operator").addEventListener("change", async () => { selectedJobId = undefined; await loadDashboard(); });
$("#refresh").addEventListener("click", () => loadDashboard());

loadDashboard().catch((error) => { toast(error.message, true); $("#job-workspace").innerHTML = `<div class="workspace-loading"><p>${escapeHtml(error.message)}</p></div>`; });
