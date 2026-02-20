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

"""Unit tests for Red Hat Support Case tools."""

import pytest

from mcp_server.tools.support_case_tools import validate_case_number


def test_validate_case_number_valid():
    """Test validation of valid case numbers."""
    assert validate_case_number("03619625") == "03619625"
    assert validate_case_number("12345678") == "12345678"
    assert validate_case_number("00001") == "00001"
    assert validate_case_number("1234567890") == "1234567890"


def test_validate_case_number_with_whitespace():
    """Test validation trims whitespace."""
    assert validate_case_number("  03619625  ") == "03619625"
    assert validate_case_number("\t03619625\n") == "03619625"


def test_validate_case_number_invalid():
    """Test validation rejects invalid case numbers."""
    with pytest.raises(ValueError, match="Invalid case number format"):
        validate_case_number("invalid")

    with pytest.raises(ValueError, match="Invalid case number format"):
        validate_case_number("abc12345")

    with pytest.raises(ValueError, match="Invalid case number format"):
        validate_case_number("1234")  # Too short

    with pytest.raises(ValueError, match="Invalid case number format"):
        validate_case_number("")

    with pytest.raises(ValueError, match="Invalid case number format"):
        validate_case_number("123-456-789")

    with pytest.raises(ValueError, match="Invalid case number format"):
        validate_case_number("12345678901")  # Too long (11 digits)
