"""Entry point for the refactored MCP Prow server with FastMCP SSE support."""

import os

from mcp_server.main import main

if __name__ == "__main__":
    # Get the transport from environment (default to stdio)
    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    # Only set SSE-specific configurations if SSE transport is explicitly requested
    if transport == "sse":
        # Set default host to allow external connections (like the article)
        if not os.environ.get("MCP_HOST"):
            os.environ["MCP_HOST"] = "0.0.0.0"

        # Set default port for SSE
        if not os.environ.get("MCP_PORT"):
            os.environ["MCP_PORT"] = "8000"

    main()
