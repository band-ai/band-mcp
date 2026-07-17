"""Behavioral tests for runtime context ownership."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from band_mcp import context as context_mod
from band_mcp.config import Config, ConfigError
from band_mcp.context import AGENT_TOOLS_CACHE_MAX_SIZE, AppContext, build_app_context


def test_build_app_context_creates_only_requested_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_clients: list[str] = []

    class FakeRestClient:
        def __init__(self, api_key: str, base_url: str) -> None:
            created_clients.append(api_key)

    class FakeAgentTools:
        def __init__(self, room_id: str, rest: object) -> None:
            self.room_id = room_id

    monkeypatch.setattr(context_mod, "AsyncRestClient", FakeRestClient)
    monkeypatch.setattr(context_mod, "_agent_tools_class", lambda: FakeAgentTools)

    context = build_app_context(Config(scope=["agent"], agent_key="agent-key"))

    assert created_clients == ["agent-key"]
    assert context.human_rest is None
    assert context.human_tools is None
    assert context.agent_tools_roomless.room_id == ""


def test_build_app_context_constructs_one_human_tools_singleton(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed_tools: list[object] = []

    class FakeRestClient:
        def __init__(self, api_key: str, base_url: str) -> None:
            self.api_key = api_key

    class FakeHumanTools:
        def __init__(self, rest: object) -> None:
            constructed_tools.append(rest)

    monkeypatch.setattr(context_mod, "AsyncRestClient", FakeRestClient)
    monkeypatch.setattr(context_mod, "_human_tools_class", lambda: FakeHumanTools)

    context = build_app_context(Config(scope=["human"], user_key="human-key"))

    assert context.human_tools is not None
    assert constructed_tools == [context.human_rest]


def test_agent_tools_cache_reuses_a_room_but_isolates_rooms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed: list[str] = []

    class FakeAgentTools:
        def __init__(self, room_id: str, rest: object) -> None:
            self.room_id = room_id
            constructed.append(room_id)

    monkeypatch.setattr(context_mod, "_agent_tools_class", lambda: FakeAgentTools)
    context = AppContext(agent_rest=MagicMock())

    first = context.agent_tools_for("room-a")
    repeated = context.agent_tools_for("room-a")
    other = context.agent_tools_for("room-b")

    assert first is repeated
    assert other is not first
    assert constructed == ["room-a", "room-b"]


def test_roomless_tools_never_share_participant_state_with_room_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAgentTools:
        def __init__(self, room_id: str, rest: object) -> None:
            self.room_id = room_id

    monkeypatch.setattr(context_mod, "_agent_tools_class", lambda: FakeAgentTools)
    rest = MagicMock()
    roomless = context_mod._create_agent_tools("", rest)
    context = AppContext(agent_rest=rest, agent_tools_roomless=roomless)

    assert context.agent_tools_roomless is not context.agent_tools_for("")


def test_cache_evicts_the_least_recently_used_room(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAgentTools:
        def __init__(self, room_id: str, rest: object) -> None:
            self.room_id = room_id

    monkeypatch.setattr(context_mod, "_agent_tools_class", lambda: FakeAgentTools)
    context = AppContext(agent_rest=MagicMock())

    for index in range(AGENT_TOOLS_CACHE_MAX_SIZE):
        context.agent_tools_for(f"room-{index}")
    context.agent_tools_for("room-0")
    context.agent_tools_for("room-overflow")

    assert "room-0" in context._agent_tools_cache
    assert "room-1" not in context._agent_tools_cache
    assert len(context._agent_tools_cache) == AGENT_TOOLS_CACHE_MAX_SIZE


def test_discard_only_evicts_the_matching_cached_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAgentTools:
        def __init__(self, room_id: str, rest: object) -> None:
            self.room_id = room_id

    monkeypatch.setattr(context_mod, "_agent_tools_class", lambda: FakeAgentTools)
    context = AppContext(agent_rest=MagicMock())
    current = context.agent_tools_for("room-a")

    context.discard("room-a", object())
    assert context.agent_tools_for("room-a") is current

    context.discard("room-a", current)
    assert "room-a" not in context._agent_tools_cache


def test_same_room_lock_is_stable() -> None:
    context = AppContext()

    assert context.room_lock("room-a") is context.room_lock("room-a")


def test_missing_sdk_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    context = AppContext(agent_rest=MagicMock())

    def missing_sdk() -> object:
        raise ConfigError("band-sdk is required")

    monkeypatch.setattr(context_mod, "_agent_tools_class", missing_sdk)

    with pytest.raises(ConfigError, match="band-sdk"):
        context.agent_tools_for("room-a")
