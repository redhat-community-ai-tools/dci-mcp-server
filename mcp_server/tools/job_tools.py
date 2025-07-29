"""MCP tools for DCI job operations."""

import json

from fastmcp import FastMCP

from ..services.dci_job_service import DCIJobService
from ..utils.pagination import (
    MAX_PAGES_DEFAULT,
    PAGE_SIZE_DEFAULT,
    fetch_all_with_progress,
)


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
        fetch_all: bool = True, where: str = "", sort: str = ""
    ) -> str:
        """
        List DCI jobs with optional filtering and automatic pagination.

        Args:
            fetch_all: Whether to fetch all jobs (default: True)
            where: Filter criteria (e.g., "state:active",
                "team_id:615a5fb0-d6ac-4a5f-93de-99ffb73c7473")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            JSON string with list of jobs and pagination info
        """
        try:
            service = DCIJobService()

            # Convert empty strings to None for optional parameters
            where_filter = where if where else None
            sort_criteria = sort if sort else None

            if fetch_all:
                # Fetch all jobs with pagination
                result = fetch_all_with_progress(
                    service.list_jobs,
                    where=where_filter,
                    sort=sort_criteria,
                    page_size=PAGE_SIZE_DEFAULT,
                    max_pages=MAX_PAGES_DEFAULT,
                )

                return json.dumps(
                    {
                        "jobs": result["results"],
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
                result = service.list_jobs(
                    limit=50, offset=0, where=where_filter, sort=sort_criteria
                )
                if not isinstance(result, list):
                    result = []
                return json.dumps(
                    {
                        "jobs": result,
                        "count": len(result),
                        "limit": PAGE_SIZE_DEFAULT,
                        "offset": 0,
                        "note": "First page only. Use fetch_all=True for all results.",
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
