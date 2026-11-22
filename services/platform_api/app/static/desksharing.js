const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const initialQuery = new URLSearchParams(window.location.search);
let state;
let selectedDesk;
let selectedFloor = initialQuery.get("floor") || "EG";
let selectedRoomId = initialQuery.get("room") || "";
let selectedInfoDeskId = "";
let selectedColleague = null;
let searchMode = initialQuery.get("colleague") ? "colleague" : "booking";
let initialSelectionApplied = false;

const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
const initials = (name) => String(name).split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  if (response.status === 401) {
    window.location.assign(`/auth/login?next=${encodeURIComponent(window.location.pathname)}`);
    throw new Error("Anmeldung erforderlich");
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unbekannter Fehler" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

function localDate() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function params() {
  return new URLSearchParams({
    user_id: $("#user-filter").value || "USR-001",
    booking_date: $("#date-filter").value,
    site_id: $("#site-filter").value || initialQuery.get("site") || "BER",
    slot: $("#slot-filter").value,
  });
}

async function load() {
  try {
    state = await api(`/api/desksharing/dashboard?${params()}`);
    if (!initialSelectionApplied) {
      selectedFloor = state.sites.find((site) => site.id === state.selected_site)?.floors.includes(selectedFloor) ? selectedFloor : "EG";
      selectedRoomId = state.rooms.some((room) => room.id === selectedRoomId) ? selectedRoomId : "";
      if (initialQuery.get("colleague")) $("#colleague-search").value = initialQuery.get("colleague");
      initialSelectionApplied = true;
    }
    render();
  } catch (error) {
    toast(error.message, true);
  }
}

function render() {
  const metrics = state.metrics;
  $("#hero-stats").innerHTML = [
    ["Freie Plätze", metrics.available_desks, `von ${metrics.total_desks} am Standort`],
    ["Auslastung", `${metrics.utilization_percent} %`, `${metrics.occupied_desks} belegt`],
    ["Erwartete Personen", metrics.expected_people, "im gewählten Zeitraum"],
    ["Standorte", state.sites.length, "Berlin · Hamburg"],
  ].map(([label, value, detail]) => `<article class="stat"><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b><small>${escapeHtml(detail)}</small></article>`).join("");

  if (!$("#user-filter").options.length) {
    $("#user-filter").innerHTML = state.demo_users.map((user) => `<option value="${escapeHtml(user.id)}">${escapeHtml(user.name)} · ${escapeHtml(user.department)}</option>`).join("");
    $("#user-filter").value = state.current_user.id;
  }
  if (!$("#site-filter").options.length) {
    $("#site-filter").innerHTML = state.sites.map((site) => `<option value="${site.id}">${escapeHtml(site.name)}</option>`).join("");
  }
  $("#site-filter").value = state.selected_site;
  $("#date-filter").value = state.selected_date;
  $("#slot-filter").value = state.selected_slot;
  const site = state.sites.find((item) => item.id === state.selected_site);
  $("#floor-title").textContent = `${site.name} · ${selectedFloor}`;
  $("#floor-eyebrow").textContent = `${site.building_code} · ${site.address} · ${state.slot_labels[state.selected_slot]}`;
  setMode(searchMode, false);
  renderFloorTabs();
  renderRoomTabs();
  renderColleagues();
  renderPlan();
  renderInfoPanel();
  renderBookings();
  if (state.permissions.can_manage) loadAdmin(); else $("#admin-section").hidden = true;
}

function roomForDesk(desk) {
  return state.rooms.find((room) => room.id === desk.room_id);
}

function visibleDesk(desk) {
  const room = roomForDesk(desk);
  const query = $("#desk-search").value.trim().toLowerCase();
  const zones = new Set($$("input[name=zone]:checked").map((item) => item.value));
  const haystack = `${desk.id} ${desk.label} ${desk.zone} ${room?.name || ""} ${desk.features.join(" ")}`.toLowerCase();
  return desk.floor === selectedFloor
    && (!selectedRoomId || desk.room_id === selectedRoomId)
    && (!query || haystack.includes(query))
    && zones.has(desk.zone)
    && (!$("#standing-filter").checked || desk.features.includes("Höhenverstellbar"))
    && (!$("#accessible-filter").checked || desk.accessible)
    && (!$("#dual-filter").checked || desk.features.includes("Dual-Monitor"));
}

function renderFloorTabs() {
  const site = state.sites.find((item) => item.id === state.selected_site);
  $("#floor-tabs").innerHTML = site.floors.map((floor) => `<button class="${floor === selectedFloor ? "active" : ""}" data-floor="${escapeHtml(floor)}" type="button">${floor === "EG" ? "Erdgeschoss" : floor}</button>`).join("");
  $$('[data-floor]').forEach((button) => button.addEventListener("click", () => {
    selectedFloor = button.dataset.floor;
    selectedRoomId = "";
    selectedInfoDeskId = "";
    selectedColleague = null;
    render();
  }));
}

function renderRoomTabs() {
  const rooms = state.rooms.filter((room) => room.floor === selectedFloor);
  $("#room-tabs").innerHTML = `<button class="${selectedRoomId ? "" : "active"}" data-room-tab="" type="button">Alle Räume</button>${rooms.map((room) => `<button class="${room.id === selectedRoomId ? "active" : ""}" data-room-tab="${room.id}" type="button">${escapeHtml(room.name)}</button>`).join("")}`;
  $$('[data-room-tab]').forEach((button) => button.addEventListener("click", () => {
    selectedRoomId = button.dataset.roomTab;
    selectedInfoDeskId = "";
    selectedColleague = null;
    renderRoomTabs();
    renderPlan();
    renderInfoPanel();
  }));
}

function planSvg() {
  const rooms = state.rooms.filter((room) => room.floor === selectedFloor);
  const desks = state.desks.filter((desk) => desk.floor === selectedFloor);
  const visibleIds = new Set(desks.filter(visibleDesk).map((desk) => desk.id));
  const infoDesk = desks.find((desk) => desk.id === selectedInfoDeskId);
  const roomShapes = rooms.map((room) => {
    const geometry = room.map;
    const selected = room.id === selectedRoomId || room.id === infoDesk?.room_id;
    return `<g data-room="${room.id}" role="button" aria-label="${escapeHtml(room.name)}"><rect class="map-room ${room.zone.toLowerCase()} ${selected ? "selected" : ""}" x="${geometry.x}" y="${geometry.y}" width="${geometry.width}" height="${geometry.height}" rx="1.5"></rect><text class="map-room-label" x="${geometry.x + 2}" y="${geometry.y + 4}">${escapeHtml(room.name)}</text><text class="map-room-meta" x="${geometry.x + 2}" y="${geometry.y + 7}">${room.capacity} Plätze · ${escapeHtml(room.zone)}</text></g>`;
  }).join("");
  const deskShapes = desks.map((desk) => {
    const filtered = !visibleIds.has(desk.id);
    const colleague = desk.id === selectedColleague?.desk_id;
    const selected = desk.id === selectedInfoDeskId;
    const shortNumber = String(desk.number > 25 ? desk.number - 25 : desk.number).padStart(2, "0");
    return `<g class="map-desk ${desk.availability} ${filtered ? "filtered" : ""} ${colleague ? "colleague" : ""} ${selected ? "selected" : ""}" data-map-desk="${desk.id}" role="button" aria-label="Arbeitsplatz ${shortNumber}, ${desk.availability}"><rect x="${desk.map_x - 4}" y="${desk.map_y - 3}" width="8" height="6"></rect><text x="${desk.map_x}" y="${desk.map_y + 0.7}">${shortNumber}</text></g>`;
  }).join("");
  return `<svg viewBox="0 0 100 103" role="img" aria-label="Gebäudeplan ${escapeHtml(selectedFloor)}"><rect class="map-shell" x="1" y="1" width="98" height="100" rx="2"></rect>${roomShapes}<rect class="map-corridor" x="3" y="52" width="94" height="5"></rect><rect class="map-entry" x="42" y="94" width="16" height="7" rx="1"></rect><text class="map-entry-label" x="50" y="98.5" text-anchor="middle">${selectedFloor === "EG" ? "EMPFANG" : "AUFZUG"}</text>${deskShapes}</svg>`;
}

function renderPlan() {
  const visible = state.desks.filter(visibleDesk);
  $("#result-count").textContent = `${visible.length} Treffer · ${selectedFloor}`;
  $("#building-plan").innerHTML = planSvg();
  $$('[data-room]').forEach((room) => room.addEventListener("click", () => {
    selectedRoomId = room.dataset.room;
    selectedInfoDeskId = "";
    selectedColleague = null;
    renderRoomTabs();
    renderPlan();
    renderInfoPanel();
  }));
  $$('[data-map-desk]').forEach((node) => node.addEventListener("click", () => {
    const desk = state.desks.find((item) => item.id === node.dataset.mapDesk);
    if (searchMode === "colleague") {
      const colleague = state.colleague_locations.find((item) => item.desk_id === desk.id);
      if (colleague) showColleague(colleague); else toast("Für diesen Platz ist keine sichtbare Kollegenbuchung vorhanden.");
      return;
    }
    if (desk.availability === "occupied") {
      toast("Dieser Platz ist belegt. Nutze die Kollegensuche für sichtbare Buchungen.");
      return;
    }
    openDesk(desk.id);
  }));
}

function renderInfoPanel() {
  const desk = state?.desks.find((item) => item.id === selectedInfoDeskId);
  if (!desk) {
    $("#info-panel").innerHTML = `<span class="eyebrow">PLATZINFORMATION</span><h3>Wähle einen Platz oder Kollegen</h3><p>FLOWSPACE zeigt Etage, Raum und den markierten Arbeitsplatz.</p>`;
    return;
  }
  if (selectedColleague) {
    $("#info-panel").innerHTML = `<span class="eyebrow">KOLLEGENPLATZ</span><h3>${escapeHtml(selectedColleague.room_name)} · ${escapeHtml(selectedColleague.floor)} · ${escapeHtml(desk.label.split("·").at(-1).trim())}</h3><div class="info-person"><span class="colleague-avatar">${initials(selectedColleague.user_name)}</span><span><b>${escapeHtml(selectedColleague.user_name)}</b><small>${escapeHtml(selectedColleague.department)} · ${escapeHtml(selectedColleague.slot_label)}</small></span></div><p>Der Arbeitsplatz ist im Grundriss blau markiert.</p>`;
    return;
  }
  const room = roomForDesk(desk);
  $("#info-panel").innerHTML = `<span class="eyebrow">PLATZINFORMATION</span><h3>${escapeHtml(room.name)} · ${escapeHtml(desk.floor)} · ${escapeHtml(desk.label.split("·").at(-1).trim())}</h3><p>Der ausgewählte Arbeitsplatz ist im Grundriss markiert.</p><span class="info-tag">${escapeHtml(desk.features.join(" · "))}</span>`;
}

function showColleague(colleague) {
  selectedColleague = colleague;
  selectedFloor = colleague.floor;
  selectedRoomId = colleague.room_id;
  selectedInfoDeskId = colleague.desk_id;
  render();
}

function renderColleagues() {
  const query = $("#colleague-search").value.trim().toLowerCase();
  const matches = state.colleague_locations.filter((person) => !query || `${person.user_name} ${person.department}`.toLowerCase().includes(query));
  $("#colleague-results").innerHTML = matches.length ? matches.map((person) => `<button class="colleague-card ${person.user_id === selectedColleague?.user_id ? "active" : ""}" data-colleague="${person.user_id}" type="button"><span class="colleague-avatar">${initials(person.user_name)}</span><span><b>${escapeHtml(person.user_name)}</b><small>${escapeHtml(person.department)} · ${escapeHtml(person.room_name)}</small></span></button>`).join("") : `<div class="empty-state">Keine aktive Buchung für diese Suche.</div>`;
  $$('[data-colleague]').forEach((button) => button.addEventListener("click", () => showColleague(state.colleague_locations.find((item) => item.user_id === button.dataset.colleague))));
}

function setMode(mode, rerender = true) {
  searchMode = mode;
  const colleagueMode = mode === "colleague";
  $("#booking-mode").classList.toggle("active", !colleagueMode);
  $("#booking-mode").setAttribute("aria-selected", String(!colleagueMode));
  $("#colleague-mode").classList.toggle("active", colleagueMode);
  $("#colleague-mode").setAttribute("aria-selected", String(colleagueMode));
  $("#booking-filters").hidden = colleagueMode;
  $("#colleague-finder").hidden = !colleagueMode;
  if (rerender && state) {
    selectedInfoDeskId = "";
    selectedColleague = null;
    renderColleagues();
    renderPlan();
    renderInfoPanel();
  }
}

function openDesk(id) {
  const desk = state.desks.find((item) => item.id === id);
  if (desk.availability === "mine") {
    selectedInfoDeskId = desk.id;
    selectedRoomId = desk.room_id;
    renderPlan();
    renderInfoPanel();
    toast("Dieser Platz ist bereits für dich gebucht.");
    return;
  }
  selectedDesk = desk;
  selectedInfoDeskId = desk.id;
  selectedRoomId = desk.room_id;
  renderPlan();
  renderInfoPanel();
  $("#dialog-title").textContent = desk.label;
  $("#dialog-meta").textContent = `${desk.room.name} · ${state.selected_date} · ${state.slot_labels[state.selected_slot]}`;
  $("#dialog-features").innerHTML = desk.features.map((item) => `<span>${escapeHtml(item)}</span>`).join("");
  $("#booking-note").value = "";
  $("#booking-dialog").showModal();
}

function renderBookings() {
  const statuses = { booked: "Gebucht", checked_in: "Eingecheckt", completed: "Abgeschlossen", cancelled: "Storniert" };
  const items = state.my_bookings.filter((item) => item.status !== "cancelled");
  $("#my-bookings").innerHTML = items.length ? items.map((item) => `<article class="booking-card"><header><div><h3>${escapeHtml(item.desk_label)}</h3><p>${escapeHtml(item.site_name)} · ${escapeHtml(item.room_name)} · ${item.date} · ${escapeHtml(item.slot_label)}</p></div><span class="status ${item.status}">${statuses[item.status]}</span></header><div class="booking-actions">${item.status === "booked" ? `<button data-action="check-in" data-booking="${item.id}">Einchecken</button>` : ""}${item.status === "checked_in" ? `<button data-action="check-out" data-booking="${item.id}">Auschecken</button>` : ""}${["booked", "checked_in"].includes(item.status) ? `<button data-action="cancel" data-booking="${item.id}">Stornieren</button>` : ""}</div></article>`).join("") : `<div class="empty-state">Noch keine Buchung. Wähle im Gebäudeplan einen freien Platz aus.</div>`;
  $$('[data-booking]').forEach((button) => button.addEventListener("click", () => bookingAction(button.dataset.booking, button.dataset.action)));
}

async function bookingAction(id, action) {
  try {
    await api(`/api/desksharing/bookings/${encodeURIComponent(id)}/${action}`, { method: "POST", body: JSON.stringify({ actor_id: state.current_user.id }) });
    toast(action === "cancel" ? "Buchung storniert" : action === "check-in" ? "Erfolgreich eingecheckt" : "Erfolgreich ausgecheckt");
    await load();
  } catch (error) {
    toast(error.message, true);
  }
}

async function loadAdmin() {
  try {
    const result = await api(`/api/desksharing/admin?actor_id=${encodeURIComponent(state.current_user.id)}`);
    $("#admin-section").hidden = false;
    $("#admin-content").innerHTML = result.sites.map((site) => `<article class="admin-card"><span>${escapeHtml(site.site_name)}</span><b>${site.active_bookings}</b><span>aktive Buchungen · ${site.desks} Plätze</span></article>`).join("") + `<article class="admin-card"><span>Identitäten</span><b>${result.users}</b><span>Keycloak-Demobenutzer</span></article>`;
  } catch (error) {
    $("#admin-section").hidden = true;
  }
}

function toast(message, error = false) {
  const node = $("#toast");
  node.textContent = message;
  node.className = `toast show ${error ? "error" : ""}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.className = "toast", 2800);
}

$("#booking-form").addEventListener("submit", async (event) => {
  if (event.submitter?.value === "cancel") return;
  event.preventDefault();
  try {
    await api("/api/desksharing/bookings", { method: "POST", body: JSON.stringify({ user_id: state.current_user.id, desk_id: selectedDesk.id, date: state.selected_date, slot: state.selected_slot, note: $("#booking-note").value }) });
    $("#booking-dialog").close();
    toast("Arbeitsplatz verbindlich gebucht");
    await load();
  } catch (error) {
    toast(error.message, true);
  }
});

$("#refresh").addEventListener("click", load);
$("#user-filter").addEventListener("change", load);
$("#site-filter").addEventListener("change", () => { selectedFloor = "EG"; selectedRoomId = ""; selectedInfoDeskId = ""; selectedColleague = null; load(); });
$("#date-filter").addEventListener("change", load);
$("#slot-filter").addEventListener("change", load);
$("#booking-mode").addEventListener("click", () => setMode("booking"));
$("#colleague-mode").addEventListener("click", () => setMode("colleague"));
$("#colleague-search").addEventListener("input", () => state && renderColleagues());
$$("#desk-search, input[name=zone], #standing-filter, #accessible-filter, #dual-filter").forEach((item) => item.addEventListener("input", () => state && renderPlan()));
$("#reset-demo").addEventListener("click", async () => {
  try {
    state = await api(`/api/desksharing/reset?user_id=${encodeURIComponent($("#user-filter").value)}`, { method: "POST" });
    selectedFloor = "EG";
    selectedRoomId = "";
    selectedInfoDeskId = "";
    selectedColleague = null;
    toast("Desksharing-Demo zurückgesetzt");
    render();
  } catch (error) {
    toast(error.message, true);
  }
});

async function loadIdentity() {
  const identity = await api("/auth/me");
  if (identity.authenticated) {
    $("#auth-dot").classList.add("online");
    $("#auth-name").textContent = identity.user.name || identity.user.username;
    $("#auth-detail").textContent = identity.user.department || "Keycloak SSO";
    $("#auth-action").textContent = "Abmelden";
    $("#auth-action").href = identity.logout_url;
    $("#user-filter").closest("label").hidden = true;
    $(".control-panel").classList.add("sso-mode");
  } else {
    $("#auth-detail").textContent = identity.mode === "oidc" ? "Anmeldung erforderlich" : "Lokale Rollen-Simulation";
  }
}

$("#date-filter").value = initialQuery.get("date") || localDate();
$("#slot-filter").value = initialQuery.get("slot") || "full_day";
loadIdentity().then(load).catch((error) => toast(error.message, true));
