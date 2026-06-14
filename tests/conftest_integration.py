"""Fixtures for integration tests against a real API server.

These tests require a running API server and valid credentials.
Credentials are loaded from .env.test file automatically.

Run integration tests:
    uv run pytest tests/integration/ -v

Skip integration tests (run only unit tests):
    uv run pytest tests/ --ignore=tests/integration/
"""

from dataclasses import dataclass
from pathlib import Path

import pytest
from band_rest import RestClient

from band_mcp.shared import AppContext
from thenvoi_testing.markers import skip_without_env
from thenvoi_testing.settings import BaseTestSettings


class BandTestSettings(BaseTestSettings):
    """Settings for integration tests, loaded from .env.test."""

    band_api_key: str = ""
    band_base_url: str = "https://app.band.ai"
    test_agent_id: str = ""

    _env_file_path: Path = Path(__file__).parent.parent / ".env.test"


# Load settings from .env.test
test_settings = BandTestSettings()


def get_api_key() -> str | None:
    return test_settings.band_api_key or None


def get_base_url() -> str:
    return test_settings.band_base_url


def get_test_agent_id() -> str | None:
    return test_settings.test_agent_id or None


# Skip marker for integration tests
requires_api = skip_without_env("BAND_API_KEY")


@dataclass
class IntegrationRequestContext:
    """Request context for integration tests."""

    lifespan_context: AppContext


class IntegrationContext:
    """Real MCP Context for integration testing with actual API client."""

    def __init__(self, client: RestClient):
        self.request_context = IntegrationRequestContext(
            lifespan_context=AppContext(client=client)
        )


@pytest.fixture(scope="session")
def api_client() -> RestClient | None:
    """Create a real API client for integration tests.

    Returns None if BAND_API_KEY is not set.
    """
    api_key = get_api_key()
    if not api_key:
        return None

    return RestClient(
        api_key=api_key,
        base_url=get_base_url(),
    )


@pytest.fixture
def integration_ctx(api_client: RestClient | None) -> IntegrationContext:
    """Create a real Context for integration tests.

    Skips test if API client is not available.
    """
    if api_client is None:
        pytest.skip("BAND_API_KEY not set")

    return IntegrationContext(client=api_client)


@pytest.fixture
def test_chat(api_client: RestClient | None):
    """Create a temporary chat for testing and clean up after.

    Yields the chat ID for use in tests.
    Note: Cleanup may not be possible if delete is not supported.
    """
    if api_client is None:
        pytest.skip("BAND_API_KEY not set")

    from band_rest import ChatRoomRequest

    # Create a test chat
    response = api_client.agent_api.create_agent_chat(
        chat=ChatRoomRequest(title="Integration Test Chat")
    )
    chat_id = response.data.id

    yield chat_id


@pytest.fixture
def test_peer_id(api_client: RestClient | None) -> str | None:
    """Get a peer ID that can be used for testing participant operations.

    Returns the first available peer (agent or user) that can be added to chats.
    """
    if api_client is None:
        pytest.skip("BAND_API_KEY not set")

    response = api_client.agent_api.list_agent_peers()
    if response.data:
        return response.data[0].id
    return None
