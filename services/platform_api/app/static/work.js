const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const state = { data: null, requirementFilter: "all", query: "", projectKey: "scu-100" };
const escapeHtml = (value) => window.PlatformApps?.escapeHtml(value) || String(value ?? "");

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { "Content-Type": "application/json", Accept: "application/json", ...(options.headers || {}) } });
  if (response.status === 401) { window.location.assign(`/auth/login?next=${encodeURIComponent(window.location.pathname)}`); throw new Error("Anmeldung erforderlich"); }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
  return payload;
}

function bucket(status) {
  const value = String(status).toLowerCase();
  if (/erledigt|closed|geschlossen|done/.test(value)) return "done";
  if (/prüfung|review|feedback/.test(value)) return "review";
  if (/bearbeitung|progress|umsetzung/.test(value)) return "progress";
  return "backlog";
}

function statusLabel(status) { return ({ draft: "Entwurf", review: "Im Review", approved: "Freigegeben", verified: "Verifiziert", rejected: "Abgelehnt", in_progress: "In Bearbeitung", changes_requested: "Änderungen angefordert", completed: "Abgeschlossen" })[status] || status; }
function toast(message, error = false) { const element = $("#work-toast"); element.textContent = message; element.className = `work-toast show ${error ? "error" : ""}`; clearTimeout(toast.timer); toast.timer = setTimeout(() => element.className = "work-toast", 3000); }
function projectKey(project) { return String(project?.identifier || project?.id || ""); }
function activeProject() { return state.data.projects.find((project) => projectKey(project) === state.projectKey) || state.data.projects[0]; }
function projectIssues() { const project = activeProject(); return state.data.issues.filter((issue) => !project || issue.project === project.name); }
function projectRequirements() { return state.data.requirements.filter((req) => String(req.project_id || "scu-100") === state.projectKey); }
function projectTraceability() { const ids = new Set(projectRequirements().map((req) => req.id)); return state.data.traceability.filter((row) => ids.has(row.requirement_id)); }
function projectWiki() { const project = activeProject(); return state.data.wiki.filter((page) => !project || page.project === project.name); }
function projectBaselines() { const ids = new Set(projectRequirements().map((req) => req.id)); return state.data.baselines.filter((baseline) => baseline.items.some((item) => ids.has(item.requirement_id))); }

function renderIdentity() {
  const user = state.data.user;
  const name = user?.name || user?.username || "Demo Benutzer";
  $("#work-user").textContent = name;
  $("#work-role").textContent = user?.department || "FLOWWORK Demo";
  $("#work-avatar").textContent = name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
  $("#redmine-mode").textContent = state.data.mode === "live" ? "Redmine Live" : "Redmine Demo";
  $("#redmine-state").textContent = state.data.integration.detail;
  $("#redmine-dot").classList.toggle("online", state.data.integration.reachable);
  $("#sync-chip").textContent = state.data.mode === "live" ? "● Redmine synchronisiert" : "○ Demo-Adapter · Redmine bereit";
}

function renderMetrics() {
  const issues = projectIssues();
  const requirements = projectRequirements();
  const traceability = projectTraceability();
  const openIssues = issues.filter((issue) => bucket(issue.status) !== "done");
  const today = new Date().toISOString().slice(0, 10);
  const m = {
    projects: state.data.metrics.projects,
    open_tasks: openIssues.length,
    overdue_tasks: openIssues.filter((issue) => issue.due_date && issue.due_date < today).length,
    requirements: requirements.length,
    approved_requirements: requirements.filter((req) => ["approved", "verified"].includes(req.status)).length,
    trace_coverage: traceability.length ? Math.round(traceability.filter((row) => row.complete).length / traceability.length * 100) : 100,
  };
  $("#work-metrics").innerHTML = [
    ["Aktive Projekte", m.projects, "Portfolio"], ["Offene Aufgaben", m.open_tasks, `${m.overdue_tasks} überfällig`, m.overdue_tasks ? "alert" : ""],
    ["Anforderungen", m.requirements, `${m.approved_requirements} freigegeben`], ["Traceability", `${m.trace_coverage}%`, "Ticket · Wiki · Test"], ["Baselines", projectBaselines().length, "eingefrorene Stände"],
  ].map(([label, value, note, type]) => `<article class="metric-card ${type || ""}"><small>${escapeHtml(label)}</small><b>${escapeHtml(value)}</b><span>${escapeHtml(note)}</span></article>`).join("");
  $("#board-count").textContent = m.open_tasks;
  $("#requirement-count").textContent = m.requirements;
}

function issueRow(issue) {
  const type = bucket(issue.status);
  return `<div class="issue-row" id="issue-${escapeHtml(issue.id)}"><span class="issue-key">${escapeHtml(issue.key)}</span><span><b>${escapeHtml(issue.subject)}</b><small>${escapeHtml(issue.project)}</small></span><small>${escapeHtml(issue.assignee)}</small><span class="status-badge ${type}">${escapeHtml(issue.status)}</span></div>`;
}

function renderDashboard() {
  const project = activeProject();
  const requirements = projectRequirements();
  const traceability = projectTraceability();
  const traceCoverage = traceability.length ? Math.round(traceability.filter((row) => row.complete).length / traceability.length * 100) : 100;
  $("#active-project-name").textContent = project?.name || "Projektportfolio";
  $("#active-project-description").textContent = project?.description || "Projektbezogene Tickets, Anforderungen und Nachweise";
  $("#my-issues").innerHTML = projectIssues().filter((issue) => bucket(issue.status) !== "done").slice(0, 5).map(issueRow).join("") || '<p class="empty">Keine offenen Aufgaben.</p>';
  const m = { trace_coverage: traceCoverage };
  $("#trace-gauge").style.setProperty("--value", m.trace_coverage);
  $("#trace-gauge").innerHTML = `<span><b>${m.trace_coverage}%</b><small>abgedeckt</small></span>`;
  const complete = traceability.filter((row) => row.complete).length;
  $("#trace-summary").innerHTML = `<div><b>${complete}</b><small>vollständig</small></div><div><b>${traceability.length - complete}</b><small>offen</small></div>`;
  $("#requirement-preview").innerHTML = requirements.slice(0, 5).map((req) => `<button data-requirement-id="${escapeHtml(req.id)}"><span class="requirement-id">${escapeHtml(req.id)}</span><b>${escapeHtml(req.title)}</b><small>${escapeHtml(req.owner)}</small><span class="status-badge ${req.status === "verified" ? "done" : req.status === "review" ? "review" : "progress"}">${escapeHtml(statusLabel(req.status))}</span></button>`).join("") || '<p class="empty">Für dieses Projekt sind noch keine Anforderungen hinterlegt.</p>';
  $("#work-activity").innerHTML = state.data.activity.slice(0, 6).map((item) => `<div class="activity-item"><b>${escapeHtml(item.message)}</b><small>${escapeHtml(item.actor)} · ${new Date(item.at).toLocaleDateString("de-DE")}</small></div>`).join("");
}

function renderBoard() {
  const labels = { backlog: "Backlog", progress: "In Bearbeitung", review: "Review", done: "Erledigt" };
  const issues = projectIssues();
  $("#kanban").innerHTML = Object.entries(labels).map(([key, label]) => { const rows = issues.filter((issue) => bucket(issue.status) === key); return `<section class="kanban-column"><div class="kanban-head">${label}<span>${rows.length}</span></div>${rows.map((issue) => `<a class="kanban-card" href="${escapeHtml(issue.url || "#")}" ${String(issue.url).startsWith("http") ? 'target="_blank"' : ""}><span class="card-key">${escapeHtml(issue.key)}</span><h3>${escapeHtml(issue.subject)}</h3><div class="kanban-meta"><span class="priority ${/hoch|dringend/i.test(issue.priority) ? "high" : ""}"></span><span>${escapeHtml(issue.assignee)}</span><span>${escapeHtml(issue.due_date || "–")}</span></div></a>`).join("")}</section>`; }).join("");
}

function renderIssues() {
  const query = state.query;
  const issues = projectIssues().filter((item) => !query || `${item.key} ${item.subject} ${item.assignee} ${item.status}`.toLowerCase().includes(query));
  $("#issue-table").innerHTML = `<div class="data-row issue-table-row header"><span>ID</span><span>Aufgabe</span><span>Status</span><span>Verantwortlich</span><span>Fällig</span><span>Fortschritt</span></div>${issues.map((issue) => `<div class="data-row issue-table-row"><a class="issue-key" href="${escapeHtml(issue.url || "#")}" ${String(issue.url).startsWith("http") ? 'target="_blank"' : ""}>${escapeHtml(issue.key)}</a><b>${escapeHtml(issue.subject)}</b><span class="status-badge ${bucket(issue.status)}">${escapeHtml(issue.status)}</span><span>${escapeHtml(issue.assignee)}</span><span>${escapeHtml(issue.due_date || "–")}</span><div class="progress-bar" title="${Number(issue.done_ratio || 0)} %"><i style="width:${Number(issue.done_ratio || 0)}%"></i></div></div>`).join("")}`;
}

function filteredRequirements() {
  return projectRequirements().filter((req) => {
    const filterMatch = state.requirementFilter === "all" || state.requirementFilter === req.status || (state.requirementFilter === "open" && ["draft", "review"].includes(req.status));
    const queryMatch = !state.query || `${req.id} ${req.title} ${req.text} ${req.owner}`.toLowerCase().includes(state.query);
    return filterMatch && queryMatch;
  });
}

function renderRequirements() {
  const requirements = filteredRequirements();
  $("#requirement-filter-count").textContent = `${requirements.length} von ${projectRequirements().length} Anforderungen`;
  $("#requirement-table").innerHTML = `<div class="data-row requirement-table-row header"><span>ID</span><span>Anforderung</span><span>Typ</span><span>Status</span><span>Owner</span><span>Version</span><span>Ticket</span></div>${requirements.map((req) => `<div class="data-row requirement-table-row"><button data-requirement-id="${escapeHtml(req.id)}">${escapeHtml(req.id)}</button><b>${escapeHtml(req.title)}${req.parent_id ? `<small> ↳ ${escapeHtml(req.parent_id)}</small>` : ""}</b><span>${escapeHtml(req.type)}</span><span class="status-badge ${req.status === "verified" ? "done" : req.status === "review" ? "review" : "progress"}">${escapeHtml(statusLabel(req.status))}</span><span>${escapeHtml(req.owner)}</span><span>v${req.version}</span><span class="trace-link">${escapeHtml(req.issue_id || "–")}</span></div>`).join("")}`;
}

function renderTraceability() {
  const rows = projectTraceability();
  const coverage = rows.length ? Math.round(rows.filter((row) => row.complete).length / rows.length * 100) : 100;
  $("#trace-status").textContent = `${coverage}% vollständig`;
  $("#trace-table").innerHTML = `<div class="trace-row header"><span>Anforderung</span><span>Titel</span><span>Umsetzung</span><span>Wiki</span><span>Verifikation</span><span>Status</span></div>${rows.map((row) => `<div class="trace-row"><button data-requirement-id="${escapeHtml(row.requirement_id)}">${escapeHtml(row.requirement_id)}</button><b>${escapeHtml(row.requirement)}</b><span class="trace-link">${escapeHtml(row.issue?.key || "fehlt")}</span><span class="trace-link">${escapeHtml(row.wiki?.title || "fehlt")}</span><span>${escapeHtml(row.verification || "Nachweis fehlt")}</span><span class="${row.complete ? "trace-complete" : "trace-missing"}">${row.complete ? "✓ vollständig" : "! offen"}</span></div>`).join("")}`;
  const relationshipCoverage = state.data.relationship_coverage || [];
  $("#coverage-list").innerHTML = relationshipCoverage.map((row) => `<article class="compact-row"><span class="state-dot ${row.compliant && !row.suspect ? "ok" : "alert"}"></span><span><b>${escapeHtml(row.item_id)} · ${escapeHtml(row.rule)}</b><small>${row.actual} / mindestens ${row.required} Beziehungen${row.suspect ? " · Suspect" : ""}</small></span><strong>${row.compliant && !row.suspect ? "konform" : "prüfen"}</strong></article>`).join("") || '<p class="empty">Keine Coverage-Regeln aktiv.</p>';
  const suspects = state.data.relationships.filter((item) => item.suspect);
  $("#suspect-list").innerHTML = suspects.map((item) => `<article class="compact-row"><span class="state-dot alert"></span><span><b>${escapeHtml(item.source_id)} → ${escapeHtml(item.target_id)}</b><small>${escapeHtml(item.suspect_reason || "Upstream-Objekt wurde geändert")}</small></span><button class="mini-action" data-clear-suspect="${escapeHtml(item.id)}">Bewertet</button></article>`).join("") || '<p class="empty success-empty">✓ Keine ungeprüften Änderungsfolgen.</p>';
}

function renderReviews() {
  const reviews = state.data.reviews || [];
  const open = reviews.filter((item) => ["in_progress", "changes_requested"].includes(item.status));
  const pending = reviews.reduce((total, review) => total + review.participants.filter((item) => item.decision === "pending").length, 0);
  $("#review-count").textContent = open.length;
  $("#review-metrics").innerHTML = [["Aktive Reviews", open.length, "moderiert"], ["Offene Entscheidungen", pending, "Teilnehmer"], ["Kommentare", reviews.reduce((sum, item) => sum + item.comments.length, 0), "auditierbar"], ["Freigegeben", reviews.filter((item) => item.status === "approved").length, "signiert"]].map(([label, value, note]) => `<article class="metric-card"><small>${label}</small><b>${value}</b><span>${note}</span></article>`).join("");
  $("#review-grid").innerHTML = reviews.map((review) => { const complete = review.participants.filter((item) => item.decision !== "pending").length; const progress = review.participants.length ? Math.round(complete / review.participants.length * 100) : 0; return `<article class="review-card"><header><span class="eyebrow">${escapeHtml(review.id)} · REVISION ${review.revision}</span><span class="status-badge ${review.status === "approved" ? "done" : review.status === "changes_requested" ? "review" : "progress"}">${escapeHtml(statusLabel(review.status))}</span></header><h2>${escapeHtml(review.title)}</h2><p>${escapeHtml(review.description)}</p><div class="review-progress"><i style="width:${progress}%"></i></div><div class="review-meta"><span>${review.items.length} Objekte</span><span>${complete}/${review.participants.length} Rückmeldungen</span><span>Frist ${escapeHtml(review.deadline || "–")}</span></div><div class="participant-list">${review.participants.map((person) => `<span><b>${escapeHtml(person.name)}</b><small>${escapeHtml(person.role)} · ${escapeHtml(person.decision)}</small></span>`).join("")}</div><footer><button class="button secondary" data-review-comment="${escapeHtml(review.id)}">Kommentar</button>${review.status !== "approved" ? `<button class="button primary" data-review-approve="${escapeHtml(review.id)}">Elektronisch freigeben</button>` : '<span class="signed-mark">✓ Freigabe abgeschlossen</span>'}</footer></article>`; }).join("") || '<p class="empty">Noch keine Reviews.</p>';
}

function renderTests() {
  const cases = state.data.test_cases || [];
  const executions = (state.data.test_runs || []).flatMap((run) => run.executions || []);
  const executed = executions.filter((item) => !["not_run", "blocked"].includes(item.result));
  const passed = executed.filter((item) => item.result === "passed").length;
  $("#test-metrics").innerHTML = [["Testfälle", cases.length, "versioniert"], ["Ausgeführt", executed.length, `${executions.length} geplant`], ["Bestanden", passed, executed.length ? `${Math.round(passed / executed.length * 100)} %` : "0 %"], ["Fehlgeschlagen", executed.filter((item) => item.result === "failed").length, "mit Defect-Link"]].map(([label, value, note]) => `<article class="metric-card"><small>${label}</small><b>${value}</b><span>${note}</span></article>`).join("");
  $("#test-case-table").innerHTML = `<div class="data-row test-table-row header"><span>ID</span><span>Testfall</span><span>Status</span><span>Owner</span><span>Version</span></div>${cases.map((item) => `<div class="data-row test-table-row"><b class="issue-key">${escapeHtml(item.id)}</b><span><b>${escapeHtml(item.title)}</b><small>${escapeHtml(item.expected_result)}</small></span><span class="status-badge ${item.status === "approved" ? "done" : "progress"}">${escapeHtml(item.status)}</span><span>${escapeHtml(item.owner)}</span><span>v${item.version}</span></div>`).join("")}`;
  $("#test-run-list").innerHTML = (state.data.test_runs || []).map((run) => `<article class="run-card"><header><span><b>${escapeHtml(run.name)}</b><small>${escapeHtml(run.id)} · ${escapeHtml(run.status)}</small></span><strong>${escapeHtml(run.outcome || "open")}</strong></header>${run.executions.map((item) => { const test = cases.find((row) => row.id === item.test_case_id); return `<div class="execution-row"><span class="state-dot ${item.result === "passed" ? "ok" : item.result === "failed" ? "alert" : ""}"></span><span><b>${escapeHtml(test?.title || item.test_case_id)}</b><small>${escapeHtml(item.result)}${item.evidence ? ` · ${escapeHtml(item.evidence)}` : ""}</small></span><span class="execution-actions"><button data-test-result="passed" data-run-id="${escapeHtml(run.id)}" data-test-id="${escapeHtml(item.test_case_id)}">✓</button><button data-test-result="failed" data-run-id="${escapeHtml(run.id)}" data-test-id="${escapeHtml(item.test_case_id)}">×</button></span></div>`; }).join("")}</article>`).join("") || '<p class="empty">Noch kein Testlauf angelegt.</p>';
}

function renderRisks() {
  $("#risk-grid").innerHTML = (state.data.risks || []).map((risk) => `<article class="risk-card severity-${risk.rating >= 15 ? "high" : risk.rating >= 8 ? "medium" : "low"}"><header><span class="risk-score">${risk.rating}</span><span><small>${escapeHtml(risk.id)}</small><b>${escapeHtml(risk.status)}</b></span></header><h2>${escapeHtml(risk.title)}</h2><p>${escapeHtml(risk.description)}</p><dl><div><dt>Wahrscheinlichkeit</dt><dd>${risk.probability}/5</dd></div><div><dt>Auswirkung</dt><dd>${risk.impact}/5</dd></div><div><dt>Owner</dt><dd>${escapeHtml(risk.owner)}</dd></div></dl><footer><b>Maßnahme</b><span>${escapeHtml(risk.mitigation)}</span></footer></article>`).join("") || '<p class="empty">Keine Risiken erfasst.</p>';
}

function renderConfiguration() {
  $("#item-type-list").innerHTML = state.data.item_types.map((item) => `<article class="compact-row"><span class="type-icon">${escapeHtml(item.prefix)}</span><span><b>${escapeHtml(item.name)}</b><small>${escapeHtml(item.key)} · ${item.field_keys.length} eigene Felder</small></span><strong>${item.workflow.length} Status</strong></article>`).join("");
  $("#field-list").innerHTML = state.data.field_definitions.map((item) => `<span title="${escapeHtml(item.applies_to.join(", "))}">${escapeHtml(item.name)} · ${escapeHtml(item.field_type)}${item.required ? " *" : ""}</span>`).join("");
  $("#rule-list").innerHTML = state.data.relationship_rules.map((rule) => `<article class="compact-row"><span class="state-dot ${rule.active ? "ok" : ""}"></span><span><b>${escapeHtml(rule.name)}</b><small>${escapeHtml(rule.upstream_type)} —${escapeHtml(rule.relationship_type)}→ ${escapeHtml(rule.downstream_types.join(", "))}</small></span><strong>${rule.coverage ? `≥ ${rule.min_downstream}` : "optional"}</strong></article>`).join("");
}

function renderBaselines() {
  $("#baseline-grid").innerHTML = projectBaselines().map((baseline) => `<article class="baseline-card"><span class="baseline-icon">◆</span><h2>${escapeHtml(baseline.name)}</h2><p>${escapeHtml(baseline.description || "Eingefrorener Anforderungsstand")}</p><div class="baseline-meta"><span>${escapeHtml(baseline.id)}</span><span>${baseline.items.length} Anforderungen</span><span>${new Date(baseline.created_at).toLocaleDateString("de-DE")}</span></div><button class="mini-action baseline-compare" data-baseline-id="${escapeHtml(baseline.id)}">Mit aktuellem Stand vergleichen</button></article>`).join("") || '<p class="empty">Für dieses Projekt wurde noch keine Baseline eingefroren.</p>';
}

function renderWiki() {
  $("#wiki-grid").innerHTML = projectWiki().map((page) => `<a class="wiki-card" href="${escapeHtml(page.url || "#")}" target="_blank"><span class="wiki-icon">▤</span><h2>${escapeHtml(String(page.title).replaceAll("_", " "))}</h2><p>${escapeHtml(page.project || "Projekt-Wiki")}</p><div class="wiki-meta"><span>Version ${escapeHtml(page.version || "–")}</span><span>In Redmine öffnen ↗</span></div></a>`).join("") || '<p class="empty">Für dieses Projekt sind noch keine Wiki-Seiten hinterlegt.</p>';
}

function renderSelects() {
  const select = $("#project-select");
  select.innerHTML = state.data.projects.map((project) => `<option value="${escapeHtml(projectKey(project))}">${escapeHtml(project.name)}</option>`).join("");
  if (!state.data.projects.some((project) => projectKey(project) === state.projectKey)) state.projectKey = projectKey(state.data.projects[0]);
  select.value = state.projectKey;
  const options = state.data.requirements.map((req) => `<option value="${escapeHtml(req.id)}">${escapeHtml(req.id)} · ${escapeHtml(req.title)}</option>`).join("");
  $("#issue-requirement").innerHTML = `<option value="">Keine Verknüpfung</option>${options}`;
  $("#requirement-parent").innerHTML = `<option value="">Keine</option>${options}`;
  $("#test-requirement").innerHTML = options;
  $("#risk-requirement").innerHTML = options;
  const requirementTypes = state.data.item_types.filter((item) => !["TestCase", "Risk"].includes(item.key));
  const typeOptions = requirementTypes.map((item) => `<option value="${escapeHtml(item.key)}">${escapeHtml(item.name)}</option>`).join("");
  $("#requirement-type").innerHTML = typeOptions;
  $("#field-item-type").innerHTML = typeOptions;
  const ruleTypeOptions = state.data.item_types.map((item) => `<option value="${escapeHtml(item.key)}">${escapeHtml(item.name)}</option>`).join("");
  $("#rule-upstream").innerHTML = `<option value="Requirement">Alle Anforderungstypen</option>${ruleTypeOptions}`;
  $("#rule-downstream").innerHTML = ruleTypeOptions;
  const relationshipTypes = state.data.relationship_types.map((item) => `<option value="${escapeHtml(item.key)}">${escapeHtml(item.name)} / ${escapeHtml(item.reverse_name)}</option>`).join("");
  $("#rule-relationship-type").innerHTML = relationshipTypes;
  $("#relationship-type").innerHTML = relationshipTypes;
  const allItems = [...state.data.requirements, ...state.data.test_cases, ...state.data.risks];
  const itemOptions = allItems.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.id)} · ${escapeHtml(item.title)}</option>`).join("");
  $("#relationship-source").innerHTML = itemOptions;
  $("#relationship-target").innerHTML = itemOptions;
  $("#review-items").innerHTML = projectRequirements().map((item) => `<label><input type="checkbox" value="${escapeHtml(item.id)}" checked /> <span><b>${escapeHtml(item.id)}</b>${escapeHtml(item.title)}</span></label>`).join("");
  $("#test-plan-cases").innerHTML = state.data.test_cases.map((item) => `<label><input type="checkbox" value="${escapeHtml(item.id)}" checked /> <span><b>${escapeHtml(item.id)}</b>${escapeHtml(item.title)}</span></label>`).join("") || '<p class="empty">Zuerst einen Testfall anlegen.</p>';
  renderCustomFields();
}

function renderCustomFields() {
  const type = $("#requirement-type").value;
  const itemType = state.data.item_types.find((item) => item.key === type);
  const fields = (itemType?.field_keys || []).map((key) => state.data.field_definitions.find((item) => item.key === key)).filter(Boolean);
  $("#custom-fields-container").innerHTML = fields.length ? `<span class="eyebrow">EIGENE FELDER</span><div class="form-grid">${fields.map((field) => { const required = field.required ? "required" : ""; if (field.field_type === "select" || field.field_type === "multi_select") return `<label>${escapeHtml(field.name)}${field.required ? " *" : ""}<select data-custom-field="${escapeHtml(field.key)}" ${required} ${field.field_type === "multi_select" ? "multiple" : ""}>${field.required ? "" : '<option value="">–</option>'}${field.options.map((option) => `<option>${escapeHtml(option)}</option>`).join("")}</select></label>`; if (field.field_type === "flag") return `<label class="check-label"><input type="checkbox" data-custom-field="${escapeHtml(field.key)}" /> ${escapeHtml(field.name)}</label>`; return `<label>${escapeHtml(field.name)}${field.required ? " *" : ""}<input data-custom-field="${escapeHtml(field.key)}" type="${field.field_type === "integer" || field.field_type === "decimal" ? "number" : field.field_type === "date" ? "date" : field.field_type === "url" ? "url" : "text"}" ${required} /></label>`; }).join("")}</div>` : "";
}

function renderAll() { renderIdentity(); renderMetrics(); renderDashboard(); renderBoard(); renderIssues(); renderRequirements(); renderTraceability(); renderReviews(); renderBaselines(); renderTests(); renderRisks(); renderWiki(); renderConfiguration(); renderSelects(); bindRequirementButtons(); }

function bindRequirementButtons() { $$('[data-requirement-id]').forEach((button) => button.addEventListener("click", () => showRequirement(button.dataset.requirementId))); }

function showRequirement(id) {
  const req = state.data.requirements.find((item) => item.id === id);
  if (!req) return;
  const custom = Object.entries(req.custom_fields || {}).map(([key, value]) => { const definition = state.data.field_definitions.find((item) => item.key === key); return `<div><small>${escapeHtml(definition?.name || key)}</small><b>${escapeHtml(Array.isArray(value) ? value.join(", ") : value)}</b></div>`; }).join("");
  const links = state.data.relationships.filter((item) => item.source_id === id || item.target_id === id);
  $("#requirement-detail-content").innerHTML = `<article class="detail-card"><div class="detail-top"><div><span class="eyebrow">${escapeHtml(req.id)} · VERSION ${req.version}</span><h2>${escapeHtml(req.title)}</h2><span class="status-badge ${req.status === "verified" ? "done" : req.status === "review" ? "review" : "progress"}">${escapeHtml(statusLabel(req.status))}</span></div><button class="detail-close" aria-label="Schließen">×</button></div><p class="detail-text">${escapeHtml(req.text)}</p><div class="detail-grid"><div><small>Typ / Priorität</small><b>${escapeHtml(req.type)} · ${escapeHtml(req.priority)}</b></div><div><small>Owner</small><b>${escapeHtml(req.owner)}</b></div><div><small>Übergeordnet</small><b>${escapeHtml(req.parent_id || "–")}</b></div><div><small>Redmine-Ticket</small><b>${escapeHtml(req.issue_id || "nicht verknüpft")}</b></div><div><small>Wiki</small><b>${escapeHtml(req.wiki_title || "nicht verknüpft")}</b></div><div><small>Verifikation</small><b>${escapeHtml(req.verification || "Nachweis offen")}</b></div>${custom}</div><p class="dialog-note"><b>Akzeptanzkriterium:</b> ${escapeHtml(req.acceptance_criteria || "Noch nicht definiert")}</p><section class="detail-section"><h3>Beziehungen & Change Impact</h3>${links.map((item) => `<div class="relation-line ${item.suspect ? "suspect" : ""}"><span>${escapeHtml(item.source_id)} —${escapeHtml(item.relationship_type)}→ ${escapeHtml(item.target_id)}</span><b>${item.suspect ? "! Suspect" : "✓ gültig"}</b></div>`).join("") || '<p class="empty">Keine Beziehungen.</p>'}</section><section class="detail-section"><h3>Versionshistorie</h3>${(req.history || []).slice(0, 6).map((item) => `<div class="history-line"><b>v${item.version} · ${escapeHtml(item.note)}</b><small>${escapeHtml(item.actor)} · ${new Date(item.at).toLocaleString("de-DE")}</small></div>`).join("")}</section><div class="detail-actions"><button class="button secondary" data-status="review">In Review</button><button class="button secondary" data-status="approved">Freigeben</button><button class="button secondary" data-branch="${escapeHtml(req.id)}">Variante ableiten</button><button class="button primary" data-status="verified">Als verifiziert markieren</button></div></article>`;
  const dialog = $("#requirement-detail");
  dialog.showModal();
  dialog.querySelector(".detail-close").addEventListener("click", () => dialog.close());
  dialog.querySelectorAll("[data-status]").forEach((button) => button.addEventListener("click", async () => { await mutateRequirement(req.id, { status: button.dataset.status, change_note: `Status auf ${button.dataset.status} gesetzt` }); dialog.close(); }));
  dialog.querySelector("[data-branch]").addEventListener("click", async () => { const variant = window.prompt("Name der Produktvariante", "SCU-100 Marine"); if (!variant) return; try { const branch = await api(`/api/work/requirements/${encodeURIComponent(req.id)}/branch`, { method: "POST", body: JSON.stringify({ variant }) }); dialog.close(); toast(`${branch.id} als Variante abgeleitet`); await load(); } catch (error) { toast(error.message, true); } });
}

async function mutateRequirement(id, values) {
  try { await api(`/api/work/requirements/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(values) }); toast(`${id} aktualisiert`); await load(); }
  catch (error) { toast(error.message, true); }
}

function openView(name) {
  $$(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${name}`));
  $$(".work-nav button[data-view]").forEach((button) => button.classList.toggle("active", button.dataset.view === name));
  const params = new URLSearchParams(location.search);
  params.set("view", name);
  history.replaceState(null, "", `${location.pathname}?${params}`);
}

async function load() {
  try { state.data = await api("/api/work/dashboard"); renderAll(); }
  catch (error) { toast(error.message, true); }
}

$("#issue-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget)); if (!values.due_date) delete values.due_date; if (!values.requirement_id) delete values.requirement_id;
  try { const issue = await api("/api/work/issues", { method: "POST", body: JSON.stringify(values) }); $("#issue-dialog").close(); event.currentTarget.reset(); toast(`Aufgabe ${issue.key} angelegt`); await load(); }
  catch (error) { toast(error.message, true); }
});
$("#requirement-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget)); if (!values.parent_id) delete values.parent_id;
  values.custom_fields = {}; $$('[data-custom-field]').forEach((field) => { let value = field.type === "checkbox" ? field.checked : field.multiple ? [...field.selectedOptions].map((item) => item.value) : field.value; if (field.type === "number" && value !== "") value = Number(value); if (value !== "" && (!Array.isArray(value) || value.length)) values.custom_fields[field.dataset.customField] = value; });
  try { const req = await api("/api/work/requirements", { method: "POST", body: JSON.stringify(values) }); $("#requirement-dialog").close(); event.currentTarget.reset(); toast(`${req.id} angelegt`); await load(); }
  catch (error) { toast(error.message, true); }
});
$("#baseline-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget)); values.requirement_ids = filteredRequirements().map((req) => req.id);
  try { const baseline = await api("/api/work/baselines", { method: "POST", body: JSON.stringify(values) }); $("#baseline-dialog").close(); toast(`${baseline.id} eingefroren`); await load(); }
  catch (error) { toast(error.message, true); }
});

$("#review-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const raw = Object.fromEntries(new FormData(event.currentTarget)); const item_ids = $$("#review-items input:checked").map((item) => item.value); const participants = [{ name: raw.approver, role: "approver" }]; if (raw.reviewer) participants.push({ name: raw.reviewer, role: "reviewer" });
  const values = { title: raw.title, description: raw.description, item_ids, participants, require_signature: raw.require_signature === "on", allow_comments_in_item: true }; if (raw.deadline) values.deadline = raw.deadline;
  try { const review = await api("/api/work/reviews", { method: "POST", body: JSON.stringify(values) }); $("#review-dialog").close(); toast(`${review.id} gestartet`); await load(); } catch (error) { toast(error.message, true); }
});

$("#test-case-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const raw = Object.fromEntries(new FormData(event.currentTarget)); const lines = raw.steps.split(/\n+/).map((item) => item.trim()).filter(Boolean); const values = { title: raw.title, owner: raw.owner, preconditions: raw.preconditions, expected_result: raw.expected_result, requirement_ids: raw.requirement_id ? [raw.requirement_id] : [], status: "draft", steps: lines.map((action, index) => ({ order: index + 1, action, expected: index === lines.length - 1 ? raw.expected_result : "Schritt erfolgreich" })) };
  try { const item = await api("/api/work/tests/cases", { method: "POST", body: JSON.stringify(values) }); $("#test-case-dialog").close(); event.currentTarget.reset(); toast(`${item.id} angelegt`); await load(); } catch (error) { toast(error.message, true); }
});

$("#test-plan-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const raw = Object.fromEntries(new FormData(event.currentTarget)); const values = { name: raw.name, description: raw.description, owner: raw.owner, test_case_ids: $$("#test-plan-cases input:checked").map((item) => item.value) };
  try { const plan = await api("/api/work/tests/plans", { method: "POST", body: JSON.stringify(values) }); $("#test-plan-dialog").close(); toast(`${plan.id} und ${plan.run_id} angelegt`); await load(); } catch (error) { toast(error.message, true); }
});

$("#risk-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const raw = Object.fromEntries(new FormData(event.currentTarget)); const values = { ...raw, probability: Number(raw.probability), impact: Number(raw.impact), requirement_ids: raw.requirement_id ? [raw.requirement_id] : [] }; delete values.requirement_id;
  try { const risk = await api("/api/work/risks", { method: "POST", body: JSON.stringify(values) }); $("#risk-dialog").close(); event.currentTarget.reset(); toast(`${risk.id} angelegt`); await load(); } catch (error) { toast(error.message, true); }
});

$("#field-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const raw = Object.fromEntries(new FormData(event.currentTarget)); const values = { ...raw, required: raw.required === "on", applies_to: [raw.applies_to], options: raw.options.split(",").map((item) => item.trim()).filter(Boolean) };
  try { const field = await api("/api/work/admin/fields", { method: "POST", body: JSON.stringify(values) }); $("#field-dialog").close(); event.currentTarget.reset(); toast(`${field.name} angelegt`); await load(); } catch (error) { toast(error.message, true); }
});

$("#item-type-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget));
  try { const item = await api("/api/work/admin/item-types", { method: "POST", body: JSON.stringify(values) }); $("#item-type-dialog").close(); event.currentTarget.reset(); toast(`${item.name} angelegt`); await load(); } catch (error) { toast(error.message, true); }
});

$("#relationship-type-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget));
  try { const item = await api("/api/work/admin/relationship-types", { method: "POST", body: JSON.stringify(values) }); $("#relationship-type-dialog").close(); event.currentTarget.reset(); toast(`${item.name} angelegt`); await load(); } catch (error) { toast(error.message, true); }
});

$("#relationship-rule-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const raw = Object.fromEntries(new FormData(event.currentTarget)); const values = { name: raw.name, upstream_type: raw.upstream_type, downstream_types: [raw.downstream_type], relationship_type: raw.relationship_type, min_downstream: Number(raw.min_downstream), coverage: raw.coverage === "on", exclusive: false };
  try { const rule = await api("/api/work/admin/relationship-rules", { method: "POST", body: JSON.stringify(values) }); $("#relationship-rule-dialog").close(); event.currentTarget.reset(); toast(`${rule.name} angelegt`); await load(); } catch (error) { toast(error.message, true); }
});

$("#relationship-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget));
  try { const relation = await api("/api/work/relationships", { method: "POST", body: JSON.stringify(values) }); $("#relationship-dialog").close(); toast(`${relation.id} angelegt`); await load(); } catch (error) { toast(error.message, true); }
});

$$('[data-view]').forEach((button) => button.addEventListener("click", () => openView(button.dataset.view)));
$$('[data-open-view]').forEach((button) => button.addEventListener("click", () => openView(button.dataset.openView)));
$$('[data-new-issue],#new-issue-top').forEach((button) => button.addEventListener("click", () => $("#issue-dialog").showModal()));
$$('[data-new-requirement],#new-requirement-top').forEach((button) => button.addEventListener("click", () => $("#requirement-dialog").showModal()));
$("#new-baseline").addEventListener("click", () => $("#baseline-dialog").showModal());
$("#new-review").addEventListener("click", () => { const identity = state.data.user; $("#review-form [name=approver]").value = identity?.name || identity?.username || "Demo Benutzer"; $("#review-dialog").showModal(); });
$("#new-test-case").addEventListener("click", () => $("#test-case-dialog").showModal());
$("#new-test-plan").addEventListener("click", () => $("#test-plan-dialog").showModal());
$("#new-risk").addEventListener("click", () => $("#risk-dialog").showModal());
$("#new-field").addEventListener("click", () => $("#field-dialog").showModal());
$("#new-item-type").addEventListener("click", () => $("#item-type-dialog").showModal());
$("#new-relationship-type").addEventListener("click", () => $("#relationship-type-dialog").showModal());
$("#new-relationship-rule").addEventListener("click", () => $("#relationship-rule-dialog").showModal());
$("#new-relationship").addEventListener("click", () => $("#relationship-dialog").showModal());
$("#requirement-type").addEventListener("change", renderCustomFields);
$("#refresh").addEventListener("click", load);
$("#project-select").addEventListener("change", (event) => { state.projectKey = event.target.value; renderAll(); });
$$('[data-req-filter]').forEach((button) => button.addEventListener("click", () => { state.requirementFilter = button.dataset.reqFilter; $$('[data-req-filter]').forEach((item) => item.classList.toggle("active", item === button)); renderRequirements(); bindRequirementButtons(); }));
$("#work-search").addEventListener("input", (event) => { state.query = event.target.value.trim().toLowerCase(); renderIssues(); renderRequirements(); bindRequirementButtons(); });

document.addEventListener("click", async (event) => {
  const clear = event.target.closest("[data-clear-suspect]");
  const approve = event.target.closest("[data-review-approve]");
  const comment = event.target.closest("[data-review-comment]");
  const test = event.target.closest("[data-test-result]");
  const baseline = event.target.closest("[data-baseline-id]");
  try {
    if (clear) { await api(`/api/work/relationships/${encodeURIComponent(clear.dataset.clearSuspect)}/clear-suspect`, { method: "POST" }); toast("Änderungsfolge bewertet"); await load(); }
    if (approve) { const review = state.data.reviews.find((item) => item.id === approve.dataset.reviewApprove); const identityName = state.data.user?.name || state.data.user?.username || "Demo Benutzer"; const person = review?.participants.find((item) => item.role === "approver" && item.name.toLowerCase() === identityName.toLowerCase()); if (!person) throw new Error("Die angemeldete Person ist in diesem Review kein Approver"); await api(`/api/work/reviews/${encodeURIComponent(review.id)}/decisions`, { method: "POST", body: JSON.stringify({ participant: person.name, decision: "approved", signature: `Elektronisch bestätigt durch ${person.name}`, note: "Freigabe über FLOWWORK Review Center" }) }); toast(`${review.id} freigegeben`); await load(); }
    if (comment) { const text = window.prompt("Review-Kommentar"); if (text) { const review = state.data.reviews.find((item) => item.id === comment.dataset.reviewComment); await api(`/api/work/reviews/${encodeURIComponent(review.id)}/comments`, { method: "POST", body: JSON.stringify({ item_id: review.items[0]?.item_id, text }) }); toast("Kommentar gespeichert"); await load(); } }
    if (test) { const evidence = test.dataset.testResult === "passed" ? `EVIDENCE-${test.dataset.testId}-${new Date().toISOString().slice(0, 10)}` : null; await api(`/api/work/tests/runs/${encodeURIComponent(test.dataset.runId)}/cases/${encodeURIComponent(test.dataset.testId)}`, { method: "POST", body: JSON.stringify({ result: test.dataset.testResult, evidence, note: "Ausführung über FLOWWORK" }) }); toast(`${test.dataset.testId}: ${test.dataset.testResult}`); await load(); }
    if (baseline) { const result = await api(`/api/work/baselines/${encodeURIComponent(baseline.dataset.baselineId)}/compare`); const changed = result.comparison.filter((item) => item.changed).length; toast(`${result.baseline.id}: ${changed} geändert, ${result.added.length} neu`); }
  } catch (error) { toast(error.message, true); }
});

const params = new URLSearchParams(location.search);
openView(params.get("view") || "dashboard");
load().then(() => { if (params.get("action") === "new-ticket") $("#issue-dialog").showModal(); if (params.get("action") === "new") $("#requirement-dialog").showModal(); });
