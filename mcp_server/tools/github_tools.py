"""MCP tools for GitHub issue and pull request operations."""

import json
import re
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.github_service import GitHubService


def validate_repo_name(repo_name: str) -> str:
    """
    Validate and normalize GitHub repository name format.

    Args:
        repo_name: Repository name in format owner/repo (e.g., octocat/Hello-World)

    Returns:
        Normalized repository name

    Raises:
        ValueError: If repository name format is invalid
    """
    # Remove any whitespace
    repo_name = repo_name.strip()

    # Pattern to match owner/repo format
    pattern = r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$"

    if not re.match(pattern, repo_name):
        raise ValueError(
            f"Invalid repository name format: '{repo_name}'. "
            "Expected format: owner/repo (e.g., octocat/Hello-World)"
        )

    return repo_name


def register_github_tools(mcp: FastMCP) -> None:
    """Register GitHub-related tools with the MCP server."""

    @mcp.tool()
    async def search_github_issues(
        query: Annotated[
            str,
            Field(
                description='GitHub search query. Examples: "is:issue is:open repo:owner/repo", "is:pr author:username", "is:open label:bug"'
            ),
        ],
        max_results: Annotated[
            int,
            Field(
                description="Maximum number of results to return (default: 50, max: 200)",
                ge=1,
                le=200,
            ),
        ] = 50,
    ) -> str:
        """Search GitHub issues and pull requests using GitHub search query syntax.

        This tool allows you to search for issues and pull requests using GitHub's
        powerful search query syntax.

        ## Authentication Required

        This tool requires GitHub API authentication. Set the following environment variable:
        - `GITHUB_TOKEN`: Your GitHub personal access token

        ## Getting Your GitHub Token

        1. Go to https://github.com/settings/tokens
        2. Click "Generate new token" -> "Generate new token (classic)"
        3. Give your token a descriptive name (e.g., "DCI MCP Server")
        4. Select scopes: `repo` (for private repos) or `public_repo` (for public repos only)
        5. Click "Generate token"
        6. Copy the generated token and set it as `GITHUB_TOKEN` in your environment

        ## Search Query Syntax

        **Basic Qualifiers:**
        - `is:issue` or `is:pr` - Filter by type
        - `is:open`, `is:closed`, or `is:merged` - Filter by state
        - `repo:owner/repo` - Search within a specific repository
        - `author:username` - Filter by author
        - `assignee:username` - Filter by assignee
        - `label:labelname` - Filter by label
        - `milestone:"milestone name"` - Filter by milestone

        **Date Qualifiers:**
        - `created:>2024-01-01` - Created after specific date
        - `updated:<2024-01-01` - Updated before specific date
        - `closed:2024-01-01..2024-12-31` - Closed within date range

        **Text Search:**
        - `keyword in:title` - Search in title
        - `keyword in:body` - Search in body/description
        - `keyword in:comments` - Search in comments

        **Examples:**

        Find open issues in a repository:
        ```
        is:issue is:open repo:octocat/Hello-World
        ```

        Find your open pull requests:
        ```
        is:pr is:open author:@me
        ```

        Find bugs in a repository:
        ```
        is:issue is:open label:bug repo:owner/repo
        ```

        Find recently updated issues:
        ```
        is:issue updated:>2024-01-01 repo:owner/repo
        ```

        Search for issues with text:
        ```
        authentication error is:issue is:open
        ```

        ## Returned Data

        The tool returns a JSON array containing issue/PR data with:
        - **number**: Issue/PR number
        - **title**: Title/summary
        - **state**: Current state (open, closed)
        - **repository**: Repository full name (owner/repo)
        - **type**: Either "issue" or "pull_request"
        - **author**: Creator username
        - **assignees**: List of assigned usernames
        - **labels**: List of label names
        - **created_at**: Creation timestamp
        - **updated_at**: Last update timestamp
        - **closed_at**: Close timestamp (if closed)
        - **url**: Direct link to the issue/PR

        Returns:
            JSON string with array of issue/PR data
        """
        try:
            # Initialize GitHub service
            github_service = GitHubService()

            # Search issues
            issues = github_service.search_issues(query, max_results)

            return json.dumps(issues, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_github_issue(
        repo: Annotated[
            str,
            Field(
                description="Repository name in format owner/repo (e.g., octocat/Hello-World)"
            ),
        ],
        issue_number: Annotated[
            int,
            Field(description="Issue or pull request number", ge=1),
        ],
        max_comments: Annotated[
            int,
            Field(
                description="Maximum number of comments to retrieve (default: 10, max: 50)",
                ge=1,
                le=50,
            ),
        ] = 10,
    ) -> str:
        """Get comprehensive GitHub issue or pull request data including comments.

        This tool retrieves detailed information about a GitHub issue or pull request including:
        - Basic information (title, body, state, type, etc.)
        - Author and assignees
        - Labels and milestone
        - Date information (created, updated, closed)
        - Recent comments (up to the specified limit)
        - Pull request specific data (if applicable): merge status, branch info, file changes

        ## Authentication Required

        This tool requires GitHub API authentication. Set the following environment variable:
        - `GITHUB_TOKEN`: Your GitHub personal access token

        ## Repository Format

        The repository name should be in the format `owner/repo`:
        - Examples: `octocat/Hello-World`, `torvalds/linux`, `facebook/react`
        - Case sensitive
        - Must be a valid repository you have access to

        ## Issue/PR Number

        The issue or pull request number (the number after the # in GitHub URLs):
        - Example: For https://github.com/octocat/Hello-World/issues/123, use 123

        ## Returned Data

        The tool returns a JSON object containing:
        - **number**: Issue/PR number
        - **title**: Title/summary
        - **body**: Full description/body text
        - **state**: Current state (open, closed)
        - **repository**: Repository full name
        - **type**: Either "issue" or "pull_request"
        - **author**: Creator username
        - **assignees**: List of assigned usernames
        - **labels**: List of label names
        - **milestone**: Milestone title (if set)
        - **created_at**: Creation timestamp
        - **updated_at**: Last update timestamp
        - **closed_at**: Close timestamp (if closed)
        - **url**: Direct link to the issue/PR
        - **comments**: Recent comments with author, body, timestamps
        - **pull_request_data**: (PR only) merge status, branches, file changes

        Returns:
            JSON string with comprehensive issue/PR data
        """
        try:
            # Validate and normalize repository name
            normalized_repo = validate_repo_name(repo)

            # Initialize GitHub service
            github_service = GitHubService()

            # Get issue/PR data
            issue_data = github_service.get_issue(
                normalized_repo, issue_number, max_comments
            )

            return json.dumps(issue_data, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_github_repository_info(
        repo: Annotated[
            str,
            Field(
                description="Repository name in format owner/repo (e.g., octocat/Hello-World)"
            ),
        ],
    ) -> str:
        """Get GitHub repository information.

        This tool retrieves basic information about a GitHub repository including
        name, description, owner, statistics, and metadata.

        ## Authentication Required

        This tool requires GitHub API authentication. Set the following environment variable:
        - `GITHUB_TOKEN`: Your GitHub personal access token

        ## Repository Format

        The repository name should be in the format `owner/repo`:
        - Examples: `octocat/Hello-World`, `torvalds/linux`, `facebook/react`
        - Case sensitive
        - Must be a valid repository you have access to

        ## Returned Data

        The tool returns a JSON object containing:
        - **name**: Repository name
        - **full_name**: Full repository name (owner/repo)
        - **description**: Repository description
        - **owner**: Repository owner username
        - **private**: Whether the repository is private
        - **default_branch**: Default branch name (e.g., main, master)
        - **stars**: Number of stars
        - **forks**: Number of forks
        - **open_issues**: Number of open issues
        - **language**: Primary programming language
        - **created_at**: Creation timestamp
        - **updated_at**: Last update timestamp
        - **url**: Direct link to the repository

        Returns:
            JSON string with repository information
        """
        try:
            # Validate and normalize repository name
            normalized_repo = validate_repo_name(repo)

            # Initialize GitHub service
            github_service = GitHubService()

            # Get repository info
            repo_info = github_service.get_repository_info(normalized_repo)

            return json.dumps(repo_info, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
