#
# Copyright (C) 2025 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""DCI topic service for managing topics."""

from typing import Any

from dciclient.v1.api import topic

from .dci_base_service import DCIBaseService


class DCITopicService(DCIBaseService):
    """Service class for DCI topic operations."""

    def query_topics(
        self,
        limit: int | None = None,
        offset: int | None = None,
        query: str | None = None,
        sort: str | None = None,
    ) -> list:
        """
        Query topics with optional filtering, sorting, and pagination.

        Args:
            limit: Maximum number of topics to return
            offset: Number of topics to skip
            query: Filter criteria (e.g., "eq(name,DCI)")
            sort: Sort criteria (e.g., "-created_at")

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

            return topic.list(
                context, limit=limit, offset=offset, query=query, sort=sort
            ).json()
        except Exception as e:
            print(f"Error listing topics: {e}")
            return []

    def get_topic_components(self, topic_id: str) -> Any:
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
            if hasattr(result, "json"):
                data = result.json()
                return data.get("components", []) if isinstance(data, dict) else []
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error getting components for topic {topic_id}: {e}")
            return []

    def get_topic_jobs_from_components(self, topic_id: str) -> Any:
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
            if hasattr(result, "json"):
                data = result.json()
                return data.get("jobs", []) if isinstance(data, dict) else []
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error getting jobs from components for topic {topic_id}: {e}")
            return []
