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
        """Search DCI (Distributed CI) job documents from Elasticsearch.

        DCI jobs represent CI/CD pipeline executions that test software components
        (like OpenShift, storage solutions, etc.) across different environments.

        ## Query Language (DSL)

        **Basic Operators:**
        - `field='value'` - exact match
        - `field!=value` - not equal
        - `field>value`, `field>=value`, `field<value`, `field<=value` - comparisons
        - `field=~'regex'` - regex match

        **List Operators:**
        - `field in ['value1', 'value2']` - value in list
        - `field not_in ['value1', 'value2']` - value not in list

        **Logical Operators:**
        - `and`, `or` - combine criteria
        - `()` - group criteria with parentheses

        **Examples:**
        - Failing daily jobs: `((tags in ['daily']) and (status in ['failure', 'error']))`
        - OpenShift 4.19 jobs: `((components.type='ocp') and (components.version='4.19.0'))`
        - Jobs with workarounds: `((keys_values.key='workarounds') and (keys_values.value>0))`
        - OpenShift jobs using 4.?.* versions: `((components.type='ocp') and (components.version=~'4.1?.*'))`
        - Jobs in specific lab: `(remoteci.name='telco-cilab-bos2')`
        - Jobs by team: `(team.name='openshift-team')`

        ## Available Fields

        **Basic Job Information:**
        - `id`: unique job identifier
        - `name`: job name (just a label, don't over-interpret)
        - `status`: current state (new, running, success, failure, error, killed)
        - `state`: internal job state
        - `status_reason`: explanation for failed jobs (free text)
        - `comment`: free text, may contain JIRA ticket numbers
        - `configuration`: job configuration (free text)
        - `duration`: execution time in seconds

        **Timestamps:**
        - `created_at`: job creation time
        - `updated_at`: last update time
        - Use `today` or `now` tools for relative dates
        - Use >, <, >=, <= operators (avoid = for dates)
        - Format: `2025-09-12` or `2025-09-12T21:47:02.908617`
        - For a period: `(created_at>='2024-09-16') and (created_at<='2025-09-20')`

        **Components & Software:**
        - `components.(type, name, version, tags)`: list of software components tested. Tags can be ('build:ga' for a released version, 'build:candidate' for Release Candidate or rc, 'build:dev' for engineering candidate or ec, 'build:nightly' for nightly build).
        - Example: `components.type='ocp'` for OpenShift components

        **Infrastructure:**
        - `remoteci.(name, id)`: lab/environment where job ran (use remoteci.name)
        - `product.(name, id)`: product being tested (use product.name)
        - `team.(name, id)`: team owning the job (use team.name)
        - `topic.(name, id)`: topic/category (use topic.name)

        **Pipeline Information:**
        - `pipeline.(name, id)`: pipeline details
        - `previous_job_id`: previous job in same pipeline

        **Tags & Classification:**
        - `tags`: list of tags for categorization
        - Common tags: `daily` for daily jobs, `agent:openshift` for OpenShift/OCP install jobs, `agent:openshift-app` for OpenShift/OCP application or workload jobs. `connected` for jobs using connected mode, `disconnected` for disconnected mode. `use-dci-container` for containerized jobs. `install_type:<type>` for install type (e.g., `install_type:ipi`, `install_type:abi`, `install_type:acm`...).
        - Use `in` or `not_in` operators

        **Files & Artifacts:**
        - `files.(id, name, size, state, mime)`: job artifacts
        - Use `download_dci_file` tool to download files

        **Metrics & Measurements:**
        - `keys_values.(key, value)`: job metrics
        - Examples: `install_time` (seconds), `workarounds` (count)
        - Query: `((keys_values.key='workarounds') and (keys_values.value>0))`

        **Kernel Information:**
        - `extra.kernel.(node, version, params)`: kernel details per node

        **Test Results:**
        - `tests`: complex nested structure with test results
        - Structure: `tests.(file_id,name)` → `testsuites.(name, testcases)` → `testcases.(name, action, classname, time, type, properties, message, stdout, stderr)`
        - `tests.name` is the testsuite filenames attached to the job, `file_id` is the id of the file in the job
        - Actions: run, skip, error, failure
        - Types: junit, robot
        - Example: `((tests.testsuites.testcases.action='failure') and (tests.testsuites.testcases.name='test_install'))`
        - Example: `((tests.name='test_filename') and (tests.testsuites.testcases.action='failure'))`
        - Example: `((tests.testsuites.testcases.name=~'.*43336-V-BR.*') and (tests.testsuites.testcases.action='success'))`

        **URLs:**
        - `url`: GitHub PR or Gerrit change URL
        - Examples: GitHub PR, Gerrit change

        **Other:**
        - `jobstates`: internal job state information
        - `results`: job results data
        - `user_agent`: client information

        ## Common Use Cases

        **Compare Jobs:** Look for jobs with same `name`, `topic`, `remoteci`, `configuration` and `url`

        **Find Failing Jobs:** `(status in ['failure', 'error'])`

        **Daily Jobs:** `(tags in ['daily'])`

        **OpenShift Jobs:** `(product.name='OpenShift')`

        **OpenShift install Jobs:** `(tags in ['agent:openshift'])`

        **OpenShift application/workload Jobs:** `(tags in ['agent:openshift-app'])`

        **Jobs with Specific Component Version:** `((components.type='ocp') and (components.version='4.19.0'))`

        **Jobs with Multiple Components:** `((components.type='ocp') and (components.version='4.19.0')) and ((components.type='storage') and (components.name='my-storage'))`

        **Jobs by Date Range:** `(created_at>='2024-09-16' and created_at<='2025-09-16')`

        **Jobs with Specific Metrics:** `((keys_values.key='install_time') and (keys_values.value>3600))`

        ## Field Filtering

        The `fields` parameter allows you to filter which fields are returned in the response:
        - If `fields` is empty `[]`, no job data is returned (only metadata)
        - If `fields` contains field names, only those fields are returned
        - Use dot notation for nested fields: `components.name`, `topic.id`, `tests.testsuites.testcases.name`
        - Common field combinations:
          - Basic info: `['id', 'name', 'status', 'created_at']`
          - Component details: `['components.name', 'components.version', 'components.tags']`
          - Test results: `['tests.testsuites.testcases.name', 'tests.testsuites.testcases.action']`

        Returns:
            JSON string with job documents under "hits" key and pagination info
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
