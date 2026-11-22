#!/usr/bin/env bash
set -euo pipefail

repository_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
container_name="erp-dms-reporting-contract-${RANDOM}"

cleanup() {
  docker rm -f "${container_name}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run --detach --name "${container_name}" \
  --env POSTGRES_USER=paperless \
  --env POSTGRES_PASSWORD=paperless-test-password \
  --env POSTGRES_DB=paperless \
  postgres:18.0-alpine >/dev/null

for attempt in $(seq 1 30); do
  if docker exec "${container_name}" pg_isready --username paperless --dbname paperless >/dev/null 2>&1; then
    break
  fi
  if [[ "${attempt}" == "30" ]]; then
    echo "PostgreSQL did not become ready" >&2
    exit 1
  fi
  sleep 1
done

docker exec --interactive "${container_name}" \
  psql --username paperless --dbname paperless \
  < "${repository_dir}/deployment/paperless/reporting_test_schema.sql"

docker exec --interactive "${container_name}" \
  psql --username paperless --dbname paperless \
  --set=reporting_password=grafana-test-password \
  < "${repository_dir}/deployment/paperless/reporting.sql"

docker exec --interactive "${container_name}" \
  psql --username paperless --dbname paperless \
  < "${repository_dir}/deployment/paperless/reporting_test_assertions.sql"

if docker exec "${container_name}" \
  psql --username paperless --dbname paperless --set=ON_ERROR_STOP=1 \
  --command="SET ROLE grafana_reader; SELECT content FROM public.documents_document;" \
  >/dev/null 2>&1; then
  echo "grafana_reader unexpectedly accessed Paperless document content" >&2
  exit 1
fi

echo "DMS reporting contract and negative permission check passed"
