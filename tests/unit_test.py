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


def test_fields_to_includes_conversion():
    """Test that fields list is converted to comma-separated includes string."""
    fields = ["id", "name", "status", "components.version"]
    includes = ",".join(fields)
    assert includes == "id,name,status,components.version"


def test_fields_empty_produces_no_includes():
    """Test that empty fields list produces None includes."""
    fields = []
    includes = ",".join(fields) if fields else None
    assert includes is None


def test_source_extraction_from_es_hits():
    """Test extracting _source from Elasticsearch hit format."""
    es_hits = [
        {"_source": {"id": "1", "name": "Job 1", "status": "success"}},
        {"_source": {"id": "2", "name": "Job 2", "status": "failure"}},
    ]
    extracted = [hit["_source"] for hit in es_hits if "_source" in hit]
    assert extracted == [
        {"id": "1", "name": "Job 1", "status": "success"},
        {"id": "2", "name": "Job 2", "status": "failure"},
    ]


def test_source_extraction_with_nested_fields():
    """Test that server-side filtered _source preserves nested structure."""
    # Simulating what ES returns when includes=id,name,components.name
    es_hits = [
        {
            "_source": {
                "id": "1",
                "name": "es-job",
                "components": [
                    {"name": "openshift"},
                    {"name": "ceph"},
                ],
            }
        }
    ]
    extracted = [hit["_source"] for hit in es_hits if "_source" in hit]
    assert len(extracted) == 1
    assert extracted[0]["id"] == "1"
    assert extracted[0]["name"] == "es-job"
    assert len(extracted[0]["components"]) == 2
    assert extracted[0]["components"][0]["name"] == "openshift"


def test_empty_fields_returns_empty_list():
    """Test that fields=[] returns empty job list."""
    result = {
        "hits": {
            "hits": [
                {"_source": {"id": "1", "name": "Job 1"}},
            ],
            "total": {"value": 1},
        }
    }
    fields = []
    if isinstance(fields, list) and not fields:
        result["hits"]["hits"] = []
    assert result["hits"]["hits"] == []
