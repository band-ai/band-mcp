"""Integration tests to verify API operations against a real server.

These tests run against a real API server using credentials from .env.test.
They verify the MCP tools work correctly end-to-end.

Run with:
    uv run pytest tests/integration/test_smoke.py -v --no-cov
"""

import json
import logging

from tests.integration.conftest import get_test_agent_id, requires_api
from band_mcp.tools.agent.agent_chats import list_agent_chats
from band_mcp.tools.agent.agent_identity import get_agent_me, list_agent_peers

logger = logging.getLogger(__name__)


@requires_api
class TestAgentIdentity:
    """Tests for agent identity tools."""

    def test_get_agent_me_returns_correct_agent(self, integration_ctx):
        """Test that get_agent_me returns the correct agent profile."""
        result = get_agent_me(integration_ctx)

        parsed = json.loads(result)
        assert "data" in parsed
        assert parsed["data"] is not None

        # Verify required fields
        agent = parsed["data"]
        assert "id" in agent
        assert "name" in agent

        # Verify this is the expected test agent
        expected_agent_id = get_test_agent_id()
        if expected_agent_id:
            assert agent["id"] == expected_agent_id, (
                f"Expected agent ID {expected_agent_id}, got {agent['id']}"
            )

        logger.info("Agent: %s (ID: %s)", agent["name"], agent["id"])

    def test_list_agent_peers_returns_list(self, integration_ctx):
        """Test that list_agent_peers returns a list of available peers."""
        result = list_agent_peers(integration_ctx)

        parsed = json.loads(result)
        assert "data" in parsed
        assert isinstance(parsed["data"], list)

        # Verify peer structure if any exist
        if parsed["data"]:
            peer = parsed["data"][0]
            assert "id" in peer
            assert "name" in peer
            assert "type" in peer  # "Agent" or "User"

        logger.info("Found %d peers", len(parsed["data"]))


@requires_api
class TestAgentChats:
    """Tests for agent chat tools."""

    def test_list_agent_chats_returns_list(self, integration_ctx):
        """Test that list_agent_chats returns a list of chats."""
        result = list_agent_chats(integration_ctx)

        parsed = json.loads(result)
        assert "data" in parsed
        assert isinstance(parsed["data"], list)

        # Verify chat structure if any exist
        if parsed["data"]:
            chat = parsed["data"][0]
            assert "id" in chat
            assert "title" in chat or chat.get("title") is None  # title can be null

        logger.info("Found %d chats", len(parsed["data"]))
