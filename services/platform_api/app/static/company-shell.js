(() => {
  const platformBase = `${window.location.protocol}//${window.location.hostname}:8088`;
  const hostHref = (port, path = "") => `${window.location.protocol}//${window.location.hostname}:${port}${path}`;
  const appId = document.querySelector('meta[name="company-shell-app"]')?.content || "app";
  if (appId === "erp" && window.location.pathname === "/login" && !new URLSearchParams(window.location.search).has("localLogin")) {
    const keycloakLink = [...document.querySelectorAll("a[href]")]
      .find((link) => link.href.includes("/protocol/openid-connect/auth"));
    const lastAttempt = Number(window.sessionStorage.getItem("flow-erp-sso-attempt") || 0);
    if (keycloakLink && Date.now() - lastAttempt > 10000) {
      window.sessionStorage.setItem("flow-erp-sso-attempt", String(Date.now()));
      window.location.replace(keycloakLink.href);
      return;
    }
  }
  const catalog = {
    erp: { short: "ERP", name: "FLOWERP", area: "ERPNext", href: hostHref(8081) },
    dms: { short: "DMS", name: "FLOWDOC", area: "Paperless-ngx", href: hostHref(8010) },
    wiki: { short: "DOC", name: "FLOWDOCS", area: "Prozess-Wiki", href: hostHref(8001) },
    redmine: { short: "TASK", name: "FLOWTASK", area: "Redmine", href: hostHref(8011) },
    keycloak: { short: "ID", name: "FLOWID", area: "Konto & SSO", href: hostHref(8082) },
    ai: { short: "AI", name: "FLOWAI", area: "Lokale Unternehmens-KI", href: hostHref(3001) },
    "ai-gateway": { short: "GW", name: "FLOWGATE", area: "KI-Gateway & Richtlinien", href: hostHref(4001, "/ui/") },
    grafana: { short: "BI", name: "FLOWINSIGHT", area: "Grafana", href: hostHref(3000) },
    prometheus: { short: "OPS", name: "FLOWOPS", area: "Prometheus", href: hostHref(9090) },
    api: { short: "API", name: "FLOWAPI", area: "Integration", href: `${platformBase}/docs` },
  };
  const app = catalog[appId] || { short: "APP", name: "FLOWAPP", area: "Unternehmensanwendung", href: window.location.href };

  window.PlatformLauncherConfig = {
    platformBase,
    identityEndpoint: appId === "api" ? "/auth/me" : "/_company/auth/me",
  };
  if (appId === "dms") {
    document.documentElement.setAttribute("data-bs-theme", "light");
    new MutationObserver(() => {
      if (document.documentElement.getAttribute("data-bs-theme") !== "light") {
        document.documentElement.setAttribute("data-bs-theme", "light");
      }
    }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-bs-theme"] });
  }
  document.documentElement.classList.add("company-shell-active", `company-shell-app-${appId}`);

  const rail = document.createElement("aside");
  rail.className = "company-shell-rail";
  rail.setAttribute("aria-label", "Unternehmensnavigation");
  rail.innerHTML = `
    <div class="company-shell-launcher"><button data-app-launcher aria-label="Unternehmensanwendungen öffnen"></button></div>
    <a class="company-shell-product" href="${app.href}" title="${app.name} · ${app.area}">
      <span>${app.short}</span><b>${app.name}</b><small>${app.area}</small>
    </a>
    <nav class="company-shell-shortcuts" aria-label="Schnellnavigation">
      <a href="${platformBase}/" title="FLOWPORTAL"><span>⌂</span><small>PORTAL</small></a>
      <a href="${platformBase}/work" title="FLOWWORK"><span>R</span><small>WORK</small></a>
      <a href="${platformBase}/quality" title="FLOWQ"><span>Q</span><small>QS</small></a>
      <a href="${platformBase}/mes" title="FLOWMES"><span>▦</span><small>MES</small></a>
      <a href="${hostHref(8001)}" title="FLOWDOCS"><span>?</span><small>DOCS</small></a>
    </nav>
    <div class="company-shell-state" title="Unternehmensplattform verbunden"><i></i><span>Online</span></div>`;
  document.body.prepend(rail);

  fetch(window.PlatformLauncherConfig.identityEndpoint, { headers: { Accept: "application/json" } })
    .then((response) => response.ok ? response.json() : null)
    .then((identity) => {
      const user = identity?.user;
      if (!user) return;
      const label = user.name || user.username || "Angemeldet";
      rail.querySelector(".company-shell-state span").textContent = label.split(" ")[0];
      rail.querySelector(".company-shell-state").title = label;
    })
    .catch(() => {});
})();
