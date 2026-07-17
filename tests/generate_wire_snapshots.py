"""Generate the committed MCP tool-schema compatibility snapshots.

Run this against the current implementation before changing tool registration:

    uv run python tests/generate_wire_snapshots.py tests/fixtures/wire_schemas/full.json
    uv run python tests/generate_wire_snapshots.py --room-id room_pinned tests/fixtures/wire_schemas/pinned.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from band_mcp.config import Config
from band_mcp.server import health_check  # noqa: F401 - registers the health tool
from band_mcp.shared import mcp
from band_mcp.tools.registrar import register_tools


def parse_args() -> argparse.Namespace:
    """Parse the output path and optional pinned room identifier."""
    parser = argparse.ArgumentParser(
        description="Generate a band-mcp MCP tool-schema snapshot."
    )
    parser.add_argument("output", type=Path)
    parser.add_argument("--room-id", default=None)
    return parser.parse_args()


def snapshot(config: Config) -> list[dict[str, Any]]:
    """Return the current advertised MCP tools for the supplied config."""
    register_tools(mcp, config)
    tools = asyncio.run(mcp.list_tools())
    return [tool.model_dump(mode="json", by_alias=True, exclude_none=True) for tool in tools]


def main() -> None:
    """Write a deterministic full-surface snapshot."""
    args = parse_args()
    config = Config(
        agent_key="snapshot-agent-key",
        user_key="snapshot-user-key",
        room_id=args.room_id,
        scope=["agent", "human"],
        tools=["contacts", "memory"],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshot(config), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
