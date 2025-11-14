# Repository Guidelines

## Project Structure & Module Organization

- Source: `mcp_server/` (entry: `mcp_server/main.py`, services under `mcp_server/services/`, tools under `mcp_server/tools/`, utils under `mcp_server/utils/`, prompts under `mcp_server/prompts/`).
- CLI entry: `main.py` (select transport via `MCP_TRANSPORT=stdio|sse`).
- Tests: `tests/` (unit/integration markers; see `pytest.ini`).
- Config: `.env` (see `env.example`), project config in `pyproject.toml`.

## Build, Test, and Development Commands

- Setup env: `uv sync && source .venv/bin/activate`.
- Run server (stdio): `uv run main.py`.
- Run server (SSE): `MCP_TRANSPORT=sse uv run main.py` (SSE endpoint handled by FastMCP).
- All checks: `bash scripts/run-checks.sh`.
- Lint/format: `uv run black --check . && uv run isort --check-only . && uv run ruff check .`.
- Tests: `uv run pytest -v` or `uv run pytest -m "not slow"`.

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

**ALWAYS** ensure code quality by running pre-commit checks after modifications:

1. **After any code changes**: Run the comprehensive checks script
2. **Before committing**: Ensure all pre-commit hooks pass
3. **Format code**: Use Black and isort for consistent formatting
4. **Lint code**: Use Ruff for fast linting and auto-fixing
5. **Type check**: Use mypy for static type checking
6. **Security scan**: Use bandit for vulnerability detection

### Example workflow:

```bash
# 1. Make your code changes
# 2. Run comprehensive checks
bash scripts/run-checks.sh

# 3. If issues found, fix them:
./.venv/bin/python -m black .           # Format code
./.venv/bin/python -m isort .           # Sort imports
./.venv/bin/python -m ruff check --fix . # Fix linting issues
./.venv/bin/python -m mypy mcp_server/  # Check types

# 4. Run checks again to ensure everything passes
bash scripts/run-checks.sh
```

### Pre-commit Hooks (Optional but Recommended):

```bash
# Install pre-commit hooks
./.venv/bin/python -m pre_commit install

# Run pre-commit on all files
./.venv/bin/python -m pre_commit run --all-files
```

### Never:

- Commit code without running quality checks
- Ignore linting or type checking errors
- Skip security scanning with bandit
- Leave formatting inconsistencies

### Always:

- Run `bash scripts/run-checks.sh` after code changes
- Fix any issues found by the checks
- Ensure Black formatting is applied
- Verify imports are properly sorted with isort
- Check that mypy type checking passes
- Confirm bandit security scan passes

## Coding Style & Naming Conventions

- Python 3.12+, 4‑space indentation, max line length 88.
- Formatting: Black; Imports: isort (profile=black); Lint: Ruff (E,W,F,I,B,C4,UP) with ignores in `pyproject.toml`.
- Modules: snake_case files; classes PascalCase; functions/vars snake_case; constants UPPER_SNAKE.
- Tool files: `mcp_server/tools/<domain>_tools.py`; services: `mcp_server/services/dci_<domain>_service.py`.

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

## Project Structure

- **Configuration**: Use `pyproject.toml` for all Python project configuration
- **Dependencies**: All dependencies must be declared in `pyproject.toml`
- **Virtual Environment**: Use the `.venv` directory created by `uv`
- **Lock File**: Keep `uv.lock` updated and committed
- **Code Quality**: All code must pass pre-commit checks

## Code Style

- Follow existing code patterns in the codebase
- Use type hints where appropriate
- Add docstrings for new functions and classes
- Update `NEWS.md` for significant changes
- Update `README.md` for user-facing changes
- **ALWAYS** run quality checks before considering work complete
