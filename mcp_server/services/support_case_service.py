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

"""Red Hat Support Case service for case data retrieval."""

import os
import time
from typing import Any

import httpx

from ..config import DEFAULT_TIMEOUT


class SupportCaseService:
    """Service class for Red Hat Support Case API interactions."""

    SSO_TOKEN_URL = (
        "https://sso.redhat.com/auth/realms/redhat-external"
        "/protocol/openid-connect/token"
    )
    BASE_URL = "https://access.redhat.com/hydra/rest"
    RHSM_BASE_URL = "https://api.access.redhat.com/management/v1"

    def __init__(self) -> None:
        """Initialize support case service with authentication."""
        self.offline_token = os.environ.get("OFFLINE_TOKEN")
        if not self.offline_token:
            raise ValueError(
                "OFFLINE_TOKEN environment variable must be set. "
                "Get your offline token from "
                "https://access.redhat.com/management/api"
            )
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    async def _get_access_token(self) -> str:
        """Exchange offline token for access token, with caching."""
        now = time.time()
        if self._access_token and now < self._token_expires_at:
            return self._access_token

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(
                self.SSO_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": "rhsm-api",
                    "refresh_token": self.offline_token,
                },
            )
            response.raise_for_status()
            token_data = response.json()
            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 300)
            # Expire 30 seconds early to avoid edge-case expiry
            self._token_expires_at = now + expires_in - 30
            return self._access_token

    async def _request(
        self,
        method: str,
        path: str,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make an authenticated request with automatic token refresh."""
        url = f"{base_url or self.BASE_URL}{path}"
        token = await self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.request(method, url, headers=headers, **kwargs)

            # Handle JWT expiry: force token refresh and retry once
            if response.status_code == 401:
                self._access_token = None
                self._token_expires_at = 0.0
                token = await self._get_access_token()
                headers["Authorization"] = f"Bearer {token}"
                response = await client.request(
                    method,
                    url,
                    headers=headers,
                    **kwargs,
                )

            return response

    async def get_case(self, case_number: str) -> dict[str, Any]:
        """Get support case data by case number.

        Returns the raw API response with an added 'url' field.

        Args:
            case_number: The Red Hat support case number (e.g., "03619625")

        Returns:
            Dictionary containing case data

        Raises:
            Exception: If the API call fails
        """
        try:
            response = await self._request("GET", f"/v1/cases/{case_number}")

            if response.status_code == 404:
                raise Exception(f"Case {case_number} not found")
            if response.status_code == 403:
                raise Exception(
                    f"Access denied for case {case_number}. "
                    "Check your account permissions."
                )
            response.raise_for_status()

            case_data: dict[str, Any] = response.json()
            case_data["url"] = (
                f"https://access.redhat.com/support/cases/#/case/{case_number}"
            )
            return case_data

        except httpx.HTTPStatusError as e:
            raise Exception(
                f"Support Case API error ({e.response.status_code}): {e.response.text}"
            ) from e
        except Exception as e:
            if "not found" in str(e) or "Access denied" in str(e):
                raise
            raise Exception(f"Error retrieving case {case_number}: {str(e)}") from e

    async def get_case_comments(
        self,
        case_number: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Any:
        """Get comments for a support case.

        Args:
            case_number: The Red Hat support case number
            start_date: Optional start date filter (ISO format)
            end_date: Optional end date filter (ISO format)

        Returns:
            List of comment dictionaries

        Raises:
            Exception: If the API call fails
        """
        try:
            params: dict[str, str] = {}
            if start_date:
                params["startDate"] = start_date
            if end_date:
                params["endDate"] = end_date

            response = await self._request(
                "GET", f"/v1/cases/{case_number}/comments", params=params
            )

            if response.status_code == 404:
                raise Exception(f"Case {case_number} not found")
            if response.status_code == 403:
                raise Exception(
                    f"Access denied for case {case_number}. "
                    "Check your account permissions."
                )
            response.raise_for_status()

            return response.json()

        except httpx.HTTPStatusError as e:
            raise Exception(
                f"Support Case API error ({e.response.status_code}): {e.response.text}"
            ) from e
        except Exception as e:
            if "not found" in str(e) or "Access denied" in str(e):
                raise
            raise Exception(
                f"Error retrieving comments for case {case_number}: {str(e)}"
            ) from e

    async def search_cases(self, filter_params: dict[str, Any]) -> Any:
        """Search cases using the filter API.

        Args:
            filter_params: Dictionary matching the CaseFilter schema

        Returns:
            Filtered case results

        Raises:
            Exception: If the API call fails
        """
        try:
            response = await self._request(
                "POST", "/v1/cases/filter", json=filter_params
            )
            response.raise_for_status()

            return response.json()

        except httpx.HTTPStatusError as e:
            raise Exception(
                f"Support Case API error ({e.response.status_code}): {e.response.text}"
            ) from e
        except Exception as e:
            raise Exception(f"Error searching cases: {str(e)}") from e

    async def list_case_attachments(self, case_number: str) -> Any:
        """List attachments for a support case.

        Args:
            case_number: The Red Hat support case number

        Returns:
            List of attachment metadata

        Raises:
            Exception: If the API call fails
        """
        try:
            response = await self._request("GET", f"/cases/{case_number}/attachments/")

            if response.status_code == 404:
                raise Exception(f"Case {case_number} not found")
            if response.status_code == 403:
                raise Exception(
                    f"Access denied for case {case_number}. "
                    "Check your account permissions."
                )
            response.raise_for_status()

            return response.json()

        except httpx.HTTPStatusError as e:
            raise Exception(
                f"Support Case API error ({e.response.status_code}): {e.response.text}"
            ) from e
        except Exception as e:
            if "not found" in str(e) or "Access denied" in str(e):
                raise
            raise Exception(
                f"Error listing attachments for case {case_number}: {str(e)}"
            ) from e

    async def get_errata(self, advisory_id: str) -> dict[str, Any]:
        """Get errata/advisory details by advisory ID.

        Args:
            advisory_id: The advisory ID (e.g., "RHSA-2025:4018")

        Returns:
            Dictionary containing errata details

        Raises:
            Exception: If the API call fails
        """
        try:
            response = await self._request(
                "GET",
                f"/errata/{advisory_id}",
                base_url=self.RHSM_BASE_URL,
            )

            if response.status_code == 404:
                raise Exception(f"Errata {advisory_id} not found")
            response.raise_for_status()

            data: dict[str, Any] = response.json()
            # The RHSM API wraps the response in a "body" key
            if "body" in data:
                data = data["body"]
            data["url"] = f"https://access.redhat.com/errata/{advisory_id}"
            return data

        except httpx.HTTPStatusError as e:
            raise Exception(
                f"RHSM API error ({e.response.status_code}): {e.response.text}"
            ) from e
        except Exception as e:
            if "not found" in str(e):
                raise
            raise Exception(f"Error retrieving errata {advisory_id}: {str(e)}") from e
