# DCI MCP Server - Change Log

## [2026-02-27]

### Improvements

- Add `get_github_pr_diff` tool to retrieve per-file diffs/patches for GitHub pull requests
- `get_jira_ticket` now includes custom fields in the response under a `custom_fields` key with human-readable field names

### Bug Fixes

- Fix crash in `get_jira_ticket` when changelog entries have no author

## [2026-02-18]

### Improvements

- When DCI credentials are not set, the server no longer fails at startup; DCI tools are simply omitted so Jira- or GitHub-only usage is possible.

## [2026-01-27]

### Improvements

- Simplified prompt implementations to use FastMCP's modern API (direct string returns instead of PromptMessage/TextContent wrappers)

### Dependencies

- Updated all project dependencies to their latest versions:
  - black: 25.1.0 → 26.1.0
  - ruff: 0.12.8 → 0.14.14
  - pytest: 8.4.1 → 9.0.2
  - fastapi: 0.116.1 → 0.128.0
  - fastmcp: 2.11.3 → 2.14.4
  - mcp: 1.12.4 → 1.26.0
  - pydantic: 2.11.7 → 2.12.5
  - isort: 6.0.1 → 7.0.0
  - cryptography: 45.0.6 → 46.0.3
  - dciclient: 4.1.0.post202509100810 → 4.1.0.post202510221005
  - google-api-python-client: 2.181.0 → 2.188.0
  - uvicorn: 0.35.0 → 0.40.0
  - pre-commit: 4.3.0 → 4.5.1
  - And many other dependency updates

## [2025-11-21]

### Improvements

- Restored `query_dci_teams` and `query_dci_remotecis` tools that were previously removed

## [2025-09-15] - 0.3.0

### Improvements

- Use the search API
- Removed most of the tools as the search API is now covering everything

### Dependencies

- Updated dciclient dependency to version 4.1.0 or higher (to get access to the search API)

## [2025-09-10] - 0.2.0

### Improvements

- Add new Google drive tools to convert MarkDown files to Google docs

## [2025-08-12]

### Dependencies

- Updated all project dependencies to their latest versions:
  - fastmcp: 2.10.6 → 2.11.3
  - fastapi: 0.104.0 → 0.116.1
  - uvicorn: 0.24.0 → 0.35.0
  - pytest: 7.0.0 → 8.4.1
  - pytest-asyncio: 0.21.0 → 1.1.0
  - pytest-mock: 3.10.0 → 3.14.1
  - pre-commit: 4.2.0 → 4.3.0
  - ruff: 0.12.5 → 0.12.8
  - bandit: 1.7.8 → 1.8.6
  - detect-secrets: 1.4.0 → 1.5.0
  - types-python-dateutil: 2.9.0.20250708 → 2.9.0.20250809

### Improvements

- Standardized all query tools to use `fields` parameter instead of `only_fields` for consistency across the codebase.
- Updated parameter type from `list[str] | None` to `list[str]` for better type safety.
- Changed default behavior: empty list `[]` now returns no fields, instead of `None` returning no fields.

## [2025-08-05]

### Bug Fixes

- Fixed `query_dci_components` tool by using the correct `component.base.list` method instead of the non-existent `component.list` method.
- Fixed `query_dci_files` tool by using the correct `job.list_files()` method instead of `dci_file.list()` to properly query files for a specific job.
- Fixed JSON parsing errors in `query_dci_files` tool by improving error handling and response structure validation.
- Fixed `test_file_download_tools` integration test to correctly access file ID from the response structure.

### Improvements

- Replaced `list_dci_components` with `query_dci_components` using the same advanced query language model as `query_dci_jobs`.
- Replaced `list_dci_products` with `query_dci_products` using the same advanced query language model as `query_dci_jobs`.
- Replaced `list_dci_teams` with `query_dci_teams` using the same advanced query language model as `query_dci_jobs`.
- Replaced `list_dci_pipelines` with `query_dci_pipelines` using the same advanced query language model as `query_dci_jobs`.
- Replaced `list_dci_files` with `query_dci_files` using the same advanced query language model as `query_dci_jobs`.
- Enhanced `query_dci_topics` with field filtering capabilities to match other query tools.
- Removed individual `get_dci_*` tools for products, teams, topics, pipelines, and files in favor of query-based tools.
- Added `query_dci_remotecis` tool for querying remote CI labs with advanced query language.

## [2025-08-04]

### Improvements

- `query_dci_jobs` MCP tool can now filter non needed fields.

## [2025-07-29]

### Tests

- Added comprehensive integration tests for all MCP tools in `tests/integration_test.py`

### Bootstrap

Used https://github.com/redhat-ai-tools/prow-mcp-server as the starting point to create an MCP server for the DCI API.
