"""MCP tools for DCI file operations."""

import json

from fastmcp import FastMCP

from ..services.dci_file_service import DCIFileService


def register_file_tools(mcp: FastMCP) -> None:
    """Register file-related tools with the MCP server."""

    @mcp.tool()
    async def get_dci_file(file_id: str) -> str:
        """
        Get a specific DCI file by ID.

        Args:
            file_id: The ID of the file to retrieve

        Returns:
            JSON string with file information
        """
        try:
            service = DCIFileService()
            result = service.get_file(file_id)

            if result:
                return json.dumps(result, indent=2)
            else:
                return json.dumps({"error": f"File {file_id} not found"}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_dci_files(
        limit: int = 50, offset: int = 0, where: str = "", sort: str = ""
    ) -> str:
        """
        List DCI files with optional filtering and pagination.

        Args:
            limit: Maximum number of files to return (default: 50)
            offset: Number of files to skip (default: 0)
            where: Filter criteria (e.g., "name:like:log")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            JSON string with list of files
        """
        try:
            service = DCIFileService()

            # Convert empty strings to None for optional parameters
            where_filter = where if where else None
            sort_criteria = sort if sort else None

            result = service.list_files(
                limit=limit, offset=offset, where=where_filter, sort=sort_criteria
            )

            return json.dumps(
                {
                    "files": result,
                    "count": len(result),
                    "limit": limit,
                    "offset": offset,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def download_dci_file(file_id: str, output_path: str) -> str:
        """
        Download a DCI file to a local path.

        Args:
            file_id: The ID of the file to download
            output_path: Local path where to save the file

        Returns:
            JSON string with download status
        """
        try:
            service = DCIFileService()
            success = service.download_file(file_id, output_path)

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

    @mcp.tool()
    async def get_file_content(file_id: str) -> str:
        """
        Get the content of a DCI file as a string.

        Args:
            file_id: The ID of the file

        Returns:
            JSON string with file content
        """
        try:
            service = DCIFileService()
            content = service.get_file_content(file_id)

            if content is not None:
                return json.dumps(
                    {
                        "file_id": file_id,
                        "content": content,
                        "content_length": len(content),
                    },
                    indent=2,
                )
            else:
                return json.dumps(
                    {"error": f"Could not retrieve content for file {file_id}"},
                    indent=2,
                )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
