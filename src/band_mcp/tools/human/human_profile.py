from typing import Any, Optional, cast

from band_mcp.shared import AppContextType, get_app_context, mcp, serialize_response


@mcp.tool()
def get_my_profile(ctx: AppContextType) -> str:
    """Get the current user's profile details.

    Returns your profile information including name, email, role, etc.
    """
    client = get_app_context(ctx).client
    result = client.human_api_profile.get_my_profile()
    return serialize_response(result)


@mcp.tool()
def update_my_profile(
    ctx: AppContextType,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> str:
    """Update the current user's profile.

    Args:
        first_name: New first name (optional).
        last_name: New last name (optional).
    """
    client = get_app_context(ctx).client

    # Only include fields that are actually provided (not None)
    # to avoid the API interpreting None as "set to null"
    user_data: dict[str, Any] = {}
    if first_name is not None:
        user_data["first_name"] = first_name
    if last_name is not None:
        user_data["last_name"] = last_name

    if not user_data:
        return "Error: At least one field (first_name or last_name) must be provided"

    result = client.human_api_profile.update_my_profile(user=cast(Any, user_data))
    return serialize_response(result)


@mcp.tool()
def list_my_peers(
    ctx: AppContextType,
    not_in_chat: Optional[str] = None,
    peer_type: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> str:
    """List entities you can interact with in chat rooms.

    Peers include other users, your agents, and global agents.

    Args:
        not_in_chat: Exclude entities already in this chat room (optional).
        peer_type: Filter by type: 'User' or 'Agent' (optional).
        page: Page number (optional).
        page_size: Items per page (optional).
    """
    client = get_app_context(ctx).client
    result = client.human_api_peers.list_my_peers(
        not_in_chat=not_in_chat,
        type=peer_type,
        page=page,
        page_size=page_size,
    )
    return serialize_response(result)
