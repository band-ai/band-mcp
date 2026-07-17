"""Wire-compatibility behavior for SDK MCP registration shims."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from band.runtime.mcp_server import MCPToolRegistration
from pydantic import BaseModel

from band_mcp.tools.shims import chat_id_compat, pinned


class RoomInput(BaseModel):
    room_id: str
    content: str


def registration(execute: AsyncMock) -> MCPToolRegistration:
    """Build one representative room-scoped SDK registration."""
    return MCPToolRegistration(
        name="band_send_message",
        description="Send a message.",
        input_model=RoomInput,
        execute=execute,
        input_schema={
            "type": "object",
            "properties": {
                "room_id": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["room_id", "content"],
        },
    )


async def test_chat_id_compat_advertises_chat_id_and_maps_to_sdk_room_id() -> None:
    execute = AsyncMock(return_value="sent")
    shim = chat_id_compat(registration(execute))

    result = await shim.execute({"chat_id": "room-a", "content": "hello"})

    assert result == "sent"
    execute.assert_awaited_once_with({"room_id": "room-a", "content": "hello"})
    schema = shim.to_mcp_tool().inputSchema
    assert "chat_id" in schema["properties"]
    assert "room_id" not in schema["properties"]
    assert "chat_id" in schema["required"]


async def test_pinned_room_injects_matching_room_and_hides_the_parameter() -> None:
    execute = AsyncMock(return_value="sent")
    shim = pinned(chat_id_compat(registration(execute)), "room-pinned")

    await shim.execute({"chat_id": "room-pinned", "content": "hello"})

    execute.assert_awaited_once_with({"content": "hello", "room_id": "room-pinned"})
    schema = shim.to_mcp_tool().inputSchema
    assert "chat_id" not in schema["properties"]
    assert "chat_id" not in schema["required"]


async def test_pinned_room_rejects_a_conflicting_caller_value() -> None:
    execute = AsyncMock()
    shim = pinned(chat_id_compat(registration(execute)), "room-pinned")

    with pytest.raises(ValueError, match="server is pinned to room room-pinned"):
        await shim.execute({"chat_id": "room-other", "content": "hello"})

    execute.assert_not_awaited()
