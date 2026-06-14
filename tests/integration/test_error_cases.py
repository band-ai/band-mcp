"""Integration tests for error cases and edge cases.

Tests error handling for:
- Authentication errors (wrong API key)
- Chat access errors (non-existent chat)
- Participant errors (invalid UUID, non-existent participant)
- Participant role variations (add agent, add user as owner)

Run with: uv run pytest tests/integration/test_error_cases.py -v -s --no-cov
"""

import json
import logging
import uuid

import pytest
from band_rest import RestClient
from band_rest.errors import (
    NotFoundError,
    UnauthorizedError,
    UnprocessableEntityError,
)

from tests.integration.conftest import get_base_url, requires_api
from band_mcp.tools.agent.agent_chats import get_agent_chat
from band_mcp.tools.agent.agent_identity import list_agent_peers
from band_mcp.tools.agent.agent_participants import (
    add_agent_chat_participant,
    list_agent_chat_participants,
    remove_agent_chat_participant,
)
from thenvoi_testing.pagination import fetch_all_pages

logger = logging.getLogger(__name__)


def fetch_all_peers(
    ctx, not_in_chat: str | None = None, debug: bool = False
) -> list[dict]:
    """Fetch all peers across all pages with optional debug logging.

    Args:
        ctx: Integration context
        not_in_chat: Optional chat ID to filter peers not in that chat
        debug: Print debug info about pages and peer types
    """
    kwargs = {"not_in_chat": not_in_chat} if not_in_chat else {}
    peers = fetch_all_pages(ctx, list_agent_peers, page_size=100, **kwargs)

    if debug:
        peer_types: dict[str, int] = {}
        for p in peers:
            t = p.get("type", "Unknown")
            peer_types[t] = peer_types.get(t, 0) + 1
        logger.info("  Total: %d peers - %s", len(peers), peer_types)

    return peers


@requires_api
class TestAuthenticationErrors:
    """Tests for authentication error handling."""

    def test_wrong_api_key_raises_unauthorized(self):
        """Connect with invalid API key, expect UnauthorizedError (401)."""
        logger.info("\n" + "=" * 60)
        logger.info("Testing: Wrong API Key → UnauthorizedError")
        logger.info("=" * 60)

        bad_client = RestClient(
            api_key="not-a-real-key",  # noqa: S106
            base_url=get_base_url(),
        )

        with pytest.raises(UnauthorizedError) as exc_info:
            bad_client.agent_api.get_agent_me()

        logger.info("Got expected UnauthorizedError: %s", exc_info.value)
        logger.info("✓ Wrong API key correctly raises UnauthorizedError")


@requires_api
class TestChatAccessErrors:
    """Tests for chat access error handling."""

    def test_get_nonexistent_chat_raises_not_found(self, integration_ctx):
        """Access chat with random UUID, expect NotFoundError (404)."""
        logger.info("\n" + "=" * 60)
        logger.info("Testing: Non-existent Chat → NotFoundError")
        logger.info("=" * 60)

        fake_chat_id = str(uuid.uuid4())
        logger.info("Attempting to access fake chat: %s", fake_chat_id)

        with pytest.raises(NotFoundError) as exc_info:
            get_agent_chat(integration_ctx, chat_id=fake_chat_id)

        logger.info("Got expected NotFoundError: %s", exc_info.value)
        logger.info("✓ Non-existent chat correctly raises NotFoundError")

    def test_list_participants_nonexistent_chat(self, integration_ctx):
        """List participants for non-existent chat, expect NotFoundError."""
        logger.info("\n" + "=" * 60)
        logger.info("Testing: List Participants for Non-existent Chat → NotFoundError")
        logger.info("=" * 60)

        fake_chat_id = str(uuid.uuid4())
        logger.info("Attempting to list participants for fake chat: %s", fake_chat_id)

        with pytest.raises(NotFoundError) as exc_info:
            list_agent_chat_participants(integration_ctx, chat_id=fake_chat_id)

        logger.info("Got expected NotFoundError: %s", exc_info.value)
        logger.info(
            "✓ List participants for non-existent chat correctly raises NotFoundError"
        )

    def test_add_participant_to_nonexistent_chat(self, integration_ctx, test_peer_id):
        """Add participant to non-existent chat, expect NotFoundError."""
        logger.info("\n" + "=" * 60)
        logger.info("Testing: Add Participant to Non-existent Chat → NotFoundError")
        logger.info("=" * 60)

        if not test_peer_id:
            pytest.skip("No peer available for testing")

        fake_chat_id = str(uuid.uuid4())
        logger.info("Attempting to add participant to fake chat: %s", fake_chat_id)

        with pytest.raises(NotFoundError) as exc_info:
            add_agent_chat_participant(
                integration_ctx,
                chat_id=fake_chat_id,
                participant_id=test_peer_id,
                role="member",
            )

        logger.info("Got expected NotFoundError: %s", exc_info.value)
        logger.info(
            "✓ Add participant to non-existent chat correctly raises NotFoundError"
        )


@requires_api
class TestParticipantErrors:
    """Tests for participant error handling."""

    def test_add_nonexistent_participant(self, integration_ctx, test_chat):
        """Add participant with valid UUID that doesn't exist."""
        logger.info("\n" + "=" * 60)
        logger.info("Testing: Add Non-existent Participant")
        logger.info("=" * 60)

        fake_participant_id = str(uuid.uuid4())
        logger.info(
            "Attempting to add non-existent participant: %s", fake_participant_id
        )

        # Expect either NotFoundError or UnprocessableEntityError
        with pytest.raises((NotFoundError, UnprocessableEntityError)) as exc_info:
            add_agent_chat_participant(
                integration_ctx,
                chat_id=test_chat,
                participant_id=fake_participant_id,
                role="member",
            )

        logger.info(
            "Got expected error: %s: %s", type(exc_info.value).__name__, exc_info.value
        )
        logger.info("✓ Adding non-existent participant raises appropriate error")

    def test_add_participant_invalid_uuid_format(self, integration_ctx, test_chat):
        """Add participant with malformed UUID string."""
        logger.info("\n" + "=" * 60)
        logger.info("Testing: Add Participant with Invalid UUID Format")
        logger.info("=" * 60)

        invalid_uuid = "not-a-valid-uuid"
        logger.info("Attempting to add participant with invalid UUID: %s", invalid_uuid)

        # Expect UnprocessableEntityError for validation failure
        with pytest.raises(UnprocessableEntityError) as exc_info:
            add_agent_chat_participant(
                integration_ctx,
                chat_id=test_chat,
                participant_id=invalid_uuid,
                role="member",
            )

        logger.info("Got expected UnprocessableEntityError: %s", exc_info.value)
        logger.info("✓ Invalid UUID format correctly raises UnprocessableEntityError")

    def test_remove_nonexistent_participant(self, integration_ctx, test_chat):
        """Remove participant that's not in the chat."""
        logger.info("\n" + "=" * 60)
        logger.info("Testing: Remove Non-existent Participant")
        logger.info("=" * 60)

        fake_participant_id = str(uuid.uuid4())
        logger.info(
            "Attempting to remove non-existent participant: %s", fake_participant_id
        )

        # Expect NotFoundError or similar
        with pytest.raises((NotFoundError, UnprocessableEntityError)) as exc_info:
            remove_agent_chat_participant(
                integration_ctx, chat_id=test_chat, participant_id=fake_participant_id
            )

        logger.info(
            "Got expected error: %s: %s", type(exc_info.value).__name__, exc_info.value
        )
        logger.info("✓ Removing non-existent participant raises appropriate error")


@requires_api
class TestPeersFiltering:
    """Tests for peers endpoint filtering with notInChat parameter."""

    def test_peers_without_filter_returns_all(self, integration_ctx):
        """Test that peers without filter returns all available peers."""
        logger.info("\n" + "=" * 60)
        logger.info("Testing: List All Peers (no filter)")
        logger.info("=" * 60)

        peers = fetch_all_peers(integration_ctx, debug=True)
        assert len(peers) > 0, "Should have at least one peer"
        logger.info("✓ Found %d total peers", len(peers))

    def test_peers_filter_excludes_chat_participants(self, integration_ctx, test_chat):
        """Test that notInChat filter excludes participants already in the chat."""
        logger.info("\n" + "=" * 60)
        logger.info("Testing: notInChat Filter Excludes Participants")
        logger.info("=" * 60)

        # Step 1: Get all peers (no filter)
        logger.info("\nStep 1: Get all peers without filter:")
        all_peers = fetch_all_peers(integration_ctx, debug=True)
        initial_count = len(all_peers)
        assert initial_count > 0, "Need at least one peer for this test"

        # Step 2: Get peers not in our test chat (should be same as all since chat is empty)
        logger.info("\nStep 2: Get peers not in chat %s:", test_chat)
        peers_not_in_chat = fetch_all_peers(
            integration_ctx, not_in_chat=test_chat, debug=True
        )
        count_before_add = len(peers_not_in_chat)
        logger.info("Peers not in chat (before adding): %d", count_before_add)

        # Step 3: Add a peer to the chat
        peer_to_add = all_peers[0]
        peer_id = peer_to_add["id"]
        peer_name = peer_to_add["name"]
        logger.info("\nStep 3: Adding peer '%s' (ID: %s) to chat", peer_name, peer_id)

        result = add_agent_chat_participant(
            integration_ctx, chat_id=test_chat, participant_id=peer_id, role="member"
        )
        assert "successfully" in result.lower()
        logger.info("Added: %s", result)

        # Step 4: Get peers not in chat again - should be one less
        logger.info("\nStep 4: Get peers not in chat (after adding one):")
        peers_after_add = fetch_all_peers(
            integration_ctx, not_in_chat=test_chat, debug=True
        )
        count_after_add = len(peers_after_add)

        # Verify the added peer is no longer in the filtered list
        peer_ids_after = [p["id"] for p in peers_after_add]
        assert peer_id not in peer_ids_after, (
            f"Added peer {peer_id} should not appear in filtered list"
        )
        assert count_after_add == count_before_add - 1, (
            f"Expected {count_before_add - 1} peers, got {count_after_add}"
        )
        logger.info(
            "✓ Filter correctly excludes added participant (%d → %d)",
            count_before_add,
            count_after_add,
        )

        # Cleanup
        remove_agent_chat_participant(
            integration_ctx, chat_id=test_chat, participant_id=peer_id
        )
        logger.info("\nCleanup: Removed peer from chat")

    def test_agent_can_see_owner_in_peers(self, integration_ctx):
        """Test that an agent can see its owner (User) in the peers list."""
        logger.info("\n" + "=" * 60)
        logger.info("Testing: Agent Can See Owner (User) in Peers")
        logger.info("=" * 60)

        # Get all peers and look for Users
        logger.info("Fetching all peers to find Users:")
        peers = fetch_all_peers(integration_ctx, debug=True)

        # Count by type
        agents = [p for p in peers if p["type"] == "Agent"]
        users = [p for p in peers if p["type"] == "User"]

        logger.info("\nPeer breakdown:")
        logger.info("  - Agents: %d", len(agents))
        logger.info("  - Users: %d", len(users))

        assert len(users) > 0, (
            f"Agent should be able to see at least one User peer (its owner). "
            f"Found {len(agents)} Agents but 0 Users in {len(peers)} total peers."
        )

        logger.info("\nFound %d User peer(s):", len(users))
        for user in users:
            logger.info("  - %s (ID: %s)", user["name"], user["id"])
        logger.info("✓ Agent can see User peers (including owner)")


@requires_api
class TestParticipantRoles:
    """Tests for different participant types and roles."""

    def test_add_agent_as_participant(self, integration_ctx, test_chat):
        """Add another agent to chat as member."""
        logger.info("\n" + "=" * 60)
        logger.info("Testing: Add Agent as Participant")
        logger.info("=" * 60)

        # Find an agent peer not already in the chat
        peers = fetch_all_peers(integration_ctx, not_in_chat=test_chat)
        agent_peer = next((p for p in peers if p["type"] == "Agent"), None)

        if not agent_peer:
            pytest.skip("No agent peer available for testing")

        agent_id = agent_peer["id"]
        agent_name = agent_peer["name"]
        logger.info("Found agent peer: %s (ID: %s)", agent_name, agent_id)

        # Add agent as member
        result = add_agent_chat_participant(
            integration_ctx, chat_id=test_chat, participant_id=agent_id, role="member"
        )
        logger.info("Add result: %s", result)
        assert "successfully" in result.lower()

        # Verify agent was added
        result = list_agent_chat_participants(integration_ctx, chat_id=test_chat)
        parsed = json.loads(result)
        participant_ids = [p["id"] for p in parsed["data"]]
        assert agent_id in participant_ids, "Agent should be in participant list"

        # Find the agent's role
        agent_participant = next(
            (p for p in parsed["data"] if p["id"] == agent_id), None
        )
        logger.info("Agent participant: %s", agent_participant)
        assert agent_participant is not None
        assert agent_participant["type"] == "Agent"

        # Cleanup: remove the agent
        remove_agent_chat_participant(
            integration_ctx, chat_id=test_chat, participant_id=agent_id
        )
        logger.info("✓ Successfully added and removed agent as participant")

    def test_add_user_as_owner(self, integration_ctx, test_chat):
        """Add user peer with owner role."""
        logger.info("\n" + "=" * 60)
        logger.info("Testing: Add User as Owner")
        logger.info("=" * 60)

        # Find a user peer not already in the chat (with debug to see all pages)
        logger.info("Fetching peers not in chat %s:", test_chat)
        peers = fetch_all_peers(integration_ctx, not_in_chat=test_chat, debug=True)
        user_peer = next((p for p in peers if p["type"] == "User"), None)

        if not user_peer:
            pytest.skip("No user peer available for testing")

        user_id = user_peer["id"]
        user_name = user_peer["name"]
        logger.info("Found user peer: %s (ID: %s)", user_name, user_id)

        # Add user as owner
        result = add_agent_chat_participant(
            integration_ctx, chat_id=test_chat, participant_id=user_id, role="owner"
        )
        logger.info("Add result: %s", result)
        assert "successfully" in result.lower()

        # Verify user was added with owner role
        result = list_agent_chat_participants(integration_ctx, chat_id=test_chat)
        parsed = json.loads(result)
        user_participant = next((p for p in parsed["data"] if p["id"] == user_id), None)
        logger.info("User participant: %s", user_participant)
        assert user_participant is not None
        assert user_participant["type"] == "User"
        assert user_participant.get("role") == "owner"

        # Cleanup: remove the user
        remove_agent_chat_participant(
            integration_ctx, chat_id=test_chat, participant_id=user_id
        )
        logger.info("✓ Successfully added user as owner and removed")

    def test_add_participant_then_remove(
        self, integration_ctx, test_chat, test_peer_id
    ):
        """Full add → verify → remove → verify cycle."""
        logger.info("\n" + "=" * 60)
        logger.info("Testing: Add → Verify → Remove → Verify Cycle")
        logger.info("=" * 60)

        if not test_peer_id:
            pytest.skip("No peer available for testing")

        # Get peer info (filter by not in chat)
        peers = fetch_all_peers(integration_ctx, not_in_chat=test_chat)
        peer = next((p for p in peers if p["id"] == test_peer_id), None)
        if peer:
            logger.info(
                "Using peer: %s (%s, ID: %s)", peer["name"], peer["type"], test_peer_id
            )
        else:
            logger.info("Using peer ID: %s", test_peer_id)

        # Step 1: Add participant
        logger.info("\nStep 1: Adding participant...")
        result = add_agent_chat_participant(
            integration_ctx,
            chat_id=test_chat,
            participant_id=test_peer_id,
            role="member",
        )
        logger.info("Add result: %s", result)
        assert "successfully" in result.lower()

        # Step 2: Verify participant is present
        logger.info("\nStep 2: Verifying participant is present...")
        result = list_agent_chat_participants(integration_ctx, chat_id=test_chat)
        parsed = json.loads(result)
        participant_ids = [p["id"] for p in parsed["data"]]
        assert test_peer_id in participant_ids, "Peer should be in participant list"
        logger.info("✓ Participant found in list (total: %d)", len(parsed["data"]))

        # Step 3: Remove participant
        logger.info("\nStep 3: Removing participant...")
        result = remove_agent_chat_participant(
            integration_ctx, chat_id=test_chat, participant_id=test_peer_id
        )
        logger.info("Remove result: %s", result)
        assert "successfully" in result.lower()

        # Step 4: Verify participant is removed
        logger.info("\nStep 4: Verifying participant is removed...")
        result = list_agent_chat_participants(integration_ctx, chat_id=test_chat)
        parsed = json.loads(result)
        participant_ids = [p["id"] for p in parsed["data"]]
        assert test_peer_id not in participant_ids, (
            "Peer should not be in participant list"
        )
        logger.info("✓ Participant removed (remaining: %d)", len(parsed["data"]))

        logger.info("\n✓ Full add/remove cycle completed successfully")
