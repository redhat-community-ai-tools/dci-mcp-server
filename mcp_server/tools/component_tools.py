"""MCP tools for DCI component operations."""

import json

from fastmcp import FastMCP

from ..services.dci_component_service import DCIComponentService
from ..utils.pagination import fetch_all_with_progress


def register_component_tools(mcp: FastMCP) -> None:
    """Register component-related tools with the MCP server."""

    @mcp.tool()
    async def get_dci_component(component_id: str) -> str:
        """
        Get a specific DCI component by ID.

        Args:
            component_id: The ID of the component to retrieve

        Returns:
            JSON string with component information
        """
        try:
            service = DCIComponentService()
            result = service.get_component(component_id)

            if result:
                return json.dumps(result, indent=2)
            else:
                return json.dumps(
                    {"error": f"Component {component_id} not found"}, indent=2
                )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_dci_components(
        fetch_all: bool = True, where: str = "", sort: str = ""
    ) -> str:
        """
        List DCI components with optional filtering and automatic pagination.

        Args:
            fetch_all: Whether to fetch all components (default: True)
            where: Filter criteria (e.g., "name:like:kernel")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            JSON string with list of components and pagination info
        """
        try:
            service = DCIComponentService()

            # Convert empty strings to None for optional parameters
            where_filter = where if where else None
            sort_criteria = sort if sort else None

            if fetch_all:
                # Fetch all components with pagination
                result = fetch_all_with_progress(
                    service.list_components,
                    where=where_filter,
                    sort=sort_criteria,
                    page_size=50,
                    max_pages=100,
                )

                return json.dumps(
                    {
                        "components": result["results"],
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
                result = service.list_components(
                    limit=50, offset=0, where=where_filter, sort=sort_criteria
                )

                return json.dumps(
                    {
                        "components": result,
                        "count": len(result),
                        "limit": 50,
                        "offset": 0,
                        "note": "First page only. Use fetch_all=True for all results.",
                    },
                    indent=2,
                )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
