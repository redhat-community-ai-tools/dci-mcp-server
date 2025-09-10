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

"""MCP tools for DCI job operations."""

import json
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.dci_job_service import DCIJobService


def filter_jobs_by_fields(jobs: list, fields: list) -> list:
    """Filter jobs by fields."""

    if not fields:
        return []

    def get_nested_value(obj, field_path):
        """Get nested value from object using dot notation."""
        keys = field_path.split(".")
        current = obj
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    # Handle both simple job lists and Elasticsearch response format
    if isinstance(jobs, dict) and "hits" in jobs and "hits" in jobs["hits"]:
        # Full Elasticsearch response format
        job_list = jobs["hits"]["hits"]
        # Extract _source if present, otherwise use the job directly
        job_data = []
        for job in job_list:
            if "_source" in job:
                job_data.append(job["_source"])
            else:
                job_data.append(job)
    elif (
        isinstance(jobs, list)
        and len(jobs) > 0
        and isinstance(jobs[0], dict)
        and "_source" in jobs[0]
    ):
        # List of Elasticsearch job objects (each has _source)
        job_data = []
        for job in jobs:
            if "_source" in job:
                job_data.append(job["_source"])
            else:
                job_data.append(job)
    else:
        # Simple job list format - jobs are already the source data
        job_data = jobs

    # Group fields by their top-level key for better handling
    field_groups = {}
    simple_fields = []

    for field in fields:
        if "." in field:
            top_key = field.split(".")[0]
            if top_key not in field_groups:
                field_groups[top_key] = []
            field_groups[top_key].append(field)
        else:
            simple_fields.append(field)

    filtered_result = []
    for job in job_data:
        filtered_job = {}

        # Handle simple fields first
        for field in simple_fields:
            value = get_nested_value(job, field)
            if value is not None:
                filtered_job[field] = value

        # Handle nested field groups
        for top_key, field_list in field_groups.items():
            if top_key in job and isinstance(job[top_key], list):
                # Handle list fields like components
                nested_items = []
                for item in job[top_key]:
                    if isinstance(item, dict):
                        nested_item = {}
                        for field in field_list:
                            if "." in field:
                                nested_field = field.split(".", 1)[
                                    1
                                ]  # Get the part after the first dot
                                value = get_nested_value(item, nested_field)
                                if value is not None:
                                    nested_item[nested_field] = value
                        if nested_item:  # Only add if we found some fields
                            nested_items.append(nested_item)
                if nested_items:
                    filtered_job[top_key] = nested_items
            else:
                # Handle non-list nested fields
                nested_obj = {}
                for field in field_list:
                    if "." in field:
                        nested_field = field.split(".", 1)[
                            1
                        ]  # Get the part after the first dot
                        value = get_nested_value(job, field)
                        if value is not None:
                            nested_obj[nested_field] = value
                if nested_obj:
                    filtered_job[top_key] = nested_obj
        filtered_result.append(filtered_job)

    return filtered_result


def register_job_tools(mcp: FastMCP) -> None:
    """Register job-related tools with the MCP server."""

    @mcp.tool()
    async def search_dci_jobs(
        query: Annotated[
            str,
            Field(
                description="search criteria (e.g., ((components.type='ocp') and (components.version='4.19.0')) and ((components.type='storage') and (components.name='my-storage'))"
            ),
        ],
        sort: Annotated[str, Field(description="Sort criteria")] = "-created_at",
        limit: Annotated[
            int,
            Field(
                description="Maximum number of results to return for pagination (default 20, max 200). Use limit=1 to get count from metadata.",
                ge=1,
                le=200,
            ),
        ] = 20,
        offset: Annotated[int, Field(description="Offset for pagination", ge=0)] = 0,
        fields: Annotated[
            list[str],
            Field(
                description="List of fields to return. Fields are the one listed in the query description and responses. Must be specified as a list of strings, you can use 'components.name' or 'topic.id' to get only nested fields. If empty, no fields are returned.",
            ),
        ] = [],
    ) -> str:
        """Search DCI job documents from Elasticsearch.

        The query language is based on this DSL:

        <field>='<value>' to lookup resources with a <field> having the value <value>.
        You can use the comparison operators !=, >, >=, <, <= using the same syntax as =: <field><op>'<value>'. =~ is the operator for a regex match.

        The is also a `in` operator to check if a value is in a list of values. The `not_in` operator checks if a value is not in a list of values. The `and`, and `or` operators are supported to combine multiple criteria. Parentheses can be used to group criteria. For example, to get failing daily jobs, use ((tags in ['daily']) and (status in ['failure', 'error'])).

        You can search for sub-object fields like components or tests. If you need multiple criteria for a sub-object, you need to group them with parentheses. For example, to get jobs with a component of type ocp and version 4.19.0, use ((components.type='ocp') and (components.version='4.19.0')).

        Here are the fields to be used in the query:

        - comment: free text. Can contain a JIRA ticket number.
        - components.(type, name, version): list of components (software) associated with the job.
        - configuration: representation of the job configuration. It is a free text field.
        - created_at: The creation timestamp. Use `today` tool to compute relative dates or `now` tool to compute relative times.  Use the >, <, >=, <= operators to filter jobs by last update date. Do not use the = operator with a date on this field as it means the hour is 00:00:00 UTC. You can use a date like 2025-09-12 or a time like 2025-09-12T21:47:02.908617.
        - duration: duration in seconds.
        - extra.kernel.(node, version, params): kernel information for each node if available.
        - files.(id, name, size, state, type, url): list of files associated with the job. If you want to download a file, use the download_dci_file tool.
        - id: unique identifier
        - jobstates
        - keys_values.(key, value): metric associated with the job. For example, OpenShift install jobs have a metric called `install_time` with the installation time in seconds. Jobs can also have a workarounds metrics to count the number of workarounds applied during the job. To find jobs with at least one workaround, use the query "((keys_values.key='workarounds') and (keys_values.value>0))".
        - name: name of the job. Don't associate too many meanings to the job name. It is just a label.
        - pipeline.(name, id): pipeline information
        - previous_job_id: the previous job ID if any in the same pipeline.
        - product.(name, id): product information. Always use product.name in the query if possible.
        - remoteci.(name, id): the remote CI associated with the job. It represents the lab. Always use remoteci.name in the query if possible.
        - results
        - state
        - status: The current state  (new, running, success, failure, error, killed). Finished jobs have a status of killed, success, failure, or error. Failing jobs have a status of failure or error.
        - status_reason: explanation of the failed job. It is a free text field.
        - tags: : list of tags associated with the job. Daily jobs refers to a daily tag. OpenShift install jobs have a tag like agent:openshift. OpenShift application or workload jobs have a tag like agent:openshift-app. Use the `in` or `not_in` operators to filter jobs by tags.
        - team.(name, id): team information. Always use team.name in the query if possible.
        - tests.(name, testsuites.testcases.(name, action, classname, time, type, properties, message, stdout, stderr)): list of tests associated with the job. Each test has a name and a list of test suites. Each test suite has a name and a list of test cases. Each test case has a name, an action (run, skip, error, failure), a classname, a time in seconds, a type (junit or robot), properties (key/value pairs), a message (for failures and errors), stdout and stderr.
        - topic.(name, id): topic information Always use topic.name in the query if possible.
        - updated_at: The last update timestamp. Use `today` tool to compute relative dates or `now` tool to compute relative times. Use the >, <, >=, <= operators to filter jobs by last update date. Do not use the = operator with a date on this field as it means the hour is 00:00:00 UTC. You can use a date like 2025-09-12 or a time like 2025-09-12T21:47:02.908617.
        - url: The URL associated with the job can be a GitHub PR URL (like https://github.com/redhatci/ansible-collection-redhatci-ocp/pull/771) or a Gerrit change URL. Gerrit changes URL can be like https://softwarefactory-project.io/r/c/python-dciclient/+/34227.
        - user_agent

        If you need to compare jobs, look for jobs with the same name, topic, remoteci and url.

        Returns:
            JSON string with list of job documents under the key "hits" and pagination info
        """
        try:
            service = DCIJobService()

            result = service.search_jobs(
                query=query, sort=sort, limit=limit, offset=offset
            )

            # manage error message from the service
            if "message" in result:
                return json.dumps(
                    {"error": result.get("message", "Unknown error")}, indent=2
                )
            # manage empty result
            if "hits" not in result or "hits" not in result["hits"]:
                return json.dumps({"hits": []}, indent=2)

            if isinstance(fields, list):
                if fields:
                    # Filter the result to only include specified fields
                    result["hits"]["hits"] = filter_jobs_by_fields(
                        result["hits"]["hits"], fields
                    )
                else:
                    # If fields is empty, return no jobs
                    result["hits"]["hits"] = []

            return json.dumps(result.get("hits", []), indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)


# job_tools.py ends here
