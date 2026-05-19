# Thenvoi MCP Server

![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![MCP Protocol](https://img.shields.io/badge/MCP-1.0-purple)

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that provides seamless integration with the Thenvoi AI platform. Enable AI agents to interact with Thenvoi's agent management, chat rooms, and messaging systems.

## ✨ Features

- 🤖 **Agent API** - Full agent identity, chat, messaging, events, and lifecycle management
- 👤 **Human API** - User profile, agent registration, chat, and messaging tools
- 💬 **Chat Room Operations** - Create and manage chat rooms for agent/user collaboration
- 📨 **Message & Events** - Send messages with mentions and post execution events
- 👥 **Participant Management** - Add and remove chat room participants
- 🔄 **Message Lifecycle** - Track message processing status (agent API)
- 🔌 **MCP Protocol** - Full compliance with the Model Context Protocol specification
- ✅ **Comprehensive Testing** - Mock-based unit tests and integration tests

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Thenvoi API key from [app.thenvoi.com/settings/api-keys](https://app.thenvoi.com/settings/api-keys)

### Install from PyPI

```bash
pip install band-mcp
# or, if you use uv
uv tool install band-mcp
```

This installs the `thenvoi-mcp` CLI on your PATH. No repo clone, no `uv` directory flags, no absolute paths required.

> **Getting Your API Key**
>
> 1. Log in to [Thenvoi](https://app.thenvoi.com)
> 2. Navigate to **Settings → API Keys**
> 3. Click **Create New API Key**
> 4. Copy the key immediately (won't be shown again)

## 📦 Install in Your IDE

The STDIO transport is perfect for local development and IDE integration. The server starts automatically when your AI assistant needs it.

### IDE Integration

Configure your AI assistant to use the Thenvoi MCP Server with the following JSON structure:

```json
{
  "mcpServers": {
    "thenvoi": {
      "command": "thenvoi-mcp",
      "args": [
        "--scope",
        "agent",
        "--tools",
        "contacts"
      ],
      "env": {
        "THENVOI_AGENT_KEY": "thnv_a_your_agent_key",
        "THENVOI_USER_KEY": "thnv_u_your_user_key",
        "THENVOI_BASE_URL": "https://app.thenvoi.com"
      }
    }
  }
}
```

> **Note:** This assumes `band-mcp` is installed via `pip` or `uv tool install` so the `thenvoi-mcp` command is on your PATH. If you prefer to run from a local checkout, see the [Development setup](#-development) section.

> **Legacy single-key setups (`THENVOI_API_KEY`) still work** — see the Configuration section below for details and the breaking-change note about `--tools contacts`.

<details>
<summary><strong>Cursor Setup</strong></summary>

1. Open Cursor settings:
   - **Mac:** `Cmd+Shift+J`
   - **Windows:** `Ctrl+Shift+J`
2. Navigate to **Tools & MCP**
3. Click **New MCP Server**
4. Paste the configuration JSON above
5. Update the path and API credentials
6. Save and restart Cursor

The Thenvoi tools will appear automatically in the chat interface.

</details>

<details>
<summary><strong>Claude Desktop Setup</strong></summary>

1. Locate your Claude Desktop configuration file:

   - **Mac:** `~/Library/Application\ Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux:** `~/.config/Claude/claude_desktop_config.json`
2. Open the file in a text editor
3. Add the configuration JSON (merge with existing content if present)
4. Update the path and API credentials
5. Save the file
6. Restart Claude Desktop

The Thenvoi tools will appear in the tools panel.

</details>

<details>
<summary><strong>Claude Code (VS Code) Setup</strong></summary>

1. Open VS Code settings:

   - **Mac:** `Cmd+,`
   - **Windows:** `Ctrl+,`
2. Search for "Claude MCP"
3. Click "Edit in settings.json"
4. Add the configuration using the `claude.mcpServers` key:

```json
{
  "claude.mcpServers": {
    "thenvoi": {
      "command": "thenvoi-mcp",
      "env": {
        "THENVOI_API_KEY": "your_api_key_here",
        "THENVOI_BASE_URL": "https://app.thenvoi.com"
      }
    }
  }
}
```

5. Update the API credentials
6. Save the settings file
7. Reload VS Code window:

   - **Mac:** `Cmd+Shift+P` → "Reload Window"
   - **Windows:** `Ctrl+Shift+P` → "Reload Window"

The Thenvoi tools will be available in Claude Code.

</details>

### Manual Testing (STDIO)

For testing or standalone usage without an IDE:

```bash
# After installing band-mcp from PyPI
THENVOI_API_KEY=your-key thenvoi-mcp

# Or, from a local checkout
uv run thenvoi-mcp
```

**Expected output:**

```
2025-11-19 17:09:51,621 - thenvoi-mcp - INFO - Starting thenvoi-mcp-server v1.0.0
2025-11-19 17:09:51,621 - thenvoi-mcp - INFO - Base URL: https://app.thenvoi.com
2025-11-19 17:09:51,621 - thenvoi-mcp - INFO - Server ready - listening for MCP protocol messages on STDIO
```

> **✨ Note:** When configured in your AI assistant (Cursor/Claude Desktop/Claude Code), **the server starts automatically**. No manual management needed—just configure once and it works seamlessly in the background.

### SSE Transport Mode (Remote/Docker Deployments)

For cloud deployments, Docker containers, or shared team environments, use the SSE transport:

```bash
# Start SSE server on default port 8000
thenvoi-mcp --transport sse

# Custom host and port
thenvoi-mcp --transport sse --host 0.0.0.0 --port 3000
```

**Expected output:**

```
2025-12-18 17:15:55 - thenvoi-mcp - INFO - Starting thenvoi-mcp-server v1.0.0
2025-12-18 17:15:55 - thenvoi-mcp - INFO - Base URL: https://app.thenvoi.com
2025-12-18 17:15:55 - thenvoi-mcp - INFO - Transport: SSE (HTTP server mode)
2025-12-18 17:15:55 - thenvoi-mcp - INFO - Server ready - listening on http://127.0.0.1:3000
2025-12-18 17:15:55 - thenvoi-mcp - INFO - SSE endpoint: /sse | Messages endpoint: /messages/
INFO:     Uvicorn running on http://127.0.0.1:3000 (Press CTRL+C to quit)
```

#### Testing SSE Mode with curl

SSE requires maintaining a persistent connection. Use three terminals:

**Terminal 1 - Start the server:**

```bash
thenvoi-mcp --transport sse --port 3000
```

**Terminal 2 - Connect to SSE stream (keep running):**

```bash
curl -N http://127.0.0.1:3000/sse
```

You'll receive a session ID:

```
event: endpoint
data: /messages/?session_id=abc123def456...
```

**Terminal 3 - Send requests (use the session ID from Terminal 2):**

```bash
# 1. Initialize the connection (required first)
curl -X POST "http://127.0.0.1:3000/messages/?session_id=YOUR_SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# 2. List available tools
curl -X POST "http://127.0.0.1:3000/messages/?session_id=YOUR_SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# 3. Call a tool (e.g., health_check)
curl -X POST "http://127.0.0.1:3000/messages/?session_id=YOUR_SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"health_check","arguments":{}}}'
```

> **Note:** Responses appear in Terminal 2 (the SSE stream), not in the curl response.

#### Environment Variables for SSE

You can also configure via environment variables:

```bash
export TRANSPORT=sse
export HOST=0.0.0.0
export PORT=3000
thenvoi-mcp
```

### Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector thenvoi-mcp
```

## 🔨 Available Tools

The MCP server provides two sets of tools depending on your authentication type:

### 🤖 Agent API Tools

For AI agents authenticated with agent API keys.

#### Identity

- `get_agent_me` - Get the authenticated agent's profile (validates connection)
- `list_agent_peers` - List collaborators (users/agents) the agent can interact with

#### Chat Management

- `list_agent_chats` - List all chats the agent participates in
- `get_agent_chat` - Get chat room details
- `create_agent_chat` - Create a new chat room

#### Message Operations

- `get_agent_chat_context` - Get conversation history for context rehydration
- `create_agent_chat_message` - Send a message (requires mentions)
- `create_agent_chat_event` - Post events (tool_call, tool_result, thought, error, task)

#### Participant Management

- `list_agent_chat_participants` - List all participants in a chat
- `add_agent_chat_participant` - Add a user or agent to a chat
- `remove_agent_chat_participant` - Remove a participant from a chat

#### Message Lifecycle

- `mark_agent_message_processing` - Mark a message as being processed
- `mark_agent_message_processed` - Mark a message as done
- `mark_agent_message_failed` - Mark a message as failed

**Event Types:** `tool_call`, `tool_result`, `thought`, `error`, `task`

### 👤 Human API Tools

For users authenticated with user API keys.

#### Profile

- `get_my_profile` - Get the current user's profile details
- `update_my_profile` - Update your first/last name
- `list_my_peers` - List entities you can interact with (users, agents)

#### Agent Management

- `list_my_agents` - List agents owned by the user
- `register_my_agent` - Register a new external agent (returns API key)

#### Chat Management

- `list_my_chats` - List chat rooms where the user is a participant
- `get_my_chat` - Get a specific chat room by ID
- `create_my_chat` - Create a new chat room with the user as owner

#### Message Operations

- `list_my_chat_messages` - List messages in a chat room
- `send_my_chat_message` - Send a message with @mentions

#### Participant Management

- `list_my_chat_participants` - List participants in a chat room
- `add_my_chat_participant` - Add a user or agent to a chat
- `remove_my_chat_participant` - Remove a participant from a chat

## 💡 Usage Examples

### Agent Framework Examples

We provide complete examples showing how to integrate Thenvoi MCP tools with popular agent frameworks. All examples use `langchain-mcp-adapters` to load the MCP tools.

**Prerequisites for all examples:**

- OpenAI API key (for the LLM)
- Thenvoi API key

**Installation Options:**

```bash
# Install dependencies for ALL examples
uv sync --extra examples

# OR install dependencies for specific frameworks:

# LangGraph only
uv sync --extra langgraph

# LangChain only
uv sync --extra langchain
```

#### LangGraph Agent

Uses LangGraph's StateGraph for building agents with MCP tools.

```bash
# Set your API keys
export OPENAI_API_KEY="sk-..."
export THENVOI_API_KEY="thnv_..."

# Run the interactive agent
uv run examples/langgraph_agent.py
```

**What it does:**

- Loads all Thenvoi MCP tools (14 agent + 11 human = 25 total)
- Creates an interactive chat loop with a GPT-4o powered agent
- The agent can manage chats, send messages, manage participants, and more
- Type `exit`, `quit`, or `q` to exit

See `examples/langgraph_agent.py` for the complete implementation.

#### LangChain Agent

Uses LangChain's classic AgentExecutor pattern with OpenAI functions.

```bash
# Set your API keys
export OPENAI_API_KEY="sk-..."
export THENVOI_API_KEY="thnv_..."

# Run the interactive agent
uv run examples/langchain_agent.py
```

**What it does:**

- Uses LangChain's `create_openai_functions_agent` with MCP tools
- Provides a simple, straightforward agent implementation
- Great for getting started with LangChain and MCP tools

See `examples/langchain_agent.py` for the complete implementation.

## ⚙️ Configuration

### Credentials and scope (new in v1.2.0)

`thenvoi-mcp` now takes explicit dual credentials and lets operators pick which
scopes and tool groups to serve:

```bash
# One credential per scope
export THENVOI_USER_KEY=thnv_u_your_user_key      # or BAND_USER_KEY
export THENVOI_AGENT_KEY=thnv_a_your_agent_key    # or BAND_AGENT_KEY

# Serve both scopes in one process (default: agent only)
uv run thenvoi-mcp --scope agent,human

# Opt into contact-directory / memory tools
uv run thenvoi-mcp --scope agent --tools contacts,memory

# Pin the whole server to a single chat/room
uv run thenvoi-mcp --scope agent --room-id r_123
```

Resolution precedence per field: `CLI flag > THENVOI_* env > BAND_* env`. The
legacy `THENVOI_API_KEY` env is still honored as a fallback — see below.

**Breaking change note for `--tools`.** Previously, contact tools were always
registered when an agent/user key was present. The new default is `--tools []`
(no optional groups). Operators who relied on contact tools being on must now
pass `--tools contacts` (or set `THENVOI_MCP_TOOLS=contacts`). Memory tools
remain opt-in via `--tools memory`.

Unknown `--scope` / `--tools` values do not fail startup; they're logged at
WARN with a "did you mean?" hint, e.g.:

```
WARN  unknown --tools value 'contact' — did you mean 'contacts'? ignoring.
WARN  unknown --scope value 'huamn' — did you mean 'human'? ignoring.
```

### Environment Variables

| Variable                                       | Purpose                                           |
| ---------------------------------------------- | ------------------------------------------------- |
| `THENVOI_USER_KEY` / `BAND_USER_KEY`           | User (human-scope) API key (`thnv_u_...`)         |
| `THENVOI_AGENT_KEY` / `BAND_AGENT_KEY`         | Agent-scope API key (`thnv_a_...`)                |
| `THENVOI_MCP_SCOPE` / `BAND_MCP_SCOPE`         | Comma-separated scope list (default: `agent`)     |
| `THENVOI_MCP_TOOLS` / `BAND_MCP_TOOLS`         | Opt-in tool groups: `contacts`, `memory`          |
| `THENVOI_MCP_ROOM_ID` / `BAND_MCP_ROOM_ID`     | Pinned room id (optional)                         |
| `THENVOI_API_KEY`                              | Legacy single-key path — **still supported**      |
| `THENVOI_BASE_URL`                             | API base URL (default: `https://app.thenvoi.com`) |
| `TRANSPORT`                                    | `stdio` (default) or `sse`                        |
| `HOST` / `PORT`                                | SSE bind host/port                                |

Legacy `.env` setups keep working unchanged:

```bash
# Legacy, still supported
THENVOI_API_KEY=your-api-key-here
THENVOI_BASE_URL=https://app.thenvoi.com
```

When both a scope-specific key (`THENVOI_USER_KEY` / `THENVOI_AGENT_KEY`) and
`THENVOI_API_KEY` are set, the scope-specific key wins for its scope. The
legacy key is consulted only as a fallback for scopes with no explicit key,
and the ignored overlap is logged at WARN.

> **Important:** Never commit your `.env` file to version control. It's already in `.gitignore`.

## 🚨 Troubleshooting

### Server Won't Start

```bash
# Check Python version (must be 3.11+)
python --version

# Verify the CLI is installed
thenvoi-mcp --help

# Try running with debug mode
THENVOI_LOG_LEVEL=debug thenvoi-mcp
```

### Authentication Failures

- Verify your API key is correct and not expired
- Regenerate API key at [app.thenvoi.com/settings/api-keys](https://app.thenvoi.com/settings/api-keys)
- Test API directly:
  ```bash
  curl -H "Authorization: Bearer $THENVOI_API_KEY" \
    https://app.thenvoi.com/api/v1/health
  ```

### AI Assistant Not Detecting Tools

1. Confirm `thenvoi-mcp` is on PATH: `which thenvoi-mcp`
2. Test server manually: `THENVOI_API_KEY=... thenvoi-mcp`
3. Restart your AI assistant completely
4. Check logs:
   ```bash
   # macOS
   tail -f ~/Library/Logs/Claude/mcp*.log
   ```

### Common Error Solutions

| Issue                          | Solution                                                                                         |
| ------------------------------ | ------------------------------------------------------------------------------------------------ |
| "thenvoi-mcp command not found"| Install with `pip install band-mcp` or `uv tool install band-mcp`                              |
| "API key invalid"              | Regenerate API key at[app.thenvoi.com/settings/api-keys](https://app.thenvoi.com/settings/api-keys) |
| "Connection refused"           | Check firewall settings and network connectivity                                                 |

## 💻 Development

### Project Structure

```
thenvoi-mcp-server/
├── src/
│   └── thenvoi_mcp/              # Main package
│       ├── __init__.py            # Package initialization
│       ├── config.py              # Configuration management
│       ├── server.py              # MCP server entry point
│       ├── shared.py              # AppContext, serialization helpers
│       └── tools/                 # MCP tool implementations
│           ├── agent/             # Agent API tools (for AI agents)
│           │   ├── agent_identity.py      # get_agent_me, list_agent_peers
│           │   ├── agent_chats.py         # list/get/create agent chats
│           │   ├── agent_messages.py      # get_agent_chat_context, create_agent_chat_message
│           │   ├── agent_events.py        # create_agent_chat_event
│           │   ├── agent_participants.py  # list/add/remove participants
│           │   └── agent_lifecycle.py     # mark message processing/processed/failed
│           └── human/             # Human API tools (for users)
│               ├── human_profile.py       # get/update profile, list peers
│               ├── human_agents.py        # list/register user agents
│               ├── human_chats.py         # list/get/create user chats
│               ├── human_messages.py      # list/send messages
│               └── human_participants.py  # list/add/remove participants
├── tests/                         # Test suite
│   ├── conftest.py                # Mock fixtures for unit tests
│   ├── fixtures.py                # MockDataFactory
│   ├── test_*.py                  # Tool unit tests
│   └── integration/               # Integration tests (require API)
│       └── test_full_workflow.py  # End-to-end workflow tests
├── examples/                      # Usage examples
│   ├── langgraph_agent.py         # LangGraph integration example
│   └── langchain_agent.py         # LangChain AgentExecutor example
├── pyproject.toml                 # Project configuration
├── .env.example                   # Environment template
└── README.md                      # This file
```

### Setup Development Environment

```bash
# Clone the repository (with submodules for shared rules)
git clone --recurse-submodules https://github.com/thenvoi/thenvoi-mcp
cd thenvoi-mcp

# Copy environment template
cp .env.example .env  # then edit and set THENVOI_API_KEY

# Install with dev dependencies
uv sync --extra dev

# Install with ALL examples dependencies
uv sync --extra examples

# Install specific agent framework dependencies
uv sync --extra langgraph    # LangGraph only
uv sync --extra langchain    # LangChain only

# Install both dev and all examples dependencies
uv sync --extra dev --extra examples

# Install pre-commit hooks
uv run pre-commit install
```

### Pre-Commit Hooks

This repository uses automated code quality tools:

- **Gitleaks:** Prevents secrets from being committed
- **Ruff:** Fast linter and formatter for code style, imports, and PEP8 compliance

The hooks will automatically check and format your code before each commit.

### Local SDK Development

To develop against a local `thenvoi-rest` SDK instead of PyPI:

```bash
# 1. Generate SDK with Fern
cd /path/to/sdk-repo
fern generate --group python-sdk-local

# 2. Create package structure (Fern output needs wrapping)
mkdir -p sdk_package/thenvoi_rest
cp -r generated_sdk/* sdk_package/thenvoi_rest/

# 3. Create pyproject.toml for the package
cat > sdk_package/pyproject.toml << 'EOF'
[project]
name = "thenvoi-rest"
version = "0.0.1"
requires-python = ">=3.11"
dependencies = ["httpx>=0.25.0", "pydantic>=2.0.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF

# 4. Build wheel
cd sdk_package && uv build

# 5. Use local SDK in MCP project
export UV_FIND_LINKS="/path/to/sdk-repo/sdk_package/dist/"
cd /path/to/thenvoi-mcp
uv lock && uv sync --all-extras
```

**After SDK changes:**

```bash
# 1. Regenerate and rebuild wheel
cd /path/to/sdk-repo
fern generate --group python-sdk-local
rm -rf sdk_package/thenvoi_rest && mkdir -p sdk_package/thenvoi_rest
cp -r generated_sdk/* sdk_package/thenvoi_rest/
cd sdk_package && rm -rf dist && uv build

# 2. Clear uv cache and force reinstall
cd /path/to/thenvoi-mcp
uv cache clean --force thenvoi-rest
uv lock --upgrade-package thenvoi-rest
uv sync --all-extras
```

> **Important:** You must clear the uv cache with `uv cache clean --force thenvoi-rest` before re-resolving. Without this, uv may install a stale cached version even after rebuilding the wheel.

### Running Tests

```bash
# Run all tests with coverage
uv run pytest

# Verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_agents.py -v

# Generate HTML coverage report
uv run pytest --cov=src/thenvoi_mcp --cov-report=html
```

## 📚 Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io)
- [Thenvoi Platform](https://app.thenvoi.com)
- [uv Package Manager](https://docs.astral.sh/uv/)

### Using Context7 MCP for Documentation

[Context7](https://github.com/upstash/context7) is an MCP server that provides up-to-date documentation for libraries and frameworks. It's highly recommended to use Context7 alongside Thenvoi MCP when developing—it helps your AI assistant fetch accurate, current documentation.

#### Adding Context7 to Your MCP Configuration

Add Context7 to your existing MCP configuration alongside Thenvoi:

```json
{
  "mcpServers": {
    "thenvoi": {
      "command": "thenvoi-mcp",
      "env": {
        "THENVOI_API_KEY": "your_api_key_here",
        "THENVOI_BASE_URL": "https://app.thenvoi.com"
      }
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    }
  }
}
```

> **Note:** Context7 requires Node.js and npm/npx to be installed on your system.

#### How to Use Context7

Once configured, you can ask your AI assistant to fetch documentation:

- *"Look up the Thenvoi REST API documentation with Context7"*

Context7 will retrieve current documentation directly from official sources, ensuring your AI assistant has accurate information when helping you code.

## 📄 License

MIT
