"""Unit tests for `thenvoi_mcp.shared`.

Covers acceptance criterion #11 from INT-350: `get_human_tools` returns a
singleton, `get_agent_tools` caches per-room, `reset_agent_tools_cache` clears
the cache, and both helpers fail-soft (log + return None) when the SDK import
fails.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

from thenvoi_mcp import shared as shared_mod
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

    constructed: list[str] = []

    class FakeAgentTools:
        def __init__(self, room_id: str, rest: object):
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
        def __init__(self, room_id: str, rest: object):
            self.room_id = room_id

    monkeypatch.setattr(shared_mod, "_try_import_agent_tools", lambda: FakeAgentTools)

    a = get_agent_tools(ctx, "room_A")
    b = get_agent_tools(ctx, "room_B")
    assert a is not b
    assert a.room_id == "room_A"
    assert b.room_id == "room_B"


def test_reset_agent_tools_cache_clears_entries(monkeypatch):
    fake_agent_rest = MagicMock()
    app_ctx = AppContext(agent_rest=fake_agent_rest)
    ctx = _make_ctx(app_ctx)

    class FakeAgentTools:
        def __init__(self, room_id: str, rest: object):
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


def test_get_agent_tools_returns_none_when_sdk_import_fails(monkeypatch, caplog):
    fake_agent_rest = MagicMock()
    app_ctx = AppContext(agent_rest=fake_agent_rest)
    ctx = _make_ctx(app_ctx)

    # Simulate INT-349 not yet merged: the SDK import inside
    # _try_import_agent_tools fails and the helper returns None.
    monkeypatch.setattr(shared_mod, "_try_import_agent_tools", lambda: None)

    result = get_agent_tools(ctx, "room_A")
    assert result is None
    # Nothing should be cached when construction fails.
    assert app_ctx._agent_tools_cache == {}
