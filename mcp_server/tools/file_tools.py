"""MCP tools for DCI file operations."""

import json

from fastmcp import FastMCP

from ..services.dci_file_service import DCIFileService
from ..utils.pagination import fetch_all_with_progress


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
        fetch_all: bool = True, where: str = "", sort: str = ""
    ) -> str:
        """
        List DCI files with optional filtering and automatic pagination.

        Args:
            fetch_all: Whether to fetch all files (default: True)
            where: Filter criteria (e.g., "name:like:log")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            JSON string with list of files and pagination info
        """
        try:
            service = DCIFileService()

            # Convert empty strings to None for optional parameters
            where_filter = where if where else None
            sort_criteria = sort if sort else None

            if fetch_all:
                # Fetch all files with pagination
                result = fetch_all_with_progress(
                    service.list_files,
                    where=where_filter,
                    sort=sort_criteria,
                    page_size=50,
                    max_pages=100,
                )

                return json.dumps(
                    {
                        "files": result["results"],
                        "total_count": result["total_count"],
                        "pages_fetched": result["pages_fetched"],
                        "page_size": result["page_size"],
                        "reached_end": result["reached_end"],
                        "pagination_info": result,
                    },
                    indent=2,
                )
            else:
                # Fetch just the first page
                result = service.list_files(
                    limit=50, offset=0, where=where_filter, sort=sort_criteria
                )

                return json.dumps(
                    {
                        "files": result,
                        "count": len(result),
                        "limit": 50,
                        "offset": 0,
                        "note": "First page only. Use fetch_all=True for all results.",
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
