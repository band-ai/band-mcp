import logging
from typing import Literal, Optional

from band_mcp.shared import AppContextType, get_app_context, mcp, serialize_response

logger = logging.getLogger(__name__)


@mcp.tool()
def list_agent_contacts(
    ctx: AppContextType,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> str:
    """List the agent's contacts.

    Returns contacts that have been approved (mutual connections).
    Each contact includes handle, name, type, and description.

    Args:
        page: Page number for pagination (optional).
        page_size: Number of items per page (optional).

    Returns:
        JSON string containing the list of contacts.
    """
    logger.debug("Fetching agent contacts")
    client = get_app_context(ctx).client
    result = client.agent_api_contacts.list_agent_contacts(
        page=page,
        page_size=page_size,
    )
    contact_count = len(result.data) if result.data else 0
    logger.info("Retrieved %s contacts", contact_count)
    return serialize_response(result)


@mcp.tool()
def add_agent_contact(
    ctx: AppContextType,
    handle: str,
    message: Optional[str] = None,
) -> str:
    """Send a contact request to another entity by handle.

    Initiates a contact request. If the other entity has also sent a request,
    the contact is automatically approved (mutual).

    Args:
        handle: The handle of the entity to add as a contact (required).
        message: Optional message to include with the request.

    Returns:
        JSON string containing the contact request status.
    """
    logger.debug("Adding agent contact: %s", handle)
    client = get_app_context(ctx).client
    kwargs: dict = {"handle": handle}
    if message is not None:
        kwargs["message"] = message
    result = client.agent_api_contacts.add_agent_contact(**kwargs)
    logger.info("Contact request sent to: %s", handle)
    return serialize_response(result)


@mcp.tool()
def remove_agent_contact(
    ctx: AppContextType,
    contact_id: Optional[str] = None,
    handle: Optional[str] = None,
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
    logger.debug("Removing agent contact: %s", identifier)
    client = get_app_context(ctx).client
    kwargs: dict = {}
    if contact_id is not None:
        kwargs["contact_id"] = contact_id
    if handle is not None:
        kwargs["handle"] = handle
    result = client.agent_api_contacts.remove_agent_contact(**kwargs)
    logger.info("Contact removed: %s", identifier)
    return serialize_response(result)


@mcp.tool()
def list_agent_contact_requests(
    ctx: AppContextType,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    sent_status: Optional[
        Literal["pending", "approved", "rejected", "cancelled", "all"]
    ] = None,
) -> str:
    """List the agent's contact requests (both sent and received).

    Returns both received (pending) and sent contact requests.
    Use sent_status to filter sent requests by status.

    Args:
        page: Page number for pagination (optional).
        page_size: Number of items per page (optional).
        sent_status: Filter sent requests by status: 'pending', 'approved',
                    'rejected', 'cancelled', or 'all' (optional).

    Returns:
        JSON string containing received and sent contact requests.
    """
    logger.debug("Fetching agent contact requests")
    client = get_app_context(ctx).client
    result = client.agent_api_contacts.list_agent_contact_requests(
        page=page,
        page_size=page_size,
        sent_status=sent_status,
    )
    logger.info("Retrieved contact requests")
    return serialize_response(result)


@mcp.tool()
def respond_to_agent_contact_request(
    ctx: AppContextType,
    action: Literal["approve", "reject", "cancel"],
    handle: Optional[str] = None,
    request_id: Optional[str] = None,
) -> str:
    """Respond to a contact request (approve, reject, or cancel).

    - approve: Accept a received contact request
    - reject: Decline a received contact request
    - cancel: Cancel a sent contact request

    Identify the request by either handle or request_id. At least one must be provided.

    Args:
        action: The response action: 'approve', 'reject', or 'cancel' (required).
        handle: The handle of the requester/recipient (optional, provide this or request_id).
        request_id: The contact request ID (optional, provide this or handle).

    Returns:
        JSON string confirming the action.
    """
    if not handle and not request_id:
        return "Error: Either handle or request_id must be provided"

    identifier = handle or request_id
    logger.debug("Responding to contact request %s with action: %s", identifier, action)
    client = get_app_context(ctx).client
    kwargs: dict = {"action": action}
    if handle is not None:
        kwargs["handle"] = handle
    if request_id is not None:
        kwargs["request_id"] = request_id
    result = client.agent_api_contacts.respond_to_agent_contact_request(**kwargs)
    logger.info("Contact request %s: %s", action, identifier)
    return serialize_response(result)
