"""MCP tools for DCI team operations."""

import json

from fastmcp import FastMCP

from ..services.dci_team_service import DCITeamService


def register_team_tools(mcp: FastMCP) -> None:
    """Register team-related tools with the MCP server."""

    @mcp.tool()
    async def get_dci_team(team_id: str) -> str:
        """
        Get a specific DCI team by ID.

        Args:
            team_id: The ID of the team to retrieve

        Returns:
            JSON string with team information
        """
        try:
            service = DCITeamService()
            result = service.get_team(team_id)

            if result:
                return json.dumps(result, indent=2)
            else:
                return json.dumps({"error": f"Team {team_id} not found"}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_dci_teams(
        limit: int = 50, offset: int = 0, where: str = "", sort: str = ""
    ) -> str:
        """
        List DCI teams with optional filtering and pagination.

        Args:
            limit: Maximum number of teams to return (default: 50)
            offset: Number of teams to skip (default: 0)
            where: Filter criteria (e.g., "name:like:qa")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            JSON string with list of teams
        """
        try:
            service = DCITeamService()

            # Convert empty strings to None for optional parameters
            where_filter = where if where else None
            sort_criteria = sort if sort else None

            result = service.list_teams(
                limit=limit, offset=offset, where=where_filter, sort=sort_criteria
            )

            return json.dumps(
                {
                    "teams": result,
                    "count": len(result),
                    "limit": limit,
                    "offset": offset,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
