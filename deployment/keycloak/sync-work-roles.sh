#!/bin/sh
set -eu

KCADM=/opt/keycloak/bin/kcadm.sh
REALM=open-manufacturing

attempt=0
until "$KCADM" config credentials \
  --server http://keycloak:8080 \
  --realm master \
  --user "$KEYCLOAK_ADMIN" \
  --password "$KEYCLOAK_ADMIN_PASSWORD" >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "Keycloak admin API did not become ready" >&2
    exit 1
  fi
  sleep 2
done

ensure_role() {
  role="$1"
  description="$2"
  "$KCADM" get "roles/$role" -r "$REALM" >/dev/null 2>&1 || \
    "$KCADM" create roles -r "$REALM" -s "name=$role" -s "description=$description" >/dev/null
}

sync_confidential_client() {
  client_id="$1"
  client_secret="$2"
  redirect_uri="$3"
  web_origin="$4"
  client_uuid=$("$KCADM" get clients -r "$REALM" -q "clientId=$client_id" \
    --fields id --format csv --noquotes | head -n 1)
  if [ -z "$client_uuid" ]; then
    echo "Keycloak client $client_id is missing" >&2
    exit 1
  fi
  "$KCADM" update "clients/$client_uuid" -r "$REALM" \
    -s publicClient=false \
    -s clientAuthenticatorType=client-secret \
    -s standardFlowEnabled=true \
    -s directAccessGrantsEnabled=false \
    -s "secret=$client_secret" \
    -s "redirectUris=[\"$redirect_uri\"]" \
    -s "webOrigins=[\"$web_origin\"]" >/dev/null
}

ensure_role work-user "FLOWWORK-Projekte, Tickets und Wiki"
ensure_role requirements-user "Anforderungen, Baselines und Traceability"
ensure_role work-admin "FLOWWORK-Administration und Projektvorlagen"

"$KCADM" add-roles -r "$REALM" --rname platform-admin \
  --rolename work-user --rolename requirements-user --rolename work-admin >/dev/null

"$KCADM" create partialImport -r "$REALM" \
  -s ifResourceExists=OVERWRITE \
  -s policy=OVERWRITE \
  -f /sync/ad-partial-import.json >/dev/null

sync_confidential_client \
  erpnext \
  "$ERPNEXT_OIDC_CLIENT_SECRET" \
  "http://localhost:8081/api/method/frappe.integrations.oauth2_logins.login_via_keycloak" \
  "http://localhost:8081"

echo "AD demo groups, FLOWWORK roles and SSO clients are synchronized in Keycloak"
