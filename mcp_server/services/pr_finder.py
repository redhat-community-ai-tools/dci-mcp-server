"""Service for finding PR builds by analyzing job URLs."""

import re
from typing import Any

from .dci_job_service import DCIJobService


class PRFinder:
    """Service for finding PR builds by analyzing job URLs in DCI jobs."""

    def __init__(self) -> None:
        """Initialize the PR finder with DCI job service."""
        self.job_service = DCIJobService()

    def _extract_pr_from_url(self, url: str) -> str | None:
        """
        Extract PR number from various URL formats.

        Args:
            url: The URL to analyze

        Returns:
            PR number as string, or None if not found
        """
        if not url:
            return None

        # Common GitHub PR URL patterns
        patterns = [
            r"github\.com/[^/]+/[^/]+/pull/(\d+)",  # github.com/org/repo/pull/123
            r"github\.com/[^/]+/[^/]+/issues/(\d+)",  # github.com/org/repo/issues/123
            r"/pull/(\d+)",  # /pull/123
            r"/issues/(\d+)",  # /issues/123
            r"pr/(\d+)",  # pr/123
            r"PR-(\d+)",  # PR-123
            r"#(\d+)",  # #123
        ]

        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _is_pr_job(self, job: dict[str, Any], target_pr: str) -> bool:
        """
        Check if a job is related to a specific PR.

        Args:
            job: The job dictionary
            target_pr: The PR number to look for

        Returns:
            True if the job is related to the PR, False otherwise
        """
        # Check job URL field
        job_url = job.get("url", "")
        if job_url:
            pr_from_url = self._extract_pr_from_url(job_url)
            if pr_from_url == target_pr:
                return True

        # Check job name for PR patterns
        job_name = job.get("name", "")
        if job_name:
            # Look for PR patterns in job name
            pr_patterns = [
                rf"pr-{target_pr}",
                rf"pull-{target_pr}",
                rf"#{target_pr}",
                rf"PR-{target_pr}",
            ]
            for pattern in pr_patterns:
                if re.search(pattern, job_name, re.IGNORECASE):
                    return True

        # Check job metadata for PR information
        metadata = job.get("metadata", {})
        if metadata:
            # Check various metadata fields that might contain PR info
            metadata_fields = ["pr_number", "pull_request", "pr", "issue"]
            for field in metadata_fields:
                if metadata.get(field) == target_pr:
                    return True

        return False

    def find_pr_jobs(self, pr_number: str, limit: int = 100) -> list[dict[str, Any]]:
        """
        Find jobs related to a specific PR by analyzing job URLs and metadata.

        Args:
            pr_number: The PR number to search for
            limit: Maximum number of jobs to search through

        Returns:
            List of jobs related to the PR
        """
        try:
            # Get recent jobs
            jobs = self.job_service.list_jobs(limit=limit, sort="created_at:desc")

            pr_jobs = []
            for job in jobs:
                if self._is_pr_job(job, pr_number):
                    pr_jobs.append(job)

            return pr_jobs
        except Exception as e:
            print(f"Error finding PR jobs: {e}")
            return []


# Convenience function for backward compatibility
async def smart_pr_build_finder(pr_number: str, job_name: str) -> dict[str, Any]:
    """
    Advanced PR build finder that uses DCI job analysis to find builds for PRs.

    Args:
        pr_number: The PR number to search for
        job_name: The name pattern of the DCI job

    Returns:
        Dictionary with build information and metadata about the search process
    """
    finder = PRFinder()
    result = finder.get_latest_pr_build(pr_number, job_name)

    if result and result.get("success"):
        return result
    else:
        return {
            "success": False,
            "pr_number": pr_number,
            "job_name": job_name,
            "error": "No matching builds found",
            "suggestions": [
                f"Verify PR {pr_number} exists and has CI runs",
                "Check if the job name pattern is correct",
                "The build might be very old and archived",
                "Try searching manually in the DCI dashboard",
            ],
        }
