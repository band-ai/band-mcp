# Thenvoi MCP Server

MCP (Model Context Protocol) server that connects AI assistants to the Thenvoi platform.

## Core Features

1. Connects AI assistants to Thenvoi's agent collaboration platform
2. Supports dual transport modes: STDIO (IDE integration) and SSE (remote deployments)
3. Conditional tool loading based on API key type (user vs agent)

## API Key Types

- `thnv_u_*` → User keys → Only human tools loaded
- `thnv_a_*` → Agent keys → Only agent tools loaded
- `thnv_*` → Legacy keys → All tools loaded

## Tool Registration

MCP platform tools are registered through `thenvoi_mcp.tools.registrar.register_tools`, which consumes `thenvoi.runtime.tools.iter_tool_definitions` from the SDK. Do not add handwritten per-tool handlers under `tools/agent/` or `tools/human/`; add or update the SDK tool definition instead, then adapt the registrar only when MCP transport behavior differs from the SDK method contract.

The only handwritten MCP tool in this repo is `health_check`, which is a server diagnostic rather than a platform SDK tool.

## Repo-Specific Conventions

- Use the shared logger: `from thenvoi_mcp.shared import logger`
- Platform tools must come from the SDK-driven registrar, not `@mcp.tool()` decorators
- Runtime dependencies live on `AppContext` as `human_rest`, `agent_rest`, and `human_tools`; agent tools are constructed with `get_agent_tools(ctx, room_id)`
- Tools must return strings (success messages or JSON)

## Commands

```bash
# Install dependencies
uv sync

# Run the server
uv run thenvoi-mcp

# Run unit tests
uv run pytest tests/ --ignore=tests/integration/ -v

# Lint and format
uv run pre-commit run --all-files
```

## Transport Modes

- **STDIO** (default): `thenvoi-mcp` - For Cursor, Claude Desktop
- **SSE**: `thenvoi-mcp --transport sse --port 3000` - For Docker, cloud deployments

## Environment Variables

- `THENVOI_API_KEY`: Required API key
- `THENVOI_BASE_URL`: API base URL (default: https://app.thenvoi.com)
- `TRANSPORT`: stdio or sse (default: stdio)
- `HOST`: SSE host (default: 127.0.0.1)
- `PORT`: SSE port (default: 8000)

### Transport Security (DNS Rebinding Protection)

- `ENABLE_DNS_REBINDING_PROTECTION`: Enable DNS rebinding protection (default: true)
- `ALLOWED_HOSTS`: JSON array of allowed Host header values (default: [])
- `ALLOWED_ORIGINS`: JSON array of allowed Origin header values (default: [])

**Important for Docker/remote deployments:** When `ENABLE_DNS_REBINDING_PROTECTION=true` (default),
requests are rejected unless the Host header matches an entry in `ALLOWED_HOSTS`.

```bash
# Whitelist specific hosts for Docker/remote deployments
ALLOWED_HOSTS='["localhost:*","127.0.0.1:*","host.docker.internal:*"]'
```

Wildcard port matching is supported: `"localhost:*"` matches `localhost:8000`, `localhost:3000`, etc.

## Git Workflow

- Default branch: `dev` (PRs target here)
