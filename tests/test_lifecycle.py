"""Unit tests for lifecycle tools (mark_agent_message_processing, mark_agent_message_processed, mark_agent_message_failed)."""

import json


from thenvoi_testing.factories import factory
from band_mcp.tools.agent.agent_lifecycle import (
    mark_agent_message_failed,
    mark_agent_message_processed,
    mark_agent_message_processing,
)


class TestMarkAgentMessageProcessing:
    """Tests for mark_agent_message_processing tool."""

    def test_marks_message_processing(self, mock_ctx, mock_agent_api):
        """Test marking a message as processing."""
        chat_id = "chat-123"
        message_id = "msg-456"
        mock_agent_api.mark_agent_message_processing.return_value = factory.response(
            {"status": "processing", "attempt_number": 1}
        )

        result = mark_agent_message_processing(
            mock_ctx, chat_id=chat_id, message_id=message_id
        )

        mock_agent_api.mark_agent_message_processing.assert_called_once_with(
            chat_id=chat_id,
            id=message_id,
        )
        parsed = json.loads(result)
        assert parsed["data"]["status"] == "processing"

    def test_returns_serialized_response(self, mock_ctx, mock_agent_api):
        """Test that response is properly serialized."""
        mock_agent_api.mark_agent_message_processing.return_value = factory.response(
            {"attempt_number": 1, "started_at": "2024-01-01T00:00:00Z"}
        )

        result = mark_agent_message_processing(
            mock_ctx, chat_id="chat-123", message_id="msg-456"
        )

        parsed = json.loads(result)
        assert "attempt_number" in parsed["data"]
        assert "started_at" in parsed["data"]


class TestMarkAgentMessageProcessed:
    """Tests for mark_agent_message_processed tool."""

    def test_marks_message_processed(self, mock_ctx, mock_agent_api):
        """Test marking a message as processed."""
        chat_id = "chat-123"
        message_id = "msg-456"
        mock_agent_api.mark_agent_message_processed.return_value = factory.response(
            {"status": "processed", "completed_at": "2024-01-01T00:01:00Z"}
        )

        result = mark_agent_message_processed(
            mock_ctx, chat_id=chat_id, message_id=message_id
        )

        mock_agent_api.mark_agent_message_processed.assert_called_once_with(
            chat_id=chat_id,
            id=message_id,
        )
        parsed = json.loads(result)
        assert parsed["data"]["status"] == "processed"

    def test_returns_serialized_response(self, mock_ctx, mock_agent_api):
        """Test that response is properly serialized."""
        mock_agent_api.mark_agent_message_processed.return_value = factory.response(
            {"status": "success", "processed_at": "2024-01-01T00:01:00Z"}
        )

        result = mark_agent_message_processed(
            mock_ctx, chat_id="chat-123", message_id="msg-456"
        )

        parsed = json.loads(result)
        assert "status" in parsed["data"]


class TestMarkAgentMessageFailed:
    """Tests for mark_agent_message_failed tool."""

    def test_marks_message_failed(self, mock_ctx, mock_agent_api):
        """Test marking a message as failed."""
        chat_id = "chat-123"
        message_id = "msg-456"
        error_message = "Processing timeout exceeded"
        mock_agent_api.mark_agent_message_failed.return_value = factory.response(
            {"status": "failed", "error": error_message}
        )

        result = mark_agent_message_failed(
            mock_ctx, chat_id=chat_id, message_id=message_id, error=error_message
        )

        mock_agent_api.mark_agent_message_failed.assert_called_once_with(
            chat_id=chat_id,
            id=message_id,
            error=error_message,
        )
        parsed = json.loads(result)
        assert parsed["data"]["status"] == "failed"

    def test_passes_error_message_to_api(self, mock_ctx, mock_agent_api):
        """Test that error message is correctly passed to API."""
        error_message = "Tool execution failed: API unavailable"
        mock_agent_api.mark_agent_message_failed.return_value = factory.response(
            {"error": error_message}
        )

        mark_agent_message_failed(
            mock_ctx, chat_id="chat-123", message_id="msg-456", error=error_message
        )

        call_args = mock_agent_api.mark_agent_message_failed.call_args
        assert call_args.kwargs["error"] == error_message

    def test_returns_serialized_response(self, mock_ctx, mock_agent_api):
        """Test that response is properly serialized."""
        mock_agent_api.mark_agent_message_failed.return_value = factory.response(
            {"status": "failed", "attempt_number": 3, "error": "Max retries exceeded"}
        )

        result = mark_agent_message_failed(
            mock_ctx,
            chat_id="chat-123",
            message_id="msg-456",
            error="Max retries exceeded",
        )

        parsed = json.loads(result)
        assert "status" in parsed["data"]
        assert "error" in parsed["data"]
