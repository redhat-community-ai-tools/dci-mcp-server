"""MCP tools for GitLab project, issue, and merge request operations."""

import json
import re
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.gitlab_service import GitLabService


def validate_project_path(project_path: str) -> str:
    """
    Validate and normalize GitLab project path format.

    Args:
        project_path: Project path in format group/project or numeric ID

    Returns:
        Normalized project path

    Raises:
        ValueError: If project path format is invalid
    """
    project_path = project_path.strip()

    if project_path.isdigit():
        return project_path

    pattern = r"^[a-zA-Z0-9._-]+(/[a-zA-Z0-9._-]+)+$"

    if not re.match(pattern, project_path):
        raise ValueError(
            f"Invalid project path format: '{project_path}'. "
            "Expected format: group/project (e.g., gitlab-org/gitlab) "
            "or numeric project ID"
        )

    return project_path


def register_gitlab_tools(mcp: FastMCP) -> None:
    """Register GitLab-related tools with the MCP server."""

    @mcp.tool()
    async def search_gitlab_issues(
        project: Annotated[
            str,
            Field(
                description="GitLab project path (e.g., gitlab-org/gitlab) or numeric project ID"
            ),
        ],
        gitlab_url: Annotated[
            str | None,
            Field(
                description="GitLab instance URL (e.g., https://gitlab.cee.redhat.com). Overrides GITLAB_URL env var. Defaults to https://gitlab.com"
            ),
        ] = None,
        search: Annotated[
            str | None,
            Field(description="Text to search for in issue titles and descriptions"),
        ] = None,
        state: Annotated[
            str | None,
            Field(
                description='Filter by state: "opened", "closed", or "all" (default: all)'
            ),
        ] = None,
        labels: Annotated[
            str | None,
            Field(
                description="Comma-separated list of labels to filter by (e.g., bug,critical)"
            ),
        ] = None,
        max_results: Annotated[
            int,
            Field(
                description="Maximum number of results to return (default: 50, max: 200)",
                ge=1,
                le=200,
            ),
        ] = 50,
        offset: Annotated[
            int,
            Field(
                description="Number of results to skip for pagination (default: 0)",
                ge=0,
            ),
        ] = 0,
    ) -> str:
        """Search GitLab issues in a project.

        This tool searches for issues within a GitLab project using various filters.

        ## Authentication Required

        This tool requires GitLab API authentication. Set the following environment variables:
        - `GITLAB_TOKEN`: Your GitLab personal access token
        - `GITLAB_URL`: GitLab instance URL (default: https://gitlab.com)
        - `GITLAB_SSL_VERIFY`: SSL verification (default: true). Set to `false` for self-signed certificates (e.g., internal GitLab instances), or to a CA bundle path.

        ## Getting Your GitLab Token

        1. Go to your GitLab instance -> User Settings -> Access Tokens
        2. Create a new personal access token
        3. Select scopes: `read_api` (for read-only) or `api` (for full access)
        4. Copy the token and set it as `GITLAB_TOKEN` in your environment

        ## Filtering

        **State:** Filter by issue state:
        - `opened` - Open issues only
        - `closed` - Closed issues only
        - `all` - All issues (default)

        **Labels:** Comma-separated label names:
        - `bug` - Single label
        - `bug,critical` - Multiple labels (AND logic)

        **Search:** Free-text search in titles and descriptions

        ## Returned Data

        The tool returns a JSON object containing:
        - **total_count**: Total number of matching results (may be null)
        - **offset**: Number of results skipped
        - **limit**: Maximum results requested
        - **items**: Array of issue data, each with:
          - **iid**: Issue internal ID (shown in URLs)
          - **title**: Issue title
          - **state**: Current state (opened, closed)
          - **project**: Project path
          - **author**: Creator username
          - **assignees**: List of assigned usernames
          - **labels**: List of label names
          - **created_at**: Creation timestamp
          - **updated_at**: Last update timestamp
          - **url**: Direct link to the issue

        Returns:
            JSON string with total_count and items array
        """
        try:
            normalized_project = validate_project_path(project)
            gitlab_service = GitLabService(gitlab_url=gitlab_url)

            labels_list = (
                [lbl.strip() for lbl in labels.split(",") if lbl.strip()]
                if labels
                else None
            )

            results = gitlab_service.search_issues(
                normalized_project,
                search,
                state,
                labels_list,
                max_results,
                offset,
            )

            return json.dumps(results, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_gitlab_issue(
        project: Annotated[
            str,
            Field(
                description="GitLab project path (e.g., gitlab-org/gitlab) or numeric project ID"
            ),
        ],
        issue_iid: Annotated[
            int,
            Field(
                description="Issue internal ID (the number shown in the GitLab UI)",
                ge=1,
            ),
        ],
        gitlab_url: Annotated[
            str | None,
            Field(
                description="GitLab instance URL (e.g., https://gitlab.cee.redhat.com). Overrides GITLAB_URL env var. Defaults to https://gitlab.com"
            ),
        ] = None,
        max_notes: Annotated[
            int,
            Field(
                description="Maximum number of notes/comments to retrieve (default: 10, max: 50)",
                ge=1,
                le=50,
            ),
        ] = 10,
        note_offset: Annotated[
            int,
            Field(
                description="Number of notes to skip for pagination (default: 0)",
                ge=0,
            ),
        ] = 0,
    ) -> str:
        """Get comprehensive GitLab issue data including notes (comments).

        This tool retrieves detailed information about a GitLab issue including:
        - Basic information (title, description, state, etc.)
        - Author and assignees
        - Labels and milestone
        - Date information (created, updated, closed)
        - User notes/comments (system notes are excluded)

        ## Authentication Required

        This tool requires GitLab API authentication. Set the following environment variables:
        - `GITLAB_TOKEN`: Your GitLab personal access token
        - `GITLAB_URL`: GitLab instance URL (default: https://gitlab.com)
        - `GITLAB_SSL_VERIFY`: SSL verification (default: true). Set to `false` for self-signed certificates (e.g., internal GitLab instances), or to a CA bundle path.

        ## Project Format

        The project path should be in the format `group/project`:
        - Examples: `gitlab-org/gitlab`, `mygroup/myproject`
        - Nested groups: `group/subgroup/project`
        - Numeric IDs are also accepted: `12345`

        ## Issue IID

        The issue internal ID (the number after the # in GitLab URLs):
        - Example: For https://gitlab.com/group/project/-/issues/42, use 42

        ## Returned Data

        The tool returns a JSON object containing:
        - **iid**: Issue internal ID
        - **title**: Issue title
        - **description**: Full description text
        - **state**: Current state (opened, closed)
        - **project**: Project path
        - **author**: Creator username
        - **assignees**: List of assigned usernames
        - **labels**: List of label names
        - **milestone**: Milestone title (if set)
        - **created_at**: Creation timestamp
        - **updated_at**: Last update timestamp
        - **closed_at**: Close timestamp (if closed)
        - **url**: Direct link to the issue
        - **total_notes**: Total number of user notes
        - **notes**: Notes with author, body, timestamps (paginated, system notes excluded)

        Returns:
            JSON string with comprehensive issue data
        """
        try:
            normalized_project = validate_project_path(project)
            gitlab_service = GitLabService(gitlab_url=gitlab_url)

            issue_data = gitlab_service.get_issue(
                normalized_project, issue_iid, max_notes, note_offset
            )

            return json.dumps(issue_data, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def search_gitlab_merge_requests(
        project: Annotated[
            str,
            Field(
                description="GitLab project path (e.g., gitlab-org/gitlab) or numeric project ID"
            ),
        ],
        gitlab_url: Annotated[
            str | None,
            Field(
                description="GitLab instance URL (e.g., https://gitlab.cee.redhat.com). Overrides GITLAB_URL env var. Defaults to https://gitlab.com"
            ),
        ] = None,
        search: Annotated[
            str | None,
            Field(
                description="Text to search for in merge request titles and descriptions"
            ),
        ] = None,
        state: Annotated[
            str | None,
            Field(
                description='Filter by state: "opened", "closed", "merged", or "all" (default: all)'
            ),
        ] = None,
        labels: Annotated[
            str | None,
            Field(
                description="Comma-separated list of labels to filter by (e.g., bug,critical)"
            ),
        ] = None,
        max_results: Annotated[
            int,
            Field(
                description="Maximum number of results to return (default: 50, max: 200)",
                ge=1,
                le=200,
            ),
        ] = 50,
        offset: Annotated[
            int,
            Field(
                description="Number of results to skip for pagination (default: 0)",
                ge=0,
            ),
        ] = 0,
    ) -> str:
        """Search GitLab merge requests in a project.

        This tool searches for merge requests within a GitLab project using various filters.

        ## Authentication Required

        This tool requires GitLab API authentication. Set the following environment variables:
        - `GITLAB_TOKEN`: Your GitLab personal access token
        - `GITLAB_URL`: GitLab instance URL (default: https://gitlab.com)
        - `GITLAB_SSL_VERIFY`: SSL verification (default: true). Set to `false` for self-signed certificates (e.g., internal GitLab instances), or to a CA bundle path.

        ## Filtering

        **State:** Filter by merge request state:
        - `opened` - Open MRs only
        - `closed` - Closed MRs only
        - `merged` - Merged MRs only
        - `all` - All MRs (default)

        **Labels:** Comma-separated label names

        **Search:** Free-text search in titles and descriptions

        ## Returned Data

        The tool returns a JSON object containing:
        - **total_count**: Total number of matching results (may be null)
        - **offset**: Number of results skipped
        - **limit**: Maximum results requested
        - **items**: Array of merge request data, each with:
          - **iid**: MR internal ID
          - **title**: MR title
          - **state**: Current state (opened, closed, merged)
          - **draft**: Whether the MR is a draft
          - **project**: Project path
          - **author**: Creator username
          - **assignees**: List of assigned usernames
          - **reviewers**: List of reviewer usernames
          - **labels**: List of label names
          - **source_branch**: Source branch name
          - **target_branch**: Target branch name
          - **merge_status**: Whether the MR can be merged
          - **created_at**: Creation timestamp
          - **updated_at**: Last update timestamp
          - **merged_at**: Merge timestamp (if merged)
          - **url**: Direct link to the MR

        Returns:
            JSON string with total_count and items array
        """
        try:
            normalized_project = validate_project_path(project)
            gitlab_service = GitLabService(gitlab_url=gitlab_url)

            labels_list = (
                [lbl.strip() for lbl in labels.split(",") if lbl.strip()]
                if labels
                else None
            )

            results = gitlab_service.search_merge_requests(
                normalized_project,
                search,
                state,
                labels_list,
                max_results,
                offset,
            )

            return json.dumps(results, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_gitlab_mr_diff(
        project: Annotated[
            str,
            Field(
                description="GitLab project path (e.g., gitlab-org/gitlab) or numeric project ID"
            ),
        ],
        mr_iid: Annotated[
            int,
            Field(description="Merge request internal ID", ge=1),
        ],
        gitlab_url: Annotated[
            str | None,
            Field(
                description="GitLab instance URL (e.g., https://gitlab.cee.redhat.com). Overrides GITLAB_URL env var. Defaults to https://gitlab.com"
            ),
        ] = None,
        max_files: Annotated[
            int,
            Field(
                description="Maximum number of files to return (default: 100, max: 500)",
                ge=1,
                le=500,
            ),
        ] = 100,
        offset: Annotated[
            int,
            Field(
                description="Number of files to skip for pagination (default: 0)",
                ge=0,
            ),
        ] = 0,
    ) -> str:
        """Get the diff/patch for a GitLab merge request.

        This tool retrieves the unified diff for each file changed in a merge request,
        along with MR summary information.

        ## Authentication Required

        This tool requires GitLab API authentication. Set the following environment variables:
        - `GITLAB_TOKEN`: Your GitLab personal access token
        - `GITLAB_URL`: GitLab instance URL (default: https://gitlab.com)
        - `GITLAB_SSL_VERIFY`: SSL verification (default: true). Set to `false` for self-signed certificates (e.g., internal GitLab instances), or to a CA bundle path.

        ## Project Format

        The project path should be in the format `group/project`:
        - Examples: `gitlab-org/gitlab`, `mygroup/myproject`
        - Nested groups: `group/subgroup/project`
        - Numeric IDs are also accepted

        ## Merge Request IID

        The merge request internal ID (the number after the ! in GitLab URLs):
        - Example: For https://gitlab.com/group/project/-/merge_requests/42, use 42

        ## Returned Data

        The tool returns a JSON object containing:
        - **iid**: MR internal ID
        - **title**: MR title
        - **state**: Current state (opened, closed, merged)
        - **draft**: Whether the MR is a draft
        - **source_branch**: Source branch name
        - **target_branch**: Target branch name
        - **additions**: Total lines added (computed from diffs)
        - **deletions**: Total lines deleted (computed from diffs)
        - **changed_files**: Total number of changed files
        - **url**: Direct link to the MR
        - **files**: Array of file objects, each containing:
          - **filename**: Path of the file
          - **status**: File status (added, modified, removed, renamed)
          - **additions**: Lines added in this file
          - **deletions**: Lines deleted in this file
          - **diff**: Unified diff content (null for binary files)
          - **old_filename**: Previous path (only for renames)
        - **files_returned**: Number of files included in response
        - **total_files**: Total number of files changed in the MR
        - **offset**: Number of files skipped
        - **truncated**: Whether more files remain (only present if true)

        Returns:
            JSON string with MR diff data
        """
        try:
            normalized_project = validate_project_path(project)
            gitlab_service = GitLabService(gitlab_url=gitlab_url)
            mr_diff = gitlab_service.get_mr_diff(
                normalized_project, mr_iid, max_files, offset
            )
            return json.dumps(mr_diff, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_gitlab_project_info(
        project: Annotated[
            str,
            Field(
                description="GitLab project path (e.g., gitlab-org/gitlab) or numeric project ID"
            ),
        ],
        gitlab_url: Annotated[
            str | None,
            Field(
                description="GitLab instance URL (e.g., https://gitlab.cee.redhat.com). Overrides GITLAB_URL env var. Defaults to https://gitlab.com"
            ),
        ] = None,
    ) -> str:
        """Get GitLab project information.

        This tool retrieves basic information about a GitLab project including
        name, description, namespace, statistics, and metadata.

        ## Authentication Required

        This tool requires GitLab API authentication. Set the following environment variables:
        - `GITLAB_TOKEN`: Your GitLab personal access token
        - `GITLAB_URL`: GitLab instance URL (default: https://gitlab.com)
        - `GITLAB_SSL_VERIFY`: SSL verification (default: true). Set to `false` for self-signed certificates (e.g., internal GitLab instances), or to a CA bundle path.

        ## Project Format

        The project path should be in the format `group/project`:
        - Examples: `gitlab-org/gitlab`, `mygroup/myproject`
        - Nested groups: `group/subgroup/project`
        - Numeric IDs are also accepted

        ## Returned Data

        The tool returns a JSON object containing:
        - **name**: Project name
        - **path_with_namespace**: Full project path (group/project)
        - **description**: Project description
        - **namespace**: Namespace/group path
        - **visibility**: Visibility level (public, internal, private)
        - **default_branch**: Default branch name
        - **stars**: Number of stars
        - **forks**: Number of forks
        - **open_issues_count**: Number of open issues
        - **topics**: List of project topics/tags
        - **created_at**: Creation timestamp
        - **last_activity_at**: Last activity timestamp
        - **url**: Direct link to the project

        Returns:
            JSON string with project information
        """
        try:
            normalized_project = validate_project_path(project)
            gitlab_service = GitLabService(gitlab_url=gitlab_url)
            project_info = gitlab_service.get_project_info(normalized_project)
            return json.dumps(project_info, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
