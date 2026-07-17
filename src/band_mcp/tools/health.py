"""The server diagnostic tool that is not part of the Band SDK surface."""

from __future__ import annotations

from typing import Any

from band.runtime.mcp_server import MCPToolRegistration
from pydantic import BaseModel

from band_mcp.context import AppContext
from band_mcp.settings import settings

__all__ = ["health_registration"]


class HealthCheckInput(BaseModel):
    """Test MCP server and API connectivity."""


def health_registration(context: AppContext) -> MCPToolRegistration:
    """Build the diagnostic registration for one server context."""

    async def execute(arguments: dict[str, Any]) -> str:  # noqa: ARG001
        checked: list[str] = []
        if context.human_rest is not None:
            try:
                await context.human_rest.human_api_agents.list_my_agents()
                checked.append("human")
            except Exception as exc:
                return f"Failed | human | {exc}"
        if context.agent_rest is not None:
            try:
                await context.agent_rest.agent_api_identity.get_agent_me()
                checked.append("agent")
            except Exception as exc:
                return f"Failed | agent | {exc}"
        if checked:
            return f"OK | {','.join(checked)} | {settings.band_base_url}"
        return "Failed | no credential configured"

    return MCPToolRegistration(
        name="health_check",
        description=HealthCheckInput.__doc__ or "",
        input_model=HealthCheckInput,
        execute=execute,
    )
