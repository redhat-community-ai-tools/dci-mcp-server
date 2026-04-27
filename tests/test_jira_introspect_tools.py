"""Unit tests for Jira introspection tools and service methods."""

from unittest.mock import MagicMock, patch

import pytest

from mcp_server.services.jira_service import JiraService


def _make_jira_service():
    """Create a JiraService with mocked JIRA client."""
    with patch.dict("os.environ", {"JIRA_API_TOKEN": "test-token"}):
        with patch("mcp_server.services.jira_service.JIRA"):
            svc = JiraService()
    return svc


# -- get_filter tests --


def test_get_filter():
    svc = _make_jira_service()
    mock_filter = MagicMock()
    mock_filter.id = "12345"
    mock_filter.name = "CI Duty Filter"
    mock_filter.jql = "project = CILAB AND status = Open"
    mock_filter.description = "Daily CI duty filter"
    mock_filter.owner.displayName = "Test User"
    mock_filter.favourite = True
    mock_filter.viewUrl = "https://jira.example.com/issues/?filter=12345"
    svc.jira.filter.return_value = mock_filter

    result = svc.get_filter("12345")

    assert result["id"] == "12345"
    assert result["name"] == "CI Duty Filter"
    assert result["jql"] == "project = CILAB AND status = Open"
    assert result["description"] == "Daily CI duty filter"
    assert result["owner"] == "Test User"
    assert result["favourite"] is True
    assert result["url"] == "https://jira.example.com/issues/?filter=12345"
    svc.jira.filter.assert_called_once_with("12345")


def test_get_filter_error():
    svc = _make_jira_service()
    svc.jira.filter.side_effect = Exception("Not found")

    with pytest.raises(Exception, match="Error retrieving filter 99999"):
        svc.get_filter("99999")


# -- get_favourite_filters tests --


def test_get_favourite_filters():
    svc = _make_jira_service()
    f1 = MagicMock()
    f1.id = "100"
    f1.name = "Filter A"
    f1.jql = "project = A"
    f1.description = "Desc A"
    f1.owner.displayName = "User A"
    f1.viewUrl = "https://jira.example.com/issues/?filter=100"

    f2 = MagicMock()
    f2.id = "200"
    f2.name = "Filter B"
    f2.jql = "project = B"
    f2.description = None
    f2.owner.displayName = "User B"
    f2.viewUrl = None

    svc.jira.favourite_filters.return_value = [f1, f2]

    result = svc.get_favourite_filters()

    assert len(result) == 2
    assert result[0]["id"] == "100"
    assert result[0]["name"] == "Filter A"
    assert result[0]["jql"] == "project = A"
    assert result[1]["id"] == "200"
    assert result[1]["description"] is None


def test_get_favourite_filters_empty():
    svc = _make_jira_service()
    svc.jira.favourite_filters.return_value = []

    result = svc.get_favourite_filters()

    assert result == []


# -- search_filters tests --


def test_search_filters():
    svc = _make_jira_service()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "values": [
            {
                "id": "10100",
                "name": "TELCO-V10N-STORIES-ALL",
                "jql": "project = V10N AND type = Story",
                "description": "All V10N stories",
                "owner": {"displayName": "Test User"},
                "favourite": False,
                "viewUrl": "https://jira.example.com/issues/?filter=10100",
            },
            {
                "id": "10101",
                "name": "TELCO-V10N-BUGS",
                "jql": "project = V10N AND type = Bug",
                "description": None,
                "owner": None,
                "favourite": True,
                "viewUrl": None,
            },
        ]
    }
    svc.jira._session.get.return_value = mock_response

    result = svc.search_filters("TELCO-V10N")

    assert len(result) == 2
    assert result[0]["id"] == "10100"
    assert result[0]["name"] == "TELCO-V10N-STORIES-ALL"
    assert result[0]["jql"] == "project = V10N AND type = Story"
    assert result[0]["owner"] == "Test User"
    assert result[1]["id"] == "10101"
    assert result[1]["owner"] is None


def test_search_filters_empty():
    svc = _make_jira_service()
    mock_response = MagicMock()
    mock_response.json.return_value = {"values": []}
    svc.jira._session.get.return_value = mock_response

    result = svc.search_filters("nonexistent")

    assert result == []


def test_search_filters_error():
    svc = _make_jira_service()
    svc.jira._session.get.side_effect = Exception("Connection failed")

    with pytest.raises(Exception, match="Error searching filters by name"):
        svc.search_filters("test")


# -- get_project_components tests --


def test_get_project_components():
    svc = _make_jira_service()
    c1 = MagicMock()
    c1.id = "1001"
    c1.name = "Backend"
    c1.description = "Backend services"
    c1.lead.displayName = "Lead User"
    c1.assigneeType = "PROJECT_LEAD"

    c2 = MagicMock()
    c2.id = "1002"
    c2.name = "Frontend"
    c2.description = None
    del c2.lead
    c2.assigneeType = "UNASSIGNED"

    svc.jira.project_components.return_value = [c1, c2]

    result = svc.get_project_components("TEST")

    assert len(result) == 2
    assert result[0]["id"] == "1001"
    assert result[0]["name"] == "Backend"
    assert result[0]["description"] == "Backend services"
    assert result[0]["lead"] == "Lead User"
    assert result[0]["assignee_type"] == "PROJECT_LEAD"
    assert result[1]["name"] == "Frontend"
    svc.jira.project_components.assert_called_once_with("TEST")


def test_get_project_components_empty():
    svc = _make_jira_service()
    svc.jira.project_components.return_value = []

    result = svc.get_project_components("TEST")

    assert result == []


# -- get_project_versions tests --


def test_get_project_versions():
    svc = _make_jira_service()
    v1 = MagicMock()
    v1.id = "2001"
    v1.name = "4.18.0"
    v1.description = "GA release"
    v1.released = True
    v1.archived = False
    v1.releaseDate = "2025-06-01"
    v1.startDate = "2025-01-01"

    v2 = MagicMock()
    v2.id = "2002"
    v2.name = "4.19.0"
    v2.description = None
    v2.released = False
    v2.archived = False
    del v2.releaseDate
    del v2.startDate

    svc.jira.project_versions.return_value = [v1, v2]

    result = svc.get_project_versions("TEST")

    assert len(result) == 2
    assert result[0]["id"] == "2001"
    assert result[0]["name"] == "4.18.0"
    assert result[0]["released"] is True
    assert result[0]["release_date"] == "2025-06-01"
    assert result[0]["start_date"] == "2025-01-01"
    assert result[1]["name"] == "4.19.0"
    assert result[1]["released"] is False
    svc.jira.project_versions.assert_called_once_with("TEST")


def test_get_project_versions_empty():
    svc = _make_jira_service()
    svc.jira.project_versions.return_value = []

    result = svc.get_project_versions("TEST")

    assert result == []


# -- get_issue_types_for_project tests --


def test_get_issue_types_for_project():
    svc = _make_jira_service()
    it1 = MagicMock()
    it1.id = "10001"
    it1.name = "Bug"
    it1.subtask = False
    it1.description = "A defect"

    it2 = MagicMock()
    it2.id = "10002"
    it2.name = "Sub-task"
    it2.subtask = True
    it2.description = "A sub-task"

    svc.jira.issue_types_for_project.return_value = [it1, it2]

    result = svc.get_issue_types_for_project("TEST")

    assert len(result) == 2
    assert result[0]["id"] == "10001"
    assert result[0]["name"] == "Bug"
    assert result[0]["subtask"] is False
    assert result[0]["description"] == "A defect"
    assert result[1]["subtask"] is True
    svc.jira.issue_types_for_project.assert_called_once_with("TEST")


def test_get_issue_types_for_project_no_description():
    svc = _make_jira_service()
    it1 = MagicMock()
    it1.id = "10001"
    it1.name = "Task"
    it1.subtask = False
    del it1.description

    svc.jira.issue_types_for_project.return_value = [it1]

    result = svc.get_issue_types_for_project("TEST")

    assert result[0]["description"] is None


# -- get_boards tests --


def test_get_boards():
    svc = _make_jira_service()
    b1 = MagicMock()
    b1.id = 42
    b1.name = "CILAB Board"
    b1.type = "scrum"

    b2 = MagicMock()
    b2.id = 43
    b2.name = "OCP Kanban"
    b2.type = "kanban"

    mock_boards = MagicMock()
    mock_boards.total = 2
    mock_boards.__iter__ = MagicMock(return_value=iter([b1, b2]))
    svc.jira.boards.return_value = mock_boards

    result = svc.get_boards()

    assert result["total"] == 2
    assert result["start_at"] == 0
    assert result["max_results"] == 50
    assert len(result["items"]) == 2
    assert result["items"][0]["id"] == 42
    assert result["items"][0]["name"] == "CILAB Board"
    assert result["items"][0]["type"] == "scrum"


def test_get_boards_with_project_filter():
    svc = _make_jira_service()
    mock_boards = MagicMock()
    mock_boards.total = 0
    mock_boards.__iter__ = MagicMock(return_value=iter([]))
    svc.jira.boards.return_value = mock_boards

    svc.get_boards(project_key="CILAB", board_type="scrum", max_results=10, start_at=5)

    svc.jira.boards.assert_called_once_with(
        startAt=5,
        maxResults=10,
        type="scrum",
        name=None,
        projectKeyOrID="CILAB",
    )


# -- get_sprints tests --


def test_get_sprints():
    svc = _make_jira_service()
    s1 = MagicMock()
    s1.id = 101
    s1.name = "Sprint 1"
    s1.state = "active"
    s1.startDate = "2025-01-01"
    s1.endDate = "2025-01-14"
    s1.completeDate = None
    s1.goal = "Deliver feature X"

    s2 = MagicMock()
    s2.id = 102
    s2.name = "Sprint 2"
    s2.state = "future"
    del s2.startDate
    del s2.endDate
    del s2.completeDate
    del s2.goal

    mock_sprints = MagicMock()
    mock_sprints.total = 2
    mock_sprints.__iter__ = MagicMock(return_value=iter([s1, s2]))
    svc.jira.sprints.return_value = mock_sprints

    result = svc.get_sprints(board_id=42)

    assert result["total"] == 2
    assert len(result["items"]) == 2
    assert result["items"][0]["id"] == 101
    assert result["items"][0]["name"] == "Sprint 1"
    assert result["items"][0]["state"] == "active"
    assert result["items"][0]["start_date"] == "2025-01-01"
    assert result["items"][0]["goal"] == "Deliver feature X"
    assert result["items"][1]["state"] == "future"


def test_get_sprints_with_state_filter():
    svc = _make_jira_service()
    mock_sprints = MagicMock()
    mock_sprints.total = 0
    mock_sprints.__iter__ = MagicMock(return_value=iter([]))
    svc.jira.sprints.return_value = mock_sprints

    svc.get_sprints(board_id=42, state="active", max_results=10, start_at=5)

    svc.jira.sprints.assert_called_once_with(
        board_id=42,
        startAt=5,
        maxResults=10,
        state="active",
    )
