"""MCP tools for DCI pipeline operations."""

import json

from fastmcp import FastMCP

from ..services.dci_pipeline_service import DCIPipelineService
from ..utils.pagination import fetch_all_with_progress


def register_pipeline_tools(mcp: FastMCP) -> None:
    """Register pipeline-related tools with the MCP server."""

    @mcp.tool()
    async def get_dci_pipeline(pipeline_id: str) -> str:
        """
        Get a specific DCI pipeline by ID.

        Args:
            pipeline_id: The ID of the pipeline to retrieve

        Returns:
            JSON string with pipeline information
        """
        try:
            service = DCIPipelineService()
            result = service.get_pipeline(pipeline_id)

            if result:
                return json.dumps(result, indent=2)
            else:
                return json.dumps(
                    {"error": f"Pipeline {pipeline_id} not found"}, indent=2
                )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_dci_pipelines(
        fetch_all: bool = True, where: str = "", sort: str = ""
    ) -> str:
        """
        List DCI pipelines with optional filtering and automatic pagination.

        Args:
            fetch_all: Whether to fetch all pipelines (default: True)
            where: Filter criteria (e.g., "name:like:test")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            JSON string with list of pipelines and pagination info
        """
        try:
            service = DCIPipelineService()

            # Convert empty strings to None for optional parameters
            where_filter = where if where else None
            sort_criteria = sort if sort else None

            if fetch_all:
                # Fetch all pipelines with pagination
                result = fetch_all_with_progress(
                    service.list_pipelines,
                    where=where_filter,
                    sort=sort_criteria,
                    page_size=50,
                    max_pages=100,
                )

                return json.dumps(
                    {
                        "pipelines": result["results"],
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
                result = service.list_pipelines(
                    limit=50, offset=0, where=where_filter, sort=sort_criteria
                )
                if not isinstance(result, list):
                    result = []
                return json.dumps(
                    {
                        "pipelines": result,
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
    async def get_pipeline_jobs(pipeline_id: str) -> str:
        """
        Get jobs associated with a specific DCI pipeline.

        Args:
            pipeline_id: The ID of the pipeline

        Returns:
            JSON string with list of pipeline jobs
        """
        try:
            service = DCIPipelineService()
            result = service.get_pipeline_jobs(pipeline_id)

            return json.dumps(
                {"pipeline_id": pipeline_id, "jobs": result, "count": len(result)},
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
