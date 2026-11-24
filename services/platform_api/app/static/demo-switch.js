// Demo-Benutzerwechsel (nur wenn DEMO_USER_SWITCH aktiv ist). Zeigt die Demo-Konten mit Funktion,
// AD-Gruppen und Projektrechten. Der Wechsel meldet über Keycloak ab und mit vorbelegtem Konto neu an;
// Rollen kommen danach wie im Livebetrieb aus den AD-Gruppen, nie aus dem Browser.
(() => {
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const RIGHT = { aendern: ["ändern", "ds-right-edit"], lesen: ["lesen", "ds-right-read"], "": ["–", "ds-right-none"] };

  function style() {
    const css = document.createElement("style");
    css.textContent = `
      .ds-switch-btn{position:fixed;right:18px;bottom:18px;z-index:9000;display:flex;align-items:center;gap:8px;border:0;border-radius:999px;padding:9px 14px 9px 9px;background:#102126;color:#fff;font:600 13px/1.2 system-ui,sans-serif;box-shadow:0 10px 30px rgba(16,33,38,.25);cursor:pointer}
      .ds-switch-btn i{display:grid;place-items:center;width:26px;height:26px;border-radius:50%;background:#c8f04a;color:#102126;font-style:normal;font-weight:800}
      .ds-switch-btn small{display:block;font-weight:500;opacity:.7}
      .ds-switch-panel{position:fixed;right:18px;bottom:72px;z-index:9001;width:min(760px,calc(100vw - 32px));max-height:min(78vh,720px);overflow:auto;background:#fffdf8;color:#102126;border:1px solid rgba(16,33,38,.12);border-radius:16px;box-shadow:0 24px 70px rgba(16,33,38,.28);font:13px/1.45 system-ui,sans-serif}
      .ds-switch-panel header{position:sticky;top:0;background:#fffdf8;padding:14px 16px 10px;border-bottom:1px solid rgba(16,33,38,.1);display:flex;justify-content:space-between;gap:12px}
      .ds-switch-panel h3{margin:0;font-size:15px}.ds-switch-panel p{margin:4px 0 0;color:#66767a}
      .ds-switch-panel table{width:100%;border-collapse:collapse}
      .ds-switch-panel th,.ds-switch-panel td{padding:8px 10px;border-bottom:1px solid rgba(16,33,38,.08);text-align:left;vertical-align:top}
      .ds-switch-panel th{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:#66767a;background:#f3f2ed}
      .ds-switch-panel tr.current{background:#eef9d2}
      .ds-switch-panel a.ds-go{display:inline-block;padding:5px 10px;border-radius:8px;background:#0d756c;color:#fff;text-decoration:none;font-weight:600;white-space:nowrap}
      .ds-switch-panel .ds-groups{margin-top:3px;color:#66767a;font-size:11px}
      .ds-right{display:inline-block;min-width:46px;text-align:center;padding:2px 6px;border-radius:6px;font-size:11px;font-weight:700}
      .ds-right-edit{background:#c8f04a;color:#102126}.ds-right-read{background:#dcebf5;color:#1c4b6b}.ds-right-none{color:#9aa5a8}
      .ds-switch-panel .ds-close{border:0;background:none;font-size:20px;cursor:pointer;color:#66767a}
      .ds-switch-panel footer{padding:10px 16px;color:#66767a;font-size:12px}`;
    document.head.append(css);
  }

  function render(data) {
    const codes = Object.keys(data.projects || {});
    const button = document.createElement("button");
    const me = (data.accounts || []).find((a) => a.username === data.current);
    button.className = "ds-switch-btn";
    button.type = "button";
    button.innerHTML = `<i>⇄</i><span>Person wechseln<small>${esc(me ? `${me.name} · ${me.function}` : data.current || "Demo")}</small></span>`;
    const panel = document.createElement("section");
    panel.className = "ds-switch-panel";
    panel.hidden = true;
    panel.setAttribute("aria-label", "Demo-Konto wechseln");
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    panel.innerHTML = `<header><div><h3>Demo: zwischen Personen wechseln</h3>
        <p>Rechte kommen aus den AD-Gruppen (AD → Keycloak-Gruppe → Realm-Rolle). Der Wechsel meldet bei FLOWID ab und mit dem gewählten Konto neu an.</p></div>
        <button class="ds-close" type="button" aria-label="Schließen">×</button></header>
      <table><thead><tr><th>Person</th><th>Funktion</th>${codes.map((c) => `<th title="${esc(data.projects[c].title)}">${esc(c)}</th>`).join("")}<th></th></tr></thead>
      <tbody>${(data.accounts || []).map((a) => `<tr class="${a.username === data.current ? "current" : ""}">
        <td><b>${esc(a.name)}</b><div class="ds-groups">${esc(a.username)} · ${esc(a.department)}</div></td>
        <td>${esc(a.function)}<div class="ds-groups">${esc((a.groups || []).filter((g) => g.includes("FLOW-AGENTS") || g.includes("PLATFORM-ADMIN")).join(", "))}</div></td>
        ${codes.map((c) => { const [label, cls] = RIGHT[(a.projects || {})[c] || ""]; return `<td><span class="ds-right ${cls}">${label}</span></td>`; }).join("")}
        <td>${a.username === data.current ? "<b>angemeldet</b>" : data.enabled ? `<a class="ds-go" href="/auth/switch?user=${encodeURIComponent(a.username)}&next=${next}">Wechseln</a>` : "–"}</td></tr>`).join("")}</tbody></table>
      <footer>ändern = Aufträge einreichen und Arbeitspakete starten (mit Funktion Product Owner oder Tech Lead) · lesen = Projekt sehen und als Mitglied entscheiden · ISB und Geschäftsführung sehen alle Projekte (Aufsicht). Kennwort der Demo-Konten: Wiki „Demo-Projekte und Projektrechte“.</footer>`;
    button.addEventListener("click", () => { panel.hidden = !panel.hidden; });
    panel.querySelector(".ds-close").addEventListener("click", () => { panel.hidden = true; });
    document.body.append(panel, button);
  }

  async function init() {
    try {
      const response = await fetch("/api/auth/demo-accounts", { headers: { Accept: "application/json" } });
      if (!response.ok) return;
      style();
      render(await response.json());
    } catch (_) { /* Benutzerwechsel ist optional. */ }
  }

  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", init) : init();
})();
