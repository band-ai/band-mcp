import json
import logging
import re
from typing import Any, Dict, List, Literal, Optional, Union

from thenvoi_rest import (
    ChatMessageRequest,
    ChatMessageRequestMentionsItem,
)
from thenvoi_rest.core.api_error import ApiError

from thenvoi_mcp.shared import AppContextType, get_app_context, mcp, serialize_response

logger = logging.getLogger(__name__)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


def _looks_like_uuid(value: Any) -> bool:
    """True if value is a string matching the canonical UUID form."""
    return isinstance(value, str) and bool(_UUID_RE.match(value))


def _build_participant_index(client: Any, chat_id: str) -> Dict[str, Any]:
    """Map a chat room's participants by every name-like key (lowercased, @-stripped).

    Indexes name, username, display_name and handle so a caller can resolve a
    participant by any of them — used to turn human-friendly names or handles
    into the platform participant IDs that mentions require.
    """
    participants_response = client.agent_api_participants.list_agent_chat_participants(
        chat_id=chat_id
    )
    index: Dict[str, Any] = {}
    for p in participants_response.data or []:
        for attr in ("name", "username", "display_name", "handle"):
            val = getattr(p, attr, None)
            if isinstance(val, str) and val:
                index[val.lower().lstrip("@")] = p
    return index


def _participant_display_name(participant: Any) -> str:
    """Best display name for a participant, without the @ prefix."""
    return (
        getattr(participant, "name", None)
        or getattr(participant, "username", None)
        or getattr(participant, "display_name", None)
        or "Unknown"
    )


@mcp.tool()
def list_agent_messages(
    ctx: AppContextType,
    chat_id: str,
    status: Optional[
        Literal["pending", "processing", "processed", "failed", "all"]
    ] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> str:
    """List messages that the agent needs to process, filtered by status.

    Default behavior (no status): Returns all messages that are NOT processed.
    This is the recommended way to get all work the agent should handle, including
    new, delivered, processing (stuck/crashed), and failed messages.

    Status filter options:
    - (no param): Everything NOT processed - get all work to do
    - "pending": No status, delivered, or failed without active attempt - queue depth
    - "processing": Currently being processed - in-flight work
    - "processed": Successfully completed - done items
    - "failed": Failed only - failure backlog
    - "all": All messages regardless of status - full history

    Messages are returned in chronological order (oldest first).

    Workflow after retrieving messages:
    1. Get messages via this tool or get_agent_next_message
    2. Call mark_agent_message_processing before starting work
    3. Process the message
    4. Call mark_agent_message_processed or mark_agent_message_failed

    Args:
        chat_id: The unique identifier of the chat room (required).
        status: Filter by processing status (optional, default: all actionable).
        page: Page number for pagination (optional).
        page_size: Items per page (optional, default: 20, max: 100).

    Returns:
        JSON string containing the list of messages.
    """
    logger.debug("Listing agent messages for chat: %s (status=%s)", chat_id, status)
    client = get_app_context(ctx).client
    result = client.agent_api_messages.list_agent_messages(
        chat_id=chat_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    message_count = len(result.data) if result.data else 0
    logger.info("Retrieved %s messages for chat: %s", message_count, chat_id)
    return serialize_response(result)


@mcp.tool()
def get_agent_next_message(
    ctx: AppContextType,
    chat_id: str,
) -> str:
    """Get the next message that needs processing.

    Returns the single oldest message that is NOT processed, including
    new, delivered, processing (stuck/crashed), and failed messages.

    Returns empty result if there are no messages to process.

    This is the primary endpoint for agent reasoning loops:
    1. Call this tool to get the next work item
    2. Call mark_agent_message_processing to claim the message
    3. Process the message (reasoning, tool calls, etc.)
    4. Call mark_agent_message_processed or mark_agent_message_failed
    5. Loop back to step 1

    Crash recovery: If the agent crashes while processing, the message stays
    in "processing" state. When restarted, calling this tool returns that same
    stuck message (oldest first), allowing the agent to reclaim and retry it.

    Difference from list_agent_messages:
    - list_agent_messages returns ALL actionable messages (batch processing)
    - get_agent_next_message returns ONE message (sequential processing loops)

    Args:
        chat_id: The unique identifier of the chat room (required).

    Returns:
        JSON string containing the next message to process, or empty if none.
    """
    logger.debug("Getting next message for chat: %s", chat_id)
    client = get_app_context(ctx).client
    try:
        result = client.agent_api_messages.get_agent_next_message(chat_id=chat_id)
    except ApiError as e:
        if e.status_code == 204:
            logger.info("No messages to process for chat: %s", chat_id)
            return json.dumps({"data": None, "message": "No messages to process"})
        raise
    logger.info("Next message retrieved for chat: %s", chat_id)
    return serialize_response(result)


@mcp.tool()
def get_agent_chat_context(
    ctx: AppContextType,
    chat_id: str,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> str:
    """Get conversation context for agent rehydration.

    Returns all messages relevant to the agent for execution context/rehydration.
    This includes:
    - All messages the agent sent (any type: text, tool_call, tool_result, thought, etc.)
    - All text messages that @mention the agent

    Use this to load the complete context a remote agent needs to resume execution.
    Messages are returned in chronological order (oldest first).

    Args:
        chat_id: The unique identifier of the chat room (required).
        page: Page number for pagination (optional, default: 1).
        page_size: Items per page (optional, default: 50, max: 100).

    Returns:
        JSON string containing the agent's conversation context with messages.
    """
    logger.debug("Fetching agent context for chat: %s", chat_id)
    client = get_app_context(ctx).client
    result = client.agent_api_context.get_agent_chat_context(
        chat_id=chat_id,
        page=page,
        page_size=page_size,
    )
    message_count = len(result.data) if result.data else 0
    logger.info("Retrieved %s context messages for chat: %s", message_count, chat_id)
    return serialize_response(result)


@mcp.tool()
def create_agent_chat_message(
    ctx: AppContextType,
    chat_id: str,
    content: str,
    recipients: Optional[str] = None,
    mentions: Optional[Union[str, list]] = None,
) -> str:
    """Send a text message in a chat room.

    Creates a new text message in a chat room. Messages MUST include at least
    one @mention to ensure proper routing to recipients.

    TWO WAYS TO SPECIFY RECIPIENTS:

    Option 1 - Use `recipients` (recommended for LLMs):
        Provide comma-separated names. The tool resolves names to IDs automatically.
        Example: recipients="weather agent,sarah"

    Option 2 - Use `mentions`:
        Provide a list of mentions — either as a native list or a JSON-encoded
        string. Each item may be a handle/name string, or an object with any of
        id / handle / name. Handles and names are resolved to participant IDs
        automatically; items that already carry a UUID `id` skip resolution.
        Example: mentions=[{"id": "uuid-123", "name": "weather agent"}]
        Example: mentions=["weather agent", "@sarah"]

    If both are provided, `mentions` takes precedence.

    For event-type messages (tool_call, tool_result, thought, error, etc.),
    use create_agent_chat_event instead.

    Args:
        chat_id: The unique identifier of the chat room (required).
        content: The message content/text (required).
        recipients: Comma-separated participant names to tag (LLM-friendly).
                   Example: "weather agent,sarah,mike"
                   Names are resolved to IDs via list_agent_chat_participants.
        mentions: List of mentions, as a native list or a JSON-encoded string.
                 Items may be handle/name strings or objects with id/handle/name.
                 Format: [{"id": "uuid", "name": "display_name"}, ...] or
                 ["handle-or-name", ...]. Handles/names are resolved to IDs;
                 UUID ids are used as-is.

    Returns:
        JSON string containing the created message details.

    Examples:
        # LLM usage (names):
        create_agent_chat_message(chat_id="123", content="Hello!", recipients="weather agent")

        # LLM usage (mentions as a list of handles):
        create_agent_chat_message(chat_id="123", content="Hello!", mentions=["weather agent"])

        # Library usage (pre-resolved IDs):
        create_agent_chat_message(
            chat_id="123",
            content="Hello!",
            mentions=[{"id": "uuid-456", "name": "weather agent"}]
        )
    """
    logger.debug("Creating message in chat: %s", chat_id)
    client = get_app_context(ctx).client

    mentions_list: List[ChatMessageRequestMentionsItem] = []

    # Option 1: mentions provided (native list OR JSON-encoded string).
    if mentions:
        if isinstance(mentions, str):
            try:
                parsed_mentions = json.loads(mentions)
            except json.JSONDecodeError as e:
                return (
                    f"Error: Invalid JSON for mentions: {str(e)}. Pass a native "
                    f'list like [{{"id": "uuid", "name": "display_name"}}] or '
                    f"[\"handle\"], or use recipients='name1,name2'."
                )
        else:
            parsed_mentions = mentions

        if not isinstance(parsed_mentions, list):
            return (
                f"Error: mentions must be a list of mention objects or handles, "
                f"got {type(parsed_mentions).__name__}."
            )

        # Split into pre-resolved (UUID-id objects) and items needing lookup
        # (handle/name strings, or objects whose id is a handle, not a UUID).
        needs_resolution: List[Any] = []
        for m in parsed_mentions:
            if isinstance(m, dict) and _looks_like_uuid(m.get("id")):
                mentions_list.append(
                    ChatMessageRequestMentionsItem(
                        id=m["id"], name=m.get("name") or "Unknown"
                    )
                )
            else:
                needs_resolution.append(m)

        if needs_resolution:
            index = _build_participant_index(client, chat_id)
            not_found: List[str] = []
            for m in needs_resolution:
                if isinstance(m, str):
                    key = m
                elif isinstance(m, dict):
                    key = m.get("handle") or m.get("name") or m.get("id") or ""
                else:
                    not_found.append(str(m))
                    continue
                participant = index.get(str(key).lower().lstrip("@"))
                if participant:
                    mentions_list.append(
                        ChatMessageRequestMentionsItem(
                            id=participant.id,
                            name=_participant_display_name(participant),
                        )
                    )
                else:
                    not_found.append(str(key))

            if not_found:
                return (
                    f"Error: Could not resolve mentions: {', '.join(not_found)}. "
                    f"Available participants: {', '.join(index.keys())}"
                )

        if not mentions_list:
            return (
                "Error: mentions resolved to an empty list. Provide at least one "
                "valid mention (handle, name, or {id, name})."
            )

    # Option 2: Resolve names to IDs (LLM-friendly path)
    elif recipients:
        recipient_names = [
            name.strip().lower() for name in recipients.split(",") if name.strip()
        ]

        if not recipient_names:
            return "Error: recipients cannot be empty"

        # Fetch participants to map names to IDs
        name_to_participant = _build_participant_index(client, chat_id)

        # Resolve names to mentions
        not_found = []
        for name in recipient_names:
            participant = name_to_participant.get(name.lstrip("@"))
            if participant:
                mentions_list.append(
                    ChatMessageRequestMentionsItem(
                        id=participant.id,
                        name=_participant_display_name(participant),
                    )
                )
            else:
                not_found.append(name)

        if not_found:
            available_names = list(name_to_participant.keys())
            return (
                f"Error: Could not find participants: {', '.join(not_found)}. "
                f"Available participants: {', '.join(available_names)}"
            )

    # Neither provided - error with helpful guidance
    else:
        return (
            f"Error: Missing recipients or mentions. To send a message, specify who to tag. "
            f'Use recipients=\'name1,name2\' (names) or mentions=[{{"id":"uuid","name":"display_name"}}] (IDs). '
            f"Call list_agent_chat_participants(chat_id='{chat_id}') to see available participants."
        )

    # Build and send message
    message_request = ChatMessageRequest(
        content=content,
        mentions=mentions_list,
    )

    result = client.agent_api_messages.create_agent_chat_message(
        chat_id=chat_id,
        message=message_request,
    )

    logger.info("Message sent successfully: %s", result.data.id)
    return serialize_response(result)
