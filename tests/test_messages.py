"""Unit tests for message tools (list_agent_messages, get_agent_next_message, get_agent_chat_context, create_agent_chat_message)."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from band_rest.core.api_error import ApiError
from thenvoi_testing.factories import factory
from band_mcp.tools.agent.agent_messages import (
    create_agent_chat_message,
    get_agent_chat_context,
    get_agent_next_message,
    list_agent_messages,
)


class TestListAgentMessages:
    """Tests for list_agent_messages tool."""

    def test_returns_messages(self, mock_ctx, mock_agent_api):
        """Test successful retrieval of messages."""
        chat_id = "chat-123"
        messages = [
            factory.chat_message(content="Hello", message_type="text"),
            factory.chat_message(content="Help me", message_type="text"),
        ]
        mock_agent_api.list_agent_messages.return_value = factory.list_response(
            messages
        )

        result = list_agent_messages(mock_ctx, chat_id=chat_id)

        mock_agent_api.list_agent_messages.assert_called_once_with(
            chat_id=chat_id,
            status=None,
            page=None,
            page_size=None,
        )
        parsed = json.loads(result)
        assert len(parsed["data"]) == 2

    def test_status_filter(self, mock_ctx, mock_agent_api):
        """Test filtering messages by status."""
        mock_agent_api.list_agent_messages.return_value = factory.list_response([])

        list_agent_messages(mock_ctx, chat_id="chat-123", status="pending")

        mock_agent_api.list_agent_messages.assert_called_once_with(
            chat_id="chat-123",
            status="pending",
            page=None,
            page_size=None,
        )

    def test_pagination_parameters(self, mock_ctx, mock_agent_api):
        """Test pagination parameters are passed through."""
        mock_agent_api.list_agent_messages.return_value = factory.list_response([])

        list_agent_messages(mock_ctx, chat_id="chat-123", page=2, page_size=25)

        mock_agent_api.list_agent_messages.assert_called_once_with(
            chat_id="chat-123",
            status=None,
            page=2,
            page_size=25,
        )

    def test_empty_messages(self, mock_ctx, mock_agent_api):
        """Test handling of empty message list."""
        mock_agent_api.list_agent_messages.return_value = factory.list_response([])

        result = list_agent_messages(mock_ctx, chat_id="empty-chat")

        parsed = json.loads(result)
        assert parsed["data"] == []


class TestGetAgentNextMessage:
    """Tests for get_agent_next_message tool."""

    def test_returns_next_message(self, mock_ctx, mock_agent_api):
        """Test successful retrieval of next message."""
        chat_id = "chat-123"
        message = factory.chat_message(id="msg-456", content="Process me")
        mock_agent_api.get_agent_next_message.return_value = factory.response(message)

        result = get_agent_next_message(mock_ctx, chat_id=chat_id)

        mock_agent_api.get_agent_next_message.assert_called_once_with(
            chat_id=chat_id,
        )
        parsed = json.loads(result)
        assert parsed["data"]["id"] == "msg-456"

    def test_returns_empty_when_no_messages(self, mock_ctx, mock_agent_api):
        """Test handling when no messages need processing."""
        mock_agent_api.get_agent_next_message.return_value = factory.response(None)

        result = get_agent_next_message(mock_ctx, chat_id="empty-chat")

        parsed = json.loads(result)
        assert parsed["data"] is None

    def test_handles_204_no_content(self, mock_ctx, mock_agent_api):
        """Test that HTTP 204 (no messages) is handled as success, not error."""
        error = ApiError(status_code=204, body=None)
        mock_agent_api.get_agent_next_message.side_effect = error

        result = get_agent_next_message(mock_ctx, chat_id="empty-chat")

        parsed = json.loads(result)
        assert parsed["data"] is None
        assert parsed["message"] == "No messages to process"

    def test_reraises_non_204_errors(self, mock_ctx, mock_agent_api):
        """Test that non-204 errors are reraised."""
        error = ApiError(status_code=500, body="Server error")
        mock_agent_api.get_agent_next_message.side_effect = error

        with pytest.raises(ApiError):
            get_agent_next_message(mock_ctx, chat_id="chat-123")


class TestGetAgentChatContext:
    """Tests for get_agent_chat_context tool."""

    def test_returns_context_messages(self, mock_ctx, mock_agent_api):
        """Test successful retrieval of context messages."""
        chat_id = "chat-123"
        messages = [
            factory.chat_message(content="Hello", message_type="text"),
            factory.chat_message(content="Thinking...", message_type="thought"),
        ]
        mock_agent_api.get_agent_chat_context.return_value = factory.list_response(
            messages
        )

        result = get_agent_chat_context(mock_ctx, chat_id=chat_id)

        mock_agent_api.get_agent_chat_context.assert_called_once_with(
            chat_id=chat_id,
            page=None,
            page_size=None,
        )
        parsed = json.loads(result)
        assert len(parsed["data"]) == 2

    def test_pagination_parameters(self, mock_ctx, mock_agent_api):
        """Test pagination parameters are passed through."""
        mock_agent_api.get_agent_chat_context.return_value = factory.list_response([])

        get_agent_chat_context(mock_ctx, chat_id="chat-123", page=2, page_size=25)

        mock_agent_api.get_agent_chat_context.assert_called_once_with(
            chat_id="chat-123",
            page=2,
            page_size=25,
        )

    def test_empty_context(self, mock_ctx, mock_agent_api):
        """Test handling of empty context."""
        mock_agent_api.get_agent_chat_context.return_value = factory.list_response([])

        result = get_agent_chat_context(mock_ctx, chat_id="empty-chat")

        parsed = json.loads(result)
        assert parsed["data"] == []


class TestCreateAgentChatMessage:
    """Tests for create_agent_chat_message tool."""

    def test_creates_message_with_recipients(self, mock_ctx, mock_agent_api):
        """Test creating a message using recipients parameter."""
        chat_id = "chat-123"
        content = "Hello everyone!"
        participant = factory.chat_participant(id="agent-456", name="Weather Agent")
        mock_agent_api.list_agent_chat_participants.return_value = (
            factory.list_response([participant])
        )
        message = factory.chat_message(id="msg-789", content=content)
        mock_agent_api.create_agent_chat_message.return_value = factory.response(
            message
        )

        result = create_agent_chat_message(
            mock_ctx, chat_id=chat_id, content=content, recipients="Weather Agent"
        )

        mock_agent_api.list_agent_chat_participants.assert_called_once_with(
            chat_id=chat_id
        )
        mock_agent_api.create_agent_chat_message.assert_called_once()
        parsed = json.loads(result)
        assert parsed["data"]["id"] == "msg-789"

    def test_creates_message_with_mentions(self, mock_ctx, mock_agent_api):
        """Test creating a message using pre-resolved mentions."""
        chat_id = "chat-123"
        content = "Hello!"
        mentions = '[{"id": "agent-456", "name": "Weather Agent"}]'
        message = factory.chat_message(id="msg-789", content=content)
        mock_agent_api.create_agent_chat_message.return_value = factory.response(
            message
        )

        result = create_agent_chat_message(
            mock_ctx, chat_id=chat_id, content=content, mentions=mentions
        )

        # Should NOT call list_agent_chat_participants when mentions is provided
        mock_agent_api.list_agent_chat_participants.assert_not_called()
        mock_agent_api.create_agent_chat_message.assert_called_once()
        parsed = json.loads(result)
        assert parsed["data"]["id"] == "msg-789"

    def test_mentions_takes_precedence_over_recipients(self, mock_ctx, mock_agent_api):
        """Test that mentions takes precedence when both are provided."""
        chat_id = "chat-123"
        mentions = '[{"id": "agent-456", "name": "Weather Agent"}]'
        message = factory.chat_message(id="msg-789")
        mock_agent_api.create_agent_chat_message.return_value = factory.response(
            message
        )

        create_agent_chat_message(
            mock_ctx,
            chat_id=chat_id,
            content="Hello!",
            recipients="Other Agent",  # Should be ignored
            mentions=mentions,
        )

        # Should NOT call list_agent_chat_participants when mentions is provided
        mock_agent_api.list_agent_chat_participants.assert_not_called()

    def test_returns_error_when_no_recipients_or_mentions(
        self, mock_ctx, mock_agent_api
    ):
        """Test error when neither recipients nor mentions is provided."""
        result = create_agent_chat_message(
            mock_ctx, chat_id="chat-123", content="Hello!"
        )
        assert "Error" in result
        assert "Missing recipients or mentions" in result

    def test_returns_error_on_invalid_mentions_json(self, mock_ctx, mock_agent_api):
        """Test error handling for invalid JSON in mentions."""
        result = create_agent_chat_message(
            mock_ctx,
            chat_id="chat-123",
            content="Hello!",
            mentions="not valid json",
        )
        assert "Error" in result
        assert "Invalid JSON for mentions" in result

    def test_returns_error_when_recipient_not_found(self, mock_ctx, mock_agent_api):
        """Test error when recipient name doesn't match any participant."""
        participant = factory.chat_participant(name="Existing Agent")
        mock_agent_api.list_agent_chat_participants.return_value = (
            factory.list_response([participant])
        )

        result = create_agent_chat_message(
            mock_ctx,
            chat_id="chat-123",
            content="Hello!",
            recipients="unknown agent",
        )
        assert "Error" in result
        assert "Could not find participants: unknown agent" in result

    def test_multiple_recipients(self, mock_ctx, mock_agent_api):
        """Test message with multiple comma-separated recipients."""
        participants = [
            factory.chat_participant(id="agent-1", name="Agent One"),
            factory.chat_participant(id="agent-2", name="Agent Two"),
        ]
        mock_agent_api.list_agent_chat_participants.return_value = (
            factory.list_response(participants)
        )
        message = factory.chat_message(id="msg-789")
        mock_agent_api.create_agent_chat_message.return_value = factory.response(
            message
        )

        create_agent_chat_message(
            mock_ctx,
            chat_id="chat-123",
            content="Hello!",
            recipients="Agent One, Agent Two",
        )

        call_args = mock_agent_api.create_agent_chat_message.call_args
        mentions = call_args.kwargs["message"].mentions
        assert len(mentions) == 2

    def test_recipient_matching_is_case_insensitive(self, mock_ctx, mock_agent_api):
        """Test that recipient name matching is case insensitive."""
        participant = factory.chat_participant(id="agent-456", name="Weather Agent")
        mock_agent_api.list_agent_chat_participants.return_value = (
            factory.list_response([participant])
        )
        message = factory.chat_message(id="msg-789")
        mock_agent_api.create_agent_chat_message.return_value = factory.response(
            message
        )

        create_agent_chat_message(
            mock_ctx, chat_id="chat-123", content="Hello!", recipients="WEATHER AGENT"
        )

        mock_agent_api.create_agent_chat_message.assert_called_once()

    def test_returns_error_on_mentions_missing_key(self, mock_ctx, mock_agent_api):
        """Test error when mentions JSON is valid but missing required fields."""
        result = create_agent_chat_message(
            mock_ctx,
            chat_id="chat-123",
            content="Hello!",
            mentions='[{"id": "agent-456"}]',
        )
        assert "Error" in result
        assert "Missing required field in mentions" in result

    def test_returns_error_on_empty_recipients_string(self, mock_ctx, mock_agent_api):
        """Test error when recipients is whitespace/commas only."""
        result = create_agent_chat_message(
            mock_ctx,
            chat_id="chat-123",
            content="Hello!",
            recipients=", ,",
        )
        assert "Error" in result
        assert "recipients cannot be empty" in result

    def test_resolves_participant_by_username(self, mock_ctx, mock_agent_api):
        """Test that participants can be matched by username attribute."""
        participant = SimpleNamespace(id="user-1", name=None, username="jdoe")
        mock_agent_api.list_agent_chat_participants.return_value = MagicMock(
            data=[participant]
        )
        message = factory.chat_message(id="msg-789")
        mock_agent_api.create_agent_chat_message.return_value = factory.response(
            message
        )

        create_agent_chat_message(
            mock_ctx, chat_id="chat-123", content="Hello!", recipients="jdoe"
        )

        mock_agent_api.create_agent_chat_message.assert_called_once()
        call_args = mock_agent_api.create_agent_chat_message.call_args
        mention = call_args.kwargs["message"].mentions[0]
        assert mention.id == "user-1"
        assert mention.name == "jdoe"

    def test_resolves_participant_by_display_name(self, mock_ctx, mock_agent_api):
        """Test that participants can be matched by display_name attribute."""
        participant = SimpleNamespace(
            id="user-2", name=None, display_name="Alice Smith"
        )
        mock_agent_api.list_agent_chat_participants.return_value = MagicMock(
            data=[participant]
        )
        message = factory.chat_message(id="msg-789")
        mock_agent_api.create_agent_chat_message.return_value = factory.response(
            message
        )

        create_agent_chat_message(
            mock_ctx, chat_id="chat-123", content="Hello!", recipients="alice smith"
        )

        mock_agent_api.create_agent_chat_message.assert_called_once()
        call_args = mock_agent_api.create_agent_chat_message.call_args
        mention = call_args.kwargs["message"].mentions[0]
        assert mention.id == "user-2"
        assert mention.name == "Alice Smith"
