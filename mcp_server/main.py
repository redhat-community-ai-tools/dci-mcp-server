"""Main entry point for the DCI MCP server."""

import os

from fastmcp import FastMCP

from .tools.component_tools import register_component_tools
from .tools.file_tools import register_file_tools
from .tools.job_tools import register_job_tools
from .tools.pipeline_tools import register_pipeline_tools
from .tools.pr_tools import register_pr_tools
from .tools.product_tools import register_product_tools
from .tools.team_tools import register_team_tools
from .tools.topic_tools import register_topic_tools


def create_server() -> FastMCP:
    """Create and configure the MCP server."""
    mcp: FastMCP = FastMCP(
        name="dci-mcp-server",
        instructions="""
        This server provides tools for managing DCI (Distributed CI) jobs,
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
    register_job_tools(mcp)
    register_file_tools(mcp)
    register_pipeline_tools(mcp)
    register_product_tools(mcp)
    register_team_tools(mcp)
    register_topic_tools(mcp)
    register_pr_tools(mcp)

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
