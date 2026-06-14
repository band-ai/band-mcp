"""Unit tests for participant tools (list_agent_chat_participants, add_agent_chat_participant, remove_agent_chat_participant)."""

import json

import pytest

from thenvoi_testing.factories import factory
from band_mcp.tools.agent.agent_participants import (
    VALID_ROLES,
    add_agent_chat_participant,
    list_agent_chat_participants,
    remove_agent_chat_participant,
)


class TestListAgentChatParticipants:
    """Tests for list_agent_chat_participants tool."""

    def test_returns_list_of_participants(self, mock_ctx, mock_agent_api):
        """Test successful retrieval of participant list."""
        chat_id = "chat-123"
        participants = [
            factory.chat_participant(name="Agent A", type="Agent", role="owner"),
            factory.chat_participant(name="User B", type="User", role="member"),
        ]
        mock_agent_api.list_agent_chat_participants.return_value = (
            factory.list_response(participants)
        )

        result = list_agent_chat_participants(mock_ctx, chat_id=chat_id)

        mock_agent_api.list_agent_chat_participants.assert_called_once_with(
            chat_id=chat_id
        )
        parsed = json.loads(result)
        assert len(parsed["data"]) == 2

    def test_empty_participant_list(self, mock_ctx, mock_agent_api):
        """Test handling of empty participant list."""
        mock_agent_api.list_agent_chat_participants.return_value = (
            factory.list_response([])
        )

        result = list_agent_chat_participants(mock_ctx, chat_id="empty-chat")

        parsed = json.loads(result)
        assert parsed["data"] == []

    def test_participant_includes_required_fields(self, mock_ctx, mock_agent_api):
        """Test that participant data includes required fields."""
        participant = factory.chat_participant(
            name="Test Agent",
            type="Agent",
            role="admin",
            status="active",
        )
        mock_agent_api.list_agent_chat_participants.return_value = (
            factory.list_response([participant])
        )

        result = list_agent_chat_participants(mock_ctx, chat_id="chat-456")

        parsed = json.loads(result)
        data = parsed["data"][0]
        assert "id" in data
        assert "name" in data
        assert "type" in data
        assert "role" in data
        assert "status" in data


class TestAddAgentChatParticipant:
    """Tests for add_agent_chat_participant tool."""

    def test_adds_participant_without_role(self, mock_ctx, mock_agent_api):
        """Test adding a participant with default role."""
        chat_id = "chat-123"
        participant_id = "agent-456"

        result = add_agent_chat_participant(
            mock_ctx, chat_id=chat_id, participant_id=participant_id
        )

        mock_agent_api.add_agent_chat_participant.assert_called_once()
        call_args = mock_agent_api.add_agent_chat_participant.call_args
        assert call_args.kwargs["chat_id"] == chat_id
        assert call_args.kwargs["participant"].participant_id == participant_id
        assert call_args.kwargs["participant"].role == "member"  # Default role
        assert f"Participant added successfully: {participant_id}" == result

    def test_adds_participant_with_member_role(self, mock_ctx, mock_agent_api):
        """Test adding a participant with member role."""
        chat_id = "chat-123"
        participant_id = "agent-456"

        add_agent_chat_participant(
            mock_ctx, chat_id=chat_id, participant_id=participant_id, role="member"
        )

        call_args = mock_agent_api.add_agent_chat_participant.call_args
        assert call_args.kwargs["participant"].role == "member"

    def test_adds_participant_with_admin_role(self, mock_ctx, mock_agent_api):
        """Test adding a participant with admin role."""
        chat_id = "chat-123"
        participant_id = "agent-456"

        add_agent_chat_participant(
            mock_ctx, chat_id=chat_id, participant_id=participant_id, role="admin"
        )

        call_args = mock_agent_api.add_agent_chat_participant.call_args
        assert call_args.kwargs["participant"].role == "admin"

    def test_adds_participant_with_owner_role(self, mock_ctx, mock_agent_api):
        """Test adding a participant with owner role."""
        chat_id = "chat-123"
        participant_id = "agent-456"

        add_agent_chat_participant(
            mock_ctx, chat_id=chat_id, participant_id=participant_id, role="owner"
        )

        call_args = mock_agent_api.add_agent_chat_participant.call_args
        assert call_args.kwargs["participant"].role == "owner"

    def test_role_is_case_insensitive(self, mock_ctx, mock_agent_api):
        """Test that role parameter is case insensitive."""
        add_agent_chat_participant(
            mock_ctx, chat_id="chat-123", participant_id="agent-456", role="ADMIN"
        )

        call_args = mock_agent_api.add_agent_chat_participant.call_args
        assert call_args.kwargs["participant"].role == "admin"

    def test_raises_on_invalid_role(self, mock_ctx, mock_agent_api):
        """Test error handling for invalid role."""
        with pytest.raises(ValueError, match="Invalid role: invalid_role"):
            add_agent_chat_participant(
                mock_ctx,
                chat_id="chat-123",
                participant_id="agent-456",
                role="invalid_role",
            )

    def test_valid_roles_constant(self):
        """Test that VALID_ROLES contains expected values."""
        expected = {"owner", "admin", "member"}
        assert VALID_ROLES == expected


class TestRemoveAgentChatParticipant:
    """Tests for remove_agent_chat_participant tool."""

    def test_removes_participant(self, mock_ctx, mock_agent_api):
        """Test successful participant removal."""
        chat_id = "chat-123"
        participant_id = "agent-456"

        result = remove_agent_chat_participant(
            mock_ctx, chat_id=chat_id, participant_id=participant_id
        )

        mock_agent_api.remove_agent_chat_participant.assert_called_once_with(
            chat_id=chat_id,
            id=participant_id,
        )
        assert f"Participant removed successfully: {participant_id}" == result
