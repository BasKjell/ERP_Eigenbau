const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const euro = (value, digits = 0) => new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: digits }).format(value || 0);
const number = (value) => new Intl.NumberFormat("de-DE").format(value || 0);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
let state;

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  if (!response.ok) { const detail = await response.json().catch(() => ({ detail: `HTTP ${response.status}` })); throw new Error(detail.detail || `HTTP ${response.status}`); }
  return response.json();
}

function kpi(label, value, sub, tone = "") { return `<article class="kpi ${tone}"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong><span>${escapeHtml(sub)}</span></article>`; }
function status(value) { return `<span class="status ${escapeHtml(value)}">${escapeHtml(({ on_track: "Im Plan", at_risk: "Gefährdet", pending: "Offen", approved: "Freigegeben", rejected: "Abgelehnt", overdue: "Überfällig" })[value] || value)}</span>`; }

function render(data) {
  state = data;
  $("#as-of").textContent = `Stand ${new Date(`${data.as_of}T12:00:00`).toLocaleDateString("de-DE")}`;
  const m = data.metrics;
  $("#executive-kpis").innerHTML = [
    kpi("Aufträge in Fertigung", euro(m.production_order_value), `${euro(m.production_weighted_revenue)} gewichtet`, "good"),
    kpi("Auftragsbestand", euro(m.backlog_value), `${euro(m.weighted_backlog)} wahrscheinlichkeitsgewichtet`),
    kpi("Erwartete Marge", euro(m.expected_gross_margin), "nach Estimate-at-Completion", m.expected_gross_margin > 0 ? "good" : "bad"),
    kpi("Liquidität", euro(m.cash_balance), `Minimum Forecast ${euro(m.minimum_forecast_cash)}`),
    kpi("Überfällige Forderungen", euro(m.overdue_receivables), `${m.overdue_receivables_count} offene Position(en)`, m.overdue_receivables ? "warn" : "good"),
  ].join("");
  renderRevenueChart(); renderRisks(); renderOrders(); renderProjects(); renderCash(); renderInnovation(); renderOperations(); renderIntegrations();
}

function renderRevenueChart() {
  const max = Math.max(...state.revenue_by_month.map((row) => row.order_value), 1);
  $("#revenue-chart").innerHTML = state.revenue_by_month.map((row) => `<div class="bar-group"><span class="bar-value">${euro(row.weighted_revenue / 1000)}k</span><i class="bar" style="height:${Math.max(4, row.weighted_revenue / max * 100)}%" title="Gewichtet ${euro(row.weighted_revenue)} / Brutto ${euro(row.order_value)}"></i><small>${escapeHtml(row.month.slice(5))}/${escapeHtml(row.month.slice(2, 4))}</small></div>`).join("");
}

function renderRisks() {
  const riskyOrders = state.orders.filter((item) => item.risk === "at_risk");
  const overBudgets = state.budgets.filter((item) => item.variance < 0);
  const rows = [
    ...riskyOrders.map((item) => ({ tone: "bad", title: `${item.id} · ${item.product}`, text: `${euro(item.order_value)} · ${item.stage} · ${item.expected_invoice_date}` })),
    ...overBudgets.map((item) => ({ tone: "", title: `${item.name} über Forecast`, text: `${euro(Math.abs(item.variance))} oberhalb Budget` })),
    { tone: "good", title: "Liquidität bleibt positiv", text: `Tiefpunkt im Forecast: ${euro(state.metrics.minimum_forecast_cash)}` },
  ];
  $("#risk-list").innerHTML = rows.slice(0, 5).map((row) => `<div class="risk-item ${row.tone}"><b>${escapeHtml(row.title)}</b><small>${escapeHtml(row.text)}</small></div>`).join("");
}

function orderTable(rows, compact = false) {
  return `<table class="data-grid"><thead><tr><th>Auftrag / Projekt</th><th>Kunde & Produkt</th><th>Phase</th><th>Fortschritt</th><th>Wert / gewichtet</th><th>EAC-Marge</th><th>Rechnung</th><th>Risiko</th></tr></thead><tbody>${rows.map((item) => `<tr><td><strong>${escapeHtml(item.id)}</strong><small>${escapeHtml(item.project_id)}</small></td><td>${escapeHtml(item.customer)}<small>${escapeHtml(item.product)}</small></td><td>${escapeHtml(item.stage)}</td><td><div class="progress"><i style="width:${item.progress}%"></i></div><small>${item.progress}%</small></td><td><strong>${euro(item.order_value)}</strong><small>${euro(item.weighted_revenue)} gewichtet</small></td><td><strong>${euro(item.expected_margin)}</strong><small>${item.expected_margin_percent}%</small></td><td>${escapeHtml(item.expected_invoice_date)}</td><td>${status(item.risk)}</td></tr>`).join("")}</tbody></table>`;
}

function renderOrders() {
  $("#executive-orders").innerHTML = orderTable(state.orders.filter((item) => ["Produktion", "Endprüfung"].includes(item.stage)));
  $("#orders-table").innerHTML = orderTable(state.orders);
  $("#revenue-kpis").innerHTML = [kpi("Backlog brutto", euro(state.metrics.backlog_value), `${state.orders.length} Chancen/Aufträge`), kpi("Backlog gewichtet", euro(state.metrics.weighted_backlog), "Probability × Order Value", "good"), kpi("In Produktion", euro(state.metrics.production_order_value), "inkl. Endprüfung"), kpi("Gewichtete Produktion", euro(state.metrics.production_weighted_revenue), "erwarteter Umsatz", "good")].join("");
}

function renderProjects() {
  $("#projects-table").innerHTML = `<table class="data-grid"><thead><tr><th>Kommission</th><th>Kunde / Produkt</th><th>Umsatz</th><th>Istkosten</th><th>EAC Kosten</th><th>Erwartete Marge</th><th>Fortschritt</th><th>Risiko</th></tr></thead><tbody>${state.project_profitability.map((item) => `<tr><td><strong>${escapeHtml(item.project_id)}</strong><small>${escapeHtml(item.order_id)}</small></td><td>${escapeHtml(item.customer)}<small>${escapeHtml(item.product)}</small></td><td>${euro(item.revenue)}</td><td>${euro(item.actual_cost)}</td><td>${euro(item.forecast_cost)}</td><td><strong>${euro(item.expected_margin)}</strong><small>${item.expected_margin_percent}%</small></td><td>${item.progress}%</td><td>${status(item.risk)}</td></tr>`).join("")}</tbody></table>`;
}

function renderCash() {
  const max = Math.max(...state.cash_forecast.map((item) => item.closing_balance), 1);
  const currentMonth = state.as_of.slice(0, 7);
  $("#cash-kpis").innerHTML = [kpi("Kontostand", euro(state.metrics.cash_balance), `Stand ${state.as_of}`, "good"), kpi("Forecast-Tiefpunkt", euro(state.metrics.minimum_forecast_cash), "24 Monate"), kpi("Forderungen überfällig", euro(state.metrics.overdue_receivables), `${state.metrics.overdue_receivables_count} Posten`, "warn"), kpi("Offene Posten", euro(state.open_items.reduce((sum, item) => sum + item.amount, 0)), "AR und AP")].join("");
  $("#cash-chart").innerHTML = state.cash_forecast.map((item, index) => { const marker = item.month === currentMonth; const showLabel = marker || index % 3 === 0 || index === state.cash_forecast.length - 1; return `<div class="cash-column ${item.month > currentMonth ? "forecast" : "history"}${marker ? " current" : ""}" title="${escapeHtml(item.month)} · Bestand ${euro(item.closing_balance)} · Ein ${euro(item.inflow)} · Aus ${euro(item.outflow)}"><span class="cash-value">${showLabel ? `${number(item.closing_balance / 1000)}k` : ""}</span><i class="cash-bar" style="height:${item.closing_balance / max * 84}%"></i><small>${showLabel ? `${escapeHtml(item.month.slice(5))}/${escapeHtml(item.month.slice(2, 4))}` : ""}</small></div>`; }).join("");
  $("#open-items").innerHTML = state.open_items.map((item) => `<div class="mini-row"><span><b>${escapeHtml(item.document)} · ${item.type}</b><small>${escapeHtml(item.partner)} · fällig ${escapeHtml(item.due_date)}</small></span><span class="amount">${euro(item.amount)}<small>${status(item.status)}</small></span></div>`).join("");
}

function renderInnovation() {
  $("#rd-list").innerHTML = state.rd_projects.map((item) => `<div class="detail-row"><span><b>${escapeHtml(item.name)}</b><small>${escapeHtml(item.id)} · Ziel ${escapeHtml(item.release_target)}</small></span><span class="amount">${euro(item.forecast_cost)}<small>${item.capitalization_candidate ? "Aktivierungskandidat · Prüfung" : "Aufwand · Forschung"}</small></span></div>`).join("");
  $("#subscription-list").innerHTML = state.subscriptions.map((item) => `<div class="detail-row"><span><b>${escapeHtml(item.product)}</b><small>${escapeHtml(item.vendor)} · Verlängerung ${escapeHtml(item.renewal_date)}</small></span><span class="amount">${euro(item.annual_value)}<small>pro Jahr · ${escapeHtml(item.allocation)}</small></span></div>`).join("");
  $("#quality-list").innerHTML = state.quality_costs.map((item) => `<div class="detail-row"><span><b>${escapeHtml(item.category)}</b><small>${escapeHtml(item.project_id)} · ${escapeHtml(item.period)}</small></span><span class="amount">${euro(item.amount)}</span></div>`).join("");
  $("#warranty-list").innerHTML = state.warranty_cases.map((item) => `<div class="detail-row"><span><b>${escapeHtml(item.id)} · ${escapeHtml(item.product)}</b><small>${escapeHtml(item.customer)} · ${escapeHtml(item.root_cause)}</small></span><span class="amount">${euro(item.amount)}<small>Reserve ${euro(item.reserve)}</small></span></div>`).join("");
}

function renderOperations() {
  $("#budget-list").innerHTML = state.budgets.map((item) => `<div class="budget-row"><span><b>${escapeHtml(item.name)}</b><small>${euro(item.actual)} Ist · ${euro(item.budget)} Budget</small></span><div><div class="budget-meter"><i class="${item.usage_percent > 100 ? "over" : ""}" style="width:${Math.min(item.usage_percent, 100)}%"></i></div><small>${item.usage_percent}% · Varianz ${euro(item.variance)}</small></div><span><input data-budget-value="${escapeHtml(item.id)}" type="number" value="${item.forecast}" /><button data-budget-save="${escapeHtml(item.id)}">Speichern</button></span></div>`).join("");
  $("#expense-list").innerHTML = state.expenses.length ? state.expenses.map((item) => `<div class="detail-row"><span><b>${escapeHtml(item.description)}</b><small>${escapeHtml(item.id)} · ${escapeHtml(item.cost_center)} · ${escapeHtml(item.submitted_by)}</small></span><span class="amount">${euro(item.amount)}<small>${status(item.status)}${item.status === "pending" ? `<button data-expense-approve="${escapeHtml(item.id)}">Freigeben</button>` : ""}</small></span></div>`).join("") : `<div class="detail-row"><span><b>Keine Auslagen</b><small>Neue Auslage über den Button oben erfassen.</small></span></div>`;
  $("#asset-table").innerHTML = `<table class="data-grid"><thead><tr><th>Anlage</th><th>Klasse</th><th>Kostenstelle</th><th>Anschaffung</th><th>Wert</th><th>Monatl. AfA</th><th>Quelle</th></tr></thead><tbody>${state.assets.map((item) => `<tr><td><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.id)}</small></td><td>${escapeHtml(item.asset_class)}</td><td>${escapeHtml(item.cost_center)}</td><td>${escapeHtml(item.acquisition_date)}</td><td>${euro(item.acquisition_cost)}</td><td>${euro(item.monthly_depreciation, 2)}</td><td>${escapeHtml(item.source)}</td></tr>`).join("")}</tbody></table>`;
  $$('[data-budget-save]').forEach((button) => button.addEventListener("click", () => saveBudget(button.dataset.budgetSave)));
  $$('[data-expense-approve]').forEach((button) => button.addEventListener("click", () => approveExpense(button.dataset.expenseApprove)));
}

function renderIntegrations() {
  const cards = [
    { id: "datev", label: "DATEV Buchungsstapel", help: "Periode prüfen und simulierten Buchungsstapel erzeugen.", key: state.as_of.slice(0, 7), keyLabel: "Periode (YYYY-MM)" },
    { id: "bank", label: "SEPA / Bank", help: "Fällige Kreditorenposten in einem simulierten Zahllauf prüfen.", key: "2026-11-30", keyLabel: "Fällig bis" },
    { id: "e_invoice", label: "XRechnung / ZUGFeRD", help: "Struktur- und Pflichtfeldprüfung ohne externen Versand.", key: "INV-DEMO-2026-001", keyLabel: "Rechnungsreferenz" },
  ];
  $("#adapter-grid").innerHTML = cards.map((item) => `<article class="adapter" data-adapter="${item.id}"><header><h2>${escapeHtml(item.label)}</h2><span class="test-tag">TEST ONLY</span></header><p>${escapeHtml(item.help)}</p><label>${escapeHtml(item.keyLabel)}<input data-adapter-key value="${escapeHtml(item.key)}" /></label>${item.id === "e_invoice" ? '<label>Format<select data-invoice-format><option value="xrechnung">XRechnung</option><option value="zugferd">ZUGFeRD</option></select></label>' : ""}<button class="primary" data-adapter-run="${item.id}">${item.id === "e_invoice" ? "Testvalidierung starten" : "Vorschau erzeugen"}</button><div class="adapter-result warn">Keine externe Verbindung konfiguriert.</div></article>`).join("");
  renderRunList();
  $$('[data-adapter-run]').forEach((button) => button.addEventListener("click", () => runAdapter(button.dataset.adapterRun)));
}

function renderRunList() {
  $("#run-list").innerHTML = state.integration_runs.length ? state.integration_runs.map((item) => `<div class="detail-row"><span><b>${escapeHtml(item.adapter_label)}</b><small>${escapeHtml(item.id)} · ${escapeHtml(item.created_at)} · ${escapeHtml(item.created_by)}</small></span><span class="amount">${escapeHtml(item.status)}<small>TEST · nicht übertragen</small></span></div>`).join("") : `<div class="detail-row"><span><b>Noch keine Testläufe</b><small>Starte oben eine Preview oder Validierung.</small></span></div>`;
}

async function saveBudget(id) { try { const forecast = Number($(`[data-budget-value="${id}"]`).value); await api(`/api/finance/budgets/${encodeURIComponent(id)}/forecast`, { method: "POST", body: JSON.stringify({ actor_id: "demo36", forecast }) }); await load(); toast("Forecast aktualisiert"); } catch (error) { toast(error.message, true); } }
async function approveExpense(id) { try { await api(`/api/finance/expenses/${encodeURIComponent(id)}/decision`, { method: "POST", body: JSON.stringify({ actor_id: "demo40", decision: "approved", comment: "Sachlich und rechnerisch geprüft" }) }); await load(); toast("Auslage freigegeben"); } catch (error) { toast(error.message, true); } }

async function runAdapter(id) {
  const card = $(`[data-adapter="${id}"]`); const key = card.querySelector("[data-adapter-key]").value; const resultBox = card.querySelector(".adapter-result");
  try {
    if (id === "e_invoice") { const result = await api("/api/finance/integrations/e-invoice/validate", { method: "POST", body: JSON.stringify({ actor_id: "demo36", invoice_id: key, invoice_format: card.querySelector("[data-invoice-format]").value }) }); resultBox.className = "adapter-result"; resultBox.textContent = `${result.status}: ${result.notice}`; state = await api("/api/finance/dashboard"); renderRunList(); }
    else { const path = id === "datev" ? "/api/finance/integrations/datev" : "/api/finance/integrations/bank"; const preview = await api(path, { method: "POST", body: JSON.stringify({ actor_id: "demo36", key, confirm: false }) }); resultBox.className = "adapter-result"; resultBox.innerHTML = `${preview.record_count} Datensätze · ${euro(preview.amount)}<br><b>Nur Test:</b> keine Übertragung. <button class="text-button" data-confirm-run>Testlauf bestätigen</button>`; resultBox.querySelector("[data-confirm-run]").addEventListener("click", async () => { const run = await api(path, { method: "POST", body: JSON.stringify({ actor_id: "demo36", key, confirm: true, confirmation_token: preview.confirmation_token }) }); resultBox.textContent = `${run.external_reference}: simuliert, nicht übertragen.`; state = await api("/api/finance/dashboard"); renderRunList(); toast("Testlauf bestätigt – keine externe Übertragung"); }); }
    toast("Testadapter erfolgreich ausgeführt");
  } catch (error) { resultBox.className = "adapter-result warn"; resultBox.textContent = error.message; toast(error.message, true); }
}

async function load(renderPage = true) { const data = await api("/api/finance/dashboard"); if (renderPage) render(data); else { state = data; renderOperations(); renderIntegrations(); } }
function toast(message, error = false) { const element = $("#toast"); element.textContent = message; element.className = `toast show${error ? " error" : ""}`; clearTimeout(window.flowfinToast); window.flowfinToast = setTimeout(() => element.className = "toast", 3200); }

$$('[data-view]').forEach((button) => button.addEventListener("click", () => { $$('[data-view]').forEach((item) => item.classList.remove("active")); $$('.view').forEach((item) => item.classList.remove("active")); button.classList.add("active"); $(`#view-${button.dataset.view}`).classList.add("active"); window.scrollTo({ top: 0, behavior: "smooth" }); }));
$$('[data-switch]').forEach((link) => link.addEventListener("click", (event) => { event.preventDefault(); $(`[data-view="${link.dataset.switch}"]`).click(); }));
$$('[data-open]').forEach((button) => button.addEventListener("click", () => $(`#${button.dataset.open}`).showModal()));
$$('[data-close]').forEach((button) => button.addEventListener("click", () => $(`#${button.dataset.close}`).close()));
$("#refresh").addEventListener("click", () => load().then(() => toast("Dashboard aktualisiert")).catch((error) => toast(error.message, true)));
$("#expense-form").addEventListener("submit", async (event) => { event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget)); values.amount = Number(values.amount); try { await api("/api/finance/expenses", { method: "POST", body: JSON.stringify({ actor_id: "demo37", ...values }) }); $("#expense-dialog").close(); await load(); $(`[data-view="operations"]`).click(); toast("Auslage zur Freigabe gesendet"); } catch (error) { toast(error.message, true); } });
$("#asset-form").addEventListener("submit", async (event) => { event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget)); values.acquisition_cost = Number(values.acquisition_cost); values.useful_life_months = Number(values.useful_life_months); try { await api("/api/finance/assets", { method: "POST", body: JSON.stringify({ actor_id: "demo36", asset_class: "Technische Anlagen", ...values }) }); $("#asset-dialog").close(); await load(); $(`[data-view="operations"]`).click(); toast("Anlage angelegt"); } catch (error) { toast(error.message, true); } });
load().catch((error) => toast(error.message, true));
