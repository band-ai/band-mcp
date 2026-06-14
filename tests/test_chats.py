"""Unit tests for chat tools (list_agent_chats, get_agent_chat, create_agent_chat)."""

import json

from thenvoi_testing.factories import factory
from band_mcp.tools.agent.agent_chats import (
    create_agent_chat,
    get_agent_chat,
    list_agent_chats,
)


class TestListAgentChats:
    """Tests for list_agent_chats tool."""

    def test_returns_list_of_chats(self, mock_ctx, mock_agent_api):
        """Test successful retrieval of chat list."""
        chats = [
            factory.chat_room(title="Project Alpha"),
            factory.chat_room(title="Support Chat"),
        ]
        mock_agent_api.list_agent_chats.return_value = factory.list_response(chats)

        result = list_agent_chats(mock_ctx)

        mock_agent_api.list_agent_chats.assert_called_once_with(
            page=None,
            page_size=None,
        )
        parsed = json.loads(result)
        assert len(parsed["data"]) == 2

    def test_pagination_parameters(self, mock_ctx, mock_agent_api):
        """Test pagination parameters are passed through."""
        mock_agent_api.list_agent_chats.return_value = factory.list_response([])

        list_agent_chats(mock_ctx, page=3, page_size=25)

        mock_agent_api.list_agent_chats.assert_called_once_with(
            page=3,
            page_size=25,
        )

    def test_empty_chat_list(self, mock_ctx, mock_agent_api):
        """Test handling of empty chat list."""
        mock_agent_api.list_agent_chats.return_value = factory.list_response([])

        result = list_agent_chats(mock_ctx)

        parsed = json.loads(result)
        assert parsed["data"] == []


class TestGetAgentChat:
    """Tests for get_agent_chat tool."""

    def test_returns_chat_details(self, mock_ctx, mock_agent_api):
        """Test successful retrieval of chat details."""
        chat_id = "chat-456"
        chat = factory.chat_room(id=chat_id, title="Team Discussion")
        mock_agent_api.get_agent_chat.return_value = factory.response(chat)

        result = get_agent_chat(mock_ctx, chat_id=chat_id)

        mock_agent_api.get_agent_chat.assert_called_once_with(id=chat_id)
        parsed = json.loads(result)
        assert parsed["data"]["id"] == chat_id
        assert parsed["data"]["title"] == "Team Discussion"

    def test_includes_timestamps(self, mock_ctx, mock_agent_api):
        """Test that response includes timestamps."""
        chat = factory.chat_room()
        mock_agent_api.get_agent_chat.return_value = factory.response(chat)

        result = get_agent_chat(mock_ctx, chat_id="any-id")

        parsed = json.loads(result)
        assert "inserted_at" in parsed["data"]
        assert "updated_at" in parsed["data"]


class TestCreateAgentChat:
    """Tests for create_agent_chat tool."""

    def test_creates_chat_without_task(self, mock_ctx, mock_agent_api):
        """Test creating a chat room without associated task."""
        chat_id = "new-chat-123"
        chat = factory.chat_room(id=chat_id)
        mock_agent_api.create_agent_chat.return_value = factory.response(chat)

        result = create_agent_chat(mock_ctx)

        mock_agent_api.create_agent_chat.assert_called_once()
        call_args = mock_agent_api.create_agent_chat.call_args
        assert call_args.kwargs["chat"].task_id is None
        parsed = json.loads(result)
        assert parsed["data"]["id"] == chat_id

    def test_creates_chat_with_task_id(self, mock_ctx, mock_agent_api):
        """Test creating a chat room with associated task."""
        chat_id = "new-chat-456"
        task_id = "task-789"
        chat = factory.chat_room(id=chat_id, task_id=task_id)
        mock_agent_api.create_agent_chat.return_value = factory.response(chat)

        result = create_agent_chat(mock_ctx, task_id=task_id)

        mock_agent_api.create_agent_chat.assert_called_once()
        call_args = mock_agent_api.create_agent_chat.call_args
        assert call_args.kwargs["chat"].task_id == task_id
        parsed = json.loads(result)
        assert parsed["data"]["id"] == chat_id
        assert parsed["data"]["task_id"] == task_id
