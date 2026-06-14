"""Unit tests for human participant tools (list_my_chat_participants, add_my_chat_participant, remove_my_chat_participant)."""

import json
from unittest.mock import MagicMock

from band_mcp.tools.human.human_participants import (
    add_my_chat_participant,
    list_my_chat_participants,
    remove_my_chat_participant,
)


class TestListMyChatParticipants:
    """Tests for list_my_chat_participants tool."""

    def test_returns_participants(self, mock_ctx, mock_human_api):
        """Test successful retrieval of participants."""
        mock_human_api.list_my_chat_participants.return_value = MagicMock(
            model_dump=lambda **kw: {
                "data": [
                    {"id": "p-1", "name": "Alice", "type": "User"},
                    {"id": "p-2", "name": "Bot", "type": "Agent"},
                ]
            }
        )

        result = list_my_chat_participants(mock_ctx, chat_id="chat-123")

        mock_human_api.list_my_chat_participants.assert_called_once_with(
            chat_id="chat-123",
            participant_type=None,
        )
        parsed = json.loads(result)
        assert len(parsed["data"]) == 2

    def test_filters_by_type(self, mock_ctx, mock_human_api):
        """Test filtering participants by type."""
        mock_human_api.list_my_chat_participants.return_value = MagicMock(
            model_dump=lambda **kw: {"data": [{"id": "p-1", "type": "Agent"}]}
        )

        list_my_chat_participants(
            mock_ctx, chat_id="chat-123", participant_type="Agent"
        )

        mock_human_api.list_my_chat_participants.assert_called_once_with(
            chat_id="chat-123",
            participant_type="Agent",
        )


class TestAddMyChatParticipant:
    """Tests for add_my_chat_participant tool."""

    def test_adds_participant_default_role(self, mock_ctx, mock_human_api):
        """Test adding a participant with default role."""
        result = add_my_chat_participant(
            mock_ctx, chat_id="chat-123", participant_id="user-456"
        )

        mock_human_api.add_my_chat_participant.assert_called_once()
        call_args = mock_human_api.add_my_chat_participant.call_args
        assert call_args.kwargs["chat_id"] == "chat-123"
        assert call_args.kwargs["participant"].participant_id == "user-456"
        assert call_args.kwargs["participant"].role == "member"
        assert "Added participant: user-456" in result

    def test_adds_participant_with_role(self, mock_ctx, mock_human_api):
        """Test adding a participant with a specific role."""
        add_my_chat_participant(
            mock_ctx, chat_id="chat-123", participant_id="user-456", role="admin"
        )

        call_args = mock_human_api.add_my_chat_participant.call_args
        assert call_args.kwargs["participant"].role == "admin"


class TestRemoveMyChatParticipant:
    """Tests for remove_my_chat_participant tool."""

    def test_removes_participant(self, mock_ctx, mock_human_api):
        """Test removing a participant."""
        result = remove_my_chat_participant(
            mock_ctx, chat_id="chat-123", participant_id="user-456"
        )

        mock_human_api.remove_my_chat_participant.assert_called_once_with(
            chat_id="chat-123",
            id="user-456",
        )
        assert "Removed participant: user-456" in result
