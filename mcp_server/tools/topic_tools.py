"""MCP tools for DCI topic operations."""

import json

from fastmcp import FastMCP

from ..services.dci_topic_service import DCITopicService
from ..utils.pagination import fetch_all_with_progress


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
        fetch_all: bool = True, where: str = "", sort: str = ""
    ) -> str:
        """
        List DCI topics with optional filtering and automatic pagination.

        Args:
            fetch_all: Whether to fetch all topics (default: True)
            where: Filter criteria (e.g., "name:like:kernel")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            JSON string with list of topics and pagination info
        """
        try:
            service = DCITopicService()

            # Convert empty strings to None for optional parameters
            where_filter = where if where else None
            sort_criteria = sort if sort else None

            if fetch_all:
                # Fetch all topics with pagination
                result = fetch_all_with_progress(
                    service.list_topics,
                    where=where_filter,
                    sort=sort_criteria,
                    page_size=50,
                    max_pages=100,
                )

                return json.dumps(
                    {
                        "topics": result["results"],
                        "total_count": result["total_count"],
                        "pages_fetched": result["pages_fetched"],
                        "page_size": result["page_size"],
                        "reached_end": result["reached_end"],
                        "pagination_info": result,
                    },
                    indent=2,
                )
            else:
                # Fetch just the first page
                result = service.list_topics(
                    limit=50, offset=0, where=where_filter, sort=sort_criteria
                )

                return json.dumps(
                    {
                        "topics": result,
                        "count": len(result),
                        "limit": 50,
                        "offset": 0,
                        "note": "First page only. Use fetch_all=True for all results.",
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
