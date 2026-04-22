"""Shared app context, logger, and FastMCP singleton for thenvoi-mcp.

`AppContext` carries two async REST clients: `human_rest` (bound to
`user_key` or a human-capable legacy key) and `agent_rest` (bound to
`agent_key` or an agent-capable legacy key). Either may be None when the
corresponding scope is not served by the current config.

HumanTools / AgentTools coordination with INT-349
-------------------------------------------------
The SDK's `HumanTools` class lives in `thenvoi-sdk-python` (INT-349).
`get_human_tools()` / `get_agent_tools()` import it lazily and guard the
import: if either import fails, the helper logs a WARN and returns `None`.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from mcp.server.transport_security import TransportSecuritySettings
from thenvoi_rest import AsyncRestClient

from thenvoi_mcp.config import (
    Config,
    ConfigError,
    settings,
    resolve_credential_for_scope,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """Type-safe container for application dependencies.

    `human_rest` / `agent_rest` are async REST clients used by the registrar.
    Either may be None when the corresponding scope is not served by the
    current config (e.g. a human-only deployment has no `agent_rest`).

    `human_tools` is the startup-constructed singleton returned by
    `get_human_tools()`. `AgentTools` is constructed per-room and cached in
    `_agent_tools_cache` by `get_agent_tools()`.

    `pinned_room_id`, `scope`, and `tools` carry the resolved Config values
    forward so the registrar doesn't need to re-resolve.
    """

    human_rest: AsyncRestClient | None = None
    agent_rest: AsyncRestClient | None = None
    human_tools: Any = None  # HumanTools | None; typed Any to avoid SDK hard-dep
    pinned_room_id: str | None = None
    scope: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)

    # Per-request cache for AgentTools keyed by room_id. The registrar clears
    # this at the start of each tool call; see `get_agent_tools`.
    _agent_tools_cache: dict[str, Any] = field(default_factory=dict)


AppContextType = Context[ServerSession, AppContext, None]


def _require_sdk_tools() -> tuple[Any, Any]:
    """Import and return ``(HumanTools, AgentTools)`` from the SDK.

    Raises ``ConfigError`` if the SDK package is not importable, so the
    operator gets a clear startup error instead of a silent empty tool
    surface. Phase 4 (INT-352) pinned ``thenvoi-sdk>=0.3.0`` as a hard
    dependency; a missing import now means the install is broken, not a
    development-timeline race with INT-349.
    """
    try:
        from thenvoi.runtime.tools import AgentTools, HumanTools
    except ImportError as exc:
        raise ConfigError(
            "thenvoi-sdk >= 0.3.0 is required but is not importable "
            "(`from thenvoi.runtime.tools import HumanTools, AgentTools` "
            f"failed: {exc}). Install/upgrade with "
            "`pip install 'thenvoi-sdk>=0.3.0'` or `uv sync`."
        ) from exc
    return HumanTools, AgentTools


def _try_import_human_tools() -> Any:
    """Return SDK ``HumanTools`` class. Raises ConfigError if unavailable."""
    HumanTools, _ = _require_sdk_tools()
    return HumanTools


def _try_import_agent_tools() -> Any:
    """Return SDK ``AgentTools`` class. Raises ConfigError if unavailable."""
    _, AgentTools = _require_sdk_tools()
    return AgentTools


def build_app_context(
    config: Config | None = None,
) -> AppContext:
    """Construct an `AppContext` from a resolved `Config`.

    Per-scope `AsyncRestClient` instances are built lazily: a client is only
    constructed for a scope that resolves to a credential. This keeps
    human-only or agent-only deployments from opening connections they'll
    never use.

    If `config` is None, we fall back to the legacy `THENVOI_API_KEY` path:
    the async slots are populated from the single legacy key, tried against
    both human and agent scopes based on the key prefix (server.run rewrites
    `config.scope` to match). If `settings.thenvoi_api_key` is also unset,
    the AppContext is returned with both slots None — tool calls will fail
    at request time with a structured error.
    """
    base_url = settings.thenvoi_base_url

    if config is None:
        # Legacy path with no resolved Config. Build both clients from the
        # legacy key if set; either can be None if the key can't serve that
        # scope (e.g. thnv_u_* cannot serve agent calls).
        legacy_key = settings.thenvoi_api_key or ""
        human_rest = (
            AsyncRestClient(api_key=legacy_key, base_url=base_url)
            if legacy_key
            else None
        )
        agent_rest = (
            AsyncRestClient(api_key=legacy_key, base_url=base_url)
            if legacy_key
            else None
        )
        return AppContext(human_rest=human_rest, agent_rest=agent_rest)

    human_rest: AsyncRestClient | None = None
    agent_rest: AsyncRestClient | None = None

    human_cred = resolve_credential_for_scope(config, "human")
    agent_cred = resolve_credential_for_scope(config, "agent")

    if human_cred is not None:
        human_rest = AsyncRestClient(api_key=human_cred, base_url=base_url)
    if agent_cred is not None:
        agent_rest = AsyncRestClient(api_key=agent_cred, base_url=base_url)

    # Startup-construct `HumanTools` singleton if the human client is
    # available. AgentTools is per-room and constructed on demand.
    # `_try_import_human_tools` raises ConfigError if the SDK is missing —
    # we let that propagate so the operator sees a clear startup failure
    # instead of a running-but-empty MCP server.
    human_tools_obj: Any = None
    if human_rest is not None:
        HumanToolsCls = _try_import_human_tools()
        try:
            human_tools_obj = HumanToolsCls(rest=human_rest)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to construct HumanTools singleton: %s", exc)
            human_tools_obj = None

    return AppContext(
        human_rest=human_rest,
        agent_rest=agent_rest,
        human_tools=human_tools_obj,
        pinned_room_id=config.room_id,
        scope=list(config.scope),
        tools=list(config.tools),
    )


# Module-level slot the lifespan reads; server.run() populates this before
# starting FastMCP. Using a module-level value (vs passing through closures)
# matches how `settings` is already consumed and keeps the lifespan signature
# unchanged.
_pending_config: Config | None = None


def set_pending_config(config: Config) -> None:
    """Store the resolved config for the lifespan to pick up at startup."""
    global _pending_config
    _pending_config = config


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Lifespan context manager for MCP server."""
    logger.info("Initializing Thenvoi API client")
    app_context = build_app_context(_pending_config)
    logger.info("Thenvoi MCP server lifespan started successfully")

    try:
        yield app_context
    finally:
        logger.info("Thenvoi MCP server lifespan shutdown complete")


def get_app_context(ctx: AppContextType) -> AppContext:
    """Helper to extract AppContext from the lifespan context.

    Usage in tools:
        app_ctx = get_app_context(ctx)
        human_rest = app_ctx.human_rest  # async REST client for human scope
        agent_rest = app_ctx.agent_rest  # async REST client for agent scope
    """
    return ctx.request_context.lifespan_context


def get_human_tools(ctx: AppContextType) -> Any:
    """Return the startup-constructed `HumanTools` singleton, or None.

    Phase 3 (INT-351) calls this per tool invocation. The singleton is built
    once in `build_app_context` from the human `AsyncRestClient`; there is no
    per-request reconstruction.

    Returns None when the SDK isn't installed (INT-349 not yet merged) or when
    the deployment has no human credential. The caller is responsible for
    surfacing that as an actionable error.
    """
    app_ctx = get_app_context(ctx)
    if app_ctx.human_tools is None:
        logger.warning(
            "get_human_tools(): HumanTools not available. Ensure the Thenvoi "
            "SDK (INT-349) is installed and a human credential is configured."
        )
    return app_ctx.human_tools


def get_agent_tools(ctx: AppContextType, room_id: str) -> Any:
    """Return an `AgentTools` instance scoped to `room_id`.

    Per-request cache: Phase 3 can call this multiple times in the same tool
    invocation (participant-resolution paths walk back to the room) and must
    not construct twice. The registrar is responsible for clearing the cache
    at the start of each request; within a single call, repeated
    `get_agent_tools(ctx, "r1")` returns the same object.

    Returns None when no agent credential is configured. Raises
    ``ConfigError`` (via ``_try_import_agent_tools``) when the SDK is not
    installed — that condition should have been caught at startup but this
    keeps us honest if a tool is dispatched on a broken install.
    """
    app_ctx = get_app_context(ctx)
    if app_ctx.agent_rest is None:
        logger.warning(
            "get_agent_tools(room_id=%s): no agent credential configured.",
            room_id,
        )
        return None

    cached = app_ctx._agent_tools_cache.get(room_id)
    if cached is not None:
        return cached

    AgentToolsCls = _try_import_agent_tools()

    try:
        instance = AgentToolsCls(room_id=room_id, rest=app_ctx.agent_rest)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to construct AgentTools for room %s: %s", room_id, exc)
        return None

    app_ctx._agent_tools_cache[room_id] = instance
    return instance


def reset_agent_tools_cache(ctx: AppContextType) -> None:
    """Clear the per-request `AgentTools` cache.

    The registrar calls this at the start of each tool invocation so the
    cache's per-request semantics hold.
    """
    get_app_context(ctx)._agent_tools_cache.clear()


def serialize_response(result: Any, **kwargs: Any) -> str:
    """Serialize a Pydantic model response to JSON.

    Args:
        result: A Pydantic model or any object with model_dump() method.
        **kwargs: Additional arguments passed to model_dump().

    Returns:
        JSON string representation of the result.
    """
    if hasattr(result, "model_dump") and callable(result.model_dump):
        return json.dumps(result.model_dump(**kwargs), indent=2, default=str)
    return json.dumps(result, indent=2, default=str)


transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=settings.enable_dns_rebinding_protection,
    allowed_hosts=settings.allowed_hosts,
    allowed_origins=settings.allowed_origins,
)

if (
    settings.transport == "sse"
    and settings.enable_dns_rebinding_protection
    and not settings.allowed_hosts
):
    logger.warning(
        "DNS rebinding protection enabled with empty ALLOWED_HOSTS. "
        "All SSE requests will be blocked. Configure ALLOWED_HOSTS to allow connections."
    )

mcp = FastMCP(
    name="thenvoi-mcp-server",
    lifespan=app_lifespan,
    host=settings.host,
    port=settings.port,
    transport_security=transport_security,
)
