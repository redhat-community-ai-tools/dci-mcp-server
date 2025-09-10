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

"""Date tools for FastMCP server."""

import datetime
import json

from fastmcp import FastMCP


def register_date_tools(mcp: FastMCP) -> None:
    """Register date related tools with the MCP server."""

    @mcp.tool()
    async def today() -> str:
        """
        Get today's date.

        Returns:
            JSON string with today's date in this format: "YYYY-MM-DD"
        """
        # make sure the date is on the GMT timezone as DCI works in GMT
        today_date = datetime.datetime.now(datetime.UTC).date().isoformat()
        return json.dumps({"today": today_date}, indent=2)

    @mcp.tool()
    async def now() -> str:
        """
        Get current date and time.

        Returns:
            JSON string with current date and time in this format: "2025-09-12T21:47:02.908617"
        """
        # return the time in UTC timezone with the DCI expected format
        current_time = datetime.datetime.now(datetime.UTC).strftime(
            "%Y-%m-%dT%H:%M:%S.%6N"
        )
        return json.dumps({"now": current_time}, indent=2)


# date_tools.py ends here
