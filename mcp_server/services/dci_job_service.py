"""DCI job service for managing jobs."""

import sys
from typing import Any

from dciclient.v1.api import job

from .dci_base_service import DCIBaseService


class DCIJobService(DCIBaseService):
    """Service class for DCI job operations."""

    def list_jobs_advanced(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        sort: str | None = None,
    ) -> list:
        """
        List jobs using the advanced query syntax.

        Args:
            query: query criteria (e.g., "and(ilike(name,ptp),contains(tags,build:ga))")
            limit: Maximum number of jobs to return (default: 50)
            offset: Number of jobs to skip (default: 0)
            sort: Sort criteria (e.g., "-created_at")

        Returns:
            A dictionary with jobs data or an empty dictionary on error
        """
        try:
            context = self._get_dci_context()
            result = job.list(
                context, query=query, limit=limit, offset=offset, sort=sort
            )
            if hasattr(result, "json"):
                data = result.json()
                return data
            return result
        except Exception as e:
            print(f"Error listing jobs: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            return {}

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
