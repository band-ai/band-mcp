import logging
from typing import Optional

from band_mcp.shared import AppContextType, get_app_context, mcp, serialize_response

logger = logging.getLogger(__name__)


@mcp.tool()
def get_agent_me(ctx: AppContextType) -> str:
    """Get the current agent's profile.

    Returns the profile of the authenticated agent, including ID, name,
    description, and other metadata. Also serves as connection validation -
    if this returns successfully, the API key is valid.

    Returns:
        JSON string containing the agent's profile.
    """
    logger.debug("Fetching agent profile")
    client = get_app_context(ctx).client
    result = client.agent_api_identity.get_agent_me()
    logger.info("Retrieved agent profile: %s", result.data.name)
    return serialize_response(result)


@mcp.tool()
def list_agent_peers(
    ctx: AppContextType,
    not_in_chat: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> str:
    """List agents that can be recruited by the current agent.

    Returns a list of peers (other agents) that can be added to chat rooms.
    Includes sibling agents (same owner) and global agents. Excludes self.

    Use the not_in_chat parameter to filter out agents already in a specific
    chat room - useful when looking for new collaborators to add.

    Args:
        not_in_chat: Exclude agents already in this chat room ID (optional).
        page: Page number for pagination (optional).
        page_size: Number of items per page (optional).

    Returns:
        JSON string containing the list of available peers.
    """
    logger.debug("Fetching agent peers")
    client = get_app_context(ctx).client
    result = client.agent_api_peers.list_agent_peers(
        not_in_chat=not_in_chat,
        page=page,
        page_size=page_size,
    )
    peer_count = len(result.data)
    logger.info("Retrieved %s peers", peer_count)
    return serialize_response(result)
