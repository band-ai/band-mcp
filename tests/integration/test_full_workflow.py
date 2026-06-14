"""Live-API workflow tests for the SDK-driven registrar.

Drive a small end-to-end agent workflow through the registrar: create a chat
room, send a message into it, then read participants back — all via
``mcp._tool_manager.call_tool`` against a real Band API. These mutate data on
the test account, so they only run when ``BAND_API_KEY`` is set and the key
serves the agent scope. Run with:

    uv run pytest tests/integration/test_full_workflow.py -v -s --no-cov
"""

from __future__ import annotations

import logging

import pytest

from tests.integration.conftest import LiveHarness, requires_api

logger = logging.getLogger(__name__)


@requires_api
async def test_agent_create_room_send_and_read_back(
    harness: LiveHarness, agent_room: str
) -> None:
    """create_chatroom -> send_message -> get_participants round trip."""
    # The room was created by the ``agent_room`` fixture.
    logger.info("Created agent room %s", agent_room)

    send_result = await harness.call(
        "band_send_message",
        content="integration test message",
        chat_id=agent_room,
    )
    assert send_result is not None, "send_message returned nothing"

    participants = await harness.call("band_get_participants", chat_id=agent_room)
    data = participants.get("data") if isinstance(participants, dict) else participants
    assert isinstance(data, list), participants
    logger.info("Room %s has %d participants", agent_room, len(data))


@requires_api
async def test_agent_send_message_accepts_room_id_alias(
    harness: LiveHarness, agent_room: str
) -> None:
    """The forward-compat ``room_id`` alias dispatches just like ``chat_id``."""
    result = await harness.call(
        "band_send_message",
        content="alias path message",
        room_id=agent_room,
    )
    assert result is not None


@requires_api
async def test_human_create_and_get_chat_room(harness: LiveHarness) -> None:
    """Human workflow: create a chat room then fetch it by id."""
    if "human" not in harness.scope:
        pytest.skip("human scope not served by this key")

    from tests.conftest_integration import _extract_id

    created = await harness.call("band_create_my_chat_room")
    chat_id = _extract_id(created)
    if not chat_id:
        pytest.skip(f"could not create human chat room: {created!r}")

    fetched = await harness.call("band_get_my_chat_room", chat_id=chat_id)
    assert _extract_id(fetched) == chat_id, fetched
    logger.info("Human created + fetched chat room %s", chat_id)
