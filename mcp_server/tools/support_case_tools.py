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
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.support_case_service import SupportCaseService


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
