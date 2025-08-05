"""MCP tools for DCI component operations."""

import json
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.dci_component_service import DCIComponentService


def register_component_tools(mcp: FastMCP) -> None:
    """Register component-related tools with the MCP server."""

    @mcp.tool()
    async def query_dci_components(
        query: Annotated[
            str,
            Field(
                description="search criteria (e.g., and(ilike(name,ocp),contains(tags,ga))"
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
        only_fields: Annotated[
            list[str] | None,
            Field(
                description="List of fields to return, empty list means all fields, None means no data. Fields are the one listed in the query description plus components.",
            ),
        ] = [],
    ) -> str:
        """
        Lookup DCI components with an advanced query language.

        The query language is based on this DSL:

            eq(<field>,<value>) to lookup resources with a <field> having the value <value>.

            You can use the comparison functions gt (greater than), ge (greater or equal),
            lt (less than) or le (less or equal) using the same syntax as eq: <op>(<field>,<value>).

            like(<field>,<value with percent>) and ilike(<field>,<value with percent>)
            to lookup a field with a SQL glob like way. For example, to get the components
            with a specific name pattern, use like(name,ocp-%).

            contains(<field>,<value1>,...) and not_contains(<field>,<value1>,...)
            to lookup elements in an array. This is useful mainly for tags.

            and(<op1>(...),<op2>(...)), or(<op1>(...),<op2>(...)) and not(<op>) allow
            to build nested boolean queries.

            null(<field>) to lookup resources with a field having a NULL value.

        Here are all the fields of a DCI component that can be used in the query:

            - id: unique identifier

            - name: name of the component

            - type: type of the component. `ocp` is the type of component for OpenShift release components.

            - team_id: The ID of the team that owns the component. Use the `query_dci_teams` tool to get it.

            - released_at: The release timestamp. Use `today` tool to compute relative dates.

            - topic_id: The ID of the topic associated with the component. Use the `query_dci_topics` tool to get it.

            - state: The current state of the component (active, inactive, etc.).

            - url: The URL of the component, if applicable.

            - tags: list of tags associated with the component. For components of type ocp, it has a build status tag like `build:dev` (also called engineering candidate or ec), `build:candidate` (also called release candidate or rc), `build:ga` or `build:nightly`.

        **Counting Components**: To get the total count of components matching a query, set `limit=1` and read the `count` field in the `_meta` section of the response.

        **Example for counting components by type**:
        ```json
        {
          "query": "eq(type,ocp)",
          "limit": 1,
          "offset": 0,
          "only_fields": null
        }
        ```
        This will return a response like:
        ```json
        {
          "components": [],
          "_meta": {"count": 150},
          ...
        }
        ```
        The total count is 150 components.

        Returns:
            JSON string with list of components and pagination info
        """
        try:
            service = DCIComponentService()

            result = service.query_components(
                query=query, sort=sort, limit=limit, offset=offset
            )

            if isinstance(only_fields, list) and only_fields:
                # Filter the result to only include specified fields
                if "components" in result:
                    filtered_result = [
                        {field: component.get(field) for field in only_fields}
                        for component in result["components"]
                    ]
                    result["components"] = filtered_result
            elif only_fields is None:
                result["components"] = []

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
