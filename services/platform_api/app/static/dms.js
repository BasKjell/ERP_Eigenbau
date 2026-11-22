/* FLOWDOC · eigene DMS-Oberfläche. Alle Daten kommen über /api/dms (Plattform-API -> Paperless-ngx
 * im Namen der angemeldeten Person). Die Oberfläche speichert keine Dokumente und entscheidet keine Rechte. */
(function () {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const params = new URLSearchParams(window.location.search);
  const state = {
    q: params.get("q") || "",
    status: params.get("status") || "",
    document_type: params.get("document_type") || "",
    tag: params.get("tag") || "",
    correspondent: params.get("correspondent") || "",
    ordering: params.get("ordering") || "-created",
    page: Number(params.get("page") || 1),
    selected: params.get("doc") || "",
  };
  let facets = null;
  let searchTimer = null;
  const STATUS_CLASS = { "Status/Entwurf": "entwurf", "Status/In Prüfung": "pruefung", "Status/Freigegeben": "freigegeben", "Status/Ungültig": "ungueltig" };
  const STATUS_TEXT = (status) => (status || "").replace("Status/", "") || "ohne Status";
  const TRANSITION_LABEL = { pruefen: "Zur Prüfung geben", freigeben: "Freigeben", zurueckweisen: "Zurückweisen" };

  function syncUrl() {
    const query = new URLSearchParams();
    for (const key of ["q", "status", "document_type", "tag", "correspondent"]) if (state[key]) query.set(key, state[key]);
    if (state.ordering !== "-created") query.set("ordering", state.ordering);
    if (state.page > 1) query.set("page", String(state.page));
    if (state.selected) query.set("doc", state.selected);
    history.replaceState(null, "", `${location.pathname}${query.toString() ? `?${query}` : ""}`);
  }

  async function api(path, options = {}) {
    const response = await fetch(path, { headers: { Accept: "application/json", ...(options.headers || {}) }, ...options });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `FLOWDOC antwortete ${response.status}`);
    return body;
  }

  function setAccess(text, tone) {
    const box = $("#dms-access");
    box.className = `dms-access ${tone}`;
    box.innerHTML = `<span class="dot"></span><span>${text}</span>`;
  }

  function renderFacets() {
    if (!facets) return;
    const facet = (target, rows, key, withColor = false) => {
      $(target).innerHTML = rows.length ? rows.map((row) => `<li><button type="button" class="${String(state[key]) === String(row.id) ? "active" : ""}" data-facet="${key}" data-value="${esc(row.id)}"><span>${withColor && row.color ? `<i class="swatch" style="background:${esc(row.color)}"></i>` : ""}${esc(row.name)}</span><small>${esc(row.count ?? "")}</small></button></li>`).join("") : '<li><small style="padding:6px 8px;display:block;color:#66767a">keine sichtbar</small></li>';
    };
    facet("#facet-types", facets.document_types, "document_type");
    facet("#facet-tags", facets.tags.filter((t) => !t.name.startsWith("Status/")), "tag", true);
    facet("#facet-correspondents", facets.correspondents, "correspondent");
    document.querySelectorAll("[data-facet]").forEach((button) => button.addEventListener("click", () => {
      const key = button.dataset.facet;
      state[key] = String(state[key]) === button.dataset.value ? "" : button.dataset.value;
      state.page = 1;
      load();
    }));
    const upType = $("#upload-type"), upTag = $("#upload-tag");
    upType.innerHTML = '<option value="">automatisch</option>' + facets.document_types.map((t) => `<option value="${esc(t.id)}">${esc(t.name)}</option>`).join("");
    upTag.innerHTML = '<option value="">automatisch</option>' + facets.tags.filter((t) => !t.name.startsWith("Status/")).map((t) => `<option value="${esc(t.id)}">${esc(t.name)}</option>`).join("");
  }

  function renderActiveFilters() {
    const items = [];
    const name = (list, id) => (facets?.[list] || []).find((row) => String(row.id) === String(id))?.name || id;
    if (state.q) items.push(["q", `Suche: ${state.q}`]);
    if (state.status) items.push(["status", STATUS_TEXT(state.status)]);
    if (state.document_type) items.push(["document_type", name("document_types", state.document_type)]);
    if (state.tag) items.push(["tag", name("tags", state.tag)]);
    if (state.correspondent) items.push(["correspondent", name("correspondents", state.correspondent)]);
    $("#active-filters").innerHTML = items.map(([key, label]) => `<button type="button" data-clear="${key}">${esc(label)} ✕</button>`).join("");
    document.querySelectorAll("[data-clear]").forEach((button) => button.addEventListener("click", () => {
      state[button.dataset.clear] = "";
      if (button.dataset.clear === "q") $("#dms-query").value = "";
      state.page = 1;
      load();
    }));
    document.querySelectorAll("#status-filter button").forEach((button) => button.classList.toggle("active", button.dataset.status === state.status));
  }

  function row(doc) {
    // Treffer-Hervorhebung: alles escapen und nur Paperless' <span class="match"> wiederherstellen.
    const highlight = doc.highlight ? `<div class="hit">${esc(doc.highlight).replace(/&lt;span class=&quot;match&quot;&gt;/g, "<span>").replace(/&lt;\/span&gt;/g, "</span>")}</div>` : "";
    return `<button class="dms-row ${String(doc.id) === String(state.selected) ? "selected" : ""}" type="button" data-doc="${esc(doc.id)}">
      <span class="dms-thumb" data-thumb="${esc(doc.id)}">${esc((doc.mime_type || "PDF").split("/").pop().toUpperCase().slice(0, 4))}</span>
      <span><b>${esc(doc.title)}</b><small>${esc(doc.document_type || "ohne Dokumenttyp")}${doc.correspondent ? ` · ${esc(doc.correspondent)}` : ""}${doc.storage_path ? ` · ${esc(doc.storage_path)}` : ""}</small>${highlight}<span class="dms-tags">${doc.tags.slice(0, 5).map((t) => `<span class="dms-tag">${t.color ? `<i style="background:${esc(t.color)}"></i>` : ""}${esc(t.name)}</span>`).join("")}</span></span>
      <span class="dms-date">erstellt ${esc(doc.created)}<br>abgelegt ${esc(doc.added)}</span>
      <span class="dms-status ${STATUS_CLASS[doc.status] || ""}">${esc(STATUS_TEXT(doc.status))}</span>
    </button>`;
  }

  function lazyThumbs() {
    const observer = "IntersectionObserver" in window ? new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const element = entry.target;
        element.style.backgroundImage = `url("/api/dms/documents/${encodeURIComponent(element.dataset.thumb)}/thumb")`;
        element.textContent = "";
        observer.unobserve(element);
      });
    }) : null;
    document.querySelectorAll("[data-thumb]").forEach((element) => observer ? observer.observe(element) : null);
  }

  async function load() {
    syncUrl();
    renderActiveFilters();
    const query = new URLSearchParams({ ordering: state.ordering, page: String(state.page) });
    for (const key of ["q", "status", "document_type", "tag", "correspondent"]) if (state[key]) query.set(key, state[key]);
    $("#dms-list").innerHTML = '<div class="dms-empty">Dokumente werden geladen …</div>';
    try {
      const result = await api(`/api/dms/documents?${query}`);
      facets = result.facets;
      renderFacets();
      renderActiveFilters();
      const delegated = result.access.startsWith("im Namen");
      setAccess(delegated ? `<b>${esc(result.access)}</b> – FLOWDOC prüft deine Rechte für jedes Dokument, jeden Titel und jede Vorschau.` : `<b>${esc(result.access)}</b> – lokale Demo ohne Anmeldung.`, delegated ? "ok" : "");
      $("#dms-summary").textContent = `${result.count} Dokument${result.count === 1 ? "" : "e"} sichtbar${state.q ? ` für „${state.q}“` : ""}`;
      $("#dms-list").innerHTML = result.results.length ? result.results.map(row).join("") : '<div class="dms-empty"><b>Keine Dokumente gefunden</b>Filter lockern oder anderen Suchbegriff verwenden. Nicht freigegebene Dokumente erscheinen grundsätzlich nicht.</div>';
      document.querySelectorAll("[data-doc]").forEach((button) => button.addEventListener("click", () => openDocument(button.dataset.doc)));
      lazyThumbs();
      const pages = Math.max(1, Math.ceil(result.count / (result.page_size || 25)));
      $("#dms-pager").innerHTML = pages > 1 ? Array.from({ length: Math.min(pages, 12) }, (_, i) => `<button type="button" class="${i + 1 === state.page ? "active" : ""}" data-page="${i + 1}">${i + 1}</button>`).join("") : "";
      document.querySelectorAll("[data-page]").forEach((button) => button.addEventListener("click", () => { state.page = Number(button.dataset.page); load(); window.scrollTo({ top: 0, behavior: "smooth" }); }));
    } catch (error) {
      setAccess(esc(error.message), "error");
      $("#dms-summary").textContent = "FLOWDOC ist nicht erreichbar.";
      $("#dms-list").innerHTML = `<div class="dms-empty"><b>${esc(error.message)}</b>Für die lokale Umgebung: <code>make full</code> startet Paperless-ngx; die Plattform-API braucht den Paperless-Zugang (siehe Betriebsdoku).</div>`;
    }
  }

  async function openDocument(id) {
    state.selected = String(id);
    syncUrl();
    document.querySelectorAll("[data-doc]").forEach((element) => element.classList.toggle("selected", element.dataset.doc === state.selected));
    const panel = $("#dms-detail");
    panel.hidden = false;
    document.querySelector(".dms-main").classList.add("with-detail");
    panel.innerHTML = '<div class="dms-empty">Dokument wird geladen …</div>';
    try {
      renderDetail(await api(`/api/dms/documents/${encodeURIComponent(id)}`));
    } catch (error) {
      panel.innerHTML = `<header><b>Dokument</b><button class="close" type="button" data-close>×</button></header><div class="dms-empty">${esc(error.message)}</div>`;
      panel.querySelector("[data-close]").addEventListener("click", closeDetail);
    }
  }

  function closeDetail() {
    state.selected = "";
    syncUrl();
    $("#dms-detail").hidden = true;
    document.querySelector(".dms-main").classList.remove("with-detail");
    document.querySelectorAll("[data-doc]").forEach((element) => element.classList.remove("selected"));
  }

  function renderDetail(doc) {
    const panel = $("#dms-detail");
    const order = ["Status/Entwurf", "Status/In Prüfung", "Status/Freigegeben"];
    const isImage = (doc.mime_type || "").startsWith("image/");
    const fields = (doc.custom_fields || []).filter((f) => f.value !== null && f.value !== "").slice(0, 12);
    panel.innerHTML = `
      <header><div><span class="dms-status ${STATUS_CLASS[doc.status] || ""}">${esc(STATUS_TEXT(doc.status))}</span><h2>${esc(doc.title)}</h2><small>${esc(doc.document_type || "ohne Dokumenttyp")} · Nr. ${esc(doc.id)}${doc.archive_serial_number ? ` · ASN ${esc(doc.archive_serial_number)}` : ""}</small></div><button class="close" type="button" data-close aria-label="Schließen">×</button></header>
      ${isImage ? `<img class="dms-preview" style="object-fit:contain" src="/api/dms/documents/${encodeURIComponent(doc.id)}/preview" alt="Vorschau ${esc(doc.title)}">` : `<iframe class="dms-preview" title="Vorschau ${esc(doc.title)}" src="/api/dms/documents/${encodeURIComponent(doc.id)}/preview#toolbar=0"></iframe>`}
      <div class="dms-workflow"><div class="steps">${order.map((s, i) => `<span class="${order.indexOf(doc.status) >= i ? "on" : ""}">${i ? "→ " : ""}${esc(STATUS_TEXT(s))}</span>`).join(" ")}</div>
        ${doc.transitions.map((t) => `<button class="dms-btn ${t === "freigeben" ? "green" : t === "pruefen" ? "primary" : ""}" type="button" data-transition="${esc(t)}">${esc(TRANSITION_LABEL[t] || t)}</button>`).join("")}
        ${doc.transitions.length ? "" : "<small>Kein Statuswechsel aus diesem Stand vorgesehen.</small>"}
        <span class="dms-error" data-error></span></div>
      <dl class="dms-meta">
        <dt>Erstellt</dt><dd>${esc(doc.created)}</dd><dt>Abgelegt</dt><dd>${esc(doc.added)}</dd>
        <dt>Korrespondent</dt><dd>${esc(doc.correspondent || "–")}</dd><dt>Ablagepfad</dt><dd>${esc(doc.storage_path || "–")}</dd>
        <dt>Originaldatei</dt><dd>${esc(doc.original_file ? doc.original_file.name : doc.original_file_name || "–")}</dd>
        ${doc.original_file ? `<dt>Prüfsumme</dt><dd><code title="SHA-256 der Originaldatei">${esc(doc.original_file.sha256)}</code></dd>` : ""}<dt>Seiten</dt><dd>${esc(doc.page_count ?? "–")}</dd>
        <dt>Projekte/Bereiche</dt><dd>${doc.tags.map((t) => `<span class="dms-tag">${esc(t.name)}</span>`).join(" ") || "–"}</dd>
        ${fields.map((f) => `<dt>Feld ${esc(f.field)}</dt><dd>${esc(f.value)}</dd>`).join("")}
      </dl>
      <div style="display:flex;gap:6px;margin-top:12px">${doc.original_file ? `<a class="dms-btn primary" href="/api/dms/documents/${encodeURIComponent(doc.id)}/original">Originaldatei herunterladen (${esc(doc.original_file.name)})</a>` : ""}<a class="dms-btn" href="/api/dms/documents/${encodeURIComponent(doc.id)}/download">${doc.original_file ? "Begleitblatt" : "Herunterladen"}</a><a class="dms-btn" href="/api/dms/documents/${encodeURIComponent(doc.id)}/preview" target="_blank" rel="noopener">Vorschau in neuem Tab</a></div>
      <h3>Notizen</h3><div class="dms-notes">${doc.notes.length ? doc.notes.map((n) => `<div class="dms-note">${esc(n.note)}<small>${esc(n.user || "")} · ${esc(String(n.created || "").slice(0, 16).replace("T", " "))}</small></div>`).join("") : '<small style="color:#66767a">Noch keine Notiz.</small>'}</div>
      <form class="dms-note-form" data-note><input name="note" minlength="2" maxlength="2000" placeholder="Notiz für Prüfung oder Freigabe" required><button class="dms-btn" type="submit">Hinzufügen</button></form>
      ${doc.content ? `<h3>Erkannter Text (Auszug)</h3><div class="dms-ocr">${esc(doc.content)}</div>` : ""}`;
    panel.querySelector("[data-close]").addEventListener("click", closeDetail);
    panel.querySelectorAll("[data-transition]").forEach((button) => button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        renderDetail(await api(`/api/dms/documents/${encodeURIComponent(doc.id)}/transition`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: button.dataset.transition }) }));
        load();
      } catch (error) {
        button.disabled = false;
        panel.querySelector("[data-error]").textContent = error.message;
      }
    }));
    panel.querySelector("[data-note]").addEventListener("submit", async (event) => {
      event.preventDefault();
      const note = new FormData(event.currentTarget).get("note");
      try {
        renderDetail(await api(`/api/dms/documents/${encodeURIComponent(doc.id)}/notes`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ note }) }));
      } catch (error) {
        panel.querySelector("[data-error]").textContent = error.message;
      }
    });
  }

  // -- Ablage ----------------------------------------------------------------------------
  function openUpload() {
    $("#upload-msg").textContent = "";
    $("#upload-msg").className = "msg";
    $("#upload-dialog").showModal();
  }

  async function submitUpload() {
    const form = $("#upload-form");
    const file = $("#upload-file").files[0];
    const message = $("#upload-msg");
    if (!file) { message.textContent = "Bitte eine Datei wählen."; message.className = "msg error"; return; }
    const data = new FormData();
    data.append("document", file);
    data.append("title", form.title.value);
    if (form.document_type.value) data.append("document_type", form.document_type.value);
    if (form.tags.value) data.append("tags", form.tags.value);
    message.textContent = "Wird übertragen …";
    message.className = "msg";
    try {
      const response = await fetch("/api/dms/upload", { method: "POST", body: data });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || `Ablage abgelehnt (${response.status})`);
      message.textContent = body.original_file
        ? "3D-Modell sicher abgelegt (Prüfsumme gespeichert). FLOWDOC legt das Begleitblatt an …"
        : "Übertragen. FLOWDOC erkennt Text und ordnet ab …";
      for (let attempt = 0; attempt < 40; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 1500));
        const task = await api(`/api/dms/tasks/${encodeURIComponent(body.task_id)}`);
        if (task.status === "SUCCESS") {
          message.textContent = "Abgelegt.";
          setTimeout(() => { $("#upload-dialog").close(); form.reset(); $("#upload-filename").textContent = ""; load(); if (task.document_id) openDocument(task.document_id); }, 700);
          return;
        }
        if (task.status === "FAILURE") throw new Error(`Verarbeitung fehlgeschlagen: ${task.result || "unbekannt"}`);
      }
      message.textContent = "Die Verarbeitung dauert länger. Das Dokument erscheint, sobald FLOWDOC fertig ist.";
    } catch (error) {
      message.textContent = error.message;
      message.className = "msg error";
    }
  }

  // -- Ereignisse --------------------------------------------------------------------------
  $("#dms-query").value = state.q;
  $("#dms-query").addEventListener("input", (event) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { state.q = event.target.value.trim(); state.page = 1; load(); }, 350);
  });
  $("#dms-ordering").value = state.ordering;
  $("#dms-ordering").addEventListener("change", (event) => { state.ordering = event.target.value; state.page = 1; load(); });
  document.querySelectorAll("#status-filter button").forEach((button) => button.addEventListener("click", () => { state.status = button.dataset.status; state.page = 1; load(); }));
  $("#open-upload").addEventListener("click", openUpload);
  $("#upload-submit").addEventListener("click", submitUpload);
  $("#upload-file").addEventListener("change", (event) => { $("#upload-filename").textContent = event.target.files[0]?.name || ""; });
  const drop = $("#drop-zone");
  ["dragenter", "dragover"].forEach((name) => drop.addEventListener(name, () => drop.classList.add("drag")));
  ["dragleave", "drop"].forEach((name) => drop.addEventListener(name, () => drop.classList.remove("drag")));
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !$("#dms-detail").hidden && !document.querySelector("dialog[open]")) closeDetail(); });

  load().then(() => { if (state.selected) openDocument(state.selected); });
  if (params.get("action") === "upload") openUpload();
})();
