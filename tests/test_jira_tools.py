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

"""Unit tests for Jira tools and service."""

from unittest.mock import MagicMock, patch

import pytest

from mcp_server.services.jira_service import JiraService, _simplify_field_value
from mcp_server.tools.jira_tools import validate_ticket_key

# -- _simplify_field_value tests --


def test_simplify_none():
    assert _simplify_field_value(None) is None


def test_simplify_string():
    assert _simplify_field_value("hello") == "hello"


def test_simplify_int():
    assert _simplify_field_value(42) == 42


def test_simplify_float():
    assert _simplify_field_value(3.14) == 3.14


def test_simplify_bool():
    assert _simplify_field_value(True) is True
    assert _simplify_field_value(False) is False


def test_simplify_dict_with_display_name():
    assert (
        _simplify_field_value({"displayName": "Test User", "key": "tuser"})
        == "Test User"
    )


def test_simplify_dict_with_name():
    assert _simplify_field_value({"name": "Sprint 42", "id": 123}) == "Sprint 42"


def test_simplify_dict_with_value():
    assert _simplify_field_value({"value": "High", "id": "1"}) == "High"


def test_simplify_dict_display_name_takes_priority_over_name():
    result = _simplify_field_value(
        {"displayName": "John Smith", "name": "jsmith", "key": "jsmith"}
    )
    assert result == "John Smith"


def test_simplify_list():
    result = _simplify_field_value([{"name": "item1"}, {"name": "item2"}, "plain"])
    assert result == ["item1", "item2", "plain"]


def test_simplify_nested_dict():
    result = _simplify_field_value({"key1": {"name": "val1"}, "key2": "val2"})
    assert result == {"key1": "val1", "key2": "val2"}


def test_simplify_empty_list():
    assert _simplify_field_value([]) == []


def test_simplify_empty_dict():
    assert _simplify_field_value({}) == {}


def test_simplify_unknown_type():
    """Unknown types are converted to string."""
    result = _simplify_field_value(object())
    assert isinstance(result, str)


# -- validate_ticket_key tests --


def test_validate_ticket_key_valid():
    assert validate_ticket_key("CILAB-1234") == "CILAB-1234"
    assert validate_ticket_key("OCP-5678") == "OCP-5678"
    assert validate_ticket_key("RHEL-9999") == "RHEL-9999"
    assert validate_ticket_key("CNF-20992") == "CNF-20992"


def test_validate_ticket_key_with_whitespace():
    assert validate_ticket_key("  CILAB-1234  ") == "CILAB-1234"


def test_validate_ticket_key_invalid():
    with pytest.raises(ValueError, match="Invalid ticket key format"):
        validate_ticket_key("invalid")

    with pytest.raises(ValueError, match="Invalid ticket key format"):
        validate_ticket_key("1234")

    with pytest.raises(ValueError, match="Invalid ticket key format"):
        validate_ticket_key("")

    with pytest.raises(ValueError, match="Invalid ticket key format"):
        validate_ticket_key("CILAB")


# -- _get_field_map tests --


def _make_jira_service():
    """Create a JiraService with mocked JIRA client."""
    with patch.dict("os.environ", {"JIRA_API_TOKEN": "test-token"}):
        with patch("mcp_server.services.jira_service.JIRA"):
            svc = JiraService()
    return svc


def test_get_field_map_caching():
    svc = _make_jira_service()
    svc.jira.fields.return_value = [
        {"id": "customfield_10001", "name": "Sprint"},
        {"id": "customfield_10002", "name": "Story Points"},
    ]

    result1 = svc._get_field_map()
    result2 = svc._get_field_map()

    assert result1 == {
        "customfield_10001": "Sprint",
        "customfield_10002": "Story Points",
    }
    assert result1 is result2
    svc.jira.fields.assert_called_once()


def test_get_field_map_failure_graceful():
    svc = _make_jira_service()
    svc.jira.fields.side_effect = Exception("API error")

    result = svc._get_field_map()
    assert result == {}


# -- get_ticket_data with custom fields --


def _make_mock_issue(raw_fields=None, has_changelog=True, changelog_histories=None):
    """Create a mock Jira issue."""
    issue = MagicMock()
    issue.key = "TEST-123"
    issue.fields.summary = "Test summary"
    issue.fields.description = "Test description"
    issue.fields.status.name = "Open"
    issue.fields.priority.name = "High"
    issue.fields.issuetype.name = "Bug"
    issue.fields.assignee.displayName = "Test User"
    issue.fields.reporter.displayName = "Reporter User"
    issue.fields.created = "2025-01-01T00:00:00Z"
    issue.fields.updated = "2025-01-02T00:00:00Z"
    issue.fields.resolution = None
    issue.fields.labels = ["test-label"]
    issue.fields.components = []
    issue.fields.fixVersions = []
    issue.fields.versions = []

    # Comments
    issue.fields.comment.comments = []

    # Raw fields for custom field extraction
    default_raw = {
        "summary": "Test summary",
        "status": {"name": "Open"},
    }
    if raw_fields:
        default_raw.update(raw_fields)
    issue.raw = {"fields": default_raw}

    # Changelog
    if has_changelog and changelog_histories is not None:
        issue.changelog.histories = changelog_histories
    elif has_changelog:
        issue.changelog.histories = []
    else:
        del issue.changelog

    return issue


def test_get_ticket_data_includes_custom_fields():
    svc = _make_jira_service()
    svc.jira.fields.return_value = [
        {"id": "customfield_10001", "name": "Sprint"},
        {"id": "customfield_10002", "name": "Story Points"},
    ]

    issue = _make_mock_issue(
        raw_fields={
            "customfield_10001": {"name": "Sprint 42", "id": 100},
            "customfield_10002": 5,
        }
    )
    svc.jira.issue.return_value = issue

    result = svc.get_ticket_data("TEST-123")

    assert "custom_fields" in result
    assert result["custom_fields"]["Sprint"] == "Sprint 42"
    assert result["custom_fields"]["Story Points"] == 5


def test_get_ticket_data_skips_null_custom_fields():
    svc = _make_jira_service()
    svc.jira.fields.return_value = [
        {"id": "customfield_10001", "name": "Sprint"},
        {"id": "customfield_10002", "name": "Story Points"},
    ]

    issue = _make_mock_issue(
        raw_fields={
            "customfield_10001": None,
            "customfield_10002": 5,
        }
    )
    svc.jira.issue.return_value = issue

    result = svc.get_ticket_data("TEST-123")

    assert "custom_fields" in result
    assert "Sprint" not in result["custom_fields"]
    assert result["custom_fields"]["Story Points"] == 5


def test_get_ticket_data_no_custom_fields_key_when_all_null():
    svc = _make_jira_service()
    svc.jira.fields.return_value = [
        {"id": "customfield_10001", "name": "Sprint"},
    ]

    issue = _make_mock_issue(
        raw_fields={
            "customfield_10001": None,
        }
    )
    svc.jira.issue.return_value = issue

    result = svc.get_ticket_data("TEST-123")

    assert "custom_fields" not in result


def test_get_ticket_data_falls_back_to_raw_id():
    """When field map is empty, raw IDs are used as keys."""
    svc = _make_jira_service()
    svc.jira.fields.side_effect = Exception("API error")

    issue = _make_mock_issue(
        raw_fields={
            "customfield_10001": "some value",
        }
    )
    svc.jira.issue.return_value = issue

    result = svc.get_ticket_data("TEST-123")

    assert "custom_fields" in result
    assert result["custom_fields"]["customfield_10001"] == "some value"


# -- Changelog author bug fix --


def test_changelog_without_author():
    """Changelog entries without author should not crash."""
    svc = _make_jira_service()
    svc.jira.fields.return_value = []

    history_no_author = MagicMock(spec=["created", "items"])
    history_no_author.created = "2025-01-01T00:00:00Z"
    # Remove author attribute
    del history_no_author.author
    item = MagicMock()
    item.field = "status"
    item.fieldtype = "jira"
    item.fromString = "Open"
    item.toString = "Closed"
    history_no_author.items = [item]

    issue = _make_mock_issue(changelog_histories=[history_no_author])
    svc.jira.issue.return_value = issue

    result = svc.get_ticket_data("TEST-123")

    assert len(result["changelog"]) == 1
    assert result["changelog"][0]["author"] == "Unknown"
    assert result["changelog"][0]["items"][0]["field"] == "status"
