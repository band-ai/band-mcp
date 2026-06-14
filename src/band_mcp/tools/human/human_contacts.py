from __future__ import annotations

import logging
from typing import Literal

from band_rest import CreateContactRequestRequestContactRequest

from band_mcp.shared import AppContextType, get_app_context, mcp, serialize_response

logger = logging.getLogger(__name__)


@mcp.tool()
def list_my_contacts(
    ctx: AppContextType,
    page: int | None = None,
    page_size: int | None = None,
) -> str:
    """List the user's contacts.

    Returns active contacts with their details including handle, email, and type.

    Args:
        page: Page number for pagination (optional).
        page_size: Number of items per page (optional).

    Returns:
        JSON string containing the list of contacts.
    """
    logger.debug("Fetching user contacts")
    client = get_app_context(ctx).client
    result = client.human_api_contacts.list_my_contacts(
        page=page,
        page_size=page_size,
    )
    contact_count = len(result.data) if result.data else 0
    logger.info("Retrieved %s contacts", contact_count)
    return serialize_response(result)


@mcp.tool()
def create_contact_request(
    ctx: AppContextType,
    recipient_handle: str,
    message: str | None = None,
) -> str:
    """Send a contact request to another user.

    Args:
        recipient_handle: Handle of the user to add (with or without @ prefix, required).
        message: Optional message to include with the request (max 500 chars).

    Returns:
        JSON string containing the created contact request details.
    """
    logger.debug("Creating contact request to: %s", recipient_handle)
    client = get_app_context(ctx).client
    kwargs: dict = {"recipient_handle": recipient_handle}
    if message is not None:
        kwargs["message"] = message
    contact_request = CreateContactRequestRequestContactRequest(**kwargs)
    result = client.human_api_contacts.create_contact_request(
        contact_request=contact_request,
    )
    logger.info("Contact request sent to: %s", recipient_handle)
    return serialize_response(result)


@mcp.tool()
def list_received_contact_requests(
    ctx: AppContextType,
    page: int | None = None,
    page_size: int | None = None,
) -> str:
    """List contact requests received by the user.

    Returns pending contact requests that need approval or rejection.

    Args:
        page: Page number for pagination (optional).
        page_size: Number of items per page (optional).

    Returns:
        JSON string containing the list of received contact requests.
    """
    logger.debug("Fetching received contact requests")
    client = get_app_context(ctx).client
    result = client.human_api_contacts.list_received_contact_requests(
        page=page,
        page_size=page_size,
    )
    logger.info("Retrieved received contact requests")
    return serialize_response(result)


@mcp.tool()
def list_sent_contact_requests(
    ctx: AppContextType,
    status: Literal["pending", "approved", "rejected", "cancelled", "all"]
    | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> str:
    """List contact requests sent by the user.

    Args:
        status: Filter by status: 'pending', 'approved', 'rejected',
                'cancelled', or 'all' (optional).
        page: Page number for pagination (optional).
        page_size: Number of items per page (optional).

    Returns:
        JSON string containing the list of sent contact requests.
    """
    logger.debug("Fetching sent contact requests")
    client = get_app_context(ctx).client
    result = client.human_api_contacts.list_sent_contact_requests(
        status=status,
        page=page,
        page_size=page_size,
    )
    logger.info("Retrieved sent contact requests")
    return serialize_response(result)


@mcp.tool()
def approve_contact_request(
    ctx: AppContextType,
    request_id: str,
) -> str:
    """Approve a received contact request.

    Args:
        request_id: The contact request ID to approve (required).

    Returns:
        JSON string confirming the approval.
    """
    logger.debug("Approving contact request: %s", request_id)
    client = get_app_context(ctx).client
    result = client.human_api_contacts.approve_contact_request(id=request_id)
    logger.info("Contact request approved: %s", request_id)
    return serialize_response(result)


@mcp.tool()
def reject_contact_request(
    ctx: AppContextType,
    request_id: str,
) -> str:
    """Reject a received contact request.

    Args:
        request_id: The contact request ID to reject (required).

    Returns:
        JSON string confirming the rejection.
    """
    logger.debug("Rejecting contact request: %s", request_id)
    client = get_app_context(ctx).client
    result = client.human_api_contacts.reject_contact_request(id=request_id)
    logger.info("Contact request rejected: %s", request_id)
    return serialize_response(result)


@mcp.tool()
def cancel_contact_request(
    ctx: AppContextType,
    request_id: str,
) -> str:
    """Cancel a sent contact request.

    Args:
        request_id: The contact request ID to cancel (required).

    Returns:
        JSON string confirming the cancellation.
    """
    logger.debug("Cancelling contact request: %s", request_id)
    client = get_app_context(ctx).client
    result = client.human_api_contacts.cancel_contact_request(id=request_id)
    logger.info("Contact request cancelled: %s", request_id)
    return serialize_response(result)


@mcp.tool()
def resolve_handle(
    ctx: AppContextType,
    handle: str,
) -> str:
    """Look up an entity by handle.

    Resolves a handle to its entity details. Use this to verify a handle
    exists before sending a contact request.

    Args:
        handle: The handle to resolve (required).

    Returns:
        JSON string containing the resolved entity details.
    """
    logger.debug("Resolving handle: %s", handle)
    client = get_app_context(ctx).client
    result = client.human_api_contacts.resolve_handle(handle=handle)
    logger.info("Handle resolved: %s", handle)
    return serialize_response(result)


@mcp.tool()
def remove_my_contact(
    ctx: AppContextType,
    contact_id: str | None = None,
    handle: str | None = None,
) -> str:
    """Remove an existing contact.

    Removes a contact by either contact_id or handle. At least one must be provided.
    If both are provided, both are sent to the API (contact_id takes precedence).

    Args:
        contact_id: The contact record ID (optional, provide this or handle).
        handle: The contact's handle (optional, provide this or contact_id).

    Returns:
        JSON string confirming removal.
    """
    if not contact_id and not handle:
        return "Error: Either contact_id or handle must be provided"

    identifier = contact_id or handle
    logger.debug("Removing contact: %s", identifier)
    client = get_app_context(ctx).client
    kwargs: dict = {}
    if contact_id is not None:
        kwargs["contact_id"] = contact_id
    if handle is not None:
        kwargs["handle"] = handle
    result = client.human_api_contacts.remove_my_contact(**kwargs)
    logger.info("Contact removed: %s", identifier)
    return serialize_response(result)
