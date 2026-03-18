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
- 🎫 **Jira Integration**: Collect comprehensive ticket data from Jira with comments and changelog
- 🐙 **GitHub Integration**: Search issues and pull requests using GitHub's powerful search API
- 🔴 **Red Hat Support Case Integration**: Access Red Hat support case data from the Customer Portal

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
- `/dci/quarterly <remoteci name/id>` conducts a comprehensive quarterly analysis (last 3 months) with statistics about pipelines, topics, failure rates, trends, and component usage. Uses pagination and caching to handle large datasets. Report stored at `/tmp/dci/<remoteci>/quarterly/<date-range>/report.md`.

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

## Jira Integration

The server includes Jira integration to collect comprehensive ticket data from Red Hat Jira, including comments and changelog information.

### Features
- 🎫 **Ticket Data Collection**: Retrieve comprehensive ticket information including summary, description, status, and dates
- 💬 **Comments Analysis**: Get up to 50 recent comments with author and timestamp information
- 📝 **Changelog Tracking**: Access complete ticket history and field changes
- 🔍 **JQL Search**: Search tickets using Jira Query Language (JQL)
- 📊 **Project Information**: Get project details and metadata
- 🔗 **DCI Integration**: Seamlessly extract Jira tickets from DCI job comments

### Setup
To use Jira features, follow the [Jira Setup Guide](JIRA_SETUP.md) for detailed configuration instructions.

**Quick Setup:**
1. Get your Jira API token from [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Set environment variables in your `.env` file:
   ```bash
   JIRA_API_TOKEN=your_jira_api_token_here
   JIRA_EMAIL=you@redhat.com
   JIRA_URL=https://redhat.atlassian.net
   ```

### Usage Examples
```python
# Get comprehensive ticket data with comments
ticket_data = await get_jira_ticket("CILAB-1234", max_comments=10)

# Search for tickets using JQL
open_tickets = await search_jira_tickets("project = CILAB AND status = Open")

# Get project information
project_info = await get_jira_project_info("CILAB")

# Extract Jira tickets from DCI job comments
jobs_with_tickets = await search_dci_jobs("comment=~'.*CILAB.*'")
for job in jobs_with_tickets:
    if job.get('comment'):
        ticket_data = await get_jira_ticket(job['comment'])
```

## GitHub Integration

The server includes GitHub integration to search for issues and pull requests and retrieve detailed information about them.

### Features
- 🔍 **Issue & PR Search**: Search using GitHub's powerful query syntax
- 📊 **Comprehensive Data**: Get detailed information including comments, labels, assignees, and more
- 🔀 **Pull Request Metadata**: Access PR-specific data like merge status, branch info, and file changes
- 📈 **Repository Information**: Retrieve repository metadata and statistics
- 🔐 **Token Authentication**: Secure authentication with GitHub personal access tokens

### Setup

**Quick Setup:**
1. Get your GitHub personal access token from [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. Create a new token (classic) with `repo` scope (for private repos) or `public_repo` (for public repos only)
3. Set environment variable in your `.env` file:
   ```bash
   GITHUB_TOKEN=your_github_token_here
   ```

## Red Hat Support Case Integration

The server includes Red Hat Support Case integration to retrieve case data from the Red Hat Customer Portal.

### Features
- 📋 **Case Data Retrieval**: Get comprehensive case information including summary, status, severity, and product details
- 💬 **Comments**: Access case comments and communication history
- 🐛 **Linked Bugs**: View Bugzilla bugs linked to the case
- 📢 **Errata/Advisory Details**: Retrieve errata information including CVEs, affected products, and references
- 🔐 **Offline Token Authentication**: Secure authentication using Red Hat API offline tokens

### Setup

**Quick Setup:**
1. Get your offline token from [https://access.redhat.com/management/api](https://access.redhat.com/management/api)
2. Set environment variable in your `.env` file:
   ```bash
   OFFLINE_TOKEN=your_offline_token_here
   ```

## Available Tools exposed by the MCP server

The server provides tools for interacting with DCI API components:

### Component Tools

- `query_dci_components(query, limit, offset, sort, fields)`: Query components with advanced query language and pagination

### Date Tools

- `today()`: Returns today's date in YYYY-MM-DD format.
- `now()`: Returns current date and time in DCI compatible format (GMT).

### Job Tools

- `search_dci_jobs(query, sort, limit, offset, fields)`: Search jobs with advanced query language and pagination

### File Tools

- `download_dci_file(job_id, file_id, output_path)`: Download a file to local path

### Google Drive Tools

- `create_google_doc_from_markdown(markdown_content, doc_title, folder_id, folder_name)`: Create a Google Doc from markdown content
- `create_google_doc_from_file(file_path, doc_title, folder_id, folder_name)`: Create a Google Doc from a markdown file
- `convert_dci_report_to_google_doc(report_path, doc_title, folder_id, folder_name)`: Convert a DCI report to Google Doc
- `list_google_docs(query, max_results)`: List Google Docs in your Drive

**Note**: For folder placement, you can use either `folder_id` (exact folder ID) or `folder_name` (searches for folder by name). Do not use both parameters together.

### Jira Tools

- `get_jira_ticket(ticket_key, max_comments)`: Get comprehensive ticket data including comments and changelog
- `search_jira_tickets(jql, max_results)`: Search tickets using JQL (Jira Query Language)
- `get_jira_project_info(project_key)`: Get project information and metadata

**Note**: Jira tools require `JIRA_API_TOKEN` environment variable to be set.

### GitHub Tools

- `search_github_issues(query, max_results)`: Search issues and pull requests using GitHub search query syntax
- `get_github_issue(repo, issue_number, max_comments)`: Get comprehensive issue/PR data including comments and PR-specific information
- `get_github_repository_info(repo)`: Get repository information and statistics
- `get_github_pr_diff(repo, pull_number, max_files)`: Get the diff/patch for a pull request with per-file unified diffs

**Note**: GitHub tools require `GITHUB_TOKEN` environment variable to be set.

### Support Case Tools

- `get_support_case(case_number)`: Get Red Hat support case data including comments and linked Bugzilla bugs
- `get_support_case_comments(case_number, start_date?, end_date?)`: Get comments for a case with optional date filtering
- `list_support_case_attachments(case_number)`: List attachment metadata for a case
- `get_errata(advisory_id)`: Get Red Hat errata/advisory details (RHSA, RHBA, RHEA)

**Note**: Support Case tools require `OFFLINE_TOKEN` environment variable to be set.

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
│   ├── dci_log_service.py
│   ├── dci_pipeline_service.py
│   ├── dci_product_service.py
│   ├── dci_team_service.py
│   ├── dci_remoteci_service.py
│   ├── dci_topic_service.py
│   ├── google_drive_service.py
│   ├── jira_service.py
│   ├── github_service.py
│   └── support_case_service.py
├── promps/               # Templatized prompts
│   └── prompts.py
├── tools/                # MCP tools
│   ├── component_tools.py
│   ├── date_tools.py
│   ├── job_tools.py
│   ├── file_tools.py
│   ├── google_drive_tools.py
│   ├── jira_tools.py
│   ├── github_tools.py
│   ├── support_case_tools.py
│   └── log_tools.py
└── utils/                # Utility functions
    └── http_client.py
```

### Adding New Tools

1. Create a new service in `mcp_server/services/` if needed
2. Create a new tool file in `mcp_server/tools/`
3. Register the tools in `mcp_server/main.py`
4. Update this README with documentation
