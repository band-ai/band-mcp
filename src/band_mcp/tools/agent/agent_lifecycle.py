import logging

from band_mcp.shared import AppContextType, get_app_context, mcp, serialize_response

logger = logging.getLogger(__name__)


@mcp.tool()
def mark_agent_message_processing(
    ctx: AppContextType,
    chat_id: str,
    message_id: str,
) -> str:
    """Mark a message as being processed by the agent.

    Creates a new processing attempt with a system-managed timestamp.
    Call this when the agent starts working on a message.

    This endpoint automatically:
    - Creates a new attempt with auto-incremented attempt_number
    - Sets the attempt status to "processing"
    - Records the started_at timestamp (system-managed)
    - Updates the agent's delivery status to "processing"

    Args:
        chat_id: The unique identifier of the chat room (required).
        message_id: The ID of the message to mark as processing (required).

    Returns:
        Success message confirming the message is marked as processing.
    """
    logger.debug("Marking message %s as processing in chat %s", message_id, chat_id)
    client = get_app_context(ctx).client

    result = client.agent_api_messages.mark_agent_message_processing(
        chat_id=chat_id,
        id=message_id,
    )

    logger.info("Message marked as processing: %s", message_id)
    return serialize_response(result)


@mcp.tool()
def mark_agent_message_processed(
    ctx: AppContextType,
    chat_id: str,
    message_id: str,
) -> str:
    """Mark a message as successfully processed by the agent.

    Completes the current processing attempt with a system-managed timestamp.
    Call this when the agent finishes processing a message successfully.

    This endpoint automatically:
    - Sets the current attempt's completed_at timestamp (system-managed)
    - Sets the current attempt status to "success"
    - Sets the agent's processed_at timestamp (system-managed)
    - Updates the agent's delivery status to "processed"

    Note: Requires an active processing attempt. If no processing attempt exists,
    returns a 422 error. Call mark_agent_message_processing first.

    Args:
        chat_id: The unique identifier of the chat room (required).
        message_id: The ID of the message to mark as processed (required).

    Returns:
        Success message confirming the message is marked as processed.
    """
    logger.debug("Marking message %s as processed in chat %s", message_id, chat_id)
    client = get_app_context(ctx).client

    result = client.agent_api_messages.mark_agent_message_processed(
        chat_id=chat_id,
        id=message_id,
    )

    logger.info("Message marked as processed: %s", message_id)
    return serialize_response(result)


@mcp.tool()
def mark_agent_message_failed(
    ctx: AppContextType,
    chat_id: str,
    message_id: str,
    error: str,
) -> str:
    """Mark a message processing as failed by the agent.

    Completes the current processing attempt with an error message.
    Call this when the agent cannot process a message.

    This endpoint automatically:
    - Sets the current attempt's completed_at timestamp (system-managed)
    - Sets the current attempt status to "failed"
    - Records the error message in the current attempt
    - Updates the agent's delivery status to "failed"

    Note: Requires an active processing attempt. If no processing attempt exists,
    returns a 422 error. Call mark_agent_message_processing first.

    Args:
        chat_id: The unique identifier of the chat room (required).
        message_id: The ID of the message to mark as failed (required).
        error: Error message describing why processing failed (required).

    Returns:
        Success message confirming the message is marked as failed.
    """
    logger.debug(
        "Marking message %s as failed in chat %s: %s", message_id, chat_id, error
    )
    client = get_app_context(ctx).client

    result = client.agent_api_messages.mark_agent_message_failed(
        chat_id=chat_id,
        id=message_id,
        error=error,
    )

    logger.info("Message marked as failed: %s", message_id)
    return serialize_response(result)
