from datetime import datetime
from typing import Any, Optional

from band_rest import ChatMessageRequest, ChatMessageRequestMentionsItem

from band_mcp.shared import AppContextType, get_app_context, mcp, serialize_response


@mcp.tool()
def list_my_chat_messages(
    ctx: AppContextType,
    chat_id: str,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    message_type: Optional[str] = None,
    since: Optional[str] = None,
) -> str:
    """List messages in a chat room.

    Args:
        chat_id: The chat room ID (required).
        page: Page number (optional).
        page_size: Items per page (optional).
        message_type: Filter by type: 'text', 'tool_call', etc. (optional).
        since: ISO 8601 timestamp to filter messages after (optional).
    """
    client = get_app_context(ctx).client

    since_dt = None
    if since:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))

    result = client.human_api_messages.list_my_chat_messages(
        chat_id=chat_id,
        page=page,
        page_size=page_size,
        message_type=message_type,
        since=since_dt,
    )
    return serialize_response(result)


@mcp.tool()
def send_my_chat_message(
    ctx: AppContextType,
    chat_id: str,
    content: str,
    recipients: str,
) -> str:
    """Send a message in a chat room.

    Args:
        chat_id: The chat room ID (required).
        content: Message text (required).
        recipients: Non-empty comma-separated participant names to @mention (required).
                    Must contain at least one name; empty string is not accepted.
    """
    client = get_app_context(ctx).client

    recipient_names = [
        name.strip().lower() for name in recipients.split(",") if name.strip()
    ]

    if not recipient_names:
        return "Error: recipients cannot be empty"

    # Fetch participants to resolve names to IDs
    participants_response = client.human_api_participants.list_my_chat_participants(
        chat_id=chat_id
    )
    participants = participants_response.data or []

    # Build name -> participant mapping
    name_to_participant: dict[str, Any] = {}
    for p in participants:
        if hasattr(p, "name") and p.name:
            name_to_participant[p.name.lower()] = p
        if hasattr(p, "username") and p.username:
            name_to_participant[p.username.lower()] = p
        if hasattr(p, "first_name") and p.first_name:
            name_to_participant[p.first_name.lower()] = p

    # Resolve names to mentions
    mentions_list: list[ChatMessageRequestMentionsItem] = []
    not_found: list[str] = []

    for name in recipient_names:
        participant = name_to_participant.get(name)
        if participant:
            display_name = getattr(participant, "name", None) or getattr(
                participant, "username", "Unknown"
            )
            mentions_list.append(
                ChatMessageRequestMentionsItem(id=participant.id, name=display_name)
            )
        else:
            not_found.append(name)

    if not_found:
        available = list(name_to_participant.keys())
        return (
            f"Error: Not found: {', '.join(not_found)}. "
            f"Available: {', '.join(available)}"
        )

    message_request = ChatMessageRequest(content=content, mentions=mentions_list)
    result = client.human_api_messages.send_my_chat_message(
        chat_id=chat_id, message=message_request
    )
    return serialize_response(result)
