"""Tools for PR-related operations in the MCP DCI server."""

import json

from fastmcp import FastMCP

from ..services.pr_finder import PRFinder


def register_pr_tools(mcp: FastMCP) -> None:
    """Register PR-related tools with the MCP server."""

    @mcp.tool()
    async def get_pr_by_job_id(job_id: str) -> str:
        """
        Find the PR number and details associated with a specific DCI job.

        Args:
            job_id: The DCI job ID to analyze

        Returns:
            JSON string with PR information
        """
        try:
            from ..services.dci_job_service import DCIJobService

            # Get the job details
            job_service = DCIJobService()
            job = job_service.get_job(job_id)

            if not job:
                return json.dumps({"error": f"Job {job_id} not found"}, indent=2)

            # Extract PR information from job URL
            finder = PRFinder()
            job_url = job.get("url", "")
            pr_number = finder._extract_pr_from_url(job_url)

            if pr_number:
                return json.dumps(
                    {
                        "success": True,
                        "job_id": job_id,
                        "pr_number": pr_number,
                        "job_url": job_url,
                        "job_name": job.get("name"),
                        "job_state": job.get("state"),
                        "extraction_method": "url_analysis",
                    },
                    indent=2,
                )
            else:
                return json.dumps(
                    {
                        "success": False,
                        "job_id": job_id,
                        "error": "No PR information found in job URL",
                        "job_url": job_url,
                        "suggestions": [
                            "The job might not be associated with a PR",
                            "Check if the job URL contains PR information",
                            "The PR might be referenced differently",
                        ],
                    },
                    indent=2,
                )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_latest_dci_job_for_pr(
        pr_url: str, job_name: str | None, limit: int = 50
    ) -> str:
        """
        Get the latest DCI jobs for a specific GitHub PR URL.

        Args:
            pr_url: The GitHub PR number (e.g., "https://myorg/myrepo/pull/123")
            job_name: The DCI job name (optional to match any jobs)
            limit: Maximum number of jobs to return (default: 50)

        Returns:
            JSON string with build information including job_id, job_name, etc.
        """
        try:
            from ..services.dci_job_service import DCIJobService

            # Get the job details
            job_service = DCIJobService()
            jobs = job_service.list_jobs(
                where=f"url:{pr_url}" + (f",name:{job_name}" if job_name else ""),
                sort="-created_at",
                limit=limit,
            )

            if isinstance(jobs, list):
                return json.dumps(jobs, indent=2)
            else:
                return json.dumps(
                    {
                        "success": False,
                        "pr_url": pr_url,
                        "job_name": job_name,
                        "error": "No matching jobs found",
                        "suggestions": [
                            f"Verify PR {pr_url} exists and has DCI runs",
                            "Check if the job name pattern is correct",
                            "The build might be very old and archived",
                            "Try searching manually in the DCI dashboard",
                        ],
                    },
                    indent=2,
                )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_recent_job_status(job_name: str) -> str:
        """
        Get recent job status for a specific DCI job.

        Args:
            job_name: The DCI job name pattern

        Returns:
            JSON string with recent job status information
        """
        try:
            from ..services.dci_job_service import DCIJobService

            job_service = DCIJobService()
            jobs = job_service.list_jobs(limit=20, sort="created_at:desc")

            # Filter jobs by name pattern
            matching_jobs = [
                job for job in jobs if job_name.lower() in job.get("name", "").lower()
            ]

            if matching_jobs:
                return json.dumps(
                    {
                        "success": True,
                        "job_name": job_name,
                        "recent_jobs": [
                            {
                                "id": job.get("id"),
                                "name": job.get("name"),
                                "state": job.get("state"),
                                "created_at": job.get("created_at"),
                                "updated_at": job.get("updated_at"),
                                "url": job.get("url"),
                            }
                            for job in matching_jobs[:10]  # Limit to 10 most recent
                        ],
                        "total_matches": len(matching_jobs),
                    },
                    indent=2,
                )
            else:
                return json.dumps(
                    {
                        "success": False,
                        "job_name": job_name,
                        "error": "No matching jobs found",
                        "recent_jobs": [],
                    },
                    indent=2,
                )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_pr_builds_summary(pr_number: str) -> str:
        """
        Get a comprehensive summary of all builds for a specific PR.

        Args:
            pr_number: The GitHub PR number

        Returns:
            JSON string with build summary information
        """
        try:
            finder = PRFinder()
            result = finder.get_pr_builds_summary(pr_number)

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def find_pr_jobs(pr_number: str, limit: int = 50) -> str:
        """
        Find all jobs related to a specific PR by analyzing job URLs and metadata.

        Args:
            pr_number: The GitHub PR number
            limit: Maximum number of jobs to search through (default: 50)

        Returns:
            JSON string with list of PR-related jobs
        """
        try:
            finder = PRFinder()
            pr_jobs = finder.find_pr_jobs(pr_number, limit)

            return json.dumps(
                {
                    "success": True,
                    "pr_number": pr_number,
                    "jobs": [
                        {
                            "id": job.get("id"),
                            "name": job.get("name"),
                            "state": job.get("state"),
                            "created_at": job.get("created_at"),
                            "updated_at": job.get("updated_at"),
                            "url": job.get("url"),
                        }
                        for job in pr_jobs
                    ],
                    "total_matches": len(pr_jobs),
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
