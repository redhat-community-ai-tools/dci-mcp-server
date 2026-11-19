#
# Copyright (C) 2026 Red Hat, Inc.
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

"""What an agent is told when a DCI call fails: enough to tell the causes apart."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import Client

from mcp_server.services.dci_base_service import DCIBaseService


def _response(status, text, json_value=None):
    response = MagicMock()
    response.status_code = status
    response.text = text
    response.json.side_effect = (
        (lambda: json_value)
        if json_value is not None
        else ValueError("Expecting value: line 1 column 1 (char 0)")
    )
    return response


@pytest.mark.unit
def test_json_body_is_returned_unchanged():
    assert DCIBaseService.decoded(_response(200, '{"a": 1}', {"a": 1})) == {"a": 1}


@pytest.mark.unit
def test_a_non_json_body_names_the_status_and_quotes_the_body():
    """A proxy or gateway error arrives as HTML: 'Expecting value' alone hides which it was."""
    html = "<!doctype html>\n<html>\n<title>502 Bad Gateway</title>\n</html>"
    with pytest.raises(ValueError) as excinfo:
        DCIBaseService.decoded(_response(502, html))
    message = str(excinfo.value)
    assert "502" in message
    assert "Bad Gateway" in message
    assert "\n" not in message


@pytest.mark.unit
def test_a_long_body_is_truncated():
    with pytest.raises(ValueError) as excinfo:
        DCIBaseService.decoded(_response(500, "x" * 5000))
    assert len(str(excinfo.value)) < 400


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setenv("DCI_CLIENT_ID", "remoteci/00000000-0000-0000-0000-000000000000")
    monkeypatch.setenv("DCI_API_SECRET", "test-secret")
    from mcp_server.main import create_server

    return create_server()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_dci_jobs_reports_the_cause_not_only_the_summary(server):
    """The tool used to drop the service's 'error' key, leaving 'Failed to list jobs.' alone."""
    cause = "HTTP 502, body is not JSON: <title>502 Bad Gateway</title>"
    with patch("mcp_server.tools.job_tools.DCIJobService") as service:
        service.return_value.search_jobs.return_value = {
            "error": cause,
            "message": "Failed to list jobs.",
        }
        async with Client(server) as client:
            result = await client.call_tool(
                "search_dci_jobs", {"query": "(status='failure')"}
            )

    reported = json.dumps(json.loads(result.content[0].text))
    assert "Failed to list jobs." in reported
    assert "502" in reported and "Bad Gateway" in reported
