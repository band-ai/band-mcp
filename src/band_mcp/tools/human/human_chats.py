from typing import Optional

from band_rest import CreateMyChatRoomRequestChat

from band_mcp.shared import AppContextType, get_app_context, mcp, serialize_response


@mcp.tool()
def list_my_chats(
    ctx: AppContextType,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> str:
    """List chat rooms where the user is a participant.

    Args:
        page: Page number (optional).
        page_size: Items per page (optional).
    """
    client = get_app_context(ctx).client
    result = client.human_api_chats.list_my_chats(page=page, page_size=page_size)
    return serialize_response(result)


@mcp.tool()
def get_my_chat(ctx: AppContextType, chat_id: str) -> str:
    """Get a specific chat room by ID.

    Args:
        chat_id: The chat room ID (required).
    """
    client = get_app_context(ctx).client
    result = client.human_api_chats.get_my_chat_room(id=chat_id)
    return serialize_response(result)


@mcp.tool()
def create_my_chat(ctx: AppContextType, task_id: Optional[str] = None) -> str:
    """Create a new chat room with the user as owner.

    Args:
        task_id: Optional task ID to associate with the chat.
    """
    client = get_app_context(ctx).client
    chat_request = (
        CreateMyChatRoomRequestChat(task_id=task_id)
        if task_id
        else CreateMyChatRoomRequestChat()
    )
    result = client.human_api_chats.create_my_chat_room(chat=chat_request)
    return serialize_response(result)
