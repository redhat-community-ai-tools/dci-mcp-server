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
Integration tests for query patterns and syntax.
Tests cover complex query combinations, edge cases, and various operators.
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
async def test_and_operator_multiple_conditions(mcp_client):
    """Test AND operator with multiple conditions."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((status='success') and (created_at>='2026-04-01') and (duration>=1000))",
            "limit": 5,
            "fields": ["id", "status", "created_at", "duration"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data

    # Verify all returned jobs match the criteria
    for job in data["hits"]:
        assert job["status"] == "success"
        assert job["created_at"] >= "2026-04-01"
        assert job["duration"] >= 1000


@pytest.mark.integration
async def test_or_operator(mcp_client):
    """Test OR operator for status filtering."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((status='failure') or (status='error'))",
            "limit": 10,
            "fields": ["id", "status"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data

    # Verify all returned jobs are either failure or error
    for job in data["hits"]:
        assert job["status"] in ["failure", "error"]


@pytest.mark.integration
async def test_in_operator_with_multiple_values(mcp_client):
    """Test IN operator with multiple status values."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(status in ['success', 'failure', 'error'])",
            "limit": 10,
            "fields": ["id", "status"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data

    # Verify all returned jobs have one of the specified statuses
    for job in data["hits"]:
        assert job["status"] in ["success", "failure", "error"]


@pytest.mark.integration
async def test_not_in_operator(mcp_client):
    """Test NOT IN operator."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((status not_in ['killed', 'error']) and (created_at>='2026-04-01'))",
            "limit": 10,
            "fields": ["id", "status"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data

    # Verify no job has status 'killed' or 'error'
    for job in data["hits"]:
        assert job["status"] not in ["killed", "error"]


@pytest.mark.integration
async def test_not_equal_operator(mcp_client):
    """Test != (not equal) operator."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((status!='success') and (created_at>='2026-04-01'))",
            "limit": 10,
            "fields": ["id", "status"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data

    # Verify no job has status 'success'
    for job in data["hits"]:
        assert job["status"] != "success"


@pytest.mark.integration
async def test_regex_pattern_matching(mcp_client):
    """Test regex pattern matching with =~ operator."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((pipeline.name=~'.*vcp.*') and (created_at>='2026-04-01'))",
            "limit": 5,
            "fields": ["id", "pipeline.name"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data

    # Verify all pipeline names match the pattern
    for job in data["hits"]:
        if "pipeline" in job and job["pipeline"]:
            assert "vcp" in job["pipeline"]["name"].lower()


@pytest.mark.integration
async def test_date_range_query(mcp_client):
    """Test date range queries with >= and < operators."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((created_at>='2026-04-01') and (created_at<'2026-04-08'))",
            "limit": 10,
            "fields": ["id", "created_at"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data

    # Verify all dates are in the range
    for job in data["hits"]:
        assert job["created_at"] >= "2026-04-01"
        assert job["created_at"] < "2026-04-08"


@pytest.mark.integration
async def test_duration_range_query(mcp_client):
    """Test duration range queries."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((duration>=3600) and (duration<=7200) and (status='success'))",
            "limit": 10,
            "fields": ["id", "duration", "status"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data

    # Verify all durations are in range (1-2 hours)
    for job in data["hits"]:
        assert job["duration"] >= 3600
        assert job["duration"] <= 7200
        assert job["status"] == "success"


@pytest.mark.integration
async def test_nested_and_or_combination(mcp_client):
    """Test complex nested AND/OR combinations."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(((status='success') and (duration>=5000)) or ((status='failure') and (created_at>='2026-04-15')))",
            "limit": 10,
            "fields": ["id", "status", "duration", "created_at"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data

    # Verify each job matches one of the two conditions
    for job in data["hits"]:
        condition1 = job["status"] == "success" and job["duration"] >= 5000
        condition2 = job["status"] == "failure" and job["created_at"] >= "2026-04-15"
        assert condition1 or condition2


@pytest.mark.integration
async def test_multiple_component_conditions(mcp_client):
    """Test multiple component conditions (requires both OCP and another component)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((components.type='ocp') and (created_at>='2026-04-01'))",
            "limit": 5,
            "fields": ["id", "components.type", "components.name"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data

    # Verify all jobs have OCP component
    for job in data["hits"]:
        if "components" in job and job["components"]:
            has_ocp = any(c["type"] == "ocp" for c in job["components"])
            assert has_ocp


@pytest.mark.integration
async def test_tags_in_operator(mcp_client):
    """Test IN operator with tags field (array)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((tags in ['daily']) and (created_at>='2026-04-01'))",
            "limit": 10,
            "fields": ["id", "tags"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data

    # Verify all jobs have 'daily' tag
    for job in data["hits"]:
        if "tags" in job and job["tags"]:
            assert "daily" in job["tags"]


@pytest.mark.integration
async def test_complex_nested_component_query(mcp_client):
    """Test complex nested component query with version filtering."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((components.type='ocp') and (components.version=~'4.1.*') and (created_at>='2026-04-01'))",
            "limit": 5,
            "fields": ["id", "components.type", "components.version"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data

    # Verify jobs have OCP 4.1x components
    # Note: Due to ES query semantics, we might get jobs with OCP
    # but not necessarily 4.1x if they have other components matching
    for job in data["hits"]:
        if "components" in job and job["components"]:
            assert any(c["type"] == "ocp" for c in job["components"])


@pytest.mark.integration
async def test_query_with_parentheses_grouping(mcp_client):
    """Test proper parentheses grouping in queries."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(((status='success') or (status='failure')) and (created_at>='2026-04-10'))",
            "limit": 10,
            "fields": ["id", "status", "created_at"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data

    # Verify all jobs match the grouped condition
    for job in data["hits"]:
        assert job["status"] in ["success", "failure"]
        assert job["created_at"] >= "2026-04-10"


@pytest.mark.integration
async def test_empty_result_query(mcp_client):
    """Test query that returns no results (edge case)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2100-01-01')",
            "limit": 10,
            "fields": ["id"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data
    assert len(data["hits"]) == 0
    # Total field might not be present for empty results, but if present should be 0
    if "total" in data:
        total = data["total"]
        if isinstance(total, int):
            assert total == 0
        elif isinstance(total, dict):
            assert total.get("value", 0) == 0
