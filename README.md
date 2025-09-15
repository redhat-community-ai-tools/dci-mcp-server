# DCI MCP Server

This project provides a Model Context Protocol (MCP) server adapted for the [DCI API](https://doc.distributed-ci.io/dci-control-server/docs/API/).
It allows AI models to interact with [DCI](https://doc.distributed-ci.io/) for comprehensive data extraction about DCI jobs, components, topics and files.

## Features

- 🚀 **FastAPI**: Built on a modern, fast web framework
- 🤖 **MCP**: Implements the Model Context Protocol for AI integration
- 🔍 **Comprehensive DCI API**: Full access to DCI components, jobs, files, pipelines, products, teams, and topics
- 🔧 **Smart PR Detection**: Advanced PR build finder that analyzes job URLs and metadata
- 🔐 **DCI Integration**: Native DCI API support with authentication
- 📝 **Easy Configuration**: Support for .env files for simple setup
- ✅ **Code Quality**: Comprehensive pre-commit checks and linting
- 📊 **Google Drive Integration**: Convert DCI reports to Google Docs with rich formatting

## Installation

```bash
# Clone the repository
git clone https://github.com/redhat-ai-tools/dci-mcp-server
cd dci-mcp-server

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### Configuration

The server supports multiple ways to configure DCI authentication:

Copy the example file and customize it:

```bash
cp env.example .env
# Edit .env with your DCI credentials
```

Example `.env` file:

```bash
# Method 1: API Key Authentication
DCI_CLIENT_ID=<client_type>/<client_id>
DCI_API_SECRET=<api_secret>

# Method 2: User ID/Password (alternative to API key)
# DCI_LOGIN=foo
# DCI_PASSWORD=bar

# Google Drive Integration (optional)
# GOOGLE_CREDENTIALS_PATH=credentials.json
# GOOGLE_TOKEN_PATH=token.json
```

### MCP Configuration

#### Cursor IDE (stdio transport)

Add to your `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "dci": {
      "command": "uv",
      "args": ["run", "/path/to/dci-mcp-server/.venv/bin/python", "/path/to/dci-mcp-server/main.py"],
      "description": "MCP server for DCI integration"
    }
  }
}
```

#### Web-based Integration (SSE transport)

For web applications or services that need HTTP-based communication:

```json
{
  "mcpServers": {
    "dci": {
      "url": "http://0.0.0.0:8000/sse/",
      "description": "MCP server for DCI integration with direct SSE",
      "env": {
        "MCP_TRANSPORT": "sse"
      }
    }
  }
}
```

**SSE Endpoint**: `http://0.0.0.0:8000/sse/`

> **Note**: Make sure to start the SSE server separately with `MCP_TRANSPORT=sse uv run main.py` before using this configuration.

## Prompts

You can then use [prompts](PROMPTS.md) to explore the DCI data.

There are also parameterized prompts defined in the MCP server:

- `/dci/rca <job id>` conducts a Root Cause Analysis of the problem in the job. Storing the downloaded files under `/tmp/dci/<job id>` and generating a report at `/tmp/dci/rca-<job id>.md`.
- `/dci/weekly <team name/id or remoteci name/id>` conducts a report for the last 7 days stored at `/tmp/dci`.
- `/dci/biweekly <team name/id or remoteci name/id>` conducts a report for the last 14 days stored at `/tmp/dci`.

## Google Drive Integration

The server includes Google Drive integration to convert DCI reports and markdown content to Google Docs with rich formatting support.

### Features
- 📄 **Markdown to Google Docs**: Convert markdown content to properly formatted Google Docs
- 📊 **DCI Report Conversion**: Specialized tools for converting DCI weekly/biweekly reports
- 🎨 **Rich Formatting**: Support for tables, code blocks, headers, lists, and links
- 🔐 **OAuth2 Authentication**: Secure authentication with Google Drive API
- 📁 **Folder Organization**: Option to organize documents in specific Google Drive folders

### Setup
To use Google Drive features, follow the [Google Drive Setup Guide](GOOGLE_DRIVE_SETUP.md) for detailed configuration instructions.

**Quick Setup:**
1. Set up Google Cloud Project and enable Google Drive API
2. Download OAuth2 credentials and save as `credentials.json`
3. Initialize the service: `uv run python -c "from mcp_server.services.google_drive_service import GoogleDriveService; GoogleDriveService()"`
4. Complete browser authentication when prompted

### Usage Examples
```python
# Convert a DCI report to Google Doc in a specific folder by name
result = await convert_dci_report_to_google_doc(
    report_path="/tmp/dci/the_weekly_report_2025-09-09.md",
    doc_title="The Weekly Report - September 2025",
    folder_name="DCI Reports"
)

# Create a Google Doc from markdown content in a folder by ID
result = await create_google_doc_from_markdown(
    markdown_content="# My Report\n\nThis is a **test** document.",
    doc_title="My Custom Report",
    folder_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
)

# Create a Google Doc from a file in a folder by name
result = await create_google_doc_from_file(
    file_path="/path/to/report.md",
    doc_title="My Report",
    folder_name="Project Documents"
)
```

## Available Tools exposed by the MCP server

The server provides comprehensive tools for interacting with DCI API components:

### Component Tools

- `get_dci_component(component_id)`: Get a specific component by ID
- `query_dci_components(query, limit, offset, sort)`: Query components with advanced query language and pagination

### Date tools

- `today`: returns today's date.

### Job Tools

- `query_dci_jobs(query, limit, offset, sort)`: Query jobs with pagination.

### File Tools

- `query_dci_files(query, limit, offset, sort)`: Query files with advanced query language and pagination
- `download_dci_file(job_id, file_id, output_path)`: Download a file to local path
- `get_file_content(file_id)`: Get file content as string

### Pipeline Tools

- `query_dci_pipelines(query, limit, offset, sort)`: Query pipelines with advanced query language and pagination
- `get_pipeline_jobs(pipeline_id)`: Get jobs associated with a pipeline

### RemoteCI Tools

- `query_dci_remotecis(query, limit, offset, sort)`: Query remotecis with advanced query language and pagination

### Product Tools

- `query_dci_products(query, limit, offset, sort)`: Query products with advanced query language and pagination
- `get_product_teams(product_id)`: Get teams associated with a product

### Team Tools

- `query_dci_teams(query, limit, offset, sort)`: Query teams with advanced query language and pagination

### Topic Tools

- `query_dci_topics(query, limit, offset, sort)`: Query topics with advanced query language and pagination

### Google Drive Tools

- `create_google_doc_from_markdown(markdown_content, doc_title, folder_id, folder_name)`: Create a Google Doc from markdown content
- `create_google_doc_from_file(file_path, doc_title, folder_id, folder_name)`: Create a Google Doc from a markdown file
- `convert_dci_report_to_google_doc(report_path, doc_title, folder_id, folder_name)`: Convert a DCI report to Google Doc
- `list_google_docs(query, max_results)`: List Google Docs in your Drive

**Note**: For folder placement, you can use either `folder_id` (exact folder ID) or `folder_name` (searches for folder by name). Do not use both parameters together.


## Code Quality Checks

The project includes comprehensive code quality checks:

#### Manual Checks
```bash
# Run all checks
bash scripts/run-checks.sh

# Or run individual checks
./.venv/bin/python -m black --check .
./.venv/bin/python -m isort --check-only .
./.venv/bin/python -m ruff check .
./.venv/bin/python -m mypy mcp_server/
./.venv/bin/python -m bandit -r .
```

#### Pre-commit Hooks (Optional)
```bash
# Install pre-commit hooks
./.venv/bin/python -m pre_commit install

# Run pre-commit on all files
./.venv/bin/python -m pre_commit run --all-files
```

## Development

### Project Structure

```
mcp_server/
├── config.py             # Configuration and authentication
├── main.py               # Server entry point
├── services/             # DCI API services
│   ├── dci_base_service.py
│   ├── dci_component_service.py
│   ├── dci_job_service.py
│   ├── dci_file_service.py
│   ├── dci_pipeline_service.py
│   ├── dci_product_service.py
│   ├── dci_team_service.py
│   ├── dci_remoteci_service.py
│   ├── dci_topic_service.py
│   └── google_drive_service.py
├── promps/               # Templatized prompts
│   └── prompts.py
├── tools/                # MCP tools
│   ├── component_tools.py
│   ├── date_tools.py
│   ├── job_tools.py
│   ├── file_tools.py
│   ├── google_drive_tools.py
│   ├── pipeline_tools.py
│   ├── product_tools.py
│   ├── remoteci_tools.py
│   ├── team_tools.py
│   └── topic_tools.py
└── utils/                # Utility functions
    └── http_client.py
```

### Adding New Tools

1. Create a new service in `mcp_server/services/` if needed
2. Create a new tool file in `mcp_server/tools/`
3. Register the tools in `mcp_server/main.py`
4. Update this README with documentation
