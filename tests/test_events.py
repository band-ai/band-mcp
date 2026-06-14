"""Unit tests for event tools (create_agent_chat_event)."""

import json

import pytest

from thenvoi_testing.factories import factory
from band_mcp.tools.agent.agent_events import (
    VALID_EVENT_TYPES,
    create_agent_chat_event,
)


class TestCreateAgentChatEvent:
    """Tests for create_agent_chat_event tool."""

    def test_creates_thought_event(self, mock_ctx, mock_agent_api):
        """Test creating a thought event."""
        chat_id = "chat-123"
        content = "I should check the weather first"
        event = factory.chat_event(
            id="event-456", content=content, message_type="thought"
        )
        mock_agent_api.create_agent_chat_event.return_value = factory.response(event)

        result = create_agent_chat_event(
            mock_ctx, chat_id=chat_id, content=content, message_type="thought"
        )

        mock_agent_api.create_agent_chat_event.assert_called_once()
        call_args = mock_agent_api.create_agent_chat_event.call_args
        assert call_args.kwargs["chat_id"] == chat_id
        assert call_args.kwargs["event"].content == content
        assert call_args.kwargs["event"].message_type == "thought"
        parsed = json.loads(result)
        assert parsed["data"]["id"] == "event-456"

    def test_creates_tool_call_event(self, mock_ctx, mock_agent_api):
        """Test creating a tool_call event with metadata."""
        chat_id = "chat-123"
        content = "Calling weather_service"
        metadata = '{"function": {"name": "get_weather", "arguments": {"city": "NYC"}}, "id": "call_1", "type": "function"}'
        event = factory.chat_event(id="event-789", message_type="tool_call")
        mock_agent_api.create_agent_chat_event.return_value = factory.response(event)

        create_agent_chat_event(
            mock_ctx,
            chat_id=chat_id,
            content=content,
            message_type="tool_call",
            metadata=metadata,
        )

        call_args = mock_agent_api.create_agent_chat_event.call_args
        assert call_args.kwargs["event"].message_type == "tool_call"
        assert call_args.kwargs["event"].metadata["function"]["name"] == "get_weather"

    def test_creates_tool_result_event(self, mock_ctx, mock_agent_api):
        """Test creating a tool_result event with metadata."""
        chat_id = "chat-123"
        content = "Weather retrieved successfully"
        metadata = '{"success": true, "temperature": 72, "conditions": "sunny"}'
        event = factory.chat_event(id="event-101", message_type="tool_result")
        mock_agent_api.create_agent_chat_event.return_value = factory.response(event)

        create_agent_chat_event(
            mock_ctx,
            chat_id=chat_id,
            content=content,
            message_type="tool_result",
            metadata=metadata,
        )

        call_args = mock_agent_api.create_agent_chat_event.call_args
        assert call_args.kwargs["event"].message_type == "tool_result"
        assert call_args.kwargs["event"].metadata["success"] is True

    def test_creates_error_event(self, mock_ctx, mock_agent_api):
        """Test creating an error event."""
        chat_id = "chat-123"
        content = "API rate limit exceeded"
        metadata = '{"error_code": "RATE_LIMIT", "retry_after": 60}'
        event = factory.chat_event(id="event-err", message_type="error")
        mock_agent_api.create_agent_chat_event.return_value = factory.response(event)

        create_agent_chat_event(
            mock_ctx,
            chat_id=chat_id,
            content=content,
            message_type="error",
            metadata=metadata,
        )

        call_args = mock_agent_api.create_agent_chat_event.call_args
        assert call_args.kwargs["event"].message_type == "error"

    def test_creates_task_event(self, mock_ctx, mock_agent_api):
        """Test creating a task event."""
        chat_id = "chat-123"
        content = "Task started"
        event = factory.chat_event(id="event-task", message_type="task")
        mock_agent_api.create_agent_chat_event.return_value = factory.response(event)

        create_agent_chat_event(
            mock_ctx, chat_id=chat_id, content=content, message_type="task"
        )

        call_args = mock_agent_api.create_agent_chat_event.call_args
        assert call_args.kwargs["event"].message_type == "task"

    def test_creates_event_without_metadata(self, mock_ctx, mock_agent_api):
        """Test creating an event without metadata."""
        event = factory.chat_event(id="event-no-meta")
        mock_agent_api.create_agent_chat_event.return_value = factory.response(event)

        create_agent_chat_event(
            mock_ctx,
            chat_id="chat-123",
            content="Simple thought",
            message_type="thought",
        )

        call_args = mock_agent_api.create_agent_chat_event.call_args
        assert call_args.kwargs["event"].metadata is None

    def test_message_type_is_case_insensitive(self, mock_ctx, mock_agent_api):
        """Test that message_type parameter is case insensitive."""
        event = factory.chat_event(id="event-case")
        mock_agent_api.create_agent_chat_event.return_value = factory.response(event)

        create_agent_chat_event(
            mock_ctx, chat_id="chat-123", content="Test", message_type="THOUGHT"
        )

        call_args = mock_agent_api.create_agent_chat_event.call_args
        assert call_args.kwargs["event"].message_type == "thought"

    def test_raises_on_invalid_message_type(self, mock_ctx, mock_agent_api):
        """Test error handling for invalid message type."""
        with pytest.raises(ValueError, match="Invalid message_type: invalid"):
            create_agent_chat_event(
                mock_ctx, chat_id="chat-123", content="Test", message_type="invalid"
            )

    def test_raises_on_invalid_metadata_json(self, mock_ctx, mock_agent_api):
        """Test error handling for invalid JSON in metadata."""
        with pytest.raises(ValueError, match="Invalid JSON for metadata"):
            create_agent_chat_event(
                mock_ctx,
                chat_id="chat-123",
                content="Test",
                message_type="thought",
                metadata="not valid json",
            )

    def test_valid_event_types_constant(self):
        """Test that VALID_EVENT_TYPES contains expected values."""
        expected = {"tool_call", "tool_result", "thought", "error", "task"}
        assert VALID_EVENT_TYPES == expected

    @pytest.mark.parametrize(
        "event_type", ["tool_call", "tool_result", "thought", "error", "task"]
    )
    def test_all_valid_event_types_accepted(self, mock_ctx, mock_agent_api, event_type):
        """Test that all valid event types are accepted."""
        event = factory.chat_event(message_type=event_type)
        mock_agent_api.create_agent_chat_event.return_value = factory.response(event)

        create_agent_chat_event(
            mock_ctx, chat_id="chat-123", content="Test", message_type=event_type
        )

        call_args = mock_agent_api.create_agent_chat_event.call_args
        assert call_args.kwargs["event"].message_type == event_type
