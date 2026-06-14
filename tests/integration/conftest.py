"""Pytest configuration for live-API integration tests.

Re-exports the live fixtures from ``tests.conftest_integration`` so test
modules under ``tests/integration/`` can request them directly. Credentials
are loaded from ``.env.test``; the whole suite skips without ``BAND_API_KEY``.
"""

from tests.conftest_integration import (
    BandTestSettings,
    LiveHarness,
    agent_room,
    get_api_key,
    get_base_url,
    get_test_agent_id,
    harness,
    live_config,
    requires_api,
    test_settings,
)

__all__ = [
    "BandTestSettings",
    "LiveHarness",
    "agent_room",
    "get_api_key",
    "get_base_url",
    "get_test_agent_id",
    "harness",
    "live_config",
    "requires_api",
    "test_settings",
]
