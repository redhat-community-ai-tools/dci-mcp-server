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

import pytest

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
