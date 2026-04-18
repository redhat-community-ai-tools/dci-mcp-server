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


# -- search_tickets pagination tests --


@pytest.mark.unit
def test_search_tickets_returns_total_count():
    """Test that search_tickets returns total_count and items structure."""
    svc = _make_jira_service()

    mock_issues = MagicMock()
    mock_issues.total = 100
    mock_issue = MagicMock()
    mock_issue.key = "TEST-1"
    mock_issue.fields.summary = "Test"
    mock_issue.fields.description = None
    mock_issue.fields.status.name = "Open"
    mock_issue.fields.status.id = "1"
    mock_issue.fields.issuetype.name = "Bug"
    mock_issue.fields.priority.name = "High"
    mock_issue.fields.assignee.displayName = "Test User"
    mock_issue.fields.labels = []
    mock_issue.fields.resolution = None
    mock_issue.fields.created = "2025-01-01"
    mock_issue.fields.updated = "2025-01-02"
    mock_issues.__iter__ = MagicMock(return_value=iter([mock_issue]))
    svc.jira.search_issues.return_value = mock_issues

    result = svc.search_tickets("project = TEST")

    assert result["total_count"] == 100
    assert result["offset"] == 0
    assert result["limit"] == 50
    assert len(result["items"]) == 1
    assert result["items"][0]["key"] == "TEST-1"


@pytest.mark.unit
def test_search_tickets_with_offset():
    """Test that search_tickets passes offset to Jira API as startAt."""
    svc = _make_jira_service()

    mock_issues = MagicMock()
    mock_issues.total = 200
    mock_issues.__iter__ = MagicMock(return_value=iter([]))
    svc.jira.search_issues.return_value = mock_issues

    svc.search_tickets("project = TEST", max_results=10, offset=50)

    svc.jira.search_issues.assert_called_once_with(
        "project = TEST",
        startAt=50,
        maxResults=10,
        fields="summary,status,issuetype,priority,assignee,labels,resolution,created,updated,description",
    )


# -- _get_comments pagination tests --


@pytest.mark.unit
def test_jira_get_comments_with_offset():
    """Test that Jira _get_comments paginates with offset."""
    svc = _make_jira_service()

    mock_comments = []
    for i in range(5):
        c = MagicMock()
        c.id = str(i)
        c.author.displayName = f"User {i}"
        c.body = f"Comment {i}"
        c.created = f"2025-01-0{i + 1}T00:00:00Z"
        c.updated = f"2025-01-0{i + 1}T00:00:00Z"
        mock_comments.append(c)

    mock_issue = MagicMock()
    mock_issue.fields.comment.comments = mock_comments

    result = svc._get_comments(mock_issue, max_comments=2, offset=2)

    assert len(result) == 2
    assert result[0]["id"] == "2"
    assert result[1]["id"] == "3"


@pytest.mark.unit
def test_jira_get_comments_offset_past_end():
    """Test that offset past end returns empty list."""
    svc = _make_jira_service()

    mock_comments = []
    for i in range(3):
        c = MagicMock()
        c.id = str(i)
        c.author.displayName = f"User {i}"
        c.body = f"Comment {i}"
        c.created = "2025-01-01T00:00:00Z"
        c.updated = "2025-01-01T00:00:00Z"
        mock_comments.append(c)

    mock_issue = MagicMock()
    mock_issue.fields.comment.comments = mock_comments

    result = svc._get_comments(mock_issue, max_comments=10, offset=10)

    assert result == []


@pytest.mark.unit
def test_get_ticket_data_includes_total_comments():
    """Test that get_ticket_data includes total_comments field."""
    svc = _make_jira_service()
    svc.jira.fields.return_value = []

    mock_comments = []
    for i in range(5):
        c = MagicMock()
        c.id = str(i)
        c.author.displayName = f"User {i}"
        c.body = f"Comment {i}"
        c.created = "2025-01-01T00:00:00Z"
        c.updated = "2025-01-01T00:00:00Z"
        mock_comments.append(c)

    issue = _make_mock_issue()
    issue.fields.comment.comments = mock_comments
    svc.jira.issue.return_value = issue

    result = svc.get_ticket_data("TEST-123", max_comments=2, comment_offset=1)

    assert result["total_comments"] == 5
    assert len(result["comments"]) == 2
    assert result["comments"][0]["id"] == "1"
    assert result["comments"][1]["id"] == "2"


# -- create_issue tests --


def test_create_issue():
    svc = _make_jira_service()
    mock_issue = MagicMock()
    mock_issue.key = "TEST-999"
    mock_issue.fields.summary = "New ticket"
    svc.jira.create_issue.return_value = mock_issue

    result = svc.create_issue("TEST", "New ticket")

    svc.jira.create_issue.assert_called_once_with(
        fields={
            "project": {"key": "TEST"},
            "summary": "New ticket",
            "issuetype": {"name": "Task"},
        }
    )
    assert result["key"] == "TEST-999"
    assert result["summary"] == "New ticket"
    assert "url" in result


def test_create_issue_with_optional_fields():
    svc = _make_jira_service()
    mock_issue = MagicMock()
    mock_issue.key = "TEST-1000"
    mock_issue.fields.summary = "Full ticket"
    svc.jira.create_issue.return_value = mock_issue

    result = svc.create_issue(
        project_key="TEST",
        summary="Full ticket",
        description="A description",
        issue_type="Bug",
        priority="Critical",
        labels=["label1", "label2"],
        components=["comp1"],
        assignee="jsmith",
    )

    call_fields = svc.jira.create_issue.call_args[1]["fields"]
    assert call_fields["project"] == {"key": "TEST"}
    assert call_fields["summary"] == "Full ticket"
    assert call_fields["description"] == "A description"
    assert call_fields["issuetype"] == {"name": "Bug"}
    assert call_fields["priority"] == {"name": "Critical"}
    assert call_fields["labels"] == ["label1", "label2"]
    assert call_fields["components"] == [{"name": "comp1"}]
    assert call_fields["assignee"] == {"name": "jsmith"}
    assert result["key"] == "TEST-1000"


# -- update_issue tests --


def test_update_issue_fields():
    svc = _make_jira_service()
    mock_issue = MagicMock()
    mock_issue.key = "TEST-123"
    svc.jira.issue.return_value = mock_issue

    result = svc.update_issue("TEST-123", summary="Updated summary", priority="Major")

    mock_issue.update.assert_called_once_with(
        fields={"summary": "Updated summary", "priority": {"name": "Major"}}
    )
    assert result["key"] == "TEST-123"
    assert result["status"] == "updated"


def test_update_issue_transition():
    svc = _make_jira_service()
    mock_issue = MagicMock()
    mock_issue.key = "TEST-123"
    svc.jira.issue.return_value = mock_issue
    svc.jira.transitions.return_value = [
        {"id": "21", "name": "In Progress"},
        {"id": "31", "name": "Done"},
    ]

    result = svc.update_issue("TEST-123", transition="In Progress")

    svc.jira.transition_issue.assert_called_once_with(mock_issue, "21")
    assert result["status"] == "updated"


def test_update_issue_transition_case_insensitive():
    svc = _make_jira_service()
    mock_issue = MagicMock()
    svc.jira.issue.return_value = mock_issue
    svc.jira.transitions.return_value = [
        {"id": "21", "name": "In Progress"},
    ]

    svc.update_issue("TEST-123", transition="in progress")

    svc.jira.transition_issue.assert_called_once_with(mock_issue, "21")


def test_update_issue_transition_not_found():
    svc = _make_jira_service()
    mock_issue = MagicMock()
    svc.jira.issue.return_value = mock_issue
    svc.jira.transitions.return_value = [
        {"id": "21", "name": "In Progress"},
        {"id": "31", "name": "Done"},
    ]

    with pytest.raises(ValueError, match="Transition 'Closed' not found"):
        svc.update_issue("TEST-123", transition="Closed")


# -- add_comment tests --


def test_add_comment():
    svc = _make_jira_service()
    mock_comment = MagicMock()
    mock_comment.id = "12345"
    mock_comment.author.displayName = "Test User"
    mock_comment.created = "2025-01-01T00:00:00Z"
    svc.jira.add_comment.return_value = mock_comment

    result = svc.add_comment("TEST-123", "This is a comment")

    svc.jira.add_comment.assert_called_once_with("TEST-123", "This is a comment")
    assert result["comment_id"] == "12345"
    assert result["author"] == "Test User"
    assert result["created"] == "2025-01-01T00:00:00Z"


# -- get_transitions tests --


def test_get_transitions():
    svc = _make_jira_service()
    svc.jira.transitions.return_value = [
        {"id": "11", "name": "To Do", "extra": "ignored"},
        {"id": "21", "name": "In Progress", "extra": "ignored"},
        {"id": "31", "name": "Done", "extra": "ignored"},
    ]

    result = svc.get_transitions("TEST-123")

    assert len(result) == 3
    assert result[0] == {"id": "11", "name": "To Do"}
    assert result[1] == {"id": "21", "name": "In Progress"}
    assert result[2] == {"id": "31", "name": "Done"}
