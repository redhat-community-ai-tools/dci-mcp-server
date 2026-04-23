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

"""
Integration tests for nested field aggregations (depth 1).
Tests cover: components, team, remoteci, pipeline, topic, files, keys_values.
"""

import json

import pytest
from fastmcp import Client

from mcp_server.main import create_server


@pytest.fixture(scope="module")
def mcp_server():
    server = create_server()
    return server


@pytest.fixture(scope="module")
async def mcp_client(mcp_server):
    async with Client(mcp_server) as client:
        yield client


def parse_response(result):
    """Helper function to parse MCP tool response."""
    if result.content and len(result.content) > 0:
        content_text = result.content[0].text
        return json.loads(content_text)
    else:
        pytest.fail("No content returned from tool")


@pytest.mark.integration
async def test_components_type_aggregation(mcp_client):
    """Test aggregation on components.type (nested field)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {
                "component_types": {
                    "nested": {"path": "components"},
                    "aggs": {
                        "types": {"terms": {"field": "components.type", "size": 20}}
                    },
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "component_types" in data["aggregations"]
    assert "doc_count" in data["aggregations"]["component_types"]
    assert "types" in data["aggregations"]["component_types"]
    assert "buckets" in data["aggregations"]["component_types"]["types"]

    buckets = data["aggregations"]["component_types"]["types"]["buckets"]
    assert len(buckets) > 0

    # Should have component types like 'ocp', 'storage', etc.
    for bucket in buckets:
        assert "key" in bucket
        assert "doc_count" in bucket
        assert bucket["doc_count"] > 0


@pytest.mark.integration
async def test_ocp_version_distribution(mcp_client):
    """Test OCP version distribution using nested aggregation with filter."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {
                "components_agg": {
                    "nested": {"path": "components"},
                    "aggs": {
                        "ocp_only": {
                            "filter": {"term": {"components.type": "ocp"}},
                            "aggs": {
                                "versions": {
                                    "terms": {
                                        "field": "components.version",
                                        "size": 50,
                                    }
                                }
                            },
                        }
                    },
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "components_agg" in data["aggregations"]
    assert "ocp_only" in data["aggregations"]["components_agg"]
    assert "versions" in data["aggregations"]["components_agg"]["ocp_only"]
    assert "buckets" in data["aggregations"]["components_agg"]["ocp_only"]["versions"]

    buckets = data["aggregations"]["components_agg"]["ocp_only"]["versions"]["buckets"]
    assert len(buckets) > 0

    # OCP versions should be like "4.14.0", "4.15.0", etc.
    for bucket in buckets:
        assert "key" in bucket
        assert "doc_count" in bucket


@pytest.mark.integration
async def test_component_names_aggregation(mcp_client):
    """Test aggregation on components.name."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "component_names": {
                    "nested": {"path": "components"},
                    "aggs": {
                        "names": {"terms": {"field": "components.name", "size": 30}}
                    },
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "component_names" in data["aggregations"]
    assert "names" in data["aggregations"]["component_names"]
    assert "buckets" in data["aggregations"]["component_names"]["names"]

    buckets = data["aggregations"]["component_names"]["names"]["buckets"]
    assert len(buckets) > 0


@pytest.mark.integration
async def test_component_tags_aggregation(mcp_client):
    """Test aggregation on components.tags."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {
                "component_tags": {
                    "nested": {"path": "components"},
                    "aggs": {
                        "tags": {"terms": {"field": "components.tags", "size": 30}}
                    },
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "component_tags" in data["aggregations"]
    assert "tags" in data["aggregations"]["component_tags"]
    assert "buckets" in data["aggregations"]["component_tags"]["tags"]


@pytest.mark.integration
async def test_team_name_aggregation(mcp_client):
    """Test aggregation on team.name (nested field)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {
                "teams": {
                    "nested": {"path": "team"},
                    "aggs": {"by_name": {"terms": {"field": "team.name", "size": 30}}},
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "teams" in data["aggregations"]
    assert "by_name" in data["aggregations"]["teams"]
    assert "buckets" in data["aggregations"]["teams"]["by_name"]

    buckets = data["aggregations"]["teams"]["by_name"]["buckets"]
    assert len(buckets) > 0

    for bucket in buckets:
        assert "key" in bucket
        assert "doc_count" in bucket


@pytest.mark.integration
async def test_remoteci_name_aggregation(mcp_client):
    """Test aggregation on remoteci.name (nested field)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {
                "remotecis": {
                    "nested": {"path": "remoteci"},
                    "aggs": {
                        "by_name": {"terms": {"field": "remoteci.name", "size": 50}}
                    },
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "remotecis" in data["aggregations"]
    assert "by_name" in data["aggregations"]["remotecis"]
    assert "buckets" in data["aggregations"]["remotecis"]["by_name"]

    buckets = data["aggregations"]["remotecis"]["by_name"]["buckets"]
    assert len(buckets) > 0


@pytest.mark.integration
async def test_pipeline_name_aggregation(mcp_client):
    """Test aggregation on pipeline.name (nested field)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {
                "pipelines": {
                    "nested": {"path": "pipeline"},
                    "aggs": {
                        "by_name": {"terms": {"field": "pipeline.name", "size": 50}}
                    },
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "pipelines" in data["aggregations"]
    assert "by_name" in data["aggregations"]["pipelines"]
    assert "buckets" in data["aggregations"]["pipelines"]["by_name"]

    buckets = data["aggregations"]["pipelines"]["by_name"]["buckets"]
    assert len(buckets) > 0


@pytest.mark.integration
async def test_topic_name_aggregation(mcp_client):
    """Test aggregation on topic.name (nested field)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {
                "topics": {
                    "nested": {"path": "topic"},
                    "aggs": {"by_name": {"terms": {"field": "topic.name", "size": 30}}},
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "topics" in data["aggregations"]
    assert "by_name" in data["aggregations"]["topics"]
    assert "buckets" in data["aggregations"]["topics"]["by_name"]

    buckets = data["aggregations"]["topics"]["by_name"]["buckets"]
    assert len(buckets) > 0


@pytest.mark.integration
async def test_files_mime_aggregation(mcp_client):
    """Test aggregation on files.mime (nested field)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {
                "file_types": {
                    "nested": {"path": "files"},
                    "aggs": {"by_mime": {"terms": {"field": "files.mime", "size": 30}}},
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "file_types" in data["aggregations"]
    assert "by_mime" in data["aggregations"]["file_types"]
    assert "buckets" in data["aggregations"]["file_types"]["by_mime"]


@pytest.mark.integration
async def test_files_size_stats(mcp_client):
    """Test statistics aggregation on files.size (nested field)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {
                "file_stats": {
                    "nested": {"path": "files"},
                    "aggs": {"size_stats": {"stats": {"field": "files.size"}}},
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "file_stats" in data["aggregations"]
    assert "size_stats" in data["aggregations"]["file_stats"]

    stats = data["aggregations"]["file_stats"]["size_stats"]
    assert "count" in stats
    assert "min" in stats
    assert "max" in stats
    assert "avg" in stats


@pytest.mark.integration
async def test_multi_nested_aggregations(mcp_client):
    """Test multiple nested aggregations simultaneously."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "by_pipeline": {
                    "nested": {"path": "pipeline"},
                    "aggs": {
                        "names": {"terms": {"field": "pipeline.name", "size": 20}}
                    },
                },
                "by_remoteci": {
                    "nested": {"path": "remoteci"},
                    "aggs": {
                        "names": {"terms": {"field": "remoteci.name", "size": 20}}
                    },
                },
                "by_ocp_version": {
                    "nested": {"path": "components"},
                    "aggs": {
                        "ocp_filter": {
                            "filter": {"term": {"components.type": "ocp"}},
                            "aggs": {
                                "versions": {
                                    "terms": {
                                        "field": "components.version",
                                        "size": 20,
                                    }
                                }
                            },
                        }
                    },
                },
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data

    # All three aggregations should be present
    assert "by_pipeline" in data["aggregations"]
    assert "by_remoteci" in data["aggregations"]
    assert "by_ocp_version" in data["aggregations"]

    # Verify structure
    assert "names" in data["aggregations"]["by_pipeline"]
    assert "names" in data["aggregations"]["by_remoteci"]
    assert "ocp_filter" in data["aggregations"]["by_ocp_version"]
    assert "versions" in data["aggregations"]["by_ocp_version"]["ocp_filter"]


@pytest.mark.integration
async def test_reverse_nested_components_to_status(mcp_client):
    """Test reverse nested: OCP versions with job status breakdown."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "components_agg": {
                    "nested": {"path": "components"},
                    "aggs": {
                        "ocp_versions": {
                            "filter": {"term": {"components.type": "ocp"}},
                            "aggs": {
                                "versions": {
                                    "terms": {
                                        "field": "components.version",
                                        "size": 10,
                                    },
                                    "aggs": {
                                        "back_to_jobs": {
                                            "reverse_nested": {},
                                            "aggs": {
                                                "by_status": {
                                                    "terms": {"field": "status"}
                                                }
                                            },
                                        }
                                    },
                                }
                            },
                        }
                    },
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "components_agg" in data["aggregations"]
    assert "ocp_versions" in data["aggregations"]["components_agg"]
    assert "versions" in data["aggregations"]["components_agg"]["ocp_versions"]
    assert (
        "buckets" in data["aggregations"]["components_agg"]["ocp_versions"]["versions"]
    )

    buckets = data["aggregations"]["components_agg"]["ocp_versions"]["versions"][
        "buckets"
    ]
    if len(buckets) > 0:
        # Each version bucket should have reverse nested to job status
        for bucket in buckets:
            assert "back_to_jobs" in bucket
            assert "by_status" in bucket["back_to_jobs"]
            assert "buckets" in bucket["back_to_jobs"]["by_status"]


@pytest.mark.integration
async def test_pipeline_with_status_subagg(mcp_client):
    """Test nested pipeline aggregation with status sub-aggregation via reverse nested."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "pipelines": {
                    "nested": {"path": "pipeline"},
                    "aggs": {
                        "by_name": {
                            "terms": {"field": "pipeline.name", "size": 10},
                            "aggs": {
                                "back_to_jobs": {
                                    "reverse_nested": {},
                                    "aggs": {
                                        "by_status": {"terms": {"field": "status"}},
                                        "avg_duration": {"avg": {"field": "duration"}},
                                    },
                                }
                            },
                        }
                    },
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "pipelines" in data["aggregations"]
    assert "by_name" in data["aggregations"]["pipelines"]
    assert "buckets" in data["aggregations"]["pipelines"]["by_name"]

    buckets = data["aggregations"]["pipelines"]["by_name"]["buckets"]
    assert len(buckets) > 0

    # Each pipeline should have status breakdown and avg duration
    for bucket in buckets:
        assert "back_to_jobs" in bucket
        assert "by_status" in bucket["back_to_jobs"]
        assert "avg_duration" in bucket["back_to_jobs"]


@pytest.mark.integration
async def test_component_version_per_type(mcp_client):
    """Test component versions grouped by component type (sub-aggregation)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "components_agg": {
                    "nested": {"path": "components"},
                    "aggs": {
                        "by_type": {
                            "terms": {"field": "components.type", "size": 10},
                            "aggs": {
                                "versions": {
                                    "terms": {
                                        "field": "components.version",
                                        "size": 10,
                                    }
                                }
                            },
                        }
                    },
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "components_agg" in data["aggregations"]
    assert "by_type" in data["aggregations"]["components_agg"]
    assert "buckets" in data["aggregations"]["components_agg"]["by_type"]

    buckets = data["aggregations"]["components_agg"]["by_type"]["buckets"]
    assert len(buckets) > 0

    # Each type bucket should have versions sub-aggregation
    for bucket in buckets:
        assert "versions" in bucket
        assert "buckets" in bucket["versions"]
