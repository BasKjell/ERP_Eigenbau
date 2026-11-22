#!/usr/bin/env bash
# FLOWAGENTS-Orchestrator als lokaler Host-Dienst (start | stop | restart | status | logs).
# Der Dienst lauscht nur auf 127.0.0.1:8095. Zustand, venv und Log liegen privat in ~/.flow-agents.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="${FLOW_AGENTS_STATE:-$HOME/.flow-agents}"
CONFIG="${FLOW_AGENTS_CONFIG:-services/agent_orchestrator/config/orchestrator.yaml}"
VENV="$STATE/venv"
PIDFILE="$STATE/flow-agents.pid"
LOG="$STATE/flow-agents.log"
REQ="$ROOT/services/agent_orchestrator/requirements.txt"
URL="http://127.0.0.1:8095/health"

umask 077
mkdir -p "$STATE"
chmod 700 "$STATE"

python_bin() {
  for candidate in python3.13 python3.12 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 12))'; then
      command -v "$candidate"
      return
    fi
  done
  echo "Python 3.12 oder neuer wird benötigt" >&2
  exit 1
}

ensure_venv() {
  local stamp="$VENV/.requirements.sha256"
  local wanted
  wanted="$(shasum -a 256 "$REQ" | cut -d' ' -f1)"
  if [[ ! -x "$VENV/bin/python" || ! -f "$stamp" || "$(cat "$stamp")" != "$wanted" ]]; then
    "$(python_bin)" -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --disable-pip-version-check -r "$REQ"
    echo "$wanted" > "$stamp"
  fi
}

running() { [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }

start() {
  if running; then echo "FLOWAGENTS läuft bereits (PID $(cat "$PIDFILE"))."; return; fi
  ensure_venv
  (cd "$ROOT" && PYTHONPATH="$ROOT/services/agent_orchestrator" FLOW_AGENTS_STATE="$STATE" \
    nohup "$VENV/bin/python" -m flowagents serve --config "$CONFIG" --repo-root "$ROOT" </dev/null >>"$LOG" 2>&1 &
    echo $! > "$PIDFILE")
  for _ in $(seq 1 30); do
    if curl -fsS "$URL" >/dev/null 2>&1; then echo "FLOWAGENTS gestartet: $URL (Log: $LOG)"; return; fi
    sleep 1
  done
  echo "FLOWAGENTS antwortet nicht. Letzte Logzeilen:" >&2
  tail -n 20 "$LOG" >&2
  exit 1
}

stop() {
  if running; then kill "$(cat "$PIDFILE")"; sleep 1; fi
  rm -f "$PIDFILE"
  echo "FLOWAGENTS gestoppt."
}

status() {
  if running && curl -fsS "$URL"; then
    echo
    (cd "$ROOT" && PYTHONPATH="$ROOT/services/agent_orchestrator" FLOW_AGENTS_STATE="$STATE" \
      "$VENV/bin/python" -m flowagents status --config "$CONFIG" --repo-root "$ROOT" | head -60)
  else
    echo "FLOWAGENTS läuft nicht. Start: make agents-up"
    return 1
  fi
}

case "${1:-status}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) status ;;
  logs) tail -n 100 -f "$LOG" ;;
  *) echo "Verwendung: $0 start|stop|restart|status|logs" >&2; exit 2 ;;
esac
