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

"""MCP tools for DCI topic operations."""

import json
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.dci_topic_service import DCITopicService


def register_topic_tools(mcp: FastMCP) -> None:
    """Register topic-related tools with the MCP server."""

    @mcp.tool()
    async def query_dci_topics(
        query: Annotated[
            str,
            Field(
                description="search criteria (e.g., and(ilike(name,ptp),contains(tags,build:ga))"
            ),
        ] = "",
        sort: Annotated[str, Field(description="Sort criteria")] = "-created_at",
        limit: Annotated[
            int,
            Field(
                description="Maximum number of results to return for pagination (default 20, max 200). Use limit=1 to get count from metadata.",
                ge=1,
                le=200,
            ),
        ] = 20,
        offset: Annotated[int, Field(description="Offset for pagination", ge=0)] = 0,
    ) -> str:
        """
        Lookup DCI topics with an advanced query language.

        Uses the same query language as `query_dci_jobs`.

        Here are the fields of a DCI topic you can use in your query:

        - id: The unique identifier of the topic

        - name: The name of the topic

        - created_at: The creation date of the topic. Use the `today` tool if you need relative dates.

        - updated_at: The last update date of the topic. Use the `today` tool if you need relative dates.
        - product_id: The ID of the product associated with the topic. Use the `query_dci_products` tool to find product IDs.

        - next_topic_id: The ID of the next topic in the sequence. This is useful for knowing which topic to upgrade to.

        - export_control: boolean indicating if the topic is export controlled.

        - state: The state of the topic, which can be one of the following: active or inactive.

        Returns:
            JSON string with list of topics and pagination info
        """
        try:
            service = DCITopicService()
            result = service.query_topics(
                query=query, sort=sort, limit=limit, offset=offset
            )
            return json.dumps(result, indent=2)
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
