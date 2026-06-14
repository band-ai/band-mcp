"""Unit tests for human profile tools (get_my_profile, update_my_profile, list_my_peers)."""

import json
from unittest.mock import MagicMock

from band_mcp.tools.human.human_profile import (
    get_my_profile,
    list_my_peers,
    update_my_profile,
)


class TestGetMyProfile:
    """Tests for get_my_profile tool."""

    def test_returns_profile(self, mock_ctx, mock_human_api):
        """Test successful retrieval of user profile."""
        mock_human_api.get_my_profile.return_value = MagicMock(
            model_dump=lambda **kw: {
                "data": {
                    "first_name": "Alice",
                    "last_name": "Smith",
                    "email": "a@b.com",
                }
            }
        )

        result = get_my_profile(mock_ctx)

        mock_human_api.get_my_profile.assert_called_once()
        parsed = json.loads(result)
        assert parsed["data"]["first_name"] == "Alice"


class TestUpdateMyProfile:
    """Tests for update_my_profile tool."""

    def test_updates_first_name(self, mock_ctx, mock_human_api):
        """Test updating first name only."""
        mock_human_api.update_my_profile.return_value = MagicMock(
            model_dump=lambda **kw: {
                "data": {"first_name": "Bob", "last_name": "Smith"}
            }
        )

        result = update_my_profile(mock_ctx, first_name="Bob")

        mock_human_api.update_my_profile.assert_called_once()
        call_args = mock_human_api.update_my_profile.call_args
        assert call_args.kwargs["user"] == {"first_name": "Bob"}
        parsed = json.loads(result)
        assert parsed["data"]["first_name"] == "Bob"

    def test_updates_last_name(self, mock_ctx, mock_human_api):
        """Test updating last name only."""
        mock_human_api.update_my_profile.return_value = MagicMock(
            model_dump=lambda **kw: {
                "data": {"first_name": "Alice", "last_name": "Jones"}
            }
        )

        update_my_profile(mock_ctx, last_name="Jones")

        call_args = mock_human_api.update_my_profile.call_args
        assert call_args.kwargs["user"] == {"last_name": "Jones"}

    def test_updates_both_names(self, mock_ctx, mock_human_api):
        """Test updating both first and last name."""
        mock_human_api.update_my_profile.return_value = MagicMock(
            model_dump=lambda **kw: {
                "data": {"first_name": "Bob", "last_name": "Jones"}
            }
        )

        update_my_profile(mock_ctx, first_name="Bob", last_name="Jones")

        call_args = mock_human_api.update_my_profile.call_args
        assert call_args.kwargs["user"] == {"first_name": "Bob", "last_name": "Jones"}

    def test_returns_error_when_no_fields_provided(self, mock_ctx):
        """Test error when neither first_name nor last_name is provided."""
        result = update_my_profile(mock_ctx)
        assert "Error" in result
        assert "At least one field" in result


class TestListMyPeers:
    """Tests for list_my_peers tool."""

    def test_returns_peers(self, mock_ctx, mock_human_api):
        """Test successful retrieval of peers."""
        mock_human_api.list_my_peers.return_value = MagicMock(
            model_dump=lambda **kw: {
                "data": [
                    {"id": "p-1", "name": "Alice", "type": "User"},
                    {"id": "p-2", "name": "Bot", "type": "Agent"},
                ]
            }
        )

        result = list_my_peers(mock_ctx)

        mock_human_api.list_my_peers.assert_called_once_with(
            not_in_chat=None,
            type=None,
            page=None,
            page_size=None,
        )
        parsed = json.loads(result)
        assert len(parsed["data"]) == 2

    def test_not_in_chat_filter(self, mock_ctx, mock_human_api):
        """Test filtering peers not in a specific chat."""
        mock_human_api.list_my_peers.return_value = MagicMock(
            model_dump=lambda **kw: {"data": []}
        )

        list_my_peers(mock_ctx, not_in_chat="chat-123")

        mock_human_api.list_my_peers.assert_called_once_with(
            not_in_chat="chat-123",
            type=None,
            page=None,
            page_size=None,
        )

    def test_peer_type_filter(self, mock_ctx, mock_human_api):
        """Test filtering peers by type."""
        mock_human_api.list_my_peers.return_value = MagicMock(
            model_dump=lambda **kw: {"data": []}
        )

        list_my_peers(mock_ctx, peer_type="Agent")

        mock_human_api.list_my_peers.assert_called_once_with(
            not_in_chat=None,
            type="Agent",
            page=None,
            page_size=None,
        )

    def test_pagination_parameters(self, mock_ctx, mock_human_api):
        """Test pagination parameters are passed through."""
        mock_human_api.list_my_peers.return_value = MagicMock(
            model_dump=lambda **kw: {"data": []}
        )

        list_my_peers(mock_ctx, page=3, page_size=25)

        mock_human_api.list_my_peers.assert_called_once_with(
            not_in_chat=None,
            type=None,
            page=3,
            page_size=25,
        )
