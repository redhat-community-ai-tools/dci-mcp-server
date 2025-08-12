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

"""MCP tools for DCI file operations."""

import json
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.dci_file_service import DCIFileService


def register_file_tools(mcp: FastMCP) -> None:
    """Register file-related tools with the MCP server."""

    @mcp.tool()
    async def query_dci_files(
        job_id: Annotated[
            str, Field(description="The ID of the job associated with the file")
        ],
        query: Annotated[
            str | None,
            Field(
                description="search criteria (e.g., and(ilike(name,%ansible%),lt(size,10240000))"
            ),
        ] = None,
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
        Lookup DCI files with an advanced query language.

        The query language is based on this DSL:

            eq(<field>,<value>) to lookup resources with a <field> having the value <value>.

            You can use the comparison functions gt (greater than), ge (greater or equal),
            lt (less than) or le (less or equal) using the same syntax as eq: <op>(<field>,<value>).

            like(<field>,<value with percent>) and ilike(<field>,<value with percent>)
            to lookup a field with a SQL glob like way. For example, to get the files
            with a specific name pattern, use like(name,ansible-%).

            contains(<field>,<value1>,...) and not_contains(<field>,<value1>,...)
            to lookup elements in an array. This is useful mainly for tags.

            and(<op1>(...),<op2>(...)), or(<op1>(...),<op2>(...)) and not(<op>) allow
            to build nested boolean queries.

            null(<field>) to lookup resources with a field having a NULL value.

        Here are all the fields of a DCI file that can be used in the query:

            - id: unique identifier

            - name: name of the file

            - created_at: The creation timestamp. Use `today` tool to compute relative dates.

            - updated_at: The last update timestamp. Use `today` tool to compute relative dates.

            - job_id: The ID of the job associated with the file. Use the `query_dci_jobs` tool to get it.

            - mime: The MIME type of the file, e.g., text/plain, application/json, etc. Task files are of MIME type application/x-ansible-output.

            - size: The size of the file in bytes.

            - md5: The MD5 checksum of the file.

            - state: The state of the file (active or inactive).

            - team_id: The ID of the team that owns the file.

            - jobstate_id: The ID of the job state associated with the file.

        **Counting Files**: To get the total count of files matching a query, set `limit=1` and read the `count` field in the `_meta` section of the response.

        **Example for counting files by name**:
        ```json
        {
          "query": "eq(name,ansible.log)",
          "limit": 1,
          "offset": 0,
          "fields": []
        }
        ```
        This will return a response like:
        ```json
        {
          "files": [],
          "_meta": {"count": 15},
          ...
        }
        ```
        The total count is 15 files.

        Returns:
            JSON string with list of files and pagination info
        """
        try:
            service = DCIFileService()

            result = service.query_files(
                job_id=job_id, query=query, sort=sort, limit=limit, offset=offset
            )

            if isinstance(fields, list) and fields:
                # Filter the result to only include specified fields
                if "files" in result:
                    filtered_result = [
                        {field: file.get(field) for field in fields}
                        for file in result["files"]
                    ]
                    result["files"] = filtered_result
            elif not fields:
                result["files"] = []

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def download_dci_file(
        job_id: Annotated[
            str, Field(description="The ID of the job associated with the file")
        ],
        file_id: Annotated[str, Field(description="The ID of the file to download")],
        output_path: Annotated[
            str,
            Field(
                description="Local path where to save the file. If not instructed otherwise, always ask to download to /tmp/dci/<dci job id>/."
            ),
        ],
    ) -> str:
        """
        Download a DCI file to a local path.

        Returns:
            JSON string with download status
        """
        try:
            service = DCIFileService()
            success = service.download_file(job_id, file_id, output_path)

            if success:
                return json.dumps(
                    {
                        "success": True,
                        "file_id": file_id,
                        "output_path": output_path,
                        "message": "File downloaded successfully",
                    },
                    indent=2,
                )
            else:
                return json.dumps(
                    {
                        "success": False,
                        "file_id": file_id,
                        "error": "Failed to download file",
                    },
                    indent=2,
                )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
