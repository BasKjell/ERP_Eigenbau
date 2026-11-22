const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const escapeHtml = (value) => window.PlatformApps?.escapeHtml(value) || String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);

const state = { data: null, selectedReceiptId: new URLSearchParams(location.search).get("receipt"), selectedInspectionId: null, selectedSample: null, filter: "open" };
const STATUS = { awaiting_inspection: "Prüfung offen", in_progress: "In Prüfung", accepted: "Freigegeben", rejected: "Gesperrt", reinspection: "Nachprüfung" };
const CALIBRATION = { valid: "gültig", due: "bald fällig", expired: "abgelaufen", blocked: "gesperrt", missing: "fehlt" };

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { Accept: "application/json", "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || `HTTP ${response.status}`); }
  return response.json();
}

function toast(message, error = false) {
  const node = $("#quality-toast"); node.textContent = message; node.className = `quality-toast show${error ? " error" : ""}`;
  clearTimeout(toast.timer); toast.timer = setTimeout(() => { node.className = "quality-toast"; }, 3200);
}

function selectedReceipt() { return state.data?.receipts.find((item) => item.id === state.selectedReceiptId); }
function selectedInspection() {
  const receipt = selectedReceipt();
  if (!receipt) return null;
  return state.data.inspections.filter((item) => item.receipt_id === receipt.id).sort((a, b) => b.started_at.localeCompare(a.started_at)).find((item) => item.id === state.selectedInspectionId) || receipt.active_inspection || state.data.inspections.filter((item) => item.receipt_id === receipt.id).sort((a, b) => b.started_at.localeCompare(a.started_at))[0] || null;
}

async function load() {
  const operator = $("#operator").value || "QOP-001";
  state.data = await api(`/api/quality/dashboard?operator_id=${encodeURIComponent(operator)}`);
  if (!state.selectedReceiptId || !state.data.receipts.some((item) => item.id === state.selectedReceiptId)) state.selectedReceiptId = state.data.receipts.find((item) => ["awaiting_inspection", "in_progress"].includes(item.status))?.id || state.data.receipts[0]?.id;
  const receipt = selectedReceipt();
  if (receipt?.active_inspection) state.selectedInspectionId = receipt.active_inspection.id;
  const inspection = selectedInspection();
  if (inspection && (!state.selectedSample || !inspection.sample_refs.includes(state.selectedSample))) state.selectedSample = inspection.sample_refs[0];
  render();
}

function render() {
  renderOperators(); renderMetrics(); renderReceipts(); renderWorkspace(); renderContext();
}

function renderOperators() {
  const current = state.data.operator.id;
  $("#operator").innerHTML = state.data.operators.map((item) => `<option value="${escapeHtml(item.id)}" ${item.id === current ? "selected" : ""}>${escapeHtml(item.name)}</option>`).join("");
  $("#operator-avatar").textContent = state.data.operator.name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}

function renderMetrics() {
  const metrics = state.data.metrics;
  $("#quality-metrics").innerHTML = [
    ["Offene Eingänge", metrics.open_receipts, ""], ["Laufende Prüfungen", metrics.active_inspections, ""], ["Gesperrte Lose", metrics.blocked_lots, metrics.blocked_lots ? "alert" : ""], ["Freigabequote", `${metrics.acceptance_rate} %`, ""], ["Kalibrierhinweise", metrics.calibration_due, metrics.calibration_due ? "alert" : ""]
  ].map(([label, value, css]) => `<article class="metric ${css}"><small>${label}</small><b>${value}</b></article>`).join("");
}

function renderReceipts() {
  const rows = state.filter === "open" ? state.data.receipts.filter((item) => ["awaiting_inspection", "in_progress", "reinspection"].includes(item.status)) : state.data.receipts;
  $("#receipt-count").textContent = rows.length;
  $("#receipt-list").innerHTML = rows.map((item) => `<button class="receipt-card ${item.id === state.selectedReceiptId ? "active" : ""}" data-receipt-id="${escapeHtml(item.id)}"><header><small>${escapeHtml(item.id)}</small><small>${escapeHtml(item.received_at.slice(11,16))}</small></header><b>${escapeHtml(item.item_code)} · ${item.quantity_received} ${escapeHtml(item.uom)}</b><small class="receipt-supplier">${escapeHtml(item.supplier)}</small><span class="status-pill ${escapeHtml(item.status)}">${escapeHtml(STATUS[item.status] || item.status)}</span></button>`).join("") || '<p class="empty-copy">Keine Wareneingänge in dieser Ansicht.</p>';
}

function renderWorkspace() {
  const receipt = selectedReceipt();
  if (!receipt) { $("#inspection-workspace").innerHTML = '<div class="empty-workspace"><span>◇</span><h2>Kein Prüfauftrag ausgewählt</h2><p>Scanne einen Wareneingang oder wähle ihn links aus.</p></div>'; return; }
  const inspection = selectedInspection();
  if (!inspection) { renderStart(receipt); return; }
  if (inspection.status === "completed") { renderDecision(inspection); return; }
  renderInspection(inspection);
}

function renderStart(receipt) {
  const plan = receipt.plan; const sampling = state.data.sampling_plans.find((item) => item.id === plan.sampling_plan_id);
  $("#inspection-workspace").innerHTML = `<div class="workspace-head"><div><span class="eyebrow">${escapeHtml(receipt.id)} · ${escapeHtml(receipt.purchase_order)}</span><h2>${escapeHtml(receipt.item_name)}</h2><p>${escapeHtml(receipt.supplier)} · Lieferschein ${escapeHtml(receipt.supplier_delivery_note)}</p></div><span class="lot-badge">Charge ${escapeHtml(receipt.batch)}</span></div><div class="plan-summary"><div><small>Menge</small><b>${receipt.quantity_received} ${escapeHtml(receipt.uom)}</b></div><div><small>Prüfplan</small><b>${escapeHtml(plan.id)} · Rev. ${escapeHtml(plan.revision)}</b></div><div><small>Stichprobe</small><b>${escapeHtml(sampling?.name || "–")}</b></div><div><small>Zwischenlager</small><b>${escapeHtml(receipt.source_warehouse)}</b></div><div><small>Projekt</small><b>${escapeHtml(receipt.project_id)}</b></div><div><small>Freigabeziel</small><b>${escapeHtml(receipt.accepted_warehouse)}</b></div></div><div class="plan-description"><b>Freigegebener Prüfplan:</b> FLOWWORK ${escapeHtml(plan.work_test_plan_id)} und FLOWDOC ${escapeHtml(plan.dms_document_id)} sind fest auf Revision ${escapeHtml(plan.revision)} referenziert. FLOWQ ermittelt die Stichprobe automatisch.</div><div class="characteristic-preview">${plan.characteristics.map((item, index) => `<article><i>${index + 1}</i><span><b>${escapeHtml(item.name)}</b><small>${escapeHtml(item.instruction)}</small></span><strong>${item.type === "numeric" ? `${item.min_value}–${item.max_value} ${escapeHtml(item.unit)}` : "OK / n. OK"}</strong></article>`).join("")}</div><div class="start-row"><button class="button primary" id="start-inspection">Stichprobe ermitteln und Prüfung starten →</button></div>`;
}

function activeMeasurement(inspection, sample, characteristicId) { return inspection.measurements.find((item) => item.sample_ref === sample && item.characteristic_id === characteristicId); }

function renderInspection(inspection) {
  const sample = state.selectedSample; const sampleIndex = inspection.sample_refs.indexOf(sample); const progress = inspection.measurement_progress;
  $("#inspection-workspace").innerHTML = `<div class="inspection-top"><div><span class="eyebrow">${escapeHtml(inspection.id)} · PRÜFPLAN REV. ${escapeHtml(inspection.plan_revision)}</span><h2>${escapeHtml(inspection.receipt.item_code)} · ${inspection.sample_size} Stichproben</h2></div><div class="progress-block"><div class="progress-copy"><span>${progress.completed} von ${progress.required} Prüfungen</span><b>${progress.percent} %</b></div><div class="progress-track"><i style="width:${progress.percent}%"></i></div></div></div><div class="sample-strip">${inspection.sample_refs.map((item, index) => { const done = inspection.plan.characteristics.filter((characteristic) => characteristic.required !== false).every((characteristic) => activeMeasurement(inspection, item, characteristic.id)); return `<button class="sample-chip ${item === sample ? "active" : ""} ${done ? "done" : ""}" data-sample="${escapeHtml(item)}">${index + 1}. ${escapeHtml(item)}</button>`; }).join("")}</div><div class="sample-title"><h3>Probe ${sampleIndex + 1}: ${escapeHtml(sample)}</h3><span>Ac ${inspection.acceptance_number} · Re ${inspection.rejection_number}</span></div><div class="measurement-list">${inspection.plan.characteristics.map((characteristic) => measurementCard(inspection, sample, characteristic)).join("")}</div><div class="inspection-footer"><p>Alle Pflichtmerkmale aller Stichproben müssen erfasst sein.</p><button class="button success" id="complete-inspection" ${progress.completed < progress.required ? "disabled" : ""}>Prüfung abschließen und Lagerentscheid vorbereiten</button></div>`;
}

function measurementCard(inspection, sample, characteristic) {
  const measurement = activeMeasurement(inspection, sample, characteristic.id); const status = measurement?.status || "open";
  const result = measurement ? `${measurement.value}${measurement.unit ? ` ${measurement.unit}` : ""} · ${status === "passed" ? "bestanden" : "nicht bestanden"}` : "offen";
  if (characteristic.type === "numeric") {
    const instruments = state.data.instruments.filter((item) => item.calibration_state === "valid" && (!characteristic.instrument_types?.length || characteristic.instrument_types.includes(item.type)));
    return `<article class="measurement-card ${status === "passed" ? "done" : status === "failed" ? "failed" : ""}"><div class="measurement-head"><div><h4>${escapeHtml(characteristic.name)}</h4><p>${escapeHtml(characteristic.instruction)} · Toleranz ${characteristic.min_value}–${characteristic.max_value} ${escapeHtml(characteristic.unit)}</p></div><span class="result-mark">${escapeHtml(result)}</span></div><div class="measurement-actions"><label>Messwert<input data-value-for="${escapeHtml(characteristic.id)}" type="number" step="any" value="${measurement ? escapeHtml(measurement.value) : escapeHtml(characteristic.target)}" /></label><label>Messmittel<select data-instrument-for="${escapeHtml(characteristic.id)}">${instruments.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join("")}</select></label><button class="button secondary" data-record="${escapeHtml(characteristic.id)}" data-value-type="numeric">Übernehmen</button><button class="button primary" data-device="${escapeHtml(characteristic.id)}" title="Messwert über offene Gateway-API simulieren">Vom Messgerät</button></div></article>`;
  }
  return `<article class="measurement-card ${status === "passed" ? "done" : status === "failed" ? "failed" : ""}"><div class="measurement-head"><div><h4>${escapeHtml(characteristic.name)}</h4><p>${escapeHtml(characteristic.instruction)}</p></div><span class="result-mark">${escapeHtml(result)}</span></div><div class="boolean-actions"><button class="button success" data-record="${escapeHtml(characteristic.id)}" data-boolean="true">✓ Bestanden</button><button class="button danger" data-record="${escapeHtml(characteristic.id)}" data-boolean="false">× Abweichung</button></div></article>`;
}

function renderDecision(inspection) {
  const accepted = inspection.decision === "accepted"; const sync = inspection.erp_sync || {};
  $("#inspection-workspace").innerHTML = `<div class="workspace-head"><div><span class="eyebrow">${escapeHtml(inspection.id)} · ABGESCHLOSSEN</span><h2>${escapeHtml(inspection.receipt.item_name)}</h2><p>${inspection.sample_size} Stichproben · ${inspection.failed_samples?.length || 0} fehlerhafte Proben</p></div><span class="lot-badge">${escapeHtml(inspection.receipt.batch)}</span></div><div class="decision-card ${accepted ? "" : "rejected"}"><span class="eyebrow">LAGERENTSCHEID</span><h3>${accepted ? "Freigabe vorbereitet" : "Los gesperrt"}</h3><p>${accepted ? `Bestand wird nach ${escapeHtml(inspection.receipt.target_warehouse)} freigegeben.` : `Bestand bleibt in ${escapeHtml(inspection.receipt.target_warehouse)}; ${escapeHtml(inspection.ncr_id || "NCR wird angelegt")}.`}</p><div class="decision-actions"><button class="button primary" id="erp-sync" ${sync.status === "synced" ? "disabled" : ""}>${sync.status === "synced" ? `ERP übertragen · ${escapeHtml(sync.erp_reference)}` : "ERP-Übergabe bestätigen"}</button><a class="button secondary" href="http://localhost:8010" target="_blank">Prüfprotokoll in FLOWDOC ↗</a></div></div><div class="plan-summary"><div><small>Prüfer</small><b>${escapeHtml(inspection.operator_name)}</b></div><div><small>Prüfplan</small><b>${escapeHtml(inspection.inspection_plan_id)} Rev. ${escapeHtml(inspection.plan_revision)}</b></div><div><small>FLOWWORK</small><b>${escapeHtml(inspection.work_test_plan_id)}</b></div><div><small>ERP-Ziel</small><b>${escapeHtml(inspection.receipt.target_warehouse)}</b></div><div><small>DMS-Protokoll</small><b>${escapeHtml(inspection.dms_protocol?.status || "vorbereitet")}</b></div><div><small>NCR</small><b>${escapeHtml(inspection.ncr_id || "keine")}</b></div></div>`;
}

function renderContext() {
  $("#instrument-list").innerHTML = state.data.instruments.map((item) => `<div class="instrument-row"><i class="state-dot ${escapeHtml(item.calibration_state)}"></i><span><b>${escapeHtml(item.name)}</b><small>${escapeHtml(item.interface.toUpperCase())} · bis ${escapeHtml(item.calibration_valid_until)}</small></span><strong>${escapeHtml(CALIBRATION[item.calibration_state] || item.calibration_state)}</strong></div>`).join("");
  $("#adapter-list").innerHTML = state.data.adapters.map((item) => `<div class="adapter-row"><i class="state-dot"></i><span><b>${escapeHtml(item.name)}</b><small>${escapeHtml(item.protocol.toUpperCase())}</small></span><strong>${escapeHtml(item.status)}</strong></div>`).join("");
  const receipt = selectedReceipt(); const plan = receipt?.plan;
  $("#trace-links").innerHTML = plan ? `<div class="trace-grid"><a href="/work?view=tests"><b>FLOWWORK · ${escapeHtml(plan.work_test_plan_id)}</b><small>Prüfplan, Review und Testnachweis</small></a><a href="http://localhost:8010" target="_blank"><b>FLOWDOC · ${escapeHtml(plan.dms_document_id)}</b><small>Freigegebene Anweisung und Revision</small></a><a href="http://localhost:8081/app/purchase-receipt/${escapeHtml(receipt.erp_reference)}" target="_blank"><b>FLOWERP · ${escapeHtml(receipt.erp_reference)}</b><small>Bestellung, Charge und Lagerbestand</small></a></div>` : "<p>Prüfauftrag auswählen.</p>";
}

async function startInspection() {
  const result = await api("/api/quality/inspections", { method: "POST", body: JSON.stringify({ receipt_id: state.selectedReceiptId, operator_id: $("#operator").value }) });
  state.selectedInspectionId = result.id; state.selectedSample = result.sample_refs[0]; toast(`${result.sample_size} Stichproben wurden ausgewählt`); await load();
}

async function record(characteristicId, value, instrumentId = null, source = "manual") {
  const inspection = selectedInspection(); const characteristic = inspection.plan.characteristics.find((item) => item.id === characteristicId);
  const payload = { characteristic_id: characteristicId, sample_ref: state.selectedSample, value, unit: characteristic.unit || "", instrument_id: instrumentId, source, actor_id: $("#operator").value };
  if (source !== "manual") payload.external_event_id = `${inspection.id}-${characteristicId}-${Date.now()}`;
  const path = source === "manual" ? `/api/quality/inspections/${encodeURIComponent(inspection.id)}/measurements` : "/api/quality/v1/measurements";
  if (source !== "manual") payload.inspection_id = inspection.id;
  const result = await api(path, { method: "POST", body: JSON.stringify(payload) }); toast(`${characteristic.name}: ${result.status === "passed" ? "bestanden" : "Abweichung"}`); await load();
}

document.addEventListener("click", async (event) => {
  try {
    const receiptButton = event.target.closest("[data-receipt-id]"); if (receiptButton) { state.selectedReceiptId = receiptButton.dataset.receiptId; state.selectedInspectionId = null; state.selectedSample = null; render(); return; }
    const filterButton = event.target.closest("[data-receipt-filter]"); if (filterButton) { state.filter = filterButton.dataset.receiptFilter; $$('[data-receipt-filter]').forEach((item) => item.classList.toggle("active", item === filterButton)); renderReceipts(); return; }
    const sampleButton = event.target.closest("[data-sample]"); if (sampleButton) { state.selectedSample = sampleButton.dataset.sample; renderWorkspace(); return; }
    if (event.target.closest("#start-inspection")) { await startInspection(); return; }
    const recordButton = event.target.closest("[data-record]"); if (recordButton) { const id = recordButton.dataset.record; if (recordButton.dataset.boolean) await record(id, recordButton.dataset.boolean === "true"); else await record(id, $(`[data-value-for="${CSS.escape(id)}"]`).value, $(`[data-instrument-for="${CSS.escape(id)}"]`).value); return; }
    const deviceButton = event.target.closest("[data-device]"); if (deviceButton) { const id = deviceButton.dataset.device; const inspection = selectedInspection(); const characteristic = inspection.plan.characteristics.find((item) => item.id === id); const instrument = state.data.instruments.find((item) => item.calibration_state === "valid" && characteristic.instrument_types.includes(item.type)); await record(id, characteristic.target, instrument?.id, instrument?.interface === "opcua" ? "opcua" : "rest"); return; }
    if (event.target.closest("#complete-inspection")) { const result = await api(`/api/quality/inspections/${encodeURIComponent(selectedInspection().id)}/complete`, { method: "POST", body: JSON.stringify({ actor_id: $("#operator").value }) }); toast(result.decision === "accepted" ? "Prüfung bestanden; Freigabe vorbereitet" : "Los gesperrt und NCR angelegt", result.decision !== "accepted"); await load(); return; }
    if (event.target.closest("#erp-sync")) { const result = await api(`/api/quality/inspections/${encodeURIComponent(selectedInspection().id)}/erp-sync`, { method: "POST", body: JSON.stringify({ actor_id: $("#operator").value, confirm: true }) }); toast(`ERP-Übergabe ${result.mode}: ${result.erp_reference}`); await load(); return; }
    if (event.target.closest("#quality-reset")) { await api(`/api/quality/reset?operator_id=${encodeURIComponent($("#operator").value)}`, { method: "POST" }); state.selectedInspectionId = null; state.selectedSample = null; toast("FLOWQ-Demodaten zurückgesetzt"); await load(); }
  } catch (error) { toast(error.message, true); }
});

$("#operator").addEventListener("change", () => load().catch((error) => toast(error.message, true)));
$("#scan").addEventListener("keydown", (event) => { if (event.key !== "Enter") return; event.preventDefault(); const query = event.target.value.trim().toLowerCase(); const receipt = state.data.receipts.find((item) => [item.id, item.purchase_order, item.item_code, item.batch, item.supplier_delivery_note].some((value) => String(value || "").toLowerCase().includes(query))); if (!receipt) { toast("Kein passender Wareneingang gefunden", true); return; } state.selectedReceiptId = receipt.id; state.selectedInspectionId = null; state.selectedSample = null; render(); toast(`${receipt.id} geladen`); });

load().catch((error) => toast(error.message, true));
