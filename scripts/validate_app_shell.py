#!/usr/bin/env python3
"""Validate the shared company shell in front of every external web app."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    completed = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "compose.yaml",
            "--profile",
            "full",
            "--profile",
            "work",
            "--profile",
            "webui",
            "--profile",
            "ops",
            "--profile",
            "iam",
            "--profile",
            "ai-gateway",
            "config",
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    services = json.loads(completed.stdout)["services"]
    expected = {
        "docs-shell": (8001, "docs:8000", "docs.conf", "wiki"),
        "erpnext-shell": (8081, "erpnext-frontend:8080", "erpnext.conf", "erp"),
        "paperless-shell": (
            8010,
            "paperless-webserver:8000",
            "paperless.conf",
            "dms",
        ),
        "redmine-shell": (8011, "redmine:3000", "redmine.conf", "redmine"),
        "keycloak-shell": (8082, "keycloak:8080", "keycloak.conf", "keycloak"),
        "open-webui-shell": (3001, "open-webui:8080", "open-webui.conf", "ai"),
        "agentgateway-shell": (
            4001,
            "agentgateway:4001",
            "agentgateway.conf",
            "ai-gateway",
        ),
        "prometheus-shell": (
            9090,
            "prometheus:9090",
            "prometheus.conf",
            "prometheus",
        ),
        "grafana-shell": (3000, "grafana:3000", "grafana.conf", "grafana"),
    }
    for service_name, (
        published_port,
        upstream,
        config_name,
        app_id,
    ) in expected.items():
        service = services[service_name]
        assert any(
            port["target"] == 8080 and port["published"] == str(published_port)
            for port in service["ports"]
        )
        config = (ROOT / "deployment" / "app-shell" / config_name).read_text(
            encoding="utf-8"
        )
        direct_proxy = f"proxy_pass http://{upstream};" in config
        dns_refreshed_proxy = upstream in config and "proxy_pass http://$" in config
        assert direct_proxy or dns_refreshed_proxy
        assert "sub_filter '</head>'" in config
        assert f'content="{app_id}"' in config
        assert "/_company/app-launcher.js" in config
        assert "/_company/app-launcher.css" in config
        assert "/_company/company-shell.js" in config
        assert "/_company/company-theme.css" in config
        assert "charset utf-8;" in config

        if service_name in {
            "docs-shell",
            "erpnext-shell",
            "paperless-shell",
            "redmine-shell",
            "open-webui-shell",
            "prometheus-shell",
        }:
            assert "include /etc/nginx/company/sso-server.inc;" in config
            assert any(
                mount["target"] == "/etc/nginx/company" and mount["read_only"]
                for mount in service["volumes"]
            )

    sso_include = (ROOT / "deployment" / "app-shell" / "sso-server.inc").read_text(
        encoding="utf-8"
    )
    sso_headers = (
        ROOT / "deployment" / "app-shell" / "sso-proxy-headers.inc"
    ).read_text(encoding="utf-8")
    assert "auth_request /_company/sso-auth;" in sso_include
    assert "X-Flow-Sso-User" in sso_headers
    assert "Remote-User" in sso_headers
    assert "auth/app-login?app_id=$flow_sso_app" in sso_include

    erp_shell = (ROOT / "deployment" / "app-shell" / "erpnext.conf").read_text(
        encoding="utf-8"
    )
    assert "return 302 /desk/setup/home;" in erp_shell
    assert "absolute_redirect off;" in erp_shell
    assert "proxy_set_header Host frontend;" in erp_shell
    assert "proxy_redirect http://localhost/ $scheme://$http_host/;" in erp_shell
    compose_source = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert "bench set-config -g webserver_host erpnext-backend;" in compose_source
    assert "bench set-config -gp webserver_port 8000;" in compose_source
    assert "PAPERLESS_ENABLE_HTTP_REMOTE_USER: \"true\"" in compose_source
    assert "WEBUI_AUTH_TRUSTED_EMAIL_HEADER: X-Flow-Sso-Email" in compose_source
    assert "FLOW_SSO_ENABLED: \"true\"" in compose_source
    assert "KC_PROXY_HEADERS: xforwarded" in compose_source
    assert 'bench --site frontend set-config host_name "$${ERPNEXT_PUBLIC_URL}";' in compose_source

    open_webui_shell = (
        ROOT / "deployment" / "app-shell" / "open-webui.conf"
    ).read_text(encoding="utf-8")
    assert "set $flow_open_webui_upstream open-webui:8080;" in open_webui_shell
    assert "proxy_pass http://$flow_open_webui_upstream;" in open_webui_shell

    realm = json.loads(
        (ROOT / "deployment" / "keycloak" / "realm.json").read_text(
            encoding="utf-8"
        )
    )
    demo_user = next(user for user in realm["users"] if user["username"] == "demo01")
    assert demo_user["clientRoles"]["realm-management"] == ["realm-admin"]
    erp_client = next(
        client for client in realm["clients"] if client["clientId"] == "erpnext"
    )
    assert erp_client["attributes"]["pkce.code.challenge.method"] == ""
    erp_seed = (ROOT / "deployment" / "erpnext" / "seed_demo.py").read_text(
        encoding="utf-8"
    )
    assert 'requested_roles.add("System Manager")' in erp_seed
    assert 'platform_admin="platform-admin" in entry["roles"]' in erp_seed

    for upstream in (
        "docs",
        "erpnext-frontend",
        "paperless-webserver",
        "redmine",
        "keycloak",
        "open-webui",
        "agentgateway",
        "prometheus",
        "grafana",
    ):
        assert not services[upstream].get("ports"), upstream

    shell_path = (
        ROOT
        / "services"
        / "platform_api"
        / "app"
        / "static"
        / "company-shell.js"
    )
    shell = shell_path.read_text(encoding="utf-8")
    assert "data-app-launcher" in shell
    assert "company-shell-rail" in shell
    assert "company-shell-active" in shell
    assert 'document.documentElement.setAttribute("data-bs-theme", "light")' in shell
    assert 'appId === "erp"' in shell
    assert "/protocol/openid-connect/auth" in shell
    for product in (
        "FLOWERP",
        "FLOWDOC",
        "FLOWDOCS",
        "FLOWTASK",
        "FLOWID",
        "FLOWAI",
        "FLOWGATE",
        "FLOWINSIGHT",
        "FLOWOPS",
        "FLOWAPI",
    ):
        assert product in shell

    launcher = (
        ROOT
        / "services"
        / "platform_api"
        / "app"
        / "static"
        / "app-launcher.js"
    ).read_text(encoding="utf-8")
    for product in (
        "FLOWPORTAL",
        "FLOWMANAGE",
        "FLOWWORK",
        "FLOWERP",
        "FLOWQ",
        "FLOWMES",
        "FLOWHR",
        "FLOWSPACE",
        "FLOWDOC",
        "FLOWDOCS",
        "FLOWFIN",
        "FLOWINSIGHT",
        "FLOWAI",
        "FLOWGATE",
        "FLOWTASK",
        "FLOWID",
        "FLOWAPI",
        "FLOWOPS",
    ):
        assert f'name: "{product}"' in launcher
    assert launcher.count("{ app:") == 25
    assert "AD-GG-FLOW-PROCUREMENT-USER" in launcher
    assert 'target.searchParams.set("managementDemo", "1")' in launcher
    assert 'target.searchParams.set("tourStep", String(index))' in launcher
    assert 'aria-label", "Geführte Management-Demo"' in launcher

    launcher_css = (
        ROOT
        / "services"
        / "platform_api"
        / "app"
        / "static"
        / "app-launcher.css"
    ).read_text(encoding="utf-8")
    assert ".platform-tour" in launcher_css
    assert ".company-shell-app-dms nav.navbar.fixed-top" in launcher_css
    assert '.company-shell-app-ai #sidebar[aria-label="Chat history"]' in launcher_css
    assert "left: 76px" in launcher_css
    assert "left: 62px" in launcher_css
    assert "width: calc(100% - 76px)" in launcher_css

    for page in ("index", "portal", "work", "quality", "mes", "hr", "desksharing", "finance"):
        html = (
            ROOT
            / "services"
            / "platform_api"
            / "app"
            / "static"
            / f"{page}.html"
        ).read_text(encoding="utf-8")
        assert "/assets/company-theme.css" in html, page
        assert "data-app-launcher" in html, page
    management = (
        ROOT / "services" / "platform_api" / "app" / "static" / "index.html"
    ).read_text(encoding="utf-8")
    assert "FLOWMANAGE" in management
    assert 'data-tour="iam-sso"' in management
    assert "Ein Konto aus dem AD" in management
    assert 'managementDemo=1&amp;tourStep=0' in management
    print("Unified company shell and theme: OK")


if __name__ == "__main__":
    main()
