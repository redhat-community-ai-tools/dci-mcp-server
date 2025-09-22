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

"""Main entry point for the DCI MCP server."""

import os

from fastmcp import FastMCP

from .config import validate_required_config
from .prompts.prompts import register_prompts
from .tools.component_tools import register_component_tools
from .tools.date_tools import register_date_tools
from .tools.file_tools import register_file_tools
from .tools.google_drive_tools import register_google_drive_tools
from .tools.jira_tools import register_jira_tools
from .tools.job_tools import register_job_tools


def create_server() -> FastMCP:
    """Create and configure the MCP server."""

    if not validate_required_config():
        raise ValueError("Required configuration is missing or invalid.")

    mcp: FastMCP = FastMCP(
        name="dci-mcp-server",
        instructions="""
        This server provides tools for searching DCI (Distributed CI) jobs,
        pipelines, logs, teams, and components.

        Daily jobs refer to DCI jobs with a tag "daily" in the list of tags.

        Most of the tools support pagination with the `limit` and
        `offset` parameters. You get the total count of items in the
        `_meta` field of the response under the `count`. To count, you
        just need to set `limit` to 1.
        """,
    )

    # Register all tools
    register_component_tools(mcp)
    register_date_tools(mcp)
    register_job_tools(mcp)
    register_file_tools(mcp)

    # Register Jira tools only when credentials are set
    if os.getenv("JIRA_API_TOKEN"):
        register_jira_tools(mcp)

    # Register Google drive tools only when credentials are set
    if os.getenv("GOOGLE_CREDENTIALS_PATH") and os.getenv("GOOGLE_TOKEN_PATH"):
        register_google_drive_tools(mcp)

    # Register prompts for user interaction
    register_prompts(mcp)

    return mcp


def main() -> None:
    """Main entry point for the server."""
    mcp = create_server()

    # Get transport from environment variables
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if transport == "stdio":
        mcp.run()
    elif transport == "tcp":
        host = os.getenv("MCP_HOST", "localhost")
        port = int(os.getenv("MCP_PORT", "8000"))
        # Note: TCP transport might not be supported in this version
        print("TCP transport not supported. Use stdio transport instead.")
        print(f"Would connect to {host}:{port}")
        exit(1)
    else:
        print(f"Unsupported transport: {transport}")
        exit(1)


if __name__ == "__main__":
    main()
