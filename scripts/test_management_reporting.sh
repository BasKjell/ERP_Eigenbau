#!/usr/bin/env bash
set -euo pipefail

repository_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
container_name="erp-management-reporting-contract-${RANDOM}"

cleanup() {
  docker rm -f "${container_name}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run --detach --name "${container_name}" \
  --env POSTGRES_USER=platform \
  --env POSTGRES_PASSWORD=platform-test-password \
  --env POSTGRES_DB=platform_demo \
  postgres:17-alpine >/dev/null

for attempt in $(seq 1 30); do
  if docker exec "${container_name}" pg_isready --username platform --dbname platform_demo >/dev/null 2>&1; then
    break
  fi
  if [[ "${attempt}" == "30" ]]; then
    echo "PostgreSQL did not become ready" >&2
    exit 1
  fi
  sleep 1
done

docker exec --interactive "${container_name}" \
  psql --username platform --dbname platform_demo \
  --set=reporting_password=grafana-management-test-password \
  < "${repository_dir}/deployment/postgres/management_reporting.sql"

docker exec --interactive "${container_name}" \
  psql --username platform --dbname platform_demo \
  < "${repository_dir}/deployment/postgres/management_reporting_assertions.sql"

if docker exec "${container_name}" \
  psql --username platform --dbname platform_demo --set=ON_ERROR_STOP=1 \
  --command="SET ROLE grafana_management_reader; SELECT content FROM public.knowledge_chunks;" \
  >/dev/null 2>&1; then
  echo "grafana_management_reader unexpectedly accessed knowledge content" >&2
  exit 1
fi

echo "Management reporting contract and negative permission check passed"
