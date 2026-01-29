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
        dci_job_id: str = Annotated[
            str, "The DCI job ID for which to perform root cause analysis (RCA)."
        ],
    ) -> str:
        """
        Prompt for instructions on how to do a Root Cause Analysis (RCA) of a failing DCI job. Always use this prompt when analysing a failing DCI job.

        Returns:
            A prompt message with instructions on how to perform RCA of a failing DCI job.
        """
        return f"""Conduct a root cause analysis (RCA) on the following DCI job: {dci_job_id}. Store all the downloaded files at /tmp/dci/<job id>, so as not to download them twice. Create a report with your findings at /tmp/dci/rca-<job id>.md. Be sure to include details about the timeline of events and the DCI job information in the report, such as the components, the topic, and the pipeline name. If there is a CILAB-<num> comment, replace it with https://issues.redhat.com/browse/CILAB-<num>. Include a hyperlink in the form https://distributed-ci.io/jobs/<job id> each time you refer to the DCI job ID.

First step is to review ansible.log (overview of the CI job execution). Then the logjuicer.txt (for regular files) and logjuicer_omg.txt (for must_gather) files that compare the logs from a previous successful run.

Later always download events.txt if it is available to understand the timeline.

And lately, always validate your findings using the must_gather file and the omc utility if the must_gather file is available. Extract the must_gather file using the command: `tar -xf <must_gather_file>`. You can then use the omc utility to analyze the must_gather data using `omc use <extracted_must_gather_directory>`.

Avoid looking at the DCI task files or failed_task.txt or play_recap, as they contain the same information as ansible.log.

Do not hesitate to download any extra files that you think is relevant to the RCA.

Check it the associated JIRA ticket is consistent with your findings.
"""

    @mcp.prompt()
    async def weekly(
        subject: str = Annotated[
            str, "The subject of the analysis (team name or id, remoteci name or id)."
        ],
    ) -> str:
        """
        Prompt for instructions on how to analyze DCI jobs for a week.

        Returns:
            A prompt message with instructions on how to analyze DCI jobs for a week.
        """
        return f"""Analyze the DCI jobs for the last week for {subject}. Provide a summary of the number of jobs, the number of failures, and the failure rate. Identify the top 3 reasons for failures and provide recommendations for improvement. If there are any CILAB-<num> comments, replace them with https://issues.redhat.com/browse/CILAB-<num>. Include hyperlinks in the form https://distributed-ci.io/jobs/<job id> each time you refer to a DCI job ID.

Create a report with your findings in the /tmp/dci directory (create the directory if it doesn't exist). Be sure to include a summary,  statistics and anomaly detection if applicable. Use markdown formatting for the report.
        """

    @mcp.prompt()
    async def biweekly(
        subject: str = Annotated[
            str, "The subject of the analysis (team name or id, remoteci name or id)."
        ],
    ) -> str:
        """
        Prompt for instructions on how to analyze DCI jobs for 2 weeks.

        Returns:
            A prompt message with instructions on how to analyze DCI jobs for a week.
        """
        return f"""Analyze the DCI jobs for the last 2 weeks for {subject}. Provide a summary of the number of jobs, the number of failures, and the failure rate. Identify the top 3 reasons for failures and provide recommendations for improvement. If there are any CILAB-<num> comments, replace them with https://issues.redhat.com/browse/CILAB-<num>. Include hyperlinks in the form https://distributed-ci.io/jobs/<job id> each time you refer to a DCI job ID.

Create a report with your findings in the /tmp/dci directory (create the directory if it doesn't exist). Be sure to include a summary, statistics and anomaly detection if applicable. Use markdown formatting for the report.
        """

    @mcp.prompt()
    async def quarterly(
        subject: str = Annotated[
            str, "The subject of the analysis (remoteci name or id)."
        ],
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
- Replace all CILAB-<num> comments with https://issues.redhat.com/browse/CILAB-<num>
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
