"""MCP tools for DCI team operations."""

import json
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.dci_team_service import DCITeamService


def register_team_tools(mcp: FastMCP) -> None:
    """Register team-related tools with the MCP server."""

    @mcp.tool()
    async def query_dci_teams(
        query: Annotated[
            str,
            Field(
                description="search criteria (e.g., and(ilike(name,qa),contains(tags,ga))"
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
        Lookup DCI teams with an advanced query language.

        The query language is based on this DSL:

            eq(<field>,<value>) to lookup resources with a <field> having the value <value>.

            You can use the comparison functions gt (greater than), ge (greater or equal),
            lt (less than) or le (less or equal) using the same syntax as eq: <op>(<field>,<value>).

            like(<field>,<value with percent>) and ilike(<field>,<value with percent>)
            to lookup a field with a SQL glob with at least one % character. For example, to get the teams
            with a specific name pattern, use like(name,%Name%).

            contains(<field>,<value1>,...) and not_contains(<field>,<value1>,...)
            to lookup elements in an array. This is useful mainly for tags.

            and(<op1>(...),<op2>(...)), or(<op1>(...),<op2>(...)) and not(<op>) allow
            to build nested boolean queries.

            null(<field>) to lookup resources with a field having a NULL value.

        Here are all the fields of a DCI team that can be used in the query:

            - id: unique identifier

            - name: name of the team

            - created_at: The creation timestamp. Use `today` tool to compute relative dates.

            - updated_at: The last update timestamp. Use `today` tool to compute relative dates.

            - tags: list of tags associated with the team.

        **Counting Teams**: To get the total count of teams matching a query, set `limit=1` and read the `count` field in the `_meta` section of the response.

        **Example for counting teams by name**:
        ```json
        {
          "query": "eq(name,DCI)",
          "limit": 1,
          "offset": 0,
          "fields": []
        }
        ```
        This will return a response like:
        ```json
        {
          "teams": [],
          "_meta": {"count": 10},
          ...
        }
        ```
        The total count is 10 teams.

        Returns:
            JSON string with list of teams and pagination info
        """
        try:
            service = DCITeamService()

            result = service.query_teams(
                query=query, sort=sort, limit=limit, offset=offset
            )

            if isinstance(fields, list) and fields:
                # Filter the result to only include specified fields
                if "teams" in result:
                    filtered_result = [
                        {field: team.get(field) for field in fields}
                        for team in result["teams"]
                    ]
                    result["teams"] = filtered_result
            elif not fields:
                result["teams"] = []

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
