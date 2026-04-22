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

"""
Integration tests for simple field aggregations (non-nested fields).
Tests cover: status, tags, created_at, duration, team_id, remoteci_id, etc.
"""

import json

import pytest
from fastmcp import Client

from mcp_server.main import create_server


@pytest.fixture(scope="module")
def mcp_server():
    server = create_server()
    return server


@pytest.fixture(scope="module")
async def mcp_client(mcp_server):
    async with Client(mcp_server) as client:
        yield client


def parse_response(result):
    """Helper function to parse MCP tool response."""
    if result.content and len(result.content) > 0:
        content_text = result.content[0].text
        return json.loads(content_text)
    else:
        pytest.fail("No content returned from tool")


@pytest.mark.integration
async def test_status_aggregation(mcp_client):
    """Test aggregation by status field (keyword)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {"by_status": {"terms": {"field": "status", "size": 10}}},
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "by_status" in data["aggregations"]
    assert "buckets" in data["aggregations"]["by_status"]

    # Should have at least success and failure buckets
    buckets = data["aggregations"]["by_status"]["buckets"]
    assert len(buckets) > 0

    # Each bucket should have key and doc_count
    for bucket in buckets:
        assert "key" in bucket
        assert "doc_count" in bucket
        assert bucket["doc_count"] > 0
        # Status should be a non-empty string (DCI has various statuses)
        # Known statuses: success, failure, error, killed, running, new, pre-run, post-run
        assert isinstance(bucket["key"], str)
        assert len(bucket["key"]) > 0


@pytest.mark.integration
async def test_duration_stats_aggregation(mcp_client):
    """Test statistics aggregation on duration field (long)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((status='success') and (created_at>='2026-01-01'))",
            "limit": 1,
            "aggs": {"duration_stats": {"stats": {"field": "duration"}}},
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "duration_stats" in data["aggregations"]

    stats = data["aggregations"]["duration_stats"]
    # Stats should include: count, min, max, avg, sum
    assert "count" in stats and stats["count"] > 0
    assert "min" in stats and stats["min"] >= 0
    assert "max" in stats and stats["max"] >= stats["min"]
    assert "avg" in stats and stats["avg"] >= 0
    assert "sum" in stats and stats["sum"] >= 0


@pytest.mark.integration
async def test_date_histogram_daily(mcp_client):
    """Test date histogram aggregation with daily interval."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((created_at>='2026-04-01') and (created_at<'2026-04-08'))",
            "limit": 1,
            "aggs": {
                "daily": {
                    "date_histogram": {
                        "field": "created_at",
                        "calendar_interval": "day",
                    }
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "daily" in data["aggregations"]
    assert "buckets" in data["aggregations"]["daily"]

    buckets = data["aggregations"]["daily"]["buckets"]
    # Should have buckets for the date range
    assert len(buckets) > 0

    for bucket in buckets:
        assert "key" in bucket
        assert "doc_count" in bucket
        assert "key_as_string" in bucket
        # key_as_string should be a date string
        assert "2026-04" in bucket["key_as_string"]


@pytest.mark.integration
async def test_date_histogram_weekly(mcp_client):
    """Test date histogram aggregation with weekly interval."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-03-01')",
            "limit": 1,
            "aggs": {
                "weekly": {
                    "date_histogram": {
                        "field": "created_at",
                        "calendar_interval": "week",
                    }
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "weekly" in data["aggregations"]
    assert "buckets" in data["aggregations"]["weekly"]

    buckets = data["aggregations"]["weekly"]["buckets"]
    assert len(buckets) > 0

    for bucket in buckets:
        assert "key" in bucket
        assert "doc_count" in bucket


@pytest.mark.integration
async def test_tags_aggregation(mcp_client):
    """Test aggregation by tags field (keyword array)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {"by_tags": {"terms": {"field": "tags", "size": 20}}},
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "by_tags" in data["aggregations"]
    assert "buckets" in data["aggregations"]["by_tags"]

    buckets = data["aggregations"]["by_tags"]["buckets"]
    # Should have tag buckets (e.g., 'daily', 'build:ga', etc.)
    assert len(buckets) > 0

    for bucket in buckets:
        assert "key" in bucket
        assert "doc_count" in bucket
        assert bucket["doc_count"] > 0


@pytest.mark.integration
async def test_team_id_aggregation(mcp_client):
    """Test aggregation by team_id field (keyword)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {"by_team": {"terms": {"field": "team_id", "size": 20}}},
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "by_team" in data["aggregations"]
    assert "buckets" in data["aggregations"]["by_team"]

    buckets = data["aggregations"]["by_team"]["buckets"]
    assert len(buckets) > 0

    for bucket in buckets:
        assert "key" in bucket
        assert "doc_count" in bucket
        # team_id should be a UUID-like string
        assert len(bucket["key"]) > 0


@pytest.mark.integration
async def test_multi_aggregation_simple_fields(mcp_client):
    """Test multiple aggregations on simple fields simultaneously."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "by_status": {"terms": {"field": "status", "size": 10}},
                "duration_stats": {"stats": {"field": "duration"}},
                "by_tags": {"terms": {"field": "tags", "size": 15}},
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data

    # All three aggregations should be present
    assert "by_status" in data["aggregations"]
    assert "duration_stats" in data["aggregations"]
    assert "by_tags" in data["aggregations"]

    # Verify structure
    assert "buckets" in data["aggregations"]["by_status"]
    assert "count" in data["aggregations"]["duration_stats"]
    assert "buckets" in data["aggregations"]["by_tags"]


@pytest.mark.integration
async def test_sub_aggregation_status_with_duration(mcp_client):
    """Test sub-aggregation: status breakdown with duration stats per status."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "by_status": {
                    "terms": {"field": "status", "size": 10},
                    "aggs": {
                        "avg_duration": {"avg": {"field": "duration"}},
                        "total_count": {"value_count": {"field": "id"}},
                    },
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "by_status" in data["aggregations"]
    assert "buckets" in data["aggregations"]["by_status"]

    buckets = data["aggregations"]["by_status"]["buckets"]
    assert len(buckets) > 0

    # Each bucket should have sub-aggregations
    for bucket in buckets:
        assert "avg_duration" in bucket
        assert "value" in bucket["avg_duration"]
        assert "total_count" in bucket
        assert "value" in bucket["total_count"]
        assert bucket["total_count"]["value"] == bucket["doc_count"]


@pytest.mark.integration
async def test_daily_trend_with_status_breakdown(mcp_client):
    """Test date histogram with status sub-aggregation (daily trend analysis)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((created_at>='2026-04-01') and (created_at<'2026-04-15'))",
            "limit": 1,
            "aggs": {
                "daily": {
                    "date_histogram": {
                        "field": "created_at",
                        "calendar_interval": "day",
                    },
                    "aggs": {
                        "by_status": {"terms": {"field": "status"}},
                        "avg_duration": {"avg": {"field": "duration"}},
                    },
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "daily" in data["aggregations"]
    assert "buckets" in data["aggregations"]["daily"]

    buckets = data["aggregations"]["daily"]["buckets"]
    assert len(buckets) > 0

    # Each day bucket should have status breakdown and avg duration
    for bucket in buckets:
        assert "by_status" in bucket
        assert "buckets" in bucket["by_status"]
        assert "avg_duration" in bucket
        # avg_duration might be null if no jobs that day
        if bucket["doc_count"] > 0:
            assert "value" in bucket["avg_duration"]


@pytest.mark.integration
async def test_filter_aggregation_success_only(mcp_client):
    """Test filter aggregation to get stats only for successful jobs."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "success_only": {
                    "filter": {"term": {"status": "success"}},
                    "aggs": {"duration_stats": {"stats": {"field": "duration"}}},
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "success_only" in data["aggregations"]
    assert "doc_count" in data["aggregations"]["success_only"]
    assert "duration_stats" in data["aggregations"]["success_only"]

    stats = data["aggregations"]["success_only"]["duration_stats"]
    assert "count" in stats
    assert "avg" in stats


@pytest.mark.integration
async def test_percentiles_aggregation(mcp_client):
    """Test percentiles aggregation on duration field."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((status='success') and (created_at>='2026-04-01'))",
            "limit": 1,
            "aggs": {
                "duration_percentiles": {
                    "percentiles": {
                        "field": "duration",
                        "percents": [50, 90, 95, 99],
                    }
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "duration_percentiles" in data["aggregations"]
    assert "values" in data["aggregations"]["duration_percentiles"]

    values = data["aggregations"]["duration_percentiles"]["values"]
    # Should have percentile values
    assert "50.0" in values
    assert "90.0" in values
    assert "95.0" in values
    assert "99.0" in values

    # Verify percentiles are ordered
    assert values["50.0"] <= values["90.0"]
    assert values["90.0"] <= values["95.0"]
    assert values["95.0"] <= values["99.0"]
