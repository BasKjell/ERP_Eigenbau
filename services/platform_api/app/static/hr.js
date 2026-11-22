const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
let dashboard;
let calendarData;
let calendarMonth;
let calendarScope = "team";
let exportToken = "";
let recruitingData;
let payrollData;

const TYPE_LABEL = {
  vacation: "Urlaub", sick: "Krankmeldung", time_off: "Überstundenabbau", overtime: "Mehrarbeit",
  remote_work: "Mobiles Arbeiten", business_trip: "Dienstreise",
  correction: "Zeitkorrektur", absence: "Abwesend", holiday: "Feiertag"
};
const STATUS_LABEL = { pending: "Beantragt", approved: "Genehmigt", rejected: "Abgelehnt" };

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try { message = (await response.json()).detail || message; } catch (_) { /* response without JSON */ }
    throw new Error(message);
  }
  return response.json();
}
function escapeHtml(value) { return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char])); }
function employeeId() { return $("#employee").value || "DEMO-EMP-006"; }
function formatMinutes(value, signed = false) { const amount = Number(value || 0); const sign = signed && amount > 0 ? "+" : amount < 0 ? "−" : ""; const absolute = Math.abs(amount); return `${sign}${Math.floor(absolute / 60)}:${String(absolute % 60).padStart(2, "0")} h`; }
function formatDate(value, options = {}) { return new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", ...options }).format(new Date(`${value}T12:00:00`)); }
function formatTime(value) { return new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit" }).format(new Date(value)); }
function isoDate(date) { return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`; }
function requestPeriod(item) { return item.start_date === item.end_date ? formatDate(item.start_date) : `${formatDate(item.start_date)}–${formatDate(item.end_date)}`; }
function formatCurrency(cents) { return new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(Number(cents || 0) / 100); }

async function loadDashboard() {
  const employee = employeeId();
  const selected = $("#selected-date").value;
  const query = new URLSearchParams({ employee_id: employee });
  if (selected) query.set("selected_date", selected);
  dashboard = await api(`/api/hr/dashboard?${query}`);
  if (!$("#selected-date").value) $("#selected-date").value = dashboard.date;
  if (!$("#export-date").value) $("#export-date").value = dashboard.date;
  calendarMonth ||= dashboard.date.slice(0, 7);
  calendarScope = dashboard.is_manager ? calendarScope : "self";
  renderAll();
}

function renderAll() {
  calendarData = dashboard.calendar;
  renderHeader(); renderPresence(); renderMetrics(); renderAttendance(); renderTeam();
  renderUpcoming(); renderRequests(); renderApprovals(); renderExports(); renderAudit();
  renderCalendar();
}
function renderHeader() {
  const select = $("#employee");
  const previous = select.value || dashboard.employee.id;
  select.innerHTML = dashboard.employees.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join("");
  select.value = dashboard.employees.some((item) => item.id === previous) ? previous : dashboard.employee.id;
  $("#employee-avatar").textContent = dashboard.employee.initials;
  $("#first-name").textContent = dashboard.employee.name.split(" ")[0];
  $("#today-label").textContent = formatDate(dashboard.date, { weekday: "long" }).toUpperCase();
  $("#team-date").textContent = formatDate(dashboard.date, { weekday: "long" });
  $("#core-time").textContent = dashboard.work_rules.core_time;
  $("#day-target").textContent = formatMinutes(dashboard.metrics.target_minutes);
  $("#break-rule").textContent = `${dashboard.work_rules.minimum_break_minutes} min`;
  $("#request-badge").textContent = dashboard.metrics.pending_requests;
  $("#approval-badge").textContent = dashboard.metrics.team_pending_approvals;
  $("#approval-badge").hidden = !dashboard.is_manager;
  $$('[data-scope="team"]').forEach((button) => button.disabled = !dashboard.is_manager);
}
function renderPresence() {
  const own = dashboard.team.find((item) => item.id === dashboard.employee.id);
  const attendance = dashboard.attendance;
  const ring = $("#presence-ring");
  ring.className = `presence-ring ${own.status}`;
  $("#presence-time").textContent = attendance.last_timestamp ? formatTime(attendance.last_timestamp) : "–";
  $("#presence-status").textContent = own.status_label;
  $("#presence-copy").textContent = attendance.is_present ? `Du bist seit ${formatTime(attendance.last_timestamp)} eingestempelt.` : `${own.status_label}. Deine nächste Buchung wird minutengenau erfasst.`;
  $("#presence-detail").innerHTML = `<span>${escapeHtml(dashboard.employee.location)}</span><span>Pause ${formatMinutes(attendance.break_minutes)}</span><span>Quelle ${attendance.events.at(-1)?.terminal ? escapeHtml(attendance.events.at(-1).terminal) : "–"}</span>`;
  const button = $("#punch-button");
  button.textContent = attendance.is_present ? "Gehen buchen" : "Kommen buchen";
  button.dataset.direction = attendance.is_present ? "OUT" : "IN";
  button.classList.toggle("out", attendance.is_present);
  const blocked = ["vacation", "absent"].includes(own.status) && !attendance.is_present;
  button.disabled = blocked;
  button.title = blocked ? "Für heute ist eine ganztägige Abwesenheit hinterlegt" : "";
  const warning = $("#rule-warning");
  warning.hidden = !attendance.warnings.length;
  warning.textContent = attendance.warnings.join(" · ");
}
function renderMetrics() {
  const metrics = dashboard.metrics;
  const cards = [
    ["Arbeitszeit heute", formatMinutes(metrics.worked_minutes), `${formatMinutes(metrics.target_minutes)} Soll`, ""],
    ["Tagessaldo", formatMinutes(metrics.day_delta_minutes, true), "inkl. Zeitgutschrift", metrics.day_delta_minutes >= 0 ? "good" : "warn"],
    ["Zeitkonto", formatMinutes(metrics.overtime_balance_minutes, true), "aktueller Stand", metrics.overtime_balance_minutes >= 0 ? "good" : "warn"],
    ["Resturlaub", `${metrics.leave_remaining_days} Tage`, `${metrics.leave_entitlement_days} Tage Anspruch`, ""],
    ["Offene Anträge", metrics.pending_requests, dashboard.is_manager ? `${metrics.team_pending_approvals} im Team` : "in Bearbeitung", metrics.pending_requests ? "warn" : ""]
  ];
  $("#metric-grid").innerHTML = cards.map(([label, value, hint, css]) => `<article class="metric ${css}"><small>${label}</small><b>${value}</b><span>${hint}</span></article>`).join("");
}
function renderAttendance() {
  const events = dashboard.attendance.events;
  $("#attendance-timeline").innerHTML = events.length ? events.map((item) => `<article class="attendance-event"><time>${formatTime(item.timestamp)}</time><i></i><span><b>${item.direction === "IN" ? "Kommen" : "Gehen"}</b><small>${escapeHtml(item.terminal)} · ${item.source === "approved_correction" ? "genehmigte Korrektur" : escapeHtml(item.source)}</small></span><small>${item.erp_status === "exported" ? "ERP ✓" : "offen"}</small></article>`).join("") : `<div class="attendance-empty">Für diesen Tag wurden noch keine Zeiten gebucht.</div>`;
}
function teamRow(item) { return `<article class="team-row"><span class="avatar">${escapeHtml(item.initials)}</span><span><b>${escapeHtml(item.name)}</b><small>${escapeHtml(item.location)}</small></span><span class="status ${escapeHtml(item.status)}">${escapeHtml(item.detail)}</span></article>`; }
function renderTeam() {
  $("#team-preview").innerHTML = dashboard.team.slice(0, 5).map(teamRow).join("");
  $("#team-display").innerHTML = dashboard.team.map((item) => `<article class="person-card"><span class="avatar">${escapeHtml(item.initials)}</span><div><h3>${escapeHtml(item.name)}</h3><p>${escapeHtml(item.role)} · ${escapeHtml(item.department)}</p><span class="status ${escapeHtml(item.status)}">${escapeHtml(item.detail)}</span></div><footer><span>${escapeHtml(item.location)}</span><b>${item.worked_minutes ? formatMinutes(item.worked_minutes) : "–"}</b></footer></article>`).join("");
}
function renderUpcoming() {
  const events = calendarData.events.filter((item) => item.end_date >= dashboard.date).slice(0, 4);
  $("#upcoming-events").innerHTML = events.length ? events.map((item) => `<article class="event-card ${item.status}"><small>${requestPeriod(item)}</small><b>${escapeHtml(item.employee_name || item.label)}</b><span>${escapeHtml(item.employee_name ? item.label : "Feiertag")}</span><small>${item.status === "pending" ? " · Genehmigung offen" : ""}</small></article>`).join("") : `<p class="attendance-empty">Keine anstehenden Einträge.</p>`;
}
function renderRequests() {
  const own = dashboard.requests.filter((item) => item.employee_id === dashboard.employee.id);
  $("#request-summary").innerHTML = `<article class="summary-card"><small>Resturlaub</small><b>${dashboard.metrics.leave_remaining_days} Tage</b></article><article class="summary-card"><small>Zeitkonto</small><b>${formatMinutes(dashboard.metrics.overtime_balance_minutes, true)}</b></article><article class="summary-card"><small>In Genehmigung</small><b>${dashboard.metrics.pending_requests}</b></article>`;
  $("#request-table").innerHTML = own.length ? `<table><thead><tr><th>Antrag</th><th>Zeitraum</th><th>Umfang</th><th>Begründung</th><th>Status</th></tr></thead><tbody>${own.map((item) => `<tr><td><b>${escapeHtml(item.type_label)}</b><br><small>${escapeHtml(item.id)}</small></td><td>${requestPeriod(item)}</td><td>${item.minutes ? formatMinutes(item.minutes) : "ganztägig"}</td><td>${escapeHtml(item.reason)}</td><td><span class="pill ${item.status}">${STATUS_LABEL[item.status]}</span></td></tr>`).join("")}</tbody></table>` : `<div class="attendance-empty">Noch keine Anträge vorhanden.</div>`;
}
function renderApprovals() {
  const pending = dashboard.requests.filter((item) => item.can_decide);
  $("#approval-list").innerHTML = pending.length ? pending.map((item) => `<article class="approval"><span class="avatar">${escapeHtml(item.employee_name.split(" ").map((part) => part[0]).join(""))}</span><div><b>${escapeHtml(item.employee_name)} · ${escapeHtml(item.type_label)}</b><p>${requestPeriod(item)}${item.minutes ? ` · ${formatMinutes(item.minutes)}` : ""} · ${escapeHtml(item.reason)}</p></div><button type="button" data-decide="${escapeHtml(item.id)}">Entscheiden →</button></article>`).join("") : `<div class="attendance-empty">Keine offenen Genehmigungen.</div>`;
  $$('[data-decide]').forEach((button) => button.addEventListener("click", () => openDecision(button.dataset.decide)));
}

async function loadCalendar() {
  calendarData = await api(`/api/hr/calendar?${new URLSearchParams({ employee_id: employeeId(), month: calendarMonth, scope: calendarScope })}`);
  renderCalendar();
}
function renderCalendar() {
  if (!calendarData) return;
  const [year, month] = calendarMonth.split("-").map(Number);
  const first = new Date(year, month - 1, 1);
  const start = new Date(first); start.setDate(first.getDate() - ((first.getDay() + 6) % 7));
  const cells = Array.from({ length: 42 }, (_, index) => { const day = new Date(start); day.setDate(start.getDate() + index); return day; });
  $("#calendar-title").textContent = new Intl.DateTimeFormat("de-DE", { month: "long", year: "numeric" }).format(first);
  $("#calendar-grid").innerHTML = cells.map((day) => {
    const iso = isoDate(day); const outside = day.getMonth() !== month - 1; const today = iso === dashboard.date;
    const events = calendarData.events.filter((item) => item.start_date <= iso && item.end_date >= iso);
    return `<div class="calendar-day ${outside ? "outside" : ""} ${today ? "today" : ""}"><b>${day.getDate()}</b>${events.slice(0, 4).map((item) => `<span class="calendar-event ${escapeHtml(item.type)} ${item.status === "pending" ? "pending" : ""}" title="${escapeHtml(`${item.employee_name} ${item.label}`)}">${escapeHtml(calendarScope === "team" && item.employee_name ? `${item.employee_name.split(" ")[0]} · ${item.label}` : item.label)}</span>`).join("")}</div>`;
  }).join("");
  $$('[data-scope]').forEach((button) => button.classList.toggle("active", button.dataset.scope === calendarScope));
}
function renderExports() {
  $("#erp-mode").textContent = dashboard.erp.configured ? "ERPNext live" : "Demo-Adapter";
  $("#export-person").textContent = `${dashboard.employee.name} · ${formatDate($("#export-date").value || dashboard.date)}`;
  $("#export-history").innerHTML = dashboard.erp.exports.length ? dashboard.erp.exports.slice().reverse().map((item) => `<article><span><b>${escapeHtml(item.erp_reference)}</b><br><small>${formatDate(item.date)} · ${item.interval_count} Intervalle</small></span><span class="pill approved">${escapeHtml(item.mode)}</span></article>`).join("") : `<div class="attendance-empty">Noch keine Anwesenheit übergeben.</div>`;
}
function renderAudit() {
  $("#audit-list").innerHTML = dashboard.audit.length ? dashboard.audit.map((item) => `<article><span><b>${escapeHtml(item.message)}</b><small>${escapeHtml(item.actor_id)} · ${formatTime(item.timestamp)}</small></span><span class="pill approved">${escapeHtml(item.action)}</span></article>`).join("") : `<div class="attendance-empty">Keine Änderungen protokolliert.</div>`;
}

function showView(name) {
  $$('.view').forEach((view) => view.classList.toggle("active", view.id === `view-${name}`));
  $$('.nav-item').forEach((button) => button.classList.toggle("active", button.dataset.view === name));
  const titles = { overview: "Mein Arbeitstag", calendar: "Abwesenheitskalender", requests: "Anträge & Konten", team: "Teamübersicht", recruiting: "Bewerbungen & Stellen", payroll: "Lohnabrechnung", erp: "ERP-Übergabe" };
  $("#page-title").textContent = titles[name];
  if (name === "calendar") loadCalendar().catch(showError);
  if (name === "recruiting") loadRecruiting().catch(showError);
  if (name === "payroll") loadPayroll().catch(showError);
}

async function loadRecruiting() {
  const actor = $("#recruiting-actor").value || "HR-USER-001";
  recruitingData = await api(`/api/hr/recruiting?${new URLSearchParams({ actor_id: actor })}`);
  renderRecruiting();
}
function renderRecruiting() {
  const actorSelect = $("#recruiting-actor");
  const previous = actorSelect.value || recruitingData.actor.id;
  actorSelect.innerHTML = recruitingData.actors.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} · ${escapeHtml(item.roles.join(", "))}</option>`).join("");
  actorSelect.value = recruitingData.actors.some((item) => item.id === previous) ? previous : recruitingData.actor.id;
  $("#application-badge").textContent = recruitingData.metrics.active_applications;
  const cards = [
    ["Offene Stellen", recruitingData.metrics.open_vacancies, "Personalbedarf"],
    ["Aktive Bewerbungen", recruitingData.metrics.active_applications, "in Bearbeitung"],
    ["Gespräche", recruitingData.metrics.interviews, "aktuelle Phase"],
    ["Löschprüfung", recruitingData.metrics.retention_due, "in den nächsten 30 Tagen"]
  ];
  $("#recruiting-metrics").innerHTML = cards.map(([label, value, hint]) => `<article class="metric"><small>${label}</small><b>${value}</b><span>${hint}</span></article>`).join("");
  $("#vacancy-list").innerHTML = recruitingData.vacancies.map((item) => `<article><span><b>${escapeHtml(item.title)}</b><small>${escapeHtml(item.id)} · ${escapeHtml(item.department)} · ${item.positions} Stelle(n)</small></span><span class="pill approved">${escapeHtml(item.status)}</span></article>`).join("");
  $("#application-vacancy").innerHTML = recruitingData.vacancies.filter((item) => item.status === "open").map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.id)} · ${escapeHtml(item.title)}</option>`).join("");
  $("#recruiting-dms-mode").textContent = recruitingData.dms.mode === "live" ? "Paperless live" : "DMS-Demo";
  $("#recruiting-policy").innerHTML = `<div><dt>Zugriffsgruppe</dt><dd>${escapeHtml(recruitingData.dms.access_group)}</dd></div><div><dt>Prüffrist</dt><dd>${recruitingData.dms.retention_policy.days_after_close} Tage nach Abschluss</dd></div><div><dt>Aktion</dt><dd>Löschen oder Rechtsgrund dokumentieren</dd></div>`;
  $("#application-list").innerHTML = recruitingData.applications.map(applicationCard).join("");
  $$('[data-application-stage]').forEach((button) => button.addEventListener("click", () => moveApplication(button.dataset.applicationId, button.dataset.applicationStage)));
  $$('[data-application-upload]').forEach((button) => button.addEventListener("click", () => uploadApplicationDocument(button.dataset.applicationUpload)));
}
function applicationCard(item) {
  const nextStage = { new: "screening", screening: "interview", interview: "offer", offer: "hired" }[item.stage];
  const documents = item.documents.length ? item.documents.map((document) => document.document_id ? `<a href="/api/documents/${encodeURIComponent(document.document_id)}" target="_blank" rel="noopener"><span>PDF</span><b>${escapeHtml(document.document_type)}</b><small>${escapeHtml(document.title)} · im Browser öffnen</small></a>` : `<div class="processing-document"><span>↻</span><b>${escapeHtml(document.document_type)}</b><small>Paperless verarbeitet ${escapeHtml(document.filename || document.title)}</small></div>`).join("") : `<p class="attendance-empty">Noch keine DMS-Unterlage verknüpft.</p>`;
  const actions = nextStage ? `<button class="button primary small" data-application-stage="${nextStage}" data-application-id="${escapeHtml(item.id)}" type="button">Weiter: ${escapeHtml(recruitingData.stage_labels[nextStage])}</button><button class="link-button danger-text" data-application-stage="rejected" data-application-id="${escapeHtml(item.id)}" type="button">Ablehnen</button>` : `<span class="pill ${item.stage === "hired" ? "approved" : "rejected"}">${escapeHtml(item.stage_label)}</span>`;
  const uploadDisabled = recruitingData.dms.mode !== "live" ? "disabled title=\"Paperless-Zugang für Upload konfigurieren\"" : "";
  return `<article class="application-card"><header><span><b>${escapeHtml(item.candidate_name)}</b><small>${escapeHtml(item.id)} · ${escapeHtml(item.vacancy_title)}</small></span><span class="stage-pill ${escapeHtml(item.stage)}">${escapeHtml(item.stage_label)}</span></header><div class="application-meta"><span>${escapeHtml(item.email)}</span><span>Quelle ${escapeHtml(item.source)}</span><span class="${item.retention_status === "due" ? "warn-text" : ""}">Löschprüfung ${formatDate(item.retention_until)}</span></div><div class="application-documents">${documents}</div><footer><div class="upload-control"><input id="upload-${escapeHtml(item.id)}" type="file" accept="application/pdf,image/png,image/jpeg" ${uploadDisabled}/><button class="link-button" type="button" data-application-upload="${escapeHtml(item.id)}" ${uploadDisabled}>In DMS hochladen</button></div><div class="stage-actions">${actions}</div></footer></article>`;
}
async function moveApplication(id, stage) {
  try {
    await api(`/api/hr/recruiting/applications/${encodeURIComponent(id)}/stage`, { method: "POST", body: JSON.stringify({ actor_id: $("#recruiting-actor").value, stage, note: "Änderung in FLOWHR" }) });
    toast(stage === "rejected" ? "Bewerbung abgeschlossen" : "Bewerbungsphase aktualisiert");
    await loadRecruiting();
  } catch (error) { showError(error); }
}
async function uploadApplicationDocument(id) {
  const input = $(`#upload-${CSS.escape(id)}`);
  if (!input.files.length) { toast("Bitte zuerst eine PDF- oder Bilddatei auswählen", true); return; }
  const body = new FormData();
  body.append("file", input.files[0]); body.append("actor_id", $("#recruiting-actor").value); body.append("document_type", "Bewerbungsunterlage");
  try {
    const response = await fetch(`/api/hr/recruiting/applications/${encodeURIComponent(id)}/documents/upload`, { method: "POST", body });
    if (!response.ok) { const result = await response.json(); throw new Error(result.detail || `HTTP ${response.status}`); }
    toast("Unterlage wurde an die geschützte DMS-Akte übergeben"); await loadRecruiting();
  } catch (error) { showError(error); }
}

async function loadPayroll() {
  const actor = $("#payroll-actor").value || "HR-USER-001";
  const period = $("#payroll-period").value;
  const query = new URLSearchParams({ actor_id: actor });
  if (period) query.set("period_id", period);
  payrollData = await api(`/api/hr/payroll?${query}`);
  renderPayroll();
}
function renderPayroll() {
  const actorSelect = $("#payroll-actor");
  const selectedActor = actorSelect.value || payrollData.actor.id;
  actorSelect.innerHTML = payrollData.actors.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} · ${escapeHtml(item.roles.join(", "))}</option>`).join("");
  actorSelect.value = payrollData.actors.some((item) => item.id === selectedActor) ? selectedActor : payrollData.actor.id;
  const periodSelect = $("#payroll-period"); const selectedPeriod = periodSelect.value || payrollData.period.id;
  periodSelect.innerHTML = payrollData.periods.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.label)}</option>`).join(""); periodSelect.value = selectedPeriod;
  $("#payroll-notice").innerHTML = `<b>Abgrenzung:</b> ${escapeHtml(payrollData.legal_notice)} ELStAM: <b>${escapeHtml(payrollData.interfaces.elstam)}</b>, Sozialversicherung: <b>${escapeHtml(payrollData.interfaces.social_insurance)}</b>.`;
  const basis = payrollData.run || payrollData.preview;
  const metrics = [
    ["Beschäftigte", basis?.employee_count ?? payrollData.profiles.length, "geprüfte Stammdaten"],
    ["Brutto", basis ? formatCurrency(basis.gross_cents) : "–", "Testwerte"],
    ["Abzüge", basis ? formatCurrency(basis.deduction_cents) : "–", "Testwerte"],
    ["Netto", basis ? formatCurrency(basis.net_cents) : "–", "Auszahlungsbetrag Demo"]
  ];
  $("#payroll-metrics").innerHTML = metrics.map(([label, value, hint]) => `<article class="metric"><small>${label}</small><b>${value}</b><span>${hint}</span></article>`).join("");
  $("#payroll-status").textContent = payrollData.period.status;
  $("#attendance-lock").textContent = payrollData.period.attendance_status === "locked" ? "Zeitdaten abgeschlossen ✓" : "Zeitdaten noch offen";
  $("#payroll-interface-mode").textContent = `DMS ${payrollData.interfaces.dms} · ERP ${payrollData.interfaces.erp}`;
  $("#payroll-profiles").innerHTML = `<table><thead><tr><th>Beschäftigte/r</th><th>Steuer / Kasse</th><th>Bank</th><th>Brutto Testwert</th><th>Prüfung</th></tr></thead><tbody>${payrollData.profiles.map((item) => `<tr><td><b>${escapeHtml(item.employee_name)}</b><br><small>${escapeHtml(item.employee_id)} · ${escapeHtml(item.department)}</small></td><td>Klasse ${escapeHtml(item.tax_class)}<br><small>${escapeHtml(item.health_insurance)}</small></td><td>${escapeHtml(item.bank_account_masked)}</td><td>${formatCurrency(item.gross_cents)}</td><td><span class="pill ${item.master_data_status === "complete" ? "approved" : "rejected"}">${item.master_data_status === "complete" ? "vollständig" : "prüfen"}</span></td></tr>`).join("")}</tbody></table>`;
  renderPayrollPreview(); renderPayrollOutputs();
  const prepare = $("#prepare-payroll"), approve = $("#approve-payroll"), deliver = $("#deliver-payroll");
  prepare.disabled = !payrollData.permissions.can_prepare || payrollData.period.status !== "open";
  approve.disabled = !payrollData.permissions.can_approve || !payrollData.preview || payrollData.period.status !== "open";
  deliver.disabled = !payrollData.permissions.can_approve || !payrollData.run || payrollData.run.status !== "approved_pending_delivery";
  if (payrollData.permissions.can_prepare && payrollData.period.status === "open") $("#payroll-role-hint").textContent = payrollData.preview ? "Vorschau liegt vor. Für die Freigabe auf Konrad Kontrolle wechseln." : "Du bereitest die Vorschau vor; du kannst sie nicht selbst freigeben.";
  else if (payrollData.permissions.can_approve && payrollData.preview) $("#payroll-role-hint").textContent = `Vorbereitet durch ${payrollData.preview.prepared_by_name}. Du kannst getrennt freigeben.`;
  else $("#payroll-role-hint").textContent = payrollData.run ? "Der freigegebene Lauf kann jetzt kontrolliert übergeben oder eingesehen werden." : "Für den nächsten Schritt ist eine andere Payroll-Rolle erforderlich.";
}
function renderPayrollPreview() {
  const item = payrollData.run || payrollData.preview;
  if (!item) { $("#payroll-preview").innerHTML = `<p class="attendance-empty">Noch keine Abrechnungsvorschau erstellt.</p>`; return; }
  $("#payroll-preview").innerHTML = `<div class="payroll-total"><small>${payrollData.run ? "Freigegebener Lauf" : "Vorschau"}</small><b>${payrollData.run ? escapeHtml(payrollData.run.id) : "noch nicht freigegeben"}</b><span>${item.employee_count} Beschäftigte</span></div><dl><div><dt>Gesamtbrutto</dt><dd>${formatCurrency(item.gross_cents)}</dd></div><div><dt>Abzüge</dt><dd>${formatCurrency(item.deduction_cents)}</dd></div><div><dt>Netto</dt><dd>${formatCurrency(item.net_cents)}</dd></div>${payrollData.run ? `<div><dt>ERP-Beleg</dt><dd>${escapeHtml(payrollData.run.erp_reference || "noch ausstehend")}</dd></div>` : `<div><dt>Vorbereitet durch</dt><dd>${escapeHtml(item.prepared_by_name)}</dd></div>`}</dl>`;
}
function renderPayrollOutputs() {
  if (!payrollData.run) { $("#payroll-outputs").innerHTML = `<div class="attendance-empty">Nach Vier-Augen-Freigabe werden die Abrechnungs-PDFs erzeugt.</div>`; return; }
  const actor = encodeURIComponent($("#payroll-actor").value);
  $("#payroll-outputs").innerHTML = payrollData.run.outputs.map((output) => { const row = payrollData.run.rows.find((item) => item.employee_id === output.employee_id); return `<a href="/api/hr/payroll/runs/${encodeURIComponent(payrollData.run.id)}/payslips/${encodeURIComponent(output.employee_id)}?actor_id=${actor}" target="_blank" rel="noopener"><span>PDF</span><b>${escapeHtml(row.employee_name)}</b><small>${escapeHtml(output.filename)} · DMS ${escapeHtml(output.dms_status)}</small><i>Im Browser öffnen ↗</i></a>`; }).join("");
}
async function preparePayroll() { try { await api(`/api/hr/payroll/${encodeURIComponent(payrollData.period.id)}/prepare`, { method: "POST", body: JSON.stringify({ actor_id: $("#payroll-actor").value }) }); toast("Abrechnungsvorschau erstellt"); await loadPayroll(); } catch (error) { showError(error); } }
async function approvePayroll() { try { const result = await api(`/api/hr/payroll/${encodeURIComponent(payrollData.period.id)}/approve`, { method: "POST", body: JSON.stringify({ actor_id: $("#payroll-actor").value, confirmation_token: payrollData.preview.token }) }); toast(`Vier-Augen-Freigabe erfolgt: ${result.run.id}`); await loadPayroll(); } catch (error) { showError(error); } }
async function deliverPayroll() { try { const result = await api(`/api/hr/payroll/runs/${encodeURIComponent(payrollData.run.id)}/deliver`, { method: "POST", body: JSON.stringify({ actor_id: $("#payroll-actor").value }) }); toast(`Übergabe abgeschlossen: ${result.run.erp_reference}`); await loadPayroll(); } catch (error) { showError(error); } }
function openRequest(type = "vacation") {
  $("#request-type").value = type;
  $("#request-start").value = dashboard.date;
  $("#request-end").value = dashboard.date;
  updateRequestFields();
  $("#request-dialog").showModal();
}
function updateRequestFields() {
  const type = $("#request-type").value;
  const timed = ["time_off", "overtime", "correction"].includes(type);
  $("#time-fields").hidden = !timed;
  $("#minutes-field").hidden = !["time_off", "overtime"].includes(type);
}
function openDecision(id) {
  const item = dashboard.requests.find((request) => request.id === id);
  $("#decision-request-id").value = id;
  $("#decision-title").textContent = `${item.type_label} · ${item.employee_name}`;
  $("#decision-comment").value = "";
  $("#decision-dialog").showModal();
}
async function decide(decision) {
  try {
    await api(`/api/hr/requests/${encodeURIComponent($("#decision-request-id").value)}/decision`, { method: "POST", body: JSON.stringify({ approver_id: employeeId(), decision, comment: $("#decision-comment").value }) });
    $("#decision-dialog").close(); toast(decision === "approved" ? "Antrag genehmigt" : "Antrag abgelehnt"); await loadDashboard();
  } catch (error) { showError(error); }
}
async function previewExport() {
  try {
    const result = await api("/api/hr/export/erp", { method: "POST", body: JSON.stringify({ employee_id: employeeId(), date: $("#export-date").value, confirm: false }) });
    if (result.status === "already_exported") { $("#export-preview").innerHTML = `<p>Bereits übertragen: <b>${escapeHtml(result.export.erp_reference)}</b></p>`; return; }
    exportToken = result.confirmation_token;
    $("#export-preview").innerHTML = `${result.payload.time_logs.map((item) => `<div class="export-line"><span>${escapeHtml(item.from_time.slice(11,16))}–${escapeHtml(item.to_time.slice(11,16))}</span><b>${Number(item.hours).toLocaleString("de-DE")} h</b></div>`).join("")}<p>${result.mode === "live" ? "Die Bestätigung legt ein ERPNext-Timesheet an." : "Demo-Modus: Die Übergabe wird lokal protokolliert."}</p><button id="confirm-export" class="button success" type="button">Verbindlich übergeben</button>`;
    $("#confirm-export").addEventListener("click", confirmExport);
  } catch (error) { showError(error); }
}
async function confirmExport() {
  try {
    const result = await api("/api/hr/export/erp", { method: "POST", body: JSON.stringify({ employee_id: employeeId(), date: $("#export-date").value, confirm: true, confirmation_token: exportToken }) });
    toast(`Übergabe erfolgreich: ${result.export.erp_reference}`); exportToken = ""; $("#export-preview").innerHTML = `<p>Erfolgreich an <b>${escapeHtml(result.export.erp_reference)}</b> übergeben.</p>`; await loadDashboard();
  } catch (error) { showError(error); }
}
function toast(message, error = false) { const element = $("#toast"); element.textContent = message; element.className = `toast show ${error ? "error" : ""}`; clearTimeout(toast.timer); toast.timer = setTimeout(() => element.className = "toast", 3300); }
function showError(error) { toast(error.message || String(error), true); }

$$('.nav-item').forEach((button) => button.addEventListener("click", () => showView(button.dataset.view)));
$$('[data-open-view]').forEach((button) => button.addEventListener("click", () => showView(button.dataset.openView)));
$$('[data-close-dialog]').forEach((button) => button.addEventListener("click", () => $(`#${button.dataset.closeDialog}`).close()));
[$("#new-request-overview"), $("#new-request-calendar"), $("#new-request-main")].forEach((button) => button.addEventListener("click", () => openRequest()));
$("#correction-button").addEventListener("click", () => openRequest("correction"));
$("#request-type").addEventListener("change", updateRequestFields);
$("#employee").addEventListener("change", () => { $("#selected-date").value = ""; calendarMonth = undefined; exportToken = ""; loadDashboard().catch(showError); });
$("#selected-date").addEventListener("change", () => { $("#export-date").value = $("#selected-date").value; calendarMonth = $("#selected-date").value.slice(0,7); loadDashboard().catch(showError); });
$("#export-date").addEventListener("change", renderExports);
$("#punch-button").addEventListener("click", async () => { try { await api("/api/hr/punch", { method: "POST", body: JSON.stringify({ employee_id: employeeId(), direction: $("#punch-button").dataset.direction, source: "web", terminal: "FLOWHR Web" }) }); toast($("#punch-button").dataset.direction === "IN" ? "Kommen gebucht" : "Gehen gebucht"); await loadDashboard(); } catch (error) { showError(error); } });
$("#request-form").addEventListener("submit", async (event) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); const payload = { employee_id: employeeId(), ...data, minutes: data.minutes ? Number(data.minutes) : null }; try { await api("/api/hr/requests", { method: "POST", body: JSON.stringify(payload) }); $("#request-dialog").close(); event.currentTarget.reset(); toast("Antrag wurde zur Genehmigung eingereicht"); await loadDashboard(); } catch (error) { showError(error); } });
$("#approve-request").addEventListener("click", () => decide("approved"));
$("#reject-request").addEventListener("click", () => decide("rejected"));
$$('[data-scope]').forEach((button) => button.addEventListener("click", () => { calendarScope = button.dataset.scope; loadCalendar().catch(showError); }));
$("#calendar-prev").addEventListener("click", () => { const [year, month] = calendarMonth.split("-").map(Number); const value = new Date(year, month - 2, 1); calendarMonth = `${value.getFullYear()}-${String(value.getMonth()+1).padStart(2,"0")}`; loadCalendar().catch(showError); });
$("#calendar-next").addEventListener("click", () => { const [year, month] = calendarMonth.split("-").map(Number); const value = new Date(year, month, 1); calendarMonth = `${value.getFullYear()}-${String(value.getMonth()+1).padStart(2,"0")}`; loadCalendar().catch(showError); });
$("#calendar-today").addEventListener("click", () => { calendarMonth = dashboard.date.slice(0,7); loadCalendar().catch(showError); });
$("#preview-export").addEventListener("click", previewExport);
$("#new-application").addEventListener("click", () => $("#application-dialog").showModal());
$("#application-form").addEventListener("submit", async (event) => { event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget)); try { await api("/api/hr/recruiting/applications", { method: "POST", body: JSON.stringify({ actor_id: $("#recruiting-actor").value, ...values }) }); $("#application-dialog").close(); event.currentTarget.reset(); toast("Bewerbung mit Löschprüfung angelegt"); await loadRecruiting(); } catch (error) { showError(error); } });
$("#recruiting-actor").addEventListener("change", () => loadRecruiting().catch(showError));
$("#payroll-actor").addEventListener("change", () => loadPayroll().catch(showError));
$("#payroll-period").addEventListener("change", () => loadPayroll().catch(showError));
$("#prepare-payroll").addEventListener("click", preparePayroll);
$("#approve-payroll").addEventListener("click", approvePayroll);
$("#deliver-payroll").addEventListener("click", deliverPayroll);
function updateClock() { $("#clock").textContent = new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date()); }
setInterval(updateClock, 1000); updateClock();

loadDashboard().catch(showError);
