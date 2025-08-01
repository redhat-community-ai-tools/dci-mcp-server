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

"""Prompts for the DCI MCP server."""

from fastmcp.prompts.prompt import PromptMessage, TextContent


def register_prompts(mcp):
    """Register prompts with the MCP server."""

    @mcp.prompt()
    async def rca(dci_job_id: str) -> PromptMessage:
        """
        Prompt for Root Cause Analysis (RCA) instructions.

        Returns:
            A prompt message with instructions on how to perform RCA.
        """
        content = f"""Conduct a root cause analysis (RCA) on the following DCI job: {dci_job_id}. Store all the downloaded files at /tmp/dci/<job id>, so as not to download them twice. Always download events.txt if it is available to understand the timeline. Create a report with your findings at /tmp/dci/rca-<job id>.md. Be sure to include details about the timeline of events and the DCI job information in the report, such as the components, the topic, and the pipeline name. If there is CILAB-<num> comment, replace it by https://issues.redhat.com/browse/CILAB-<num>. Include an hyperlink each time you refer to the DCI job id.

        You can review the logjuicer.txt (for regular files) and logjuicer_omg.txt (for must_gather) files that compare the logs from a previous successful run.

        If you need to use a must-gather file, you can use the omc utility to manipulate it.
"""
        return PromptMessage(
            role="user", content=TextContent(type="text", text=content)
        )


# prompts.py ends here
