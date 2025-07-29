"""DCI topic service for managing topics."""

from typing import Any

from dciclient.v1.api import topic

from .dci_base_service import DCIBaseService


class DCITopicService(DCIBaseService):
    """Service class for DCI topic operations."""

    def get_topic(self, topic_id: str) -> dict[str, Any] | None:
        """
        Get a specific topic by ID.

        Args:
            topic_id: The ID of the topic to retrieve

        Returns:
            Topic data as dictionary, or None if not found
        """
        try:
            context = self._get_dci_context()
            result = topic.get(context, topic_id)
            return result
        except Exception as e:
            print(f"Error getting topic {topic_id}: {e}")
            return None

    def list_topics(
        self,
        limit: int | None = None,
        offset: int | None = None,
        where: str | None = None,
        sort: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List topics with optional filtering and pagination.

        Args:
            limit: Maximum number of topics to return
            offset: Number of topics to skip
            where: Filter criteria (e.g., "name:like:kernel")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            List of topic dictionaries
        """
        try:
            context = self._get_dci_context()
            # Provide default values for required parameters
            if limit is None:
                limit = 50
            if offset is None:
                offset = 0

            result = topic.list(
                context, limit=limit, offset=offset, where=where, sort=sort
            )
            return result
        except Exception as e:
            print(f"Error listing topics: {e}")
            return []

    def get_topic_components(self, topic_id: str) -> list[dict[str, Any]]:
        """
        Get components associated with a specific topic.

        Args:
            topic_id: The ID of the topic

        Returns:
            List of component dictionaries
        """
        try:
            context = self._get_dci_context()
            result = topic.list_components(context, topic_id)
            return result
        except Exception as e:
            print(f"Error getting components for topic {topic_id}: {e}")
            return []

    def get_topic_jobs_from_components(self, topic_id: str) -> list[dict[str, Any]]:
        """
        Get jobs from components associated with a specific topic.

        Args:
            topic_id: The ID of the topic

        Returns:
            List of job dictionaries
        """
        try:
            context = self._get_dci_context()
            result = topic.get_jobs_from_components(context, topic_id)
            return result
        except Exception as e:
            print(f"Error getting jobs from components for topic {topic_id}: {e}")
            return []
