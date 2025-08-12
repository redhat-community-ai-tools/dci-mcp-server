"""MCP tools for DCI pipeline operations."""

import json
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.dci_pipeline_service import DCIPipelineService


def register_pipeline_tools(mcp: FastMCP) -> None:
    """Register pipeline-related tools with the MCP server."""

    @mcp.tool()
    async def query_dci_pipelines(
        query: Annotated[
            str,
            Field(
                description="search criteria (e.g., and(ilike(name,test),contains(tags,ga))"
            ),
        ],
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
        fields: Annotated[
            list[str],
            Field(
                description="List of fields to return. Fields are the one listed in the query description and responses. Must be specified as a list of strings. If empty, no fields are returned.",
            ),
        ] = [],
    ) -> str:
        """
        Lookup DCI pipelines with an advanced query language.

        The query language is based on this DSL:

            eq(<field>,<value>) to lookup resources with a <field> having the value <value>.

            You can use the comparison functions gt (greater than), ge (greater or equal),
            lt (less than) or le (less or equal) using the same syntax as eq: <op>(<field>,<value>).

            like(<field>,<value with percent>) and ilike(<field>,<value with percent>)
            to lookup a field with a SQL glob like way. For example, to get the pipelines
            with a specific name pattern, use like(name,test-%).

            contains(<field>,<value1>,...) and not_contains(<field>,<value1>,...)
            to lookup elements in an array. This is useful mainly for tags.

            and(<op1>(...),<op2>(...)), or(<op1>(...),<op2>(...)) and not(<op>) allow
            to build nested boolean queries.

            null(<field>) to lookup resources with a field having a NULL value.

        Here are all the fields of a DCI pipeline that can be used in the query:

            - id: unique identifier

            - name: name of the pipeline

            - created_at: The creation timestamp. Use `today` tool to compute relative dates.

            - updated_at: The last update timestamp. Use `today` tool to compute relative dates.

            - tags: list of tags associated with the pipeline.

        **Counting Pipelines**: To get the total count of pipelines matching a query, set `limit=1` and read the `count` field in the `_meta` section of the response.

        **Example for counting pipelines by name**:
        ```json
        {
          "query": "eq(name,test-pipeline)",
          "limit": 1,
          "offset": 0,
          "fields": []
        }
        ```
        This will return a response like:
        ```json
        {
          "pipelines": [],
          "_meta": {"count": 3},
          ...
        }
        ```
        The total count is 3 pipelines.

        Returns:
            JSON string with list of pipelines and pagination info
        """
        try:
            service = DCIPipelineService()

            result = service.query_pipelines(
                query=query, sort=sort, limit=limit, offset=offset
            )

            if isinstance(fields, list) and fields:
                # Filter the result to only include specified fields
                if "pipelines" in result:
                    filtered_result = [
                        {field: pipeline.get(field) for field in fields}
                        for pipeline in result["pipelines"]
                    ]
                    result["pipelines"] = filtered_result
            elif not fields:
                result["pipelines"] = []

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_pipeline_jobs(pipeline_id: str) -> str:
        """
        Get jobs associated with a specific DCI pipeline.

        Args:
            pipeline_id: The ID of the pipeline

        Returns:
            JSON string with list of pipeline jobs
        """
        try:
            service = DCIPipelineService()
            result = service.get_pipeline_jobs(pipeline_id)

            return json.dumps(
                {"pipeline_id": pipeline_id, "jobs": result, "count": len(result)},
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
