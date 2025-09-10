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
    ) -> str:
        """
        Create a Google Doc from markdown content.

        This tool converts markdown content to HTML and then creates a Google Doc
        in your Google Drive. The markdown is converted with support for:
        - Tables
        - Code blocks with syntax highlighting
        - Headers and formatting
        - Lists and links

        Args:
            markdown_content: The markdown content to convert
            doc_title: The title for the Google Doc
            folder_id: Optional folder ID to place the document in

        Returns:
            JSON string with the created document information including ID and URL
        """
        try:
            service = GoogleDriveService()
            result = service.create_google_doc_from_markdown(
                markdown_content, doc_title, folder_id
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
    ) -> str:
        """
        Create a Google Doc from a markdown file.

        This tool reads a markdown file from the local filesystem and creates
        a Google Doc in your Google Drive. Perfect for converting DCI reports
        and other markdown documents.

        Args:
            file_path: Path to the markdown file
            doc_title: Optional title for the Google Doc (defaults to filename)
            folder_id: Optional folder ID to place the document in

        Returns:
            JSON string with the created document information including ID and URL
        """
        try:
            service = GoogleDriveService()
            result = service.create_google_doc_from_file(
                file_path, doc_title, folder_id
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

        Args:
            query: Optional search query to filter documents by name
            max_results: Maximum number of results to return (1-100)

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
    async def delete_google_doc(
        document_id: Annotated[
            str,
            Field(description="The ID of the Google Doc to delete"),
        ],
    ) -> str:
        """
        Delete a Google Doc from your Google Drive.

        WARNING: This action cannot be undone. The document will be permanently deleted.

        Args:
            document_id: The ID of the document to delete

        Returns:
            JSON string with the deletion result
        """
        try:
            service = GoogleDriveService()
            result = service.delete_document(document_id)
            return json.dumps(
                {
                    "success": result,
                    "message": (
                        "Document deleted successfully"
                        if result
                        else "Failed to delete document"
                    ),
                },
                indent=2,
            )
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
    ) -> str:
        """
        Convert a DCI report markdown file to a Google Doc.

        This is a specialized tool for converting DCI weekly reports and other
        analysis documents to Google Docs. It automatically formats the content
        with proper styling for tables, code blocks, and headers.

        Args:
            report_path: Path to the DCI report markdown file
            doc_title: Optional title for the Google Doc (defaults to report filename)
            folder_id: Optional folder ID to place the document in

        Returns:
            JSON string with the created document information including ID and URL
        """
        try:
            service = GoogleDriveService()
            result = service.create_google_doc_from_file(
                report_path, doc_title, folder_id
            )

            # Add some metadata about the conversion
            result["conversion_info"] = {
                "source_file": report_path,
                "converted_at": (
                    service.service._http.request.utcnow().isoformat()
                    if hasattr(service.service, "_http")
                    else None
                ),
                "tool": "convert_dci_report_to_google_doc",
            }

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
