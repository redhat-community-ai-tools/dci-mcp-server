"""MCP tools for DCI team operations."""

import json

from fastmcp import FastMCP

from ..services.dci_team_service import DCITeamService
from ..utils.pagination import fetch_all_with_progress


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
        fetch_all: bool = True, where: str = "", sort: str = ""
    ) -> str:
        """
        List DCI teams with optional filtering and automatic pagination.

        Args:
            fetch_all: Whether to fetch all teams (default: True)
            where: Filter criteria (e.g., "name:DCI")
            sort: Sort criteria (e.g., "-created_at")

        Returns:
            JSON string with list of teams and pagination info
        """
        try:
            service = DCITeamService()

            # Convert empty strings to None for optional parameters
            where_filter = where if where else None
            sort_criteria = sort if sort else None

            if fetch_all:
                # Fetch all teams with pagination
                result = fetch_all_with_progress(
                    service.list_teams,
                    where=where_filter,
                    sort=sort_criteria,
                    page_size=50,
                    max_pages=100,
                )

                return json.dumps(
                    {
                        "teams": result["results"],
                        "total_count": result["total_count"],
                        "pages_fetched": result["pages_fetched"],
                        "page_size": result["page_size"],
                        "reached_end": result["reached_end"],
                        "pagination_info": result,
                    },
                    indent=2,
                )
            else:
                # Fetch just the first page
                result = service.list_teams(
                    limit=50, offset=0, where=where_filter, sort=sort_criteria
                )
                if not isinstance(result, list):
                    result = []
                return json.dumps(
                    {
                        "teams": result,
                        "count": len(result),
                        "limit": 50,
                        "offset": 0,
                        "note": "First page only. Use fetch_all=True for all results.",
                    },
                    indent=2,
                )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
