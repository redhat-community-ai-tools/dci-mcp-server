"""MCP tools for DCI product operations."""

import json

from fastmcp import FastMCP

from ..services.dci_product_service import DCIProductService
from ..utils.pagination import fetch_all_with_progress


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
        fetch_all: bool = True, where: str = "", sort: str = ""
    ) -> str:
        """
        List DCI products with optional filtering and automatic pagination.

        Args:
            fetch_all: Whether to fetch all products (default: True)
            where: Filter criteria (e.g., "name:like:rhel")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            JSON string with list of products and pagination info
        """
        try:
            service = DCIProductService()

            # Convert empty strings to None for optional parameters
            where_filter = where if where else None
            sort_criteria = sort if sort else None

            if fetch_all:
                # Fetch all products with pagination
                result = fetch_all_with_progress(
                    service.list_products,
                    where=where_filter,
                    sort=sort_criteria,
                    page_size=50,
                    max_pages=100,
                )

                return json.dumps(
                    {
                        "products": result["results"],
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
                result = service.list_products(
                    limit=50, offset=0, where=where_filter, sort=sort_criteria
                )

                return json.dumps(
                    {
                        "products": result,
                        "count": len(result),
                        "limit": 50,
                        "offset": 0,
                        "note": "First page only. Use fetch_all=True for all results.",
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
