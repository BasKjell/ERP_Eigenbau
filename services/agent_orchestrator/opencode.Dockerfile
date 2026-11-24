# OpenCode-Worker für FLOWAGENTS (lokale Modelle über FLOWGATE, kein Abo, kein Internet).
# Bauen:  docker build -f services/agent_orchestrator/opencode.Dockerfile -t flow-agents-opencode:1 services/agent_orchestrator
# Danach den Digest (docker image inspect --format '{{.Id}}') in opencode.image eintragen.
FROM node:22-bookworm-slim
ARG OPENCODE_VERSION=1.19.6
RUN npm install -g "opencode-ai@${OPENCODE_VERSION}" && npm cache clean --force \
    && opencode --version
COPY opencode/run.sh /opt/flow-opencode.sh
RUN chmod 0555 /opt/flow-opencode.sh
WORKDIR /work
ENTRYPOINT ["/opt/flow-opencode.sh"]
