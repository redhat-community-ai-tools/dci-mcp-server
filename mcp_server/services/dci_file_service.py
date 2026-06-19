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

"""DCI file service for managing files."""

import os
from pathlib import Path
from typing import Any

from dciclient.v1.api import file as dci_file

from .dci_base_service import DCIBaseService


class DCIFileService(DCIBaseService):
    """Service class for DCI file operations."""

    def get_file(self, file_id: str) -> Any:
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
            if hasattr(result, "json"):
                return result.json()
            return result
        except Exception as e:
            print(f"Error getting file {file_id}: {e}")
            return None

    def query_files(
        self,
        job_id: str,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort: str | None = None,
    ) -> dict:
        """
        List files for a specific job using the advanced query syntax.

        Args:
            job_id: The ID of the job to filter files
            query: query criteria (e.g., "ilike(name,%ansible%)")
            limit: Maximum number of files to return (default: 50)
            offset: Number of files to skip (default: 0)
            sort: Sort criteria (e.g., "-created_at")

        Returns:
            A dictionary with files data or an error dictionary on failure
        """
        try:
            context = self._get_dci_context()
            from dciclient.v1.api import job

            result = job.list_files(context, job_id)

            # Check if the result has a json method
            if hasattr(result, "json"):
                data = result.json()
                # Ensure we return a proper structure
                if isinstance(data, dict):
                    return data
                else:
                    return {
                        "files": data if isinstance(data, list) else [],
                        "error": "Invalid response format",
                    }
            else:
                # If result doesn't have json method, try to convert it
                if isinstance(result, dict):
                    return result
                elif isinstance(result, list):
                    return {"files": result}
                else:
                    return {"files": [], "error": "Unexpected response type"}

        except Exception as e:
            return {"error": str(e), "message": "Failed to list files.", "files": []}

    def list_files(
        self,
        limit: int | None = None,
        offset: int | None = None,
        where: str | None = None,
        sort: str | None = None,
    ) -> list:
        """
        List files with optional filtering and pagination.

        Args:
            limit: Maximum number of files to return
            offset: Number of files to skip
            where: Filter criteria (e.g., "name:ansible.log")
            sort: Sort criteria (e.g., "-created_at")

        Returns:
            List of file dictionaries
        """
        try:
            context = self._get_dci_context()
            # Provide default values for required parameters
            if limit is None:
                limit = 50
            if offset is None:
                offset = 0

            result = dci_file.list(
                context, limit=limit, offset=offset, where=where, sort=sort
            )
            if hasattr(result, "json"):
                data = result.json()
                return data.get("files", []) if isinstance(data, dict) else []
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error listing files: {e}")
            return []

    DOWNLOAD_ROOT = Path(os.environ.get("DCI_DOWNLOAD_DIR", "/tmp/dci")).resolve()  # nosec B108

    def download_file(self, job_id: str, file_id: str, output_path: str) -> str:
        """
        Download a file to a local path.

        Args:
            job_id: The ID of the job associated with the file
            file_id: The ID of the file to download
            output_path: Local path where to save the file

        Returns:
            The resolved path where the file was saved.

        Raises:
            ValueError: If output_path escapes the download root.
        """
        # SECURITY: output_path is LLM-controlled. Confine to DOWNLOAD_ROOT.
        root = self.DOWNLOAD_ROOT
        root.mkdir(parents=True, exist_ok=True)
        p = Path(output_path)
        if p.is_absolute():
            try:
                relative = p.relative_to(root)
            except ValueError:
                raise ValueError(
                    f"output_path must be a relative path or under {root}. "
                    f"Got absolute path outside download root: {output_path!r}"
                ) from None
        else:
            relative = p
        candidate = (root / relative).resolve()
        if root not in candidate.parents and candidate != root:
            raise ValueError(
                f"output_path escapes download root {root} via traversal: {output_path!r}"
            )
        candidate.parent.mkdir(parents=True, exist_ok=True)

        context = self._get_dci_context()
        dci_file.download(context, job_id, file_id, str(candidate))
        return str(candidate)
