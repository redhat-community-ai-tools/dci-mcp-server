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

import fnmatch
import logging
from typing import Annotated

from ..services.dci_job_service import DCIJobService

logger = logging.getLogger(__name__)

# Shared RCA methodology text (Steps 2-4) used by both the static
# fallback prompt and the dynamic prompt to avoid duplication.
_RCA_METHODOLOGY = """## Step 2: Root Cause Analysis using the 5 Whys Method

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

## Step 3: Adversarial Challenge

Before finalizing your root cause, actively try to DISPROVE it:

1. **Generate an alternative hypothesis** from a DIFFERENT category than your root cause. If your root cause is "Software Bug," propose an Infrastructure or Timing explanation that fits the same evidence. If it's "Infrastructure," propose a Configuration explanation.

2. **Find evidence that supports the alternative** — look in the logs for anything consistent with the alternative and inconsistent with your primary hypothesis.

3. **Apply the counterfactual test to BOTH hypotheses**:
   - If root cause A had been absent, would the job have succeeded?
   - If alternative B had been absent, would the job have succeeded?
   - If both pass the counterfactual test, you may have two contributing factors rather than one root cause.

4. **Timeline consistency**: Verify your causal chain against events.txt. Does the root cause PRECEDE all its consequences? If not, you have the causation direction wrong.

5. **Cross-failure check**: Does the root cause explain ALL failures in the job, not just the first one? Unexplained failures suggest a deeper cause.

6. **State your confidence with criteria**:
   - HIGH: root cause has direct log evidence, alternative was investigated and ruled out, timeline is consistent
   - MEDIUM: root cause fits the evidence but alternative was not fully ruled out, or some log evidence is missing
   - LOW: multiple hypotheses fit equally well, or key evidence (must_gather, events.txt) is unavailable

## Step 4: Report

Structure the report with these sections:

1. **Job Information**: components, topic, pipeline, timeline of events
2. **Failure Symptom**: what the user would observe
3. **Causal Chain (5 Whys)**: the full chain from symptom to root cause, with log evidence at each level
4. **Root Cause**: the deepest actionable cause identified
5. **Contributing Factors**: conditions that enabled or worsened the failure
6. **Confidence Level**: high, medium, or low — based on the strength of available evidence
7. **Recommendations**: what should be done to prevent recurrence
"""


def _fetch_job_metadata(job_id: str) -> dict | None:
    """Fetch job metadata (tags, components, pipeline, status_reason).

    Uses the DCI ES search API to retrieve a single job by ID with only
    the fields needed for dynamic prompt generation.

    Returns:
        A dict with keys: tags, components, pipeline_name, status_reason,
        status, topic_name.  Returns None on any failure.
    """
    try:
        service = DCIJobService()
        result = service.search_jobs(
            query=f"(id='{job_id}')",
            limit=1,
            includes="id,tags,components.name,components.type,components.version,"
            "pipeline.name,status_reason,status,topic.name,comment",
        )
        hits = result.get("hits", {}).get("hits", [])
        if not hits:
            return None
        src = hits[0].get("_source", hits[0])
        return {
            "tags": src.get("tags", []),
            "components": src.get("components", []),
            "pipeline_name": (src.get("pipeline") or {}).get("name", ""),
            "status_reason": src.get("status_reason", ""),
            "status": src.get("status", ""),
            "topic_name": (src.get("topic") or {}).get("name", ""),
            "comment": src.get("comment", ""),
        }
    except Exception:
        logger.debug("Failed to fetch metadata for job %s", job_id, exc_info=True)
        return None


def _fetch_job_files(job_id: str) -> list[dict] | None:
    """Fetch the list of files attached to a job.

    Calls the DCI API directly rather than through
    ``DCIJobService.list_job_files()``, which swallows exceptions and
    returns ``[]`` — making it impossible to distinguish *no files* from
    *API failure*.

    Paginates through the API (default page size is 20) to retrieve all
    files.

    Returns:
        A list of dicts with keys id, name, size.  Returns None on failure.
    """
    try:
        from dciclient.v1.api import job as job_api

        service = DCIJobService()
        context = service._get_dci_context()

        all_files: list[dict] = []
        limit = 200
        offset = 0

        while True:
            response = job_api.list_files(context, job_id, limit=limit, offset=offset)
            data = response.json()
            files_page = data.get("files", []) if isinstance(data, dict) else []
            all_files.extend(files_page)
            if len(files_page) < limit:
                break
            offset += limit

        return [
            {"id": f.get("id", ""), "name": f.get("name", ""), "size": f.get("size", 0)}
            for f in all_files
        ]
    except Exception:
        logger.debug("Failed to fetch files for job %s", job_id, exc_info=True)
        return None


def _classify_job_type(tags: list[str]) -> str:
    """Classify the job type based on its tags.

    Returns one of: "acm", "ztp", "upgrade", "day2", "sno", "standard".
    The first matching rule wins (most-specific first).
    """
    tag_set = {t.lower() for t in tags}

    if "install_type:acm" in tag_set:
        return "acm"
    if any("ztp" in t for t in tag_set):
        return "ztp"
    if any("upgrade" in t for t in tag_set):
        return "upgrade"
    if "agent:openshift-app" in tag_set or any("day2" in t for t in tag_set):
        return "day2"
    if any("sno" in t for t in tag_set) or "spoke" in tag_set:
        return "sno"
    return "standard"


def _prioritize_files(
    files: list[dict],
) -> dict[str, list[dict]]:
    """Categorize files into priority buckets for the RCA prompt.

    Priority buckets (P1 = most important):
      P1 – ansible.log
      P2 – logjuicer*.txt  (excluding logjuicer_omg*)
      P3 – logjuicer_omg*.txt
      P4 – *junit*
      P5 – *must_gather*.tar.gz
      P6 – *events.txt
      P7 – other *.log files
      P8 – supporting (everything else)

    Files matching skip patterns (failed_task.txt, play_recap, DCI task
    files) are excluded entirely.
    """
    skip_patterns = [
        "failed_task.txt",
        "play_recap",
        "task_*",
        "TASK *",
        "TASK [*",
        "*/TASK *",
        "*/TASK [*",
        "*/PLAY RECAP",
        "PLAY *",
        "PLAYBOOK*",
        "failed/*",
        "skipped/*",
        "dci-openshift-*-agent",
        "hardware.*",
        "kernel.*",
    ]
    buckets: dict[str, list[dict]] = {
        "P1": [],
        "P2": [],
        "P3": [],
        "P4": [],
        "P5": [],
        "P6": [],
        "P7": [],
        "P8": [],
    }

    for f in files:
        name = f.get("name", "")
        if f.get("size", 0) == 0:
            continue
        if any(fnmatch.fnmatch(name, pat) for pat in skip_patterns):
            continue

        if name == "ansible.log":
            buckets["P1"].append(f)
        elif fnmatch.fnmatch(name, "logjuicer_omg*"):
            buckets["P3"].append(f)
        elif fnmatch.fnmatch(name, "logjuicer*"):
            buckets["P2"].append(f)
        elif fnmatch.fnmatch(name, "*junit*"):
            buckets["P4"].append(f)
        elif fnmatch.fnmatch(name, "*must_gather*"):
            buckets["P5"].append(f)
        elif fnmatch.fnmatch(name, "*events.txt"):
            buckets["P6"].append(f)
        elif fnmatch.fnmatch(name, "*.log"):
            buckets["P7"].append(f)
        else:
            buckets["P8"].append(f)

    return buckets


def _build_job_type_guidance(job_type: str, components: list[dict]) -> str:
    """Return job-type-specific RCA guidance text.

    Args:
        job_type: one of the values returned by _classify_job_type().
        components: list of component dicts (name, type, version).

    Returns:
        A markdown section string, or empty string for 'standard' jobs.
    """
    if job_type == "acm":
        return """
## Job-Type Guidance: ACM (Advanced Cluster Management)

This is an ACM-managed deployment with a **hub/spoke architecture**.
- The **hub cluster** runs ACM and orchestrates spoke cluster provisioning.
- **Spoke clusters** are the managed clusters deployed by ACM.

Key ACM resources to check with `omc` or in must_gather:
- **ManagedCluster** – registration and availability status of spoke clusters
- **ClusterDeployment** – Hive cluster provisioning status
- **AgentClusterInstall** – agent-based installation progress and conditions
- **BareMetalHost** – hardware provisioning status (power, inspection, provisioning)
- **InfraEnv** – discovery ISO and agent registration
- Check ACM logs: `open-cluster-management-agent`, `assisted-service`, `infrastructure-operator`
"""

    if job_type == "ztp":
        return """
## Job-Type Guidance: ZTP (Zero Touch Provisioning)

Key ZTP resources to check:
- **SiteConfig / ClusterInstance** – declarative site definition and rendering status
- **TALM (Topology Aware Lifecycle Manager)** – `ClusterGroupUpgrade` (CGU) status and conditions
- **ArgoCD** – Application sync status, sync errors, out-of-sync resources
- **PolicyGenTemplate / PolicyGenerator** – policy rendering and compliance status
- Check that the Git repository content matches what ArgoCD applied.
"""

    if job_type == "upgrade":
        # Extract version info from components if available
        ocp_versions = [
            c.get("version", c.get("name", ""))
            for c in components
            if c.get("type", "") == "ocp"
        ]
        version_note = ""
        if ocp_versions:
            version_note = (
                f"\n- OCP component versions in this job: {', '.join(ocp_versions)}"
            )
        return f"""
## Job-Type Guidance: Upgrade Pipeline

This job is an **upgrade pipeline** — focus on the version transition.
- Compare **before and after OCP versions** to identify known upgrade issues.{version_note}
- Check **ClusterVersion** history: `oc get clusterversion version -o yaml`
- Look for **degraded ClusterOperators** after the upgrade.
- Check **MachineConfigPool** status — nodes may be stuck updating.
- Review **etcd** health and leader election during the upgrade window.
"""

    if job_type == "day2":
        return """
## Job-Type Guidance: Day-2 Operation

This job performs a **day-2 operation** (post-install workload or configuration).
- Focus on the **specific operation being performed** (operator install, workload deploy, config change).
- Check if the cluster was healthy *before* the day-2 operation started.
- Look for resource conflicts, quota limits, or scheduling issues.
- Review operator subscription and CSV (ClusterServiceVersion) status if an operator install is involved.
"""

    if job_type == "sno":
        return """
## Job-Type Guidance: SNO (Single Node OpenShift)

This is a **Single Node OpenShift** deployment.
- All control-plane and worker workloads run on one node — resource exhaustion is common.
- Check node resource usage: CPU, memory, disk pressure conditions.
- SNO has no failover — any node issue means total cluster unavailability.
- Check if the node was rebooted unexpectedly during the job.
"""

    return ""


def _build_file_section(
    buckets: dict[str, list[dict]],
    *,
    status_reason: str = "",
    job_type: str = "standard",
) -> str:
    """Build the file inventory section of the RCA prompt.

    Lists files grouped by priority with download instructions referencing
    actual file IDs.  Buckets are numbered sequentially (1, 2, 3, …) in
    the output — only non-empty buckets appear.
    """
    lines = ["## Available Files\n"]
    lines.append(
        "Below are the files attached to this job, organized by investigation "
        "priority. Use the **file ID** to download each file.\n"
    )

    # Descriptions for common supporting files to help the agent decide
    # which ones are worth downloading.
    _file_descriptions: dict[str, str] = {
        "clusteroperator.txt": "ClusterOperator status — check for degraded operators",
        "clusterversion.txt": "ClusterVersion — installed and target OCP version",
        "nodes.txt": "node status summary (Ready/NotReady)",
        "all-nodes.yaml": "full node objects with conditions and resources",
        "pods.txt": "pod status across namespaces",
        "operators.json": "installed OLM operators and subscriptions",
        "clusternetwork.yaml": "cluster network configuration",
        "machine-configs.txt": "MachineConfig and MachineConfigPool status",
        "csr.txt": "pending certificate signing requests",
        "pvc.txt": "PersistentVolumeClaim status",
        "version.txt": "OCP version string",
        "virtual-machines.txt": "KubeVirt VM status",
        "image-sources.yaml": "image content source policies (mirrors)",
        "install-config.yaml": "cluster install configuration",
        "agent-config.yaml": "agent-based installer configuration",
        "openshift_install.log": "openshift-install command output",
        "claim.json": "certsuite test claim report",
    }

    def _describe(f: dict) -> str:
        """Return a short description for a known file, or empty string."""
        name = f.get("name", "")
        # Strip spoke prefixes to match base name
        for prefix in spoke_prefixes:
            if name.startswith(prefix):
                name = name[len(prefix) :]
                break
        return _file_descriptions.get(name, "")

    def _fmt(f: dict, annotation: str = "") -> str:
        size_kb = f.get("size", 0) / 1024
        if size_kb > 1024:
            size_str = f"{size_kb / 1024:.1f} MB"
        else:
            size_str = f"{size_kb:.0f} KB"
        parts = [p for p in (annotation, _describe(f)) if p]
        suffix = f" — {'; '.join(parts)}" if parts else ""
        return f"  - `{f['name']}` (id: `{f['id']}`, {size_str}){suffix}"

    p1_description = (
        "Start here. Use `status_reason` (shown above) to jump to the "
        "failure point in the Ansible run."
        if status_reason
        else "Start here. Read through the Ansible run to find the failure point."
    )

    bucket_labels = {
        "P1": (
            "Entry Point: ansible.log",
            p1_description,
        ),
        "P2": (
            "Logjuicer diffs (Ansible logs)",
            "Diffs comparing this job's Ansible logs against the last successful "
            "run. Identify what changed.",
        ),
        "P3": (
            "Logjuicer diffs (must_gather)",
            "Diffs comparing must_gather output against the last successful run. "
            "Each file corresponds to a different must_gather archive.",
        ),
        "P4": (
            "Test results (JUnit)",
            "Test result summaries. Check which tests failed and their error messages.",
        ),
        "P5": (
            "must_gather archives",
            "Cluster state snapshots. Extract with `tar -xf <file>` and inspect "
            "with `omc use <extracted_dir>`.",
        ),
        "P6": (
            "Event logs",
            "Kubernetes events timeline. Use to verify causal ordering.",
        ),
        "P7": (
            "Other log files",
            "Additional log files that may contain relevant clues.",
        ),
        "P8": (
            "Supporting files",
            "Other files attached to the job. Download if needed for deeper "
            "investigation.",
        ),
    }

    # Detect spoke prefixes from must_gather filenames in ACM jobs.
    # e.g. "HighAvailable_must_gather.tar.gz" → prefix "HighAvailable_"
    spoke_prefixes: list[str] = []
    if job_type == "acm" and len(buckets.get("P5", [])) >= 2:
        for f in buckets["P5"]:
            name = f.get("name", "")
            if name != "must_gather.tar.gz" and name.endswith("_must_gather.tar.gz"):
                spoke_prefixes.append(name.removesuffix("must_gather.tar.gz"))

    def _acm_annotation(f: dict, bucket_key: str) -> str:
        if not spoke_prefixes or bucket_key == "P1":
            return ""
        name = f.get("name", "")
        for prefix in spoke_prefixes:
            if name.startswith(prefix):
                return f"**spoke** cluster ({prefix.rstrip('_')})"
        return "**hub** cluster"

    seq = 0
    for bucket_key in ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"):
        bucket_files = buckets.get(bucket_key, [])
        if not bucket_files:
            continue
        seq += 1
        label, description = bucket_labels[bucket_key]
        lines.append(f"\n### {seq}. {label}\n")
        lines.append(f"{description}\n")
        for f in bucket_files:
            lines.append(_fmt(f, _acm_annotation(f, bucket_key)))

    if spoke_prefixes:
        lines.append(
            "\n> **Note:** Files prefixed with "
            + " or ".join(f"`{p}`" for p in spoke_prefixes)
            + " belong to the **spoke** cluster. "
            "Unprefixed files belong to the **hub** cluster.\n"
        )

    if seq == 0:
        lines.append("\n_No files found on this job._\n")

    return "\n".join(lines)


def _static_rca_prompt(dci_job_id: str) -> str:
    """Return the static fallback RCA prompt when pre-fetching fails."""
    return f"""Conduct a root cause analysis (RCA) on the following DCI job: {dci_job_id}. Store all the downloaded files at /tmp/dci/{dci_job_id}/, so as not to download them twice. Create a report with your findings at /tmp/dci/rca-{dci_job_id}.md. Be sure to include details about the timeline of events and the DCI job information in the report, such as the components, the topic, and the pipeline name. If there is a CILAB-<num> comment, replace it with https://redhat.atlassian.net/browse/CILAB-<num>. Include a hyperlink in the form https://distributed-ci.io/jobs/<job id> each time you refer to the DCI job ID.

## Step 1: Evidence Gathering

First step is to review ansible.log (overview of the CI job execution). Then the logjuicer.txt (for regular files) and logjuicer_omg.txt (for must_gather) files that compare the logs from a previous successful run. For each difference flagged by logjuicer, determine whether it is a cause, a consequence, or unrelated to the failure.

Later always download events.txt if it is available to understand the timeline.

And lately, always validate your findings using the must_gather file and the omc utility if the must_gather file is available. Extract the must_gather file using the command: `tar -xf <must_gather_file>`. You can then use the omc utility to analyze the must_gather data using `omc use <extracted_must_gather_directory>`.

Avoid looking at the DCI task files or failed_task.txt or play_recap, as they contain the same information as ansible.log.

Do not hesitate to download any extra files that you think are relevant to the RCA.

{_RCA_METHODOLOGY}"""


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
        # -- Pre-fetch job metadata and files ----------------------------------
        metadata = _fetch_job_metadata(dci_job_id)
        files = _fetch_job_files(dci_job_id)

        # If both fetches fail, fall back to the static prompt so the agent
        # can still do its job (just without the dynamic file list).
        if metadata is None and files is None:
            return _static_rca_prompt(dci_job_id)

        # -- Build dynamic prompt sections -------------------------------------
        tags = (metadata or {}).get("tags", [])
        components = (metadata or {}).get("components", [])
        pipeline_name = (metadata or {}).get("pipeline_name", "unknown")
        status_reason = (metadata or {}).get("status_reason", "")
        status = (metadata or {}).get("status", "unknown")
        topic_name = (metadata or {}).get("topic_name", "unknown")
        comment = (metadata or {}).get("comment", "")

        job_type = _classify_job_type(tags)

        # -- Job context header ------------------------------------------------
        comp_summary = ", ".join(
            f"{c.get('type', '?')}:{c.get('name', c.get('version', '?'))}"
            for c in components
        )

        job_context = f"""## Job Context

| Field | Value |
|-------|-------|
| **Job ID** | [{dci_job_id}](https://distributed-ci.io/jobs/{dci_job_id}) |
| **Status** | {status} |
| **Pipeline** | {pipeline_name} |
| **Topic** | {topic_name} |
| **Job type** | {job_type} |
| **Tags** | {", ".join(tags) if tags else "none"} |
| **Components** | {comp_summary or "none"} |
"""
        if status_reason:
            job_context += f"""
**Status reason** (use this to locate the failure point in ansible.log):
```
{status_reason}
```
"""

        # -- File inventory section --------------------------------------------
        has_must_gather = False
        if files is not None:
            buckets = _prioritize_files(files)
            has_must_gather = bool(buckets.get("P5"))
            file_section = _build_file_section(
                buckets, status_reason=status_reason, job_type=job_type
            )
        else:
            file_section = (
                "## Available Files\n\n"
                "_File list could not be pre-fetched. "
                "Use the `search_dci_jobs` or file listing tools to discover "
                "available files for this job._\n"
            )

        # -- Job-type guidance -------------------------------------------------
        type_guidance = _build_job_type_guidance(job_type, components)

        # -- must_gather instructions -------------------------------------------
        if has_must_gather:
            must_gather_instructions = """
**MANDATORY — must_gather inspection:**
You MUST download and inspect ALL must_gather archives listed above. Do NOT skip this step.
1. Download each must_gather archive using its file ID.
2. Extract it: `tar -xf <file>`
3. Inspect with: `omc use <extracted_dir>`
4. Use `omc` to check cluster state: nodes, pods, operators, events, and any resources relevant to the failure.

Your root cause analysis is incomplete without must_gather validation. If your findings from ansible.log and logjuicer are not confirmed by must_gather data, state that explicitly.
"""
        else:
            must_gather_instructions = ""

        # -- Jira ticket instruction -------------------------------------------
        if comment:
            jira_instruction = (
                f"\nCheck that the associated Jira ticket "
                f"[{comment}](https://redhat.atlassian.net/browse/{comment}) "
                f"is consistent with your findings.\n"
            )
        else:
            jira_instruction = ""

        # -- Assemble full prompt ----------------------------------------------
        return f"""Conduct a root cause analysis (RCA) on DCI job [{dci_job_id}](https://distributed-ci.io/jobs/{dci_job_id}).

Store all downloaded files at `/tmp/dci/{dci_job_id}/` to avoid re-downloading.
Create a report at `/tmp/dci/rca-{dci_job_id}.md`.

{job_context}
{file_section}
{type_guidance}
## Step 1: Evidence Gathering

Follow the prioritized file list above. For each file:
1. Download it using its **file ID** (provided above).
2. Analyze it according to its role described in the file list.
3. For each difference flagged by logjuicer files, determine whether it is a **cause**, a **consequence**, or **unrelated** to the failure.
{must_gather_instructions}
**Avoid** looking at DCI task files, `failed_task.txt`, or `play_recap` — they duplicate ansible.log content.

Do not hesitate to download any extra files from the "Other files" or "Supporting files" sections that may be relevant.

{_RCA_METHODOLOGY}{jira_instruction}"""

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
