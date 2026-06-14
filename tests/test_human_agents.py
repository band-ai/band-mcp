"""Unit tests for human agent tools (list_my_agents, register_my_agent)."""

import json

from thenvoi_testing.factories import factory
from band_mcp.tools.human.human_agents import (
    list_my_agents,
    register_my_agent,
)


class TestListMyAgents:
    """Tests for list_my_agents tool."""

    def test_returns_list_of_agents(self, mock_ctx, mock_human_api):
        """Test successful retrieval of agent list."""
        agents = [
            factory.owned_agent(name="Agent One"),
            factory.owned_agent(name="Agent Two"),
        ]
        mock_human_api.list_my_agents.return_value = factory.list_response(agents)

        result = list_my_agents(mock_ctx)

        mock_human_api.list_my_agents.assert_called_once_with(
            page=None,
            page_size=None,
        )
        parsed = json.loads(result)
        assert len(parsed["data"]) == 2

    def test_pagination_parameters(self, mock_ctx, mock_human_api):
        """Test pagination parameters are passed through."""
        mock_human_api.list_my_agents.return_value = factory.list_response([])

        list_my_agents(mock_ctx, page=2, page_size=10)

        mock_human_api.list_my_agents.assert_called_once_with(
            page=2,
            page_size=10,
        )

    def test_empty_agent_list(self, mock_ctx, mock_human_api):
        """Test handling of empty agent list."""
        mock_human_api.list_my_agents.return_value = factory.list_response([])

        result = list_my_agents(mock_ctx)

        parsed = json.loads(result)
        assert parsed["data"] == []


class TestRegisterMyAgent:
    """Tests for register_my_agent tool."""

    def test_registers_agent_with_name_and_description(self, mock_ctx, mock_human_api):
        """Test registering an agent with name and description."""
        mock_human_api.register_my_agent.return_value = factory.response(
            factory.registered_agent(name="New Agent")
        )

        result = register_my_agent(
            mock_ctx, name="New Agent", description="A helpful agent"
        )

        mock_human_api.register_my_agent.assert_called_once()
        call_args = mock_human_api.register_my_agent.call_args
        assert call_args.kwargs["agent"].name == "New Agent"
        assert call_args.kwargs["agent"].description == "A helpful agent"
        parsed = json.loads(result)
        assert "data" in parsed

    def test_registers_agent_passes_request_object(self, mock_ctx, mock_human_api):
        """Test that register_my_agent passes an AgentRegisterRequest to the API."""
        mock_human_api.register_my_agent.return_value = factory.response(
            factory.registered_agent(name="My Agent")
        )

        register_my_agent(
            mock_ctx,
            name="My Agent",
            description="Does things",
        )

        call_args = mock_human_api.register_my_agent.call_args
        agent_req = call_args.kwargs["agent"]
        assert agent_req.name == "My Agent"
        assert agent_req.description == "Does things"
