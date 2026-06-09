#
# Copyright (C) 2025-2026 Red Hat, Inc.
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

"""Unit tests for RCA prompt helpers and dynamic prompt generation."""

from unittest.mock import MagicMock, patch

import pytest

from mcp_server.prompts.prompts import (
    _build_file_section,
    _build_job_type_guidance,
    _classify_job_type,
    _fetch_job_files,
    _fetch_job_metadata,
    _prioritize_files,
)

# ---------------------------------------------------------------------------
# _classify_job_type
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClassifyJobType:
    """Tests for _classify_job_type()."""

    def test_acm_tag(self):
        assert _classify_job_type(["install_type:acm", "daily"]) == "acm"

    def test_acm_tag_case_insensitive(self):
        assert _classify_job_type(["install_type:ACM"]) == "acm"

    def test_ztp_tag(self):
        assert _classify_job_type(["ztp", "daily"]) == "ztp"

    def test_ztp_in_compound_tag(self):
        assert _classify_job_type(["pipeline:ztp-deploy"]) == "ztp"

    def test_upgrade_tag(self):
        assert _classify_job_type(["upgrade", "nightly"]) == "upgrade"

    def test_upgrade_in_compound_tag(self):
        assert _classify_job_type(["pipeline:upgrade-4.16-to-4.17"]) == "upgrade"

    def test_day2_agent_tag(self):
        assert _classify_job_type(["agent:openshift-app"]) == "day2"

    def test_day2_explicit_tag(self):
        assert _classify_job_type(["day2-workload"]) == "day2"

    def test_sno_tag(self):
        assert _classify_job_type(["sno", "ga"]) == "sno"

    def test_spoke_tag(self):
        assert _classify_job_type(["spoke"]) == "sno"

    def test_bespoke_does_not_match_spoke(self):
        """'bespoke' should not be classified as SNO via loose 'spoke' matching."""
        assert _classify_job_type(["bespoke"]) == "standard"

    def test_standard_no_tags(self):
        assert _classify_job_type([]) == "standard"

    def test_standard_unrelated_tags(self):
        assert _classify_job_type(["daily", "ga", "build:ga"]) == "standard"

    def test_acm_takes_priority_over_sno(self):
        """ACM should win when both acm and sno tags are present."""
        assert _classify_job_type(["install_type:acm", "sno"]) == "acm"

    def test_ztp_takes_priority_over_upgrade(self):
        """ZTP should win over upgrade in priority order."""
        assert _classify_job_type(["ztp", "upgrade"]) == "ztp"


# ---------------------------------------------------------------------------
# _prioritize_files
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPrioritizeFiles:
    """Tests for _prioritize_files()."""

    @staticmethod
    def _f(name, fid="id-1", size=1024, mime="text/plain"):
        return {"name": name, "id": fid, "size": size, "mime": mime}

    def test_ansible_log_is_p1(self):
        result = _prioritize_files([self._f("ansible.log")])
        assert len(result["P1"]) == 1
        assert result["P1"][0]["name"] == "ansible.log"

    def test_logjuicer_txt_is_p2(self):
        result = _prioritize_files([self._f("logjuicer.txt")])
        assert len(result["P2"]) == 1

    def test_logjuicer_omg_is_p3(self):
        result = _prioritize_files([self._f("logjuicer_omg.txt")])
        assert len(result["P3"]) == 1

    def test_logjuicer_omg_sno_is_p3(self):
        result = _prioritize_files([self._f("logjuicer_omg_SNO.txt")])
        assert len(result["P3"]) == 1

    def test_junit_mime_is_p4(self):
        result = _prioritize_files(
            [self._f("dci-openshift-agent", mime="application/junit")]
        )
        assert len(result["P4"]) == 1

    def test_junit_name_is_p4(self):
        result = _prioritize_files([self._f("results.junit", mime="application/junit")])
        assert len(result["P4"]) == 1

    def test_must_gather_is_p5(self):
        result = _prioritize_files([self._f("must_gather.tar.gz")])
        assert len(result["P5"]) == 1

    def test_sno_must_gather_is_p5(self):
        result = _prioritize_files([self._f("SNO_must_gather.tar.gz")])
        assert len(result["P5"]) == 1

    def test_events_txt_is_p6(self):
        result = _prioritize_files([self._f("events.txt")])
        assert len(result["P6"]) == 1

    def test_console_log_is_p6b(self):
        result = _prioritize_files([self._f("cluster4-master-0-console.log")])
        assert len(result["P6b"]) == 1

    def test_other_log_is_p7(self):
        result = _prioritize_files([self._f("custom_output.log")])
        assert len(result["P7"]) == 1

    def test_other_file_is_p8(self):
        result = _prioritize_files([self._f("config.yaml")])
        assert len(result["P8"]) == 1

    def test_failed_task_is_skipped(self):
        result = _prioritize_files([self._f("failed_task.txt")])
        total = sum(len(v) for v in result.values())
        assert total == 0

    def test_play_recap_is_skipped(self):
        result = _prioritize_files([self._f("play_recap")])
        total = sum(len(v) for v in result.values())
        assert total == 0

    def test_task_files_are_skipped(self):
        result = _prioritize_files([self._f("task_001")])
        total = sum(len(v) for v in result.values())
        assert total == 0

    def test_ansible_output_mime_is_skipped(self):
        """Files with application/x-ansible-output MIME are skipped."""
        for name in [
            "TASK [Remove logs directory]",
            "TASK [Failure]",
            "failed/TASK [Fail properly]",
            "skipped/TASK [Run agent cleanup]",
            "failed/PLAY RECAP",
            "PLAY [all]",
            "PLAYBOOK: site.yml",
        ]:
            result = _prioritize_files(
                [self._f(name, mime="application/x-ansible-output")]
            )
            total = sum(len(v) for v in result.values())
            assert total == 0, f"{name!r} should be skipped via MIME type"

    def test_dci_agent_junit_is_p4(self):
        """DCI agent files with application/junit MIME go to P4."""
        result = _prioritize_files(
            [self._f("dci-openshift-app-agent", mime="application/junit")]
        )
        assert len(result["P4"]) == 1

    def test_hardware_and_kernel_files_are_skipped(self):
        for name in ["hardware.json", "hardware.txt", "kernel.log", "kernel.config"]:
            result = _prioritize_files([self._f(name)])
            total = sum(len(v) for v in result.values())
            assert total == 0, f"{name!r} should be skipped"

    def test_mixed_file_list(self):
        """Full scenario with various file types and MIME types."""
        files = [
            self._f("ansible.log"),
            self._f("logjuicer.txt"),
            self._f("logjuicer_omg.txt"),
            self._f("logjuicer_omg_SNO.txt"),
            self._f("dci-openshift-agent", mime="application/junit"),
            self._f("must_gather.tar.gz", mime="application/x-gzip"),
            self._f("SNO_must_gather.tar.gz", mime="application/x-gzip"),
            self._f("events.txt"),
            self._f("cluster4-master-0-console.log"),
            self._f("custom.log"),
            self._f("config.yaml"),
            self._f("failed_task.txt"),
            self._f("play_recap"),
            self._f("TASK [Remove logs]", mime="application/x-ansible-output"),
            self._f("failed/TASK [Fail]", mime="application/x-ansible-output"),
            self._f("skipped/TASK [Run]", mime="application/x-ansible-output"),
        ]
        result = _prioritize_files(files)
        assert len(result["P1"]) == 1  # ansible.log
        assert len(result["P2"]) == 1  # logjuicer.txt
        assert len(result["P3"]) == 2  # logjuicer_omg*.txt
        assert len(result["P4"]) == 1  # dci-openshift-agent (junit)
        assert len(result["P5"]) == 2  # must_gather*
        assert len(result["P6"]) == 1  # events.txt
        assert len(result["P6b"]) == 1  # console.log
        assert len(result["P7"]) == 1  # custom.log
        assert len(result["P8"]) == 1  # config.yaml


# ---------------------------------------------------------------------------
# _build_job_type_guidance
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildJobTypeGuidance:
    """Tests for _build_job_type_guidance()."""

    def test_acm_guidance_mentions_managedcluster(self):
        guidance = _build_job_type_guidance("acm", [])
        assert "ManagedCluster" in guidance
        assert "hub/spoke" in guidance.lower() or "hub" in guidance.lower()

    def test_ztp_guidance_mentions_siteconfig(self):
        guidance = _build_job_type_guidance("ztp", [])
        assert "SiteConfig" in guidance
        assert "TALM" in guidance

    def test_upgrade_guidance_mentions_clusterversion(self):
        guidance = _build_job_type_guidance("upgrade", [])
        assert "ClusterVersion" in guidance

    def test_upgrade_guidance_includes_ocp_versions(self):
        components = [
            {"type": "ocp", "version": "4.16.3", "name": "OCP-4.16.3"},
            {"type": "storage", "version": "1.0", "name": "ocs"},
        ]
        guidance = _build_job_type_guidance("upgrade", components)
        assert "4.16.3" in guidance

    def test_day2_guidance_mentions_day2(self):
        guidance = _build_job_type_guidance("day2", [])
        assert "day-2" in guidance.lower() or "day2" in guidance.lower()

    def test_sno_guidance_mentions_single_node(self):
        guidance = _build_job_type_guidance("sno", [])
        assert "Single Node" in guidance or "single node" in guidance.lower()

    def test_standard_returns_empty(self):
        guidance = _build_job_type_guidance("standard", [])
        assert guidance == ""


# ---------------------------------------------------------------------------
# _build_file_section
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildFileSection:
    """Tests for _build_file_section()."""

    def test_empty_buckets(self):
        buckets = {
            k: [] for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P6b", "P7", "P8")
        }
        section = _build_file_section(buckets)
        assert "No files found" in section

    def test_file_ids_appear_in_output(self):
        buckets = {
            k: [] for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P6b", "P7", "P8")
        }
        buckets["P1"] = [{"name": "ansible.log", "id": "file-abc", "size": 2048}]
        section = _build_file_section(buckets)
        assert "file-abc" in section
        assert "ansible.log" in section

    def test_sequential_numbering(self):
        """Non-empty buckets should be numbered sequentially."""
        buckets = {
            k: [] for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P6b", "P7", "P8")
        }
        buckets["P1"] = [{"name": "ansible.log", "id": "a", "size": 1024}]
        buckets["P4"] = [{"name": "junit.xml", "id": "b", "size": 512}]
        section = _build_file_section(buckets)
        assert "### 1. Entry Point: ansible.log" in section
        assert "### 2. Test results (application/junit)" in section

    def test_omg_without_must_gather_has_no_implied_note(self):
        """No implied note — it would trigger wasteful tool calls."""
        buckets = {
            k: [] for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P6b", "P7", "P8")
        }
        buckets["P1"] = [{"name": "ansible.log", "id": "a", "size": 1024}]
        buckets["P3"] = [{"name": "logjuicer_omg.txt", "id": "b", "size": 512}]
        section = _build_file_section(buckets)
        assert "implied" not in section.lower()


# ---------------------------------------------------------------------------
# _fetch_job_metadata (with mocked service)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchJobMetadata:
    """Tests for _fetch_job_metadata()."""

    @patch("mcp_server.prompts.prompts.DCIJobService")
    def test_successful_fetch(self, mock_cls):
        mock_service = MagicMock()
        mock_cls.return_value = mock_service
        mock_service.search_jobs.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "id": "job-1",
                            "tags": ["daily", "install_type:acm"],
                            "components": [
                                {"type": "ocp", "name": "OCP", "version": "4.16.3"}
                            ],
                            "pipeline": {"name": "acm-deploy"},
                            "status_reason": "Task failed",
                            "status": "failure",
                            "topic": {"name": "OCP-4.16"},
                        }
                    }
                ]
            }
        }
        result = _fetch_job_metadata("job-1")
        assert result is not None
        assert result["tags"] == ["daily", "install_type:acm"]
        assert result["pipeline_name"] == "acm-deploy"
        assert result["status"] == "failure"

    @patch("mcp_server.prompts.prompts.DCIJobService")
    def test_empty_hits_returns_none(self, mock_cls):
        mock_service = MagicMock()
        mock_cls.return_value = mock_service
        mock_service.search_jobs.return_value = {"hits": {"hits": []}}
        assert _fetch_job_metadata("nonexistent") is None

    @patch("mcp_server.prompts.prompts.DCIJobService")
    def test_exception_returns_none(self, mock_cls):
        mock_cls.side_effect = Exception("connection error")
        assert _fetch_job_metadata("job-1") is None


# ---------------------------------------------------------------------------
# _fetch_job_files (with mocked service)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchJobFiles:
    """Tests for _fetch_job_files()."""

    @patch("mcp_server.prompts.prompts.DCIJobService")
    def test_successful_fetch(self, mock_cls):
        """Verify successful API call returns a list of file dicts."""
        mock_service = MagicMock()
        mock_cls.return_value = mock_service
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "files": [
                {"id": "f1", "name": "ansible.log", "size": 4096},
                {"id": "f2", "name": "junit.xml", "size": 512},
            ]
        }
        # Patch the dciclient import inside _fetch_job_files
        with patch("dciclient.v1.api.job.list_files", return_value=mock_response):
            result = _fetch_job_files("job-1")
        assert result is not None
        assert len(result) == 2
        assert result[0]["name"] == "ansible.log"

    @patch("mcp_server.prompts.prompts.DCIJobService")
    def test_exception_returns_none(self, mock_cls):
        """Verify API exception returns None (not empty list)."""
        mock_cls.side_effect = Exception("connection error")
        assert _fetch_job_files("job-1") is None

    @patch("mcp_server.prompts.prompts.DCIJobService")
    def test_api_failure_returns_none_not_empty_list(self, mock_cls):
        """Verify that API failures return None, not [], so the fallback
        to static prompt can trigger correctly."""
        mock_service = MagicMock()
        mock_cls.return_value = mock_service
        # Simulate the DCI API raising an exception (not swallowed)
        with patch(
            "dciclient.v1.api.job.list_files", side_effect=Exception("HTTP 500")
        ):
            result = _fetch_job_files("job-1")
        assert result is None


# ---------------------------------------------------------------------------
# rca() integration test (mocked services)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRcaPromptIntegration:
    """Integration tests for the rca() prompt function."""

    @pytest.mark.asyncio
    @patch("mcp_server.prompts.prompts._fetch_job_files")
    @patch("mcp_server.prompts.prompts._fetch_job_metadata")
    async def test_dynamic_prompt_with_metadata_and_files(self, mock_meta, mock_files):
        """When metadata and files are available, the prompt is dynamic."""
        mock_meta.return_value = {
            "tags": ["install_type:acm", "daily"],
            "components": [{"type": "ocp", "name": "OCP", "version": "4.16.3"}],
            "pipeline_name": "acm-deploy",
            "status_reason": "Task 'deploy' failed",
            "status": "failure",
            "topic_name": "OCP-4.16",
        }
        mock_files.return_value = [
            {"id": "f1", "name": "ansible.log", "size": 4096},
            {"id": "f2", "name": "logjuicer.txt", "size": 2048},
            {"id": "f3", "name": "logjuicer_omg.txt", "size": 1024},
            {"id": "f4", "name": "logjuicer_omg_SNO.txt", "size": 1024},
            {"id": "f5", "name": "junit.xml", "size": 512},
            {"id": "f6", "name": "must_gather.tar.gz", "size": 1048576},
        ]

        from mcp_server.prompts.prompts import register_prompts

        mcp = MagicMock()
        prompts_registered = {}

        def fake_prompt():
            def decorator(fn):
                prompts_registered[fn.__name__] = fn
                return fn

            return decorator

        mcp.prompt = fake_prompt
        register_prompts(mcp)

        rca_fn = prompts_registered["rca"]
        result = await rca_fn("job-abc-123")

        # Dynamic content checks
        assert "job-abc-123" in result
        assert "acm-deploy" in result
        assert "OCP-4.16" in result
        assert "failure" in result
        assert "Task 'deploy' failed" in result
        # File IDs should be referenced
        assert "f1" in result
        assert "f2" in result
        assert "f3" in result
        # ACM-specific guidance
        assert "ManagedCluster" in result
        # Methodology sections still present
        assert "5 Whys" in result
        assert "Adversarial Challenge" in result

    @pytest.mark.asyncio
    @patch("mcp_server.prompts.prompts._fetch_job_files")
    @patch("mcp_server.prompts.prompts._fetch_job_metadata")
    async def test_fallback_to_static_prompt(self, mock_meta, mock_files):
        """When both fetches fail, fall back to the static prompt."""
        mock_meta.return_value = None
        mock_files.return_value = None

        from mcp_server.prompts.prompts import register_prompts

        mcp = MagicMock()
        prompts_registered = {}

        def fake_prompt():
            def decorator(fn):
                prompts_registered[fn.__name__] = fn
                return fn

            return decorator

        mcp.prompt = fake_prompt
        register_prompts(mcp)

        rca_fn = prompts_registered["rca"]
        result = await rca_fn("job-xyz-789")

        # Static prompt should still work
        assert "job-xyz-789" in result
        assert "5 Whys" in result
        assert "Adversarial Challenge" in result
        # Should NOT have dynamic sections
        assert "Job Context" not in result
        assert "Available Files" not in result

    @pytest.mark.asyncio
    @patch("mcp_server.prompts.prompts._fetch_job_files")
    @patch("mcp_server.prompts.prompts._fetch_job_metadata")
    async def test_partial_failure_files_only(self, mock_meta, mock_files):
        """When metadata fails but files succeed, still build dynamic prompt."""
        mock_meta.return_value = None
        mock_files.return_value = [
            {"id": "f1", "name": "ansible.log", "size": 4096},
        ]

        from mcp_server.prompts.prompts import register_prompts

        mcp = MagicMock()
        prompts_registered = {}

        def fake_prompt():
            def decorator(fn):
                prompts_registered[fn.__name__] = fn
                return fn

            return decorator

        mcp.prompt = fake_prompt
        register_prompts(mcp)

        rca_fn = prompts_registered["rca"]
        result = await rca_fn("job-partial")

        # Should have dynamic file section
        assert "Available Files" in result
        assert "f1" in result
        # Should have job context even with defaults
        assert "Job Context" in result


# test_prompts.py ends here
