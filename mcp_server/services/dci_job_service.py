"""DCI job service for managing jobs."""

from typing import Any

from dciclient.v1.api import job

from .dci_base_service import DCIBaseService


class DCIJobService(DCIBaseService):
    """Service class for DCI job operations."""

    def get_job(self, job_id: str) -> Any:
        """
        Get a specific job by ID.

        Args:
            job_id: The ID of the job to retrieve

        Returns:
            Job data as dictionary, or None if not found
        """
        try:
            context = self._get_dci_context()
            result = job.get(context, job_id)
            if hasattr(result, "json"):
                return result.json()
            return result
        except Exception as e:
            print(f"Error getting job {job_id}: {e}")
            return None

    def list_jobs(
        self,
        limit: int | None = None,
        offset: int | None = None,
        where: str | None = None,
        sort: str | None = None,
    ) -> list:
        """
        List jobs with optional filtering and pagination.

        Args:
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            where: Filter criteria (e.g., "state:eq:active")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            List of job dictionaries
        """
        try:
            context = self._get_dci_context()
            # Provide default values for required parameters
            if limit is None:
                limit = 50
            if offset is None:
                offset = 0

            result = job.list(
                context, limit=limit, offset=offset, where=where, sort=sort
            )
            if hasattr(result, "json"):
                data = result.json()
                return data.get("jobs", []) if isinstance(data, dict) else []
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error listing jobs: {e}")
            return []

    def list_job_files(self, job_id: str) -> Any:
        """
        List files associated with a specific job.

        Args:
            job_id: The ID of the job

        Returns:
            List of file dictionaries
        """
        try:
            context = self._get_dci_context()
            result = job.list_files(context, job_id)
            if hasattr(result, "json"):
                data = result.json()
                return data.get("files", []) if isinstance(data, dict) else []
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error listing files for job {job_id}: {e}")
            return []

    def list_job_results(self, job_id: str) -> Any:
        """
        List results associated with a specific job.

        Args:
            job_id: The ID of the job

        Returns:
            List of result dictionaries
        """
        try:
            context = self._get_dci_context()
            result = job.list_results(context, job_id)
            if hasattr(result, "json"):
                data = result.json()
                return data.get("results", []) if isinstance(data, dict) else []
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error listing results for job {job_id}: {e}")
            return []
