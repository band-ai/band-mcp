import logging
from typing import Optional

from band_rest import ChatRoomRequest

from band_mcp.shared import AppContextType, get_app_context, mcp, serialize_response

logger = logging.getLogger(__name__)


@mcp.tool()
def list_agent_chats(
    ctx: AppContextType,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> str:
    """List chat rooms where the agent is a participant.

    Retrieves a list of chat rooms that the authenticated agent participates in.
    Supports pagination.

    Args:
        page: Page number for pagination (optional).
        page_size: Number of items per page (optional).

    Returns:
        JSON string containing the list of chat rooms.
    """
    logger.debug("Fetching agent's chat rooms")
    client = get_app_context(ctx).client
    result = client.agent_api_chats.list_agent_chats(
        page=page,
        page_size=page_size,
    )
    chat_count = len(result.data)
    logger.info("Retrieved %s chats", chat_count)
    return serialize_response(result)


@mcp.tool()
def get_agent_chat(ctx: AppContextType, chat_id: str) -> str:
    """Get a specific chat room by ID.

    Retrieves detailed information about a single chat room where
    the agent is a participant.

    Args:
        chat_id: The unique identifier of the chat room (required).

    Returns:
        JSON string containing the chat room details.
    """
    logger.debug("Fetching chat with ID: %s", chat_id)
    client = get_app_context(ctx).client
    result = client.agent_api_chats.get_agent_chat(id=chat_id)
    logger.info("Retrieved chat: %s", chat_id)
    return serialize_response(result)


@mcp.tool()
def create_agent_chat(
    ctx: AppContextType,
    task_id: Optional[str] = None,
) -> str:
    """Create a new chat room with the agent as owner.

    Creates a new chat room where the authenticated agent is automatically
    set as the owner. Optionally associates the chat with a task.

    Args:
        task_id: Optional ID of an associated task.

    Returns:
        JSON string containing the created chat room details.
    """
    logger.debug("Creating new chat room")
    client = get_app_context(ctx).client

    # Build request
    chat_request = ChatRoomRequest(task_id=task_id) if task_id else ChatRoomRequest()

    result = client.agent_api_chats.create_agent_chat(chat=chat_request)

    logger.info("Chat room created successfully: %s", result.data.id)
    return serialize_response(result)
