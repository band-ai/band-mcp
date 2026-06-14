"""Unit tests for human chat tools (list_my_chats, get_my_chat, create_my_chat)."""

import json
from unittest.mock import MagicMock

from band_mcp.tools.human.human_chats import (
    create_my_chat,
    get_my_chat,
    list_my_chats,
)


class TestListMyChats:
    """Tests for list_my_chats tool."""

    def test_returns_list_of_chats(self, mock_ctx, mock_human_api):
        """Test successful retrieval of chat list."""
        mock_human_api.list_my_chats.return_value = MagicMock(
            model_dump=lambda **kw: {
                "data": [
                    {"id": "chat-1", "task_id": None},
                    {"id": "chat-2", "task_id": "task-1"},
                ]
            }
        )

        result = list_my_chats(mock_ctx)

        mock_human_api.list_my_chats.assert_called_once_with(
            page=None,
            page_size=None,
        )
        parsed = json.loads(result)
        assert len(parsed["data"]) == 2

    def test_pagination_parameters(self, mock_ctx, mock_human_api):
        """Test pagination parameters are passed through."""
        mock_human_api.list_my_chats.return_value = MagicMock(
            model_dump=lambda **kw: {"data": []}
        )

        list_my_chats(mock_ctx, page=2, page_size=10)

        mock_human_api.list_my_chats.assert_called_once_with(
            page=2,
            page_size=10,
        )

    def test_empty_chat_list(self, mock_ctx, mock_human_api):
        """Test handling of empty chat list."""
        mock_human_api.list_my_chats.return_value = MagicMock(
            model_dump=lambda **kw: {"data": []}
        )

        result = list_my_chats(mock_ctx)

        parsed = json.loads(result)
        assert parsed["data"] == []


class TestGetMyChat:
    """Tests for get_my_chat tool."""

    def test_returns_chat(self, mock_ctx, mock_human_api):
        """Test successful retrieval of a chat room."""
        mock_human_api.get_my_chat_room.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"id": "chat-123", "task_id": None}}
        )

        result = get_my_chat(mock_ctx, chat_id="chat-123")

        mock_human_api.get_my_chat_room.assert_called_once_with(id="chat-123")
        parsed = json.loads(result)
        assert parsed["data"]["id"] == "chat-123"


class TestCreateMyChat:
    """Tests for create_my_chat tool."""

    def test_creates_chat_without_task(self, mock_ctx, mock_human_api):
        """Test creating a chat room without a task ID."""
        mock_human_api.create_my_chat_room.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"id": "chat-new"}}
        )

        result = create_my_chat(mock_ctx)

        mock_human_api.create_my_chat_room.assert_called_once()
        call_args = mock_human_api.create_my_chat_room.call_args
        assert call_args.kwargs["chat"].task_id is None
        parsed = json.loads(result)
        assert parsed["data"]["id"] == "chat-new"

    def test_creates_chat_with_task(self, mock_ctx, mock_human_api):
        """Test creating a chat room with a task ID."""
        mock_human_api.create_my_chat_room.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"id": "chat-new", "task_id": "task-1"}}
        )

        result = create_my_chat(mock_ctx, task_id="task-1")

        call_args = mock_human_api.create_my_chat_room.call_args
        assert call_args.kwargs["chat"].task_id == "task-1"
        parsed = json.loads(result)
        assert parsed["data"]["task_id"] == "task-1"
