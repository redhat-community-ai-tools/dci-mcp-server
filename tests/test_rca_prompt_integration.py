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

"""Integration tests for the RCA prompt dynamic section selection.

These tests use real DCI job IDs to verify that the RCA prompt renders
the correct job-type guidance, file inventory, and job context sections.
Tests that hit the DCI API require credentials and are skipped otherwise.
"""

import pytest

from mcp_server.config import has_dci_credentials
from mcp_server.prompts.render import list_prompts, render_prompt

_has_dci_credentials = has_dci_credentials()

requires_dci = pytest.mark.skipif(
    not _has_dci_credentials,
    reason="DCI credentials not available (DCI_CLIENT_ID / DCI_API_SECRET)",
)


# ---------------------------------------------------------------------------
# Real DCI job IDs for each job-type classification
# ---------------------------------------------------------------------------

# install_type:acm tag → classified as "acm"
ACM_JOB_ID = "7fb9d2e5-c5d0-4134-8416-02c79af4617d"

# ztp tag + install_type:abi (no install_type:acm) → classified as "ztp"
ZTP_JOB_ID = "78738e75-d359-4a86-9522-489522ceaa2e"

# upgrade tag → classified as "upgrade"
UPGRADE_JOB_ID = "bdbf3496-fabb-43ee-a2f9-4d699a3f626e"

# agent:openshift-app tag → classified as "day2" (also has sno, but day2 wins)
DAY2_JOB_ID = "f94beb63-3269-4d91-a27e-357245d7631d"

# sno + install_type:sno (no acm/ztp/upgrade/day2 tags) → classified as "sno"
SNO_JOB_ID = "d232e2e5-99e2-4156-b20f-360e7ad8f801"

# No special tags (virt, daily, install_type:abi) → classified as "standard"
STANDARD_JOB_ID = "bd8f228e-302c-4298-96e9-a429a6547d71"


# ---------------------------------------------------------------------------
# Integration tests — real DCI API calls
# ---------------------------------------------------------------------------


@pytest.mark.integration
@requires_dci
class TestRcaPromptJobTypeSelection:
    """Verify that real DCI jobs produce the correct dynamic RCA prompt."""

    @pytest.mark.asyncio
    async def test_acm_job_produces_acm_guidance(self):
        result = await render_prompt("rca", dci_job_id=ACM_JOB_ID)
        assert "Job-Type Guidance: ACM" in result
        assert "ManagedCluster" in result
        assert "Job Context" in result
        assert "Job-Type Guidance: ZTP" not in result
        assert "Job-Type Guidance: Upgrade" not in result

    @pytest.mark.asyncio
    async def test_ztp_job_produces_ztp_guidance(self):
        result = await render_prompt("rca", dci_job_id=ZTP_JOB_ID)
        assert "Job-Type Guidance: ZTP" in result
        assert "SiteConfig" in result
        assert "TALM" in result
        assert "Job Context" in result
        assert "ManagedCluster" not in result

    @pytest.mark.asyncio
    async def test_upgrade_job_produces_upgrade_guidance(self):
        result = await render_prompt("rca", dci_job_id=UPGRADE_JOB_ID)
        assert "Job-Type Guidance: Upgrade" in result
        assert "ClusterVersion" in result
        assert "Job Context" in result
        assert "ManagedCluster" not in result
        assert "SiteConfig" not in result

    @pytest.mark.asyncio
    async def test_day2_job_produces_day2_guidance(self):
        result = await render_prompt("rca", dci_job_id=DAY2_JOB_ID)
        assert "Job-Type Guidance: Day-2" in result
        assert "Job Context" in result
        assert "ManagedCluster" not in result
        assert "SiteConfig" not in result

    @pytest.mark.asyncio
    async def test_sno_job_produces_sno_guidance(self):
        result = await render_prompt("rca", dci_job_id=SNO_JOB_ID)
        assert "Job-Type Guidance: SNO" in result
        assert "Single Node" in result
        assert "Job Context" in result
        assert "ManagedCluster" not in result
        assert "SiteConfig" not in result

    @pytest.mark.asyncio
    async def test_standard_job_has_no_job_type_guidance(self):
        result = await render_prompt("rca", dci_job_id=STANDARD_JOB_ID)
        assert "Job Context" in result
        assert "Job-Type Guidance:" not in result
        assert "ManagedCluster" not in result
        assert "SiteConfig" not in result

    @pytest.mark.asyncio
    async def test_dynamic_prompt_has_file_section(self):
        """Any real job should produce a file inventory section."""
        result = await render_prompt("rca", dci_job_id=ACM_JOB_ID)
        assert "Available Files" in result

    @pytest.mark.asyncio
    async def test_dynamic_prompt_has_methodology(self):
        """The shared RCA methodology should always be present."""
        result = await render_prompt("rca", dci_job_id=ACM_JOB_ID)
        assert "5 Whys" in result
        assert "Adversarial Challenge" in result


# ---------------------------------------------------------------------------
# Unit tests — no DCI credentials needed
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRenderPromptLibrary:
    """Tests for the render_prompt library functions."""

    def test_list_prompts_includes_all(self):
        names = list_prompts()
        assert "rca" in names
        assert "weekly" in names
        assert "biweekly" in names
        assert "quarterly" in names

    @pytest.mark.asyncio
    async def test_render_weekly_prompt(self):
        result = await render_prompt("weekly", subject="test-team")
        assert "test-team" in result
        assert "week" in result.lower()

    @pytest.mark.asyncio
    async def test_render_unknown_prompt_raises(self):
        with pytest.raises(ValueError, match="Unknown prompt 'nonexistent'"):
            await render_prompt("nonexistent")


# test_rca_prompt_integration.py ends here
