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

"""MCP tools for DCI job operations."""

import json
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.dci_job_service import DCIJobService


def register_job_tools(mcp: FastMCP) -> None:
    """Register job-related tools with the MCP server."""

    @mcp.tool()
    async def query_dci_jobs(
        query: Annotated[
            str,
            Field(
                description="search criteria (e.g., and(ilike(name,ptp),contains(tags,build:ga))"
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
        Lookup DCI jobs with an advanced query language.

        The query language is based on this DSL:

            eq(<field>,<value>) to lookup resources with a <field> having the value <value>.

            You can use the comparison functions gt (greater than), ge (greater or equal),
            lt (less than) or le (less or equal) using the same syntax as eq: <op>(<field>,<value>).

            like(<field>,<value with percent>) and ilike(<field>,<value with percent>)
            to lookup a field with a SQL glob like way. For example, to get the jobs
            with a CILAB- jira ticket number, use like(comment,CILAB-%).

            contains(<field>,<value1>,...) and not_contains(<field>,<value1>,...)
            to lookup elements in an array. This is useful mainly for tags.

            and(<op1>(...),<op2>(...)), or(<op1>(...),<op2>(...)) and not(<op>) allow
            to build nested boolean queries.

            null(<field>) to lookup resources with a field having a NULL value.

        Here are all the fields of a DCI job that can be used in the query:

            - id: unique identifier

            - name: name of the job

            - status: The current state  (new, running, success, failure, error, killed). Finished jobs have a status of killed, success, failure, or error. Failing jobs have a status of failure or error.

            - created_at: The creation timestamp. Use `today` tool to compute relative dates.

            - updated_at: The last update timestamp. Use `today` tool to compute relative dates.

            - team_id: The ID of the team associated with the job. Use the `list_dci_teams` tool to get it.

            - topic_id: The ID of the topic associated with the job. Use the `list_dci_topics` tool to get it.

            - remoteci_id: The ID of the remote CI associated with the job. It represents the lab. Use the `list_dci_remotecis` tool to get it.

            - product_id: The ID of the product associated with the job. Use the `list_dci_products` tool to get it.

            - pipeline_id: The ID of the pipeline associated with the job. Use the `list_dci_pipelines` tool to get it.

            - previous_job_id: The ID of the previous job in the pipeline.

            - tags: list of tags associated with the job. Daily jobs refers to a daily tag.

            - status_reason: explanation of the failed job. It is a free text field.

            - comment: free text. Can contain a JIRA ticket number.

            - url: The URL associated with the job can be a GitHub PR URL or a Gerrit change URL

            - configuration: the configuration of this job (which configuration was used in the lab)

        **Counting Jobs**: To get the total count of jobs matching a query, set `limit=1` and read the `count` field in the `_meta` section of the response.

        **Example for counting MyTeam jobs**:
        ```json
        {
          "query": "eq(team_id,615a5fb1-d6ac-4a5f-93de-99ffb73c7473)",
          "limit": 1,
          "offset": 0,
          "only_fields": null
        }
        ```
        This will return a response like:
        ```json
        {
          "jobs": [],
          "_meta": {"count": 880},
          ...
        }
        ```
        The total count is 880 jobs.

        If an URL is needed for a job, returns https://www.distributed-ci.io/jobs/<id>.

        Returns:
            JSON string with list of jobs and pagination info
        """
        try:
            service = DCIJobService()

            result = service.query_jobs(
                query=query, sort=sort, limit=limit, offset=offset
            )

            if isinstance(only_fields, list) and only_fields:
                # Filter the result to only include specified fields
                if "jobs" in result:
                    filtered_result = [
                        {field: job.get(field) for field in only_fields}
                        for job in result["jobs"]
                    ]
                    result["jobs"] = filtered_result
            elif only_fields is None:
                result["jobs"] = []

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_job_files(job_id: str) -> str:
        """
        List files associated with a specific DCI job.

        Args:
            job_id: The ID of the job

        Returns:
            JSON string with list of job files
        """
        try:
            service = DCIJobService()
            result = service.list_job_files(job_id)

            return json.dumps(
                {"job_id": job_id, "files": result, "count": len(result)}, indent=2
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_job_results(job_id: str) -> str:
        """
        List results associated with a specific DCI job.

        Args:
            job_id: The ID of the job

        Returns:
            JSON string with list of job results
        """
        try:
            service = DCIJobService()
            result = service.list_job_results(job_id)

            return json.dumps(
                {"job_id": job_id, "results": result, "count": len(result)}, indent=2
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)


# job_tools.py ends here
