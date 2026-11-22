const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => window.PlatformApps?.escapeHtml(value) || String(value ?? "");
const query = new URLSearchParams(window.location.search);
let workplaceData;

function setDate() {
  const now = new Date();
  const hour = now.getHours();
  const greeting = hour < 11 ? "Guten Morgen" : hour < 18 ? "Guten Tag" : "Guten Abend";
  $("#greeting").textContent = `${greeting}.`;
  $("#today").textContent = now.toLocaleDateString("de-DE", { weekday: "long", day: "2-digit", month: "long" }).toUpperCase();
  $("#date-number").textContent = String(now.getDate()).padStart(2, "0");
  $("#date-copy").textContent = now.toLocaleDateString("de-DE", { weekday: "long", month: "long" });
}

function renderApps(detail) {
  const identity = detail.identity;
  const name = identity.user?.name || identity.user?.username || "Lokale Demo";
  const initials = name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
  $("#identity-name").textContent = name;
  $("#identity-avatar").textContent = initials || "OM";
  $("#identity-department").textContent = identity.user?.department || (identity.mode === "oidc" ? "Keycloak SSO" : "Demo-Modus");
  $("#identity-action").textContent = identity.authenticated ? "Abmelden" : "Anmelden";
  $("#identity-action").href = identity.authenticated ? identity.logout_url : `${identity.login_url}?next=/`;

  const grid = $("#application-grid");
  grid.innerHTML = detail.available.filter((app) => !["prometheus", "api", "redmine"].includes(app.id)).map((app) => `<a class="application-card" data-app-name="${escapeHtml(`${app.name} ${app.description}`.toLowerCase())}" href="${escapeHtml(app.href)}" ${window.PlatformApps.isExternal(app.href) ? 'target="_blank" rel="noopener"' : ""} style="--app-color:${app.color}"><span class="application-icon">${escapeHtml(app.short)}</span><span class="application-arrow">${window.PlatformApps.isExternal(app.href) ? "↗" : "→"}</span><h3>${escapeHtml(app.name)}</h3><p>${escapeHtml(app.description)}</p></a>`).join("");
}

function setPrompt(prompt) {
  $("#selected-prompt").textContent = prompt;
}

function renderWorkplace(data) {
  workplaceData = data;
  $("#daily-role").textContent = `${data.role.label.toUpperCase()} · ${data.user.name.toUpperCase()}`;
  $("#daily-headline").textContent = data.headline;
  $("#daily-summary").textContent = data.summary;
  $("#daily-source-count").textContent = `${data.mcp.connected_servers.length} MCP-Quellen`;
  $("#focus-count").textContent = `${data.actions.length} Aktionen`;
  $("#daily-kpis").innerHTML = data.kpis.map((item) => `<article class="daily-kpi ${escapeHtml(item.tone)}"><small>${escapeHtml(item.label)}</small><b>${escapeHtml(item.value)}</b><span>${escapeHtml(item.detail)}</span></article>`).join("");
  $("#daily-actions").innerHTML = data.actions.map((action) => `<article class="focus-action ${escapeHtml(action.priority)}"><span class="focus-priority"></span><div><a href="${escapeHtml(action.href)}"><b>${escapeHtml(action.title)}</b></a><small>${escapeHtml(action.detail)}</small></div><div class="focus-meta"><span>${escapeHtml(action.source)}</span><button type="button" data-ai-prompt="${escapeHtml(action.ai_prompt)}">Mit KI besprechen</button></div></article>`).join("");
  $("#agent-list").innerHTML = data.agents.map((agent) => `<article class="agent-item"><span>AI</span><span><b>${escapeHtml(agent.name)}</b><small>${escapeHtml(agent.scope)}</small></span><i class="agent-status" title="verfügbar"></i></article>`).join("");
  $("#today-list").innerHTML = data.actions.slice(0, 5).map((action) => `<a href="${escapeHtml(action.href)}"><span class="today-icon ${escapeHtml(action.priority)}">${action.priority === "critical" ? "!" : "·"}</span><span><b>${escapeHtml(action.title)}</b><small>${escapeHtml(action.source)}</small></span></a>`).join("");
  setPrompt(data.suggested_prompts.at(-1));
  document.querySelectorAll("[data-ai-prompt]").forEach((button) => button.addEventListener("click", () => setPrompt(button.dataset.aiPrompt)));
}

async function loadWorkplace(userId) {
  const selectedDate = query.get("date") || new Date().toISOString().slice(0, 10);
  const response = await fetch(`/api/workplace/today?user_id=${encodeURIComponent(userId)}&selected_date=${encodeURIComponent(selectedDate)}`, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("Persönliches Tagesbriefing ist nicht verfügbar");
  renderWorkplace(await response.json());
}

async function initWorkplace() {
  try {
    const response = await fetch("/api/workplace/profiles", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("Rollenprofile konnten nicht geladen werden");
    const result = await response.json();
    const select = $("#workplace-profile");
    select.innerHTML = result.profiles.map((profile) => `<option value="${escapeHtml(profile.id)}">${escapeHtml(profile.name)} · ${escapeHtml(profile.role)}</option>`).join("");
    const requested = query.get("user_id") || "USR-006";
    select.value = result.profiles.some((profile) => profile.id === requested) ? requested : "USR-006";
    await loadWorkplace(select.value);
    select.addEventListener("change", async () => {
      query.set("user_id", select.value);
      history.replaceState(null, "", `${location.pathname}?${query}`);
      await loadWorkplace(select.value);
    });
  } catch (error) {
    $("#daily-headline").textContent = error.message;
    $("#daily-actions").innerHTML = `<div class="loading-card">${escapeHtml(error.message)}</div>`;
  }
}

async function renderWork() {
  try {
    const response = await fetch("/api/work/dashboard", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("FLOWWORK nicht freigegeben");
    const data = await response.json();
    const urgent = data.issues.filter((issue) => !/erledigt|closed|done/i.test(issue.status)).slice(0, 3);
    $("#work-overview").innerHTML = `<article class="work-metric"><small>Offene Tickets</small><b>${data.metrics.open_tasks}</b></article><article class="work-metric"><small>Anforderungen</small><b>${data.metrics.requirements}</b></article><article class="work-metric"><small>Traceability</small><b>${data.metrics.trace_coverage}%</b></article>${urgent.map((task) => `<a class="work-task" href="/work#issue-${escapeHtml(task.id)}"><span class="task-key">${escapeHtml(task.key)}</span><b>${escapeHtml(task.subject)}</b><small>${escapeHtml(task.assignee)}</small></a>`).join("")}`;
  } catch (error) {
    $("#work-overview").innerHTML = `<div class="loading-card">${escapeHtml(error.message)}</div>`;
  }
}

document.addEventListener("platform-apps-ready", (event) => renderApps(event.detail));
$("#app-search").addEventListener("input", (event) => {
  const search = event.target.value.trim().toLowerCase();
  let visible = 0;
  document.querySelectorAll(".application-card").forEach((card) => {
    const show = !search || card.dataset.appName.includes(search);
    card.hidden = !show;
    if (show) visible += 1;
  });
  $("#app-empty").hidden = visible !== 0;
});
$("#show-all-apps").addEventListener("click", () => document.querySelector("[data-app-launcher]")?.click());
$("#copy-prompt").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    await navigator.clipboard.writeText($("#selected-prompt").textContent);
    button.textContent = "Kopiert";
    setTimeout(() => { button.textContent = "Prompt kopieren"; }, 1800);
  } catch {
    button.textContent = "Bitte manuell kopieren";
  }
});

// Prüfaufgaben der Agenten: worauf geht die Aufgabe zurück, wo kann ich das Ergebnis ansehen?
async function loadReviewTasks() {
  const target = $("#review-tasks");
  try {
    const response = await fetch("/api/agents/overview", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("Agentenzentrale nicht verfügbar");
    const data = await response.json();
    const roles = new Set(data.viewer?.roles || []);
    const mine = (data.decisions || []).filter((d) => {
      const allowed = data.human_roles?.[d.decider]?.keycloak_roles || [];
      return allowed.some((role) => roles.has(role)) || (data.demo_mode && roles.has("platform-admin"));
    });
    const draftsResponse = await fetch("/api/agents/drafts", { headers: { Accept: "application/json" } });
    const drafts = draftsResponse.ok ? (await draftsResponse.json()).drafts || [] : [];
    $("#review-count").textContent = mine.length + drafts.length ? `${mine.length + drafts.length} offen` : "";
    const preview = (d) => (/^http:\/\/localhost:\d+(\/[a-z]*)?$/.test(d.context?.preview_url || "") ? d.context.preview_url : "");
    const draftCards = drafts.map((d) => `<article class="focus-action review-task"><span class="focus-priority"></span><div><b>Vorschlag aus FLOWAI: ${escapeHtml(d.title)}</b><small><span class="ref">${escapeHtml(d.id)}</span>${escapeHtml(d.goal)}</small><div class="review-links"><a class="primary" href="/agents?draft=${encodeURIComponent(d.id)}">Prüfen und einreichen</a><a href="#" data-discard="${escapeHtml(d.id)}">Verwerfen</a></div></div><div class="focus-meta"><span>Fachauftrag</span></div></article>`).join("");
    target.innerHTML = draftCards + (mine.length || drafts.length ? "" : "") + (mine.length ? mine.map((d) => `<article class="focus-action review-task ${d.gate === "G4" ? "g4" : ""}"><span class="focus-priority"></span><div><b>${escapeHtml(d.title)}</b><small><span class="ref">${escapeHtml(d.auftrag?.id || d.run_id)}</span>${escapeHtml(d.auftrag?.title || "")}${d.auftrag?.requested_by ? ` · beauftragt von ${escapeHtml(d.auftrag.requested_by)}` : ""}</small>${d.gate === "G4" && d.auftrag?.success_example ? `<small>Prüfe: ${escapeHtml(d.auftrag.success_example)}</small>` : ""}<div class="review-links">${preview(d) ? `<a class="primary" href="${escapeHtml(preview(d))}" target="_blank" rel="noopener">Ergebnis ansehen ↗</a>` : ""}<a href="/agents?run=${encodeURIComponent(d.run_id)}">Auftrag öffnen</a><a href="/agents#meine-entscheidungen">Entscheiden</a></div></div><div class="focus-meta"><span>${escapeHtml(data.human_roles?.[d.decider]?.label || d.decider)}</span></div></article>`).join("")
      : (drafts.length ? "" : `<div class="loading-card">${data.available === false ? "Agenten nicht verbunden." : "Nichts zu prüfen."}</div>`));
    target.querySelectorAll("[data-discard]").forEach((link) => link.addEventListener("click", async (event) => {
      event.preventDefault();
      if (!window.confirm("Vorschlag verwerfen?")) return;
      await fetch(`/api/agents/drafts/${encodeURIComponent(link.dataset.discard)}/discard`, { method: "POST" });
      loadReviewTasks();
    }));
    document.querySelectorAll("#today-list .review-today").forEach((element) => element.remove());
    const today = $("#today-list");
    if (today && mine.length) {
      today.insertAdjacentHTML("afterbegin", mine.slice(0, 3).map((d) => `<a class="review-today" href="${escapeHtml(preview(d) || `/agents?run=${encodeURIComponent(d.run_id)}`)}" ${preview(d) ? 'target="_blank" rel="noopener"' : ""}><span class="today-icon high">✓</span><span><b>${escapeHtml(d.title)}</b><small>${escapeHtml(d.auftrag?.id || "")} ${escapeHtml(d.auftrag?.title || "")}</small></span></a>`).join(""));
    }
  } catch (error) {
    target.innerHTML = `<div class="loading-card">${escapeHtml(error.message)}</div>`;
  }
}

setDate();
initWorkplace().then(loadReviewTasks);
renderWork();
setInterval(() => { if (!document.hidden) loadReviewTasks(); }, 15000);
