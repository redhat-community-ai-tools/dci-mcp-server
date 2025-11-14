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

"""Utilities for quarterly DCI job analysis."""

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def has_debug_tag(job: dict[str, Any]) -> bool:
    """
    Check if a job has the 'debug' tag.

    Args:
        job: Job dictionary

    Returns:
        True if job has 'debug' tag, False otherwise
    """
    tags = job.get("tags", [])
    if isinstance(tags, list):
        return "debug" in tags
    return False


def is_development_pipeline(pipeline_name: str) -> bool:
    """
    Check if a pipeline is a development pipeline (starts with 'pr-' or 'gr-').

    Args:
        pipeline_name: Name of the pipeline

    Returns:
        True if pipeline is a development pipeline, False otherwise
    """
    if not pipeline_name or pipeline_name == "Unknown":
        return False
    return pipeline_name.startswith("pr-") or pipeline_name.startswith("gr-")


def load_and_filter_batches(
    cache_dir: Path, start_date: datetime, end_date: datetime
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Load all batch files from cache directory and filter by date range.
    Separates jobs with 'debug' tag from regular jobs.

    Args:
        cache_dir: Path to the batches directory
        start_date: Start date for filtering
        end_date: End date for filtering

    Returns:
        Tuple of (regular_jobs, debug_jobs) - both filtered by date range
    """
    regular_jobs = []
    debug_jobs = []
    batch_files = sorted(cache_dir.glob("batch_*.json"))

    for batch_file in batch_files:
        with open(batch_file) as f:
            data = json.load(f)
            jobs = data.get("hits", [])

            # Filter by date and separate debug jobs
            for job in jobs:
                created_at_str = job.get("created_at", "")
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00")
                        )
                        if start_date <= created_at.replace(tzinfo=None) <= end_date:
                            if has_debug_tag(job):
                                debug_jobs.append(job)
                            else:
                                regular_jobs.append(job)
                    except Exception:
                        # Skip jobs with invalid dates
                        continue

    return regular_jobs, debug_jobs


def generate_statistics(
    jobs: list[dict[str, Any]], debug_jobs: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """
    Generate comprehensive statistics from job data.

    Args:
        jobs: List of regular job dictionaries (excluding debug-tagged jobs)
        debug_jobs: Optional list of debug-tagged job dictionaries

    Returns:
        Dictionary containing all computed statistics, including debug job stats if provided
    """
    # Initialize counters
    pipeline_counts = Counter()
    pipeline_status = defaultdict(
        lambda: {
            "success": 0,
            "failure": 0,
            "error": 0,
            "killed": 0,
            "running": 0,
            "new": 0,
        }
    )

    topic_counts = Counter()
    topic_status = defaultdict(
        lambda: {
            "success": 0,
            "failure": 0,
            "error": 0,
            "killed": 0,
            "running": 0,
            "new": 0,
        }
    )

    component_counts = Counter()
    component_versions = defaultdict(Counter)
    component_types = Counter()

    status_reasons = Counter()
    status_breakdown = Counter()

    daily_counts = defaultdict(int)
    daily_status = defaultdict(lambda: {"success": 0, "failure": 0})
    weekly_counts = defaultdict(int)
    weekly_status = defaultdict(lambda: {"success": 0, "failure": 0})

    # Pipeline and topic frequency trends over time
    pipeline_weekly_counts = defaultdict(lambda: defaultdict(int))
    topic_weekly_counts = defaultdict(lambda: defaultdict(int))
    pipeline_monthly_counts = defaultdict(lambda: defaultdict(int))
    topic_monthly_counts = defaultdict(lambda: defaultdict(int))

    # Process each job
    for job in jobs:
        status = job.get("status", "unknown")
        status_breakdown[status] += 1

        # Pipeline stats (exclude development pipelines)
        pipeline = job.get("pipeline", {})
        pipeline_name = pipeline.get("name", "Unknown")
        if pipeline_name and not is_development_pipeline(pipeline_name):
            pipeline_counts[pipeline_name] += 1
            pipeline_status[pipeline_name][status] += 1

        # Topic stats
        topic = job.get("topic", {})
        topic_name = topic.get("name", "Unknown")
        if topic_name:
            topic_counts[topic_name] += 1
            topic_status[topic_name][status] += 1

        # Component stats
        components = job.get("components", [])
        for comp in components:
            comp_name = comp.get("name", "Unknown")
            comp_version = comp.get("version", "Unknown")
            comp_type = comp.get("type", "Unknown")
            if comp_name and comp_name != "Unknown":
                component_counts[comp_name] += 1
                component_versions[comp_name][comp_version] += 1
                component_types[comp_type] += 1

        # Failure reasons
        if status in ["failure", "error"]:
            reason = job.get("status_reason", "No reason provided")
            if reason:
                status_reasons[reason] += 1

        # Time-based trends
        created_at_str = job.get("created_at", "")
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(
                    created_at_str.replace("Z", "+00:00")
                )
                day_of_week = created_at.strftime("%A")
                week_key = created_at.strftime("%Y-W%W")
                month_key = created_at.strftime("%Y-%m")

                daily_counts[day_of_week] += 1
                if status == "success":
                    daily_status[day_of_week]["success"] += 1
                elif status in ["failure", "error"]:
                    daily_status[day_of_week]["failure"] += 1

                weekly_counts[week_key] += 1
                if status == "success":
                    weekly_status[week_key]["success"] += 1
                elif status in ["failure", "error"]:
                    weekly_status[week_key]["failure"] += 1

                # Track pipeline and topic frequency over time (exclude development pipelines)
                if (
                    pipeline_name
                    and pipeline_name != "Unknown"
                    and not is_development_pipeline(pipeline_name)
                ):
                    pipeline_weekly_counts[pipeline_name][week_key] += 1
                    pipeline_monthly_counts[pipeline_name][month_key] += 1

                if topic_name and topic_name != "Unknown":
                    topic_weekly_counts[topic_name][week_key] += 1
                    topic_monthly_counts[topic_name][month_key] += 1
            except Exception:
                pass

    # Calculate totals
    total_jobs = len(jobs)
    success_count = status_breakdown.get("success", 0)
    failure_count = status_breakdown.get("failure", 0)
    error_count = status_breakdown.get("error", 0)

    success_rate = (success_count / total_jobs * 100) if total_jobs > 0 else 0
    failure_rate = (
        (failure_count + error_count) / total_jobs * 100 if total_jobs > 0 else 0
    )

    # Calculate durations
    durations = [job.get("duration", 0) for job in jobs if job.get("duration")]
    avg_duration = sum(durations) / len(durations) if durations else 0

    # Process development pipelines from regular jobs (pr- and gr- pipelines)
    dev_pipeline_counts = Counter()
    dev_pipeline_status = defaultdict(
        lambda: {
            "success": 0,
            "failure": 0,
            "error": 0,
            "killed": 0,
            "running": 0,
            "new": 0,
        }
    )

    for job in jobs:
        pipeline = job.get("pipeline", {})
        pipeline_name = pipeline.get("name", "Unknown")
        if pipeline_name and is_development_pipeline(pipeline_name):
            status = job.get("status", "unknown")
            dev_pipeline_counts[pipeline_name] += 1
            dev_pipeline_status[pipeline_name][status] += 1

    # Process debug jobs if provided
    debug_stats = {}
    if debug_jobs:
        debug_status_breakdown = Counter()
        debug_pipeline_counts = Counter()
        debug_topic_counts = Counter()

        for job in debug_jobs:
            status = job.get("status", "unknown")
            debug_status_breakdown[status] += 1

            pipeline = job.get("pipeline", {})
            pipeline_name = pipeline.get("name", "Unknown")
            if pipeline_name:
                debug_pipeline_counts[pipeline_name] += 1

            topic = job.get("topic", {})
            topic_name = topic.get("name", "Unknown")
            if topic_name:
                debug_topic_counts[topic_name] += 1

        # Add development pipeline jobs to debug status breakdown
        for _pipeline_name, status_dict in dev_pipeline_status.items():
            for status, count in status_dict.items():
                debug_status_breakdown[status] += count

        # Merge development pipelines from regular jobs into debug stats
        debug_pipeline_counts.update(dev_pipeline_counts)
        debug_pipeline_status_dict = {}
        for pipeline_name, status_dict in dev_pipeline_status.items():
            debug_pipeline_status_dict[pipeline_name] = dict(status_dict)

        debug_stats.update(
            {
                "total_debug_jobs": len(debug_jobs) + sum(dev_pipeline_counts.values()),
                "debug_status_breakdown": dict(debug_status_breakdown),
                "debug_pipeline_counts": dict(debug_pipeline_counts),
                "debug_topic_counts": dict(debug_topic_counts),
                "debug_pipeline_status": debug_pipeline_status_dict,
            }
        )
    elif dev_pipeline_counts:
        # If no debug jobs but we have dev pipelines, create debug stats
        dev_status_breakdown = Counter()
        for _pipeline_name, status_dict in dev_pipeline_status.items():
            for status, count in status_dict.items():
                dev_status_breakdown[status] += count

        debug_stats = {
            "total_debug_jobs": sum(dev_pipeline_counts.values()),
            "debug_status_breakdown": dict(dev_status_breakdown),
            "debug_pipeline_counts": dict(dev_pipeline_counts),
            "debug_topic_counts": {},
            "debug_pipeline_status": {
                k: dict(v) for k, v in dev_pipeline_status.items()
            },
        }

    result = {
        "total_jobs": total_jobs,
        "success_count": success_count,
        "failure_count": failure_count,
        "error_count": error_count,
        "success_rate": success_rate,
        "failure_rate": failure_rate,
        "avg_duration": avg_duration,
        "pipeline_counts": dict(pipeline_counts),
        "pipeline_status": {k: dict(v) for k, v in pipeline_status.items()},
        "topic_counts": dict(topic_counts),
        "topic_status": {k: dict(v) for k, v in topic_status.items()},
        "component_counts": dict(component_counts),
        "component_versions": {k: dict(v) for k, v in component_versions.items()},
        "component_types": dict(component_types),
        "status_reasons": dict(status_reasons.most_common(20)),
        "status_breakdown": dict(status_breakdown),
        "daily_counts": dict(daily_counts),
        "daily_status": {k: dict(v) for k, v in daily_status.items()},
        "weekly_counts": dict(weekly_counts),
        "weekly_status": {k: dict(v) for k, v in weekly_status.items()},
        "pipeline_weekly_counts": {
            k: dict(v) for k, v in pipeline_weekly_counts.items()
        },
        "topic_weekly_counts": {k: dict(v) for k, v in topic_weekly_counts.items()},
        "pipeline_monthly_counts": {
            k: dict(v) for k, v in pipeline_monthly_counts.items()
        },
        "topic_monthly_counts": {k: dict(v) for k, v in topic_monthly_counts.items()},
    }

    # Add debug stats if available
    if debug_stats:
        result.update(debug_stats)

    return result


def format_percentage(value: int, total: int) -> str:
    """Format a value as a percentage."""
    return f"{value / total * 100:.2f}%" if total > 0 else "0%"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable format."""
    hours = seconds / 3600
    if hours < 1:
        return f"{seconds / 60:.1f} minutes"
    return f"{hours:.2f} hours"


def get_failure_rate(success: int, failure: int, error: int, total: int) -> str:
    """Calculate and format failure rate."""
    if total == 0:
        return "0%"
    return f"{(failure + error) / total * 100:.2f}%"


def replace_cilab_references(text: str) -> str:
    """Replace CILAB-<num> references with Jira links."""
    import re

    pattern = r"CILAB-(\d+)"
    return re.sub(pattern, r"https://issues.redhat.com/browse/CILAB-\1", text)


def format_job_id_link(job_id: str) -> str:
    """Format a job ID as a hyperlink."""
    return f"[{job_id}](https://www.distributed-ci.io/jobs/{job_id})"


def determine_pipeline_frequency(
    pipeline_name: str,
    pipeline_weekly_counts: dict[str, dict[str, int]],
    pipeline_monthly_counts: dict[str, dict[str, int]],
    total_jobs: int,
    days_in_period: int = 90,
) -> str:
    """
    Determine the frequency pattern of a pipeline (daily, weekly, monthly, sporadic).

    Args:
        pipeline_name: Name of the pipeline
        pipeline_weekly_counts: Dictionary of pipeline weekly counts
        pipeline_monthly_counts: Dictionary of pipeline monthly counts
        total_jobs: Total number of jobs for this pipeline
        days_in_period: Number of days in the analysis period

    Returns:
        Frequency pattern string: "Daily", "Weekly", "Monthly", or "Sporadic"
    """
    if total_jobs == 0:
        return "N/A"

    # Get weekly and monthly data for this pipeline
    weekly_data = pipeline_weekly_counts.get(pipeline_name, {})
    monthly_data = pipeline_monthly_counts.get(pipeline_name, {})

    if not weekly_data and not monthly_data:
        return "Unknown"

    # Calculate average jobs per week
    weeks_with_jobs = len(weekly_data)
    total_weeks = max(len(weekly_data), 1)
    avg_per_week = total_jobs / total_weeks if total_weeks > 0 else 0

    # Calculate average jobs per day
    avg_per_day = total_jobs / days_in_period if days_in_period > 0 else 0

    # Determine frequency pattern
    # Daily: More than 0.8 jobs per day on average (runs most days)
    if avg_per_day >= 0.8:
        return "Daily"
    # Weekly: Between 0.1 and 0.8 jobs per day, or consistent weekly pattern
    elif avg_per_day >= 0.1 or (weeks_with_jobs > 0 and avg_per_week >= 1):
        # Check if it runs consistently every week
        if weeks_with_jobs >= total_weeks * 0.7:  # Runs in 70%+ of weeks
            return "Weekly"
        else:
            return "Sporadic"
    # Monthly: Less than 0.1 jobs per day but has monthly pattern
    elif len(monthly_data) > 0:
        return "Monthly"
    else:
        return "Sporadic"


def generate_report(
    stats: dict[str, Any],
    remoteci_name: str,
    start_date: datetime,
    end_date: datetime,
    output_path: Path,
) -> None:
    """
    Generate a comprehensive markdown report from statistics.

    Args:
        stats: Statistics dictionary from generate_statistics()
        remoteci_name: Name of the remoteci
        start_date: Start date of the analysis period
        end_date: End date of the analysis period
        output_path: Path where the report should be saved
    """
    report = []
    report.append(f"# Quarterly DCI Analysis Report: {remoteci_name}")
    report.append(
        f"\n**Period:** {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')} (3 months)"
    )
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**RemoteCI:** {remoteci_name}")

    # 1. Executive Summary
    report.append("\n## 1. Executive Summary\n")
    report.append(
        f"This report analyzes **{stats['total_jobs']:,}** DCI jobs executed on {remoteci_name} remoteci over the last quarter."
    )
    report.append("\n### Key Metrics:")
    report.append(f"- **Overall Success Rate:** {stats['success_rate']:.2f}%")
    report.append(f"- **Overall Failure Rate:** {stats['failure_rate']:.2f}%")
    report.append(f"- **Total Jobs:** {stats['total_jobs']:,}")
    report.append(f"- **Successful Jobs:** {stats['success_count']:,}")
    report.append(f"- **Failed Jobs:** {stats['failure_count']:,}")
    report.append(f"- **Error Jobs:** {stats['error_count']:,}")

    report.append("\n### Key Highlights:")
    if stats["success_rate"] < 50:
        report.append(
            "- ⚠️ **Low Success Rate:** Success rate below 50%, indicating significant reliability issues"
        )
    else:
        report.append(
            "- ✅ **Moderate Success Rate:** Success rate above 50%, but room for improvement"
        )

    top_pipeline = (
        max(stats["pipeline_counts"].items(), key=lambda x: x[1])
        if stats["pipeline_counts"]
        else None
    )
    if top_pipeline:
        report.append(
            f"- 📊 **Most Active Pipeline:** {top_pipeline[0]} with {top_pipeline[1]} jobs"
        )

    top_topic = (
        max(stats["topic_counts"].items(), key=lambda x: x[1])
        if stats["topic_counts"]
        else None
    )
    if top_topic:
        report.append(
            f"- 🎯 **Most Active Topic:** {top_topic[0]} with {top_topic[1]} jobs"
        )

    if stats["status_reasons"]:
        top_failure = max(stats["status_reasons"].items(), key=lambda x: x[1])
        report.append(
            f"- ❌ **Top Failure Reason:** {top_failure[0]} ({top_failure[1]} occurrences)"
        )

    # 2. Overall Statistics
    report.append("\n## 2. Overall Statistics\n")
    report.append("### Job Status Breakdown\n")
    report.append("| Status | Count | Percentage |")
    report.append("|--------|-------|------------|")
    report.append(
        f"| Success | {stats['success_count']:,} | {format_percentage(stats['success_count'], stats['total_jobs'])} |"
    )
    report.append(
        f"| Failure | {stats['failure_count']:,} | {format_percentage(stats['failure_count'], stats['total_jobs'])} |"
    )
    report.append(
        f"| Error | {stats['error_count']:,} | {format_percentage(stats['error_count'], stats['total_jobs'])} |"
    )
    report.append(
        f"| Killed | {stats['status_breakdown'].get('killed', 0):,} | {format_percentage(stats['status_breakdown'].get('killed', 0), stats['total_jobs'])} |"
    )
    report.append(
        f"| Running | {stats['status_breakdown'].get('running', 0):,} | {format_percentage(stats['status_breakdown'].get('running', 0), stats['total_jobs'])} |"
    )
    report.append(f"| **Total** | **{stats['total_jobs']:,}** | **100%** |")

    report.append("\n### Performance Metrics")
    report.append(
        f"- **Average Job Duration:** {format_duration(stats['avg_duration'])}"
    )
    report.append("- **Time Period Covered:** 90 days")
    report.append(f"- **Average Jobs per Day:** {stats['total_jobs'] / 90:.1f}")

    # 3. Pipeline Analysis
    report.append("\n## 3. Pipeline Analysis\n")

    # Top pipelines by count
    report.append("### Top Pipelines by Job Count\n")
    report.append(
        "| Pipeline Name | Total Jobs | Frequency | Success | Failure | Error | Success Rate | Failure Rate |"
    )
    report.append(
        "|---------------|------------|-----------|---------|---------|-------|--------------|--------------|"
    )

    pipeline_items = sorted(
        stats["pipeline_counts"].items(), key=lambda x: x[1], reverse=True
    )[:15]
    for pipeline_name, count in pipeline_items:
        pipeline_stat = stats["pipeline_status"].get(pipeline_name, {})
        success = pipeline_stat.get("success", 0)
        failure = pipeline_stat.get("failure", 0)
        error = pipeline_stat.get("error", 0)
        total = (
            success
            + failure
            + error
            + pipeline_stat.get("killed", 0)
            + pipeline_stat.get("running", 0)
        )
        if total == 0:
            total = count

        success_rate = format_percentage(success, total) if total > 0 else "0%"
        failure_rate = get_failure_rate(success, failure, error, total)

        # Determine frequency pattern
        frequency = determine_pipeline_frequency(
            pipeline_name,
            stats.get("pipeline_weekly_counts", {}),
            stats.get("pipeline_monthly_counts", {}),
            count,
        )

        report.append(
            f"| {pipeline_name} | {count:,} | {frequency} | {success:,} | {failure:,} | {error:,} | {success_rate} | {failure_rate} |"
        )

    # Pipeline failure rates (sorted)
    report.append("\n### Pipelines Sorted by Failure Rate (Highest First)\n")
    report.append("| Pipeline Name | Total Jobs | Failure Rate | Failure Count |")
    report.append("|---------------|------------|--------------|---------------|")

    pipeline_failure_rates = []
    for pipeline_name, count in stats["pipeline_counts"].items():
        pipeline_stat = stats["pipeline_status"].get(pipeline_name, {})
        success = pipeline_stat.get("success", 0)
        failure = pipeline_stat.get("failure", 0)
        error = pipeline_stat.get("error", 0)
        total = (
            success
            + failure
            + error
            + pipeline_stat.get("killed", 0)
            + pipeline_stat.get("running", 0)
        )
        if total == 0:
            total = count

        if total > 0:
            failure_rate_val = (failure + error) / total * 100
            pipeline_failure_rates.append(
                (pipeline_name, total, failure_rate_val, failure + error)
            )

    pipeline_failure_rates.sort(key=lambda x: x[2], reverse=True)
    for pipeline_name, total, failure_rate_val, failure_count in pipeline_failure_rates[
        :15
    ]:
        report.append(
            f"| {pipeline_name} | {total:,} | {failure_rate_val:.2f}% | {failure_count:,} |"
        )

    # Pipeline frequency trends
    if stats.get("pipeline_weekly_counts"):
        report.append("\n### Pipeline Frequency Trends (Weekly)\n")
        report.append("Frequency of top pipelines over time:\n")

        # Get top pipelines
        top_pipelines = sorted(
            stats["pipeline_counts"].items(), key=lambda x: x[1], reverse=True
        )[:5]

        # Get all weeks
        all_weeks = set()
        for pipeline_name, _ in top_pipelines:
            if pipeline_name in stats["pipeline_weekly_counts"]:
                all_weeks.update(stats["pipeline_weekly_counts"][pipeline_name].keys())

        if all_weeks:
            report.append(
                "| Week | " + " | ".join([p[0] for p in top_pipelines]) + " |"
            )
            report.append("|------|" + "|".join(["---" for _ in top_pipelines]) + "|")

            for week in sorted(all_weeks):
                row = [week]
                for pipeline_name, _ in top_pipelines:
                    count = (
                        stats["pipeline_weekly_counts"]
                        .get(pipeline_name, {})
                        .get(week, 0)
                    )
                    row.append(str(count))
                report.append("| " + " | ".join(row) + " |")

        # Monthly trends
        if stats.get("pipeline_monthly_counts"):
            report.append("\n### Pipeline Frequency Trends (Monthly)\n")
            report.append("Frequency of top pipelines by month:\n")

            all_months = set()
            for pipeline_name, _ in top_pipelines:
                if pipeline_name in stats["pipeline_monthly_counts"]:
                    all_months.update(
                        stats["pipeline_monthly_counts"][pipeline_name].keys()
                    )

            if all_months:
                report.append(
                    "| Month | " + " | ".join([p[0] for p in top_pipelines]) + " |"
                )
                report.append(
                    "|-------|" + "|".join(["---" for _ in top_pipelines]) + "|"
                )

                for month in sorted(all_months):
                    row = [month]
                    for pipeline_name, _ in top_pipelines:
                        count = (
                            stats["pipeline_monthly_counts"]
                            .get(pipeline_name, {})
                            .get(month, 0)
                        )
                        row.append(str(count))
                    report.append("| " + " | ".join(row) + " |")

    # 4. Topic Analysis
    report.append("\n## 4. Topic Analysis\n")

    report.append("### Top Topics by Job Count\n")
    report.append(
        "| Topic Name | Total Jobs | Success | Failure | Error | Success Rate | Failure Rate |"
    )
    report.append(
        "|------------|------------|---------|---------|-------|--------------|--------------|"
    )

    topic_items = sorted(
        stats["topic_counts"].items(), key=lambda x: x[1], reverse=True
    )[:15]
    for topic_name, count in topic_items:
        topic_stat = stats["topic_status"].get(topic_name, {})
        success = topic_stat.get("success", 0)
        failure = topic_stat.get("failure", 0)
        error = topic_stat.get("error", 0)
        total = (
            success
            + failure
            + error
            + topic_stat.get("killed", 0)
            + topic_stat.get("running", 0)
        )
        if total == 0:
            total = count

        success_rate = format_percentage(success, total) if total > 0 else "0%"
        failure_rate = get_failure_rate(success, failure, error, total)

        report.append(
            f"| {topic_name} | {count:,} | {success:,} | {failure:,} | {error:,} | {success_rate} | {failure_rate} |"
        )

    report.append("\n### Topics Sorted by Failure Rate (Highest First)\n")
    report.append("| Topic Name | Total Jobs | Failure Rate | Failure Count |")
    report.append("|------------|------------|--------------|---------------|")

    topic_failure_rates = []
    for topic_name, count in stats["topic_counts"].items():
        topic_stat = stats["topic_status"].get(topic_name, {})
        success = topic_stat.get("success", 0)
        failure = topic_stat.get("failure", 0)
        error = topic_stat.get("error", 0)
        total = (
            success
            + failure
            + error
            + topic_stat.get("killed", 0)
            + topic_stat.get("running", 0)
        )
        if total == 0:
            total = count

        if total > 0:
            failure_rate_val = (failure + error) / total * 100
            topic_failure_rates.append(
                (topic_name, total, failure_rate_val, failure + error)
            )

    topic_failure_rates.sort(key=lambda x: x[2], reverse=True)
    for topic_name, total, failure_rate_val, failure_count in topic_failure_rates[:15]:
        report.append(
            f"| {topic_name} | {total:,} | {failure_rate_val:.2f}% | {failure_count:,} |"
        )

    # Topic frequency trends
    if stats.get("topic_weekly_counts"):
        report.append("\n### Topic Frequency Trends (Weekly)\n")
        report.append("Frequency of top topics over time:\n")

        # Get top topics
        top_topics = sorted(
            stats["topic_counts"].items(), key=lambda x: x[1], reverse=True
        )[:5]

        # Get all weeks
        all_weeks = set()
        for topic_name, _ in top_topics:
            if topic_name in stats["topic_weekly_counts"]:
                all_weeks.update(stats["topic_weekly_counts"][topic_name].keys())

        if all_weeks:
            report.append("| Week | " + " | ".join([t[0] for t in top_topics]) + " |")
            report.append("|------|" + "|".join(["---" for _ in top_topics]) + "|")

            for week in sorted(all_weeks):
                row = [week]
                for topic_name, _ in top_topics:
                    count = (
                        stats["topic_weekly_counts"].get(topic_name, {}).get(week, 0)
                    )
                    row.append(str(count))
                report.append("| " + " | ".join(row) + " |")

        # Monthly trends
        if stats.get("topic_monthly_counts"):
            report.append("\n### Topic Frequency Trends (Monthly)\n")
            report.append("Frequency of top topics by month:\n")

            all_months = set()
            for topic_name, _ in top_topics:
                if topic_name in stats["topic_monthly_counts"]:
                    all_months.update(stats["topic_monthly_counts"][topic_name].keys())

            if all_months:
                report.append(
                    "| Month | " + " | ".join([t[0] for t in top_topics]) + " |"
                )
                report.append("|-------|" + "|".join(["---" for _ in top_topics]) + "|")

                for month in sorted(all_months):
                    row = [month]
                    for topic_name, _ in top_topics:
                        count = (
                            stats["topic_monthly_counts"]
                            .get(topic_name, {})
                            .get(month, 0)
                        )
                        row.append(str(count))
                    report.append("| " + " | ".join(row) + " |")

    # 5. Component Usage Analysis
    report.append("\n## 5. Component Usage Analysis\n")

    report.append("### Most Used Components\n")
    report.append("| Component Name | Usage Count |")
    report.append("|----------------|-------------|")

    component_items = sorted(
        stats["component_counts"].items(), key=lambda x: x[1], reverse=True
    )[:20]
    for comp_name, count in component_items:
        # Truncate long component names
        display_name = comp_name[:80] + "..." if len(comp_name) > 80 else comp_name
        report.append(f"| {display_name} | {count:,} |")

    report.append("\n### Component Types Distribution\n")
    report.append("| Component Type | Count |")
    report.append("|----------------|-------|")

    type_items = sorted(
        stats["component_types"].items(), key=lambda x: x[1], reverse=True
    )
    for comp_type, count in type_items:
        report.append(f"| {comp_type} | {count:,} |")

    # 6. Failure Analysis
    report.append("\n## 6. Failure Analysis\n")

    report.append("### Top Failure Reasons\n")
    report.append("| Failure Reason | Count | Percentage |")
    report.append("|----------------|-------|------------|")

    total_failures = stats["failure_count"] + stats["error_count"]
    for reason, count in list(stats["status_reasons"].items())[:20]:
        percentage = (
            format_percentage(count, total_failures) if total_failures > 0 else "0%"
        )
        # Truncate long reasons and replace CILAB references
        display_reason = reason[:100] + "..." if len(reason) > 100 else reason
        display_reason = replace_cilab_references(display_reason)
        report.append(f"| {display_reason} | {count:,} | {percentage} |")

    report.append("\n### Failure Rate Trends\n")
    report.append("The failure rate over the quarter shows the following patterns:")

    # Weekly trends
    report.append("\n#### Weekly Failure Rates\n")
    report.append(
        "| Week | Total Jobs | Success | Failure+Error | Success Rate | Failure Rate |"
    )
    report.append(
        "|------|------------|---------|---------------|--------------|--------------|"
    )

    weekly_items = sorted(stats["weekly_counts"].items())
    for week_key, total in weekly_items[:20]:  # Show first 20 weeks
        week_stat = stats["weekly_status"].get(week_key, {})
        success = week_stat.get("success", 0)
        failure = week_stat.get("failure", 0)
        total_week = total if total > 0 else (success + failure)

        if total_week > 0:
            success_rate = format_percentage(success, total_week)
            failure_rate = get_failure_rate(success, failure, 0, total_week)
            report.append(
                f"| {week_key} | {total_week:,} | {success:,} | {failure:,} | {success_rate} | {failure_rate} |"
            )

    # 7. Time-based Trends
    report.append("\n## 7. Time-based Trends and Patterns\n")

    report.append("### Daily Patterns (Day of Week)\n")
    report.append("| Day of Week | Total Jobs | Success | Failure | Success Rate |")
    report.append("|-------------|------------|---------|---------|--------------|")

    day_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    for day in day_order:
        if day in stats["daily_counts"]:
            total = stats["daily_counts"][day]
            day_stat = stats["daily_status"].get(day, {})
            success = day_stat.get("success", 0)
            failure = day_stat.get("failure", 0)
            success_rate = format_percentage(success, total) if total > 0 else "0%"
            report.append(
                f"| {day} | {total:,} | {success:,} | {failure:,} | {success_rate} |"
            )

    # 8. Development Activity (Debug/PR Jobs)
    if stats.get("total_debug_jobs", 0) > 0:
        report.append("\n## 8. Development Activity (Pull Requests)\n")
        report.append(
            "This section shows development jobs including:\n"
            "- Jobs with the 'debug' tag (Pull Request testing)\n"
            "- Jobs from development pipelines (pipelines starting with 'pr-' or 'gr-')\n\n"
            "These jobs are excluded from the main statistics to provide a clearer view of production/mainline job performance.\n"
        )
        report.append(f"**Total Development/PR Jobs:** {stats['total_debug_jobs']:,}\n")

        # Debug job status breakdown
        report.append("### Debug Job Status Breakdown\n")
        report.append("| Status | Count | Percentage |")
        report.append("|--------|-------|------------|")

        debug_status = stats.get("debug_status_breakdown", {})
        total_debug = stats["total_debug_jobs"]
        for status, count in sorted(
            debug_status.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (
                format_percentage(count, total_debug) if total_debug > 0 else "0%"
            )
            report.append(f"| {status.capitalize()} | {count:,} | {percentage} |")

        # Top pipelines for debug jobs
        if stats.get("debug_pipeline_counts"):
            report.append("\n### Top Pipelines for Debug/PR Jobs\n")
            report.append("| Pipeline Name | Job Count |")
            report.append("|---------------|-----------|")

            debug_pipelines = sorted(
                stats["debug_pipeline_counts"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[:15]
            for pipeline_name, count in debug_pipelines:
                report.append(f"| {pipeline_name} | {count:,} |")

        # Top topics for debug jobs
        if stats.get("debug_topic_counts"):
            report.append("\n### Top Topics for Debug/PR Jobs\n")
            report.append("| Topic Name | Job Count |")
            report.append("|------------|-----------|")

            debug_topics = sorted(
                stats["debug_topic_counts"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[:15]
            for topic_name, count in debug_topics:
                report.append(f"| {topic_name} | {count:,} |")
    else:
        report.append("\n## 8. Development Activity (Pull Requests)\n")
        report.append(
            "No development jobs (debug-tagged jobs or pr-/gr- pipelines) were found in this period. All jobs shown in this report are production/mainline jobs.\n"
        )

    # 9. Anomalies and Notable Patterns
    report.append("\n## 9. Anomalies and Notable Patterns\n")

    report.append("### Key Observations:\n")

    # Check for low success rate
    if stats["success_rate"] < 50:
        report.append(
            "- ⚠️ **Critical:** Overall success rate is below 50%, indicating systemic reliability issues"
        )

    # Check for high failure rate pipelines
    high_failure_pipelines = [
        p for p in pipeline_failure_rates if p[2] > 60 and p[1] > 10
    ]
    if high_failure_pipelines:
        report.append(
            f"\n- ⚠️ **High Failure Rate Pipelines:** {len(high_failure_pipelines)} pipelines have failure rates above 60%:"
        )
        for pipeline_name, total_jobs, failure_rate_val, _ in high_failure_pipelines[
            :5
        ]:
            report.append(
                f"  - {pipeline_name}: {failure_rate_val:.1f}% failure rate ({total_jobs} jobs)"
            )

    # Check for dominant failure reasons
    if stats["status_reasons"]:
        top_reason = max(stats["status_reasons"].items(), key=lambda x: x[1])
        if top_reason[1] > total_failures * 0.1:  # More than 10% of failures
            reason_text = replace_cilab_references(top_reason[0][:80])
            report.append(
                f"\n- 📊 **Dominant Failure Pattern:** '{reason_text}...' accounts for {top_reason[1]} failures ({format_percentage(top_reason[1], total_failures)})"
            )

    # Check for topic distribution
    if stats["topic_counts"]:
        top_topic_count = max(stats["topic_counts"].values())
        if top_topic_count > stats["total_jobs"] * 0.5:
            top_topic = max(stats["topic_counts"].items(), key=lambda x: x[1])
            report.append(
                f"\n- 📈 **Topic Concentration:** {top_topic[0]} accounts for {format_percentage(top_topic[1], stats['total_jobs'])} of all jobs"
            )

    # 10. Recommendations
    report.append("\n## 10. Recommendations\n")

    report.append("### Immediate Actions:\n")

    if stats["success_rate"] < 50:
        report.append(
            "1. **Urgent:** Investigate root causes of low success rate. Focus on:"
        )
        if stats["status_reasons"]:
            top_reasons = sorted(
                stats["status_reasons"].items(), key=lambda x: x[1], reverse=True
            )[:3]
            for i, (reason, count) in enumerate(top_reasons, 1):
                reason_text = replace_cilab_references(reason[:100])
                report.append(f"   {i}. {reason_text}... ({count} occurrences)")

    if high_failure_pipelines:
        report.append(
            "\n2. **Pipeline Optimization:** Focus improvement efforts on high-failure-rate pipelines:"
        )
        for pipeline_name, _, failure_rate_val, _ in high_failure_pipelines[:3]:
            report.append(
                f"   - {pipeline_name} ({failure_rate_val:.1f}% failure rate)"
            )

    report.append("\n### Long-term Improvements:\n")
    report.append(
        "1. **Monitoring:** Implement proactive monitoring for pipelines with failure rates above 50%"
    )
    report.append(
        "2. **Root Cause Analysis:** Conduct detailed RCA for top 5 failure reasons"
    )
    report.append(
        "3. **Testing:** Review and improve test reliability for frequently failing pipelines"
    )
    report.append(
        "4. **Documentation:** Document common failure patterns and mitigation strategies"
    )

    report.append("\n### Focus Areas:\n")
    if stats["topic_counts"]:
        problematic_topics = [t for t in topic_failure_rates if t[2] > 50 and t[1] > 20]
        if problematic_topics:
            report.append("- **Topics requiring attention:**")
            for topic_name, _, failure_rate_val, _ in problematic_topics[:5]:
                report.append(
                    f"  - {topic_name} ({failure_rate_val:.1f}% failure rate)"
                )

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(report))
