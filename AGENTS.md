# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is an **MCP (Model Context Protocol) server** that provides AI assistants with tools to interact with:
- **DCI (Distributed CI)**: Red Hat's distributed continuous integration system
- **GitHub**: Issues, PRs, and repository information
- **Jira**: Ticket data with comments and changelog
- **Google Drive**: Document creation from DCI reports
- **Red Hat Support Cases**: Case data from the Customer Portal

The server is built with **FastMCP** and supports multiple transport modes (stdio for CLI/IDE integration, SSE/HTTP for web applications).

## Architecture

### Core Components

1. **Services** (`mcp_server/services/`): Business logic for external APIs
   - All DCI services inherit from `DCIBaseService` which handles authentication (API key or login/password)
   - Each service encapsulates API interactions for a specific domain (jobs, components, files, etc.)
   - External services: `github_service.py`, `jira_service.py`, `google_drive_service.py`, `support_case_service.py`

2. **Tools** (`mcp_server/tools/`): MCP tool definitions that wrap service methods
   - Tools are registered conditionally in `mcp_server/main.py` based on available credentials
   - Each tool file exports a `register_*_tools(mcp)` function
   - Naming convention: `<domain>_tools.py` (e.g., `job_tools.py`, `github_tools.py`)

3. **Prompts** (`mcp_server/prompts/`): Parameterized prompts for common workflows
   - `/dci/rca <job_id>`: Root cause analysis workflow
   - `/dci/weekly <subject>`: 7-day analysis report
   - `/dci/biweekly <subject>`: 14-day analysis report
   - `/dci/quarterly <remoteci>`: 3-month comprehensive analysis with statistics

4. **Entry Points**:
   - `main.py`: CLI entry point that reads `MCP_TRANSPORT` env var (stdio|sse|http)
   - `mcp_server/main.py`: Creates and configures the FastMCP server instance

### Transport Modes

- **stdio**: Default mode for CLI/IDE integration (Cursor, VS Code, etc.). MCP JSON-RPC over stdin/stdout.
- **SSE/HTTP**: Web-based mode for applications needing HTTP endpoints. Starts FastAPI server on `MCP_HOST:MCP_PORT`.

Set via `MCP_TRANSPORT=stdio|sse|http` environment variable.

### Conditional Tool Registration

Tools are only registered when their required credentials are available:
- DCI tools: `DCI_CLIENT_ID` + `DCI_API_SECRET` (or `DCI_LOGIN` + `DCI_PASSWORD`)
- GitHub tools: `GITHUB_TOKEN`
- Jira tools: `JIRA_API_TOKEN` + `JIRA_EMAIL` + `JIRA_URL`
- Google Drive tools: `GOOGLE_CREDENTIALS_PATH` + `GOOGLE_TOKEN_PATH`
- Support Case tools: `OFFLINE_TOKEN`

This allows the server to run with only a subset of integrations configured.

# Repository Guidelines

## Project Structure & Module Organization

- Source: `mcp_server/` (entry: `mcp_server/main.py`, services under `mcp_server/services/`, tools under `mcp_server/tools/`, utils under `mcp_server/utils/`, prompts under `mcp_server/prompts/`).
- CLI entry: `main.py` (select transport via `MCP_TRANSPORT=stdio|sse`).
- Tests: `tests/` (unit/integration markers; see `pytest.ini`).
- Config: `.env` (see `env.example`), project config in `pyproject.toml`.

## Build, Test, and Development Commands

- Setup env: `uv sync && source .venv/bin/activate`.
- Run server (stdio): `uv run main.py`.
- Run server (SSE): `MCP_TRANSPORT=sse uv run main.py` (SSE endpoint at `http://127.0.0.1:8000/sse/`).
- All checks: `bash scripts/run-checks.sh` (runs formatting, linting, and tests).
- Selective checks: `bash scripts/run-checks.sh --format` or `--lint` or `--test`.
- Format code: `uv run ruff format .` (auto-fix formatting issues).
- Sort imports: `uv run isort .` (auto-fix import order).
- Lint: `uv run ruff check .` or `uv run ruff check --fix .` (auto-fix linting issues).
- Tests: `uv run pytest -v` or `uv run pytest -m "not slow"`.
- Single test: `uv run pytest tests/test_file.py::test_function -v`.
- Test with markers: `uv run pytest -m unit` or `-m integration`.

## Python Dependency Management

**ALWAYS** make Python dependency changes in `pyproject.toml` and use `uv` to make them effective:

1. **Add dependencies**: Edit `pyproject.toml` under the `dependencies` list
2. **Remove dependencies**: Remove from `pyproject.toml` dependencies list
3. **Update dependencies**: Modify version constraints in `pyproject.toml`
4. **Apply changes**: Run `uv sync` to update the virtual environment and lock file

### Example workflow:

```bash
# 1. Edit pyproject.toml to add/remove/update dependencies
# 2. Run uv sync to apply changes
uv sync
# 3. Verify the changes took effect
uv run python -c "import new_package; print('Success')"
```

### Never:

- Use `pip install` directly
- Edit `uv.lock` manually
- Use `requirements.txt` (this project uses `pyproject.toml`)

### Always:

- Use `uv add <package>` for adding new dependencies
- Use `uv remove <package>` for removing dependencies
- Use `uv sync` to sync the environment with pyproject.toml
- Keep `uv.lock` in version control for reproducible builds

## Code Quality and Pre-commit Checks

**ALWAYS** ensure code quality by running checks after modifications:

1. **After any code changes**: Run `bash scripts/run-checks.sh`
2. **Before committing**: Ensure all checks pass
3. **Format code**: Use Ruff format and isort for consistent formatting
4. **Lint code**: Use Ruff for fast linting and auto-fixing
5. **Tests**: Ensure all tests pass

### Example workflow:

```bash
# 1. Make your code changes
# 2. Run comprehensive checks
bash scripts/run-checks.sh

# 3. If issues found, fix them:
./.venv/bin/python -m ruff format .       # Format code
./.venv/bin/python -m isort .             # Sort imports
./.venv/bin/python -m ruff check --fix .  # Fix linting issues

# 4. Run checks again to ensure everything passes
bash scripts/run-checks.sh
```

### Pre-commit Hooks (Optional):

```bash
# Install pre-commit hooks
./.venv/bin/python -m pre_commit install

# Run pre-commit on all files
./.venv/bin/python -m pre_commit run --all-files
```

### Never:

- Commit code without running quality checks
- Ignore linting or formatting errors
- Leave formatting inconsistencies

### Always:

- Run `bash scripts/run-checks.sh` after code changes
- Fix any issues found by the checks
- Ensure Ruff formatting is applied
- Verify imports are properly sorted with isort
- Ensure all tests pass

**Note**: mypy type checking and bandit security scanning are currently disabled in the automated checks but can be run manually if needed.

## Coding Style & Naming Conventions

- Python 3.12+, 4‑space indentation, max line length 88.
- Formatting: Ruff format; Imports: isort (profile=black); Lint: Ruff (E,W,F,I,B,C4,UP) with ignores in `pyproject.toml`.
- Modules: snake_case files; classes PascalCase; functions/vars snake_case; constants UPPER_SNAKE.
- Tool files: `mcp_server/tools/<domain>_tools.py` with `register_<domain>_tools(mcp)` function.
- DCI services: `mcp_server/services/dci_<domain>_service.py` inheriting from `DCIBaseService`.
- External services: `mcp_server/services/<service>_service.py` (e.g., `github_service.py`, `jira_service.py`).

## Prompts System

The server provides parameterized prompts for common DCI workflows:

- **`/dci/rca <job_id>`**: Root Cause Analysis workflow
  - Downloads and analyzes job files (ansible.log, logjuicer.txt, events.txt, must_gather)
  - Stores files in `/tmp/dci/<job_id>/`
  - Generates report at `/tmp/dci/rca-<job_id>.md`
  - Includes timeline, components, topic, pipeline info, and Jira ticket validation

- **`/dci/weekly <subject>`**: 7-day analysis for a team or remoteci
  - Generates report stored at `/tmp/dci/`

- **`/dci/biweekly <subject>`**: 14-day analysis for a team or remoteci
  - Generates report stored at `/tmp/dci/`

- **`/dci/quarterly <remoteci>`**: 3-month comprehensive analysis
  - Statistics about pipelines, topics, failure rates, trends, component usage
  - Uses pagination and caching for large datasets
  - Report stored at `/tmp/dci/<remoteci>/quarterly/<date-range>/report.md`

Prompts are defined in `mcp_server/prompts/prompts.py` and registered via `register_prompts(mcp)`.

## Testing Guidelines

- Framework: pytest (+pytest-asyncio for async).
- Naming: files `test_*.py` or `*_test.py`; functions `test_*`; classes `Test*`.
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow` (see `pytest.ini`).
- Run subsets: `uv run pytest -m unit` or `-m "not slow"`.

## Commit & Pull Request Guidelines

- Commit style observed: short, imperative, lowercase summaries (e.g., "fix authentication", "add /dci/rca prompt"). Keep scope clear and focused.
- PRs: include purpose, key changes, testing notes, and any docs updates. Link issues; add screenshots only if UX/API output changes.
- Ensure `scripts/run-checks.sh` and tests pass before requesting review.

## Security & Configuration

- Store secrets in `.env`; never commit it. Use `env.example` as a template.
- Optional scans: `uv run bandit -r . -f json -o bandit-report.json` and `uv run detect-secrets scan`.
- Container builds: see `Containerfile`/`Containerfile.sse` if packaging is needed.

## Partner Names and Confidentiality

**NEVER** use partner names or company names anywhere in the codebase, including:
- Test files and test data
- Example code and documentation
- Comments and docstrings
- Variable names, function names, or any identifiers
- Configuration files
- Sample data or fixtures

### Why:
- This is a public repository and partner names should remain confidential
- Partner information should not be exposed in public code

### Instead:
- Use generic names like `test-team`, `example-pipeline`, `sample-remoteci`
- Use placeholder names like `partner-1`, `company-a` if differentiation is needed
- Use descriptive generic names like `telco-lab`, `ran-pipeline` (without partner-specific identifiers)

### Examples:

**Bad:**
```python
team = {"name": "the-company", "id": "team-1"}
pipeline_name = "the-company-ran-4.17"
```

**Good:**
```python
team = {"name": "test-team", "id": "team-1"}
pipeline_name = "test-pipeline-4.17"
```

## Adding New Integrations

To add a new external service integration, follow this pattern (see existing GitHub, Jira, Google Drive integrations):

1. **Service**: Create `mcp_server/services/<service>_service.py`
   - Implement service class with API interaction logic
   - Handle authentication (usually via environment variables)
   - Provide clean Python API for the service

2. **Tools**: Create `mcp_server/tools/<service>_tools.py`
   - Define `register_<service>_tools(mcp)` function
   - Use `@mcp.tool()` decorator for each tool
   - Add type hints and clear descriptions for all parameters
   - Tools should be thin wrappers around service methods

3. **Registration**: Update `mcp_server/main.py`
   - Import the registration function
   - Add conditional registration based on required env vars
   - Example: `if os.getenv("SERVICE_TOKEN"): register_service_tools(mcp)`

4. **Configuration**: Update `env.example`
   - Add required environment variables with descriptions
   - Document authentication setup process

5. **Documentation**: Update `README.md`
   - Add setup section for the new integration
   - Document available tools
   - Provide usage examples

6. **Dependencies**: Use `uv add <package>` to add any required packages

## Project Structure

- **Configuration**: Use `pyproject.toml` for all Python project configuration
- **Dependencies**: All dependencies must be declared in `pyproject.toml`
- **Virtual Environment**: Use the `.venv` directory created by `uv`
- **Lock File**: Keep `uv.lock` updated and committed
- **Code Quality**: All code must pass pre-commit checks

## Code Style

- Follow existing code patterns in the codebase
- Use type hints where appropriate (especially for tool parameters)
- Add docstrings for new functions, classes, and MCP tools
- Update `NEWS.md` for significant changes
- Update `README.md` for user-facing changes
- **ALWAYS** run quality checks before considering work complete
