(() => {
  const launcherConfig = window.PlatformLauncherConfig || {};
  const platformBase = String(launcherConfig.platformBase || "").replace(/\/$/, "");
  const platformHref = (path) => `${platformBase}${path}`;
  const hostHref = (port, path = "") => `${window.location.protocol}//${window.location.hostname}:${port}${path}`;
  const apps = [
    { id: "portal", name: "FLOWPORTAL", short: "FP", description: "Zentrale Unternehmensoberfläche", href: platformHref("/"), group: "Meine Arbeit", color: "#0d756c" },
    { id: "work", name: "FLOWWORK", short: "FW", description: "Tickets, Wiki & Requirements", href: platformHref("/work"), group: "Meine Arbeit", color: "#334fbc", roles: ["work-user", "requirements-user", "work-admin"] },
    { id: "erp", name: "FLOWERP", short: "ERP", description: "ERPNext · CRM, Einkauf & Aufträge", href: hostHref(8081), group: "Meine Arbeit", color: "#198c92", roles: ["sales-user", "procurement-user", "planning-user", "production-user", "warehouse-user", "finance-user", "project-user", "quality-user"] },
    { id: "quality", name: "FLOWQ", short: "QS", description: "Wareneingangsprüfung & Messmittel", href: platformHref("/quality"), group: "Meine Arbeit", color: "#08776e", roles: ["quality-user", "warehouse-user", "procurement-user"] },
    { id: "mes", name: "FLOWMES", short: "MES", description: "Shopfloor & Rückmeldungen", href: platformHref("/mes"), group: "Meine Arbeit", color: "#e66d32", roles: ["production-user", "planning-user", "quality-user"] },
    { id: "hr", name: "FLOWHR", short: "HR", description: "Anwesenheit, Urlaub & Payroll", href: platformHref("/hr"), group: "Meine Arbeit", color: "#8b4d9d", roles: ["hr-user", "hr-admin"] },
    { id: "desk", name: "FLOWSPACE", short: "DS", description: "Arbeitsplatz buchen", href: platformHref("/desksharing"), group: "Meine Arbeit", color: "#2877a9", roles: ["desksharing-user", "desksharing-admin"] },
    { id: "agents", name: "FLOWAGENTS", short: "AG", description: "Agentenzentrale · KI-Team, Gates & Entscheidungen", href: platformHref("/agents"), group: "Meine Arbeit", color: "#5f7d12" },
    { id: "dms", name: "FLOWDOC", short: "DMS", description: "Dokumente finden, ablegen & freigeben", href: platformHref("/dms"), group: "Wissen & Steuerung", color: "#4b7a3b", roles: ["dms-user", "project-user", "hr-user", "hr-admin"] },
    { id: "dms-admin", name: "FLOWDOC Admin", short: "PL", description: "Paperless-ngx · Ablageregeln & Administration", href: hostHref(8010), group: "Administration", color: "#4b7a3b", roles: ["platform-admin"] },
    { id: "wiki", name: "FLOWDOCS", short: "DOC", description: "Prozesse, Anleitungen & Migration", href: hostHref(8001), group: "Wissen & Steuerung", color: "#59666b" },
    { id: "management", name: "FLOWMANAGE", short: "MGT", description: "End-to-End-Management-Demo", href: platformHref("/management"), group: "Wissen & Steuerung", color: "#102126", roles: ["management-user"] },
    { id: "finance", name: "FLOWFIN", short: "FIN", description: "Management, Forecast & Finanzen", href: platformHref("/finance"), group: "Wissen & Steuerung", color: "#08776e", roles: ["finance-user", "management-user"] },
    { id: "grafana", name: "FLOWINSIGHT", short: "BI", description: "Grafana · Fertigung, CRM & Management", href: hostHref(3000), group: "Wissen & Steuerung", color: "#e88327", roles: ["grafana-viewer"] },
    { id: "ai", name: "FLOWAI", short: "AI", description: "Lokale KI mit freigegebenem Wissen", href: hostHref(3001), group: "Wissen & Steuerung", color: "#6b58c9", roles: ["ai-user"] },
    { id: "ai-gateway", name: "FLOWGATE", short: "GW", description: "Agentgateway · Modelle, Schlüssel & Richtlinien", href: hostHref(4001, "/ui/"), group: "Administration", color: "#5a48b8", roles: ["platform-admin"] },
    { id: "redmine", name: "FLOWTASK", short: "TASK", description: "Redmine · Tickets & Ausführung", href: hostHref(8011), group: "Administration", color: "#b83d45", roles: ["work-admin", "it-user"] },
    { id: "keycloak", name: "FLOWID", short: "ID", description: "Keycloak · Konto, Rollen & SSO", href: hostHref(8082, "/realms/open-manufacturing/account"), group: "Administration", color: "#3c647c" },
    { id: "api", name: "FLOWAPI", short: "API", description: "OpenAPI, Integration & Migration", href: platformHref("/docs"), group: "Administration", color: "#0d756c", roles: ["it-user"] },
    { id: "prometheus", name: "FLOWOPS", short: "OPS", description: "Prometheus · Betrieb & Monitoring", href: hostHref(9090), group: "Administration", color: "#ca4c36", roles: ["it-user"] },
  ];

  const tourSteps = [
    { app: "FLOWMANAGE", title: "Auftrag und Zielbild", summary: "Auftrag SO-4711, Liefertermin, Wertstrom, Prozessstatus und Management-Kennzahlen bilden den roten Faden.", action: "Auftragskarte, Prozessleiste und Systemereignisse zeigen.", href: platformHref("/management#cockpit") },
    { app: "FLOWPORTAL", title: "Persönlicher KI-Arbeitsplatz", summary: "Das Portal priorisiert Aufgaben, Termine und Risiken rollenabhängig und stellt passende KI-Agenten sowie MCP-Werkzeuge bereit.", action: "Felix Hoffmann wählen, 80 Prozent Liefertermintreue und die Lieferantenrückfrage zeigen; danach auf Helena Friedrich wechseln.", href: platformHref("/?user_id=USR-006&date=2026-11-05"), activateSelector: '[data-tour="future-workplace"]' },
    { app: "FLOWMANAGE", title: "Zielbild Arbeitsplatz 2028", summary: "Standardfälle laufen innerhalb geprüfter Grenzen im Hintergrund. Menschen erhalten eine Entscheidungs-Inbox für Ausnahmen, Beziehungen, Reviews und verantwortliche Freigaben.", action: "Arbeitsteilung und vier Ausnahmefälle zeigen. Danach zu Agentenregister, A0 bis A4, Vier-Stufen-Roadmap und Live-Leitplanken scrollen.", href: platformHref("/management#future-model"), activateSelector: '[data-tour="future-operating-model"]' },
    { app: "FLOWID", title: "Vom AD-Konto zu allen Anwendungen", summary: "Die AD-Simulation liefert 51 Identitäten und 21 Sicherheitsgruppen. Keycloak föderiert die Identitäten, übernimmt SSO und übersetzt Gruppen in die Rollen der Anwendungen.", action: "Bei Felix Hoffmann die geerbten Gruppen zeigen und die Kette AD-Gruppe → Keycloak-Gruppe → Realm-Rolle → Anwendung erläutern.", href: platformHref("/management#iam-sso"), activateSelector: '[data-tour="iam-sso"]' },
    { app: "FLOWERP", title: "Kunde und Opportunity", summary: "ERPNext hält Kundenstamm, Opportunity, Angebot, Auftrag und die kaufmännische Belegkette.", action: "Kunde, fünf SCU-100, Wahrscheinlichkeit und Zieltermin erläutern.", href: hostHref(8081, "/app/opportunity/OPP-2027-0018") },
    { app: "FLOWERP", title: "Projekt, Lager und Fertigung", summary: "Kommission, Konditionen, Lagerorte, BOM, Arbeitsplätze, Work Orders und Seriennummern liegen im führenden ERP.", action: "Projektbezug, Warehouse Tree und BOM-Operations zeigen.", href: hostHref(8081, "/app/work-order") },
    { app: "FLOWQ", title: "Wareneingang einfach prüfen", summary: "FLOWQ lädt Bestellung, Charge, freigegebenen Prüfplan und Stichprobenumfang aus dem Prozesskontext und führt Schritt für Schritt durch die Prüfung.", action: "PREC-2027-0045 scannen, acht Stichproben zeigen und einen Messwert automatisch übernehmen.", href: platformHref("/quality?receipt=PREC-2027-0045"), activateSelector: '[data-tour="incoming-inspection"]' },
    { app: "FLOWWORK", title: "Anforderungen und Aufgaben", summary: "Requirements, Tickets, Wiki, Tests und Baselines sind über nachvollziehbare Referenzen verbunden.", action: "Requirement Center und Traceability öffnen.", href: platformHref("/work?view=requirements") },
    { app: "FLOWWORK", title: "Jama-Connect-Funktionsumfang", summary: "Eigene Elementtypen und Felder, konfigurierbare Beziehungen, Suspect Links, Reviews mit Signatur, Baselines, Varianten, Risiken und Testmanagement sind in FLOWWORK demonstrierbar.", action: "Review Center öffnen und danach Beziehungskonfiguration sowie Tests erläutern.", href: platformHref("/work?view=reviews"), activateSelector: '[data-view="reviews"]' },
    { app: "FLOWMES", title: "Nächster ausführbarer Arbeitsgang", summary: "Das MES zeigt Bedienperson, Arbeitsplatz, Route, Sollzeit und nur freigegebene Tätigkeiten.", action: "Arbeitsvorrat, Anweisung und Pflichtcheckliste zeigen.", href: platformHref("/mes"), activateSelector: '[data-tab="instructions"]' },
    { app: "FLOWMES", title: "Zeit, Material und Qualität", summary: "Start, Pause, Nacharbeit, Seriennummern und Prüfmerkmale erzeugen belastbare Rückmeldedaten.", action: "Zeitbuchungen und Qualitätsprüfung des aktiven Jobs öffnen.", href: platformHref("/mes"), activateSelector: '[data-tab="time"]' },
    { app: "FLOWDOC", title: "Dokumentenlenkung", summary: "FLOWDOC verwaltet Metadaten, Projektzuordnung, Liefertermine, Baselines, Rollen und Freigabeworkflows.", action: "Freigegebene Projektdokumente und Workflowstatus zeigen.", href: hostHref(8010, "/dashboard") },
    { app: "FLOWHR", title: "Anwesenheit und Teamkalender", summary: "Anwesenheit, Urlaub, Überstundenabbau und Mehrarbeitsanträge sind im persönlichen und Teamkalender sichtbar.", action: "Tagessaldo, Abwesenheiten und Genehmigungen zeigen.", href: platformHref("/hr?view=calendar"), activateSelector: '[data-view="calendar"]' },
    { app: "FLOWHR", title: "Recruiting und Payroll", summary: "Bewerbungen besitzen geschützte DMS-Akten. Die Payroll-Demo nutzt Vorschau, Vier-Augen-Freigabe und PDF.", action: "Bewerberprofil und Abrechnungslauf zeigen.", href: platformHref("/hr?view=recruiting"), activateSelector: '[data-view="recruiting"]' },
    { app: "FLOWSPACE", title: "Gebäudeplan und Kollegensuche", summary: "Der interaktive Etagenplan zeigt Räume, freie Arbeitsplätze und die sichtbaren Buchungen von Kollegen an zwei Standorten.", action: "Teamraum Kreuzberg öffnen, freien Platz buchen und den Arbeitsplatz von Felix Hoffmann im Grundriss markieren.", href: platformHref("/desksharing?date=2026-11-05&site=BER&floor=EG&room=BER-EG-TEAM&colleague=Felix%20Hoffmann"), activateSelector: '[data-tour="floor-plan"]' },
    { app: "FLOWFIN", title: "Umsatz, Projekte und Finanzprozesse", summary: "Forecast, Marge, Cash, Budgets, Auslagen und Anlagen verbinden operative Daten mit Managemententscheidungen.", action: "Erwarteten Umsatz aus laufender Produktion und Lieferrisiken zeigen.", href: platformHref("/finance?view=revenue"), activateSelector: '[data-view="revenue"]' },
    { app: "FLOWINSIGHT", title: "Management-Dashboards", summary: "Grafana visualisiert Aufträge je aktuellem Arbeitsgang, Arbeitsplatzlast, CRM-Pipeline bis 2031, Umsatz, Marge, Dokumententermine und Qualität.", action: "Vom Executive Cockpit in Fertigung und CRM-Pipeline wechseln.", href: hostHref(3000, "/d/management-executive") },
    { app: "FLOWGATE", title: "Zentrales Open-Source-KI-Gateway", summary: "Agentgateway stellt die lokalen Qwen-Modelle über eine OpenAI-kompatible Schnittstelle bereit. Virtuelle Schlüssel, Modellfreigaben und Protokollierung werden zentral durchgesetzt; die Administration ist nur für die Keycloak-Gruppe platform-admin sichtbar.", action: "Qwen3 und Qwen3-Coder in der Modellliste sowie den eingeschränkten Open-WebUI-Dienstschlüssel zeigen.", href: hostHref(4001, "/ui/llm/models") },
    { app: "FLOWAI", title: "Lokale Unternehmens-KI", summary: "Open WebUI nutzt das persönliche Tagesbriefing sowie freigegebene ERP-, DMS- und Wiki-Werkzeuge über drei MCP-Verbindungen.", action: "Persönliches Briefing abrufen, Quellen öffnen und eine vorgeschlagene Fachaktion zusammenfassen lassen.", href: hostHref(3001) },
    { app: "FLOWDOCS", title: "Prozess- und Benutzerdokumentation", summary: "Gesamtprozess, Abteilungsanleitungen, Screenshots, Stammdaten, Migration und Betrieb sind gemeinsam dokumentiert.", action: "Order-to-Cash und Migration/API öffnen.", href: hostHref(8001, "/user-guides/presentation/") },
    { app: "FLOWTASK", title: "Tickets und Ausführung", summary: "Redmine hält Aufgaben, Zuständigkeiten, Termine und Wiki-Inhalte. FLOWWORK ergänzt Requirements und Traceability.", action: "SCU-100-Projekt und verknüpfte Tickets zeigen.", href: hostHref(8011, "/projects/scu-100/issues") },
    { app: "FLOWID", title: "Keycloak-Gruppen und SSO live", summary: "Die simulierten AD-Sicherheitsgruppen sind in Keycloak sichtbar und tragen die Anwendungsrollen. Eine bestehende Keycloak-Sitzung öffnet Grafana, ERP, DMS und weitere Anwendungen ohne zweite Passworteingabe.", action: "AD-GG-FLOW-PROCUREMENT-USER öffnen, Rollenvererbung zeigen und anschließend FLOWINSIGHT ohne erneute Anmeldung öffnen.", href: hostHref(8082, "/admin/open-manufacturing/console/#/open-manufacturing/groups") },
    { app: "FLOWAPI", title: "Integration und Migration", summary: "Die versionierten APIs unterstützen Stammdaten, Prozesse, Demo-Lifecycle und die spätere KI-gestützte Migrationsplanung.", action: "OpenAPI-Endpunkte und Migrationsgrenzen zeigen.", href: platformHref("/docs") },
    { app: "FLOWOPS", title: "Betrieb und Monitoring", summary: "Healthchecks, Prometheus, Tests, Backups, Rechteprüfungen und Updatepfade bilden die technische Betriebsbasis.", action: "Servicezustand und zentrale Metriken zeigen.", href: hostHref(9090, "/query") },
    { app: "FLOWMANAGE", title: "Entscheidungsstand und Entstehungsaufwand", summary: "Der Rundgang endet bei Pilotumfang, Fit-Gaps, Integrationsgrenzen und einer transparent als Schätzung gekennzeichneten Aufwandsbetrachtung. Exakte historische Modell- oder GPU-Zeit ist nicht verfügbar und wird im Pilot künftig gemessen.", action: "Schätzkorridor für Fachaufwand und Agentenarbeit einordnen, Ergebnis zusammenfassen und Demo bei Bedarf zurücksetzen.", href: platformHref("/management#delivery-evidence") },
  ];

  const state = { identity: { mode: "demo", authenticated: false, user: null }, available: [] };
  const adminRoles = new Set(["platform-admin"]);
  const isExternal = (href) => /^https?:\/\//.test(href);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);

  function allowed(app) {
    if (state.identity.mode !== "oidc") return true;
    const roles = new Set(state.identity.user?.roles || []);
    if ([...adminRoles].some((role) => roles.has(role))) return true;
    return !app.roles?.length || app.roles.some((role) => roles.has(role));
  }

  function launcherButton() {
    return `<span class="platform-launcher-sr">Anwendungen öffnen</span>${"<i></i>".repeat(9)}`;
  }

  function renderPanel(panel) {
    const groups = [...new Set(state.available.map((app) => app.group))];
    const userName = state.identity.user?.name || state.identity.user?.username || "Lokale Demo";
    panel.innerHTML = `<div class="platform-launcher-head"><div><b>Unternehmensanwendungen</b><small>${escapeHtml(userName)}</small></div><button class="platform-launcher-close" type="button" aria-label="App-Menü schließen">×</button></div><div class="platform-launcher-content">${groups.map((group) => `<div class="platform-launcher-group-title">${escapeHtml(group)}</div><div class="platform-launcher-grid">${state.available.filter((app) => app.group === group).map((app) => `<a class="platform-launcher-app" href="${escapeHtml(app.href)}" ${isExternal(app.href) ? 'target="_blank" rel="noopener"' : ""}><span class="platform-launcher-icon" style="--app-color:${app.color}">${escapeHtml(app.short)}</span><span><b>${escapeHtml(app.name)}</b><small>${escapeHtml(app.description)}</small></span></a>`).join("")}</div>`).join("") || '<p class="platform-launcher-empty">Für deine Rolle sind noch keine Anwendungen freigegeben.</p>'}</div>`;
  }

  function setupLauncher() {
    const buttons = [...document.querySelectorAll("[data-app-launcher]")];
    buttons.forEach((button) => { button.classList.add("platform-launcher-button"); button.type = "button"; button.setAttribute("aria-haspopup", "dialog"); button.setAttribute("aria-expanded", "false"); button.innerHTML = launcherButton(); });
    if (!buttons.length) return;
    const backdrop = document.createElement("div");
    backdrop.className = "platform-launcher-backdrop";
    const panel = document.createElement("section");
    panel.className = "platform-launcher-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Unternehmensanwendungen");
    document.body.append(backdrop, panel);
    renderPanel(panel);

    const close = () => { backdrop.classList.remove("open"); panel.classList.remove("open"); buttons.forEach((button) => button.setAttribute("aria-expanded", "false")); };
    const open = (button) => { renderPanel(panel); backdrop.classList.add("open"); panel.classList.add("open"); button.setAttribute("aria-expanded", "true"); panel.querySelector(".platform-launcher-close")?.focus(); };
    buttons.forEach((button) => button.addEventListener("click", () => panel.classList.contains("open") ? close() : open(button)));
    backdrop.addEventListener("click", close);
    panel.addEventListener("click", (event) => { if (event.target.closest(".platform-launcher-close")) close(); });
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") close(); });
  }

  function tourHref(index) {
    const step = tourSteps[index];
    const target = new URL(step.href, window.location.href);
    target.searchParams.set("managementDemo", "1");
    target.searchParams.set("tourStep", String(index));
    return target.href;
  }

  function setupManagementTour() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("managementDemo") !== "1") return;
    const requested = Number.parseInt(params.get("tourStep") || "0", 10);
    const index = Number.isFinite(requested) ? Math.max(0, Math.min(tourSteps.length - 1, requested)) : 0;
    const step = tourSteps[index];
    const tour = document.createElement("aside");
    tour.className = "platform-tour";
    tour.setAttribute("aria-label", "Geführte Management-Demo");
    tour.innerHTML = `
      <div class="platform-tour-progress"><span style="width:${Math.round(((index + 1) / tourSteps.length) * 100)}%"></span></div>
      <div class="platform-tour-head"><span>${escapeHtml(step.app)}</span><b>Schritt ${index + 1} / ${tourSteps.length}</b></div>
      <h2>${escapeHtml(step.title)}</h2>
      <p>${escapeHtml(step.summary)}</p>
      <div class="platform-tour-action"><b>Live-Aktion</b><span>${escapeHtml(step.action)}</span></div>
      <div class="platform-tour-buttons">
        ${index > 0 ? `<a class="platform-tour-back" href="${escapeHtml(tourHref(index - 1))}">Zurück</a>` : '<span></span>'}
        <a class="platform-tour-next" href="${escapeHtml(index + 1 < tourSteps.length ? tourHref(index + 1) : platformHref("/management"))}">${index + 1 < tourSteps.length ? "Weiter" : "Rundgang beenden"}<span>→</span></a>
      </div>
      <a class="platform-tour-close" href="${escapeHtml(platformHref("/management"))}" aria-label="Rundgang beenden">×</a>`;
    document.body.append(tour);
    document.documentElement.classList.add("platform-tour-active");
    if (step.activateSelector) {
      window.setTimeout(() => {
        const target = document.querySelector(step.activateSelector);
        if (!target) return;
        target.click();
        target.classList.add("platform-tour-focus");
      }, 700);
    }
  }

  async function init() {
    try {
      const response = await fetch(launcherConfig.identityEndpoint || "/auth/me", { headers: { Accept: "application/json" } });
      if (response.ok) state.identity = await response.json();
    } catch (_) { /* Local demo remains usable without auth endpoint. */ }
    state.available = apps.filter(allowed);
    setupLauncher();
    setupManagementTour();
    document.dispatchEvent(new CustomEvent("platform-apps-ready", { detail: state }));
  }

  window.PlatformApps = { apps, state, allowed, escapeHtml, isExternal, tourSteps, tourHref };
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", init) : init();
})();
