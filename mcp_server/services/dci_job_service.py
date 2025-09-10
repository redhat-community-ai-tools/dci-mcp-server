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

"""DCI job service for managing jobs."""

from typing import Any

from dciclient.v1.api import job

from .dci_base_service import DCIBaseService


class DCIJobService(DCIBaseService):
    """Service class for DCI job operations."""

    def search_jobs(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        sort: str | None = None,
    ) -> list:
        """
        List jobs using the advanced search syntax.

        Args:
            query: query criteria (e.g., "((components.type='ocp') and (components.version='4.19.0')) and ((components.type='storage') and (components.name='my-storage'))")
            limit: Maximum number of jobs to return (default: 50)
            offset: Number of jobs to skip (default: 0)
            sort: Sort criteria (e.g., "-created_at")

        Returns:
            A dictionary with jobs data or an empty dictionary on error
        """
        try:
            context = self._get_dci_context()
            return job.search(
                context,
                query=query,
                limit=limit,
                offset=offset,
                sort=sort,
            ).json()
        except Exception as e:
            return {"error": str(e), "message": "Failed to list jobs."}

    def query_jobs(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        sort: str | None = None,
    ) -> list:
        """
        List jobs using the advanced query syntax.

        Args:
            query: query criteria (e.g., "and(ilike(name,ptp),contains(tags,build:ga))")
            limit: Maximum number of jobs to return (default: 50)
            offset: Number of jobs to skip (default: 0)
            sort: Sort criteria (e.g., "-created_at")

        Returns:
            A dictionary with jobs data or an empty dictionary on error
        """
        try:
            context = self._get_dci_context()
            return job.list(
                context,
                query=query,
                limit=limit,
                offset=offset,
                sort=sort,
            ).json()
        except Exception as e:
            return {"error": str(e), "message": "Failed to list jobs."}

    def list_job_files(self, job_id: str) -> Any:
        """
        List files associated with a specific job.

        Args:
            job_id: The ID of the job

        Returns:
            List of file dictionaries
        """
        try:
            context = self._get_dci_context()
            result = job.list_files(context, job_id)
            if hasattr(result, "json"):
                data = result.json()
                return data.get("files", []) if isinstance(data, dict) else []
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error listing files for job {job_id}: {e}")
            return []

    def list_job_results(self, job_id: str) -> Any:
        """
        List results associated with a specific job.

        Args:
            job_id: The ID of the job

        Returns:
            List of result dictionaries
        """
        try:
            context = self._get_dci_context()
            result = job.list_results(context, job_id)
            if hasattr(result, "json"):
                data = result.json()
                return data.get("results", []) if isinstance(data, dict) else []
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error listing results for job {job_id}: {e}")
            return []
