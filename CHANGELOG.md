# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New CLI flags: `--user-key`, `--agent-key`, `--room-id`, `--scope`, `--tools` (INT-350).
- Matching env vars: `THENVOI_USER_KEY` / `BAND_USER_KEY`, `THENVOI_AGENT_KEY` / `BAND_AGENT_KEY`, `THENVOI_MCP_ROOM_ID` / `BAND_MCP_ROOM_ID`, `THENVOI_MCP_SCOPE` / `BAND_MCP_SCOPE`, `THENVOI_MCP_TOOLS` / `BAND_MCP_TOOLS` (INT-350).
- SDK-driven tool registrar: tool definitions now live in `thenvoi-sdk-python` and are consumed by `thenvoi-mcp` via `iter_tool_definitions()`. Single source of truth for both agent and human tool logic (INT-351).
- Room pinning: `--room-id` binds the MCP server to a single chat/room; the room field is hidden from the advertised JSON schema and injected at call time (INT-351).
- Runtime dependency on `thenvoi-sdk >= 0.3.0` (provides `HumanTools`, `AgentTools`, and `iter_tool_definitions`). Missing the SDK now raises `ConfigError` at startup with exit code 2 instead of silently serving zero tools (INT-352).

### Changed
- **BREAKING**: Contact tools are no longer registered by default. Operators who relied on implicit contacts (either through `THENVOI_API_KEY` or the old MCP default) must pass `--tools contacts`. Memory tools remain opt-in via `--tools memory` as before.
- `health_check` now uses the async REST clients on `AppContext` (`human_rest` preferred, falls back to `agent_rest`). The tool name and response shape are unchanged.

### Migration — tool name changes

**BREAKING** for downstream MCP consumers that pin tool names (Claude Desktop, Cursor, LangChain `tools=[...]` whitelists, etc.). Every surviving tool was prefixed with `thenvoi_`, several agent tools got semantic renames, and a block of agent-surface tools was removed outright.

Agent tools removed (no replacement at the MCP layer):

| Old tool | Why it went away |
| --- | --- |
| `get_agent_me` | Agent identity travels with the credential; remove from consumers. |
| `list_agent_chats` | `AgentTools` is room-scoped; the MCP no longer enumerates rooms on the agent surface. |
| `get_agent_chat` | Same as above. |
| `get_agent_chat_context` | Context is fetched via the SDK's room-scoped helpers. |
| `get_agent_next_message` | Agents receive messages via the SDK's websocket subscription, not a polling tool. |
| `mark_agent_message_processing` | Lifecycle status handled by the SDK runtime. |
| `mark_agent_message_processed` | Same as above. |
| `mark_agent_message_failed` | Same as above. |

Agent tools renamed:

| Old tool | New tool |
| --- | --- |
| `create_agent_chat` | `thenvoi_create_chatroom` |
| `create_agent_chat_message` | `thenvoi_send_message` |
| `create_agent_chat_event` | `thenvoi_send_event` |
| `list_agent_chat_participants` | `thenvoi_get_participants` |
| `add_agent_chat_participant` | `thenvoi_add_participant` |
| `remove_agent_chat_participant` | `thenvoi_remove_participant` |
| `list_agent_peers` | `thenvoi_lookup_peers` |
| `list_agent_contacts` | `thenvoi_list_contacts` |
| `add_agent_contact` | `thenvoi_add_contact` |
| `remove_agent_contact` | `thenvoi_remove_contact` |
| `list_agent_contact_requests` | `thenvoi_list_contact_requests` |
| `respond_to_agent_contact_request` | `thenvoi_respond_contact_request` |

Human tools with semantic renames (beyond the `thenvoi_` prefix):

| Old tool | New tool |
| --- | --- |
| `create_my_chat` | `thenvoi_create_my_chat_room` |
| `get_my_chat` | `thenvoi_get_my_chat_room` |

Human tools prefixed only (`thenvoi_<old_name>`):
`list_my_agents`, `register_my_agent`, `list_my_chats`, `list_my_chat_messages`, `send_my_chat_message`, `list_my_chat_participants`, `add_my_chat_participant`, `remove_my_chat_participant`, `get_my_profile`, `update_my_profile`, `list_my_peers`.

Contact tools on the human surface (opt-in via `--tools contacts`):
`thenvoi_list_my_contacts`, `thenvoi_create_contact_request`, `thenvoi_list_received_contact_requests`, `thenvoi_list_sent_contact_requests`, `thenvoi_approve_contact_request`, `thenvoi_reject_contact_request`, `thenvoi_cancel_contact_request`, `thenvoi_resolve_handle`, `thenvoi_remove_my_contact`.

Memory tools (opt-in via `--tools memory`):
- Agent: `thenvoi_list_memories`, `thenvoi_store_memory`, `thenvoi_get_memory`, `thenvoi_supersede_memory`, `thenvoi_archive_memory`.
- Human: `thenvoi_list_user_memories`, `thenvoi_get_user_memory`, `thenvoi_supersede_user_memory`, `thenvoi_archive_user_memory`, `thenvoi_restore_user_memory`, `thenvoi_delete_user_memory`.

### Removed
- Handwritten FastMCP handlers under `src/thenvoi_mcp/tools/agent/` (8 files) and `src/thenvoi_mcp/tools/human/` (7 files). Replaced by the SDK-driven registrar (INT-352).
- Per-tool unit tests under `tests/` (13 files) — coverage subsumed by `tests/integration/test_forwarding.py` (Phase 3) and `tests/runtime/test_human_tools.py` in `thenvoi-sdk-python` (Phase 1) (INT-352).
- `tests/integration/test_smoke.py`, `tests/integration/test_error_cases.py`, `tests/integration/test_full_workflow.py` and the `tests/conftest_integration.py` fixtures — live-API smoke suites against the deleted handwritten handlers. Registrar transport concerns are covered by `test_forwarding.py`; SDK method coverage lives in `thenvoi-sdk-python` (INT-352).
- `AppContext.client` (legacy sync `RestClient`). Replaced by `AppContext.human_rest` / `.agent_rest` (INT-352).
- `get_key_type`, `_choose_legacy_key_type`, `load_tools` in `server.py` — the legacy prefix-inference scaffolding that fed the handwritten handlers (INT-352).

### Compatibility
- `THENVOI_API_KEY` is still supported as a legacy fallback; the new `--user-key` / `--agent-key` flags take precedence when set. When `THENVOI_API_KEY` is the only credential, `config.scope` is rewritten from the key's capabilities so the advertised tool surface matches what the key can actually call.

## [1.2.0](https://github.com/thenvoi/thenvoi-mcp/compare/thenvoi-mcp-v1.1.1...thenvoi-mcp-v1.2.0) (2026-04-05)


### Features

* Add contacts MCP tools + migrate to REST client v0.0.4 (INT-163) ([#80](https://github.com/thenvoi/thenvoi-mcp/issues/80)) ([4c05c20](https://github.com/thenvoi/thenvoi-mcp/commit/4c05c20e592fba60571f4be7225515e8fb53d028))
* Add transport security configuration for Docker/remote deployments ([#75](https://github.com/thenvoi/thenvoi-mcp/issues/75)) ([8de1a19](https://github.com/thenvoi/thenvoi-mcp/commit/8de1a1941fa0a0fbcc80043366e5fc9530417aa7))


### Bug Fixes

* **ci:** add ci scope to allowed PR title scopes ([4ed73c3](https://github.com/thenvoi/thenvoi-mcp/commit/4ed73c30fefe8a349b2cf5ec1072bd39a17b3e26))
* **ci:** skip PR title validation for dependabot ([4cf3c17](https://github.com/thenvoi/thenvoi-mcp/commit/4cf3c175c2a79390a05805a9cadcf159a581f54a))
* **ci:** skip PR title validation for dependabot ([54c5aec](https://github.com/thenvoi/thenvoi-mcp/commit/54c5aecfad58f276b631b26af5be2aff5ad53fc0))
* **ci:** Target main branch for release-please PRs ([#69](https://github.com/thenvoi/thenvoi-mcp/issues/69)) ([0c70040](https://github.com/thenvoi/thenvoi-mcp/commit/0c700401ad186eca5f0d5f4df2f2d637f5a7a36d))
* **deps:** Update mcp SDK to &gt;=1.23.0 to fix DNS rebinding vulnerability ([#77](https://github.com/thenvoi/thenvoi-mcp/issues/77)) ([3f75692](https://github.com/thenvoi/thenvoi-mcp/commit/3f7569285d08e65b9f131091db7cb1d96440b86a))
* **deps:** Upgrade langchain-core to &gt;=1.2.5 (INT-124) ([#78](https://github.com/thenvoi/thenvoi-mcp/issues/78)) ([f050b82](https://github.com/thenvoi/thenvoi-mcp/commit/f050b82c111ed88f370e7d82795eca1e02c9d2ba))
* Handle HTTP 204 as success in get_agent_next_message (INT-183) ([#82](https://github.com/thenvoi/thenvoi-mcp/issues/82)) ([511d8d7](https://github.com/thenvoi/thenvoi-mcp/commit/511d8d730790a1c4afe41a4434f2d21c895c1eb6))
* Omit None values from API request bodies (INT-182) ([#81](https://github.com/thenvoi/thenvoi-mcp/issues/81)) ([7544462](https://github.com/thenvoi/thenvoi-mcp/commit/75444622279f04b9ddf2e0db4819dcfbd6cb93ac))


### Documentation

* add naming conventions and PR title validation ([9437687](https://github.com/thenvoi/thenvoi-mcp/commit/94376879114d4f7d419a64479b2d1716f96863b4))
* add naming conventions and PR title validation ([f212529](https://github.com/thenvoi/thenvoi-mcp/commit/f212529600c0197d6c7b1aebd3a95e0c6b30f7b7))
* Add shared Claude rules via git submodule ([296cbe4](https://github.com/thenvoi/thenvoi-mcp/commit/296cbe498e088dcd10489a665571bf38fdede5ca))
* Add shared Claude rules via git submodule ([8f6f5a6](https://github.com/thenvoi/thenvoi-mcp/commit/8f6f5a6accbc55e73041aaab7d7509bf72fc6b42))
* Clean up CLAUDE.md to remove duplicated shared rules ([a7eaa1b](https://github.com/thenvoi/thenvoi-mcp/commit/a7eaa1bb16e97ea324e6ce938eecb529da76573e))
* Update Python version requirement to 3.11 ([#64](https://github.com/thenvoi/thenvoi-mcp/issues/64)) ([d28da44](https://github.com/thenvoi/thenvoi-mcp/commit/d28da448cdc2eee5cf9880ca3354c56b5df95f8c))

## [1.1.1](https://github.com/thenvoi/thenvoi-mcp/compare/thenvoi-mcp-v1.1.0...thenvoi-mcp-v1.1.1) (2026-01-07)


### Bug Fixes

* remove PyPI publishing from release workflow ([8ac41e4](https://github.com/thenvoi/thenvoi-mcp/commit/8ac41e43826d8801e41bc8543bda6f1efff3b3ae))
* remove PyPI publishing from release workflow ([2aa8296](https://github.com/thenvoi/thenvoi-mcp/commit/2aa8296ab72946329b22a8eba86a8ec440e28955))

## [1.1.0](https://github.com/thenvoi/thenvoi-mcp/compare/thenvoi-mcp-v1.0.0...thenvoi-mcp-v1.1.0) (2026-01-07)


### Features

* **ci:** add changelog generation with semantic versioning ([b5f2cfe](https://github.com/thenvoi/thenvoi-mcp/commit/b5f2cfe52b968d8742372a944d29d714289523f2))


### Bug Fixes

* **ci:** move checkout before token generation ([885da5d](https://github.com/thenvoi/thenvoi-mcp/commit/885da5da11c4907f20cbaa39ca76e912da7d69b9))

## [Unreleased]

## [1.0.0] - 2024-01-01

### Added

- Initial MCP server implementation for Thenvoi integration
- Tools for managing agents (`list_agents`, `get_agent`)
- Tools for managing chats (`list_chats`, `get_chat`, `create_chat`)
- Tools for managing messages (`list_messages`, `send_message`)
- Tools for managing participants (`list_participants`, `add_participant`)
- SSE server support for remote deployments
- Pre-commit hooks for code quality (ruff, gitleaks, pyrefly)
- Comprehensive test suite with pytest
- LangGraph and LangChain integration examples

[Unreleased]: https://github.com/thenvoi/thenvoi-mcp/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/thenvoi/thenvoi-mcp/releases/tag/v1.0.0
