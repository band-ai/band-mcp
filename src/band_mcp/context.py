"""Runtime dependencies and room-scoped SDK tool state."""

from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from band_rest import AsyncRestClient

from band_mcp.config import (
    Config,
    ConfigError,
    legacy_key_capabilities,
    resolve_credential_for_scope,
)
from band_mcp.settings import settings

__all__ = [
    "AGENT_TOOLS_CACHE_MAX_SIZE",
    "AGENT_TOOLS_LOCK_STRIPES",
    "AppContext",
    "build_app_context",
    "get_app_context",
]

logger = logging.getLogger(__name__)

# A bounded cache prevents caller-provided room IDs from growing process memory.
AGENT_TOOLS_CACHE_MAX_SIZE = 128
# Stripes cap lock allocation while making same-room calls serialize reliably.
AGENT_TOOLS_LOCK_STRIPES = 64


@dataclass(slots=True, kw_only=True)
class AppContext:
    """Dependencies and mutable SDK state for one server instance."""

    human_rest: AsyncRestClient | None = None
    agent_rest: AsyncRestClient | None = None
    human_tools: Any = None
    agent_tools_roomless: Any = None
    pinned_room_id: str | None = None
    scope: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    _agent_tools_cache: OrderedDict[str, Any] = field(default_factory=OrderedDict)
    _agent_tools_locks: list[asyncio.Lock] = field(
        default_factory=lambda: [
            asyncio.Lock() for _ in range(AGENT_TOOLS_LOCK_STRIPES)
        ]
    )

    def agent_tools_for(self, room_id: str) -> Any:
        """Return cached SDK tools for one room, constructing them on demand."""
        if self.agent_rest is None:
            logger.warning("No agent credential configured for room %s.", room_id)
            return None

        cached = self._agent_tools_cache.get(room_id)
        if cached is not None:
            self._agent_tools_cache.move_to_end(room_id)
            return cached

        tools = _create_agent_tools(room_id, self.agent_rest)
        if tools is None:
            return None
        self._agent_tools_cache[room_id] = tools
        self._agent_tools_cache.move_to_end(room_id)
        if len(self._agent_tools_cache) > AGENT_TOOLS_CACHE_MAX_SIZE:
            self._agent_tools_cache.popitem(last=False)
        return tools

    def discard(self, room_id: str, instance: Any) -> None:
        """Evict ``instance`` only when it is still the current room entry."""
        if self._agent_tools_cache.get(room_id) is instance:
            self._agent_tools_cache.pop(room_id)

    def room_lock(self, room_id: str | None) -> asyncio.Lock:
        """Return the fixed lock stripe for a room-scoped tool call."""
        return self._agent_tools_locks[hash(room_id) % AGENT_TOOLS_LOCK_STRIPES]


def _require_sdk_tools() -> tuple[Any, Any]:
    """Import the SDK tool classes or raise an actionable configuration error."""
    try:
        from band.runtime.tools import AgentTools, HumanTools
    except ImportError as exc:
        raise ConfigError(
            "band-sdk is required but is not importable "
            "(`from band.runtime.tools import HumanTools, AgentTools` failed: "
            f"{exc}). Install/upgrade with `pip install 'band-sdk>=1.0.0'` or `uv sync`."
        ) from exc
    return HumanTools, AgentTools


def _human_tools_class() -> Any:
    """Return the SDK HumanTools class."""
    HumanTools, _ = _require_sdk_tools()
    return HumanTools


def _agent_tools_class() -> Any:
    """Return the SDK AgentTools class."""
    _, AgentTools = _require_sdk_tools()
    return AgentTools


def _create_agent_tools(room_id: str, rest: AsyncRestClient) -> Any:
    """Construct one SDK AgentTools instance without masking configuration errors."""
    try:
        return _agent_tools_class()(room_id=room_id, rest=rest)
    except ConfigError:
        raise
    except Exception as exc:  # pragma: no cover - defensive SDK constructor guard
        logger.warning("Failed to construct AgentTools for room %s: %s", room_id, exc)
        return None


def _create_human_tools(rest: AsyncRestClient) -> Any:
    """Construct the one HumanTools instance for this server."""
    try:
        return _human_tools_class()(rest=rest)
    except ConfigError:
        raise
    except Exception as exc:  # pragma: no cover - defensive SDK constructor guard
        logger.warning("Failed to construct HumanTools singleton: %s", exc)
        return None


def build_app_context(config: Config | None = None) -> AppContext:
    """Build dependencies from final resolved configuration without network I/O."""
    if config is None:
        legacy_key = settings.band_api_key
        can_human, can_agent = legacy_key_capabilities(legacy_key)
        scope = [
            surface
            for surface, enabled in (("human", can_human), ("agent", can_agent))
            if enabled
        ]
        config = Config(legacy_key=legacy_key or None, scope=scope)  # type: ignore[arg-type]

    human_key = (
        resolve_credential_for_scope(config, "human")
        if "human" in config.scope
        else None
    )
    agent_key = (
        resolve_credential_for_scope(config, "agent")
        if "agent" in config.scope
        else None
    )
    base_url = settings.band_base_url
    human_rest = (
        AsyncRestClient(api_key=human_key, base_url=base_url) if human_key else None
    )
    agent_rest = (
        AsyncRestClient(api_key=agent_key, base_url=base_url) if agent_key else None
    )

    return AppContext(
        human_rest=human_rest,
        agent_rest=agent_rest,
        human_tools=_create_human_tools(human_rest) if human_rest else None,
        agent_tools_roomless=_create_agent_tools("", agent_rest)
        if agent_rest
        else None,
        pinned_room_id=config.room_id,
        scope=list(config.scope),
        tools=list(config.tools),
    )


def get_app_context(ctx: Any) -> AppContext:
    """Extract the application context from the current MCP request context."""
    return ctx.request_context.lifespan_context
