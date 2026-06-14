"""Live-API smoke tests for the SDK-driven registrar.

Verify that read-only tools register and dispatch end-to-end against a real
Band API, adapting to whichever scope(s) the ``BAND_API_KEY`` serves. Run with:

    uv run pytest tests/integration/test_smoke.py -v -s --no-cov
"""

from __future__ import annotations

import logging

import pytest

from tests.integration.conftest import LiveHarness, requires_api

logger = logging.getLogger(__name__)


@requires_api
async def test_registrar_advertises_only_scoped_tools(harness: LiveHarness) -> None:
    """Every registered tool is band_-prefixed and matches the served scope."""
    names = await harness.names()
    assert names, "registrar advertised no tools"
    assert all(n.startswith("band_") for n in names), sorted(names)

    if "agent" in harness.scope:
        assert "band_lookup_peers" in names
    if "human" in harness.scope:
        assert "band_list_my_chats" in names
        assert "band_get_my_profile" in names
    logger.info("Registered %d tools for scope %s", len(names), harness.scope)


@requires_api
async def test_human_profile_and_chats_round_trip(harness: LiveHarness) -> None:
    """Human read-only tools return well-formed payloads."""
    if "human" not in harness.scope:
        pytest.skip("human scope not served by this key")

    profile = await harness.call("band_get_my_profile")
    assert isinstance(profile, dict), profile

    chats = await harness.call("band_list_my_chats")
    # Responses are typically {"data": [...]} but tolerate a bare list.
    data = chats.get("data") if isinstance(chats, dict) else chats
    assert isinstance(data, list), chats
    logger.info("Human sees %d chats", len(data))


@requires_api
async def test_agent_lookup_peers_returns_list(harness: LiveHarness) -> None:
    """Agent (room-less) read-only tool dispatches and returns a list."""
    if "agent" not in harness.scope:
        pytest.skip("agent scope not served by this key")

    peers = await harness.call("band_lookup_peers")
    data = peers.get("data") if isinstance(peers, dict) else peers
    assert isinstance(data, list), peers
    logger.info("Agent sees %d peers", len(data))
