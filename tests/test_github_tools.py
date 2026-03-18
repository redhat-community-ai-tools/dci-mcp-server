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

"""Unit tests for GitHub tools."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from github.GithubException import GithubException, RateLimitExceededException

from mcp_server.services.github_service import GitHubService
from mcp_server.tools.github_tools import validate_repo_name


def test_validate_repo_name_valid():
    """Test validation of valid repository names."""
    assert validate_repo_name("octocat/Hello-World") == "octocat/Hello-World"
    assert validate_repo_name("torvalds/linux") == "torvalds/linux"
    assert validate_repo_name("facebook/react") == "facebook/react"
    assert validate_repo_name("test-org/test-repo") == "test-org/test-repo"
    assert validate_repo_name("user.name/repo_name") == "user.name/repo_name"


def test_validate_repo_name_with_whitespace():
    """Test validation trims whitespace."""
    assert validate_repo_name("  octocat/Hello-World  ") == "octocat/Hello-World"
    assert validate_repo_name("\toctocat/Hello-World\n") == "octocat/Hello-World"


def test_validate_repo_name_invalid():
    """Test validation rejects invalid repository names."""
    with pytest.raises(ValueError, match="Invalid repository name format"):
        validate_repo_name("invalid")

    with pytest.raises(ValueError, match="Invalid repository name format"):
        validate_repo_name("invalid/")

    with pytest.raises(ValueError, match="Invalid repository name format"):
        validate_repo_name("/invalid")

    with pytest.raises(ValueError, match="Invalid repository name format"):
        validate_repo_name("invalid/repo/extra")

    with pytest.raises(ValueError, match="Invalid repository name format"):
        validate_repo_name("")

    with pytest.raises(ValueError, match="Invalid repository name format"):
        validate_repo_name("owner/repo with spaces")


# -- get_pr_diff tests --


def _make_github_service():
    """Create a GitHubService with mocked GitHub client."""
    with patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}):
        with patch("mcp_server.services.github_service.Github"):
            svc = GitHubService()
    return svc


def _make_mock_pr_file(
    filename="src/main.py",
    status="modified",
    additions=10,
    deletions=5,
    changes=15,
    patch="@@ -1,5 +1,10 @@\n+added line",
    sha="abc123",
    previous_filename=None,
):
    """Create a mock PullRequestFile object."""
    pr_file = MagicMock()
    pr_file.filename = filename
    pr_file.status = status
    pr_file.additions = additions
    pr_file.deletions = deletions
    pr_file.changes = changes
    pr_file.patch = patch
    pr_file.sha = sha
    pr_file.previous_filename = previous_filename
    return pr_file


def _make_mock_pr(
    number=42,
    title="Test PR",
    state="open",
    merged=False,
    base_ref="main",
    head_ref="feature-branch",
    additions=10,
    deletions=5,
    changed_files=1,
    files=None,
):
    """Create a mock PullRequest object."""
    mock_pr = MagicMock()
    mock_pr.number = number
    mock_pr.title = title
    mock_pr.state = state
    mock_pr.merged = merged
    mock_pr.base.ref = base_ref
    mock_pr.head.ref = head_ref
    mock_pr.additions = additions
    mock_pr.deletions = deletions
    mock_pr.changed_files = changed_files
    mock_pr.html_url = f"https://github.com/test-org/test-repo/pull/{number}"
    mock_pr.get_files.return_value = files if files is not None else []
    return mock_pr


def test_get_pr_diff_basic():
    """Test basic PR diff retrieval."""
    svc = _make_github_service()

    mock_file = _make_mock_pr_file()
    mock_pr = _make_mock_pr(files=[mock_file])

    mock_repo = MagicMock()
    mock_repo.get_pull.return_value = mock_pr
    svc.github.get_repo.return_value = mock_repo

    result = svc.get_pr_diff("test-org/test-repo", 42)

    assert result["number"] == 42
    assert result["title"] == "Test PR"
    assert result["state"] == "open"
    assert result["merged"] is False
    assert result["base_ref"] == "main"
    assert result["head_ref"] == "feature-branch"
    assert result["additions"] == 10
    assert result["deletions"] == 5
    assert result["changed_files"] == 1
    assert len(result["files"]) == 1
    assert result["files"][0]["filename"] == "src/main.py"
    assert result["files"][0]["status"] == "modified"
    assert result["files"][0]["patch"] == "@@ -1,5 +1,10 @@\n+added line"
    assert result["files_returned"] == 1
    assert result["total_files"] == 1
    assert "truncated" not in result


def test_get_pr_diff_binary_file():
    """Test that binary files have null patch."""
    svc = _make_github_service()

    mock_file = _make_mock_pr_file(
        filename="image.png",
        status="added",
        additions=0,
        deletions=0,
        changes=0,
        patch=None,
        sha="def456",
    )
    mock_pr = _make_mock_pr(
        number=1,
        title="Binary change",
        additions=0,
        deletions=0,
        changed_files=1,
        files=[mock_file],
    )

    mock_repo = MagicMock()
    mock_repo.get_pull.return_value = mock_pr
    svc.github.get_repo.return_value = mock_repo

    result = svc.get_pr_diff("test-org/test-repo", 1)

    assert result["files"][0]["filename"] == "image.png"
    assert result["files"][0]["patch"] is None


def test_get_pr_diff_renamed_file():
    """Test that renamed files include previous_filename."""
    svc = _make_github_service()

    mock_file = _make_mock_pr_file(
        filename="new_name.py",
        status="renamed",
        previous_filename="old_name.py",
        patch="",
    )
    mock_pr = _make_mock_pr(
        number=2,
        title="Rename file",
        state="closed",
        merged=True,
        changed_files=1,
        files=[mock_file],
    )

    mock_repo = MagicMock()
    mock_repo.get_pull.return_value = mock_pr
    svc.github.get_repo.return_value = mock_repo

    result = svc.get_pr_diff("test-org/test-repo", 2)

    assert result["files"][0]["previous_filename"] == "old_name.py"
    assert result["merged"] is True


def test_get_pr_diff_truncation():
    """Test that files are truncated when exceeding max_files."""
    svc = _make_github_service()

    mock_files = [
        _make_mock_pr_file(filename=f"file{i}.py", sha=f"sha{i}") for i in range(5)
    ]
    mock_pr = _make_mock_pr(
        number=3,
        title="Large PR",
        additions=100,
        deletions=50,
        changed_files=5,
        files=mock_files,
    )

    mock_repo = MagicMock()
    mock_repo.get_pull.return_value = mock_pr
    svc.github.get_repo.return_value = mock_repo

    result = svc.get_pr_diff("test-org/test-repo", 3, max_files=2)

    assert result["files_returned"] == 2
    assert result["total_files"] == 5
    assert result["truncated"] is True
    assert "2 of 5" in result["truncation_message"]
    assert len(result["files"]) == 2


def test_get_pr_diff_no_previous_filename_when_none():
    """Test that previous_filename is omitted when not a rename."""
    svc = _make_github_service()

    mock_file = _make_mock_pr_file(previous_filename=None)
    mock_pr = _make_mock_pr(changed_files=1, files=[mock_file])

    mock_repo = MagicMock()
    mock_repo.get_pull.return_value = mock_pr
    svc.github.get_repo.return_value = mock_repo

    result = svc.get_pr_diff("test-org/test-repo", 4)

    assert "previous_filename" not in result["files"][0]


def test_get_pr_diff_github_exception():
    """Test that GithubException is handled properly."""
    svc = _make_github_service()

    mock_repo = MagicMock()
    mock_repo.get_pull.side_effect = GithubException(
        404, {"message": "Not Found"}, None
    )
    svc.github.get_repo.return_value = mock_repo

    with pytest.raises(Exception, match="GitHub API error"):
        svc.get_pr_diff("test-org/test-repo", 999)


def test_get_pr_diff_empty_pr():
    """Test PR with no changed files."""
    svc = _make_github_service()

    mock_pr = _make_mock_pr(
        number=5,
        title="Empty PR",
        additions=0,
        deletions=0,
        changed_files=0,
        files=[],
    )

    mock_repo = MagicMock()
    mock_repo.get_pull.return_value = mock_pr
    svc.github.get_repo.return_value = mock_repo

    result = svc.get_pr_diff("test-org/test-repo", 5)

    assert result["files"] == []
    assert result["files_returned"] == 0
    assert result["total_files"] == 0
    assert "truncated" not in result


# -- rate limit tests --

_RATE_LIMIT_HEADERS = {
    "x-ratelimit-reset": "9999999999",
    "x-ratelimit-remaining": "0",
    "x-ratelimit-limit": "30",
}


@pytest.mark.unit
def test_rate_limit_exceeded_search_issues():
    """Test that RateLimitExceededException surfaces a clear error with reset time."""
    svc = _make_github_service()
    svc.github.search_issues.side_effect = RateLimitExceededException(
        403, {}, _RATE_LIMIT_HEADERS
    )

    with pytest.raises(Exception, match="rate limit exceeded"):
        svc.search_issues("is:issue repo:test-org/test-repo")

    try:
        svc.search_issues("is:issue repo:test-org/test-repo")
    except Exception as exc:
        assert "resets at" in str(exc)
        assert "0/30" in str(exc)


@pytest.mark.unit
def test_rate_limit_exceeded_get_issue():
    """Test that RateLimitExceededException is raised from get_issue."""
    svc = _make_github_service()
    mock_repo = MagicMock()
    mock_repo.get_issue.side_effect = RateLimitExceededException(
        403, {}, _RATE_LIMIT_HEADERS
    )
    svc.github.get_repo.return_value = mock_repo

    with pytest.raises(Exception, match="rate limit exceeded"):
        svc.get_issue("test-org/test-repo", 1)


@pytest.mark.unit
def test_rate_limit_exceeded_get_pr_diff():
    """Test that RateLimitExceededException is raised from get_pr_diff."""
    svc = _make_github_service()
    mock_repo = MagicMock()
    mock_repo.get_pull.side_effect = RateLimitExceededException(
        403, {}, _RATE_LIMIT_HEADERS
    )
    svc.github.get_repo.return_value = mock_repo

    with pytest.raises(Exception, match="rate limit exceeded"):
        svc.get_pr_diff("test-org/test-repo", 42)


@pytest.mark.unit
def test_rate_limit_exceeded_get_repository_info():
    """Test that RateLimitExceededException is raised from get_repository_info."""
    svc = _make_github_service()
    svc.github.get_repo.side_effect = RateLimitExceededException(
        403, {}, _RATE_LIMIT_HEADERS
    )

    with pytest.raises(Exception, match="rate limit exceeded"):
        svc.get_repository_info("test-org/test-repo")


@pytest.mark.unit
def test_rate_limit_exceeded_no_headers():
    """Test graceful fallback when rate limit exception has no headers."""
    svc = _make_github_service()
    svc.github.get_repo.side_effect = RateLimitExceededException(403, {}, None)

    with pytest.raises(Exception, match="rate limit exceeded") as exc_info:
        svc.get_repository_info("test-org/test-repo")

    # Should not include reset time info when headers are absent
    assert "resets at" not in str(exc_info.value)


@pytest.mark.unit
def test_rate_limit_not_swallowed_in_get_comments():
    """Test that RateLimitExceededException is not swallowed in _get_comments."""
    svc = _make_github_service()
    mock_issue = MagicMock()
    mock_issue.get_comments.side_effect = RateLimitExceededException(
        403, {}, _RATE_LIMIT_HEADERS
    )

    with pytest.raises(RateLimitExceededException):
        svc._get_comments(mock_issue, 10)


@pytest.mark.unit
def test_get_rate_limit_status_success():
    """Test get_rate_limit_status returns correctly structured data."""
    svc = _make_github_service()

    reset_dt = datetime(2026, 3, 18, 12, 0, tzinfo=UTC)

    mock_core = MagicMock()
    mock_core.limit = 5000
    mock_core.remaining = 4800
    mock_core.used = 200
    mock_core.reset = reset_dt

    mock_search = MagicMock()
    mock_search.limit = 30
    mock_search.remaining = 28
    mock_search.used = 2
    mock_search.reset = reset_dt

    mock_rl = MagicMock()
    mock_rl.resources.core = mock_core
    mock_rl.resources.search = mock_search
    svc.github.get_rate_limit.return_value = mock_rl

    result = svc.get_rate_limit_status()

    assert result["core"]["limit"] == 5000
    assert result["core"]["remaining"] == 4800
    assert result["core"]["used"] == 200
    assert result["core"]["reset"] == reset_dt.isoformat()
    assert result["search"]["limit"] == 30
    assert result["search"]["remaining"] == 28
    assert result["search"]["used"] == 2
    assert result["search"]["reset"] == reset_dt.isoformat()


@pytest.mark.unit
def test_get_rate_limit_status_github_exception():
    """Test that GithubException from get_rate_limit propagates correctly."""
    svc = _make_github_service()
    svc.github.get_rate_limit.side_effect = GithubException(
        500, {"message": "Server error"}, None
    )

    with pytest.raises(Exception, match="GitHub API error"):
        svc.get_rate_limit_status()
