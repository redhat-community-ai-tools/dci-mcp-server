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

## Available Tools

The server provides comprehensive tools for interacting with DCI API components:

### Component Tools
- `get_dci_component(component_id)`: Get a specific component by ID
- `list_dci_components(limit, offset, where, sort)`: List components with filtering and pagination

### Job Tools
- `get_dci_job(job_id)`: Get a specific job by ID
- `list_dci_jobs(limit, offset, where, sort)`: List jobs with filtering and pagination
- `list_job_files(job_id)`: List files associated with a job
- `list_job_results(job_id)`: List results associated with a job

### File Tools
- `get_dci_file(file_id)`: Get a specific file by ID
- `list_dci_files(limit, offset, where, sort)`: List files with filtering and pagination
- `download_dci_file(file_id, output_path)`: Download a file to local path
- `get_file_content(file_id)`: Get file content as string

### Pipeline Tools
- `get_dci_pipeline(pipeline_id)`: Get a specific pipeline by ID
- `list_dci_pipelines(limit, offset, where, sort)`: List pipelines with filtering and pagination
- `get_pipeline_jobs(pipeline_id)`: Get jobs associated with a pipeline

### Product Tools
- `get_dci_product(product_id)`: Get a specific product by ID
- `list_dci_products(limit, offset, where, sort)`: List products with filtering and pagination
- `get_product_teams(product_id)`: Get teams associated with a product

### Team Tools
- `get_dci_team(team_id)`: Get a specific team by ID
- `list_dci_teams(limit, offset, where, sort)`: List teams with filtering and pagination

### Topic Tools
- `get_dci_topic(topic_id)`: Get a specific topic by ID
- `list_dci_topics(limit, offset, where, sort)`: List topics with filtering and pagination
- `get_topic_components(topic_id)`: Get components associated with a topic
- `get_topic_jobs_from_components(topic_id)`: Get jobs from topic components

### Log Tools
- `get_dci_job_logs(job_id)`: Get logs for a specific job
- `get_dci_job_artifacts(job_id)`: Get artifacts for a specific job

### PR Tools (Smart PR Detection)
- `get_pr_by_job_id(job_id)`: Extract PR information from job URL
- `get_latest_dci_build_for_pr(pr_number, job_name)`: Get latest build for a PR using URL analysis
- `get_recent_job_status(job_name)`: Get recent job status for a job pattern
- `get_pr_builds_summary(pr_number)`: Get comprehensive summary of all PR builds
- `find_pr_jobs(pr_number, limit)`: Find all jobs related to a PR by analyzing URLs and metadata

### Diagnostic Tools
- `diagnose_pr_failures(pr_number, job_name)`: Analyze PR failure patterns using URL-based detection
- `diagnose_pr_build_status(pr_number, job_name)`: Comprehensive PR build diagnosis
- `get_test_failures_from_artifacts(pr_number, job_name)`: Extract test failures from artifacts

## Smart PR Detection

The server includes advanced PR detection capabilities that analyze job URLs and metadata:

### URL Analysis
The PR finder service extracts PR numbers from various URL formats:
- GitHub PR URLs: `github.com/org/repo/pull/123`
- GitHub Issue URLs: `github.com/org/repo/issues/123`
- Short PR patterns: `/pull/123`, `pr/123`, `PR-123`, `#123`

### Detection Methods
1. **Job URL Analysis**: Extracts PR numbers from job URL fields
2. **Job Name Patterns**: Searches for PR patterns in job names
3. **Metadata Analysis**: Checks job metadata for PR information
4. **Comprehensive Matching**: Combines multiple detection methods for accuracy

### Example Usage
```python
# Find latest build for PR 1234
result = await get_latest_dci_build_for_pr("1234", "e2e-tests")

# Get all jobs for PR 5678
result = await find_pr_jobs("5678", limit=50)

# Extract PR from job URL
result = await get_pr_by_job_id("job-abc123")
```

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd dci-mcp-server

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### Configuration

The server supports multiple ways to configure DCI authentication:

#### Option 1: Environment Variables
```bash
# DCI Authentication (choose one method)
export DCI_API_KEY="your-dci-api-key"

# OR

export DCI_USER_ID="your-dci-user-id"
export DCI_USER_SECRET="your-dci-user-secret"
```

#### Option 2: .env File (Recommended)
Copy the example file and customize it:

```bash
cp env.example .env
# Edit .env with your DCI credentials
```

Example `.env` file:
```bash
# DCI Authentication (choose one method)
DCI_API_KEY=your-dci-api-key-here

# OR use User ID/Secret authentication
# DCI_USER_ID=your-dci-user-id-here
# DCI_USER_SECRET=your-dci-user-secret-here
```

## Usage

### Running the Server

```bash
# Start the server with stdio transport (default)
python main.py

# Or with TCP transport
MCP_TRANSPORT=tcp MCP_HOST=localhost MCP_PORT=8000 python main.py
```

### Example Tool Usage

```python
# Get a specific component
result = await get_dci_component("component-123")

# List jobs with filtering
result = await list_dci_jobs(
    limit=10, 
    where="state:eq:active", 
    sort="created_at:desc"
)

# Download a file
result = await download_dci_file("file-456", "/tmp/downloaded_file.log")

# Get pipeline jobs
result = await get_pipeline_jobs("pipeline-789")

# Find PR builds using smart detection
result = await get_latest_dci_build_for_pr("1234", "e2e-tests")
```

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
├── config.py              # Configuration and authentication
├── main.py               # Server entry point
├── services/             # DCI API services
│   ├── dci_base_service.py
│   ├── dci_component_service.py
│   ├── dci_job_service.py
│   ├── dci_file_service.py
│   ├── dci_pipeline_service.py
│   ├── dci_product_service.py
│   ├── dci_team_service.py
│   ├── dci_topic_service.py
│   ├── dci_log_service.py
│   └── pr_finder.py      # Smart PR detection service
├── tools/                # MCP tools
│   ├── component_tools.py
│   ├── job_tools.py
│   ├── file_tools.py
│   ├── pipeline_tools.py
│   ├── product_tools.py
│   ├── team_tools.py
│   ├── topic_tools.py
│   ├── log_tools.py
│   ├── pr_tools.py       # PR detection tools
│   └── diagnostic_tools.py
└── utils/                # Utility functions
    ├── http_client.py
    └── pr_parser.py
```

### Adding New Tools

1. Create a new service in `mcp_server/services/` if needed
2. Create a new tool file in `mcp_server/tools/`
3. Register the tools in `mcp_server/main.py`
4. Update this README with documentation

## License

[Add your license information here]
