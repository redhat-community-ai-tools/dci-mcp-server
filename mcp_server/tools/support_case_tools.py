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

"""MCP tools for Red Hat Support Case operations."""

import json
import re
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ..services.support_case_service import SupportCaseService


def validate_advisory_id(advisory_id: str) -> str:
    """Validate and normalize Red Hat advisory/errata ID format.

    Args:
        advisory_id: Advisory ID (e.g., "RHSA-2025:4018")

    Returns:
        Normalized advisory ID (stripped of whitespace, uppercased)

    Raises:
        ValueError: If advisory ID format is invalid
    """
    advisory_id = advisory_id.strip().upper()

    # Red Hat advisory IDs: RHSA/RHBA/RHEA-YYYY:NNNN
    pattern = r"^RH[SBE]A-\d{4}:\d{4,6}$"

    if not re.match(pattern, advisory_id):
        raise ValueError(
            f"Invalid advisory ID format: '{advisory_id}'. "
            "Expected format: RHSA-2025:4018, RHBA-2025:1234, or RHEA-2025:5678"
        )

    return advisory_id


def validate_case_number(case_number: str) -> str:
    """Validate and normalize Red Hat support case number format.

    Args:
        case_number: Case number (e.g., "03619625")

    Returns:
        Normalized case number (stripped of whitespace)

    Raises:
        ValueError: If case number format is invalid
    """
    case_number = case_number.strip()

    # Red Hat case numbers are numeric strings, typically 8 digits
    pattern = r"^\d{5,10}$"

    if not re.match(pattern, case_number):
        raise ValueError(
            f"Invalid case number format: '{case_number}'. "
            "Expected a numeric case number (e.g., 03619625)"
        )

    return case_number


def register_support_case_tools(mcp: FastMCP) -> None:
    """Register Red Hat Support Case tools with the MCP server."""

    @mcp.tool()
    async def get_support_case(
        case_number: Annotated[
            str,
            Field(description="Red Hat support case number (e.g., 03619625)"),
        ],
    ) -> str:
        """Get Red Hat support case data including comments and linked bugs.

        This tool retrieves detailed information about a Red Hat support case
        including basic case information, product and version, contact info,
        comments, and linked Bugzilla bugs.

        ## Authentication Required

        This tool requires a Red Hat offline token. Set the following
        environment variable:
        - `OFFLINE_TOKEN`: Your Red Hat API offline token

        ## Getting Your Offline Token

        1. Go to https://access.redhat.com/management/api
        2. Click "Generate Token"
        3. Copy the generated offline token
        4. Set it as `OFFLINE_TOKEN` in your environment or .env file

        ## Case Number Format

        The case number should be a numeric string:
        - Examples: `03619625`, `12345678`
        - Typically 8 digits
        - Leading zeros are significant

        ## Returned Data

        The tool returns the raw case data from the Red Hat Support API
        as a JSON object. Key fields include:
        - **caseNumber**: The case number
        - **summary**: Case title/summary
        - **description**: Full case description
        - **status**: Current status
        - **severity**: Severity level
        - **product**: Product name
        - **version**: Product version
        - **contactName**: Contact person name
        - **createdDate**: Case creation timestamp
        - **lastModifiedDate**: Last modification timestamp
        - **isClosed**: Whether the case is currently closed
        - **comments**: Comments on the case
        - **bugzillas**: Linked Bugzilla bugs
        - **url**: Direct link to the case on the Red Hat Customer Portal

        Returns:
            JSON string with case data
        """
        try:
            normalized_case = validate_case_number(case_number)

            service = SupportCaseService()

            case_data = await service.get_case(normalized_case)

            return json.dumps(case_data, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_support_case_comments(
        case_number: Annotated[
            str,
            Field(description="Red Hat support case number (e.g., 03619625)"),
        ],
        start_date: Annotated[
            str | None,
            Field(
                description="Optional start date filter in ISO format (e.g., 2025-01-01)"
            ),
        ] = None,
        end_date: Annotated[
            str | None,
            Field(
                description="Optional end date filter in ISO format (e.g., 2025-12-31)"
            ),
        ] = None,
    ) -> str:
        """Get comments for a Red Hat support case.

        This tool retrieves the comments/communication history for a support
        case. Comments can be filtered by date range.

        ## Authentication Required

        This tool requires a Red Hat offline token. Set the following
        environment variable:
        - `OFFLINE_TOKEN`: Your Red Hat API offline token

        ## Parameters

        - **case_number**: The case number (e.g., 03619625)
        - **start_date**: Optional ISO date to filter comments from (e.g., 2025-01-01)
        - **end_date**: Optional ISO date to filter comments until (e.g., 2025-12-31)

        ## Returned Data

        Returns the raw comments data from the API. Each comment typically
        includes:
        - **id**: Comment identifier
        - **commentBody**: The comment text
        - **createdBy**: Who created the comment
        - **createdByType**: Type of creator (customer, support, etc.)
        - **createdDate**: When the comment was created
        - **publishedDate**: When the comment was published
        - **isDraft**: Whether the comment is a draft

        Returns:
            JSON string with comments data
        """
        try:
            normalized_case = validate_case_number(case_number)
            service = SupportCaseService()
            comments = await service.get_case_comments(
                normalized_case, start_date, end_date
            )
            return json.dumps(comments, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def search_support_cases(
        keyword: Annotated[
            str | None,
            Field(description="Full-text search keyword"),
        ] = None,
        status: Annotated[
            str | None,
            Field(
                description="Filter by case status (e.g., Open, Closed, "
                "Waiting on Customer, Waiting on Red Hat)"
            ),
        ] = None,
        severity: Annotated[
            str | None,
            Field(
                description="Filter by severity (e.g., 1 (Urgent), "
                "2 (High), 3 (Normal), 4 (Low))"
            ),
        ] = None,
        product: Annotated[
            str | None,
            Field(
                description="Filter by product name (e.g., OpenShift Container Platform)"
            ),
        ] = None,
        include_closed: Annotated[
            bool,
            Field(description="Whether to include closed cases (default: false)"),
        ] = False,
        max_results: Annotated[
            int,
            Field(
                description="Maximum number of results to return (default: 50, max: 200)",
                ge=1,
                le=200,
            ),
        ] = 50,
        start_date: Annotated[
            str | None,
            Field(
                description="Filter cases created after this date in ISO format "
                "(e.g., 2025-01-01)"
            ),
        ] = None,
        end_date: Annotated[
            str | None,
            Field(
                description="Filter cases created before this date in ISO format "
                "(e.g., 2025-12-31)"
            ),
        ] = None,
    ) -> str:
        """Search Red Hat support cases by various criteria.

        This tool searches for support cases using filters like keyword,
        status, severity, product, and date range.

        ## Authentication Required

        This tool requires a Red Hat offline token. Set the following
        environment variable:
        - `OFFLINE_TOKEN`: Your Red Hat API offline token

        ## Filter Parameters

        All parameters are optional. When multiple filters are provided,
        they are combined (AND logic):
        - **keyword**: Full-text search across case fields
        - **status**: Filter by case status
        - **severity**: Filter by severity level
        - **product**: Filter by product name
        - **include_closed**: Include closed cases (default: false)
        - **max_results**: Maximum results to return (default: 50)
        - **start_date**: Cases created after this date
        - **end_date**: Cases created before this date

        ## Returned Data

        Returns the raw filtered case results from the API.

        Returns:
            JSON string with filtered case results
        """
        try:
            service = SupportCaseService()

            filter_params: dict[str, Any] = {"maxResults": max_results}
            if keyword:
                filter_params["keyword"] = keyword
            if status:
                filter_params["status"] = status
            if severity:
                filter_params["severity"] = severity
            if product:
                filter_params["product"] = product
            if include_closed:
                filter_params["includeClosed"] = True
            if start_date:
                filter_params["startDate"] = start_date
            if end_date:
                filter_params["endDate"] = end_date

            results = await service.search_cases(filter_params)
            return json.dumps(results, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_support_case_attachments(
        case_number: Annotated[
            str,
            Field(description="Red Hat support case number (e.g., 03619625)"),
        ],
    ) -> str:
        """List attachments for a Red Hat support case.

        This tool retrieves the metadata of all attachments associated with
        a support case (file names, sizes, dates). It does not download
        the attachment contents.

        ## Authentication Required

        This tool requires a Red Hat offline token. Set the following
        environment variable:
        - `OFFLINE_TOKEN`: Your Red Hat API offline token

        ## Returned Data

        Returns the raw attachment metadata from the API. Each attachment
        typically includes:
        - **id**: Attachment identifier
        - **name**: File name
        - **size**: File size
        - **createDate**: When the attachment was uploaded
        - **lastModifiedDate**: Last modification timestamp

        Returns:
            JSON string with attachment metadata
        """
        try:
            normalized_case = validate_case_number(case_number)
            service = SupportCaseService()
            attachments = await service.list_case_attachments(normalized_case)
            return json.dumps(attachments, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_errata(
        advisory_id: Annotated[
            str,
            Field(
                description="Red Hat advisory/errata ID "
                "(e.g., RHSA-2025:4018, RHBA-2025:1234, RHEA-2025:5678)"
            ),
        ],
    ) -> str:
        """Get Red Hat errata/advisory details by advisory ID.

        This tool retrieves detailed information about a Red Hat
        errata (security advisory, bug fix, or enhancement).

        ## Authentication Required

        This tool requires a Red Hat offline token. Set the following
        environment variable:
        - `OFFLINE_TOKEN`: Your Red Hat API offline token

        ## Advisory ID Format

        Red Hat advisory IDs follow the pattern `TYPE-YEAR:NUMBER`:
        - **RHSA**: Red Hat Security Advisory (e.g., RHSA-2025:4018)
        - **RHBA**: Red Hat Bug Fix Advisory (e.g., RHBA-2025:1234)
        - **RHEA**: Red Hat Enhancement Advisory (e.g., RHEA-2025:5678)

        ## Returned Data

        Returns the raw errata data from the RHSM API. Key fields include:
        - **id**: Advisory ID
        - **synopsis**: Short summary of the advisory
        - **description**: Full advisory description
        - **severity**: Severity level (Critical, Important, Moderate, Low)
        - **type**: Advisory type (security, bugfix, enhancement)
        - **issued**: When the advisory was issued
        - **lastUpdated**: When the advisory was last updated
        - **cves**: Space-separated list of CVE identifiers
        - **affectedProducts**: List of affected product names
        - **bugzillas**: Linked Bugzilla entries
        - **references**: Related references (CVEs, Jira issues, etc.)
        - **solution**: Instructions for applying the fix
        - **url**: Direct link to the advisory on the Red Hat Customer Portal

        Returns:
            JSON string with errata details
        """
        try:
            normalized_id = validate_advisory_id(advisory_id)
            service = SupportCaseService()
            errata_data = await service.get_errata(normalized_id)
            return json.dumps(errata_data, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
