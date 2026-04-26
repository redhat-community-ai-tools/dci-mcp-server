"""MCP tools for Jira introspection (filters, components, versions, boards, sprints)."""

import json
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.jira_service import JiraService


def register_jira_introspect_tools(mcp: FastMCP) -> None:
    """Register Jira introspection tools with the MCP server."""

    @mcp.tool()
    async def get_jira_filter(
        filter_id: Annotated[
            str,
            Field(description="Jira saved filter ID (numeric string)"),
        ],
    ) -> str:
        """Get a saved Jira filter's definition including its JQL query.

        Retrieves the filter name, JQL query, description, owner, and URL
        for a saved Jira filter by its numeric ID.

        Returns:
            JSON string with filter definition
        """
        try:
            jira_service = JiraService()
            result = jira_service.get_filter(filter_id.strip())
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_jira_favourite_filters() -> str:
        """List the authenticated user's favourite/saved Jira filters.

        Returns all filters marked as favourite by the current user,
        including their JQL queries, descriptions, and owners.

        Returns:
            JSON string with list of favourite filters
        """
        try:
            jira_service = JiraService()
            result = jira_service.get_favourite_filters()
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def search_jira_filters(
        filter_name: Annotated[
            str,
            Field(
                description="Filter name to search for (partial match, case-insensitive)"
            ),
        ],
    ) -> str:
        """Search for Jira filters by name.

        Finds saved filters whose name matches the search string.
        Useful when you know a filter's name but not its numeric ID.

        Returns:
            JSON string with list of matching filters
        """
        try:
            jira_service = JiraService()
            result = jira_service.search_filters(filter_name.strip())
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_jira_project_components(
        project_key: Annotated[
            str,
            Field(description="Jira project key (e.g., CILAB, OCP)"),
        ],
    ) -> str:
        """List components defined in a Jira project.

        Components are sub-sections of a project used to group issues.
        Returns each component's name, description, lead, and assignee type.

        Returns:
            JSON string with list of project components
        """
        try:
            project_key = project_key.strip().upper()
            jira_service = JiraService()
            result = jira_service.get_project_components(project_key)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_jira_project_versions(
        project_key: Annotated[
            str,
            Field(description="Jira project key (e.g., CILAB, OCP)"),
        ],
    ) -> str:
        """List versions defined in a Jira project.

        Returns each version's name, description, release status, archive status,
        and dates (start date, release date).

        Returns:
            JSON string with list of project versions
        """
        try:
            project_key = project_key.strip().upper()
            jira_service = JiraService()
            result = jira_service.get_project_versions(project_key)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_jira_issue_types_for_project(
        project_key: Annotated[
            str,
            Field(description="Jira project key (e.g., CILAB, OCP)"),
        ],
    ) -> str:
        """List issue types available in a Jira project.

        Returns the issue types configured for the project, including
        whether each type is a subtask and its description.

        Returns:
            JSON string with list of issue types
        """
        try:
            project_key = project_key.strip().upper()
            jira_service = JiraService()
            result = jira_service.get_issue_types_for_project(project_key)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_jira_boards(
        project_key: Annotated[
            str | None,
            Field(description="Filter by project key"),
        ] = None,
        board_type: Annotated[
            str | None,
            Field(description="Filter by board type: scrum or kanban"),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Filter by board name (partial match)"),
        ] = None,
        max_results: Annotated[
            int,
            Field(
                description="Maximum number of results (default: 50)",
                ge=1,
                le=200,
            ),
        ] = 50,
        offset: Annotated[
            int,
            Field(
                description="Start index for pagination (default: 0)",
                ge=0,
            ),
        ] = 0,
    ) -> str:
        """List Jira boards, optionally filtered by project, type, or name.

        Boards organize issues into sprints (Scrum) or columns (Kanban).
        Use the board ID from the results with list_jira_sprints to see sprints.

        Returns:
            JSON string with total count and list of boards
        """
        try:
            pk = project_key.strip().upper() if project_key else None
            jira_service = JiraService()
            result = jira_service.get_boards(
                project_key=pk,
                board_type=board_type,
                name=name,
                max_results=max_results,
                start_at=offset,
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_jira_sprints(
        board_id: Annotated[
            int,
            Field(description="Board ID (get from list_jira_boards)"),
        ],
        state: Annotated[
            str | None,
            Field(
                description="Filter by state: active, closed, future (comma-separated for multiple)"
            ),
        ] = None,
        max_results: Annotated[
            int,
            Field(
                description="Maximum number of results (default: 50)",
                ge=1,
                le=200,
            ),
        ] = 50,
        offset: Annotated[
            int,
            Field(
                description="Start index for pagination (default: 0)",
                ge=0,
            ),
        ] = 0,
    ) -> str:
        """List sprints for a Jira board.

        Returns sprints with their state, dates, and goal.
        Use list_jira_boards first to find the board ID.

        Returns:
            JSON string with total count and list of sprints
        """
        try:
            jira_service = JiraService()
            result = jira_service.get_sprints(
                board_id=board_id,
                state=state,
                max_results=max_results,
                start_at=offset,
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
