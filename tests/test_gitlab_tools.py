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

"""Unit tests for GitLab tools."""

from unittest.mock import MagicMock, patch

import pytest
from gitlab.exceptions import GitlabAuthenticationError, GitlabGetError

from mcp_server.services.gitlab_service import GitLabService
from mcp_server.tools.gitlab_tools import validate_project_path

# -- validate_project_path tests --


def test_validate_project_path_valid():
    """Test validation of valid project paths."""
    assert validate_project_path("gitlab-org/gitlab") == "gitlab-org/gitlab"
    assert validate_project_path("group/project") == "group/project"
    assert validate_project_path("group/subgroup/project") == "group/subgroup/project"
    assert validate_project_path("a/b/c/d") == "a/b/c/d"
    assert validate_project_path("test-org/test_repo") == "test-org/test_repo"
    assert validate_project_path("user.name/repo.name") == "user.name/repo.name"


def test_validate_project_path_numeric_id():
    """Test validation accepts numeric project IDs."""
    assert validate_project_path("12345") == "12345"
    assert validate_project_path("1") == "1"


def test_validate_project_path_with_whitespace():
    """Test validation trims whitespace."""
    assert validate_project_path("  group/project  ") == "group/project"
    assert validate_project_path("\tgroup/project\n") == "group/project"


def test_validate_project_path_invalid():
    """Test validation rejects invalid project paths."""
    with pytest.raises(ValueError, match="Invalid project path format"):
        validate_project_path("invalid")

    with pytest.raises(ValueError, match="Invalid project path format"):
        validate_project_path("invalid/")

    with pytest.raises(ValueError, match="Invalid project path format"):
        validate_project_path("/invalid")

    with pytest.raises(ValueError, match="Invalid project path format"):
        validate_project_path("")

    with pytest.raises(ValueError, match="Invalid project path format"):
        validate_project_path("group/project with spaces")


# -- helpers --


def _make_gitlab_service():
    """Create a GitLabService with mocked GitLab client."""
    with patch.dict("os.environ", {"GITLAB_TOKEN": "test-token"}):
        with patch("mcp_server.services.gitlab_service.Gitlab"):
            svc = GitLabService()
    return svc


def _make_mock_issue(
    iid=1,
    title="Test issue",
    state="opened",
    description="Issue description",
):
    """Create a mock GitLab issue object."""
    issue = MagicMock()
    issue.iid = iid
    issue.title = title
    issue.state = state
    issue.description = description
    issue.confidential = False
    issue.author = {"username": "testuser", "name": "Test User"}
    issue.assignees = []
    issue.labels = []
    issue.milestone = None
    issue.created_at = "2026-01-01T00:00:00.000Z"
    issue.updated_at = "2026-01-02T00:00:00.000Z"
    issue.closed_at = None
    issue.web_url = f"https://gitlab.com/group/project/-/issues/{iid}"
    issue.user_notes_count = 0
    return issue


def _make_mock_note(note_id=1, body="A comment", system=False):
    """Create a mock GitLab note object."""
    note = MagicMock()
    note.id = note_id
    note.body = body
    note.system = system
    note.author = {"username": "commenter", "name": "Commenter"}
    note.created_at = "2026-01-01T00:00:00.000Z"
    note.updated_at = "2026-01-02T00:00:00.000Z"
    return note


def _make_mock_mr(
    iid=10,
    title="Test MR",
    state="opened",
    draft=False,
    source_branch="feature",
    target_branch="main",
    changes=None,
):
    """Create a mock GitLab merge request object."""
    mr = MagicMock()
    mr.iid = iid
    mr.title = title
    mr.state = state
    mr.draft = draft
    mr.source_branch = source_branch
    mr.target_branch = target_branch
    mr.merged_at = None
    mr.author = {"username": "testuser"}
    mr.assignees = []
    mr.reviewers = []
    mr.labels = []
    mr.milestone = None
    mr.merge_status = "can_be_merged"
    mr.has_conflicts = False
    mr.created_at = "2026-01-01T00:00:00.000Z"
    mr.updated_at = "2026-01-02T00:00:00.000Z"
    mr.closed_at = None
    mr.web_url = f"https://gitlab.com/group/project/-/merge_requests/{iid}"
    mr.changes.return_value = {"changes": changes if changes is not None else []}
    return mr


def _make_mock_change(
    old_path="src/main.py",
    new_path="src/main.py",
    new_file=False,
    deleted_file=False,
    renamed_file=False,
    diff="@@ -1,5 +1,10 @@\n+added line\n-removed line",
):
    """Create a mock file change dict as returned by GitLab API."""
    return {
        "old_path": old_path,
        "new_path": new_path,
        "a_mode": "100644",
        "b_mode": "100644",
        "new_file": new_file,
        "deleted_file": deleted_file,
        "renamed_file": renamed_file,
        "diff": diff,
    }


# -- search_issues tests --


@pytest.mark.unit
def test_search_issues_returns_structure():
    """Test that search_issues returns correct result structure."""
    svc = _make_gitlab_service()

    mock_issues = [_make_mock_issue(iid=i) for i in range(3)]
    mock_iter = MagicMock()
    mock_iter.__iter__ = MagicMock(return_value=iter(mock_issues))
    mock_iter.total = 3

    mock_project = MagicMock()
    mock_project.issues.list.return_value = mock_iter
    svc.gl.projects.get.return_value = mock_project

    result = svc.search_issues("group/project")

    assert result["total_count"] == 3
    assert result["offset"] == 0
    assert result["limit"] == 50
    assert len(result["items"]) == 3


@pytest.mark.unit
def test_search_issues_with_offset():
    """Test that search_issues skips items when offset is set."""
    svc = _make_gitlab_service()

    mock_issues = [_make_mock_issue(iid=i) for i in range(5)]
    mock_iter = MagicMock()
    mock_iter.__iter__ = MagicMock(return_value=iter(mock_issues))
    mock_iter.total = 5

    mock_project = MagicMock()
    mock_project.issues.list.return_value = mock_iter
    svc.gl.projects.get.return_value = mock_project

    result = svc.search_issues("group/project", max_results=2, offset=2)

    assert result["total_count"] == 5
    assert result["offset"] == 2
    assert result["limit"] == 2
    assert len(result["items"]) == 2
    assert result["items"][0]["iid"] == 2
    assert result["items"][1]["iid"] == 3


@pytest.mark.unit
def test_search_issues_passes_filters():
    """Test that search filters are passed to the API."""
    svc = _make_gitlab_service()

    mock_iter = MagicMock()
    mock_iter.__iter__ = MagicMock(return_value=iter([]))
    mock_iter.total = 0

    mock_project = MagicMock()
    mock_project.issues.list.return_value = mock_iter
    svc.gl.projects.get.return_value = mock_project

    svc.search_issues(
        "group/project",
        search="keyword",
        state="opened",
        labels=["bug", "critical"],
    )

    call_kwargs = mock_project.issues.list.call_args[1]
    assert call_kwargs["search"] == "keyword"
    assert call_kwargs["state"] == "opened"
    assert call_kwargs["labels"] == ["bug", "critical"]


# -- get_issue tests --


@pytest.mark.unit
def test_get_issue_basic():
    """Test basic issue retrieval."""
    svc = _make_gitlab_service()

    mock_issue = _make_mock_issue(iid=42, title="Important issue")
    mock_issue.notes.list.return_value = MagicMock(
        __iter__=MagicMock(return_value=iter([]))
    )

    mock_project = MagicMock()
    mock_project.issues.get.return_value = mock_issue
    svc.gl.projects.get.return_value = mock_project

    result = svc.get_issue("group/project", 42)

    assert result["iid"] == 42
    assert result["title"] == "Important issue"
    assert result["description"] == "Issue description"
    assert result["author"] == "testuser"
    assert result["notes"] == []


@pytest.mark.unit
def test_get_issue_with_notes():
    """Test issue retrieval with notes."""
    svc = _make_gitlab_service()

    mock_issue = _make_mock_issue(iid=42)
    mock_notes = [
        _make_mock_note(note_id=1, body="First comment"),
        _make_mock_note(note_id=2, body="Second comment"),
    ]
    notes_iter = MagicMock()
    notes_iter.__iter__ = MagicMock(return_value=iter(mock_notes))
    mock_issue.notes.list.return_value = notes_iter

    mock_project = MagicMock()
    mock_project.issues.get.return_value = mock_issue
    svc.gl.projects.get.return_value = mock_project

    result = svc.get_issue("group/project", 42)

    assert len(result["notes"]) == 2
    assert result["notes"][0]["body"] == "First comment"
    assert result["notes"][1]["body"] == "Second comment"


@pytest.mark.unit
def test_get_issue_filters_system_notes():
    """Test that system notes are excluded from results."""
    svc = _make_gitlab_service()

    mock_issue = _make_mock_issue(iid=42)
    mock_notes = [
        _make_mock_note(note_id=1, body="User comment", system=False),
        _make_mock_note(note_id=2, body="assigned to @user", system=True),
        _make_mock_note(note_id=3, body="Another comment", system=False),
    ]
    notes_iter = MagicMock()
    notes_iter.__iter__ = MagicMock(return_value=iter(mock_notes))
    mock_issue.notes.list.return_value = notes_iter

    mock_project = MagicMock()
    mock_project.issues.get.return_value = mock_issue
    svc.gl.projects.get.return_value = mock_project

    result = svc.get_issue("group/project", 42)

    assert len(result["notes"]) == 2
    assert result["notes"][0]["body"] == "User comment"
    assert result["notes"][1]["body"] == "Another comment"


@pytest.mark.unit
def test_get_notes_with_offset():
    """Test that _get_notes skips notes when offset is set."""
    svc = _make_gitlab_service()

    mock_notes = [_make_mock_note(note_id=i, body=f"comment {i}") for i in range(5)]
    notes_iter = MagicMock()
    notes_iter.__iter__ = MagicMock(return_value=iter(mock_notes))

    mock_issue = MagicMock()
    mock_issue.notes.list.return_value = notes_iter

    result = svc._get_notes(mock_issue, max_notes=2, offset=2)

    assert len(result) == 2
    assert result[0]["id"] == 2
    assert result[1]["id"] == 3


# -- get_mr_diff tests --


@pytest.mark.unit
def test_get_mr_diff_basic():
    """Test basic MR diff retrieval."""
    svc = _make_gitlab_service()

    changes = [_make_mock_change()]
    mock_mr = _make_mock_mr(iid=10, changes=changes)

    mock_project = MagicMock()
    mock_project.mergerequests.get.return_value = mock_mr
    svc.gl.projects.get.return_value = mock_project

    result = svc.get_mr_diff("group/project", 10)

    assert result["iid"] == 10
    assert result["title"] == "Test MR"
    assert result["state"] == "opened"
    assert result["source_branch"] == "feature"
    assert result["target_branch"] == "main"
    assert len(result["files"]) == 1
    assert result["files"][0]["filename"] == "src/main.py"
    assert result["files"][0]["status"] == "modified"
    assert result["files_returned"] == 1
    assert result["total_files"] == 1
    assert "truncated" not in result


@pytest.mark.unit
def test_get_mr_diff_new_file():
    """Test that new files are detected correctly."""
    svc = _make_gitlab_service()

    changes = [
        _make_mock_change(
            old_path="new_file.py",
            new_path="new_file.py",
            new_file=True,
            diff="+new content\n+more content",
        )
    ]
    mock_mr = _make_mock_mr(iid=1, changes=changes)

    mock_project = MagicMock()
    mock_project.mergerequests.get.return_value = mock_mr
    svc.gl.projects.get.return_value = mock_project

    result = svc.get_mr_diff("group/project", 1)

    assert result["files"][0]["status"] == "added"
    assert result["files"][0]["additions"] == 2
    assert result["files"][0]["deletions"] == 0


@pytest.mark.unit
def test_get_mr_diff_deleted_file():
    """Test that deleted files are detected correctly."""
    svc = _make_gitlab_service()

    changes = [
        _make_mock_change(
            old_path="old.py",
            new_path="old.py",
            deleted_file=True,
            diff="-removed line",
        )
    ]
    mock_mr = _make_mock_mr(iid=2, changes=changes)

    mock_project = MagicMock()
    mock_project.mergerequests.get.return_value = mock_mr
    svc.gl.projects.get.return_value = mock_project

    result = svc.get_mr_diff("group/project", 2)

    assert result["files"][0]["status"] == "removed"
    assert result["files"][0]["deletions"] == 1


@pytest.mark.unit
def test_get_mr_diff_renamed_file():
    """Test that renamed files include old_filename."""
    svc = _make_gitlab_service()

    changes = [
        _make_mock_change(
            old_path="old_name.py",
            new_path="new_name.py",
            renamed_file=True,
            diff="",
        )
    ]
    mock_mr = _make_mock_mr(iid=3, changes=changes)

    mock_project = MagicMock()
    mock_project.mergerequests.get.return_value = mock_mr
    svc.gl.projects.get.return_value = mock_project

    result = svc.get_mr_diff("group/project", 3)

    assert result["files"][0]["status"] == "renamed"
    assert result["files"][0]["old_filename"] == "old_name.py"
    assert result["files"][0]["filename"] == "new_name.py"


@pytest.mark.unit
def test_get_mr_diff_binary_file():
    """Test that binary files have null diff."""
    svc = _make_gitlab_service()

    changes = [
        _make_mock_change(
            old_path="image.png",
            new_path="image.png",
            diff=None,
        )
    ]
    mock_mr = _make_mock_mr(iid=4, changes=changes)

    mock_project = MagicMock()
    mock_project.mergerequests.get.return_value = mock_mr
    svc.gl.projects.get.return_value = mock_project

    result = svc.get_mr_diff("group/project", 4)

    assert result["files"][0]["diff"] is None
    assert result["files"][0]["additions"] == 0
    assert result["files"][0]["deletions"] == 0


@pytest.mark.unit
def test_get_mr_diff_truncation():
    """Test that files are truncated when exceeding max_files."""
    svc = _make_gitlab_service()

    changes = [
        _make_mock_change(new_path=f"file{i}.py", old_path=f"file{i}.py")
        for i in range(5)
    ]
    mock_mr = _make_mock_mr(iid=5, changes=changes)

    mock_project = MagicMock()
    mock_project.mergerequests.get.return_value = mock_mr
    svc.gl.projects.get.return_value = mock_project

    result = svc.get_mr_diff("group/project", 5, max_files=2)

    assert result["files_returned"] == 2
    assert result["total_files"] == 5
    assert result["truncated"] is True
    assert "2 of 5" in result["truncation_message"]


@pytest.mark.unit
def test_get_mr_diff_offset():
    """Test pagination with offset skips files correctly."""
    svc = _make_gitlab_service()

    changes = [
        _make_mock_change(new_path=f"file{i}.py", old_path=f"file{i}.py")
        for i in range(5)
    ]
    mock_mr = _make_mock_mr(iid=6, changes=changes)

    mock_project = MagicMock()
    mock_project.mergerequests.get.return_value = mock_mr
    svc.gl.projects.get.return_value = mock_project

    result = svc.get_mr_diff("group/project", 6, max_files=2, offset=2)

    assert result["files_returned"] == 2
    assert result["offset"] == 2
    assert result["files"][0]["filename"] == "file2.py"
    assert result["files"][1]["filename"] == "file3.py"


@pytest.mark.unit
def test_get_mr_diff_offset_past_end():
    """Test offset beyond available files returns empty list."""
    svc = _make_gitlab_service()

    changes = [
        _make_mock_change(new_path=f"file{i}.py", old_path=f"file{i}.py")
        for i in range(3)
    ]
    mock_mr = _make_mock_mr(iid=7, changes=changes)

    mock_project = MagicMock()
    mock_project.mergerequests.get.return_value = mock_mr
    svc.gl.projects.get.return_value = mock_project

    result = svc.get_mr_diff("group/project", 7, max_files=10, offset=10)

    assert result["files_returned"] == 0
    assert result["files"] == []
    assert result["offset"] == 10


@pytest.mark.unit
def test_get_mr_diff_empty_mr():
    """Test MR with no changed files."""
    svc = _make_gitlab_service()

    mock_mr = _make_mock_mr(iid=8, changes=[])

    mock_project = MagicMock()
    mock_project.mergerequests.get.return_value = mock_mr
    svc.gl.projects.get.return_value = mock_project

    result = svc.get_mr_diff("group/project", 8)

    assert result["files"] == []
    assert result["files_returned"] == 0
    assert result["total_files"] == 0
    assert "truncated" not in result


@pytest.mark.unit
def test_get_mr_diff_computes_total_stats():
    """Test that total additions/deletions are computed across all files."""
    svc = _make_gitlab_service()

    changes = [
        _make_mock_change(
            new_path="a.py",
            old_path="a.py",
            diff="+line1\n+line2\n-old",
        ),
        _make_mock_change(
            new_path="b.py",
            old_path="b.py",
            diff="+new\n-old1\n-old2",
        ),
    ]
    mock_mr = _make_mock_mr(iid=9, changes=changes)

    mock_project = MagicMock()
    mock_project.mergerequests.get.return_value = mock_mr
    svc.gl.projects.get.return_value = mock_project

    result = svc.get_mr_diff("group/project", 9)

    assert result["additions"] == 3
    assert result["deletions"] == 3


# -- get_project_info tests --


@pytest.mark.unit
def test_get_project_info_basic():
    """Test basic project info retrieval."""
    svc = _make_gitlab_service()

    mock_project = MagicMock()
    mock_project.name = "my-project"
    mock_project.path_with_namespace = "group/my-project"
    mock_project.description = "A test project"
    mock_project.namespace = {"full_path": "group"}
    mock_project.visibility = "public"
    mock_project.default_branch = "main"
    mock_project.star_count = 42
    mock_project.forks_count = 10
    mock_project.open_issues_count = 5
    mock_project.topics = ["python", "testing"]
    mock_project.created_at = "2025-01-01T00:00:00.000Z"
    mock_project.last_activity_at = "2026-01-01T00:00:00.000Z"
    mock_project.web_url = "https://gitlab.com/group/my-project"
    svc.gl.projects.get.return_value = mock_project

    result = svc.get_project_info("group/my-project")

    assert result["name"] == "my-project"
    assert result["path_with_namespace"] == "group/my-project"
    assert result["description"] == "A test project"
    assert result["namespace"] == "group"
    assert result["visibility"] == "public"
    assert result["default_branch"] == "main"
    assert result["stars"] == 42
    assert result["forks"] == 10
    assert result["open_issues_count"] == 5
    assert result["topics"] == ["python", "testing"]
    assert result["url"] == "https://gitlab.com/group/my-project"


# -- search_merge_requests tests --


@pytest.mark.unit
def test_search_merge_requests_returns_structure():
    """Test that search_merge_requests returns correct structure."""
    svc = _make_gitlab_service()

    mock_mrs = [_make_mock_mr(iid=i) for i in range(3)]
    mock_iter = MagicMock()
    mock_iter.__iter__ = MagicMock(return_value=iter(mock_mrs))
    mock_iter.total = 3

    mock_project = MagicMock()
    mock_project.mergerequests.list.return_value = mock_iter
    svc.gl.projects.get.return_value = mock_project

    result = svc.search_merge_requests("group/project")

    assert result["total_count"] == 3
    assert result["offset"] == 0
    assert result["limit"] == 50
    assert len(result["items"]) == 3


@pytest.mark.unit
def test_search_merge_requests_with_offset():
    """Test MR search with offset pagination."""
    svc = _make_gitlab_service()

    mock_mrs = [_make_mock_mr(iid=i) for i in range(5)]
    mock_iter = MagicMock()
    mock_iter.__iter__ = MagicMock(return_value=iter(mock_mrs))
    mock_iter.total = 5

    mock_project = MagicMock()
    mock_project.mergerequests.list.return_value = mock_iter
    svc.gl.projects.get.return_value = mock_project

    result = svc.search_merge_requests("group/project", max_results=2, offset=2)

    assert len(result["items"]) == 2
    assert result["items"][0]["iid"] == 2
    assert result["items"][1]["iid"] == 3


# -- error handling tests --


@pytest.mark.unit
def test_auth_error_search_issues():
    """Test that GitlabAuthenticationError surfaces clearly."""
    svc = _make_gitlab_service()
    svc.gl.projects.get.side_effect = GitlabAuthenticationError("401 Unauthorized")

    with pytest.raises(Exception, match="authentication error"):
        svc.search_issues("group/project")


@pytest.mark.unit
def test_gitlab_error_get_issue():
    """Test that GitlabGetError is handled properly."""
    svc = _make_gitlab_service()

    mock_project = MagicMock()
    mock_project.issues.get.side_effect = GitlabGetError("404 Not Found")
    svc.gl.projects.get.return_value = mock_project

    with pytest.raises(Exception, match="GitLab API error"):
        svc.get_issue("group/project", 999)


@pytest.mark.unit
def test_gitlab_error_get_mr_diff():
    """Test that GitlabGetError from get_mr_diff is handled."""
    svc = _make_gitlab_service()

    mock_project = MagicMock()
    mock_project.mergerequests.get.side_effect = GitlabGetError("404 Not Found")
    svc.gl.projects.get.return_value = mock_project

    with pytest.raises(Exception, match="GitLab API error"):
        svc.get_mr_diff("group/project", 42)


@pytest.mark.unit
def test_gitlab_error_get_project_info():
    """Test that GitlabGetError from get_project_info is handled."""
    svc = _make_gitlab_service()
    svc.gl.projects.get.side_effect = GitlabGetError("404 Not Found")

    with pytest.raises(Exception, match="GitLab API error"):
        svc.get_project_info("group/nonexistent")


@pytest.mark.unit
def test_auth_error_not_swallowed_in_get_notes():
    """Test that GitlabAuthenticationError is not swallowed in _get_notes."""
    svc = _make_gitlab_service()
    mock_issue = MagicMock()
    mock_issue.notes.list.side_effect = GitlabAuthenticationError("401 Unauthorized")

    with pytest.raises(GitlabAuthenticationError):
        svc._get_notes(mock_issue, 10)


@pytest.mark.unit
def test_missing_token_raises_value_error():
    """Test that missing GITLAB_TOKEN raises ValueError."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="GITLAB_TOKEN"):
            GitLabService()


@pytest.mark.unit
def test_gitlab_url_override():
    """Test that gitlab_url parameter overrides env var."""
    with patch.dict(
        "os.environ",
        {"GITLAB_TOKEN": "test-token", "GITLAB_URL": "https://default.com"},
        clear=True,
    ):
        with patch("mcp_server.services.gitlab_service.Gitlab") as mock_gitlab:
            svc = GitLabService(gitlab_url="https://custom.example.com")

    assert svc.gitlab_url == "https://custom.example.com"
    mock_gitlab.assert_called_once_with(
        "https://custom.example.com",
        private_token="test-token",
        ssl_verify=True,
    )


@pytest.mark.unit
def test_gitlab_url_falls_back_to_env():
    """Test that GITLAB_URL env var is used when no override."""
    with patch.dict(
        "os.environ",
        {"GITLAB_TOKEN": "test-token", "GITLAB_URL": "https://env.example.com"},
        clear=True,
    ):
        with patch("mcp_server.services.gitlab_service.Gitlab") as mock_gitlab:
            svc = GitLabService()

    assert svc.gitlab_url == "https://env.example.com"
    mock_gitlab.assert_called_once_with(
        "https://env.example.com",
        private_token="test-token",
        ssl_verify=True,
    )


@pytest.mark.unit
def test_gitlab_url_defaults_to_gitlab_com():
    """Test that gitlab.com is the default when no URL is configured."""
    with patch.dict("os.environ", {"GITLAB_TOKEN": "test-token"}, clear=True):
        with patch("mcp_server.services.gitlab_service.Gitlab") as mock_gitlab:
            svc = GitLabService()

    assert svc.gitlab_url == "https://gitlab.com"
    mock_gitlab.assert_called_once_with(
        "https://gitlab.com",
        private_token="test-token",
        ssl_verify=True,
    )


@pytest.mark.unit
def test_ssl_verify_false_via_env():
    """Test that GITLAB_SSL_VERIFY=false disables SSL verification."""
    with patch.dict(
        "os.environ",
        {"GITLAB_TOKEN": "test-token", "GITLAB_SSL_VERIFY": "false"},
        clear=True,
    ):
        with patch("mcp_server.services.gitlab_service.Gitlab") as mock_gitlab:
            svc = GitLabService()

    assert svc.ssl_verify is False
    mock_gitlab.assert_called_once_with(
        "https://gitlab.com",
        private_token="test-token",
        ssl_verify=False,
    )


@pytest.mark.unit
def test_ssl_verify_ca_bundle_via_env():
    """Test that GITLAB_SSL_VERIFY can point to a CA bundle."""
    with patch.dict(
        "os.environ",
        {
            "GITLAB_TOKEN": "test-token",
            "GITLAB_SSL_VERIFY": "/etc/pki/tls/certs/ca-bundle.crt",
        },
        clear=True,
    ):
        with patch("mcp_server.services.gitlab_service.Gitlab") as mock_gitlab:
            svc = GitLabService()

    assert svc.ssl_verify == "/etc/pki/tls/certs/ca-bundle.crt"
    mock_gitlab.assert_called_once_with(
        "https://gitlab.com",
        private_token="test-token",
        ssl_verify="/etc/pki/tls/certs/ca-bundle.crt",
    )


@pytest.mark.unit
def test_ssl_verify_parameter_overrides_env():
    """Test that ssl_verify parameter overrides env var."""
    with patch.dict(
        "os.environ",
        {"GITLAB_TOKEN": "test-token", "GITLAB_SSL_VERIFY": "true"},
        clear=True,
    ):
        with patch("mcp_server.services.gitlab_service.Gitlab") as mock_gitlab:
            svc = GitLabService(ssl_verify=False)

    assert svc.ssl_verify is False
    mock_gitlab.assert_called_once_with(
        "https://gitlab.com",
        private_token="test-token",
        ssl_verify=False,
    )


# -- _count_diff_stats tests --


@pytest.mark.unit
def test_count_diff_stats_basic():
    """Test diff stats counting."""
    diff = "@@ -1,3 +1,4 @@\n+added\n-removed\n context\n+another add"
    additions, deletions = GitLabService._count_diff_stats(diff)
    assert additions == 2
    assert deletions == 1


@pytest.mark.unit
def test_count_diff_stats_none():
    """Test diff stats returns zero for None diff."""
    additions, deletions = GitLabService._count_diff_stats(None)
    assert additions == 0
    assert deletions == 0


@pytest.mark.unit
def test_count_diff_stats_ignores_header_markers():
    """Test that +++ and --- header lines are not counted."""
    diff = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new"
    additions, deletions = GitLabService._count_diff_stats(diff)
    assert additions == 1
    assert deletions == 1


# -- _get_change_status tests --


@pytest.mark.unit
def test_get_change_status():
    """Test file change status detection."""
    assert GitLabService._get_change_status({"new_file": True}) == "added"
    assert GitLabService._get_change_status({"deleted_file": True}) == "removed"
    assert GitLabService._get_change_status({"renamed_file": True}) == "renamed"
    assert GitLabService._get_change_status({}) == "modified"
