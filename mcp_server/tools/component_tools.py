"""MCP tools for DCI component operations."""

import json

from fastmcp import FastMCP

from ..services.dci_component_service import DCIComponentService


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
        limit: int = 50, offset: int = 0, where: str = "", sort: str = ""
    ) -> str:
        """
        List DCI components with optional filtering and pagination.

        Args:
            limit: Maximum number of components to return (default: 50)
            offset: Number of components to skip (default: 0)
            where: Filter criteria (e.g., "name:like:kernel")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            JSON string with list of components
        """
        try:
            service = DCIComponentService()

            # Convert empty strings to None for optional parameters
            where_filter = where if where else None
            sort_criteria = sort if sort else None

            result = service.list_components(
                limit=limit, offset=offset, where=where_filter, sort=sort_criteria
            )

            return json.dumps(
                {
                    "components": result,
                    "count": len(result),
                    "limit": limit,
                    "offset": offset,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
