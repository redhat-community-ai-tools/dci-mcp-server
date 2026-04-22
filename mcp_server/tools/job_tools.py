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
                description="search criteria (e.g., (((components.type='ocp') and (components.version='4.19.0')) and ((components.type='storage') and (components.name='my-storage'))))"
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
                description="Page size: max job rows in the response `hits` array (default 20, max 200). When using aggregations, limit is auto-set to 1 if 0 (DCI server requires limit >= 1 for aggregations). For a cheap global count, use limit=1 with minimal fields and read the match count from `total` (integer, or `total['value']` if `total` is an object).",
                ge=0,
                le=200,
            ),
        ] = 20,
        offset: Annotated[
            int,
            Field(
                description="Skip this many matching jobs (same query/sort). Next page: previous offset + limit. Not echoed in the JSON.",
                ge=0,
            ),
        ] = 0,
        fields: Annotated[
            list[str],
            Field(
                description="List of fields to return. Fields are the one listed in the query description and responses. Must be specified as a list of strings, you can use 'components.name' or 'topic.id' to get only nested fields. If empty, no fields are returned.",
            ),
        ] = [],
        aggs: Annotated[
            dict | None,
            Field(
                description="ElasticSearch 7.16 aggregation JSON (dict). Use this when the user asks for statistics, counts, trends, or aggregated data instead of individual job documents. When provided, response includes 'aggregations' field. Set limit=1 with fields=['id'] for minimal bandwidth (1 job document + aggregation results)."
            ),
        ] = None,
    ) -> str:
        """Search DCI (Distributed CI) job documents from Elasticsearch.

        DCI jobs represent CI/CD pipeline executions that test software components
        (like OpenShift, storage solutions, etc.) across different environments.

        ## ⚠️ COMMON MISTAKES TO AVOID

        ### 1. ALWAYS wrap conditions in parentheses - CRITICAL RULE
        Each condition MUST be wrapped in parentheses. When combining conditions with AND/OR, add EXTRA parentheses to group them.

        **Single condition:**
        - ❌ `status='failure'` → INVALID (no parentheses)
        - ✅ `(status='failure')` → VALID (wrapped)

        **Two conditions (AND/OR):**
        - ❌ `(status='failure') and (tags in ['daily'])` → INVALID (missing outer parentheses)
        - ✅ `((status='failure') and (tags in ['daily']))` → VALID (each condition + outer grouping)

        **Three or more conditions:**
        - ❌ `((status='failure') and (created_at>='2024-01-01') and (duration>=1000))` → MAY FAIL
        - ✅ `(((status='failure') and (created_at>='2024-01-01')) and (duration>=1000))` → VALID (proper grouping)
        - ✅ `(((tests.testsuites.testcases.action='failure') and (nodes.hardware.cpu_vendor='Intel')) and (created_at>='2024-01-01'))` → VALID (complex nested fields)

        **Rule of thumb:** Count your conditions. If N conditions, you need N pairs of parentheses PLUS (N-1) grouping pairs.
        - 1 condition = 1 pair: `(field='value')`
        - 2 conditions = 3 pairs: `((cond1) and (cond2))`
        - 3 conditions = 5 pairs: `(((cond1) and (cond2)) and (cond3))`

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
        - ✅ `(((components.type='ocp') and (components.version='4.19.0')) and ((components.type='storage') and (components.name='ceph')))` → Finds jobs with OCP 4.19.0 AND Ceph storage

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

        **Simple Examples (1-2 conditions):**
        - Single condition: `(remoteci.name='telco-cilab-bos2')`
        - Failing daily jobs: `((tags in ['daily']) and (status in ['failure', 'error']))`
        - OpenShift 4.19 jobs: `((components.type='ocp') and (components.version='4.19.0'))`
        - Jobs with workarounds: `((keys_values.key='workarounds') and (keys_values.value>0))`
        - Date range: `((created_at>='2024-09-16') and (created_at<='2025-09-20'))`

        **Complex Examples (3+ conditions - note the extra grouping parentheses):**
        - Success jobs in date range: `(((status='success') and (created_at>='2024-01-01')) and (duration>=1000))`
        - Failed test with specific firmware: `(((tests.testsuites.testcases.name=~'PTP.*') and (tests.testsuites.testcases.action='failure')) and (nodes.hardware.network_interfaces.firmware_version='2.50'))`
        - Multiple criteria: `(((tags in ['daily']) and (status='failure')) and (created_at>='2024-01-01'))`
        - Nested fields combo: `(((components.type='ocp') and (components.version=~'4.1?.*')) and (team.name='my-team'))`

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
        - Multiple components: `(((components.type='ocp') and (components.version='4.19.0')) and ((components.type='storage') and (components.name='ceph')))`

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
        - All jobs with at least 1 failed test: `(tests.testsuites.testcases.action='failure')`
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

        **Find Failing Jobs:** `(status in ['failure', 'error'])`
        **Daily Jobs:** `(tags in ['daily'])`
        **OpenShift Jobs:** `(product.name='OpenShift')`
        **OpenShift Install Jobs:** `(tags in ['agent:openshift'])`
        **OpenShift Application/Workload Jobs:** `(tags in ['agent:openshift-app'])`
        **Jobs with Specific Component Version:** `((components.type='ocp') and (components.version='4.19.0'))`
        **Jobs with Multiple Components:** `(((components.type='ocp') and (components.version='4.19.0')) and ((components.type='storage') and (components.name='ceph')))`
        **Jobs by Date Range:** `((created_at>='2024-09-16') and (created_at<='2025-09-16'))`
        **Jobs with Specific Metrics:** `((keys_values.key='install_time') and (keys_values.value>3600))`
        **Compare Jobs:** Look for jobs with same `name`, `topic`, `remoteci`, `configuration`, and `url`

        ## ElasticSearch Aggregations (for Statistics & Analysis)

        **When to use aggregations (aggs parameter):**
        - User asks for counts, statistics, trends, distributions, or averages
        - Examples: "How many jobs failed?", "Show daily trend", "Average duration", "Count by status"
        - Aggregations compute stats server-side (much faster than fetching all documents)
        - Use `limit=1` with `fields=['id']` for aggregations to minimize bandwidth (limit=0 is auto-set to 1)

        **Aggregation syntax (ElasticSearch 7.16):**
        The aggs parameter takes a dict with aggregation definitions: `{"<agg_name>": {"<agg_type>": {...}}}`

        **Simple field aggregations (keyword, date, numeric fields):**
        - Terms (group by): `{"by_status": {"terms": {"field": "status", "size": 10}}}`
        - Date histogram: `{"daily": {"date_histogram": {"field": "created_at", "calendar_interval": "day"}}}`
        - Stats (avg, min, max, sum): `{"duration_stats": {"stats": {"field": "duration"}}}`
        - Count: `{"total": {"value_count": {"field": "id"}}}`

        **Nested field aggregations (components, tests, team, remoteci, pipeline, topic, files, keys_values, nodes):**
        Nested fields require special nested aggregation syntax:
        - Step 1: Wrap in nested aggregation with path
        - Step 2: Add filter or terms aggregation inside
        - Example for components.version:
          ```
          {
            "components_agg": {
              "nested": {"path": "components"},
              "aggs": {
                "ocp_only": {
                  "filter": {"term": {"components.type": "ocp"}},
                  "aggs": {
                    "versions": {"terms": {"field": "components.version", "size": 50}}
                  }
                }
              }
            }
          }
          ```

        **Triple-nested: tests.testsuites.testcases (test results):**
        Test data requires three levels of nested aggregations:
        ```
        {
          "tests_agg": {
            "nested": {"path": "tests"},
            "aggs": {
              "testsuites_agg": {
                "nested": {"path": "tests.testsuites"},
                "aggs": {
                  "testcases_agg": {
                    "nested": {"path": "tests.testsuites.testcases"},
                    "aggs": {
                      "by_action": {"terms": {"field": "tests.testsuites.testcases.action"}}
                    }
                  }
                }
              }
            }
          }
        }
        ```

        **Available aggregation fields by type:**
        - **Simple fields** (direct aggregation): status, tags, team_id, remoteci_id, pipeline_id, topic_id, product_id, created_at, updated_at, duration, state, name
        - **Nested fields** (need nested agg):
          - components: type, name, version, tags, canonical_project_name
          - tests → testsuites → testcases: name, action (success/failure/error/skip), classname, time, type
          - team: id, name, state, external, has_pre_release_access
          - remoteci: id, name, state, public
          - pipeline: id, name, state
          - topic: id, name, component_types, export_control
          - files: id, name, mime, size, state
          - keys_values: key, value
          - nodes → hardware: (nested within nested)
          - nodes → kernel: (nested within nested)

        **Common aggregation patterns:**
        - "How many jobs by status?" → `{"by_status": {"terms": {"field": "status"}}}`
        - "Daily job count last week" → `{"daily": {"date_histogram": {"field": "created_at", "calendar_interval": "day"}}}`
        - "Average job duration" → `{"avg_duration": {"avg": {"field": "duration"}}}`
        - "Count by team" → `{"by_team": {"terms": {"field": "team_id"}}}`
        - "OCP version distribution" → Use nested aggregation on components (see example above)
        - "Test failure rate" → Use triple-nested aggregation on tests.testsuites.testcases (see example above)

        **Combining aggregations with sub-aggregations:**
        You can nest aggregations for multi-dimensional analysis:
        ```
        {
          "daily": {
            "date_histogram": {"field": "created_at", "calendar_interval": "day"},
            "aggs": {
              "by_status": {"terms": {"field": "status"}},
              "avg_duration": {"avg": {"field": "duration"}}
            }
          }
        }
        ```

        **Response format with aggregations:**
        When aggregations are provided, the response includes an "aggregations" field with the computed statistics.
        The "hits" field will contain 1 job document (auto-set when aggs provided), or more if limit is explicitly set higher.

        ## Function Parameters

        **query** (required): Query DSL string - see examples above

        **fields** (optional, default: []): List of fields to return
        - `[]`: NO data returned (only metadata: count, total)
        - `['id', 'status']`: only these fields
        - Use dot notation for nested fields: `components.name`, `tests.testsuites.testcases.action`
        - Recommended minimum: `['id', 'status', 'created_at']`
        - For components: `['components.type', 'components.name', 'components.version']`
        - For tests: `['tests.testsuites.testcases.name', 'tests.testsuites.testcases.action']`

        **limit** (optional, default: 20, max: 200): Page size — maximum job documents in `hits` for this call. Not repeated in the JSON response; you must remember what you passed. If `limit > 50`, use `__save_to_file`.

        **offset** (optional, default: 0): Number of matching jobs to skip (same sort as `sort`). Page 1: `offset=0`. Next page: `offset` = previous `offset` + `limit`. Not repeated in the JSON response.

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

        ## Response format and pagination

        The return value is a **JSON string**. Parse it once; the top-level object has at least:

        - **`hits`**: array of job objects for this page (up to `limit` items). Shape matches your `fields` (nested objects only where you requested them). If `fields=[]`, this is always `[]` — you still get `total` for counting.
        - **`total`**: hit metadata for the query. Either a non-negative **integer** (exact match count) or an Elasticsearch-style **object** with:
        - **`value`** (int): number of matching jobs, or a **lower bound** when `relation` is `gte` (see below).
        - **`relation`** (string, when present): `eq` means `value` is the **exact** total. `gte` means there are **at least** `value` matches; the true count may be higher (Elasticsearch did not track the full total). If `relation` is omitted, treat `value` as exact unless your deployment documents otherwise.

        Let `N = total` if `total` is an int, else `N = total["value"]`. Let `rel` be `None` if `total` is an int, else `total.get("relation")`.

        There is **no** `limit` or `offset` key in the response; pagination is driven only by the tool arguments on the next call.

        **How to paginate:** Keep the same `query`, `sort`, and `fields`. Start with `offset=0`. After each page, advance `offset` by `limit` while there may be more rows:
        - If `rel == "gte"`: the only reliable stop rule is **`len(hits) < limit`** (no more full pages). Do **not** assume `N` is the full count.
        - Otherwise (`rel` is `eq`, `None`, or `total` is an int): stop when **`len(hits) < limit`** or **`offset + len(hits) >= N`**.

        **Quick count:** Exact total only when `total` is an int or `relation == "eq"` (or `relation` absent and your stack guarantees exact `value`). If `relation == "gte"`, `value` is a lower bound only — you must paginate through all pages (or accept an approximate count) for a true total.

        Example (illustrative; field names depend on `fields`):

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
          "total": {"value": 150, "relation": "eq"}
        }
        ```
        """
        try:
            service = DCIJobService()

            # DCI server requires limit >= 1 to return aggregations
            if aggs is not None and limit == 0:
                limit = 1

            # Convert fields list to server-side includes parameter
            includes = ",".join(fields) if fields else None

            result = service.search_jobs(
                query=query,
                sort=sort,
                limit=limit,
                offset=offset,
                includes=includes,
                aggs=aggs,
            )

            # manage error message from the service
            if "message" in result:
                return json.dumps(
                    {"error": result.get("message", "Unknown error")}, indent=2
                )

            # If aggregations were requested, return both aggregations and hits
            if aggs is not None:
                response = {}
                if "aggregations" in result:
                    response["aggregations"] = result["aggregations"]
                if "hits" in result and "hits" in result["hits"]:
                    if isinstance(fields, list):
                        if fields:
                            # Server already filtered fields; extract _source from ES hits
                            response["hits"] = [
                                hit["_source"]
                                for hit in result["hits"]["hits"]
                                if "_source" in hit
                            ]
                        else:
                            # If fields is empty, return no jobs
                            response["hits"] = []
                    else:
                        response["hits"] = result["hits"]["hits"]
                    response["total"] = result["hits"].get("total", 0)
                else:
                    response["hits"] = []
                    response["total"] = 0
                return json.dumps(response, indent=2)

            # Regular search (no aggregations)
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

            return json.dumps(result.get("hits", []))
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)


# job_tools.py ends here
