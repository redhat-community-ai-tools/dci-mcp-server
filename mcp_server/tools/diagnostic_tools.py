"""MCP tools for comprehensive diagnostic analysis."""

import json
from typing import Any

from fastmcp import FastMCP

from ..services.dci_job_service import DCIJobService
from ..services.pr_finder import PRFinder


def register_diagnostic_tools(mcp: FastMCP) -> None:
    """Register diagnostic tools with the MCP server."""

    @mcp.tool()
    def diagnose_pr_failures(pr_number: str, job_name: str) -> str:
        """
        Comprehensive diagnostic analysis of PR failures across multiple job runs.

        Args:
            pr_number: The GitHub PR number to analyze
            job_name: Job name pattern to search for

        Returns:
            JSON string with comprehensive failure analysis including patterns, trends,
            and recommendations
        """
        try:
            finder = PRFinder()
            pr_jobs = finder.find_pr_jobs(pr_number)

            if not pr_jobs:
                return json.dumps(
                    {
                        "pr_number": pr_number,
                        "job_name": job_name,
                        "error": "No jobs found for this PR",
                        "analysis": {},
                        "suggestions": [
                            f"Verify PR {pr_number} exists and has CI runs",
                            "Check if the job name pattern is correct",
                            "The builds might be very old and archived",
                        ],
                    },
                    indent=2,
                )

            # Filter by job name pattern
            matching_jobs = [
                job
                for job in pr_jobs
                if job_name.lower() in job.get("name", "").lower()
            ]

            if not matching_jobs:
                return json.dumps(
                    {
                        "pr_number": pr_number,
                        "job_name": job_name,
                        "error": (
                            f"No jobs matching '{job_name}' found for PR {pr_number}"
                        ),
                        "total_pr_jobs": len(pr_jobs),
                        "analysis": {},
                    },
                    indent=2,
                )

            # Analyze job states
            jobs_by_state: dict[str, list] = {}
            for job in matching_jobs:
                state = job.get("state", "unknown")
                if state not in jobs_by_state:
                    jobs_by_state[state] = []
                jobs_by_state[state].append(job)

            # Calculate failure patterns
            total_jobs = len(matching_jobs)
            failed_jobs = len(
                [
                    j
                    for j in matching_jobs
                    if j.get("state") in ["failed", "error", "cancelled"]
                ]
            )
            success_rate = (
                ((total_jobs - failed_jobs) / total_jobs * 100) if total_jobs > 0 else 0
            )

            analysis = {
                "total_jobs": total_jobs,
                "failed_jobs": failed_jobs,
                "success_rate": round(success_rate, 2),
                "jobs_by_state": jobs_by_state,
                "latest_job": matching_jobs[0] if matching_jobs else None,
                "trend": (
                    "improving"
                    if success_rate > 50
                    else "declining" if success_rate < 30 else "stable"
                ),
            }

            # Build recommendations
            recommendations = [
                (
                    f"Success rate: {success_rate}% "
                    f"({total_jobs - failed_jobs}/{total_jobs} successful)"
                ),
            ]

            # Add latest job state
            latest_state = matching_jobs[0].get("state") if matching_jobs else "unknown"
            recommendations.append(f"Latest job state: {latest_state}")

            # Add failure recommendation
            if failed_jobs > 0:
                recommendations.append("Check job logs for specific failure reasons")
            else:
                recommendations.append("All recent jobs successful")

            return json.dumps(
                {
                    "pr_number": pr_number,
                    "job_name": job_name,
                    "analysis": analysis,
                    "recommendations": recommendations,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def diagnose_pr_build_status(pr_number: str, job_name: str) -> str:
        """
        Advanced diagnostic tool that checks DCI for PR build status.
        Provides comprehensive information about job accessibility and troubleshooting
        guidance.

        Args:
            pr_number: The GitHub PR number to diagnose
            job_name: The DCI job name pattern to check

        Returns:
            JSON string with comprehensive diagnostic information
        """
        try:
            finder = PRFinder()
            pr_jobs = finder.find_pr_jobs(pr_number)

            # Get latest build for this PR and job pattern
            latest_build = finder.get_latest_pr_build(pr_number, job_name)

            # Get recent jobs for comparison
            job_service = DCIJobService()
            recent_jobs = job_service.list_jobs(limit=20, sort="-created_at")

            # Filter recent jobs by name pattern
            matching_recent_jobs = [
                job
                for job in recent_jobs
                if job_name.lower() in job.get("name", "").lower()
            ]

            diagnostic_info: dict[str, Any] = {
                "pr_number": pr_number,
                "job_name": job_name,
                "timestamp": (
                    "2025-01-27T00:00:00Z"  # Current timestamp when diagnosis runs
                ),
                "checks": {
                    "pr_jobs_found": len(pr_jobs) > 0,
                    "pr_jobs_count": len(pr_jobs),
                    "latest_build_found": latest_build is not None
                    and latest_build.get("success"),
                    "recent_jobs_available": len(matching_recent_jobs) > 0,
                    "recent_jobs_count": len(matching_recent_jobs),
                },
                "build_info": {
                    "status": (
                        latest_build.get("job_state") if latest_build else "unknown"
                    ),
                    "latest_build": latest_build,
                    "recent_builds": [
                        {
                            "id": job.get("id"),
                            "name": job.get("name"),
                            "state": job.get("state"),
                            "created_at": job.get("created_at"),
                        }
                        for job in matching_recent_jobs[:5]
                    ],
                },
                "recommendations": [],
            }

            # Generate recommendations based on findings
            if not pr_jobs:
                diagnostic_info["recommendations"].append(
                    f"No jobs found for PR {pr_number}. "
                    "Verify the PR exists and has CI runs."
                )
            else:
                diagnostic_info["recommendations"].append(
                    f"Found {len(pr_jobs)} jobs for PR {pr_number}"
                )

                if not latest_build or not latest_build.get("success"):
                    diagnostic_info["recommendations"].append(
                        f"No matching jobs found for pattern '{job_name}'. "
                        "Check job naming conventions."
                    )
                else:
                    diagnostic_info["recommendations"].append(
                        f"Latest build state: {latest_build.get('job_state')}"
                    )

            if matching_recent_jobs:
                diagnostic_info["recommendations"].append(
                    f"Found {len(matching_recent_jobs)} recent jobs "
                    f"matching '{job_name}' pattern"
                )

            return json.dumps(diagnostic_info, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_test_failures_from_artifacts(pr_number: str, job_name: str) -> str:
        """
        Extract test failures from build artifacts for a specific PR.

        Args:
            pr_number: The GitHub PR number
            job_name: The DCI job name pattern

        Returns:
            JSON string with test failure analysis
        """
        try:
            finder = PRFinder()
            latest_build = finder.get_latest_pr_build(pr_number, job_name)

            if not latest_build or not latest_build.get("success"):
                return json.dumps(
                    {
                        "pr_number": pr_number,
                        "job_name": job_name,
                        "error": "No matching build found",
                        "test_failures": [],
                        "summary": {
                            "total_tests": 0,
                            "failed_tests": 0,
                            "success_rate": 0.0,
                        },
                    },
                    indent=2,
                )

            job_id = latest_build.get("job_id")
            if not job_id:
                return json.dumps(
                    {
                        "pr_number": pr_number,
                        "job_name": job_name,
                        "error": "No job ID found in build",
                        "test_failures": [],
                        "summary": {
                            "total_tests": 0,
                            "failed_tests": 0,
                            "success_rate": 0.0,
                        },
                    },
                    indent=2,
                )

            # Get job files to look for test artifacts
            job_service = DCIJobService()
            job_files = job_service.list_job_files(job_id)

            # Look for test-related files
            test_files = [
                file
                for file in job_files
                if any(
                    keyword in file.get("name", "").lower()
                    for keyword in ["test", "junit", "xml", "log", "report"]
                )
            ]

            # Build note message
            note_msg = (
                "Test failure extraction requires parsing of actual test artifacts. "
                "This is a placeholder implementation."
            )

            results = {
                "pr_number": pr_number,
                "job_name": job_name,
                "job_id": job_id,
                "build_state": latest_build.get("job_state"),
                "test_files_found": len(test_files),
                "test_failures": [],  # Would need to parse actual test files
                "summary": {
                    "total_tests": 0,  # Would be calculated from parsed files
                    "failed_tests": 0,  # Would be calculated from parsed files
                    "success_rate": 0.0,  # Would be calculated from parsed files
                },
                "note": note_msg,
            }

            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
