"""DCI pipeline service for managing pipelines."""

from typing import Any

from dciclient.v1.api import pipeline

from .dci_base_service import DCIBaseService


class DCIPipelineService(DCIBaseService):
    """Service class for DCI pipeline operations."""

    def get_pipeline(self, pipeline_id: str) -> dict[str, Any] | None:
        """
        Get a specific pipeline by ID.

        Args:
            pipeline_id: The ID of the pipeline to retrieve

        Returns:
            Pipeline data as dictionary, or None if not found
        """
        try:
            context = self._get_dci_context()
            result = pipeline.get(context, pipeline_id)
            return result
        except Exception as e:
            print(f"Error getting pipeline {pipeline_id}: {e}")
            return None

    def list_pipelines(
        self,
        limit: int | None = None,
        offset: int | None = None,
        where: str | None = None,
        sort: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List pipelines with optional filtering and pagination.

        Args:
            limit: Maximum number of pipelines to return
            offset: Number of pipelines to skip
            where: Filter criteria (e.g., "name:like:test")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            List of pipeline dictionaries
        """
        try:
            context = self._get_dci_context()
            # Provide default values for required parameters
            if limit is None:
                limit = 50
            if offset is None:
                offset = 0

            result = pipeline.list(
                context, limit=limit, offset=offset, where=where, sort=sort
            )
            return result
        except Exception as e:
            print(f"Error listing pipelines: {e}")
            return []

    def get_pipeline_jobs(self, pipeline_id: str) -> list[dict[str, Any]]:
        """
        Get jobs associated with a specific pipeline.

        Args:
            pipeline_id: The ID of the pipeline

        Returns:
            List of job dictionaries
        """
        try:
            context = self._get_dci_context()
            result = pipeline.get_jobs(context, pipeline_id)
            return result
        except Exception as e:
            print(f"Error getting jobs for pipeline {pipeline_id}: {e}")
            return []
