"""MCP tools for DCI job operations."""

import json

from fastmcp import FastMCP

from ..services.dci_job_service import DCIJobService


def register_job_tools(mcp: FastMCP) -> None:
    """Register job-related tools with the MCP server."""

    @mcp.tool()
    async def get_dci_job(job_id: str) -> str:
        """
        Get a specific DCI job by ID.

        Args:
            job_id: The ID of the job to retrieve

        Returns:
            JSON string with job information
        """
        try:
            service = DCIJobService()
            result = service.get_job(job_id)

            if result:
                return json.dumps(result, indent=2)
            else:
                return json.dumps({"error": f"Job {job_id} not found"}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_dci_jobs(
        limit: int = 50, offset: int = 0, where: str = "", sort: str = ""
    ) -> str:
        """
        List DCI jobs with optional filtering and pagination.

        Args:
            limit: Maximum number of jobs to return (default: 50)
            offset: Number of jobs to skip (default: 0)
            where: Filter criteria (e.g., "state:eq:active")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            JSON string with list of jobs
        """
        try:
            service = DCIJobService()

            # Convert empty strings to None for optional parameters
            where_filter = where if where else None
            sort_criteria = sort if sort else None

            result = service.list_jobs(
                limit=limit, offset=offset, where=where_filter, sort=sort_criteria
            )

            return json.dumps(
                {
                    "jobs": result,
                    "count": len(result),
                    "limit": limit,
                    "offset": offset,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_job_files(job_id: str) -> str:
        """
        List files associated with a specific DCI job.

        Args:
            job_id: The ID of the job

        Returns:
            JSON string with list of job files
        """
        try:
            service = DCIJobService()
            result = service.list_job_files(job_id)

            return json.dumps(
                {"job_id": job_id, "files": result, "count": len(result)}, indent=2
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_job_results(job_id: str) -> str:
        """
        List results associated with a specific DCI job.

        Args:
            job_id: The ID of the job

        Returns:
            JSON string with list of job results
        """
        try:
            service = DCIJobService()
            result = service.list_job_results(job_id)

            return json.dumps(
                {"job_id": job_id, "results": result, "count": len(result)}, indent=2
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
