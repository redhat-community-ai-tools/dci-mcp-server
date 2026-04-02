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
        sort: Annotated[
            str,
            Field(
                description="Sort criteria. Use a minus prefix for descending order (e.g., '-created_at'). Only date and numeric fields are sortable: 'created_at', 'updated_at', 'duration'. Text fields like 'name' or 'status' are NOT sortable and will return empty results. Default is '-created_at'."
            ),
        ] = "-created_at",
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

        ## ⚠️ COMMON MISTAKES TO AVOID

        ### 1. ALWAYS wrap conditions in parentheses
        - ❌ `status='failure'` → INVALID
        - ✅ `(status='failure')` → VALID
        - ✅ `((status='failure') and (tags in ['daily']))` → VALID

        ### 2. NEVER use `=` for dates
        - ❌ `created_at='2024-01-15'` → INVALID
        - ✅ `(created_at>='2024-01-15')` → VALID for "since Jan 15"
        - ✅ `((created_at>='2024-01-15') and (created_at<='2024-01-20'))` → VALID for period

        ### 3. Use `in` for lists, not `=`
        - ❌ `status='failure' or status='error'` → Works but verbose
        - ✅ `(status in ['failure', 'error'])` → BETTER
        - ❌ `tags='daily'` → INVALID
        - ✅ `(tags in ['daily'])` → VALID

        ### 4. Multiple components = separate conditions with AND
        - ❌ `(components.type in ['ocp', 'storage'])` → Finds jobs with OCP OR storage
        - ✅ `((components.type='ocp') and (components.version='4.19.0')) and ((components.type='storage') and (components.name='ceph'))` → Finds jobs with
        OCP 4.19.0 AND Ceph storage

        ### 5. Specify necessary fields
        - ❌ `fields=[]` → No data returned (only metadata)
        - ✅ `fields=['id', 'status', 'created_at', 'components.name']` → Essential data
        - 💡 Use dot notation for nested fields: `components.name`, `tests.testsuites.testcases.action`

        ### 6. Large results = save to file
        - ❌ `limit=200` without `__save_to_file` → Context overload
        - ✅ `limit=200, __save_to_file='/tmp/jobs.json'` → Saves context

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
        - `()` - group criteria with parentheses (ALWAYS REQUIRED)

        **Examples:**
        - Failing daily jobs: `((tags in ['daily']) and (status in ['failure', 'error']))`
        - OpenShift 4.19 jobs: `((components.type='ocp') and (components.version='4.19.0'))`
        - Jobs with workarounds: `((keys_values.key='workarounds') and (keys_values.value>0))`
        - OpenShift jobs using 4.?.* versions: `((components.type='ocp') and (components.version=~'4.1?.*'))`
        - Jobs in specific lab: `(remoteci.name='telco-cilab-bos2')`
        - Jobs by team: `(team.name='openshift-team')`
        - Jobs in date range: `((created_at>='2024-09-16') and (created_at<='2025-09-20'))`

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
        - Use >, <, >=, <= operators (NEVER use = for dates)
        - Format: `2025-09-12` or `2025-09-12T21:47:02.908617`
        - For a period: `((created_at>='2024-09-16') and (created_at<='2025-09-20'))`

        **Components & Software:**
        - `components.(type, name, version, tags)`: list of software components tested
        - Component types: `ocp` (OpenShift), `storage`, `cnf`, `hwcert`
        - Build tags: `build:ga` (GA release), `build:candidate` (RC), `build:dev` (EC), `build:nightly`
        - Example: `((components.type='ocp') and (components.version='4.19.0'))`
        - Multiple components: `((components.type='ocp') and (components.version='4.19.0')) and ((components.type='storage') and (components.name='ceph'))`

        **Infrastructure:**
        - `remoteci.(name, id)`: lab/environment where job ran (prefer remoteci.name)
        - `product.(name, id)`: product being tested (prefer product.name)
        - `team.(name, id)`: team owning the job (prefer team.name)
        - `topic.(name, id)`: topic/category (prefer topic.name)

        **Pipeline Information:**
        - `pipeline.(name, id)`: pipeline details
        - `previous_job_id`: previous job in same pipeline

        **Tags & Classification:**
        - `tags`: list of tags for categorization (ALWAYS use `in` operator)
        - Common tags:
        - `daily` - daily jobs
        - `agent:openshift` - OpenShift/OCP install jobs
        - `agent:openshift-app` - OpenShift/OCP application/workload jobs
        - `connected` - connected mode jobs
        - `disconnected` - disconnected mode jobs
        - `use-dci-container` - containerized jobs
        - `install_type:ipi` - IPI install
        - `install_type:abi` - Agent-Based Installer
        - `install_type:acm` - ACM install
        - `install_type:sno` - Single Node OpenShift
        - `install_type:upi` - UPI install

        **Files & Artifacts:**
        - `files.(id, name, size, state, mime)`: job artifacts
        - Use `download_dci_file` tool to download files
        - Example: Get file IDs with `fields=['id', 'files.id', 'files.name']`, then download

        **Metrics & Measurements:**
        - `keys_values.(key, value)`: job metrics
        - Common metrics: `install_time` (seconds), `workarounds` (count), `test_count`, `failure_count`
        - Query: `((keys_values.key='workarounds') and (keys_values.value>0))`

        **Node Information:**
        - `nodes`: list of nodes involved in the job
        - `nodes.(node, role)`: hostname and role (sno, master, worker, control-plane)
        - `nodes.kernel.(version, params)`: kernel details
        - `nodes.hardware.system_(vendor, model, family, sku)`: system info
        - `nodes.hardware.cpu_(model, vendor, sockets, total_cores, total_threads, frequency_mhz)`: CPU info
        - `nodes.hardware.memory_(total_gb, dimm_count)`: memory info
        - `nodes.hardware.bios_(vendor, version, date, type)`: BIOS info
        - `nodes.hardware.(network_interfaces, pci_accelerators, pci_network_controllers, storage_devices)`: device lists
        - Example: `((nodes.role='sno') and (nodes.hardware.cpu_vendor='Intel'))`

        **Test Results (3-level nested structure):**
        - `tests`: complex nested structure with test results
        - Structure:
        - Level 1: `tests.(file_id, name)` - test file/suite files
        - Level 2: `tests.testsuites.(name, testcases)` - test suites
        - Level 3: `tests.testsuites.testcases.(name, action, classname, time, type, properties, message, stdout, stderr)` - individual test cases
        - Actions: `run` (success), `skip` (skipped), `error` (error), `failure` (failed)
        - Types: `junit`, `robot`
        - Examples:
        - All jobs with at least 1 failed test: `((tests.testsuites.testcases.action='failure'))`
        - Failed tests in specific suite file: `((tests.name='test_suite.xml') and (tests.testsuites.testcases.action='failure'))`
        - Specific test by name: `((tests.testsuites.testcases.name='test_install') and (tests.testsuites.testcases.action='failure'))`
        - Test matching pattern: `((tests.testsuites.testcases.name=~'.*43336-V-BR.*') and (tests.testsuites.testcases.action='success'))`

        **URLs:**
        - `url`: GitHub PR or Gerrit change URL

        **Other:**
        - `jobstates`: internal job state information
        - `results`: job results data
        - `user_agent`: client information

        ## Common Use Cases

        **Find Failing Jobs:** `((status in ['failure', 'error']))`
        **Daily Jobs:** `((tags in ['daily']))`
        **OpenShift Jobs:** `(product.name='OpenShift')`
        **OpenShift Install Jobs:** `((tags in ['agent:openshift']))`
        **OpenShift Application/Workload Jobs:** `((tags in ['agent:openshift-app']))`
        **Jobs with Specific Component Version:** `((components.type='ocp') and (components.version='4.19.0'))`
        **Jobs with Multiple Components:** `((components.type='ocp') and (components.version='4.19.0')) and ((components.type='storage') and
        (components.name='ceph'))`
        **Jobs by Date Range:** `((created_at>='2024-09-16') and (created_at<='2025-09-16'))`
        **Jobs with Specific Metrics:** `((keys_values.key='install_time') and (keys_values.value>3600))`
        **Compare Jobs:** Look for jobs with same `name`, `topic`, `remoteci`, `configuration`, and `url`

        ## Function Parameters

        **query** (required): Query DSL string - see examples above

        **fields** (optional, default: []): List of fields to return
        - `[]`: NO data returned (only metadata: count, total)
        - `['id', 'status']`: only these fields
        - Use dot notation for nested fields: `components.name`, `tests.testsuites.testcases.action`
        - Recommended minimum: `['id', 'status', 'created_at']`
        - For components: `['components.type', 'components.name', 'components.version']`
        - For tests: `['tests.testsuites.testcases.name', 'tests.testsuites.testcases.action']`

        **limit** (optional, default: 20, max: 200): Number of results to return
        - If `limit > 50`, ALWAYS use `__save_to_file`
        - Example: `limit=200, __save_to_file='/tmp/jobs.json'`

        **offset** (optional, default: 0): Offset for pagination

        **sort** (optional, default: '-created_at'): Sort criteria
        - `-created_at`: newest to oldest (default)
        - `created_at`: oldest to newest
        - `-duration`: longest to shortest
        - `duration`: shortest to longest
        - ⚠️ WARNING: Only date and numeric fields are sortable (`created_at`, `updated_at`, `duration`)
        - Text fields like `name` or `status` are NOT sortable and will return empty results

        **__save_to_file** (optional, available on ALL tools): Path to save complete result
        - Use systematically if: `limit > 50`, many fields, multiple pagination, bulk analysis
        - Example: `__save_to_file='/tmp/dci/jobs.json'`

        ## Field Filtering

        The `fields` parameter filters which fields are returned in the response:
        - If `fields` is empty `[]`, no job data is returned (only metadata)
        - If `fields` contains field names, only those fields are returned
        - Use dot notation for nested fields: `components.name`, `topic.id`, `tests.testsuites.testcases.name`
        - Common field combinations:
        - Basic info: `['id', 'name', 'status', 'created_at']`
        - Component details: `['components.name', 'components.version', 'components.tags']`
        - Test results: `['tests.testsuites.testcases.name', 'tests.testsuites.testcases.action']`

        ## Response Format

        Returns JSON string with job documents under "hits" key and pagination info:
        ```json
        {
        "hits": [
            {
            "id": "job-abc-123",
            "status": "failure",
            "created_at": "2026-03-30T10:00:00",
            "components": [
                {
                "type": "ocp",
                "name": "OpenShift",
                "version": "4.19.0",
                "tags": ["build:ga"]
                }
            ]
            }
        ],
        "total": 150,
        "limit": 50,
        "offset": 0
        }
        """
        try:
            service = DCIJobService()

            # Convert fields list to server-side includes parameter
            includes = ",".join(fields) if fields else None

            result = service.search_jobs(
                query=query,
                sort=sort,
                limit=limit,
                offset=offset,
                includes=includes,
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
                    # Server already filtered fields; extract _source from ES hits
                    result["hits"]["hits"] = [
                        hit["_source"]
                        for hit in result["hits"]["hits"]
                        if "_source" in hit
                    ]
                else:
                    # If fields is empty, return no jobs
                    result["hits"]["hits"] = []

            return json.dumps(result.get("hits", []), indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)


# job_tools.py ends here
