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
                description="Relative path under the download directory (default /tmp/dci/), e.g. <job_id>/<filename>. Absolute paths are only accepted if they start with the download directory; other absolute paths are rejected."
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
            resolved_path = service.download_file(job_id, file_id, output_path)

            return json.dumps(
                {
                    "success": True,
                    "file_id": file_id,
                    "output_path": resolved_path,
                    "message": f"File downloaded successfully to {resolved_path}",
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps(
                {"success": False, "file_id": file_id, "error": str(e)},
                indent=2,
            )
