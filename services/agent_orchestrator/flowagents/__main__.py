"""Kommandozeile: ``python -m flowagents serve|status|registry|check-registry|cycle``."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import registry as registry_module


def main() -> int:
    parser = argparse.ArgumentParser(prog="flowagents", description=__doc__)
    parser.add_argument("action", choices=["serve", "status", "registry", "check-registry", "cycle"])
    parser.add_argument("--config", type=Path, default=Path("services/agent_orchestrator/config/orchestrator.yaml"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    os.umask(0o077)
    root = args.repo_root.resolve()

    if args.action == "check-registry":
        try:
            loaded = registry_module.load(root / "agents")
        except registry_module.RegistryError as exc:
            print(f"Agentenregister ungültig: {exc}", file=sys.stderr)
            return 1
        print(f"Agentenregister gültig: {len(loaded.agents)} Rollen, {len(loaded.steps)} Schritte, "
              f"Digest {loaded.digest[:16]}")
        return 0

    from .config import ConfigError, build

    try:
        runtime = build(root / args.config if not args.config.is_absolute() else args.config, repo_root=root)
    except ConfigError as exc:
        print(f"flowagents: {exc}", file=sys.stderr)
        return 1
    if args.action == "registry":
        print(json.dumps(runtime.engine.registry.public(), ensure_ascii=False, indent=2))
        return 0
    if args.action == "status":
        overview = runtime.engine.overview()
        print(json.dumps({k: overview[k] for k in ("control", "metrics", "runs", "decisions")}, ensure_ascii=False,
                         indent=2))
        return 0
    if args.action == "cycle":
        runtime.engine.recover()
        worked = runtime.engine.cycle()
        print("Schritt ausgeführt" if worked else "Keine Arbeit")
        return 0

    import uvicorn

    from .api import create_app

    if runtime.host not in {"127.0.0.1", "::1", "localhost"} and not os.environ.get("FLOW_AGENTS_ALLOW_REMOTE"):
        print("flowagents: Der Dienst lauscht nur auf Loopback (FLOW_AGENTS_ALLOW_REMOTE für Container)",
              file=sys.stderr)
        return 1
    uvicorn.run(create_app(runtime), host=runtime.host, port=runtime.port, log_level="warning", access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
