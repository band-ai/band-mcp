from typing import Optional

from band_rest import ParticipantRequest

from band_mcp.shared import AppContextType, get_app_context, mcp, serialize_response


@mcp.tool()
def list_my_chat_participants(
    ctx: AppContextType,
    chat_id: str,
    participant_type: Optional[str] = None,
) -> str:
    """List participants in a chat room.

    Args:
        chat_id: The chat room ID (required).
        participant_type: Filter by type: 'User' or 'Agent' (optional).
    """
    client = get_app_context(ctx).client
    result = client.human_api_participants.list_my_chat_participants(
        chat_id=chat_id, participant_type=participant_type
    )
    return serialize_response(result)


@mcp.tool()
def add_my_chat_participant(
    ctx: AppContextType,
    chat_id: str,
    participant_id: str,
    role: Optional[str] = None,
) -> str:
    """Add a participant to a chat room.

    Args:
        chat_id: The chat room ID (required).
        participant_id: ID of user or agent to add (required).
        role: 'owner', 'admin', or 'member' (optional, defaults to 'member').
    """
    client = get_app_context(ctx).client
    participant = ParticipantRequest(
        participant_id=participant_id,
        role=role or "member",
    )
    client.human_api_participants.add_my_chat_participant(
        chat_id=chat_id, participant=participant
    )
    return f"Added participant: {participant_id}"


@mcp.tool()
def remove_my_chat_participant(
    ctx: AppContextType,
    chat_id: str,
    participant_id: str,
) -> str:
    """Remove a participant from a chat room.

    Args:
        chat_id: The chat room ID (required).
        participant_id: ID of participant to remove (required).
    """
    client = get_app_context(ctx).client
    client.human_api_participants.remove_my_chat_participant(
        chat_id=chat_id, id=participant_id
    )
    return f"Removed participant: {participant_id}"
