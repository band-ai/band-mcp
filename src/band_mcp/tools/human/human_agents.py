from typing import Optional

from band_rest import AgentRegisterRequest

from band_mcp.shared import AppContextType, get_app_context, mcp, serialize_response


@mcp.tool()
def list_my_agents(
    ctx: AppContextType,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> str:
    """List agents owned by the user.

    Args:
        page: Page number (optional).
        page_size: Items per page (optional).
    """
    client = get_app_context(ctx).client
    result = client.human_api_agents.list_my_agents(page=page, page_size=page_size)
    return serialize_response(result)


@mcp.tool()
def register_my_agent(
    ctx: AppContextType,
    name: str,
    description: str,
) -> str:
    """Register a new remote agent.

    Returns the agent details including API key. Save the API key - it's only shown once!

    Args:
        name: Agent name (required).
        description: Agent description (required).
    """
    client = get_app_context(ctx).client
    agent_request = AgentRegisterRequest(name=name, description=description)
    result = client.human_api_agents.register_my_agent(agent=agent_request)
    return serialize_response(result)
