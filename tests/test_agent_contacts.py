"""Unit tests for agent contacts tools."""

import json
from unittest.mock import MagicMock

from band_mcp.tools.agent.agent_contacts import (
    add_agent_contact,
    list_agent_contact_requests,
    list_agent_contacts,
    remove_agent_contact,
    respond_to_agent_contact_request,
)


class TestListAgentContacts:
    """Tests for list_agent_contacts tool."""

    def test_returns_list_of_contacts(self, mock_ctx, mock_agent_api):
        """Test successful retrieval of contact list."""
        mock_agent_api.list_agent_contacts.return_value = MagicMock(
            data=[
                MagicMock(id="c-1", handle="alice", name="Alice"),
                MagicMock(id="c-2", handle="bob", name="Bob"),
            ],
            model_dump=lambda **kw: {
                "data": [
                    {"id": "c-1", "handle": "alice", "name": "Alice"},
                    {"id": "c-2", "handle": "bob", "name": "Bob"},
                ]
            },
        )

        result = list_agent_contacts(mock_ctx)

        mock_agent_api.list_agent_contacts.assert_called_once_with(
            page=None,
            page_size=None,
        )
        parsed = json.loads(result)
        assert len(parsed["data"]) == 2
        assert parsed["data"][0]["handle"] == "alice"

    def test_pagination_parameters(self, mock_ctx, mock_agent_api):
        """Test pagination parameters are passed through."""
        mock_agent_api.list_agent_contacts.return_value = MagicMock(
            data=[],
            model_dump=lambda **kw: {"data": []},
        )

        list_agent_contacts(mock_ctx, page=2, page_size=10)

        mock_agent_api.list_agent_contacts.assert_called_once_with(
            page=2,
            page_size=10,
        )

    def test_empty_contact_list(self, mock_ctx, mock_agent_api):
        """Test handling of empty contact list."""
        mock_agent_api.list_agent_contacts.return_value = MagicMock(
            data=[],
            model_dump=lambda **kw: {"data": []},
        )

        result = list_agent_contacts(mock_ctx)

        parsed = json.loads(result)
        assert parsed["data"] == []


class TestAddAgentContact:
    """Tests for add_agent_contact tool."""

    def test_adds_contact_by_handle(self, mock_ctx, mock_agent_api):
        """Test sending a contact request with handle only."""
        mock_agent_api.add_agent_contact.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"id": "req-1", "status": "pending"}}
        )

        result = add_agent_contact(mock_ctx, handle="alice")

        mock_agent_api.add_agent_contact.assert_called_once_with(handle="alice")
        parsed = json.loads(result)
        assert parsed["data"]["status"] == "pending"

    def test_adds_contact_with_message(self, mock_ctx, mock_agent_api):
        """Test sending a contact request with message."""
        mock_agent_api.add_agent_contact.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"id": "req-1", "status": "pending"}}
        )

        add_agent_contact(mock_ctx, handle="bob", message="Hi!")

        mock_agent_api.add_agent_contact.assert_called_once_with(
            handle="bob", message="Hi!"
        )


class TestRemoveAgentContact:
    """Tests for remove_agent_contact tool."""

    def test_removes_by_contact_id(self, mock_ctx, mock_agent_api):
        """Test removing a contact by contact_id."""
        mock_agent_api.remove_agent_contact.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"status": "removed"}}
        )

        result = remove_agent_contact(mock_ctx, contact_id="c-123")

        mock_agent_api.remove_agent_contact.assert_called_once_with(contact_id="c-123")
        parsed = json.loads(result)
        assert parsed["data"]["status"] == "removed"

    def test_removes_by_handle(self, mock_ctx, mock_agent_api):
        """Test removing a contact by handle."""
        mock_agent_api.remove_agent_contact.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"status": "removed"}}
        )

        remove_agent_contact(mock_ctx, handle="alice")

        mock_agent_api.remove_agent_contact.assert_called_once_with(handle="alice")

    def test_requires_contact_id_or_handle(self, mock_ctx):
        """Test validation when neither contact_id nor handle is provided."""
        result = remove_agent_contact(mock_ctx)
        assert "Error" in result
        assert "contact_id or handle" in result

    def test_both_contact_id_and_handle_sends_both(self, mock_ctx, mock_agent_api):
        """Test that providing both contact_id and handle passes both to the API."""
        mock_agent_api.remove_agent_contact.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"status": "removed"}}
        )

        remove_agent_contact(mock_ctx, contact_id="c-123", handle="alice")

        mock_agent_api.remove_agent_contact.assert_called_once_with(
            contact_id="c-123",
            handle="alice",
        )


class TestListAgentContactRequests:
    """Tests for list_agent_contact_requests tool."""

    def test_returns_requests(self, mock_ctx, mock_agent_api):
        """Test successful retrieval of contact requests."""
        mock_agent_api.list_agent_contact_requests.return_value = MagicMock(
            model_dump=lambda **kw: {
                "data": {
                    "received": [{"id": "r-1", "from_handle": "alice"}],
                    "sent": [{"id": "s-1", "to_handle": "bob"}],
                }
            }
        )

        result = list_agent_contact_requests(mock_ctx)

        mock_agent_api.list_agent_contact_requests.assert_called_once_with(
            page=None,
            page_size=None,
            sent_status=None,
        )
        parsed = json.loads(result)
        assert len(parsed["data"]["received"]) == 1
        assert len(parsed["data"]["sent"]) == 1

    def test_filters_by_sent_status(self, mock_ctx, mock_agent_api):
        """Test filtering sent requests by status."""
        mock_agent_api.list_agent_contact_requests.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"received": [], "sent": []}}
        )

        list_agent_contact_requests(mock_ctx, sent_status="pending")

        mock_agent_api.list_agent_contact_requests.assert_called_once_with(
            page=None,
            page_size=None,
            sent_status="pending",
        )

    def test_pagination_parameters(self, mock_ctx, mock_agent_api):
        """Test pagination parameters are passed through."""
        mock_agent_api.list_agent_contact_requests.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"received": [], "sent": []}}
        )

        list_agent_contact_requests(mock_ctx, page=3, page_size=25)

        mock_agent_api.list_agent_contact_requests.assert_called_once_with(
            page=3,
            page_size=25,
            sent_status=None,
        )


class TestRespondToAgentContactRequest:
    """Tests for respond_to_agent_contact_request tool."""

    def test_approve_by_handle(self, mock_ctx, mock_agent_api):
        """Test approving a contact request by handle."""
        mock_agent_api.respond_to_agent_contact_request.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"status": "approved"}}
        )

        result = respond_to_agent_contact_request(
            mock_ctx, action="approve", handle="alice"
        )

        mock_agent_api.respond_to_agent_contact_request.assert_called_once_with(
            action="approve", handle="alice"
        )
        parsed = json.loads(result)
        assert parsed["data"]["status"] == "approved"

    def test_reject_by_request_id(self, mock_ctx, mock_agent_api):
        """Test rejecting a contact request by request_id."""
        mock_agent_api.respond_to_agent_contact_request.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"status": "rejected"}}
        )

        respond_to_agent_contact_request(
            mock_ctx, action="reject", request_id="req-456"
        )

        mock_agent_api.respond_to_agent_contact_request.assert_called_once_with(
            action="reject", request_id="req-456"
        )

    def test_cancel_by_handle(self, mock_ctx, mock_agent_api):
        """Test cancelling a sent contact request."""
        mock_agent_api.respond_to_agent_contact_request.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"status": "cancelled"}}
        )

        respond_to_agent_contact_request(mock_ctx, action="cancel", handle="bob")

        mock_agent_api.respond_to_agent_contact_request.assert_called_once_with(
            action="cancel", handle="bob"
        )

    def test_requires_handle_or_request_id(self, mock_ctx):
        """Test validation when neither handle nor request_id is provided."""
        result = respond_to_agent_contact_request(mock_ctx, action="approve")
        assert "Error" in result
        assert "handle or request_id" in result
