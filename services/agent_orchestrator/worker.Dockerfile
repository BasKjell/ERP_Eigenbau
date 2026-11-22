# Worker-Image für die gesperrten Codex-/Claude-Abo-CLIs (aus Trading_Ai übernommen).
# Separat bauen, prüfen und nur per Digest in container.image eintragen.
FROM node:22-bookworm-slim AS node
FROM python:3.12-slim-bookworm
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
ARG CODEX_VERSION
ARG CLAUDE_VERSION
RUN test -n "$CODEX_VERSION" && test -n "$CLAUDE_VERSION" \
    && apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && npm install -g "@openai/codex@$CODEX_VERSION" "@anthropic-ai/claude-code@$CLAUDE_VERSION" \
    && npm cache clean --force
COPY worker/flow_agents_worker.py /opt/flow_agents_worker.py
WORKDIR /work
