"""Shared app context, logger, and FastMCP singleton for thenvoi-mcp.

Phase 2 (INT-350) extends `AppContext` with dual REST clients:
`human_rest` (bound to `user_key` or a human-capable legacy key) and
`agent_rest` (bound to `agent_key` or an agent-capable legacy key). The
single `client` attribute is retained during the transition so the
currently-handwritten tools in `tools/agent/` and `tools/human/` keep
working; Phase 4 (INT-352) deletes those and `client` goes with them.

HumanTools / AgentTools coordination with INT-349
-------------------------------------------------
The SDK's `HumanTools` class lands in Phase 1 (INT-349) in `thenvoi-sdk-python`
and is not yet available in this environment (the repo depends on
`thenvoi-client-rest`, which is the Fern-generated REST client only).
`get_human_tools()` / `get_agent_tools()` import `HumanTools` / `AgentTools`
lazily and guard the import: if either import fails, the helper logs a WARN
and returns `None`. Phase 3 (INT-351) is responsible for the registrar that
calls these helpers; until INT-349 is merged and the SDK is installed, the
helpers will fail closed with a structured log line rather than an import-time
crash. This keeps Phase 2 mergeable without waiting for Phase 1.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from mcp.server.transport_security import TransportSecuritySettings
from thenvoi_rest import AsyncRestClient, RestClient

from thenvoi_mcp.config import (
    Config,
    ConfigError,
    _legacy_key_capabilities,
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

    `client` is the legacy single sync `RestClient` used by the handwritten
    `tools/agent/*` and `tools/human/*` handlers. It is always populated
    during the transition and goes away in Phase 4 (INT-352) once those
    handlers are deleted.

    `human_rest` / `agent_rest` are the new async clients used by Phase 3's
    registrar. They may be None when the corresponding scope is not served by
    the current config (e.g. a human-only deployment has no `agent_rest`).

    `human_tools` is the startup-constructed singleton returned by
    `get_human_tools()`. `AgentTools` is constructed per-room and cached in a
    request-scoped ContextVar by `get_agent_tools()`.

    `pinned_room_id`, `scope`, and `tools` carry the resolved Config values
    forward so the registrar (Phase 3) doesn't need to re-resolve.
    """

    # Legacy single-client path (kept for existing handwritten tools; removed
    # in Phase 4). Always populated so the existing `@mcp.tool()` handlers
    # that do `get_app_context(ctx).client.<something>` keep type-checking.
    # TODO(INT-352): delete AppContext.client once handwritten tools under
    # tools/agent/* and tools/human/* are removed.
    client: RestClient

    # Phase 2 additions.
    human_rest: AsyncRestClient | None = None
    agent_rest: AsyncRestClient | None = None
    human_tools: Any = None  # HumanTools | None; typed Any to avoid SDK hard-dep
    pinned_room_id: str | None = None
    scope: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)


AppContextType = Context[ServerSession, AppContext, None]
_agent_tools_cache_var: ContextVar[dict[str | None, Any] | None] = ContextVar(
    "thenvoi_mcp_agent_tools_cache",
    default=None,
)


def _try_import_human_tools() -> Any:
    """Return SDK `HumanTools` class or None if unavailable.

    Guarded to tolerate the Phase 1 (INT-349) SDK landing on a different
    timeline. When Phase 3 runs and the SDK is installed, this resolves; until
    then, the registrar sees None and the helper logs a structured warning.
    """
    try:
        from thenvoi.runtime.tools import HumanTools  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - import-time guard
        logger.warning(
            "HumanTools unavailable (SDK not installed or INT-349 not yet "
            "merged); human tools will not be constructed: %s",
            exc,
        )
        return None
    return HumanTools


def _try_import_agent_tools() -> Any:
    """Return SDK `AgentTools` class or None if unavailable."""
    try:
        from thenvoi.runtime.tools import AgentTools  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - import-time guard
        logger.warning(
            "AgentTools unavailable (SDK not installed); agent tools will not "
            "be constructed: %s",
            exc,
        )
        return None
    return AgentTools


def _choose_legacy_client_credential(
    config: Config,
    *,
    human_cred: str | None,
    agent_cred: str | None,
) -> str | None:
    """Choose the transitional sync-client key for handwritten handlers.

    Scope-specific credentials must beat a stale ``THENVOI_API_KEY`` here just
    as they do in ``resolve_credential_for_scope``. Otherwise startup can log a
    human-only scope and register human handlers while the legacy ``RestClient``
    is still bound to an agent key from ``THENVOI_API_KEY``.
    """
    scopes = set(config.scope)
    if scopes == {"human"}:
        return human_cred
    if scopes == {"agent"}:
        return agent_cred

    legacy_human, legacy_agent = _legacy_key_capabilities(config.legacy_key)
    if scopes == {"agent", "human"} and legacy_human and legacy_agent:
        return config.legacy_key

    return human_cred or agent_cred or config.legacy_key


def build_app_context(
    config: Config | None = None,
) -> AppContext:
    """Construct an `AppContext` from a resolved `Config`.

    Per-scope `AsyncRestClient` instances are built lazily: a client is only
    constructed for a scope that resolves to a credential. This keeps
    human-only or agent-only deployments from opening connections they'll
    never use.

    If `config` is None, we fall back to the legacy `THENVOI_API_KEY` path:
    the sync `client` is populated from `settings.thenvoi_api_key` and the
    new async slots stay None. This preserves current behavior for any caller
    that has not yet moved to `resolve_config(...)`.

    `AppContext.client` is always populated during the Phase 2 transition.
    Phase 4 (INT-352) removes the legacy `client` slot once handwritten tool
    handlers are deleted.
    """
    base_url = settings.thenvoi_base_url

    if config is None:
        # Legacy path: single sync client, no new slots.
        client = RestClient(
            api_key=settings.thenvoi_api_key,
            base_url=base_url,
        )
        return AppContext(client=client)

    human_rest: AsyncRestClient | None = None
    agent_rest: AsyncRestClient | None = None

    human_cred = resolve_credential_for_scope(config, "human")
    agent_cred = resolve_credential_for_scope(config, "agent")

    if human_cred is not None:
        human_rest = AsyncRestClient(api_key=human_cred, base_url=base_url)
    if agent_cred is not None:
        agent_rest = AsyncRestClient(api_key=agent_cred, base_url=base_url)

    # Keep the legacy sync client alive during the transition so the existing
    # `@mcp.tool()` decorated handlers in `tools/agent/*` and `tools/human/*`
    # continue to work. The key must match the resolved scope rather than a
    # stale legacy env var; validation should catch empty credentials before this
    # point. Raise loudly here if a caller bypassed it so the server does not
    # boot into a delayed 401.
    legacy_for_client = _choose_legacy_client_credential(
        config,
        human_cred=human_cred,
        agent_cred=agent_cred,
    )
    if legacy_for_client is None:
        raise ConfigError("No API credential available for legacy RestClient")
    client = RestClient(api_key=legacy_for_client, base_url=base_url)

    # Startup-construct `HumanTools` singleton if the SDK + human client are
    # both available. AgentTools is per-room and constructed on demand.
    human_tools_obj: Any = None
    HumanToolsCls = _try_import_human_tools()
    if HumanToolsCls is not None and human_rest is not None:
        try:
            human_tools_obj = HumanToolsCls(rest=human_rest)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to construct HumanTools singleton: %s", exc)
            human_tools_obj = None

    return AppContext(
        client=client,
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
        client = app_ctx.client          # legacy sync path
        human_rest = app_ctx.human_rest  # new async path (Phase 3)
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


def get_agent_tools(ctx: AppContextType, room_id: str | None) -> Any:
    """Return an `AgentTools` instance scoped to `room_id`.

    Per-request cache: Phase 3 can call this multiple times in the same tool
    invocation (participant-resolution paths walk back to the room) and must
    not construct twice. The registrar is responsible for clearing the cache
    at the start of each request; within a single call, repeated
    `get_agent_tools(ctx, "r1")` returns the same object. Room-less agent tools
    pass None through to AgentTools.

    Returns None when the SDK isn't installed or when no agent credential is
    configured.
    """
    app_ctx = get_app_context(ctx)
    if app_ctx.agent_rest is None:
        logger.warning(
            "get_agent_tools(room_id=%s): no agent credential configured.",
            room_id,
        )
        return None

    cache = _agent_tools_cache_var.get()
    if cache is None:
        cache = {}
        _agent_tools_cache_var.set(cache)

    cached = cache.get(room_id)
    if cached is not None:
        return cached

    AgentToolsCls = _try_import_agent_tools()
    if AgentToolsCls is None:
        return None

    try:
        instance = AgentToolsCls(room_id=room_id, rest=app_ctx.agent_rest)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to construct AgentTools for room %s: %s", room_id, exc)
        return None

    cache[room_id] = instance
    return instance


def reset_agent_tools_cache(ctx: AppContextType) -> None:
    """Clear the per-request `AgentTools` cache.

    Phase 3's registrar calls this at the start of each tool invocation so the
    cache's per-request semantics hold.
    """
    _agent_tools_cache_var.set({})


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
