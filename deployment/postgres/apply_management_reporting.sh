#!/bin/sh
set -eu

if [ -z "${GRAFANA_MANAGEMENT_DB_PASSWORD:-}" ]; then
  echo "GRAFANA_MANAGEMENT_DB_PASSWORD is required" >&2
  exit 1
fi

exec psql \
  --set=ON_ERROR_STOP=1 \
  --set="reporting_password=${GRAFANA_MANAGEMENT_DB_PASSWORD}" \
  --file=/seed/management_reporting.sql
