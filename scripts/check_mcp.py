#!/usr/bin/env python3
"""List or call tools on one Streamable HTTP MCP endpoint."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from mcp import Client


async def run(endpoint: str, tool: str, arguments: dict[str, Any]) -> None:
    async with Client(endpoint) as client:
        if not tool:
            response = await client.list_tools()
            print(json.dumps([item.name for item in response.tools], ensure_ascii=False))
            return
        response = await client.call_tool(tool, arguments)
        print(json.dumps(response.structured_content, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("endpoint")
    parser.add_argument("tool", nargs="?", default="")
    parser.add_argument("arguments", nargs="?", default="{}")
    args = parser.parse_args()
    arguments = json.loads(args.arguments)
    if not isinstance(arguments, dict):
        raise SystemExit("arguments must be a JSON object")
    asyncio.run(run(args.endpoint, args.tool, arguments))


if __name__ == "__main__":
    main()
