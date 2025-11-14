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

"""Unit tests for job tools."""

from mcp_server.tools.job_tools import filter_jobs_by_fields


def test_filter_jobs_by_fields():
    jobs = [
        {"id": "1", "name": "Job 1", "status": "success"},
        {"id": "2", "name": "Job 2", "status": "failure"},
    ]
    fields = ["id", "name"]
    filtered_jobs = filter_jobs_by_fields(jobs, fields)
    assert filtered_jobs == [{"id": "1", "name": "Job 1"}, {"id": "2", "name": "Job 2"}]


def test_filter_jobs_by_fields_empty():
    jobs = [
        {"id": "1", "name": "Job 1", "status": "success"},
        {"id": "2", "name": "Job 2", "status": "failure"},
    ]
    fields = []
    filtered_jobs = filter_jobs_by_fields(jobs, fields)
    assert filtered_jobs == []


def test_filter_jobs_by_fields_complex():
    jobs = [
        {
            "id": "1",
            "components": {"type": "ocp", "version": "4.19.0", "id": "foo"},
            "status": "success",
        },
        {
            "id": "2",
            "components": {"type": "ocp", "version": "4.20.0", "id": "bar"},
            "status": "failure",
        },
    ]
    fields = ["id", "components.type", "components.version"]
    filtered_jobs = filter_jobs_by_fields(jobs, fields)
    assert filtered_jobs == [
        {"id": "1", "components": {"type": "ocp", "version": "4.19.0"}},
        {"id": "2", "components": {"type": "ocp", "version": "4.20.0"}},
    ]


def test_filter_jobs_by_fields_with_list_components():
    """Test filtering with components as a list (real DCI format)."""
    jobs = [
        {
            "id": "1",
            "name": "daily-job-1",
            "status": "success",
            "created_at": "2024-01-01T00:00:00Z",
            "tags": ["daily"],
            "components": [
                {"type": "ocp", "version": "4.19.0", "name": "openshift"},
                {"type": "storage", "version": "1.0.0", "name": "ceph"},
            ],
        },
        {
            "id": "2",
            "name": "daily-job-2",
            "status": "failure",
            "created_at": "2024-01-02T00:00:00Z",
            "tags": ["daily"],
            "components": [
                {"type": "ocp", "version": "4.20.0", "name": "openshift"},
            ],
        },
    ]
    fields = [
        "id",
        "name",
        "status",
        "created_at",
        "tags",
        "components.type",
        "components.version",
        "components.name",
    ]
    filtered_jobs = filter_jobs_by_fields(jobs, fields)

    # Check structure
    assert len(filtered_jobs) == 2

    # Check first job
    job1 = filtered_jobs[0]
    assert job1["id"] == "1"
    assert job1["name"] == "daily-job-1"
    assert job1["status"] == "success"
    assert job1["created_at"] == "2024-01-01T00:00:00Z"
    assert job1["tags"] == ["daily"]
    assert "components" in job1
    assert len(job1["components"]) == 2

    # Check components structure
    comp1 = job1["components"][0]
    assert comp1["type"] == "ocp"
    assert comp1["version"] == "4.19.0"
    assert comp1["name"] == "openshift"

    comp2 = job1["components"][1]
    assert comp2["type"] == "storage"
    assert comp2["version"] == "1.0.0"
    assert comp2["name"] == "ceph"


def test_filter_jobs_by_fields_mixed_simple_and_nested():
    """Test filtering with both simple and nested fields."""
    jobs = [
        {
            "id": "1",
            "name": "test-job",
            "status": "success",
            "team": {"name": "test-team", "id": "team-1"},
            "components": [
                {"type": "ocp", "version": "4.19.0"},
            ],
        }
    ]
    fields = ["id", "name", "team.name", "components.type"]
    filtered_jobs = filter_jobs_by_fields(jobs, fields)

    assert len(filtered_jobs) == 1
    job = filtered_jobs[0]
    assert job["id"] == "1"
    assert job["name"] == "test-job"
    assert job["team"]["name"] == "test-team"
    assert job["components"][0]["type"] == "ocp"


def test_filter_jobs_by_fields_elasticsearch_format():
    """Test filtering with Elasticsearch response format."""
    jobs = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "id": "1",
                        "name": "es-job",
                        "status": "success",
                        "components": [
                            {"type": "ocp", "version": "4.19.0"},
                        ],
                    }
                }
            ]
        }
    }
    fields = ["id", "name", "components.type"]
    filtered_jobs = filter_jobs_by_fields(jobs, fields)

    assert len(filtered_jobs) == 1
    job = filtered_jobs[0]
    assert job["id"] == "1"
    assert job["name"] == "es-job"
    assert job["components"][0]["type"] == "ocp"


def test_filter_jobs_by_fields_missing_nested_fields():
    """Test filtering when some nested fields are missing."""
    jobs = [
        {
            "id": "1",
            "name": "job-without-components",
            "status": "success",
        },
        {
            "id": "2",
            "name": "job-with-components",
            "status": "success",
            "components": [
                {"type": "ocp", "version": "4.19.0"},
            ],
        },
    ]
    fields = ["id", "name", "components.type", "components.version"]
    filtered_jobs = filter_jobs_by_fields(jobs, fields)

    assert len(filtered_jobs) == 2

    # First job should only have simple fields
    job1 = filtered_jobs[0]
    assert job1["id"] == "1"
    assert job1["name"] == "job-without-components"
    assert "components" not in job1

    # Second job should have components
    job2 = filtered_jobs[1]
    assert job2["id"] == "2"
    assert job2["name"] == "job-with-components"
    assert "components" in job2
    assert job2["components"][0]["type"] == "ocp"
    assert job2["components"][0]["version"] == "4.19.0"


def test_filter_jobs_by_fields_empty_components():
    """Test filtering with empty components list."""
    jobs = [
        {
            "id": "1",
            "name": "job-with-empty-components",
            "status": "success",
            "components": [],
        }
    ]
    fields = ["id", "name", "components.type"]
    filtered_jobs = filter_jobs_by_fields(jobs, fields)

    assert len(filtered_jobs) == 1
    job = filtered_jobs[0]
    assert job["id"] == "1"
    assert job["name"] == "job-with-empty-components"
    assert "components" not in job  # Empty list should not be included


def test_filter_jobs_by_fields_none_values():
    """Test filtering with None values in nested fields."""
    jobs = [
        {
            "id": "1",
            "name": "job-with-null-components",
            "status": "success",
            "components": [
                {"type": "ocp", "version": None, "name": "openshift"},
                {"type": None, "version": "4.19.0", "name": "openshift"},
            ],
        }
    ]
    fields = ["id", "name", "components.type", "components.version", "components.name"]
    filtered_jobs = filter_jobs_by_fields(jobs, fields)

    assert len(filtered_jobs) == 1
    job = filtered_jobs[0]
    assert job["id"] == "1"
    assert job["name"] == "job-with-null-components"
    assert len(job["components"]) == 2

    # First component should only have type and name (version is None)
    comp1 = job["components"][0]
    assert comp1["type"] == "ocp"
    assert comp1["name"] == "openshift"
    assert "version" not in comp1

    # Second component should only have version and name (type is None)
    comp2 = job["components"][1]
    assert comp2["version"] == "4.19.0"
    assert comp2["name"] == "openshift"
    assert "type" not in comp2
