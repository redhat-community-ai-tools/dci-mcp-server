"""MCP tools for DCI product operations."""

import json

from fastmcp import FastMCP

from ..services.dci_product_service import DCIProductService


def register_product_tools(mcp: FastMCP) -> None:
    """Register product-related tools with the MCP server."""

    @mcp.tool()
    async def get_dci_product(product_id: str) -> str:
        """
        Get a specific DCI product by ID.

        Args:
            product_id: The ID of the product to retrieve

        Returns:
            JSON string with product information
        """
        try:
            service = DCIProductService()
            result = service.get_product(product_id)

            if result:
                return json.dumps(result, indent=2)
            else:
                return json.dumps(
                    {"error": f"Product {product_id} not found"}, indent=2
                )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_dci_products(
        limit: int = 50, offset: int = 0, where: str = "", sort: str = ""
    ) -> str:
        """
        List DCI products with optional filtering and pagination.

        Args:
            limit: Maximum number of products to return (default: 50)
            offset: Number of products to skip (default: 0)
            where: Filter criteria (e.g., "name:like:rhel")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            JSON string with list of products
        """
        try:
            service = DCIProductService()

            # Convert empty strings to None for optional parameters
            where_filter = where if where else None
            sort_criteria = sort if sort else None

            result = service.list_products(
                limit=limit, offset=offset, where=where_filter, sort=sort_criteria
            )

            return json.dumps(
                {
                    "products": result,
                    "count": len(result),
                    "limit": limit,
                    "offset": offset,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_product_teams(product_id: str) -> str:
        """
        Get teams associated with a specific DCI product.

        Args:
            product_id: The ID of the product

        Returns:
            JSON string with list of product teams
        """
        try:
            service = DCIProductService()
            result = service.list_product_teams(product_id)

            return json.dumps(
                {"product_id": product_id, "teams": result, "count": len(result)},
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
