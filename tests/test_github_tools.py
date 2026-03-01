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

from unittest.mock import MagicMock, patch

import pytest
from github.GithubException import GithubException

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
