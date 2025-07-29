"""MCP tools for DCI pipeline operations."""

import json

from fastmcp import FastMCP

from ..services.dci_pipeline_service import DCIPipelineService


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
        limit: int = 50, offset: int = 0, where: str = "", sort: str = ""
    ) -> str:
        """
        List DCI pipelines with optional filtering and pagination.

        Args:
            limit: Maximum number of pipelines to return (default: 50)
            offset: Number of pipelines to skip (default: 0)
            where: Filter criteria (e.g., "name:like:test")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            JSON string with list of pipelines
        """
        try:
            service = DCIPipelineService()

            # Convert empty strings to None for optional parameters
            where_filter = where if where else None
            sort_criteria = sort if sort else None

            result = service.list_pipelines(
                limit=limit, offset=offset, where=where_filter, sort=sort_criteria
            )

            return json.dumps(
                {
                    "pipelines": result,
                    "count": len(result),
                    "limit": limit,
                    "offset": offset,
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
