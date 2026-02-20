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

"""Unit tests for Red Hat Support Case tools and service."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from mcp_server.tools.support_case_tools import validate_case_number

# -- Anonymized test fixtures based on real API response structure --

SAMPLE_CASE_RESPONSE = {
    "apiReturnCode": 200,
    "caseAutomationEnabled": False,
    "caseSummary": "Test case summary with technical details.",
    "collaborationScore": 1452.0,
    "createdBySSOName": "testuser1",
    "critSit": False,
    "entitlementId": "550Hn00000XXXXXXIXX",
    "externalLock": False,
    "internalStatus": "Closed",
    "isPrivate": False,
    "resolution": "Resolved: Errata",
    "resolvedAt": "2025-04-25T11:55:49Z",
    "externalTrackers": [
        {
            "caseNumber": "01234567",
            "caseURI": "https://access.redhat.com/support/cases/01234567",
            "createdAt": "2025-03-19T17:39:54Z",
            "establishedBy": "rhn-support-testuser",
            "resourceKey": "TESTBUGS-12345",
            "resourceURL": "https://issues.redhat.com/browse/TESTBUGS-12345",
            "status": "Closed",
            "system": "Jira",
            "title": "Test bug title for documentation issue",
        }
    ],
    "createdById": "Test User",
    "createdDate": "2025-03-13T13:25:21Z",
    "lastModifiedById": "Test Engineer",
    "lastModifiedDate": "2025-04-25T11:57:07Z",
    "lastClosedAt": "2025-04-25T11:55:51Z",
    "id": "500Hn00001XXXXXXIXX",
    "uri": "https://access.redhat.com/hydra/rest/v1/cases/01234567",
    "summary": "Test case: documentation does not match behavior",
    "actionPlan": "NA",
    "description": "The documentation is out of date and does not match the behavior.",
    "status": "Closed",
    "product": "OpenShift Container Platform",
    "version": "4.18",
    "caseType": "Defect / Bug",
    "accountNumberRef": "1234567",
    "openshiftClusterID": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "customerEscalation": False,
    "contactName": "Test Contact",
    "contactSSOName": "testcontact",
    "origin": "Web",
    "ownerId": "Test Owner",
    "severity": "2 (High)",
    "contactIsPartner": False,
    "apiTags": ["shift_SR-IOV", "shift_telco5g"],
    "groupNumber": "12345",
    "groupName": "Test Group",
    "comments": [
        {
            "doNotChangeSBT": False,
            "isPublic": True,
            "visibility": "Customer",
            "id": "a0aHn00000XXXXXXIXX",
            "caseNumber": "01234567",
            "commentBody": "This is a test comment on the case.",
            "createdDate": "2025-04-25T11:55:50Z",
            "createdByType": "Associate",
            "isDraft": False,
            "lastModifiedById": "Test Engineer",
            "lastModifiedDate": "2025-04-25T11:55:49Z",
            "publishedDate": "2025-04-25T11:55:49Z",
            "createdBy": "Test Engineer",
            "contentType": "plaintext",
            "doNotChangeStatus": False,
        }
    ],
    "notifiedUsers": [],
    "entitlementSla": "STANDARD",
    "fts": False,
    "sbrGroups": ["test-sbr-group"],
    "caseLanguage": "en",
    "environment": "On all test servers with 4.18",
    "caseNumber": "01234567",
    "isClosed": True,
    "caseResourceLinks": [],
    "bugzillas": [],
    "recordTypeName": "Closed Case Record",
}

SAMPLE_COMMENTS_RESPONSE = [
    {
        "doNotChangeSBT": False,
        "isPublic": True,
        "visibility": "Customer",
        "id": "a0aHn00000XXXXXXIXX",
        "caseNumber": "01234567",
        "commentBody": "This is a test comment on the case.",
        "createdDate": "2025-04-25T11:55:50Z",
        "createdByType": "Associate",
        "isDraft": False,
        "lastModifiedById": "Test Engineer",
        "lastModifiedDate": "2025-04-25T11:55:49Z",
        "publishedDate": "2025-04-25T11:55:49Z",
        "createdBy": "Test Engineer",
        "contentType": "plaintext",
        "doNotChangeStatus": False,
    },
    {
        "doNotChangeSBT": False,
        "isPublic": True,
        "visibility": "Customer",
        "id": "a0aHn00000YYYYYIXX",
        "caseNumber": "01234567",
        "commentBody": "A follow-up comment with more details.",
        "createdDate": "2025-04-10T13:22:03Z",
        "createdByType": "Associate",
        "isDraft": False,
        "lastModifiedById": "Another Engineer",
        "lastModifiedDate": "2025-04-10T13:22:03Z",
        "publishedDate": "2025-04-10T13:22:03Z",
        "createdBy": "Another Engineer",
        "contentType": "plaintext",
        "doNotChangeStatus": False,
    },
]

SAMPLE_ATTACHMENTS_RESPONSE = [
    {
        "caseNumber": "01234567",
        "uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "checksum": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "createdDate": "2025-03-14T09:38:17Z",
        "createdBy": "Test User",
        "fileName": "must-gather.tar",
        "fileType": "application/x-gtar",
        "id": "a09Hn00000XXXXXXIXX",
        "isArchived": False,
        "isDeprecated": False,
        "isPrivate": False,
        "lastModifiedDate": "2025-03-14T09:38:17Z",
        "link": "https://attachments.access.redhat.com/hydra/rest/cases/01234567/attachments/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "modifiedBy": "Test User",
        "size": 782530560,
        "sizeKB": 764190.0,
        "downloadRestricted": False,
    }
]

SAMPLE_SEARCH_RESPONSE = {
    "case": [
        {
            "caseNumber": "01234567",
            "summary": "Test case: documentation does not match behavior",
            "status": "Closed",
            "severity": "2 (High)",
            "product": "OpenShift Container Platform",
            "version": "4.18",
            "createdDate": "2025-03-13T13:25:21Z",
        },
        {
            "caseNumber": "07654321",
            "summary": "Another test case for search results",
            "status": "Open",
            "severity": "3 (Normal)",
            "product": "OpenShift Container Platform",
            "version": "4.17",
            "createdDate": "2025-02-01T10:00:00Z",
        },
    ]
}

SAMPLE_TOKEN_RESPONSE = {
    "access_token": "test-access-token-12345",
    "expires_in": 900,
    "token_type": "Bearer",
}


# -- Validation tests --


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


# -- Service tests with mocked HTTP --


def _mock_response(status_code: int, json_data: dict | list) -> httpx.Response:
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://test.example.com"),
    )


@pytest.fixture
def mock_env(monkeypatch):
    """Set OFFLINE_TOKEN env var for service instantiation."""
    monkeypatch.setenv("OFFLINE_TOKEN", "test-offline-token")


@pytest.mark.asyncio
async def test_get_case_success(mock_env):
    """Test successful case retrieval."""
    from mcp_server.services.support_case_service import SupportCaseService

    svc = SupportCaseService()
    svc._access_token = "cached-token"
    svc._token_expires_at = 9999999999.0

    with patch.object(svc, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(200, SAMPLE_CASE_RESPONSE)
        result = await svc.get_case("01234567")

    assert result["caseNumber"] == "01234567"
    assert result["status"] == "Closed"
    assert result["product"] == "OpenShift Container Platform"
    assert result["severity"] == "2 (High)"
    assert result["url"] == "https://access.redhat.com/support/cases/#/case/01234567"
    assert len(result["comments"]) == 1
    mock_req.assert_called_once_with("GET", "/v1/cases/01234567")


@pytest.mark.asyncio
async def test_get_case_not_found(mock_env):
    """Test 404 handling for case retrieval."""
    from mcp_server.services.support_case_service import SupportCaseService

    svc = SupportCaseService()
    svc._access_token = "cached-token"
    svc._token_expires_at = 9999999999.0

    with patch.object(svc, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(404, {"message": "Not found"})
        with pytest.raises(Exception, match="Case 99999999 not found"):
            await svc.get_case("99999999")


@pytest.mark.asyncio
async def test_get_case_access_denied(mock_env):
    """Test 403 handling for case retrieval."""
    from mcp_server.services.support_case_service import SupportCaseService

    svc = SupportCaseService()
    svc._access_token = "cached-token"
    svc._token_expires_at = 9999999999.0

    with patch.object(svc, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(403, {"message": "Forbidden"})
        with pytest.raises(Exception, match="Access denied"):
            await svc.get_case("01234567")


@pytest.mark.asyncio
async def test_get_case_comments_success(mock_env):
    """Test successful comments retrieval."""
    from mcp_server.services.support_case_service import SupportCaseService

    svc = SupportCaseService()
    svc._access_token = "cached-token"
    svc._token_expires_at = 9999999999.0

    with patch.object(svc, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(200, SAMPLE_COMMENTS_RESPONSE)
        result = await svc.get_case_comments("01234567")

    assert len(result) == 2
    assert result[0]["commentBody"] == "This is a test comment on the case."
    assert result[1]["createdBy"] == "Another Engineer"
    mock_req.assert_called_once_with("GET", "/v1/cases/01234567/comments", params={})


@pytest.mark.asyncio
async def test_get_case_comments_with_dates(mock_env):
    """Test comments retrieval with date filters."""
    from mcp_server.services.support_case_service import SupportCaseService

    svc = SupportCaseService()
    svc._access_token = "cached-token"
    svc._token_expires_at = 9999999999.0

    with patch.object(svc, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(200, [SAMPLE_COMMENTS_RESPONSE[0]])
        result = await svc.get_case_comments(
            "01234567", start_date="2025-04-20", end_date="2025-04-30"
        )

    assert len(result) == 1
    mock_req.assert_called_once_with(
        "GET",
        "/v1/cases/01234567/comments",
        params={"startDate": "2025-04-20", "endDate": "2025-04-30"},
    )


@pytest.mark.asyncio
async def test_get_case_comments_not_found(mock_env):
    """Test 404 handling for comments retrieval."""
    from mcp_server.services.support_case_service import SupportCaseService

    svc = SupportCaseService()
    svc._access_token = "cached-token"
    svc._token_expires_at = 9999999999.0

    with patch.object(svc, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(404, {"message": "Not found"})
        with pytest.raises(Exception, match="Case 99999999 not found"):
            await svc.get_case_comments("99999999")


@pytest.mark.asyncio
async def test_search_cases_success(mock_env):
    """Test successful case search."""
    from mcp_server.services.support_case_service import SupportCaseService

    svc = SupportCaseService()
    svc._access_token = "cached-token"
    svc._token_expires_at = 9999999999.0

    with patch.object(svc, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(200, SAMPLE_SEARCH_RESPONSE)
        result = await svc.search_cases(
            {"maxResults": 50, "keyword": "documentation", "status": "Closed"}
        )

    assert "case" in result
    assert len(result["case"]) == 2
    assert result["case"][0]["caseNumber"] == "01234567"
    mock_req.assert_called_once_with(
        "POST",
        "/v1/cases/filter",
        json={"maxResults": 50, "keyword": "documentation", "status": "Closed"},
    )


@pytest.mark.asyncio
async def test_list_case_attachments_success(mock_env):
    """Test successful attachments listing."""
    from mcp_server.services.support_case_service import SupportCaseService

    svc = SupportCaseService()
    svc._access_token = "cached-token"
    svc._token_expires_at = 9999999999.0

    with patch.object(svc, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(200, SAMPLE_ATTACHMENTS_RESPONSE)
        result = await svc.list_case_attachments("01234567")

    assert len(result) == 1
    assert result[0]["fileName"] == "must-gather.tar"
    assert result[0]["size"] == 782530560
    mock_req.assert_called_once_with("GET", "/cases/01234567/attachments/")


@pytest.mark.asyncio
async def test_list_case_attachments_not_found(mock_env):
    """Test 404 handling for attachments listing."""
    from mcp_server.services.support_case_service import SupportCaseService

    svc = SupportCaseService()
    svc._access_token = "cached-token"
    svc._token_expires_at = 9999999999.0

    with patch.object(svc, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(404, {"message": "Not found"})
        with pytest.raises(Exception, match="Case 99999999 not found"):
            await svc.list_case_attachments("99999999")


@pytest.mark.asyncio
async def test_token_exchange(mock_env):
    """Test the token exchange flow."""
    from mcp_server.services.support_case_service import SupportCaseService

    svc = SupportCaseService()
    assert svc._access_token is None

    mock_response = _mock_response(200, SAMPLE_TOKEN_RESPONSE)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        token = await svc._get_access_token()

    assert token == "test-access-token-12345"
    assert svc._access_token == "test-access-token-12345"
    mock_client.post.assert_called_once_with(
        SupportCaseService.SSO_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": "rhsm-api",
            "refresh_token": "test-offline-token",
        },
    )


@pytest.mark.asyncio
async def test_token_caching(mock_env):
    """Test that cached tokens are reused."""
    from mcp_server.services.support_case_service import SupportCaseService

    svc = SupportCaseService()
    svc._access_token = "cached-token"
    svc._token_expires_at = 9999999999.0  # Far in the future

    # Should return cached token without making any HTTP calls
    token = await svc._get_access_token()
    assert token == "cached-token"


@pytest.mark.asyncio
async def test_service_missing_token():
    """Test that service raises ValueError when OFFLINE_TOKEN is not set."""
    import os

    env = os.environ.copy()
    env.pop("OFFLINE_TOKEN", None)

    with patch.dict(os.environ, env, clear=True):
        from mcp_server.services.support_case_service import SupportCaseService

        with pytest.raises(ValueError, match="OFFLINE_TOKEN"):
            SupportCaseService()


@pytest.mark.asyncio
async def test_request_retries_on_401(mock_env):
    """Test that _request retries once on 401 response."""
    from mcp_server.services.support_case_service import SupportCaseService

    svc = SupportCaseService()
    svc._access_token = "expired-token"
    svc._token_expires_at = 9999999999.0

    response_401 = _mock_response(401, {"message": "JWT expired"})
    response_200 = _mock_response(200, SAMPLE_CASE_RESPONSE)

    mock_token_response = _mock_response(200, SAMPLE_TOKEN_RESPONSE)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        # First request returns 401, token refresh, second request returns 200
        mock_client.request.side_effect = [response_401, response_200]
        mock_client.post.return_value = mock_token_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        response = await svc._request("GET", "/v1/cases/01234567")

    assert response.status_code == 200
    assert mock_client.request.call_count == 2
    # Token should have been refreshed
    assert svc._access_token == "test-access-token-12345"
