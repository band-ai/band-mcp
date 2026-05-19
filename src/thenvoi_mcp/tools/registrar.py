"""SDK-driven MCP tool registrar (Phase 3 of INT-338, INT-351).

Replaces the handwritten per-tool ``@mcp.tool()`` registrations with a
scope-filtered loop over ``thenvoi.runtime.tools.iter_tool_definitions(...)``.
Each handler is a closure that:

1. Resets the per-request AgentTools cache on ``AppContext``.
2. Resolves the room id from validated input (or injects ``pinned_room_id``).
3. Dispatches to the Phase-1 ``HumanTools`` / ``AgentTools`` SDK method.

Design deviation from the Phase 3 spec (resolved with the ticket author)
-----------------------------------------------------------------------
The spec originally told the registrar to classify agent tools by checking
for a ``room_id`` field on ``ToolDefinition.input_model.model_fields``. That
classifier does not work for agent tools, because ``AgentTools`` is *room-
scoped via its constructor* (``AgentTools(room_id=..., rest=...)``) — the
SDK input models only cover method arguments, not the construction-time
room id. Putting ``room_id`` on the SDK input model would create a mismatch
between the input schema and the underlying ``AgentTools`` method
signature.

Resolution: the registrar *itself* is the layer that adds a room field to
the advertised agent tool schema. Today's handwritten MCP handlers use
``chat_id`` on every room-bound agent tool (see
``tools/agent/agent_messages.py`` and friends) — keeping that name means
zero breaking change for existing MCP consumers. ``AliasChoices("chat_id",
"room_id")`` makes the forward-compat ``room_id`` name work too, matching
the Phase 3 spec's intent. See ``AGENT_ROOM_BOUND_TOOL_NAMES`` below.

Human-surface classification is unchanged: human input models already carry
a ``chat_id`` field where applicable (Phase 1 derived them from
``HumanTools`` method signatures), so the Phase 3 spec's
``model_fields``-based classifier works for the human surface.
"""

from __future__ import annotations

import inspect
import json
from typing import Annotated, Any, Callable

from mcp.server.fastmcp import FastMCP
from pydantic import AliasChoices, BaseModel, Field, ValidationError, create_model
from pydantic.fields import FieldInfo
from pydantic.json_schema import SkipJsonSchema

from thenvoi_mcp.config import Config
from thenvoi_mcp.shared import (
    AppContextType,
    get_agent_tools,
    get_human_tools,
    logger,
    reset_agent_tools_cache,
)

# ---------------------------------------------------------------------------
# Agent room-bound tools
# ---------------------------------------------------------------------------
#
# These are the agent tools whose *current* MCP handler in
# ``src/thenvoi_mcp/tools/agent/*.py`` takes ``chat_id`` as a kwarg (i.e. the
# handler is room-scoped). Because ``AgentTools`` is constructor-scoped, the
# Phase 1 SDK input models do not carry a room field — so the registrar has
# to re-add it at the transport layer.
#
# Derived by grepping today's agent handlers for ``chat_id``. Kept as a
# module-level constant so tests can assert on it and so Phase 4 (INT-352)
# has an obvious pivot point for the handwritten-handler deletion.
AGENT_ROOM_BOUND_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "thenvoi_send_message",
        "thenvoi_send_event",
        "thenvoi_add_participant",
        "thenvoi_remove_participant",
        "thenvoi_get_participants",
        "thenvoi_lookup_peers",
    }
)


# ---------------------------------------------------------------------------
# Input-model transformers
# ---------------------------------------------------------------------------


def _extend_with_chat_id(
    original: type[BaseModel],
    pinned_room_id: str | None,
) -> type[BaseModel]:
    """Return a subclass of ``original`` that ADDS a ``chat_id`` field.

    Applied to agent room-bound tools (the SDK input models do not carry a
    room field; see module docstring).

    - Unpinned: ``chat_id`` is a required ``str`` with
      ``validation_alias=AliasChoices("chat_id", "room_id")`` so callers can
      post either name.
    - Pinned: ``chat_id`` is ``SkipJsonSchema[str | None]`` defaulted to
      ``None`` — the field is hidden from the advertised JSON schema but
      still accepted by the validator if a client sends it. The handler
      injects ``pinned_room_id`` at call time.
    """
    if pinned_room_id is None:
        return create_model(  # type: ignore[call-overload]
            f"{original.__name__}WithChatId",
            __base__=original,
            chat_id=(
                str,
                Field(
                    ...,
                    validation_alias=AliasChoices("chat_id", "room_id"),
                    description=(
                        "ID of the chat room (accepted as 'chat_id' or 'room_id')."
                    ),
                ),
            ),
        )
    return create_model(  # type: ignore[call-overload]
        f"{original.__name__}WithChatIdPinned",
        __base__=original,
        chat_id=(
            SkipJsonSchema[str | None],
            Field(
                default=None,
                validation_alias=AliasChoices("chat_id", "room_id"),
                description=("Pinned room id (hidden from advertised schema)."),
            ),
        ),
    )


def _pin_existing_chat_id(
    original: type[BaseModel],
    pinned_room_id: str,  # noqa: ARG001 - injected at call time, not in model
) -> type[BaseModel]:
    """Return a subclass that re-annotates existing ``chat_id`` as pinned.

    Applied to human room-bound tools (the SDK input models already have
    ``chat_id``). The advertised schema omits the field; inbound values are
    still accepted via alias so an older client passing ``chat_id`` does not
    fail validation. The handler injects ``pinned_room_id`` at call time.
    """
    return create_model(  # type: ignore[call-overload]
        f"{original.__name__}Pinned",
        __base__=original,
        chat_id=(
            SkipJsonSchema[str | None],
            Field(
                default=None,
                validation_alias=AliasChoices("chat_id", "room_id"),
                description=("Pinned room id (hidden from advertised schema)."),
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Handler construction
# ---------------------------------------------------------------------------


def _build_handler_signature(
    ctx_param_name: str,
    input_model: type[BaseModel],
) -> inspect.Signature:
    """Build a ``inspect.Signature`` for the dynamic handler.

    FastMCP inspects the handler's signature to derive the advertised JSON
    schema (see ``fastmcp.utilities.func_metadata.func_metadata``). We
    therefore need a real signature with one parameter per
    ``input_model`` field (plus the ``Context`` parameter FastMCP auto-
    injects).

    Fields annotated as ``SkipJsonSchema[...]`` are intentionally omitted:
    they are pinned-mode fields whose value is injected at call time and
    MUST NOT appear in the advertised schema.

    ``validation_alias`` (e.g. ``AliasChoices("chat_id", "room_id")``) is
    propagated onto the parameter annotation so FastMCP's internally-
    generated arg model accepts alternate names at the wire.
    """
    ctx_param = inspect.Parameter(
        ctx_param_name,
        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
        annotation=AppContextType,
    )

    parameters: list[inspect.Parameter] = [ctx_param]
    for field_name, field_info in input_model.model_fields.items():
        if _is_skip_json_schema(field_info):
            continue
        base_ann = field_info.annotation if field_info.annotation is not None else Any

        # Copy ``validation_alias`` onto the synthesized parameter so
        # FastMCP's derived arg model accepts both chat_id and room_id.
        field_kwargs: dict[str, Any] = {}
        if field_info.validation_alias is not None:
            field_kwargs["validation_alias"] = field_info.validation_alias
        if field_info.description:
            field_kwargs["description"] = field_info.description

        annotation = base_ann
        if field_kwargs:
            annotation = Annotated[base_ann, Field(**field_kwargs)]

        if field_info.is_required():
            parameters.append(
                inspect.Parameter(
                    field_name,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    annotation=annotation,
                )
            )
        else:
            default = field_info.default
            parameters.append(
                inspect.Parameter(
                    field_name,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    annotation=annotation,
                    default=default,
                )
            )

    return inspect.Signature(parameters=parameters, return_annotation=str)


def _is_skip_json_schema(field_info: FieldInfo) -> bool:
    """Return True if ``field_info.annotation`` is ``SkipJsonSchema[...]``."""
    metadata = getattr(field_info, "metadata", None) or []
    for meta in metadata:
        if meta.__class__.__name__ == "SkipJsonSchema":
            return True
    # Fallback: also inspect the annotation repr for the SkipJsonSchema marker
    # (older pydantic versions store it differently).
    ann_repr = repr(field_info.annotation)
    return "SkipJsonSchema" in ann_repr


def _serialize(result: Any) -> str:
    """Serialize SDK method output to a JSON string for MCP wire transport."""
    if result is None:
        return json.dumps(None)
    if isinstance(result, str):
        return result
    if hasattr(result, "model_dump"):
        return json.dumps(result.model_dump(mode="json"), default=str, indent=2)
    if isinstance(result, list):
        out = []
        for item in result:
            if hasattr(item, "model_dump"):
                out.append(item.model_dump(mode="json"))
            else:
                out.append(item)
        return json.dumps(out, default=str, indent=2)
    return json.dumps(result, default=str, indent=2)


async def _invoke(
    *,
    surface: str,
    tool_name: str,
    method_name: str,
    input_model: type[BaseModel],
    pinned_room_id: str | None,
    is_agent_room_bound: bool,
    is_human_room_bound: bool,
    ctx: AppContextType,
    kwargs: dict[str, Any],
) -> str:
    """The actual async dispatch body shared by every generated handler."""
    reset_agent_tools_cache(ctx)

    # Inject pinned room id BEFORE validation so the input model's chat_id
    # field is populated from the pin even though it is hidden from the
    # advertised schema.
    if pinned_room_id is not None and (is_agent_room_bound or is_human_room_bound):
        kwargs["chat_id"] = pinned_room_id

    try:
        validated = input_model.model_validate(kwargs)
    except ValidationError as exc:
        errors = "; ".join(f"{err['loc'][0]}: {err['msg']}" for err in exc.errors())
        raise ValueError(f"Invalid arguments for {tool_name}: {errors}") from exc

    call_kwargs = validated.model_dump(exclude_none=True, by_alias=False)

    if surface == "agent":
        # Agent tools: pull chat_id out of kwargs and scope AgentTools to it.
        if is_agent_room_bound:
            chat_id = call_kwargs.pop("chat_id", None)
            if not chat_id:
                raise ValueError(
                    f"{tool_name}: missing chat_id (or room_id) for room-bound tool"
                )
            tools_instance = get_agent_tools(ctx, chat_id)
        else:
            tools_instance = get_agent_tools(ctx, pinned_room_id)
    else:
        tools_instance = get_human_tools(ctx)

    if tools_instance is None:
        raise ValueError(
            f"{tool_name}: {surface} tools not available (SDK not installed or "
            "no credential configured for this scope)"
        )

    method = getattr(tools_instance, method_name, None)
    if method is None or not callable(method):
        raise RuntimeError(
            f"{tool_name}: method '{method_name}' not found on "
            f"{type(tools_instance).__name__}"
        )

    result = method(**call_kwargs)
    if inspect.isawaitable(result):
        result = await result

    return _serialize(result)


def make_handler(
    *,
    tool_name: str,
    surface: str,
    method_name: str,
    input_model: type[BaseModel],
    pinned_room_id: str | None,
    is_agent_room_bound: bool,
    is_human_room_bound: bool,
) -> Callable[..., Any]:
    """Return a dynamically-signatured async handler for ``mcp.add_tool``.

    FastMCP inspects ``__signature__`` / real parameters to build the tool's
    advertised JSON schema. We therefore synthesize a function whose
    parameter list matches the (post-extension, post-pin) input model's
    visible fields.
    """
    ctx_param_name = "ctx"

    async def _dispatch(**kwargs: Any) -> str:
        ctx = kwargs.pop(ctx_param_name)
        return await _invoke(
            surface=surface,
            tool_name=tool_name,
            method_name=method_name,
            input_model=input_model,
            pinned_room_id=pinned_room_id,
            is_agent_room_bound=is_agent_room_bound,
            is_human_room_bound=is_human_room_bound,
            ctx=ctx,
            kwargs=kwargs,
        )

    sig = _build_handler_signature(ctx_param_name, input_model)
    _dispatch.__signature__ = sig  # type: ignore[attr-defined]
    _dispatch.__name__ = tool_name
    # Description comes from the SDK input model's docstring (Phase 1 sets
    # these to the LLM-facing tool description).
    _dispatch.__doc__ = (input_model.__doc__ or "").strip() or f"Execute {tool_name}"

    # Build an Annotated annotation map for FastMCP's get_type_hints() call.
    # We can't rely on forward-referenced types since the model is dynamic,
    # so we stamp __annotations__ directly.
    annotations: dict[str, Any] = {ctx_param_name: AppContextType}
    for param in sig.parameters.values():
        if param.name == ctx_param_name:
            continue
        annotations[param.name] = param.annotation
    annotations["return"] = str
    _dispatch.__annotations__ = annotations

    return _dispatch


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def _classify_tool(
    definition: Any,  # ToolDefinition
) -> tuple[bool, bool]:
    """Return (is_agent_room_bound, is_human_room_bound) for a definition.

    Agent tools use the hard-coded ``AGENT_ROOM_BOUND_TOOL_NAMES`` set
    because the SDK input models don't carry a room field (see module
    docstring).

    Human tools are classified by inspecting ``input_model.model_fields``
    for ``chat_id`` — the Phase 1 human models carry it where applicable.
    """
    if definition.surface == "agent":
        return (definition.name in AGENT_ROOM_BOUND_TOOL_NAMES, False)
    if definition.surface == "human":
        has_chat_id = "chat_id" in definition.input_model.model_fields
        return (False, has_chat_id)
    return (False, False)


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP, config: Config) -> None:
    """Register every SDK-defined tool for the scopes in ``config.scope``.

    Delegates to ``iter_tool_definitions(surface=..., include_contacts=...,
    include_memory=...)`` for the source of truth on which tools are
    available, and translates each ``ToolDefinition`` into a FastMCP tool
    registration with an appropriate input schema (extended with chat_id
    for agent room-bound tools, schema-hidden pinned for pinned-mode
    room-bound tools on either surface).

    Safe to call after the handwritten ``tools.agent.*`` / ``tools.human.*``
    modules have been imported: SDK tool names are ``thenvoi_``-prefixed
    and do not collide with the legacy handwritten handler names.
    """
    try:
        from thenvoi.runtime.tools import iter_tool_definitions  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - import-time guard
        logger.warning(
            "register_tools(): Thenvoi SDK not available — skipping SDK-driven "
            "tool registration. Legacy handwritten handlers will still serve "
            "traffic. (%s)",
            exc,
        )
        return

    include_contacts = "contacts" in config.tools
    include_memory = "memory" in config.tools
    pinned_room_id = config.room_id

    iter_definitions: Any = iter_tool_definitions

    total = 0
    for surface in config.scope:
        definitions: list[Any] = list(
            iter_definitions(
                surface=surface,
                include_contacts=include_contacts,
                include_memory=include_memory,
            )
        )
        for definition in definitions:
            is_agent_room_bound, is_human_room_bound = _classify_tool(definition)

            # Build the per-tool input model (original, extended, or pinned).
            model: type[BaseModel] = definition.input_model
            if is_agent_room_bound:
                model = _extend_with_chat_id(model, pinned_room_id)
            elif is_human_room_bound and pinned_room_id is not None:
                model = _pin_existing_chat_id(model, pinned_room_id)

            handler = make_handler(
                tool_name=definition.name,
                surface=definition.surface,
                method_name=definition.method_name,
                input_model=model,
                pinned_room_id=pinned_room_id,
                is_agent_room_bound=is_agent_room_bound,
                is_human_room_bound=is_human_room_bound,
            )
            mcp.add_tool(handler, name=definition.name)
            total += 1

    logger.info("SDK-driven registrar: registered %d tools", total)


__all__ = [
    "AGENT_ROOM_BOUND_TOOL_NAMES",
    "make_handler",
    "register_tools",
]
