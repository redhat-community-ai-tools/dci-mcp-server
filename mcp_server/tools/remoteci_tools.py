"""MCP tools for DCI remoteci operations."""

import json
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.dci_remoteci_service import DCIRemoteCIService


def register_remoteci_tools(mcp: FastMCP) -> None:
    """Register remoteci-related tools with the MCP server."""

    @mcp.tool()
    async def query_dci_remotecis(
        query: Annotated[
            str,
            Field(
                description="search criteria (e.g., and(ilike(name,dallas),contains(tags,ga))"
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
        Lookup DCI remotecis with an advanced query language.

        The query language is based on this DSL:

            eq(<field>,<value>) to lookup resources with a <field> having the value <value>.

            You can use the comparison functions gt (greater than), ge (greater or equal),
            lt (less than) or le (less or equal) using the same syntax as eq: <op>(<field>,<value>).

            like(<field>,<value with percent>) and ilike(<field>,<value with percent>)
            to lookup a field with a SQL glob like way. For example, to get the remotecis
            with a specific name pattern, use like(name,dallas-%).

            contains(<field>,<value1>,...) and not_contains(<field>,<value1>,...)
            to lookup elements in an array. This is useful mainly for tags.

            and(<op1>(...),<op2>(...)), or(<op1>(...),<op2>(...)) and not(<op>) allow
            to build nested boolean queries.

            null(<field>) to lookup resources with a field having a NULL value.

        Here are all the fields of a DCI remoteci that can be used in the query:

            - id: unique identifier

            - name: name of the remoteci (lab)

            - created_at: The creation timestamp. Use `today` tool to compute relative dates.

            - updated_at: The last update timestamp. Use `today` tool to compute relative dates.

            - tags: list of tags associated with the remoteci.

        **Counting Remotecis**: To get the total count of remotecis matching a query, set `limit=1` and read the `count` field in the `_meta` section of the response.

        **Example for counting remotecis by name**:
        ```json
        {
          "query": "eq(name,dallas)",
          "limit": 1,
          "offset": 0,
          "fields": []
        }
        ```
        This will return a response like:
        ```json
        {
          "remotecis": [],
          "_meta": {"count": 2},
          ...
        }
        ```
        The total count is 2 remotecis.

        Returns:
            JSON string with list of remotecis and pagination info
        """
        try:
            service = DCIRemoteCIService()

            result = service.query_remotecis(
                query=query, sort=sort, limit=limit, offset=offset
            )

            if isinstance(fields, list) and fields:
                # Filter the result to only include specified fields
                if "remotecis" in result:
                    filtered_result = [
                        {field: remoteci.get(field) for field in fields}
                        for remoteci in result["remotecis"]
                    ]
                    result["remotecis"] = filtered_result
            elif not fields:
                result["remotecis"] = []

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
