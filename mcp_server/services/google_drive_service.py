"""Google Drive service for creating Google Docs from markdown content."""

import io
import os
import tempfile
from pathlib import Path

import markdown
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload


class GoogleDriveService:
    """Service for interacting with Google Drive API."""

    # If modifying these scopes, delete the file token.json.
    SCOPES = ["https://www.googleapis.com/auth/drive.file"]

    def __init__(
        self, credentials_path: str | None = None, token_path: str | None = None
    ):
        """
        Initialize the Google Drive service.

        Args:
            credentials_path: Path to the Google OAuth2 credentials JSON file
            token_path: Path to store/load the OAuth2 token
        """
        self.credentials_path = credentials_path or os.getenv(
            "GOOGLE_CREDENTIALS_PATH", "credentials.json"
        )
        self.token_path = token_path or os.getenv("GOOGLE_TOKEN_PATH", "token.json")
        self.service = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Google Drive API."""
        creds = None
        # The file token.json stores the user's access and refresh tokens.
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Google credentials file not found at {self.credentials_path}. "
                        "Please download your OAuth2 credentials from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())

        self.service = build("drive", "v3", credentials=creds)

    def markdown_to_html(self, markdown_content: str) -> str:
        """
        Convert markdown content to HTML.

        Args:
            markdown_content: The markdown content to convert

        Returns:
            HTML content
        """
        # Configure markdown with extensions for better formatting
        md = markdown.Markdown(
            extensions=[
                "tables",
                "fenced_code",
                "codehilite",
                "toc",
                "nl2br",
            ]
        )
        return md.convert(markdown_content)

    def find_folder_by_name(
        self, folder_name: str, include_shared_drives: bool = True
    ) -> str | None:
        """
        Find a folder by name in Google Drive, including shared drives.

        Args:
            folder_name: The name of the folder to find
            include_shared_drives: Whether to search in shared drives (default: True)

        Returns:
            Folder ID if found, None otherwise

        Raises:
            HttpError: If there's an error with the Google Drive API
        """
        try:
            # 🛡️ Sanitize input to prevent query injection
            sanitized_name = folder_name.replace("\\", "\\\\").replace("'", "\\'")

            # Build the base query
            query_parts = [
                f"name='{sanitized_name}'",
                "mimeType='application/vnd.google-apps.folder'",
                "trashed=false",
            ]

            query = " and ".join(query_parts)

            # Prepare request parameters
            request_params = {
                "q": query,
                "fields": "files(id, name, parents)",
            }

            # Include shared drives if requested
            if include_shared_drives:
                request_params["includeItemsFromAllDrives"] = True
                request_params["supportsAllDrives"] = True

            results = self.service.files().list(**request_params).execute()

            folders = results.get("files", [])
            if folders:
                # Return the first match
                return folders[0]["id"]

            return None

        except HttpError as error:
            raise Exception(
                f"An error occurred with the Google Drive API: {error}"
            ) from error

    def create_google_doc_from_markdown(
        self,
        markdown_content: str,
        doc_title: str,
        folder_id: str | None = None,
        folder_name: str | None = None,
    ) -> dict:
        """
        Create a Google Doc from markdown content.

        Args:
            markdown_content: The markdown content to convert
            doc_title: The title for the Google Doc
            folder_id: Optional folder ID to place the document in
            folder_name: Optional folder name to place the document in (searched by name)

        Returns:
            Dictionary containing the created document information

        Raises:
            HttpError: If there's an error with the Google Drive API
            ValueError: If both folder_id and folder_name are provided, or if folder_name is not found
        """
        try:
            # Validate parameters
            if folder_id and folder_name:
                raise ValueError(
                    "Cannot specify both folder_id and folder_name. Use only one."
                )

            # Resolve folder ID if folder_name is provided
            target_folder_id = folder_id
            if folder_name:
                target_folder_id = self.find_folder_by_name(
                    folder_name, include_shared_drives=True
                )
                if not target_folder_id:
                    raise ValueError(
                        f"Folder '{folder_name}' not found in Google Drive or shared drives"
                    )

            # Step 1: Convert markdown to HTML
            html_content = self.markdown_to_html(markdown_content)

            # Step 2: Create a temporary HTML file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False, encoding="utf-8"
            ) as temp_file:
                temp_file.write(html_content)
                temp_file_path = temp_file.name

            try:
                # Step 3: Prepare file metadata
                file_metadata = {
                    "name": doc_title,
                    "mimeType": "application/vnd.google-apps.document",
                }

                # Add folder if specified
                if target_folder_id:
                    file_metadata["parents"] = [target_folder_id]

                # Step 4: Create MediaUpload from HTML file
                media = MediaIoBaseUpload(
                    io.FileIO(temp_file_path, "rb"),
                    mimetype="text/html",
                    resumable=True,
                )

                # Step 5: Use Google Drive API to create and convert
                response = (
                    self.service.files()
                    .create(body=file_metadata, media_body=media)
                    .execute()
                )

                # Get the document URL
                doc_url = f"https://docs.google.com/document/d/{response['id']}/edit"

                return {
                    "id": response["id"],
                    "name": response["name"],
                    "url": doc_url,
                    "mimeType": response["mimeType"],
                    "createdTime": response.get("createdTime"),
                    "modifiedTime": response.get("modifiedTime"),
                    "markdown_content": markdown_content,  # Include the original content for reference
                }

            finally:
                # Clean up the temporary file

                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        except HttpError as error:
            raise Exception(
                f"Error creating Google Doc: {error.resp.status} - {error.content}"
            ) from error

    def create_google_doc_from_file(
        self,
        file_path: str,
        doc_title: str | None = None,
        folder_id: str | None = None,
        folder_name: str | None = None,
    ) -> dict:
        """
        Create a Google Doc from a markdown file.

        Args:
            file_path: Path to the markdown file
            doc_title: Optional title for the Google Doc (defaults to filename)
            folder_id: Optional folder ID to place the document in
            folder_name: Optional folder name to place the document in (searched by name)

        Returns:
            Dictionary containing the created document information

        Raises:
            FileNotFoundError: If the markdown file doesn't exist
            HttpError: If there's an error with the Google Drive API
            ValueError: If both folder_id and folder_name are provided, or if folder_name is not found
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Markdown file not found: {file_path}")

        # Read the markdown content
        with open(file_path, encoding="utf-8") as f:
            markdown_content = f.read()

        # Use filename as title if not provided
        if not doc_title:
            doc_title = file_path_obj.stem

        return self.create_google_doc_from_markdown(
            markdown_content, doc_title, folder_id, folder_name
        )

    def list_documents(self, query: str | None = None, max_results: int = 10) -> list:
        """
        List Google Docs in the user's Drive.

        Args:
            query: Optional search query
            max_results: Maximum number of results to return

        Returns:
            List of document information dictionaries

        Raises:
            HttpError: If there's an error with the Google Drive API
        """
        try:
            # Build the query to search for Google Docs
            search_query = "mimeType='application/vnd.google-apps.document'"
            if query:
                search_query += f" and name contains '{query}'"

            # Execute the search
            results = (
                self.service.files()
                .list(
                    q=search_query,
                    pageSize=max_results,
                    fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, webViewLink)",
                )
                .execute()
            )

            documents = []
            for file in results.get("files", []):
                documents.append(
                    {
                        "id": file["id"],
                        "name": file["name"],
                        "url": file.get(
                            "webViewLink",
                            f"https://docs.google.com/document/d/{file['id']}/edit",
                        ),
                        "mimeType": file["mimeType"],
                        "createdTime": file.get("createdTime"),
                        "modifiedTime": file.get("modifiedTime"),
                    }
                )

            return documents

        except HttpError as error:
            raise Exception(
                f"Error listing Google Docs: {error.resp.status} - {error.content}"
            ) from error
