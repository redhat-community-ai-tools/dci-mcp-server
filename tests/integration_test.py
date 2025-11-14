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
Integration tests. They need a valid .env at the root of the
project with credentials to access the DCI CS.
"""

import datetime
import json
import os
import tempfile

import pytest
from fastmcp import Client

from mcp_server.config import validate_required_config
from mcp_server.main import create_server


@pytest.fixture
def mcp_server():
    server = create_server()
    return server


def parse_response(result):
    """Helper function to parse MCP tool response."""
    if result.content and len(result.content) > 0:
        content_text = result.content[0].text
        return json.loads(content_text)
    else:
        pytest.fail("No content returned from tool")


def test_config():
    """Test configuration validation."""
    assert validate_required_config()


async def test_date(mcp_server):
    """Test date-related tools."""
    async with Client(mcp_server) as client:
        # Test today tool
        result = await client.call_tool("today", {})
        assert not result.is_error

        data = parse_response(result)
        assert "today" in data and data["today"] == datetime.date.today().strftime(
            "%Y-%m-%d"
        )

        # Test now tool
        result = await client.call_tool("now", {})
        assert not result.is_error

        data = parse_response(result)
        assert (
            "now" in data and len(data["now"]) == 26
        )  # Length of "2025-09-12T21:47:02.908617"


@pytest.mark.integration
async def test_job_search(mcp_server):
    """Test job-related tools."""
    async with Client(mcp_server) as client:
        # Test search_dci_jobs with a simple filter
        result = await client.call_tool(
            "search_dci_jobs",
            {
                "query": "(components.type='ocp')",
                "fields": ["id"],
                "limit": 1,
            },
        )
        assert not result.is_error

        data = parse_response(result)
        # The response should have hits
        assert "hits" in data
        assert len(data["hits"]) > 0
        # Check that the first hit has an id
        first_hit = data["hits"][0]
        assert first_hit  # Should not be empty
        assert "id" in first_hit


@pytest.mark.integration
async def test_job_tools(mcp_server):
    """Test job-related tools."""
    async with Client(mcp_server) as client:
        # Test search_dci_jobs with a simple filter
        result = await client.call_tool(
            "search_dci_jobs",
            {"query": "tags in ['daily']", "fields": ["team_id"], "limit": 5},
        )
        assert not result.is_error

        data = parse_response(result)
        # The response should have hits
        assert "hits" in data
        assert len(data["hits"]) >= 0  # Can be empty but should be an array
        # Verify each hit has only team_id field
        for job in data["hits"]:
            assert job.keys() == {"team_id"}


@pytest.mark.integration
async def test_fields_parameter_issue(mcp_server):
    """Test the fields parameter type validation issue.

    This test documents the known limitation where the MCP framework
    converts array parameters to strings during transmission, causing
    validation errors for union types like list[str] | None.
    """
    async with Client(mcp_server) as client:
        # Test 1: Query with fields as array
        result = await client.call_tool(
            "search_dci_jobs",
            {"query": "status='success'", "limit": 10, "fields": ["status"]},
        )
        data = parse_response(result)
        # The response should have hits
        assert "hits" in data
        # validate there are only status fields in jobs dictionaries
        assert all(job.keys() == {"status"} for job in data["hits"])

        # Test 2: Query with fields as empty array
        result = await client.call_tool(
            "search_dci_jobs",
            {"query": "status='success'", "limit": 10, "fields": []},
        )
        assert not result.is_error
        data = parse_response(result)
        # The response should have hits
        assert "hits" in data
        assert len(data["hits"]) == 0


@pytest.mark.integration
async def test_component_tools(mcp_server):
    """Test component-related tools."""
    async with Client(mcp_server) as client:
        # Test query_dci_components
        result = await client.call_tool(
            "query_dci_components", {"query": "like(name,%)"}
        )
        assert not result.is_error

        data = parse_response(result)
        assert "components" in data

        # Test query_dci_components with a specific component query
        result = await client.call_tool(
            "query_dci_components", {"query": "eq(id,dummy-id)"}
        )
        assert not result.is_error

        data = parse_response(result)
        # Should return empty results
        assert "components" in data


@pytest.mark.integration
async def test_file_download_tools(mcp_server):
    """Test file download tools."""
    async with Client(mcp_server) as client:
        # Test download_dci_file with dummy data (should return error but not crash)
        temp_file = tempfile.mkstemp()[1]
        result = await client.call_tool(
            "download_dci_file",
            {
                "job_id": "dummy-job-id",
                "file_id": "dummy-file-id",
                "output_path": temp_file,
            },
        )
        # This should return an error since the job/file don't exist, but not crash
        data = parse_response(result)
        assert "error" in data  # Should return an error for non-existent job/file

        # Clean up temp file
        if os.path.exists(temp_file):
            os.unlink(temp_file)


@pytest.mark.integration
async def test_daily_jobs_search_syntax(mcp_server):
    """Test daily jobs using proper search syntax for search_dci_jobs."""
    async with Client(mcp_server) as client:
        fields = [
            "id",
            "name",
            "status",
            "created_at",
            "tags",
            "components.type",
            "components.version",
            "components.name",
        ]
        # Test using proper search syntax (not query syntax)
        result = await client.call_tool(
            "search_dci_jobs",
            {
                "query": "((components.type='ocp') and (tags in ['daily']))",
                "sort": "-created_at",
                "limit": 10,
                "fields": fields,
            },
        )
        assert not result.is_error

        data = parse_response(result)
        assert "hits" in data
        assert len(data["hits"]) > 0, (
            f"Expected to find jobs, but got {len(data['hits'])} hits"
        )

        # Check that we get actual job data, not empty dictionaries
        for hit in data["hits"]:
            assert hit, (
                "Field filtering should return actual job data, not empty dictionaries"
            )
            fields_keys = {field.split(".")[0] for field in fields}
            assert hit.keys() == fields_keys, (
                f"Expected fields {fields_keys}, got {hit.keys()}"
            )
            # Data should contain the requested fields
            for field in fields_keys:
                assert field in hit, f"Expected field '{field}' in job data"
                assert hit[field], f"Field '{field}' should not be None or empty"
            # Verify components is a list of dicts with type, version, name
            assert isinstance(hit["components"], list)
            for comp in hit["components"]:
                assert isinstance(comp, dict)
                assert "type" in comp and comp["type"]
                assert "version" in comp and comp["version"]
                assert "name" in comp and comp["name"]


@pytest.mark.integration
async def test_error_handling(mcp_server):
    """Test error handling for invalid tool calls."""
    async with Client(mcp_server) as client:
        # Test calling a tool with a query that might return an error
        result = await client.call_tool(
            "search_dci_jobs", {"query": "invalid_syntax_query", "limit": 1}
        )
        # This should return an error for invalid syntax
        assert not result.is_error  # The tool should handle the error gracefully

        data = parse_response(result)
        # Should return an error message for invalid syntax
        assert "error" in data


@pytest.mark.integration
async def test_no_result(mcp_server):
    """Test no result job tool calls."""
    async with Client(mcp_server) as client:
        # Test calling a tool with a query that might return an error
        result = await client.call_tool(
            "search_dci_jobs",
            {"query": "(created_at>='2100-01-01')", "limit": 1},
        )
        # This should return an error for invalid syntax
        assert not result.is_error  # The tool should handle the error gracefully

        data = parse_response(result)
        # Should return no error and an empty hits array
        assert "error" not in data and "hits" in data and len(data["hits"]) == 0
