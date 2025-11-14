"""MCP tools for Google Drive operations."""

import json
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.google_drive_service import GoogleDriveService


def register_google_drive_tools(mcp: FastMCP) -> None:
    """Register Google Drive-related tools with the MCP server."""

    @mcp.tool()
    async def create_google_doc_from_markdown(
        markdown_content: Annotated[
            str,
            Field(description="The markdown content to convert to a Google Doc"),
        ],
        doc_title: Annotated[
            str,
            Field(description="The title for the Google Doc"),
        ],
        folder_id: Annotated[
            str | None,
            Field(description="Optional folder ID to place the document in"),
        ] = None,
        folder_name: Annotated[
            str | None,
            Field(
                description="Optional folder name to place the document in (searched by name)"
            ),
        ] = None,
    ) -> str:
        """
        Create a Google Doc from markdown content.

        This tool converts markdown content to HTML and then creates a Google Doc
        in your Google Drive. The markdown is converted with support for:
        - Tables
        - Code blocks with syntax highlighting
        - Headers and formatting
        - Lists and links

        You can specify either folder_id or folder_name to place the document in a specific folder.
        If folder_name is provided, the tool will search for a folder with that exact name.

        Returns:
            JSON string with the created document information including ID and URL
        """
        try:
            service = GoogleDriveService()
            result = service.create_google_doc_from_markdown(
                markdown_content, doc_title, folder_id, folder_name
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def create_google_doc_from_file(
        file_path: Annotated[
            str,
            Field(description="Path to the markdown file to convert"),
        ],
        doc_title: Annotated[
            str | None,
            Field(
                description="Optional title for the Google Doc (defaults to filename)"
            ),
        ] = None,
        folder_id: Annotated[
            str | None,
            Field(description="Optional folder ID to place the document in"),
        ] = None,
        folder_name: Annotated[
            str | None,
            Field(
                description="Optional folder name to place the document in (searched by name)"
            ),
        ] = None,
    ) -> str:
        """
        Create a Google Doc from a markdown file.

        This tool reads a markdown file from the local filesystem and creates
        a Google Doc in your Google Drive. Perfect for converting DCI reports
        and other markdown documents.

        You can specify either folder_id or folder_name to place the document in a specific folder.
        If folder_name is provided, the tool will search for a folder with that exact name.

        Returns:
            JSON string with the created document information including ID and URL
        """
        try:
            service = GoogleDriveService()
            result = service.create_google_doc_from_file(
                file_path, doc_title, folder_id, folder_name
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_google_docs(
        query: Annotated[
            str | None,
            Field(description="Optional search query to filter documents by name"),
        ] = None,
        max_results: Annotated[
            int,
            Field(
                description="Maximum number of results to return",
                ge=1,
                le=100,
            ),
        ] = 10,
    ) -> str:
        """
        List Google Docs in your Google Drive.

        This tool searches for Google Docs in your Drive and returns
        information about them including titles, IDs, and URLs.


        Returns:
            JSON string with list of document information
        """
        try:
            service = GoogleDriveService()
            result = service.list_documents(query, max_results)
            return json.dumps({"documents": result, "count": len(result)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def convert_dci_report_to_google_doc(
        report_path: Annotated[
            str,
            Field(description="Path to the DCI report markdown file"),
        ],
        doc_title: Annotated[
            str | None,
            Field(
                description="Optional title for the Google Doc (defaults to report filename)"
            ),
        ] = None,
        folder_id: Annotated[
            str | None,
            Field(description="Optional folder ID to place the document in"),
        ] = None,
        folder_name: Annotated[
            str | None,
            Field(
                description="Optional folder name to place the document in (searched by name)"
            ),
        ] = None,
    ) -> str:
        """
        Convert a DCI report markdown file to a Google Doc.

        This is a specialized tool for converting DCI weekly reports and other
        analysis documents to Google Docs. It automatically formats the content
        with proper styling for tables, code blocks, and headers.

        You can specify either folder_id or folder_name to place the document in a specific folder.
        If folder_name is provided, the tool will search for a folder with that exact name.

        Returns:
            JSON string with the created document information including ID and URL
        """
        try:
            service = GoogleDriveService()
            result = service.create_google_doc_from_file(
                report_path, doc_title, folder_id, folder_name
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def find_folder_by_name(
        folder_name: Annotated[
            str,
            Field(description="The name of the folder to find"),
        ],
        include_shared_drives: Annotated[
            bool,
            Field(description="Whether to search in shared drives (default: True)"),
        ] = True,
    ) -> str:
        """
        Find a folder by name in Google Drive, including shared drives.

        This tool searches for folders by exact name in both your personal Google Drive
        and shared drives (if enabled). It will return the folder ID if found.


        Returns:
            JSON string with folder information including ID and location details
        """
        try:
            service = GoogleDriveService()
            folder_id = service.find_folder_by_name(folder_name, include_shared_drives)

            if folder_id:
                return json.dumps(
                    {
                        "found": True,
                        "folder_id": folder_id,
                        "message": f"Folder '{folder_name}' found with ID: {folder_id}",
                    },
                    indent=2,
                )
            else:
                return json.dumps(
                    {
                        "found": False,
                        "message": f"Folder '{folder_name}' not found in Google Drive{' or shared drives' if include_shared_drives else ''}",
                    },
                    indent=2,
                )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
