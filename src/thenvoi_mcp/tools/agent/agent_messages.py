import json
import logging
from typing import Any, Dict, List, Literal, Optional

from thenvoi_rest import (
    ChatMessageRequest,
    ChatMessageRequestMentionsItem,
)
from thenvoi_rest.core.api_error import ApiError

from thenvoi_mcp.shared import AppContextType, get_app_context, mcp, serialize_response

logger = logging.getLogger(__name__)


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
    mentions: Optional[str] = None,
) -> str:
    """Send a text message in a chat room.

    Creates a new text message in a chat room. Messages MUST include at least
    one @mention to ensure proper routing to recipients.

    TWO WAYS TO SPECIFY RECIPIENTS:

    Option 1 - Use `recipients` (recommended for LLMs):
        Provide comma-separated names. The tool resolves names to IDs automatically.
        Example: recipients="weather agent,sarah"

    Option 2 - Use `mentions` (for libraries with caching):
        Provide a JSON array with pre-resolved IDs.
        Example: mentions='[{"id": "uuid-123", "name": "weather agent"}]'

    If both are provided, `mentions` takes precedence (no API call needed).

    For event-type messages (tool_call, tool_result, thought, error, etc.),
    use create_agent_chat_event instead.

    Args:
        chat_id: The unique identifier of the chat room (required).
        content: The message content/text (required).
        recipients: Comma-separated participant names to tag (LLM-friendly).
                   Example: "weather agent,sarah,mike"
                   Names are resolved to IDs via list_agent_chat_participants.
        mentions: JSON array of mentions with pre-resolved IDs (for libraries).
                 Format: [{"id": "uuid", "name": "display_name"}, ...]
                 When provided, skips name resolution (more efficient).

    Returns:
        JSON string containing the created message details.

    Examples:
        # LLM usage (names):
        create_agent_chat_message(chat_id="123", content="Hello!", recipients="weather agent")

        # Library usage (pre-resolved IDs):
        create_agent_chat_message(
            chat_id="123",
            content="Hello!",
            mentions='[{"id": "uuid-456", "name": "weather agent"}]'
        )
    """
    logger.debug("Creating message in chat: %s", chat_id)
    client = get_app_context(ctx).client

    mentions_list: List[ChatMessageRequestMentionsItem] = []

    # Option 1: Pre-resolved mentions provided (efficient path for libraries)
    if mentions:
        try:
            parsed_mentions = json.loads(mentions)
            mentions_list = [
                ChatMessageRequestMentionsItem(id=m["id"], name=m["name"])
                for m in parsed_mentions
            ]
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON for mentions: {str(e)}"
        except KeyError as e:
            return f"Error: Missing required field in mentions: {str(e)}"

    # Option 2: Resolve names to IDs (LLM-friendly path)
    elif recipients:
        recipient_names = [
            name.strip().lower() for name in recipients.split(",") if name.strip()
        ]

        if not recipient_names:
            return "Error: recipients cannot be empty"

        # Fetch participants to map names to IDs
        participants_response = (
            client.agent_api_participants.list_agent_chat_participants(chat_id=chat_id)
        )
        participants = participants_response.data

        # Build name -> participant mapping (case-insensitive)
        name_to_participant: Dict[str, Any] = {}
        for p in participants:
            # Agent participants have 'name' field
            if hasattr(p, "name") and p.name:
                name_to_participant[p.name.lower()] = p
            # User participants may have 'username' or 'display_name'
            if hasattr(p, "username") and p.username:
                name_to_participant[p.username.lower()] = p
            if hasattr(p, "display_name") and p.display_name:
                name_to_participant[p.display_name.lower()] = p

        # Resolve names to mentions
        not_found: List[str] = []
        for name in recipient_names:
            participant = name_to_participant.get(name)
            if participant:
                display_name = (
                    getattr(participant, "name", None)
                    or getattr(participant, "username", None)
                    or getattr(participant, "display_name", "Unknown")
                )
                mentions_list.append(
                    ChatMessageRequestMentionsItem(id=participant.id, name=display_name)
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
            f'Use recipients=\'name1,name2\' (names) or mentions=\'[{{"id":"uuid","name":"display_name"}}]\' (IDs). '
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
