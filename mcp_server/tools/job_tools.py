"""MCP tools for DCI job operations."""

import json
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.dci_job_service import DCIJobService
from ..utils.pagination import (
    MAX_PAGES_DEFAULT,
    PAGE_SIZE_DEFAULT,
)


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
            int, Field(description="Maximum number of results to return", ge=1, le=100)
        ] = PAGE_SIZE_DEFAULT,
        offset: Annotated[
            int, Field(description="Offset for pagination", ge=0)
        ] = MAX_PAGES_DEFAULT,
    ) -> str:
        """
        Lookup DCI jobs with an advanced query language.

        The query language is based on this DSL:

            eq(<field>,<value>) to lookup resources with a <field> having the value <value>.

            You can use the comparison functions gt (greater than), ge (greater or equal),
            lt (less than) or le (less or equal) using the same syntax as eq: <op>(<field>,<value>).

            like(<field>,<value with percent>) and ilike(<field>,<value with percent>)
            to lookup a field with a SQL glob like way.

            contains(<field>,<value1>,...) and not_contains(<field>,<value1>,...)
            to lookup elements in an array. This is useful mainly for tags.

            and(<op1>(...),<op2>(...)), or(<op1>(...),<op2>(...)) and not(<op>) allow
            to build nested boolean queries.

            null(<field>) to lookup resources with a field having a NULL value.

        Here are all the fields of a DCI job that can be used in the query:

            - id: unique identifier

            - name: name of the job

            - status: The current state  (new, running, success, failure, error, killed)

            - created_at: The creation timestamp

            - updated_at: The last update timestamp

            - team_id: The ID of the team associated with the job

            - topic_id: The ID of the topic associated with the job

            - remoteci_id: The ID of the remote CI associated with the job. It represents the lab.

            - product_id: The ID of the product associated with the job

            - pipeline_id: The ID of the pipeline associated with the job

            - previous_job_id: The ID of the previous job in the pipeline

            - tags: list of tags associated with the job. Daily jobs refers to a daily tag.

            - status_reason: The reason for the current status

            - comment: free text. Can contain a JIRA ticket number.

            - url: The URL associated with the job can be a GitHub URL or a Gerrit URL

            - configuration: the configuration of this job (which configuration was used in the lab)

        Returns:
            JSON string with list of jobs and pagination info
        """
        try:
            service = DCIJobService()

            result = service.list_jobs_advanced(
                query=query, sort=sort, limit=limit, offset=offset
            )
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
