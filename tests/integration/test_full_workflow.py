"""Full workflow integration tests for all MCP tools.

Tests the complete agent workflow from identity to message lifecycle.
Run with: uv run pytest tests/integration/test_full_workflow.py -v -s --no-cov
"""

import json
import logging
from typing import Any

from tests.integration.conftest import get_test_agent_id, requires_api
from band_mcp.tools.agent.agent_chats import (
    create_agent_chat,
    get_agent_chat,
    list_agent_chats,
)
from band_mcp.tools.agent.agent_events import create_agent_chat_event
from band_mcp.tools.agent.agent_identity import get_agent_me, list_agent_peers
from band_mcp.tools.agent.agent_lifecycle import (
    mark_agent_message_failed,
    mark_agent_message_processed,
    mark_agent_message_processing,
)
from band_mcp.tools.agent.agent_messages import (
    create_agent_chat_message,
    get_agent_chat_context,
)
from band_mcp.tools.agent.agent_participants import (
    add_agent_chat_participant,
    list_agent_chat_participants,
)
from thenvoi_testing.pagination import fetch_all_pages, item_exists_in_pages

logger = logging.getLogger(__name__)


def fetch_all_context(
    ctx,
    chat_id: str,
    page_size: int = 50,
) -> list[dict[str, Any]]:
    """Fetch all pages of chat context.

    Args:
        ctx: Integration context
        chat_id: The chat ID to get context for
        page_size: Number of items per page

    Returns:
        List of all context items across all pages
    """
    all_items = []
    page = 1

    while True:
        result = get_agent_chat_context(
            ctx, chat_id=chat_id, page=page, page_size=page_size
        )
        parsed = json.loads(result)

        items = parsed.get("data", [])
        all_items.extend(items)

        metadata = parsed.get("metadata", {})
        total_pages = metadata.get("total_pages", 1)

        if page >= total_pages:
            break
        page += 1

    return all_items


@requires_api
class TestFullWorkflow:
    """End-to-end integration test covering all MCP tools in a realistic workflow."""

    def test_complete_agent_workflow(self, integration_ctx):
        """Test complete workflow: identity → chat → participants → messages → events → lifecycle."""

        # ============================================================
        # STEP 1: Identity - Get agent profile
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 1: Get Agent Identity")
        logger.info("=" * 60)

        result = get_agent_me(integration_ctx)
        parsed = json.loads(result)
        assert parsed["data"] is not None, "Agent profile should not be None"

        agent = parsed["data"]
        agent_id = agent["id"]
        agent_name = agent["name"]
        logger.info("Agent: %s (ID: %s)", agent_name, agent_id)

        # Verify against expected test agent if configured
        expected_agent_id = get_test_agent_id()
        if expected_agent_id:
            assert agent_id == expected_agent_id, f"Expected agent {expected_agent_id}"

        # ============================================================
        # STEP 2: Identity - List available peers (with pagination)
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 2: List Available Peers (all pages)")
        logger.info("=" * 60)

        peers = fetch_all_pages(integration_ctx, list_agent_peers)
        assert isinstance(peers, list), "Peers should be a list"
        logger.info("Found %d available peers across all pages", len(peers))

        # We need at least one User peer to test human participant operations
        assert len(peers) > 0, "Need at least one peer for participant tests"

        # Find a User peer (human) - this is the key test: agent communicating with human
        user_peer = next((p for p in peers if p["type"] == "User"), None)
        assert user_peer is not None, (
            "Need at least one User peer to test agent-human communication"
        )

        peer = user_peer
        peer_id = peer["id"]
        peer_name = peer["name"]
        peer_type = peer["type"]
        logger.info(
            "Will use User peer: %s (%s, ID: %s)", peer_name, peer_type, peer_id
        )

        # ============================================================
        # STEP 3: Chats - Create a new chat
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 3: Create New Chat")
        logger.info("=" * 60)

        result = create_agent_chat(integration_ctx)
        parsed = json.loads(result)
        assert parsed["data"] is not None, "Created chat should not be None"

        chat = parsed["data"]
        chat_id = chat["id"]
        logger.info("Created chat (ID: %s, title: %s)", chat_id, chat.get("title"))

        # ============================================================
        # STEP 4: Chats - Get the created chat
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 4: Get Chat Details")
        logger.info("=" * 60)

        result = get_agent_chat(integration_ctx, chat_id=chat_id)
        parsed = json.loads(result)
        assert parsed["data"] is not None, "Chat should exist"
        assert parsed["data"]["id"] == chat_id, "Chat ID should match"
        logger.info("Retrieved chat: %s", parsed["data"].get("title"))

        # ============================================================
        # STEP 5: Chats - Verify chat appears in list (with pagination)
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 5: List Chats (verify new chat appears, checking all pages)")
        logger.info("=" * 60)

        chat_exists = item_exists_in_pages(integration_ctx, list_agent_chats, chat_id)
        assert chat_exists, "New chat should appear in chat list"
        all_chats = fetch_all_pages(integration_ctx, list_agent_chats)
        logger.info(
            "Chat list contains %d chats across all pages, including our test chat",
            len(all_chats),
        )

        # ============================================================
        # STEP 6: Participants - List initial participants
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 6: List Initial Participants")
        logger.info("=" * 60)

        result = list_agent_chat_participants(integration_ctx, chat_id=chat_id)
        parsed = json.loads(result)
        initial_participants = parsed["data"]
        logger.info("Initial participants: %d", len(initial_participants))
        for p in initial_participants:
            logger.info(
                "  - %s (%s, role: %s)", p["name"], p["type"], p.get("role", "N/A")
            )

        # ============================================================
        # STEP 7: Participants - Add peer to chat
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 7: Add Participant to Chat")
        logger.info("=" * 60)

        result = add_agent_chat_participant(
            integration_ctx, chat_id=chat_id, participant_id=peer_id, role="member"
        )
        logger.info("Result: %s", result)
        assert "successfully" in result.lower(), "Should indicate success"

        # ============================================================
        # STEP 8: Participants - Verify participant was added
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 8: Verify Participant Added")
        logger.info("=" * 60)

        result = list_agent_chat_participants(integration_ctx, chat_id=chat_id)
        parsed = json.loads(result)
        participants = parsed["data"]
        participant_ids = [p["id"] for p in participants]
        assert peer_id in participant_ids, "Peer should now be a participant"
        logger.info("Participants after adding: %d", len(participants))
        for p in participants:
            logger.info(
                "  - %s (%s, role: %s)", p["name"], p["type"], p.get("role", "N/A")
            )

        # ============================================================
        # STEP 9: Messages - Send a message with mention
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 9: Send Message with Mention")
        logger.info("=" * 60)

        # Find the peer's name for mention
        peer_participant = next((p for p in participants if p["id"] == peer_id), None)
        mention_name = peer_participant.get("name") or peer_name

        message_content = f"Hello @{mention_name}, this is an integration test message!"
        mentions = json.dumps([{"id": peer_id, "name": mention_name}])

        result = create_agent_chat_message(
            integration_ctx,
            chat_id=chat_id,
            content=message_content,
            mentions=mentions,
        )
        parsed = json.loads(result)
        assert parsed["data"] is not None, "Message should be created"

        message = parsed["data"]
        message_id = message["id"]
        logger.info("Sent message: '%s...' (ID: %s)", message_content[:50], message_id)

        # ============================================================
        # STEP 10: Messages - Get chat context (verify message, with pagination)
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 10: Get Chat Context (all pages)")
        logger.info("=" * 60)

        context = fetch_all_context(integration_ctx, chat_id)
        assert isinstance(context, list), "Context should be a list"
        message_ids = [m["id"] for m in context if "id" in m]
        assert message_id in message_ids, "Our message should appear in context"
        logger.info("Chat context contains %d items across all pages", len(context))

        # ============================================================
        # STEP 11: Events - Create a thought event
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 11: Create Thought Event")
        logger.info("=" * 60)

        event_content = "Processing the user's request about integration testing..."
        result = create_agent_chat_event(
            integration_ctx,
            chat_id=chat_id,
            content=event_content,
            message_type="thought",
        )
        parsed = json.loads(result)
        assert parsed["data"] is not None, "Event should be created"

        event = parsed["data"]
        event_id = event["id"]
        logger.info("Created thought event (ID: %s)", event_id)

        # ============================================================
        # STEP 12: Events - Create a tool_call event
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 12: Create Tool Call Event")
        logger.info("=" * 60)

        tool_metadata = json.dumps(
            {
                "function": {
                    "name": "search_database",
                    "arguments": {"query": "integration test"},
                }
            }
        )
        result = create_agent_chat_event(
            integration_ctx,
            chat_id=chat_id,
            content="Calling search_database",
            message_type="tool_call",
            metadata=tool_metadata,
        )
        parsed = json.loads(result)
        assert parsed["data"] is not None, "Tool call event should be created"
        logger.info("Created tool_call event (ID: %s)", parsed["data"]["id"])

        # ============================================================
        # STEP 13: Events - Create a tool_result event
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 13: Create Tool Result Event")
        logger.info("=" * 60)

        result_metadata = json.dumps(
            {"result": {"found": 5, "items": ["item1", "item2"]}}
        )
        result = create_agent_chat_event(
            integration_ctx,
            chat_id=chat_id,
            content="Search completed successfully",
            message_type="tool_result",
            metadata=result_metadata,
        )
        parsed = json.loads(result)
        assert parsed["data"] is not None, "Tool result event should be created"
        logger.info("Created tool_result event (ID: %s)", parsed["data"]["id"])

        # ============================================================
        # STEP 14: Lifecycle - Mark message as processing
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 14: Mark Message Processing")
        logger.info("=" * 60)

        result = mark_agent_message_processing(
            integration_ctx, chat_id=chat_id, message_id=message_id
        )
        parsed = json.loads(result)
        logger.info("Marked message %s as processing", message_id)

        # ============================================================
        # STEP 15: Lifecycle - Mark message as processed
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 15: Mark Message Processed")
        logger.info("=" * 60)

        result = mark_agent_message_processed(
            integration_ctx, chat_id=chat_id, message_id=message_id
        )
        parsed = json.loads(result)
        logger.info("Marked message %s as processed", message_id)

        # ============================================================
        # STEP 16: Verify User still in chat after all operations
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("STEP 16: Verify User Still in Chat")
        logger.info("=" * 60)

        result = list_agent_chat_participants(integration_ctx, chat_id=chat_id)
        parsed = json.loads(result)
        participant_ids = [p["id"] for p in parsed["data"]]
        assert peer_id in participant_ids, "User should still be a participant"
        logger.info("Verified: User '%s' is still in chat", peer_name)
        logger.info("Total participants: %d", len(parsed["data"]))
        for p in parsed["data"]:
            logger.info(
                "  - %s (%s, role: %s)", p["name"], p["type"], p.get("role", "N/A")
            )

        # ============================================================
        # COMPLETE
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("WORKFLOW COMPLETE - All 16 steps passed!")
        logger.info("=" * 60)
        logger.info("Test chat ID: %s", chat_id)
        logger.info("User '%s' remains in chat as expected", peer_name)


@requires_api
class TestAddParticipantWithoutRole:
    """Test adding a participant without specifying a role (should default to member)."""

    def test_add_participant_without_role_defaults_to_member(self, integration_ctx):
        """Test that adding a participant without role defaults to 'member'.

        This test verifies the bug fix: the docstring says role 'defaults to member'
        but the code was sending None, causing a 422 error from the API.
        """
        logger.info("\n" + "=" * 60)
        logger.info("Testing Add Participant Without Role")
        logger.info("=" * 60)

        # Create a chat for this test
        result = create_agent_chat(integration_ctx)
        parsed = json.loads(result)
        chat_id = parsed["data"]["id"]
        logger.info("Created test chat: %s", chat_id)

        # Get peers and find a User peer to add to the chat
        result = list_agent_peers(integration_ctx)
        parsed = json.loads(result)
        assert len(parsed["data"]) > 0, "Need at least one peer"

        # Find a User peer (human) for this test
        user_peer = next((p for p in parsed["data"] if p["type"] == "User"), None)
        assert user_peer is not None, "Need at least one User peer"

        peer_id = user_peer["id"]
        peer_name = user_peer["name"]
        logger.info("Found User peer: %s (ID: %s)", peer_name, peer_id)

        # Add participant WITHOUT specifying role - this should default to "member"
        logger.info("Adding participant without role parameter...")
        result = add_agent_chat_participant(
            integration_ctx, chat_id=chat_id, participant_id=peer_id
        )
        logger.info("Result: %s", result)
        assert "successfully" in result.lower(), "Should indicate success"

        # Verify participant was added with member role
        result = list_agent_chat_participants(integration_ctx, chat_id=chat_id)
        parsed = json.loads(result)
        participants = parsed["data"]

        added_participant = next((p for p in participants if p["id"] == peer_id), None)
        assert added_participant is not None, "Participant should be in the chat"
        assert added_participant.get("role") == "member", (
            f"Role should default to 'member', got: {added_participant.get('role')}"
        )

        logger.info(
            "Verified: %s added with role '%s'",
            peer_name,
            added_participant.get("role"),
        )
        logger.info("Test complete - default role works correctly!")


@requires_api
class TestMessageFailureLifecycle:
    """Test the message failure lifecycle separately."""

    def test_mark_message_failed(self, integration_ctx):
        """Test marking a message as failed with error message."""
        logger.info("\n" + "=" * 60)
        logger.info("Testing Message Failure Lifecycle")
        logger.info("=" * 60)

        # Create a chat for this test
        result = create_agent_chat(integration_ctx)
        parsed = json.loads(result)
        chat_id = parsed["data"]["id"]
        logger.info("Created test chat: %s", chat_id)

        # Get peers and find a User peer to add to the chat
        result = list_agent_peers(integration_ctx)
        parsed = json.loads(result)
        assert len(parsed["data"]) > 0, "Need at least one peer"

        # Find a User peer (human) for this test
        user_peer = next((p for p in parsed["data"] if p["type"] == "User"), None)
        assert user_peer is not None, "Need at least one User peer"

        peer_id = user_peer["id"]
        peer_name = user_peer["name"]

        add_agent_chat_participant(
            integration_ctx, chat_id=chat_id, participant_id=peer_id, role="member"
        )
        logger.info("Added User peer: %s", peer_name)

        # Send a message
        mentions = json.dumps([{"id": peer_id, "name": peer_name}])
        result = create_agent_chat_message(
            integration_ctx,
            chat_id=chat_id,
            content=f"Test message for @{peer_name}",
            mentions=mentions,
        )
        parsed = json.loads(result)
        message_id = parsed["data"]["id"]
        logger.info("Created message: %s", message_id)

        # Mark as processing
        mark_agent_message_processing(
            integration_ctx, chat_id=chat_id, message_id=message_id
        )
        logger.info("Marked as processing")

        # Mark as failed
        error_message = "Integration test simulated failure"
        result = mark_agent_message_failed(
            integration_ctx,
            chat_id=chat_id,
            message_id=message_id,
            error=error_message,
        )
        parsed = json.loads(result)
        logger.info("Marked as failed with error: %s", error_message)

        # Verify User is still in the chat
        result = list_agent_chat_participants(integration_ctx, chat_id=chat_id)
        parsed = json.loads(result)
        participant_ids = [p["id"] for p in parsed["data"]]
        assert peer_id in participant_ids, "User should still be a participant"
        logger.info("Verified: User '%s' is still in chat", peer_name)

        logger.info("Failure lifecycle test complete!")
