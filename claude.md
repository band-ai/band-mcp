# Band MCP Server

MCP (Model Context Protocol) server that connects AI assistants to the Band platform.

## Core Features

1. Connects AI assistants to Band's agent collaboration platform
2. Supports dual transport modes: STDIO (IDE integration) and SSE (remote deployments)
3. Conditional tool loading based on API key type (user vs agent)

## API Key Types

- `band_u_*` → User keys → Only human tools loaded
- `band_a_*` → Agent keys → Only agent tools loaded
- `band_*` → Legacy keys → All tools loaded

## Tool Template

```python
from band_mcp.shared import mcp, get_app_context, AppContextType

@mcp.tool()
def my_tool(ctx: AppContextType, param: str) -> str:
    """Tool description for AI assistants."""
    client = get_app_context(ctx).client
    # Use client.human_api.* or client.agent_api.*
    return "Success message"
```

## Repo-Specific Conventions

- Use the shared logger: `from band_mcp.shared import logger`
- All tools must use the `@mcp.tool()` decorator
- Tools must accept `ctx: AppContextType` as the first parameter
- Use `get_app_context(ctx).client` to access the Band API client
- Tools must return strings (success messages or JSON)

## Commands

```bash
# Install dependencies
uv sync

# Run the server
uv run band-mcp

# Run unit tests
uv run pytest tests/ --ignore=tests/integration/ -v

# Lint and format
uv run pre-commit run --all-files
```

## Transport Modes

- **STDIO** (default): `band-mcp` - For Cursor, Claude Desktop
- **SSE**: `band-mcp --transport sse --port 3000` - For Docker, cloud deployments

## Environment Variables

- `BAND_API_KEY`: Required API key
- `BAND_BASE_URL`: API base URL (default: https://app.band.ai)
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
