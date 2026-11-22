#!/usr/bin/env sh
set -eu

# Eigenes Compose-Projekt und eigene Host-Ports schützen lokale Demo-/Produktivdaten.
export DEMO_API_PORT="${CI_DEMO_API_PORT:-18088}"
export DOCS_PORT="${CI_DOCS_PORT:-18001}"
export MCP_PORT="${CI_MCP_PORT:-18090}"
export KNOWLEDGE_MCP_PORT="${CI_KNOWLEDGE_MCP_PORT:-18092}"

compose() {
  docker compose \
    --project-name erp-eigenbau-ci \
    -f compose.yaml \
    -f compose.ci.yaml \
    "$@"
}

cleanup() {
  compose --profile ci down --volumes --remove-orphans
}

trap cleanup EXIT INT TERM

set +e
compose --profile ci up \
  --build \
  --abort-on-container-exit \
  --exit-code-from integration-tests \
  integration-tests
status=$?
set -e

if [ "${status}" -ne 0 ]; then
  compose --profile ci ps -a
  compose --profile ci logs --no-color --tail=200
fi

exit "${status}"
