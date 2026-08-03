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
            Field(
                description="Relative path under the download directory (default /tmp/dci/) to the markdown file to convert, e.g. <job_id>/report.md. Absolute paths are only accepted if they start with the download directory; other absolute paths are rejected."
            ),
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
            Field(
                description="Relative path under the download directory (default /tmp/dci/) to the DCI report markdown file, e.g. report.md. Absolute paths are only accepted if they start with the download directory; other absolute paths are rejected."
            ),
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
                        "message": f"Folder '{folder_name}' not found",
                    },
                    indent=2,
                )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def read_google_doc(
        file_id: Annotated[
            str,
            Field(description="The ID of the Google Doc to read (found in the URL)"),
        ]
    ) -> str:
        """
        Read the text content of a Google Doc.
        
        This tool extracts the plain text from a Google Doc given its ID.
        Useful for reading existing meeting notes, templates, or reports.
        
        Returns:
            JSON string containing the text content or an error message.
        """
        try:
            service = GoogleDriveService()
            text_content = service.read_google_doc(file_id)
            return json.dumps({"content": text_content, "id": file_id}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def read_google_sheet(
        spreadsheet_id: Annotated[
            str,
            Field(
                description="The ID of the Google Spreadsheet to read (found in the URL between /d/ and /edit)"
            ),
        ],
        sheet_name: Annotated[
            str | None,
            Field(
                description="Name of the specific sheet/tab to read. Reads the first sheet if omitted."
            ),
        ] = None,
        cell_range: Annotated[
            str | None,
            Field(
                description="A1 notation range to limit what is read (e.g. 'A1:D10'). Reads all data if omitted."
            ),
        ] = None,
    ) -> str:
        """
        Read data from a Google Spreadsheet.

        Returns the spreadsheet content as structured JSON with headers, rows,
        and a CSV representation. Also lists all available sheet/tab names
        in the spreadsheet so you can query specific tabs.

        Returns:
            JSON string with sheet metadata, headers, rows, and CSV content.
        """
        try:
            service = GoogleDriveService()
            result = service.read_google_sheet(spreadsheet_id, sheet_name, cell_range)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def append_to_google_doc(
        file_id: Annotated[
            str,
            Field(description="The ID of the Google Doc to append to"),
        ],
        text_content: Annotated[
            str,
            Field(description="The text to append to the end of the document"),
        ]
    ) -> str:
        """
        Append text to the end of an existing Google Doc.
        
        This tool inserts new text at the very end of the document.
        Useful for adding new meeting notes to a running document.
        
        Returns:
            JSON string with status information.
        """
        try:
            service = GoogleDriveService()
            result = service.append_to_google_doc(file_id, text_content)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def prepend_to_google_doc(
        file_id: Annotated[
            str,
            Field(description="The ID of the Google Doc to prepend to"),
        ],
        text_content: Annotated[
            str,
            Field(description="The text to insert at the beginning of the document"),
        ]
    ) -> str:
        """
        Insert text at the beginning of an existing Google Doc.
        
        This tool inserts new text at the very top of the document.
        Useful for adding the newest weekly report to the top of a running document.
        
        Returns:
            JSON string with status information.
        """
        try:
            service = GoogleDriveService()
            result = service.prepend_to_google_doc(file_id, text_content)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
