# DCI MCP Server - Change Log

## [2025-08-05]

### Bug Fixes

- Fixed `query_dci_components` tool by using the correct `component.base.list` method instead of the non-existent `component.list` method.

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
