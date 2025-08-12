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

from typing import Annotated

from fastmcp.prompts.prompt import PromptMessage, TextContent


def register_prompts(mcp):
    """Register prompts with the MCP server."""

    @mcp.prompt()
    async def rca(
        dci_job_id: str = Annotated[
            str, "The DCI job ID for which to perform root cause analysis (RCA)."
        ]
    ) -> PromptMessage:
        """
        Prompt for instructions on how to do a Root Cause Analysis (RCA) of a failing DCI job.

        Returns:
            A prompt message with instructions on how to perform RCA of a DCI job.
        """
        content = f"""Conduct a root cause analysis (RCA) on the following DCI job: {dci_job_id}. Store all the downloaded files at /tmp/dci/<job id>, so as not to download them twice. Create a report with your findings at /tmp/dci/rca-<job id>.md. Be sure to include details about the timeline of events and the DCI job information in the report, such as the components, the topic, and the pipeline name. If there is a CILAB-<num> comment, replace it with https://issues.redhat.com/browse/CILAB-<num>. Include a hyperlink each time you refer to the DCI job ID.

First step is to review ansible.log (overview of the CI job execution). Then the logjuicer.txt (for regular files) and logjuicer_omg.txt (for must_gather) files that compare the logs from a previous successful run.

Later always download events.txt if it is available to understand the timeline.

And lately, always validate your findings using the must_gather file and the omc utility if the must_gather file is available.

Avoid looking at the DCI task files or failed_task.txt or play_recap, as they contain the same information as ansible.log.

Do not hesitate to download any file that you think is relevant to the RCA.
"""
        return PromptMessage(
            role="user", content=TextContent(type="text", text=content)
        )


# prompts.py ends here
