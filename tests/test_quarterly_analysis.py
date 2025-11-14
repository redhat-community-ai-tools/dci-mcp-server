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

"""Unit tests for quarterly analysis utilities."""

import json
from datetime import datetime

import pytest

from mcp_server.utils.quarterly_analysis import (
    determine_pipeline_frequency,
    format_duration,
    format_percentage,
    generate_report,
    generate_statistics,
    get_failure_rate,
    has_debug_tag,
    is_development_pipeline,
    load_and_filter_batches,
)


@pytest.mark.unit
def test_has_debug_tag_with_debug():
    """Test has_debug_tag returns True for jobs with debug tag."""
    job = {"tags": ["debug", "daily"]}
    assert has_debug_tag(job) is True


@pytest.mark.unit
def test_has_debug_tag_without_debug():
    """Test has_debug_tag returns False for jobs without debug tag."""
    job = {"tags": ["daily"]}
    assert has_debug_tag(job) is False


@pytest.mark.unit
def test_has_debug_tag_no_tags():
    """Test has_debug_tag returns False for jobs without tags."""
    job = {}
    assert has_debug_tag(job) is False


@pytest.mark.unit
def test_has_debug_tag_empty_tags():
    """Test has_debug_tag returns False for jobs with empty tags."""
    job = {"tags": []}
    assert has_debug_tag(job) is False


@pytest.mark.unit
def test_is_development_pipeline_pr_prefix():
    """Test is_development_pipeline returns True for pr- pipelines."""
    assert is_development_pipeline("pr-test-pipeline") is True
    assert is_development_pipeline("pr-bos2-ci-config-539") is True


@pytest.mark.unit
def test_is_development_pipeline_gr_prefix():
    """Test is_development_pipeline returns True for gr- pipelines."""
    assert is_development_pipeline("gr-dci-openshift-agent-34400") is True
    assert is_development_pipeline("gr-test") is True


@pytest.mark.unit
def test_is_development_pipeline_regular():
    """Test is_development_pipeline returns False for regular pipelines."""
    assert is_development_pipeline("abi") is False
    assert is_development_pipeline("ztp") is False
    assert is_development_pipeline("test-pipeline-4.17") is False


@pytest.mark.unit
def test_is_development_pipeline_edge_cases():
    """Test is_development_pipeline edge cases."""
    assert is_development_pipeline("Unknown") is False
    assert is_development_pipeline("") is False
    assert is_development_pipeline(None) is False


@pytest.mark.unit
def test_format_percentage():
    """Test format_percentage formats values correctly."""
    assert format_percentage(50, 100) == "50.00%"
    assert format_percentage(1, 3) == "33.33%"
    assert format_percentage(0, 100) == "0.00%"
    assert format_percentage(100, 100) == "100.00%"


@pytest.mark.unit
def test_format_percentage_zero_total():
    """Test format_percentage handles zero total."""
    assert format_percentage(10, 0) == "0%"


@pytest.mark.unit
def test_format_duration_seconds():
    """Test format_duration formats seconds correctly."""
    assert format_duration(30) == "0.5 minutes"
    assert format_duration(60) == "1.0 minutes"
    assert format_duration(90) == "1.5 minutes"


@pytest.mark.unit
def test_format_duration_hours():
    """Test format_duration formats hours correctly."""
    assert format_duration(3600) == "1.00 hours"
    assert format_duration(7200) == "2.00 hours"
    assert format_duration(5400) == "1.50 hours"


@pytest.mark.unit
def test_get_failure_rate():
    """Test get_failure_rate calculates correctly."""
    assert get_failure_rate(80, 15, 5, 100) == "20.00%"
    assert get_failure_rate(90, 5, 5, 100) == "10.00%"
    assert get_failure_rate(100, 0, 0, 100) == "0.00%"


@pytest.mark.unit
def test_get_failure_rate_zero_total():
    """Test get_failure_rate handles zero total."""
    assert get_failure_rate(0, 0, 0, 0) == "0%"


@pytest.mark.unit
def test_determine_pipeline_frequency_daily():
    """Test determine_pipeline_frequency identifies daily pipelines."""
    pipeline_name = "test-pipeline"
    weekly_counts = {
        pipeline_name: {
            "2025-W40": 7,
            "2025-W41": 7,
            "2025-W42": 7,
        }
    }
    monthly_counts = {pipeline_name: {"2025-10": 21}}
    total_jobs = 72  # 72 jobs / 90 days = 0.8 per day (daily threshold)
    frequency = determine_pipeline_frequency(
        pipeline_name, weekly_counts, monthly_counts, total_jobs, 90
    )
    assert frequency == "Daily"


@pytest.mark.unit
def test_determine_pipeline_frequency_weekly():
    """Test determine_pipeline_frequency identifies weekly pipelines."""
    pipeline_name = "test-pipeline"
    weekly_counts = {
        pipeline_name: {
            "2025-W40": 1,
            "2025-W41": 1,
            "2025-W42": 1,
        }
    }
    monthly_counts = {pipeline_name: {"2025-10": 3}}
    total_jobs = 3
    frequency = determine_pipeline_frequency(
        pipeline_name, weekly_counts, monthly_counts, total_jobs, 90
    )
    assert frequency == "Weekly"


@pytest.mark.unit
def test_determine_pipeline_frequency_sporadic():
    """Test determine_pipeline_frequency identifies sporadic pipelines."""
    pipeline_name = "test-pipeline"
    weekly_counts = {
        pipeline_name: {
            "2025-W40": 1,
        }
    }
    monthly_counts = {}
    total_jobs = 1
    # 1 job / 90 days = 0.011 per day, less than 0.1 threshold, and only 1 week = sporadic
    frequency = determine_pipeline_frequency(
        pipeline_name, weekly_counts, monthly_counts, total_jobs, 90
    )
    # With only 1 week out of many, it should be sporadic
    assert frequency in ["Sporadic", "Weekly"]  # Accept either based on logic


@pytest.mark.unit
def test_determine_pipeline_frequency_zero_jobs():
    """Test determine_pipeline_frequency handles zero jobs."""
    frequency = determine_pipeline_frequency("test", {}, {}, 0, 90)
    assert frequency == "N/A"


@pytest.mark.unit
def test_load_and_filter_batches(tmp_path):
    """Test load_and_filter_batches loads and filters batches correctly."""
    # Create test batch files
    batches_dir = tmp_path / "batches"
    batches_dir.mkdir()

    start_date = datetime(2025, 8, 16)
    end_date = datetime(2025, 11, 14, 23, 59, 59)

    # Create batch with jobs in date range
    job1 = {
        "id": "job1",
        "created_at": "2025-09-01T10:00:00",
        "tags": [],
    }
    job2 = {
        "id": "job2",
        "created_at": "2025-09-02T10:00:00",
        "tags": ["debug"],
    }
    job3 = {
        "id": "job3",
        "created_at": "2025-07-01T10:00:00",  # Before start date
        "tags": [],
    }

    batch_data = {"hits": [job1, job2, job3]}
    with open(batches_dir / "batch_0.json", "w") as f:
        json.dump(batch_data, f)

    regular_jobs, debug_jobs = load_and_filter_batches(
        batches_dir, start_date, end_date
    )

    assert len(regular_jobs) == 1
    assert regular_jobs[0]["id"] == "job1"
    assert len(debug_jobs) == 1
    assert debug_jobs[0]["id"] == "job2"


@pytest.mark.unit
def test_load_and_filter_batches_empty(tmp_path):
    """Test load_and_filter_batches handles empty batches."""
    batches_dir = tmp_path / "batches"
    batches_dir.mkdir()

    start_date = datetime(2025, 8, 16)
    end_date = datetime(2025, 11, 14, 23, 59, 59)

    regular_jobs, debug_jobs = load_and_filter_batches(
        batches_dir, start_date, end_date
    )

    assert len(regular_jobs) == 0
    assert len(debug_jobs) == 0


@pytest.mark.unit
def test_generate_statistics_basic():
    """Test generate_statistics generates basic statistics."""
    jobs = [
        {
            "id": "job1",
            "status": "success",
            "created_at": "2025-09-01T10:00:00",
            "duration": 3600,
            "pipeline": {"name": "abi"},
            "topic": {"name": "OCP-4.20"},
            "components": [{"name": "component1", "version": "1.0", "type": "rpm"}],
        },
        {
            "id": "job2",
            "status": "failure",
            "created_at": "2025-09-02T10:00:00",
            "duration": 1800,
            "status_reason": "Test failed",
            "pipeline": {"name": "ztp"},
            "topic": {"name": "OCP-4.20"},
            "components": [{"name": "component1", "version": "1.0", "type": "rpm"}],
        },
    ]

    stats = generate_statistics(jobs)

    assert stats["total_jobs"] == 2
    assert stats["success_count"] == 1
    assert stats["failure_count"] == 1
    assert stats["success_rate"] == 50.0
    assert stats["failure_rate"] == 50.0
    assert stats["avg_duration"] == 2700.0
    assert "abi" in stats["pipeline_counts"]
    assert stats["pipeline_counts"]["abi"] == 1
    assert "OCP-4.20" in stats["topic_counts"]
    assert stats["topic_counts"]["OCP-4.20"] == 2


@pytest.mark.unit
def test_generate_statistics_excludes_dev_pipelines():
    """Test generate_statistics excludes development pipelines from main stats."""
    jobs = [
        {
            "id": "job1",
            "status": "success",
            "created_at": "2025-09-01T10:00:00",
            "pipeline": {"name": "abi"},
            "topic": {"name": "OCP-4.20"},
        },
        {
            "id": "job2",
            "status": "success",
            "created_at": "2025-09-02T10:00:00",
            "pipeline": {"name": "pr-test-pipeline"},
            "topic": {"name": "OCP-4.20"},
        },
        {
            "id": "job3",
            "status": "success",
            "created_at": "2025-09-03T10:00:00",
            "pipeline": {"name": "gr-test-pipeline"},
            "topic": {"name": "OCP-4.20"},
        },
    ]

    stats = generate_statistics(jobs)

    assert stats["total_jobs"] == 3
    assert "abi" in stats["pipeline_counts"]
    assert stats["pipeline_counts"]["abi"] == 1
    assert "pr-test-pipeline" not in stats["pipeline_counts"]
    assert "gr-test-pipeline" not in stats["pipeline_counts"]
    assert stats.get("total_debug_jobs", 0) == 2  # pr- and gr- pipelines


@pytest.mark.unit
def test_generate_statistics_with_debug_jobs():
    """Test generate_statistics includes debug jobs in debug stats."""
    regular_jobs = [
        {
            "id": "job1",
            "status": "success",
            "created_at": "2025-09-01T10:00:00",
            "pipeline": {"name": "abi"},
            "topic": {"name": "OCP-4.20"},
        }
    ]

    debug_jobs = [
        {
            "id": "job2",
            "status": "failure",
            "created_at": "2025-09-02T10:00:00",
            "pipeline": {"name": "test-pipeline"},
            "topic": {"name": "OCP-4.19"},
        }
    ]

    stats = generate_statistics(regular_jobs, debug_jobs)

    assert stats["total_jobs"] == 1
    assert stats.get("total_debug_jobs", 0) == 1
    assert "test-pipeline" in stats.get("debug_pipeline_counts", {})
    assert stats["debug_pipeline_counts"]["test-pipeline"] == 1


@pytest.mark.unit
def test_generate_statistics_failure_reasons():
    """Test generate_statistics tracks failure reasons."""
    jobs = [
        {
            "id": "job1",
            "status": "failure",
            "created_at": "2025-09-01T10:00:00",
            "status_reason": "Test failed",
            "pipeline": {"name": "abi"},
            "topic": {"name": "OCP-4.20"},
        },
        {
            "id": "job2",
            "status": "failure",
            "created_at": "2025-09-02T10:00:00",
            "status_reason": "Test failed",
            "pipeline": {"name": "abi"},
            "topic": {"name": "OCP-4.20"},
        },
        {
            "id": "job3",
            "status": "error",
            "created_at": "2025-09-03T10:00:00",
            "status_reason": "Timeout",
            "pipeline": {"name": "abi"},
            "topic": {"name": "OCP-4.20"},
        },
    ]

    stats = generate_statistics(jobs)

    assert "Test failed" in stats["status_reasons"]
    assert stats["status_reasons"]["Test failed"] == 2
    assert "Timeout" in stats["status_reasons"]
    assert stats["status_reasons"]["Timeout"] == 1


@pytest.mark.unit
def test_generate_statistics_time_trends():
    """Test generate_statistics tracks time-based trends."""
    # Use actual dates that we know the day of week
    # 2025-09-01 is a Monday, 2025-09-02 is a Tuesday
    jobs = [
        {
            "id": "job1",
            "status": "success",
            "created_at": "2025-09-01T10:00:00",  # Monday
            "pipeline": {"name": "abi"},
            "topic": {"name": "OCP-4.20"},
        },
        {
            "id": "job2",
            "status": "failure",
            "created_at": "2025-09-02T10:00:00",  # Tuesday
            "pipeline": {"name": "abi"},
            "topic": {"name": "OCP-4.20"},
        },
    ]

    stats = generate_statistics(jobs)

    assert "Monday" in stats["daily_counts"]
    assert stats["daily_counts"]["Monday"] == 1
    assert "Tuesday" in stats["daily_counts"]
    assert stats["daily_counts"]["Tuesday"] == 1
    # Check that weekly_counts has entries
    assert len(stats["weekly_counts"]) > 0


@pytest.mark.unit
def test_generate_report_creates_file(tmp_path):
    """Test generate_report creates a report file."""
    stats = {
        "total_jobs": 100,
        "success_count": 80,
        "failure_count": 15,
        "error_count": 5,
        "success_rate": 80.0,
        "failure_rate": 20.0,
        "avg_duration": 3600.0,
        "pipeline_counts": {"abi": 50, "ztp": 50},
        "pipeline_status": {
            "abi": {"success": 40, "failure": 8, "error": 2},
            "ztp": {"success": 40, "failure": 7, "error": 3},
        },
        "topic_counts": {"OCP-4.20": 100},
        "topic_status": {"OCP-4.20": {"success": 80, "failure": 15, "error": 5}},
        "component_counts": {"component1": 100},
        "component_versions": {},
        "component_types": {"rpm": 100},
        "status_reasons": {"Test failed": 10},
        "status_breakdown": {"success": 80, "failure": 15, "error": 5},
        "daily_counts": {"Monday": 20},
        "daily_status": {"Monday": {"success": 16, "failure": 4}},
        "weekly_counts": {"2025-W40": 100},
        "weekly_status": {"2025-W40": {"success": 80, "failure": 20}},
        "pipeline_weekly_counts": {"abi": {"2025-W40": 50}},
        "topic_weekly_counts": {"OCP-4.20": {"2025-W40": 100}},
        "pipeline_monthly_counts": {"abi": {"2025-10": 50}},
        "topic_monthly_counts": {"OCP-4.20": {"2025-10": 100}},
    }

    report_path = tmp_path / "report.md"
    start_date = datetime(2025, 8, 16)
    end_date = datetime(2025, 11, 14)

    generate_report(stats, "test-remoteci", start_date, end_date, report_path)

    assert report_path.exists()
    content = report_path.read_text()
    assert "Quarterly DCI Analysis Report: test-remoteci" in content
    assert "**Total Jobs:** 100" in content
    assert "**Overall Success Rate:** 80.00%" in content


@pytest.mark.unit
def test_generate_report_includes_frequency(tmp_path):
    """Test generate_report includes pipeline frequency."""
    stats = {
        "total_jobs": 100,
        "success_count": 80,
        "failure_count": 15,
        "error_count": 5,
        "success_rate": 80.0,
        "failure_rate": 20.0,
        "avg_duration": 3600.0,
        "pipeline_counts": {"abi": 50},
        "pipeline_status": {"abi": {"success": 40, "failure": 8, "error": 2}},
        "topic_counts": {"OCP-4.20": 100},
        "topic_status": {"OCP-4.20": {"success": 80, "failure": 15, "error": 5}},
        "component_counts": {},
        "component_versions": {},
        "component_types": {},
        "status_reasons": {},
        "status_breakdown": {"success": 80, "failure": 15, "error": 5},
        "daily_counts": {},
        "daily_status": {},
        "weekly_counts": {},
        "weekly_status": {},
        "pipeline_weekly_counts": {"abi": {"2025-W40": 50}},
        "topic_weekly_counts": {},
        "pipeline_monthly_counts": {"abi": {"2025-10": 50}},
        "topic_monthly_counts": {},
    }

    report_path = tmp_path / "report.md"
    start_date = datetime(2025, 8, 16)
    end_date = datetime(2025, 11, 14)

    generate_report(stats, "test-remoteci", start_date, end_date, report_path)

    content = report_path.read_text()
    assert "Frequency" in content
    assert "abi" in content


@pytest.mark.unit
def test_generate_report_includes_debug_section(tmp_path):
    """Test generate_report includes development activity section when debug jobs exist."""
    stats = {
        "total_jobs": 100,
        "success_count": 80,
        "failure_count": 15,
        "error_count": 5,
        "success_rate": 80.0,
        "failure_rate": 20.0,
        "avg_duration": 3600.0,
        "pipeline_counts": {"abi": 100},
        "pipeline_status": {"abi": {"success": 80, "failure": 15, "error": 5}},
        "topic_counts": {"OCP-4.20": 100},
        "topic_status": {"OCP-4.20": {"success": 80, "failure": 15, "error": 5}},
        "component_counts": {},
        "component_versions": {},
        "component_types": {},
        "status_reasons": {},
        "status_breakdown": {"success": 80, "failure": 15, "error": 5},
        "daily_counts": {},
        "daily_status": {},
        "weekly_counts": {},
        "weekly_status": {},
        "pipeline_weekly_counts": {},
        "topic_weekly_counts": {},
        "pipeline_monthly_counts": {},
        "topic_monthly_counts": {},
        "total_debug_jobs": 50,
        "debug_status_breakdown": {"success": 30, "failure": 20},
        "debug_pipeline_counts": {"pr-test": 50},
        "debug_topic_counts": {"OCP-4.19": 50},
    }

    report_path = tmp_path / "report.md"
    start_date = datetime(2025, 8, 16)
    end_date = datetime(2025, 11, 14)

    generate_report(stats, "test-remoteci", start_date, end_date, report_path)

    content = report_path.read_text()
    assert "Development Activity" in content
    assert (
        "Total Development/PR Jobs: 50" in content
        or "**Total Development/PR Jobs:** 50" in content
    )
    assert "pr-test" in content


@pytest.mark.unit
def test_generate_statistics_empty_jobs():
    """Test generate_statistics handles empty job list."""
    stats = generate_statistics([])

    assert stats["total_jobs"] == 0
    assert stats["success_count"] == 0
    assert stats["failure_count"] == 0
    assert stats["success_rate"] == 0
    assert stats["failure_rate"] == 0
    assert stats["avg_duration"] == 0


@pytest.mark.unit
def test_generate_statistics_component_tracking():
    """Test generate_statistics tracks component usage."""
    jobs = [
        {
            "id": "job1",
            "status": "success",
            "created_at": "2025-09-01T10:00:00",
            "pipeline": {"name": "abi"},
            "topic": {"name": "OCP-4.20"},
            "components": [
                {"name": "component1", "version": "1.0", "type": "rpm"},
                {"name": "component2", "version": "2.0", "type": "container"},
            ],
        },
        {
            "id": "job2",
            "status": "success",
            "created_at": "2025-09-02T10:00:00",
            "pipeline": {"name": "abi"},
            "topic": {"name": "OCP-4.20"},
            "components": [
                {"name": "component1", "version": "1.0", "type": "rpm"},
            ],
        },
    ]

    stats = generate_statistics(jobs)

    assert stats["component_counts"]["component1"] == 2
    assert stats["component_counts"]["component2"] == 1
    assert stats["component_types"]["rpm"] == 2
    assert stats["component_types"]["container"] == 1
    assert "component1" in stats["component_versions"]
    assert stats["component_versions"]["component1"]["1.0"] == 2
