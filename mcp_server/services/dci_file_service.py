"""DCI file service for managing files."""

import os
from typing import Any

from dciclient.v1.api import file as dci_file

from .dci_base_service import DCIBaseService


class DCIFileService(DCIBaseService):
    """Service class for DCI file operations."""

    def get_file(self, file_id: str) -> dict[str, Any] | None:
        """
        Get a specific file by ID.

        Args:
            file_id: The ID of the file to retrieve

        Returns:
            File data as dictionary, or None if not found
        """
        try:
            context = self._get_dci_context()
            result = dci_file.get(context, file_id)
            return result
        except Exception as e:
            print(f"Error getting file {file_id}: {e}")
            return None

    def list_files(
        self,
        limit: int | None = None,
        offset: int | None = None,
        where: str | None = None,
        sort: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List files with optional filtering and pagination.

        Args:
            limit: Maximum number of files to return
            offset: Number of files to skip
            where: Filter criteria (e.g., "name:like:log")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            List of file dictionaries
        """
        try:
            context = self._get_dci_context()
            result = dci_file.list(
                context, limit=limit, offset=offset, where=where, sort=sort
            )
            return result
        except Exception as e:
            print(f"Error listing files: {e}")
            return []

    def download_file(self, file_id: str, output_path: str) -> bool:
        """
        Download a file to a local path.

        Args:
            file_id: The ID of the file to download
            output_path: Local path where to save the file

        Returns:
            True if download successful, False otherwise
        """
        try:
            context = self._get_dci_context()

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Download the file
            dci_file.download(context, file_id, output_path)
            return True
        except Exception as e:
            print(f"Error downloading file {file_id} to {output_path}: {e}")
            return False

    def get_file_content(self, file_id: str) -> str | None:
        """
        Get the content of a file as a string.

        Args:
            file_id: The ID of the file

        Returns:
            File content as string, or None if error
        """
        try:
            context = self._get_dci_context()
            result = dci_file.content(context, file_id)
            return result
        except Exception as e:
            print(f"Error getting content for file {file_id}: {e}")
            return None
