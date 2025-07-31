"""Tools for PR-related operations in the MCP DCI server."""

import json
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field


def register_pr_tools(mcp: FastMCP) -> None:
    """Register PR-related tools with the MCP server."""

    @mcp.tool()
    async def get_latest_dci_job_for_pr(
        pr_url: Annotated[
            str,
            Field(
                description="The GitHub PR URL (e.g., 'https://github.com/myorg/myrepo/pull/123')"
            ),
        ],
        job_name: Annotated[
            str | None,
            Field(
                description="The DCI job name to filter by (optional - leave empty to get all jobs)"
            ),
        ] = None,
        limit: Annotated[
            int, Field(description="Maximum number of jobs to return", ge=1, le=200)
        ] = 20,
        offset: Annotated[
            int, Field(description="Number of jobs to skip for pagination", ge=0)
        ] = 0,
    ) -> str:
        """
        Get the latest DCI jobs for a specific GitHub PR URL.

        Args:
            pr_url: The GitHub PR URL (e.g., "https://github.com/myorg/myrepo/pull/123")
            job_name: The DCI job name to filter by (optional - leave empty to get all jobs)
            limit: Maximum number of jobs to return (default: 50, max: 200)
            offset: Number of jobs to skip for pagination (default: 0)
        Returns:
            JSON string with build information including job_id, job_name, etc.
        """
        try:
            from ..services.dci_job_service import DCIJobService

            # Get the job details
            job_service = DCIJobService()
            query = f"eq(url,{pr_url})"

            # Only add job name filter if job_name is provided and not empty
            if job_name and job_name.strip():
                query = f"and({query},ilike(name,%{job_name.strip()}%))"

            jobs = job_service.query_jobs(
                query=query,
                sort="-created_at",
                limit=limit,
                offset=offset,
            )

            return json.dumps(jobs, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
