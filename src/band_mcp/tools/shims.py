"""Explicit compatibility shims around SDK-owned MCP registrations."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any, Sequence

from band.runtime.mcp_server import MCPToolRegistration
from band.runtime.tools import (
    ToolDefinition,
    get_tool_description,
    validate_tool_arguments,
)
from pydantic import BaseModel, Field, create_model

from band_mcp.context import AppContext

__all__ = [
    "AGENT_ROOM_BOUND_TOOL_NAMES",
    "chat_id_compat",
    "human_registrations",
    "pinned",
    "widen_send_event",
    "with_room_lock_and_send_refresh",
]

# TODO(sdk): add a room-scoped flag to ToolDefinition.
AGENT_ROOM_BOUND_TOOL_NAMES = frozenset(
    {
        "band_send_message",
        "band_send_event",
        "band_add_participant",
        "band_remove_participant",
        "band_get_participants",
        "band_lookup_peers",
    }
)
_ROOM_PARAMETER = "room_id"
_CHAT_PARAMETER = "chat_id"
_EVENT_TYPES = ("tool_call", "tool_result", "thought", "error", "task")


def _schema_with_chat_id(schema: dict[str, Any]) -> dict[str, Any]:
    schema = deepcopy(schema)
    properties = schema["properties"]
    room_schema = properties.pop(_ROOM_PARAMETER)
    room_schema["description"] = (
        "ID of the chat room (accepted as 'chat_id' or 'room_id')."
    )
    properties[_CHAT_PARAMETER] = room_schema
    schema["properties"] = {
        _CHAT_PARAMETER: properties.pop(_CHAT_PARAMETER),
        **properties,
    }
    schema["required"] = [
        _CHAT_PARAMETER if name == _ROOM_PARAMETER else name
        for name in schema.get("required", [])
    ]
    return schema


def _room_id(arguments: dict[str, Any]) -> str | None:
    value = arguments.get(_CHAT_PARAMETER, arguments.get(_ROOM_PARAMETER))
    return str(value) if value is not None else None


def chat_id_compat(registration: MCPToolRegistration) -> MCPToolRegistration:
    """Advertise ``chat_id`` while accepting it as an alias for SDK ``room_id``.

    TODO(sdk): allow the resolved registration builder to choose its room parameter.
    """
    schema = _schema_with_chat_id(registration.to_mcp_tool().inputSchema)

    async def execute(arguments: dict[str, Any]) -> Any:
        mapped = dict(arguments)
        if _CHAT_PARAMETER in mapped:
            mapped[_ROOM_PARAMETER] = mapped.pop(_CHAT_PARAMETER)
        return await registration.execute(mapped)

    return replace(registration, input_schema=schema, execute=execute)


def with_room_lock_and_send_refresh(
    registration: MCPToolRegistration, context: AppContext
) -> MCPToolRegistration:
    """Serialize mutable AgentTools calls and refresh mentions before sending.

    TODO(sdk): provide call-scoped locking and refresh-before-send in its builder.
    """

    async def execute(arguments: dict[str, Any]) -> Any:
        room_id = _room_id(arguments)
        async with context.room_lock(room_id):
            if registration.name == "band_send_message":
                if room_id is None:
                    return await registration.execute(arguments)
                tools = context.agent_tools_for(room_id)
                if tools is None:
                    return await registration.execute(arguments)
                try:
                    await tools.get_participants()
                except Exception:
                    context.discard(room_id, tools)
                    raise
            return await registration.execute(arguments)

    return replace(registration, execute=execute)


def widen_send_event(
    registration: MCPToolRegistration, context: AppContext
) -> MCPToolRegistration:
    """Accept legacy event types while the SDK model remains narrower.

    TODO(sdk): widen SendEventInput.message_type to include tool_call and tool_result.
    """
    if registration.name != "band_send_event":
        return registration

    input_model = create_model(
        "McpSendEventInput",
        __base__=registration.input_model,
        message_type=(str, Field(..., json_schema_extra={"enum": list(_EVENT_TYPES)})),
    )
    schema = registration.to_mcp_tool().inputSchema
    schema = deepcopy(schema)
    schema["properties"]["message_type"]["enum"] = list(_EVENT_TYPES)

    async def execute(arguments: dict[str, Any]) -> Any:
        room_id = _room_id(arguments)
        if room_id is None:
            raise ValueError("band_send_event: missing chat_id (or room_id)")
        tools = context.agent_tools_for(room_id)
        if tools is None:
            raise ValueError(f"No tools available for room {room_id}")
        values = dict(arguments)
        values.pop(_CHAT_PARAMETER, None)
        values.pop(_ROOM_PARAMETER, None)
        call_args = validate_tool_arguments(registration.name, input_model, values)
        return await tools.send_event(**call_args)

    return replace(
        registration, input_model=input_model, input_schema=schema, execute=execute
    )


def pinned(registration: MCPToolRegistration, room_id: str) -> MCPToolRegistration:
    """Hide a room field and inject one fixed room, rejecting conflicts.

    TODO(sdk): provide pinned-room registration support with conflict rejection.
    """
    schema = registration.to_mcp_tool().inputSchema
    if _CHAT_PARAMETER not in schema.get("properties", {}):
        return registration
    schema = deepcopy(schema)
    schema["properties"].pop(_CHAT_PARAMETER)
    schema["required"] = [
        name for name in schema.get("required", []) if name != _CHAT_PARAMETER
    ]

    async def execute(arguments: dict[str, Any]) -> Any:
        caller_room = _room_id(arguments)
        if caller_room is not None and caller_room != room_id:
            raise ValueError(f"server is pinned to room {room_id}")
        injected = dict(arguments)
        injected.pop(_ROOM_PARAMETER, None)
        injected[_CHAT_PARAMETER] = room_id
        return await registration.execute(injected)

    return replace(registration, input_schema=schema, execute=execute)


def human_registrations(
    context: AppContext, definitions: Sequence[ToolDefinition]
) -> list[MCPToolRegistration]:
    """Build human-surface registrations until the SDK exposes a human builder.

    TODO(sdk): provide a HumanTools MCP registration builder.
    """
    registrations: list[MCPToolRegistration] = []
    for definition in definitions:
        input_model = definition.input_model

        async def execute(
            arguments: dict[str, Any],
            definition: ToolDefinition = definition,
            input_model: type[BaseModel] = input_model,
        ) -> Any:
            if context.human_tools is None:
                raise ValueError("No human tools available")
            call_args = validate_tool_arguments(definition.name, input_model, arguments)
            method = getattr(context.human_tools, definition.method_name)
            return await method(**call_args)

        registrations.append(
            MCPToolRegistration(
                name=definition.name,
                description=get_tool_description(definition.name),
                input_model=input_model,
                execute=execute,
            )
        )
    return registrations
