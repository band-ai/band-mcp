# Contributing to Band MCP

Thank you for your interest in contributing to Band MCP! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Initial Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/band-mcp.git
   cd band-mcp
   ```
3. Add upstream remote:
   ```bash
   git remote add upstream https://github.com/thenvoi/band-mcp.git
   ```
4. Install dependencies:
   ```bash
   uv sync --all-extras
   ```
5. Set up pre-commit hooks:
   ```bash
   uv run pre-commit install
   uv run pre-commit install --hook-type commit-msg
   ```
6. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Development Workflow

1. Create a feature branch from `develop`:
   ```bash
   git checkout develop
   git pull upstream develop
   git checkout -b feat/your-feature-name
   # or fix/your-bug-fix for bug fixes
   ```

2. Make your changes following the code standards below

3. Run tests:
   ```bash
   # Unit tests
   uv run pytest tests/ --ignore=tests/integration/ -v

   # Integration tests (requires BAND_API_KEY)
   uv run pytest tests/integration/ -v -s --no-cov
   ```

4. Run pre-commit checks:
   ```bash
   uv run pre-commit run --all-files
   ```

5. Commit your changes using [Conventional Commits](https://www.conventionalcommits.org/):
   ```bash
   git commit -m "feat: add new feature description"
   # or
   git commit -m "fix: resolve issue description"
   ```

6. Push and create a pull request to `develop`

## Code Standards

### Style Guidelines

- **Formatter/Linter**: Ruff (88-character line limit)
- **Type Checker**: Pyrefly
- **Secret Detection**: Gitleaks

All formatting is enforced via pre-commit hooks.

### Type Annotations

- Use type hints for all function parameters and return types
- Use modern Python syntax:
  ```python
  # Good
  def process(items: list[str]) -> dict[str, int]:
      ...

  def get_value(key: str) -> str | None:
      ...

  # Avoid
  from typing import List, Dict, Optional
  def process(items: List[str]) -> Dict[str, int]:
      ...
  ```

### Logging

Never use `print()` statements. Always use the shared logger:
```python
from thenvoi_mcp.shared import logger

logger.info("Processing request")
logger.error("Failed to connect", exc_info=True)
```

### Writing Tools

All MCP tools must follow this pattern:
```python
from thenvoi_mcp.shared import mcp, get_app_context, AppContextType

@mcp.tool()
def my_tool(ctx: AppContextType, param: str) -> str:
    """Tool description for AI assistants.

    Provide a clear description of what the tool does,
    as this will be shown to AI assistants.
    """
    client = get_app_context(ctx).client
    # Use client.human_api.* or client.agent_api.*
    return "Success message or JSON string"
```

Key requirements:
- Use `@mcp.tool()` decorator
- First parameter must be `ctx: AppContextType`
- Return type must be `str`
- Include a descriptive docstring

### Imports

Use absolute imports from `thenvoi_mcp`:
```python
# Good
from thenvoi_mcp.shared import mcp, logger
from thenvoi_mcp.config import Settings

# Avoid
from .shared import mcp
from ..config import Settings
```

## Testing

### Running Tests

```bash
# All unit tests with coverage
uv run pytest tests/ --ignore=tests/integration/

# Specific test
uv run pytest tests/ -k "test_name"

# Integration tests (requires API key)
uv run pytest tests/integration/ -v -s --no-cov
```

### Writing Tests

This project uses the shared `thenvoi-testing-python` package for test fixtures and utilities.

**Unit Tests:**
- Place in `tests/`
- Use fixtures from `thenvoi_testing` (auto-loaded via pytest plugin)
- Use MCP-specific fixtures from `tests/conftest.py`

```python
from thenvoi_testing.factories import factory

def test_my_tool(mock_ctx, mock_agent_api):
    """Test a tool with mocked API client."""
    # Create mock response data using factory
    chat = factory.chat_room(id="chat-123", title="Test Chat")
    mock_agent_api.list_agent_chats.return_value = factory.list_response([chat])

    # Call the tool
    result = list_agent_chats(mock_ctx)

    # Assert on result
    assert "chat-123" in result
```

**Available Fixtures:**
- `mock_ctx` - MCP context with mocked API client (from `tests/conftest.py`)
- `mock_agent_api` - Mocked agent API namespace (from `thenvoi_testing`)
- `mock_api_client` - Full mocked API client (from `thenvoi_testing`)
- `factory` - MockDataFactory for creating test data (from `thenvoi_testing`)

**Integration Tests:**
- Place in `tests/integration/`
- Require `BAND_API_KEY` environment variable (set in `.env.test`)
- Use `@requires_api` decorator to skip if API key is not set

## Pull Request Guidelines

1. Ensure all tests pass
2. Ensure pre-commit checks pass
3. Update documentation if needed
4. Fill out the PR template completely
5. Request review from maintainers
6. Address any feedback

## Naming Conventions

### Issue Titles

Use component prefixes to categorize issues:

```
[Component] Brief description
```

**Components:**
- `[API]` - API client and endpoints
- `[Tools]` - MCP tools
- `[Auth]` - Authentication and API keys
- `[Transport]` - STDIO/SSE transport modes
- `[Config]` - Configuration and settings
- `[Docs]` - Documentation
- `[CI]` - CI/CD and workflows
- `[Performance]` - Performance improvements

**Examples:**
- `[Tools] Add bulk message sending tool`
- `[API] Fix timeout handling in chat endpoint`
- `[Auth] Support rotating API keys`

### PR Titles

Follow Conventional Commits format:

```
type(scope): description
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples:**
- `feat(tools): add new chat management tool`
- `fix(api): resolve connection timeout issue`
- `docs: update README with usage examples`

PR titles are validated by CI - PRs with invalid titles will fail the check.

## Branch Naming

- `feat/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes

## Commit Messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/) enforced by Commitizen:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

## Release Process

Releases follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking API changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

## Questions?

If you have questions or need help, please open an issue on GitHub.
