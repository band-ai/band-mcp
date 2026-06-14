"""Unit tests for human contacts tools."""

import json
from unittest.mock import MagicMock

from band_mcp.tools.human.human_contacts import (
    approve_contact_request,
    cancel_contact_request,
    create_contact_request,
    list_my_contacts,
    list_received_contact_requests,
    list_sent_contact_requests,
    reject_contact_request,
    remove_my_contact,
    resolve_handle,
)


class TestListMyContacts:
    """Tests for list_my_contacts tool."""

    def test_returns_list_of_contacts(self, mock_ctx, mock_human_api):
        """Test successful retrieval of contact list."""
        mock_human_api.list_my_contacts.return_value = MagicMock(
            data=[
                MagicMock(id="c-1", handle="alice"),
                MagicMock(id="c-2", handle="bob"),
            ],
            model_dump=lambda **kw: {
                "data": [
                    {"id": "c-1", "handle": "alice"},
                    {"id": "c-2", "handle": "bob"},
                ]
            },
        )

        result = list_my_contacts(mock_ctx)

        mock_human_api.list_my_contacts.assert_called_once_with(
            page=None,
            page_size=None,
        )
        parsed = json.loads(result)
        assert len(parsed["data"]) == 2

    def test_pagination_parameters(self, mock_ctx, mock_human_api):
        """Test pagination parameters are passed through."""
        mock_human_api.list_my_contacts.return_value = MagicMock(
            data=[],
            model_dump=lambda **kw: {"data": []},
        )

        list_my_contacts(mock_ctx, page=2, page_size=10)

        mock_human_api.list_my_contacts.assert_called_once_with(
            page=2,
            page_size=10,
        )

    def test_empty_contact_list(self, mock_ctx, mock_human_api):
        """Test handling of empty contact list."""
        mock_human_api.list_my_contacts.return_value = MagicMock(
            data=[],
            model_dump=lambda **kw: {"data": []},
        )

        result = list_my_contacts(mock_ctx)

        parsed = json.loads(result)
        assert parsed["data"] == []


class TestCreateContactRequest:
    """Tests for create_contact_request tool."""

    def test_creates_request_with_handle(self, mock_ctx, mock_human_api):
        """Test creating a contact request with handle only."""
        mock_human_api.create_contact_request.return_value = MagicMock(
            model_dump=lambda **kw: {
                "data": {"id": "req-1", "recipient_handle": "alice"}
            }
        )

        result = create_contact_request(mock_ctx, recipient_handle="alice")

        mock_human_api.create_contact_request.assert_called_once()
        call_args = mock_human_api.create_contact_request.call_args
        assert call_args.kwargs["contact_request"].recipient_handle == "alice"
        assert "message" not in call_args.kwargs["contact_request"].model_fields_set
        parsed = json.loads(result)
        assert parsed["data"]["recipient_handle"] == "alice"

    def test_creates_request_with_message(self, mock_ctx, mock_human_api):
        """Test creating a contact request with message."""
        mock_human_api.create_contact_request.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"id": "req-1"}}
        )

        create_contact_request(
            mock_ctx, recipient_handle="bob", message="Let's connect!"
        )

        call_args = mock_human_api.create_contact_request.call_args
        assert call_args.kwargs["contact_request"].recipient_handle == "bob"
        assert call_args.kwargs["contact_request"].message == "Let's connect!"


class TestListReceivedContactRequests:
    """Tests for list_received_contact_requests tool."""

    def test_returns_received_requests(self, mock_ctx, mock_human_api):
        """Test successful retrieval of received contact requests."""
        mock_human_api.list_received_contact_requests.return_value = MagicMock(
            model_dump=lambda **kw: {"data": [{"id": "req-1", "status": "pending"}]}
        )

        result = list_received_contact_requests(mock_ctx)

        mock_human_api.list_received_contact_requests.assert_called_once_with(
            page=None,
            page_size=None,
        )
        parsed = json.loads(result)
        assert len(parsed["data"]) == 1

    def test_pagination_parameters(self, mock_ctx, mock_human_api):
        """Test pagination parameters are passed through."""
        mock_human_api.list_received_contact_requests.return_value = MagicMock(
            model_dump=lambda **kw: {"data": []}
        )

        list_received_contact_requests(mock_ctx, page=3, page_size=25)

        mock_human_api.list_received_contact_requests.assert_called_once_with(
            page=3,
            page_size=25,
        )


class TestListSentContactRequests:
    """Tests for list_sent_contact_requests tool."""

    def test_returns_sent_requests(self, mock_ctx, mock_human_api):
        """Test successful retrieval of sent contact requests."""
        mock_human_api.list_sent_contact_requests.return_value = MagicMock(
            model_dump=lambda **kw: {"data": [{"id": "req-1", "status": "pending"}]}
        )

        result = list_sent_contact_requests(mock_ctx)

        mock_human_api.list_sent_contact_requests.assert_called_once_with(
            status=None,
            page=None,
            page_size=None,
        )
        parsed = json.loads(result)
        assert len(parsed["data"]) == 1

    def test_filters_by_status(self, mock_ctx, mock_human_api):
        """Test filtering sent requests by status."""
        mock_human_api.list_sent_contact_requests.return_value = MagicMock(
            model_dump=lambda **kw: {"data": []}
        )

        list_sent_contact_requests(mock_ctx, status="approved")

        mock_human_api.list_sent_contact_requests.assert_called_once_with(
            status="approved",
            page=None,
            page_size=None,
        )


class TestApproveContactRequest:
    """Tests for approve_contact_request tool."""

    def test_approves_request(self, mock_ctx, mock_human_api):
        """Test approving a contact request."""
        mock_human_api.approve_contact_request.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"status": "approved"}}
        )

        result = approve_contact_request(mock_ctx, request_id="req-123")

        mock_human_api.approve_contact_request.assert_called_once_with(id="req-123")
        parsed = json.loads(result)
        assert parsed["data"]["status"] == "approved"


class TestRejectContactRequest:
    """Tests for reject_contact_request tool."""

    def test_rejects_request(self, mock_ctx, mock_human_api):
        """Test rejecting a contact request."""
        mock_human_api.reject_contact_request.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"status": "rejected"}}
        )

        result = reject_contact_request(mock_ctx, request_id="req-123")

        mock_human_api.reject_contact_request.assert_called_once_with(id="req-123")
        parsed = json.loads(result)
        assert parsed["data"]["status"] == "rejected"


class TestCancelContactRequest:
    """Tests for cancel_contact_request tool."""

    def test_cancels_request(self, mock_ctx, mock_human_api):
        """Test cancelling a contact request."""
        mock_human_api.cancel_contact_request.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"status": "cancelled"}}
        )

        result = cancel_contact_request(mock_ctx, request_id="req-123")

        mock_human_api.cancel_contact_request.assert_called_once_with(id="req-123")
        parsed = json.loads(result)
        assert parsed["data"]["status"] == "cancelled"


class TestResolveHandle:
    """Tests for resolve_handle tool."""

    def test_resolves_handle(self, mock_ctx, mock_human_api):
        """Test resolving a handle."""
        mock_human_api.resolve_handle.return_value = MagicMock(
            model_dump=lambda **kw: {
                "data": {"handle": "alice", "type": "User", "name": "Alice"}
            }
        )

        result = resolve_handle(mock_ctx, handle="alice")

        mock_human_api.resolve_handle.assert_called_once_with(handle="alice")
        parsed = json.loads(result)
        assert parsed["data"]["handle"] == "alice"
        assert parsed["data"]["type"] == "User"


class TestRemoveMyContact:
    """Tests for remove_my_contact tool."""

    def test_removes_by_contact_id(self, mock_ctx, mock_human_api):
        """Test removing a contact by contact_id."""
        mock_human_api.remove_my_contact.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"status": "removed"}}
        )

        result = remove_my_contact(mock_ctx, contact_id="c-123")

        mock_human_api.remove_my_contact.assert_called_once_with(contact_id="c-123")
        parsed = json.loads(result)
        assert parsed["data"]["status"] == "removed"

    def test_removes_by_handle(self, mock_ctx, mock_human_api):
        """Test removing a contact by handle."""
        mock_human_api.remove_my_contact.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"status": "removed"}}
        )

        remove_my_contact(mock_ctx, handle="alice")

        mock_human_api.remove_my_contact.assert_called_once_with(handle="alice")

    def test_requires_contact_id_or_handle(self, mock_ctx):
        """Test validation when neither contact_id nor handle is provided."""
        result = remove_my_contact(mock_ctx)
        assert "Error" in result
        assert "contact_id or handle" in result

    def test_both_contact_id_and_handle_sends_both(self, mock_ctx, mock_human_api):
        """Test that providing both contact_id and handle passes both to the API."""
        mock_human_api.remove_my_contact.return_value = MagicMock(
            model_dump=lambda **kw: {"data": {"status": "removed"}}
        )

        remove_my_contact(mock_ctx, contact_id="c-123", handle="alice")

        mock_human_api.remove_my_contact.assert_called_once_with(
            contact_id="c-123",
            handle="alice",
        )
