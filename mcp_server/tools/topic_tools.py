"""MCP tools for DCI topic operations."""

import json

from fastmcp import FastMCP

from ..services.dci_topic_service import DCITopicService


def register_topic_tools(mcp: FastMCP) -> None:
    """Register topic-related tools with the MCP server."""

    @mcp.tool()
    async def get_dci_topic(topic_id: str) -> str:
        """
        Get a specific DCI topic by ID.

        Args:
            topic_id: The ID of the topic to retrieve

        Returns:
            JSON string with topic information
        """
        try:
            service = DCITopicService()
            result = service.get_topic(topic_id)

            if result:
                return json.dumps(result, indent=2)
            else:
                return json.dumps({"error": f"Topic {topic_id} not found"}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_dci_topics(
        limit: int = 50, offset: int = 0, where: str = "", sort: str = ""
    ) -> str:
        """
        List DCI topics with optional filtering and pagination.

        Args:
            limit: Maximum number of topics to return (default: 50)
            offset: Number of topics to skip (default: 0)
            where: Filter criteria (e.g., "name:like:kernel")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            JSON string with list of topics
        """
        try:
            service = DCITopicService()

            # Convert empty strings to None for optional parameters
            where_filter = where if where else None
            sort_criteria = sort if sort else None

            result = service.list_topics(
                limit=limit, offset=offset, where=where_filter, sort=sort_criteria
            )

            return json.dumps(
                {
                    "topics": result,
                    "count": len(result),
                    "limit": limit,
                    "offset": offset,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_topic_components(topic_id: str) -> str:
        """
        Get components associated with a specific DCI topic.

        Args:
            topic_id: The ID of the topic

        Returns:
            JSON string with list of topic components
        """
        try:
            service = DCITopicService()
            result = service.get_topic_components(topic_id)

            return json.dumps(
                {"topic_id": topic_id, "components": result, "count": len(result)},
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_topic_jobs_from_components(topic_id: str) -> str:
        """
        Get jobs from components associated with a specific DCI topic.

        Args:
            topic_id: The ID of the topic

        Returns:
            JSON string with list of jobs from topic components
        """
        try:
            service = DCITopicService()
            result = service.get_topic_jobs_from_components(topic_id)

            return json.dumps(
                {"topic_id": topic_id, "jobs": result, "count": len(result)}, indent=2
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
