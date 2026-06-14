import json
import logging
from typing import Any, Dict, Literal, Optional

from band_rest import (
    ChatEventMessageType,
    ChatEventRequest,
)

from band_mcp.shared import AppContextType, get_app_context, mcp, serialize_response

logger = logging.getLogger(__name__)


# Valid event types for create_agent_chat_event (matches ChatEventMessageType enum)
VALID_EVENT_TYPES = frozenset(
    [
        "tool_call",
        "tool_result",
        "thought",
        "error",
        "task",
    ]
)


@mcp.tool()
def create_agent_chat_event(
    ctx: AppContextType,
    chat_id: str,
    content: str,
    message_type: Literal["tool_call", "tool_result", "thought", "error", "task"],
    metadata: Optional[str] = None,
) -> str:
    """Post an event in a chat room (tool_call, tool_result, thought, error, task).

    Creates a new event in a chat room. Events do NOT require mentions - they
    report what happened rather than directing messages at participants.

    Event types and their content/metadata structure:

    - **tool_call**: Agent invokes a tool
      - content: Human-readable description (e.g., "Calling send_direct_message_service")
      - metadata: {"function": {"name": "fn_name", "arguments": {...}}, "id": "call_id", "type": "function"}

    - **tool_result**: Result from tool execution
      - content: Human-readable summary (e.g., "Message sent successfully")
      - metadata: {"success": true, "message": "...", ...result data}

    - **thought**: Agent's internal reasoning
      - content: The reasoning text
      - metadata: Optional

    - **error**: Error or failure notification
      - content: Error message
      - metadata: {"error_code": "...", "details": {...}}

    - **task**: Task-related message
      - content: Task message
      - metadata: Optional

    For text messages with mentions, use create_agent_chat_message instead.

    Args:
        chat_id: The unique identifier of the chat room (required).
        content: Human-readable event content (required).
        message_type: Event type (required). One of: 'tool_call', 'tool_result',
                    'thought', 'error', 'task'.
        metadata: Optional JSON object with structured event data. Structure varies by message_type.

    Returns:
        JSON string containing the created event details.

    Examples:
        # Tool call event
        create_agent_chat_event(
            chat_id="123",
            content="Calling weather_service",
            message_type="tool_call",
            metadata='{"function": {"name": "get_weather", "arguments": {"city": "NYC"}}, "id": "call_1", "type": "function"}'
        )

        # Tool result event
        create_agent_chat_event(
            chat_id="123",
            content="Weather retrieved successfully",
            message_type="tool_result",
            metadata='{"success": true, "temperature": 72, "conditions": "sunny"}'
        )

        # Thought event
        create_agent_chat_event(
            chat_id="123",
            content="I should check the weather before suggesting outdoor activities",
            message_type="thought"
        )
    """
    logger.debug("Creating event in chat: %s, type: %s", chat_id, message_type)
    client = get_app_context(ctx).client

    # Validate message type
    message_type_lower = message_type.lower()
    if message_type_lower not in VALID_EVENT_TYPES:
        valid_types = ", ".join(sorted(VALID_EVENT_TYPES))
        raise ValueError(
            f"Invalid message_type: {message_type}. Must be one of: {valid_types}"
        )

    # Parse optional metadata
    metadata_dict: Optional[Dict[str, Any]] = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for metadata: {str(e)}")

    # Cast to ChatEventMessageType for type safety
    event_type: ChatEventMessageType = message_type_lower  # type: ignore[assignment]

    event_request = ChatEventRequest(
        content=content,
        message_type=event_type,
        metadata=metadata_dict,
    )

    result = client.agent_api_events.create_agent_chat_event(
        chat_id=chat_id,
        event=event_request,
    )

    logger.info("Event created successfully: %s", result.data.id)
    return serialize_response(result)
