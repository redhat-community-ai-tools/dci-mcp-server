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
Integration tests for pagination functionality.
Tests cover: limit, offset, total count, and edge cases.
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


def get_total_count(data):
    """Extract total count from response, handling both int and dict formats."""
    total = data.get("total")
    if isinstance(total, int):
        return total
    elif isinstance(total, dict):
        return total.get("value", 0)
    return 0


@pytest.mark.integration
async def test_basic_pagination_first_page(mcp_client):
    """Test basic pagination - first page."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 5,
            "offset": 0,
            "fields": ["id", "created_at"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data
    assert "total" in data
    assert len(data["hits"]) <= 5


@pytest.mark.integration
async def test_pagination_second_page(mcp_client):
    """Test pagination - second page with offset."""
    # Get first page
    result1 = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 5,
            "offset": 0,
            "fields": ["id"],
            "sort": "-created_at",
        },
    )
    assert not result1.is_error
    data1 = parse_response(result1)

    # Get second page
    result2 = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 5,
            "offset": 5,
            "fields": ["id"],
            "sort": "-created_at",
        },
    )
    assert not result2.is_error
    data2 = parse_response(result2)

    # Ensure pages don't overlap
    ids_page1 = {job["id"] for job in data1["hits"]}
    ids_page2 = {job["id"] for job in data2["hits"]}
    assert len(ids_page1.intersection(ids_page2)) == 0


@pytest.mark.integration
async def test_pagination_total_count_consistency(mcp_client):
    """Test that total count is consistent across pages."""
    # Get first page
    result1 = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 10,
            "offset": 0,
            "fields": ["id"],
        },
    )
    assert not result1.is_error
    data1 = parse_response(result1)
    total1 = get_total_count(data1)

    # Get second page
    result2 = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 10,
            "offset": 10,
            "fields": ["id"],
        },
    )
    assert not result2.is_error
    data2 = parse_response(result2)
    total2 = get_total_count(data2)

    # Total should be the same
    assert total1 == total2


@pytest.mark.integration
async def test_offset_beyond_total(mcp_client):
    """Test offset beyond total results returns empty hits."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 10,
            "offset": 100000,  # Very large offset
            "fields": ["id"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data
    # Should return empty hits when offset > total
    assert len(data["hits"]) == 0


@pytest.mark.integration
async def test_max_limit_value(mcp_client):
    """Test maximum limit value (200)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 200,  # Max limit
            "offset": 0,
            "fields": ["id"],
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data
    assert len(data["hits"]) <= 200


@pytest.mark.integration
async def test_sort_consistency_across_pages(mcp_client):
    """Test that sort order is consistent across pages."""
    # Get first page with descending created_at
    result1 = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 5,
            "offset": 0,
            "fields": ["id", "created_at"],
            "sort": "-created_at",
        },
    )
    assert not result1.is_error
    data1 = parse_response(result1)

    # Get second page
    result2 = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 5,
            "offset": 5,
            "fields": ["id", "created_at"],
            "sort": "-created_at",
        },
    )
    assert not result2.is_error
    data2 = parse_response(result2)

    # Ensure second page dates are earlier than or equal to first page
    if len(data1["hits"]) > 0 and len(data2["hits"]) > 0:
        last_date_page1 = data1["hits"][-1]["created_at"]
        first_date_page2 = data2["hits"][0]["created_at"]
        # Second page should have earlier or equal dates (descending order)
        assert first_date_page2 <= last_date_page1


@pytest.mark.integration
async def test_pagination_with_aggregations(mcp_client):
    """Test that aggregations work correctly with pagination."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 5,
            "offset": 10,
            "aggs": {
                "aggs": {
                    "by_status": {"terms": {"field": "status", "size": 10}},
                    "total_count": {"value_count": {"field": "id"}},
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "hits" in data
    assert "aggregations" in data

    # Aggregations should reflect total dataset, not just the page
    aggs = data["aggregations"]
    assert "by_status" in aggs
    assert "total_count" in aggs

    # Total count in aggregation should be >= hits count
    total_in_agg = aggs["total_count"]["value"]
    hits_count = len(data["hits"])
    assert total_in_agg >= hits_count
