"""Service for interacting with DCI API and managing job information."""

from typing import Any

from dateutil.parser import parse as parse_date

from ..config import get_dci_api_key, get_dci_user_id, get_dci_user_secret
from ..models.types import ProwJob  # Reusing the same type for compatibility


class DCIService:
    """Service class for DCI API interactions."""

    def __init__(self) -> None:
        """Initialize the DCI service with authentication."""
        self.api_key = get_dci_api_key()
        self.user_id = get_dci_user_id()
        self.user_secret = get_dci_user_secret()

        if not self.api_key and not (self.user_id and self.user_secret):
            raise ValueError(
                "DCI authentication not configured. Set either DCI_API_KEY or "
                "DCI_USER_ID+DCI_USER_SECRET"
            )

    def _get_dci_context(self) -> Any:
        """Get DCI context for API calls."""
        from dciclient.v1.api.context import build_dci_context

        if self.api_key:
            # Use API key authentication
            return build_dci_context(
                dci_cs_url="https://api.distributed-ci.io", dci_api_key=self.api_key
            )
        else:
            # Use user ID/secret authentication
            return build_dci_context(
                dci_cs_url="https://api.distributed-ci.io",
                dci_user_id=self.user_id,
                dci_user_secret=self.user_secret,
            )

    async def get_all_jobs(self) -> list[ProwJob]:
        """Get all active DCI jobs.

        Returns:
            List of all DCI jobs from the API
        """
        try:
            context = self._get_dci_context()
            from dciclient.v1.api import job

            # Get all jobs
            jobs_data = job.list(context)

            # Convert DCI job format to ProwJob format for compatibility
            prow_jobs = []
            for dci_job in jobs_data:
                prow_job = self._convert_dci_to_prow_job(dci_job)
                if prow_job:
                    prow_jobs.append(prow_job)

            return prow_jobs
        except Exception as e:
            print(f"Error fetching DCI jobs: {e}")
            return []

    async def get_jobs_by_name(self, job_name: str) -> list[ProwJob]:
        """Get all jobs matching a specific job name.

        Args:
            job_name: The name of the job to filter for

        Returns:
            List of jobs matching the name, sorted by start time (newest first)
        """
        all_jobs = await self.get_all_jobs()

        # Filter by job name and ensure they have start time
        matching_jobs = [
            job
            for job in all_jobs
            if job.get("spec", {}).get("job") == job_name
            and "startTime" in job.get("status", {})
        ]

        # Sort by startTime descending
        matching_jobs.sort(
            key=lambda job: parse_date(job["status"]["startTime"]), reverse=True
        )

        return matching_jobs

    async def get_latest_job_for_name(self, job_name: str) -> Any:
        """Get the latest job for a specific job name.

        Args:
            job_name: The name of the job

        Returns:
            The most recent job or None if not found
        """
        jobs = await self.get_jobs_by_name(job_name)
        return jobs[0] if jobs else None

    async def get_job_by_id(self, job_id: str) -> Any:
        """Get a specific job by its ID.

        Args:
            job_id: The job ID to look for

        Returns:
            The job if found, None otherwise
        """
        try:
            context = self._get_dci_context()
            from dciclient.v1.api import job

            # Get specific job by ID
            dci_job = job.get(context, job_id)
            return self._convert_dci_to_prow_job(dci_job)
        except Exception as e:
            print(f"Error fetching DCI job {job_id}: {e}")
            return None

    async def get_jobs_for_pr(self, job_name: str, pr_number: str) -> list[ProwJob]:
        """Get all jobs for a specific PR.

        Args:
            job_name: The name of the job
            pr_number: The PR number to filter for

        Returns:
            List of jobs for the specified PR, sorted by start time (newest first)
        """
        jobs = await self.get_jobs_by_name(job_name)

        pr_jobs = []
        for job in jobs:
            refs = job.get("spec", {}).get("refs", {})
            pulls = refs.get("pulls", [])

            for pull in pulls:
                if str(pull.get("number", "")) == pr_number:
                    pr_jobs.append(job)
                    break

        return pr_jobs

    def _convert_dci_to_prow_job(self, dci_job: dict[str, Any]) -> Any:
        """Convert DCI job format to ProwJob format for compatibility.

        Args:
            dci_job: DCI job data

        Returns:
            ProwJob format data or None if conversion fails
        """
        try:
            # Extract basic job information
            job_id = dci_job.get("id")
            name = dci_job.get("name", "")
            state = dci_job.get("state", "unknown")
            created_at = dci_job.get("created_at")
            updated_at = dci_job.get("updated_at")

            # Build ProwJob compatible structure
            prow_job = {
                "metadata": {"name": job_id, "namespace": "dci"},
                "spec": {
                    "job": name,
                    "refs": {
                        "pulls": []  # DCI doesn't have PR info in the same format
                    },
                },
                "status": {
                    "state": state,
                    "startTime": created_at,
                    "completionTime": (
                        updated_at if state in ["success", "failure"] else None
                    ),
                    "url": f"https://api.distributed-ci.io/jobs/{job_id}",
                    "build_id": job_id,
                },
            }

            return prow_job
        except Exception as e:
            print(f"Error converting DCI job to ProwJob format: {e}")
            return None
