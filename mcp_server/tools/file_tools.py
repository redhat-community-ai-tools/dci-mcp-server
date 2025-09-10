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
