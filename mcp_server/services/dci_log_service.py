"""DCI log service for retrieving job logs and artifacts."""

from typing import Any

import httpx

from ..config import (
    DEFAULT_TIMEOUT,
    get_dci_api_key,
    get_dci_user_id,
    get_dci_user_secret,
)
from ..models.types import LogResult


class DCILogService:
    """Service class for DCI log retrieval."""

    def __init__(self) -> None:
        """Initialize the DCI log service with authentication."""
        self.api_key = get_dci_api_key()
        self.user_id = get_dci_user_id()
        self.user_secret = get_dci_user_secret()

        # Set base URL for DCI API
        self.base_url = "https://api.distributed-ci.io/v1"

        if not self.api_key and not (self.user_id and self.user_secret):
            raise ValueError(
                "DCI authentication not configured. Set either DCI_API_KEY or "
                "DCI_USER_ID+DCI_USER_SECRET"
            )

    async def get_job_logs(self, job_id: str) -> LogResult:
        """Get logs for a specific DCI job.

        Args:
            job_id: The DCI job ID

        Returns:
            LogResult with log information
        """
        try:
            # First, get job details to understand the job structure
            from .dci_service import DCIService

            dci_service = DCIService()
            job = await dci_service.get_job_by_id(job_id)

            if not job:
                return LogResult(
                    build_id=job_id, job_name="unknown", error=f"Job {job_id} not found"
                )

            job_name = job.get("spec", {}).get("job", "unknown")

            # Try to get logs from DCI API
            logs = await self._get_logs_from_dci_api(job_id)

            if logs:
                return LogResult(
                    build_id=job_id,
                    job_name=job_name,
                    logs=logs,
                    log_url_used=f"{self.base_url}/jobs/{job_id}/logs",
                )

            # If no logs found, return error
            return LogResult(
                build_id=job_id, job_name=job_name, error="No logs found for this job"
            )

        except Exception as e:
            return LogResult(
                build_id=job_id,
                job_name="unknown",
                error=f"Failed to retrieve logs: {str(e)}",
            )

    async def _get_logs_from_dci_api(self, job_id: str) -> str | None:
        """Get logs directly from DCI API.

        Args:
            job_id: The DCI job ID

        Returns:
            Log content or None if not available
        """
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                # Try to get logs from DCI API
                response = await client.get(f"{self.base_url}/jobs/{job_id}/logs")

                if response.status_code == 200:
                    return response.text

                # Try alternative log endpoints
                alt_endpoints = [
                    f"{self.base_url}/jobs/{job_id}/artifacts/logs",
                    f"{self.base_url}/jobs/{job_id}/output",
                    f"{self.base_url}/jobs/{job_id}/console",
                ]

                for endpoint in alt_endpoints:
                    try:
                        response = await client.get(endpoint)
                        if response.status_code == 200:
                            return response.text
                    except Exception:
                        continue

                return None

        except Exception as e:
            print(f"Error getting logs from DCI API: {e}")
            return None

    async def get_job_artifacts(self, job_id: str) -> dict[str, Any]:
        """Get artifacts for a specific DCI job.

        Args:
            job_id: The DCI job ID

        Returns:
            Dictionary with artifact information
        """
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.get(f"{self.base_url}/jobs/{job_id}/artifacts")

                if response.status_code == 200:
                    return {
                        "success": True,
                        "artifacts": response.json(),
                        "job_id": job_id,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to get artifacts: {response.status_code}",
                        "job_id": job_id,
                    }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get artifacts: {str(e)}",
                "job_id": job_id,
            }
