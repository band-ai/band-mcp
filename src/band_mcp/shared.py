"""Temporary FastMCP compatibility layer during the server migration."""

from __future__ import annotations

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from mcp.server.transport_security import TransportSecuritySettings

from band_mcp.config import Config
from band_mcp.context import AppContext, build_app_context
from band_mcp.settings import settings

__all__ = ["AppContextType", "logger", "mcp", "set_pending_config"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

AppContextType = Context[ServerSession, AppContext, None]
_pending_config: Config | None = None


def set_pending_config(config: Config) -> None:
    """Store resolved configuration until the legacy FastMCP lifespan starts."""
    global _pending_config
    _pending_config = config


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Build and own the application context for a legacy FastMCP server."""
    logger.info("Initializing Band API client")
    app_context = build_app_context(_pending_config)
    try:
        yield app_context
    finally:
        logger.info("Band MCP server lifespan shutdown complete")


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
    name="band-mcp-server",
    lifespan=app_lifespan,
    host=settings.host,
    port=settings.port,
    transport_security=transport_security,
)
