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

"""Unit tests for the RCA render-time triage auto-download helper."""

from unittest.mock import MagicMock, patch

import pytest

import mcp_server.prompts.prompts as prompts_mod

JOB_ID = "11111111-2222-3333-4444-555555555555"

BUCKETS = {
    "P1": [{"name": "ansible.log", "id": "id-ansible"}],
    "P2": [{"name": "logjuicer.txt", "id": "id-lj"}],
    "P3": [{"name": "logjuicer_omg.txt", "id": "id-omg"}],
    "P4": [{"name": "junit.xml", "id": "id-junit"}],
    # P5 must_gather must NOT be pre-downloaded (large, lazy).
    "P5": [{"name": "must_gather.tar.gz", "id": "id-mg"}],
    "P6": [{"name": "events.txt", "id": "id-events"}],
    # P8 supporting is outside the triage set.
    "P8": [{"name": "config.txt", "id": "id-cfg"}],
}

TRIAGE_NAMES = {
    "ansible.log",
    "logjuicer.txt",
    "logjuicer_omg.txt",
    "junit.xml",
    "events.txt",
}


@pytest.fixture
def mock_service(tmp_path):
    """Patch DCIFileService with a mock whose DOWNLOAD_ROOT is a real tmp dir."""
    with patch.object(prompts_mod, "DCIFileService") as mock_cls:
        inst = mock_cls.return_value
        inst.DOWNLOAD_ROOT = tmp_path
        inst.download_file = MagicMock(return_value="ok")
        yield inst


@pytest.mark.unit
def test_downloads_triage_set_and_skips_must_gather(monkeypatch, mock_service):
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")

    result = prompts_mod._autodownload_triage_files(JOB_ID, BUCKETS)

    requested = {
        call.args[2].split("/", 1)[1] for call in mock_service.download_file.mock_calls
    }
    assert requested == TRIAGE_NAMES
    assert "must_gather.tar.gz" not in requested
    assert "config.txt" not in requested
    assert set(result) == TRIAGE_NAMES


@pytest.mark.unit
def test_sse_transport_skips_download(monkeypatch, mock_service):
    monkeypatch.setenv("MCP_TRANSPORT", "sse")

    result = prompts_mod._autodownload_triage_files(JOB_ID, BUCKETS)

    assert result == []
    mock_service.download_file.assert_not_called()


@pytest.mark.unit
def test_idempotent_skips_existing_files(monkeypatch, mock_service, tmp_path):
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")
    job_dir = tmp_path / JOB_ID
    job_dir.mkdir()
    (job_dir / "ansible.log").write_text("already here")

    result = prompts_mod._autodownload_triage_files(JOB_ID, BUCKETS)

    requested = {
        call.args[2].split("/", 1)[1] for call in mock_service.download_file.mock_calls
    }
    assert "ansible.log" not in requested  # existing file not re-downloaded
    assert "ansible.log" in result  # but still reported as present
    assert set(result) == TRIAGE_NAMES


@pytest.mark.unit
def test_download_failure_is_graceful(monkeypatch, mock_service):
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")

    def flaky(job_id, file_id, rel):
        if file_id == "id-ansible":
            raise RuntimeError("boom")
        return "ok"

    mock_service.download_file.side_effect = flaky

    result = prompts_mod._autodownload_triage_files(JOB_ID, BUCKETS)

    # The failed file is not reported, but the others still download.
    assert "ansible.log" not in result
    assert set(result) == TRIAGE_NAMES - {"ansible.log"}


@pytest.mark.unit
def test_skips_entries_missing_name_or_id(monkeypatch, mock_service):
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")
    buckets = {
        "P1": [
            {"name": "ansible.log", "id": ""},  # missing id
            {"name": "", "id": "id-x"},  # missing name
            {"name": "good.txt", "id": "id-good"},
        ]
    }

    result = prompts_mod._autodownload_triage_files(JOB_ID, buckets)

    assert result == ["good.txt"]


@pytest.fixture
def mock_job_service(tmp_path):
    """Patch DCIJobService.get_job and DCIFileService.DOWNLOAD_ROOT."""
    with (
        patch.object(prompts_mod, "DCIJobService") as mock_job_cls,
        patch.object(prompts_mod.DCIFileService, "DOWNLOAD_ROOT", tmp_path),
    ):
        inst = mock_job_cls.return_value
        inst.get_job = MagicMock(
            return_value={"job": {"id": JOB_ID, "status": "failure"}}
        )
        yield inst, tmp_path


@pytest.mark.unit
def test_dumps_full_job_metadata(monkeypatch, mock_job_service):
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")
    inst, tmp_path = mock_job_service

    assert prompts_mod._dump_job_metadata(JOB_ID) is True

    dest = tmp_path / JOB_ID / "job-metadata.json"
    assert dest.exists()
    import json

    assert json.loads(dest.read_text()) == {"job": {"id": JOB_ID, "status": "failure"}}
    inst.get_job.assert_called_once_with(JOB_ID)


@pytest.mark.unit
def test_metadata_sse_transport_skips(monkeypatch, mock_job_service):
    monkeypatch.setenv("MCP_TRANSPORT", "sse")
    inst, tmp_path = mock_job_service

    assert prompts_mod._dump_job_metadata(JOB_ID) is False
    inst.get_job.assert_not_called()
    assert not (tmp_path / JOB_ID / "job-metadata.json").exists()


@pytest.mark.unit
def test_metadata_idempotent(monkeypatch, mock_job_service):
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")
    inst, tmp_path = mock_job_service
    job_dir = tmp_path / JOB_ID
    job_dir.mkdir()
    (job_dir / "job-metadata.json").write_text("{}")

    assert prompts_mod._dump_job_metadata(JOB_ID) is True
    inst.get_job.assert_not_called()  # existing file kept, no re-fetch


@pytest.mark.unit
def test_metadata_empty_result_not_written(monkeypatch, mock_job_service):
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")
    inst, tmp_path = mock_job_service
    inst.get_job.return_value = {}

    assert prompts_mod._dump_job_metadata(JOB_ID) is False
    assert not (tmp_path / JOB_ID / "job-metadata.json").exists()


@pytest.mark.unit
def test_metadata_fetch_failure_is_graceful(monkeypatch, mock_job_service):
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")
    inst, tmp_path = mock_job_service
    inst.get_job.side_effect = RuntimeError("boom")

    assert prompts_mod._dump_job_metadata(JOB_ID) is False
    assert not (tmp_path / JOB_ID / "job-metadata.json").exists()


def _make_must_gather_tar(path, wrapper="must_gather"):
    """Write a small tar.gz with a single top-level ``wrapper/`` dir."""
    import io
    import tarfile

    with tarfile.open(path, "w:gz") as tf:
        # the redundant top-level wrapper directory entry
        info = tarfile.TarInfo(wrapper)
        info.type = tarfile.DIRTYPE
        tf.addfile(info)
        for rel in ("timestamp", "inspect.local.1/namespaces/ns.yaml"):
            data = b"content"
            member = tarfile.TarInfo(f"{wrapper}/{rel}")
            member.size = len(data)
            tf.addfile(member, io.BytesIO(data))


MG_BUCKETS = {
    "P5": [
        {"name": "must_gather.tar.gz", "id": "id-mg"},
        {"name": "SNO_must_gather.tar.gz", "id": "id-sno"},
    ]
}


@pytest.fixture
def mock_mg_service(tmp_path):
    """Patch DCIFileService so download_file writes a real tar.gz fixture."""
    with patch.object(prompts_mod, "DCIFileService") as mock_cls:
        inst = mock_cls.return_value
        inst.DOWNLOAD_ROOT = tmp_path

        def fake_download(job_id, file_id, rel):
            dest = tmp_path / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            _make_must_gather_tar(dest)
            return str(dest)

        inst.download_file = MagicMock(side_effect=fake_download)
        yield inst, tmp_path


@pytest.mark.unit
def test_must_gather_downloaded_and_extracted(monkeypatch, mock_mg_service):
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")
    inst, tmp_path = mock_mg_service

    result = prompts_mod._autodownload_must_gather(JOB_ID, MG_BUCKETS)

    assert set(result) == {"must_gather", "SNO_must_gather"}
    for label in ("must_gather", "SNO_must_gather"):
        extracted = tmp_path / JOB_ID / label
        # wrapper stripped: content sits directly under the label dir
        assert (extracted / "timestamp").exists()
        assert (extracted / "inspect.local.1" / "namespaces" / "ns.yaml").exists()
        assert not (extracted / "must_gather").exists()  # no nested wrapper


@pytest.mark.unit
def test_must_gather_sse_transport_skips(monkeypatch, mock_mg_service):
    monkeypatch.setenv("MCP_TRANSPORT", "sse")
    inst, tmp_path = mock_mg_service

    result = prompts_mod._autodownload_must_gather(JOB_ID, MG_BUCKETS)

    assert result == []
    inst.download_file.assert_not_called()


@pytest.mark.unit
def test_must_gather_idempotent(monkeypatch, mock_mg_service):
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")
    inst, tmp_path = mock_mg_service
    (tmp_path / JOB_ID / "must_gather").mkdir(parents=True)
    (tmp_path / JOB_ID / "SNO_must_gather").mkdir()

    result = prompts_mod._autodownload_must_gather(JOB_ID, MG_BUCKETS)

    assert set(result) == {"must_gather", "SNO_must_gather"}
    inst.download_file.assert_not_called()  # both already extracted


@pytest.mark.unit
def test_must_gather_ignores_non_tar_gz(monkeypatch, mock_mg_service):
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")
    inst, tmp_path = mock_mg_service
    buckets = {"P5": [{"name": "must_gather.txt", "id": "id-x"}]}

    result = prompts_mod._autodownload_must_gather(JOB_ID, buckets)

    assert result == []
    inst.download_file.assert_not_called()


@pytest.mark.unit
def test_file_section_points_at_extracted_must_gather():
    buckets = {
        "P5": [
            {"name": "must_gather.tar.gz", "id": "id-mg", "size": 1024},
            {"name": "SNO_must_gather.tar.gz", "id": "id-sno", "size": 1024},
        ]
    }
    section = prompts_mod._build_file_section(
        buckets,
        staged_mg=["must_gather", "SNO_must_gather"],
        job_id=JOB_ID,
    )
    assert "Already downloaded and extracted" in section
    assert f"extracted at `/tmp/dci/{JOB_ID}/must_gather/`" in section
    assert f"extracted at `/tmp/dci/{JOB_ID}/SNO_must_gather/`" in section
    assert "tar -xf" not in section


@pytest.mark.unit
def test_file_section_falls_back_to_tar_when_not_staged():
    buckets = {"P5": [{"name": "must_gather.tar.gz", "id": "id-mg", "size": 1024}]}
    section = prompts_mod._build_file_section(buckets)
    assert "tar -xf" in section
    assert "extracted at" not in section


# test_rca_autodownload.py ends here
