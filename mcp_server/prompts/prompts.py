#
# Copyright (C) 2025-2026 Red Hat, Inc.
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


def register_prompts(mcp):
    """Register prompts with the MCP server."""

    @mcp.prompt()
    async def rca(
        dci_job_id: Annotated[
            str, "The DCI job ID for which to perform root cause analysis (RCA)."
        ],
    ) -> str:
        """
        Prompt for instructions on how to do a Root Cause Analysis (RCA) of a failing DCI job. Always use this prompt when analysing a failing DCI job.

        Returns:
            A prompt message with instructions on how to perform RCA of a failing DCI job.
        """
        return f"""Conduct a root cause analysis (RCA) on the following **DCI job** (numeric job id): {dci_job_id}.

**Output paths (do not confuse with Jira):** For DCI jobs, store downloaded artifacts under `/tmp/dci/<job id>/` (avoid re-downloading). Write the report to **`/tmp/dci/rca-<job id>.md`**. For **Jira Closed Loop** tickets (e.g. ECOENGCL-*), use the **`eda`** prompt instead; those reports belong at **`/tmp/dci/rca-eda-<JIRA-KEY>.md`**.

Be sure to include details about the timeline of events and the DCI job information in the report, such as the components, the topic, and the pipeline name. If there is a CILAB-<num> comment, replace it with https://redhat.atlassian.net/browse/CILAB-<num>. Include a hyperlink in the form https://distributed-ci.io/jobs/<job id> each time you refer to the DCI job ID.

## Step 1: Evidence Gathering

First step is to review ansible.log (overview of the CI job execution). Then the logjuicer.txt (for regular files) and logjuicer_omg.txt (for must_gather) files that compare the logs from a previous successful run. For each difference flagged by logjuicer, determine whether it is a cause, a consequence, or unrelated to the failure.

Later always download events.txt if it is available to understand the timeline.

And lately, always validate your findings using the must_gather file and the omc utility if the must_gather file is available. Extract the must_gather file using the command: `tar -xf <must_gather_file>`. You can then use the omc utility to analyze the must_gather data using `omc use <extracted_must_gather_directory>`.

Avoid looking at the DCI task files or failed_task.txt or play_recap, as they contain the same information as ansible.log.

Do not hesitate to download any extra files that you think are relevant to the RCA.

## Step 2: Root Cause Analysis using the 5 Whys Method

After gathering evidence, apply the "5 Whys" technique to drill down to the true root cause. Do not stop at the first error you find — that is usually a symptom, not the cause.

1. **Identify the failure symptom**: What exactly failed? (e.g., "test X timed out", "pod Y in CrashLoopBackOff", "ansible task Z returned rc=1")
2. **Ask "Why did this happen?"** and find evidence in the logs supporting the answer.
3. **Repeat**: For each answer, ask "Why?" again, each time supported by specific log evidence.
4. **Continue for at least 5 levels** or until you reach a cause that is:
   - An external factor (infrastructure issue, upstream bug, environment configuration)
   - A systemic issue (resource limits, race condition, design flaw)
   - Something actionable that can be directly fixed
5. **Document the full causal chain** in your report (Why 1 -> Why 2 -> ... -> Root Cause).

At each level, cite the specific log file and relevant log lines as evidence.

### Categorize potential causes

Before narrowing down, consider causes across these categories to avoid tunnel vision:
- **Infrastructure**: hardware, network, storage, resource exhaustion
- **Configuration**: cluster settings, deployment parameters, environment variables
- **Software Bug**: known issues, regressions in components
- **Environment**: DNS, certificates, external service dependencies
- **Timing/Race Condition**: ordering issues, timeouts, concurrency problems

## Step 3: Cross-validation

Before finalizing your root cause:
- Verify your causal chain is consistent with the timeline from events.txt.
- Check if the same root cause explains ALL the failures in the job, not just the first one.
- Look for earlier warnings or errors that preceded the main failure.
- If must_gather is available, confirm your hypothesis with cluster state.
- **Counterfactual check**: If this root cause had been absent, would the job have succeeded? If not, you may have found a contributing factor rather than the root cause.

## Step 4: Report

Structure the report with these sections:

1. **Job Information**: components, topic, pipeline, timeline of events
2. **Failure Symptom**: what the user would observe
3. **Causal Chain (5 Whys)**: the full chain from symptom to root cause, with log evidence at each level
4. **Root Cause**: the deepest actionable cause identified
5. **Contributing Factors**: conditions that enabled or worsened the failure
6. **Confidence Level**: high, medium, or low — based on the strength of available evidence
7. **Recommendations**: what should be done to prevent recurrence

Check that the associated JIRA ticket is consistent with your findings.
"""

    @mcp.prompt()
    async def eda(
        jira_ticket_key: Annotated[
            str,
            "Jira issue key (e.g. ECOENGCL-446) for EcoSystem Engineering Close Loop / EDA work.",
        ],
    ) -> str:
        """
        Prompt for a Jira-based RCA/EDA write-up for a Closed Loop ticket (not a DCI job).

        Returns:
            Instructions to produce `/tmp/dci/rca-eda-<KEY>.md` aligned with Escape Defect Analysis fields.
        """
        return f"""Produce an **RCA/EDA report** for Jira ticket **{jira_ticket_key}** (EcoSystem Engineering Close Loop or similar). This is **not** a DCI job RCA — do not use `rca`/`rca-<job id>.md`; use the filename below.

## Output

- Create **`/tmp/dci/rca-eda-{jira_ticket_key}.md`** (directory `/tmp/dci` may already exist on the server from other work).
- Use clear markdown with a title like: `# RCA/EDA Report — {jira_ticket_key}`

## Step 1: Gather issue data

- Use **`get_jira_ticket`** for `{jira_ticket_key}` and pull description, components, status, assignee, reporter, links (bugs, upstream), and **custom fields** used for EDA where available (e.g. Escape Reason, Escape Impact, Corrective Measures, SDLC stages — often `customfield_*` ids such as `customfield_10994` for Corrective Measures).
- Use **`search_jira_tickets`** or comments if you need related context; prefer authoritative Jira text over guesses.

## Step 2: Draft these sections (match common on-server examples)

1. **Ticket Information** — Key, summary, status, people, components, QA contact if present, linked bugs/upstreams with working links (`https://redhat.atlassian.net/browse/{jira_ticket_key}` for this ticket; `https://issues.redhat.com/browse/...` for OCPBUGS-style keys when applicable).
2. **Problem Summary** — What failed from the customer/field perspective; bullet notable log lines or behaviors if described in Jira.
3. **Root Cause Analysis** — Causal explanation (numbered sub-steps are fine); cite Jira/description/comments, not invented logs unless provided.
4. **Fix Details** — Upstream/OCPBUGS state, code or design changes, backports if stated.
5. **EDA Fields** — A markdown table:

| Field | Value |
|-------|-------|
| Escape Reason | … |
| Escape Impact | … |
| Corrective Measures | … |
| Stage Introduced / Found / Should Have Been Found | … |
| Test Coverage | … (if applicable) |

Fill rows from Jira when the fields exist; use "—" or "Not stated in ticket" when missing.

## Step 3: Quality checks

- Keep partner/customer names and sensitive identifiers only as they appear on the ticket; do not invent names.
- If Corrective Measures or other multi-select values are opaque from the API, say so briefly or paste human-readable values from the Jira UI if you have them.
"""

    @mcp.prompt()
    async def review_queue(
        notes: Annotated[
            str,
            "Optional: e.g. a component name, or 'OCP only' / 'RHEL only' to narrow narrative focus.",
        ] = "",
    ) -> str:
        """
        Prompt to refresh or work with the EcoSystem Engineering Close Loop Review backlog CSV.

        Returns:
            Instructions tied to `reports/review-queue-corrective-component-ocp-rhel.csv` and the fill script.
        """
        extra = f"\n\n**User focus:** {notes}\n" if notes.strip() else ""
        return f"""Help maintain the **Review** backlog spreadsheet for **EcoSystem Engineering Close Loop** Closed Loop issues in **Review** status.{extra}
## Artifacts (repo)

- **`reports/review-queue-corrective-component-ocp-rhel.csv`** — columns include `key`, **`partner_or_customer`** (paste or fill from Jira), `corrective_measures_paste_from_jira`, `jira_component`, `ocp_rhel_category`, `summary`.
- **`reports/closed-loop-review-report.md`** — JQL, Corrective Measures routing guidance, and a human-readable table mirroring the CSV.

## Refresh from Jira

From the repository root (with `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` in `.env`):

```bash
uv run python scripts/fill_review_queue_corrective_measures.py
```

- Optionally set **`JIRA_PARTNER_CUSTOM_FIELD`** (e.g. `customfield_12345`) in `.env` so **`partner_or_customer`** is populated when the API returns readable values.
- If **Corrective Measures** stay empty from the API, paste labels from the Jira issue screen into the CSV (same as documented in the report).

## JQL (reference)

`project = "EcoSystem Engineering Close Loop" AND type = "Closed Loop" AND status = Review AND ...` — use the saved filter / full JQL from **`reports/closed-loop-review-report.md`** for the exact resolution and date clauses.

When answering, prefer updating the CSV and report paths above over inventing new filenames unless the user asks otherwise.
"""

    @mcp.prompt()
    async def weekly(
        subject: Annotated[
            str, "The subject of the analysis (team name or id, remoteci name or id)."
        ],
    ) -> str:
        """
        Prompt for instructions on how to analyze DCI jobs for a week.

        Returns:
            A prompt message with instructions on how to analyze DCI jobs for a week.
        """
        return f"""Analyze the DCI jobs for the last week for {subject}. Provide a summary of the number of jobs, the number of failures, and the failure rate. Identify the top 3 reasons for failures and provide recommendations for improvement. If there are any CILAB-<num> comments, replace them with https://redhat.atlassian.net/browse/CILAB-<num>. Include hyperlinks in the form https://distributed-ci.io/jobs/<job id> each time you refer to a DCI job ID.

Create a report with your findings in the /tmp/dci directory (create the directory if it doesn't exist). Be sure to include a summary,  statistics and anomaly detection if applicable. Use markdown formatting for the report.
        """

    @mcp.prompt()
    async def biweekly(
        subject: Annotated[
            str, "The subject of the analysis (team name or id, remoteci name or id)."
        ],
    ) -> str:
        """
        Prompt for instructions on how to analyze DCI jobs for 2 weeks.

        Returns:
            A prompt message with instructions on how to analyze DCI jobs for a week.
        """
        return f"""Analyze the DCI jobs for the last 2 weeks for {subject}. Provide a summary of the number of jobs, the number of failures, and the failure rate. Identify the top 3 reasons for failures and provide recommendations for improvement. If there are any CILAB-<num> comments, replace them with https://redhat.atlassian.net/browse/CILAB-<num>. Include hyperlinks in the form https://distributed-ci.io/jobs/<job id> each time you refer to a DCI job ID.

Create a report with your findings in the /tmp/dci directory (create the directory if it doesn't exist). Be sure to include a summary, statistics and anomaly detection if applicable. Use markdown formatting for the report.
        """

    @mcp.prompt()
    async def quarterly(
        subject: Annotated[str, "The subject of the analysis (remoteci name or id)."],
    ) -> str:
        """
        Prompt for instructions on how to analyze DCI jobs for a quarter (3 months).

        Returns:
            A prompt message with instructions on how to analyze DCI jobs for a quarter.
        """
        return f"""Analyze the DCI jobs for the last quarter (3 months) for {subject}. Due to the large volume of data, you must use a multi-step approach with caching to avoid exhausting the context window.

## Step 1: Data Collection and Caching

First, use the `today` tool to get the current date and calculate the quarter date range (last 3 months from today).

Then, fetch all jobs using pagination with the `search_dci_jobs` tool:
- Use `limit=200` (maximum allowed) for each batch
- Start with `offset=0`, then increment by 200 until no more results are returned
- Query format: `(remoteci.name='{subject}' or remoteci.id='{subject}') and (created_at>='<start_date>' and created_at<='<end_date>')`
- Fetch essential fields: `['id', 'name', 'status', 'created_at', 'duration', 'status_reason', 'tags', 'pipeline.name', 'pipeline.id', 'topic.name', 'topic.id', 'components.name', 'components.version', 'components.type', 'components.tags']`

**Important:** Jobs with the 'debug' tag are Pull Request jobs and will be excluded from main statistics but included in a separate "Development Activity" section.

Cache each batch to disk:
- Cache directory: `/tmp/dci/<remoteci>/quarterly/<start_date>-<end_date>/batches/`
- Save each batch as: `batch_<offset>.json` (e.g., `batch_0.json`, `batch_200.json`, etc.)
- Create the directory structure if it doesn't exist
- Save the raw JSON response from each `search_dci_jobs` call

**Important**: Before fetching, check if cached data already exists. If batches are already present, skip the data collection step and proceed directly to analysis.

## Step 2: Data Aggregation

Load all cached batch files from the cache directory:
- Read each `batch_<offset>.json` file
- Extract the job data from the JSON structure (look for `hits.hits` or similar)
- Combine all jobs into a single dataset
- Verify the total count matches expected results

**Note:** You can use the utility functions from `mcp_server.utils.quarterly_analysis` to help with this:
- Use `load_and_filter_batches(cache_dir, start_date, end_date)` to load and filter batches by date. This function returns a tuple: `(regular_jobs, debug_jobs)` - jobs with 'debug' tag are automatically separated.
- Import it in Python: `from mcp_server.utils.quarterly_analysis import load_and_filter_batches`

## Step 3: Statistics Generation

Compute comprehensive statistics from the aggregated data:

**Note:** You can use the utility function `generate_statistics(jobs, debug_jobs)` from `mcp_server.utils.quarterly_analysis` to compute all statistics automatically. Pass regular jobs and debug jobs separately. Import it: `from mcp_server.utils.quarterly_analysis import generate_statistics`

Alternatively, manually compute:

**Pipeline Statistics:**
- Frequency: Count jobs per pipeline name
- Failure rates: Calculate success/failure rates per pipeline
- Top pipelines: Identify pipelines with most jobs
- Trends: Analyze pipeline usage over time (weekly/monthly patterns)

**Topic Statistics:**
- Frequency: Count jobs per topic name
- Failure rates: Calculate success/failure rates per topic
- Top topics: Identify topics with most jobs
- Trends: Analyze topic usage over time

**Failure Analysis:**
- Top failure reasons: Aggregate `status_reason` field, identify most common reasons
- Failure rate trends: Calculate failure rate over time (daily/weekly)
- Status breakdown: Count jobs by status (success, failure, error, killed, running)
- Failure patterns: Identify patterns in failing jobs (specific pipelines, topics, components)

**Component Usage:**
- Most used components: Count frequency of component names
- Component versions: Analyze version distribution
- Component trends: Track component usage over time
- Component failure correlation: Identify components associated with failures

**Time-based Trends:**
- Daily patterns: Job counts and success rates by day of week
- Weekly patterns: Job counts and success rates by week
- Success rate over time: Track success rate trends throughout the quarter
- Peak activity periods: Identify times with highest job activity

**Anomaly Detection:**
- Unusual patterns: Identify spikes in failures, unusual job counts
- Notable events: Detect periods with significant changes in patterns
- Outliers: Identify pipelines, topics, or components with unusual behavior

## Step 4: Report Creation

Create a comprehensive markdown report with the following structure:

**Note:** You can use the utility function `generate_report(stats, remoteci_name, start_date, end_date, output_path)` from `mcp_server.utils.quarterly_analysis` to generate the complete report automatically. Import it: `from mcp_server.utils.quarterly_analysis import generate_report`

Alternatively, manually create the report with the following structure:

1. **Executive Summary**
   - Total jobs analyzed
   - Overall success rate and failure rate
   - Key highlights and findings

2. **Overall Statistics**
   - Total jobs, successes, failures, errors
   - Average job duration
   - Time period covered

3. **Pipeline Analysis**
   - Pipeline frequency table (top pipelines by job count)
   - Pipeline failure rates (sorted by failure rate)
   - Pipeline trends over time
   - Notable pipeline patterns

4. **Topic Analysis**
   - Topic frequency table (top topics by job count)
   - Topic failure rates (sorted by failure rate)
   - Topic trends over time
   - Notable topic patterns

5. **Component Usage Analysis**
   - Most used components
   - Component version distribution
   - Component usage trends
   - Component-failure correlations

6. **Failure Analysis**
   - Top failure reasons (with counts and percentages)
   - Failure rate trends over time
   - Status breakdown
   - Failure patterns by pipeline/topic/component

7. **Time-based Trends and Patterns**
   - Daily/weekly patterns
   - Success rate trends over time
   - Peak activity periods
   - Timeline visualization (if possible)

8. **Anomalies and Notable Patterns**
   - Unusual events or patterns detected
   - Significant changes in behavior
   - Outliers and exceptions

9. **Recommendations**
   - Actionable insights based on findings
   - Areas for improvement
   - Focus areas for investigation

**Additional Requirements:**
- Replace all CILAB-<num> comments with https://redhat.atlassian.net/browse/CILAB-<num>
- Include hyperlinks each time you refer to a DCI job ID
- Use markdown formatting with tables, headers, and lists
- Save the report to: `/tmp/dci/<remoteci>/quarterly/<date-range>/report.md`
- Ensure the report is well-structured and easy to read
- Include visualizations or summaries where helpful (tables, lists, etc.)

**Processing Strategy:**
- Process data in chunks if needed to stay within context limits
- Focus on the most interesting and actionable insights
- Prioritize statistics that reveal patterns and trends
- Be thorough but concise in the report
"""


# prompts.py ends here
