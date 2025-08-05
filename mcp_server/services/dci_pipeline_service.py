"""DCI pipeline service for managing pipelines."""

import sys
from typing import Any

from dciclient.v1.api import pipeline

from .dci_base_service import DCIBaseService


class DCIPipelineService(DCIBaseService):
    """Service class for DCI pipeline operations."""

    def get_pipeline(self, pipeline_id: str) -> Any:
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
            if hasattr(result, "json"):
                return result.json()
            return result
        except Exception as e:
            print(f"Error getting pipeline {pipeline_id}: {e}")
            return None

    def query_pipelines(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        sort: str | None = None,
    ) -> list:
        """
        List pipelines using the advanced query syntax.

        Args:
            query: query criteria (e.g., "and(ilike(name,test),contains(tags,ga))")
            limit: Maximum number of pipelines to return (default: 50)
            offset: Number of pipelines to skip (default: 0)
            sort: Sort criteria (e.g., "-created_at")

        Returns:
            A dictionary with pipelines data or an empty dictionary on error
        """
        try:
            context = self._get_dci_context()
            return pipeline.list(
                context, query=query, limit=limit, offset=offset, sort=sort
            ).json()
        except Exception as e:
            print(f"Error listing pipelines: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            return {"error": str(e), "message": "Failed to list pipelines."}

    def list_pipelines(
        self,
        limit: int | None = None,
        offset: int | None = None,
        where: str | None = None,
        sort: str | None = None,
    ) -> list:
        """
        List pipelines with optional filtering and pagination.

        Args:
            limit: Maximum number of pipelines to return
            offset: Number of pipelines to skip
            where: Filter criteria (e.g., "name:test")
            sort: Sort criteria (e.g., "-created_at")

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
            if hasattr(result, "json"):
                data = result.json()
                return data.get("pipelines", []) if isinstance(data, dict) else []
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error listing pipelines: {e}")
            return []

    def get_pipeline_jobs(self, pipeline_id: str) -> Any:
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
            if hasattr(result, "json"):
                data = result.json()
                return data.get("jobs", []) if isinstance(data, dict) else []
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error getting jobs for pipeline {pipeline_id}: {e}")
            return []
