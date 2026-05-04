"""Unit tests for `thenvoi_mcp.shared`.

Covers acceptance criterion #11 from INT-350: `get_human_tools` returns a
singleton, `get_agent_tools` caches per-room, `reset_agent_tools_cache` clears
the cache. INT-352 hardened SDK import to fail-hard (ConfigError) rather than
fail-soft — tests below reflect that.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from thenvoi_mcp import shared as shared_mod
from thenvoi_mcp.config import ConfigError
from thenvoi_mcp.shared import (
    AppContext,
    get_agent_tools,
    get_human_tools,
    reset_agent_tools_cache,
)


def _make_ctx(app_context: AppContext) -> object:
    """Build a minimal ctx object matching AppContextType for the helpers."""
    request_context = SimpleNamespace(lifespan_context=app_context)
    return SimpleNamespace(request_context=request_context)


# ---------------------------------------------------------------------------
# get_human_tools: startup-constructed singleton
# ---------------------------------------------------------------------------


def test_get_human_tools_returns_singleton_across_calls():
    sentinel = object()
    app_ctx = AppContext(human_tools=sentinel)
    ctx = _make_ctx(app_ctx)

    first = get_human_tools(ctx)
    second = get_human_tools(ctx)
    assert first is sentinel
    assert second is sentinel
    assert first is second


def test_get_human_tools_returns_none_and_warns_when_unavailable(caplog):
    app_ctx = AppContext(human_tools=None)
    ctx = _make_ctx(app_ctx)

    with caplog.at_level(logging.WARNING, logger="thenvoi_mcp.shared"):
        result = get_human_tools(ctx)
    assert result is None
    assert any("HumanTools not available" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# get_agent_tools: per-room cache
# ---------------------------------------------------------------------------


def test_get_agent_tools_caches_per_room(monkeypatch):
    fake_agent_rest = MagicMock()
    app_ctx = AppContext(agent_rest=fake_agent_rest)
    ctx = _make_ctx(app_ctx)

    constructed: list[str | None] = []

    class FakeAgentTools:
        def __init__(self, room_id: str | None, rest: object):
            self.room_id = room_id
            self.rest = rest
            constructed.append(room_id)

    monkeypatch.setattr(shared_mod, "_try_import_agent_tools", lambda: FakeAgentTools)

    first = get_agent_tools(ctx, "room_A")
    second = get_agent_tools(ctx, "room_A")
    assert first is second
    assert constructed == ["room_A"]


def test_get_agent_tools_returns_distinct_instance_per_room(monkeypatch):
    fake_agent_rest = MagicMock()
    app_ctx = AppContext(agent_rest=fake_agent_rest)
    ctx = _make_ctx(app_ctx)

    class FakeAgentTools:
        def __init__(self, room_id: str | None, rest: object):
            self.room_id = room_id

    monkeypatch.setattr(shared_mod, "_try_import_agent_tools", lambda: FakeAgentTools)

    a = get_agent_tools(ctx, "room_A")
    b = get_agent_tools(ctx, "room_B")
    assert a is not b
    assert a.room_id == "room_A"
    assert b.room_id == "room_B"


def test_get_agent_tools_accepts_none_for_room_less_agent_tools(monkeypatch):
    fake_client = MagicMock()
    fake_agent_rest = MagicMock()
    app_ctx = AppContext(client=fake_client, agent_rest=fake_agent_rest)
    ctx = _make_ctx(app_ctx)

    class FakeAgentTools:
        def __init__(self, room_id: str | None, rest: object):
            self.room_id = room_id

    monkeypatch.setattr(shared_mod, "_try_import_agent_tools", lambda: FakeAgentTools)

    result = get_agent_tools(ctx, None)

    assert result.room_id is None
    assert app_ctx._agent_tools_cache == {None: result}


def test_reset_agent_tools_cache_clears_entries(monkeypatch):
    fake_agent_rest = MagicMock()
    app_ctx = AppContext(agent_rest=fake_agent_rest)
    ctx = _make_ctx(app_ctx)

    class FakeAgentTools:
        def __init__(self, room_id: str | None, rest: object):
            self.room_id = room_id

    monkeypatch.setattr(shared_mod, "_try_import_agent_tools", lambda: FakeAgentTools)

    before = get_agent_tools(ctx, "room_A")
    assert app_ctx._agent_tools_cache == {"room_A": before}

    reset_agent_tools_cache(ctx)
    assert app_ctx._agent_tools_cache == {}

    # A subsequent call produces a fresh instance.
    after = get_agent_tools(ctx, "room_A")
    assert after is not before


def test_get_agent_tools_returns_none_without_agent_credential(caplog):
    app_ctx = AppContext(agent_rest=None)
    ctx = _make_ctx(app_ctx)

    with caplog.at_level(logging.WARNING, logger="thenvoi_mcp.shared"):
        result = get_agent_tools(ctx, "room_A")
    assert result is None
    assert any("no agent credential configured" in r.message for r in caplog.records)


def test_get_agent_tools_raises_when_sdk_import_fails(monkeypatch):
    fake_agent_rest = MagicMock()
    app_ctx = AppContext(agent_rest=fake_agent_rest)
    ctx = _make_ctx(app_ctx)

    # INT-352 change: a missing SDK is a configuration error, not a silent
    # degradation. `_try_import_agent_tools` now raises ConfigError on failure;
    # get_agent_tools propagates so the operator sees an actionable message.
    def _raise() -> object:
        raise ConfigError("thenvoi-sdk >= 0.3.0 is required")

    monkeypatch.setattr(shared_mod, "_try_import_agent_tools", _raise)

    with pytest.raises(ConfigError, match="thenvoi-sdk"):
        get_agent_tools(ctx, "room_A")
    # Nothing should be cached when construction fails.
    assert app_ctx._agent_tools_cache == {}
