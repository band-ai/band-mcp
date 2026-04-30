"""MCP server entry point.

Phase 2 (INT-350) adds `--user-key`, `--agent-key`, `--room-id`, `--scope`,
and `--tools` CLI flags, resolves them through `config.resolve_config`, and
emits `config.warnings` before the server accepts traffic. The legacy
`THENVOI_API_KEY` path still works end-to-end.

Tool registration still runs through the current prefix-inference path; the
registrar that consumes `config.scope` / `config.tools` lands in Phase 3
(INT-351).
"""

from __future__ import annotations

import argparse
import os
from typing import Literal

from thenvoi_mcp import __version__
from thenvoi_mcp.config import (
    Config,
    ConfigError,
    _legacy_key_capabilities,
    resolve_config,
    settings,
    validate,
)
from thenvoi_mcp.shared import (
    AppContextType,
    get_app_context,
    logger,
    mcp,
    set_pending_config,
)
from thenvoi_mcp.tools.registrar import register_tools


def get_key_type(key: str) -> str:
    """Get API key type from prefix.

    Key formats:
    - User keys: thnv_u_<timestamp>_<random>
    - Agent keys: thnv_a_<timestamp>_<random>
    - Legacy keys: thnv_<timestamp>_<random> (loads all tools)
    """
    if key.startswith("thnv_u_"):
        return "user"
    elif key.startswith("thnv_a_"):
        return "agent"
    elif key.startswith("thnv_"):
        return "legacy"
    return "unknown"


def load_tools(key_type: str) -> None:
    """Load tools based on API key type.

    Tools register themselves via @mcp.tool() decorator on import. The
    SDK-driven registrar replaces this in Phase 3.
    """
    if key_type in ("agent", "legacy"):
        from thenvoi_mcp.tools.agent import (  # noqa: F401
            agent_chats,
            agent_contacts,
            agent_events,
            agent_identity,
            agent_lifecycle,
            agent_messages,
            agent_participants,
        )

        logger.debug("Loaded agent tools")

    if key_type in ("user", "legacy"):
        from thenvoi_mcp.tools.human import (  # noqa: F401
            human_agents,
            human_chats,
            human_contacts,
            human_messages,
            human_participants,
            human_profile,
        )

        logger.debug("Loaded human tools")


def _choose_legacy_key_type(config: Config) -> str:
    """Pick the `get_key_type` return value for the legacy tool loader.

    During the transition the handwritten tools still key off prefix inference.
    We map the new dual-credential config back onto that single label so the
    existing loader keeps working unchanged.
    """
    # If a true legacy key is present, honor its prefix (matches old behavior).
    if config.legacy_key:
        return get_key_type(config.legacy_key)
    # Otherwise map from the resolved scope list.
    has_agent = "agent" in config.scope
    has_human = "human" in config.scope
    if has_agent and has_human:
        return "legacy"
    if has_agent:
        return "agent"
    if has_human:
        return "user"
    # Fall back to whatever THENVOI_API_KEY looked like (empty string -> unknown).
    return get_key_type(settings.thenvoi_api_key)


@mcp.tool()
def health_check(ctx: AppContextType) -> str:
    """Test MCP server and API connectivity."""
    app_ctx = get_app_context(ctx)
    client = app_ctx.client
    key_type = get_key_type(settings.thenvoi_api_key)
    try:
        if key_type == "user":
            client.human_api_agents.list_my_agents()
        elif key_type == "agent":
            client.agent_api_identity.get_agent_me()
        else:  # legacy / unknown - try human path
            client.human_api_agents.list_my_agents()
        return f"OK | {key_type} | {settings.thenvoi_base_url}"
    except Exception as e:
        return f"Failed | {key_type} | {e}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Thenvoi MCP Server - Connect AI agents to Thenvoi platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Transport Modes:
  stdio   Default mode for IDE integration (Cursor, Claude Desktop, etc.)
          Communication via standard input/output streams.

  sse     HTTP server mode for remote/Docker deployments.
          Runs as a persistent HTTP service with Server-Sent Events.

Examples:
  thenvoi-mcp                                 # Run with STDIO (default)
  thenvoi-mcp --transport sse                 # Run as HTTP server on 127.0.0.1:8000
  thenvoi-mcp --scope agent,human             # Serve both scopes
  thenvoi-mcp --scope agent --tools contacts  # Agent + opt-in contacts tools
  thenvoi-mcp --scope agent --room-id r_123   # Pin to a single room

Environment Variables:
  THENVOI_USER_KEY / BAND_USER_KEY      User (human scope) API key
  THENVOI_AGENT_KEY / BAND_AGENT_KEY    Agent scope API key
  THENVOI_MCP_SCOPE / BAND_MCP_SCOPE    Comma-separated scopes (default: agent)
  THENVOI_MCP_TOOLS / BAND_MCP_TOOLS    Opt-in tool groups: contacts, memory
  THENVOI_MCP_ROOM_ID / BAND_MCP_ROOM_ID  Optional pinned room id
  THENVOI_API_KEY       Legacy single-key path (still supported as fallback)
  THENVOI_BASE_URL      Base URL for Thenvoi API (default: https://app.thenvoi.com)
  TRANSPORT             Transport mode: stdio or sse (default: stdio)
  HOST                  Host to bind for SSE mode (default: 127.0.0.1)
  PORT                  Port to bind for SSE mode (default: 8000)
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"thenvoi-mcp {__version__}",
    )

    parser.add_argument("--user-key", dest="user_key", type=str, default=None)
    parser.add_argument("--agent-key", dest="agent_key", type=str, default=None)
    parser.add_argument("--room-id", dest="room_id", type=str, default=None)
    parser.add_argument(
        "--scope",
        dest="scope",
        action="append",
        default=None,
        help=(
            "Scope to serve. Repeatable or comma-separated. "
            "Values: agent, human. Default: agent."
        ),
    )
    parser.add_argument(
        "--tools",
        dest="tools",
        action="append",
        default=None,
        help=(
            "Opt-in tool groups. Repeatable or comma-separated. "
            "Values: contacts, memory. Default: none. "
            "Note: operators who relied on implicit contacts tools must now "
            "pass --tools contacts."
        ),
    )

    parser.add_argument(
        "--transport",
        "-t",
        type=str,
        choices=["stdio", "sse"],
        default=None,
        help="Transport mode: stdio (default) or sse",
    )

    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind for SSE mode (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=None,
        help="Port to bind for SSE mode (default: 8000)",
    )

    return parser.parse_args(argv)


def _cli_mapping(args: argparse.Namespace) -> dict[str, object]:
    """Flatten argparse results into the shape `resolve_config` expects.

    `scope` and `tools` use argparse `action="append"`, so they arrive as
    `list[str] | None`. `_normalize_list_value` in `config.py` handles the
    final trim/split/lowercase/dedupe — we pass the raw list straight through.
    """
    return {
        "user_key": args.user_key,
        "agent_key": args.agent_key,
        "room_id": args.room_id,
        "scope": args.scope,
        "tools": args.tools,
    }


def run() -> None:
    """Run the MCP server with configurable transport mode.

    Order of operations:
    1. Parse CLI flags.
    2. Resolve the Config (dual-credential + scope/tools/room_id).
    3. Validate; raise ConfigError to exit before FastMCP starts.
    4. Emit every ConfigWarning entry at WARN level.
    5. Hand the Config to the lifespan (so AppContext picks it up).
    6. Register tools (legacy prefix path until Phase 3).
    7. Start FastMCP.
    """
    args = parse_args()

    config = resolve_config(cli=_cli_mapping(args), env=os.environ)

    # Emit warnings BEFORE validate() — validate might raise and we want the
    # operator to see "did you mean" hints even if config is also missing
    # credentials. Order: did-you-mean first, credentials-missing last.
    for warning in config.warnings:
        logger.warning(warning.message)

    try:
        validate(config)
    except ConfigError as exc:
        # Fall back to the pure-legacy path: if THENVOI_API_KEY is set and the
        # operator supplied no explicit scope/keys, honor the old behavior.
        # This keeps existing deployments booting even when validate() would
        # otherwise complain. We detect "no new config provided" by checking
        # that CLI is empty AND no new-style env vars were set.
        if _is_pure_legacy_invocation(args, config):
            logger.info(
                "Proceeding via legacy THENVOI_API_KEY path (no new-style "
                "credentials or scope supplied)."
            )
        else:
            logger.error("Configuration error: %s", exc)
            raise SystemExit(2) from exc

    # Escape-hatch scope write-back (C2/I3): when this is a pure-legacy
    # invocation, replace the default scope (["agent"]) with whatever the
    # legacy key actually serves. Two reasons:
    #   1. Startup logs below print `Resolved scope`; that line must match the
    #      tools that `load_tools(key_type)` will actually register.
    #   2. Phase 3's registrar reads `AppContext.scope` to pick the surface.
    #      A `thnv_u_*` legacy key must land there as ["human"], not ["agent"].
    # We do this for every pure-legacy invocation (validate() may have passed
    # for an all-capable `thnv_*` key, in which case config.scope is still the
    # default ["agent"] but load_tools will load both surfaces).
    if _is_pure_legacy_invocation(args, config):
        legacy_human, legacy_agent = _legacy_key_capabilities(config.legacy_key)
        legacy_scope: list[Literal["agent", "human"]] = []
        if legacy_agent:
            legacy_scope.append("agent")
        if legacy_human:
            legacy_scope.append("human")
        config.scope = legacy_scope

    set_pending_config(config)

    # Legacy tool loading — the registrar replaces this in Phase 3.
    if config.legacy_key and not (config.user_key or config.agent_key):
        key_type = get_key_type(config.legacy_key)
    elif config.user_key or config.agent_key:
        key_type = _choose_legacy_key_type(config)
    else:
        key_type = get_key_type(settings.thenvoi_api_key)
    load_tools(key_type)

    # Phase 3 (INT-351): SDK-driven registrar. Registers every
    # ``iter_tool_definitions(surface=s, ...)`` entry for each scope in
    # ``config.scope``. SDK tool names are ``thenvoi_``-prefixed and do not
    # collide with the legacy handwritten handler names above — both surfaces
    # coexist during the Phase 3 → Phase 4 transition. Phase 4 (INT-352)
    # deletes ``load_tools`` and the handwritten handlers.
    register_tools(mcp, config)

    # Determine transport mode (CLI args override env vars)
    transport: Literal["stdio", "sse"] = args.transport or settings.transport

    if args.host is not None:
        mcp.settings.host = args.host
    if args.port is not None:
        mcp.settings.port = args.port

    logger.info("Starting thenvoi-mcp-server v%s", __version__)
    logger.info("Base URL: %s", settings.thenvoi_base_url)
    logger.info("API key type: %s", key_type)
    logger.info("Resolved scope: %s", config.scope or "<none>")
    logger.info("Resolved tools: %s", config.tools or "<none>")
    if config.room_id:
        logger.info("Pinned room id: %s", config.room_id)

    if transport == "stdio":
        logger.info("Transport: STDIO (for IDE integration)")
        logger.info("Server ready - listening for MCP protocol messages on STDIO")
        mcp.run(transport="stdio")
    else:
        host = args.host or settings.host
        port = args.port or settings.port
        logger.info("Transport: SSE (HTTP server mode)")
        logger.info("Server ready - listening on http://%s:%s", host, port)
        logger.info("SSE endpoint: /sse | Messages endpoint: /messages/")
        mcp.run(transport="sse")


def _is_pure_legacy_invocation(args: argparse.Namespace, config: Config) -> bool:
    """True when the operator set only THENVOI_API_KEY and no new flags/envs.

    Used to preserve backward compatibility: an operator who never touched the
    new flags should keep booting even if `validate()` would otherwise fail on
    the default `--scope agent` with no agent credential, as long as the
    legacy key is present and can serve something.
    """
    if config.legacy_key is None:
        return False
    # No new-style CLI flags.
    if any(
        getattr(args, attr) is not None
        for attr in ("user_key", "agent_key", "room_id", "scope", "tools")
    ):
        return False
    # No new-style env vars.
    new_envs = (
        "THENVOI_USER_KEY",
        "THENVOI_AGENT_KEY",
        "BAND_USER_KEY",
        "BAND_AGENT_KEY",
        "THENVOI_MCP_SCOPE",
        "BAND_MCP_SCOPE",
        "THENVOI_MCP_TOOLS",
        "BAND_MCP_TOOLS",
        "THENVOI_MCP_ROOM_ID",
        "BAND_MCP_ROOM_ID",
    )
    return not any(os.environ.get(name) for name in new_envs)


if __name__ == "__main__":
    run()
