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
Integration tests for nodes and hardware aggregations.
Tests cover: nodes → hardware, nodes → kernel (double-nested structures).
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
async def test_cpu_vendor_aggregation(mcp_client):
    """Test aggregation by CPU vendor."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {
                "nodes_agg": {
                    "nested": {"path": "nodes"},
                    "aggs": {
                        "hardware": {
                            "nested": {"path": "nodes.hardware"},
                            "aggs": {
                                "cpu_vendors": {
                                    "terms": {
                                        "field": "nodes.hardware.cpu_vendor",
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
    assert "nodes_agg" in data["aggregations"]
    assert "hardware" in data["aggregations"]["nodes_agg"]
    assert "cpu_vendors" in data["aggregations"]["nodes_agg"]["hardware"]


@pytest.mark.integration
async def test_cpu_model_distribution(mcp_client):
    """Test distribution of CPU models."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {
                "nodes_agg": {
                    "nested": {"path": "nodes"},
                    "aggs": {
                        "hardware": {
                            "nested": {"path": "nodes.hardware"},
                            "aggs": {
                                "cpu_models": {
                                    "terms": {
                                        "field": "nodes.hardware.cpu_model",
                                        "size": 20,
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
    assert "nodes_agg" in data["aggregations"]
    assert "hardware" in data["aggregations"]["nodes_agg"]
    assert "cpu_models" in data["aggregations"]["nodes_agg"]["hardware"]


@pytest.mark.integration
async def test_memory_size_statistics(mcp_client):
    """Test statistics on memory size."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {
                "nodes_agg": {
                    "nested": {"path": "nodes"},
                    "aggs": {
                        "hardware": {
                            "nested": {"path": "nodes.hardware"},
                            "aggs": {
                                "memory_stats": {
                                    "stats": {"field": "nodes.hardware.memory_total_gb"}
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
    assert "nodes_agg" in data["aggregations"]
    assert "hardware" in data["aggregations"]["nodes_agg"]
    assert "memory_stats" in data["aggregations"]["nodes_agg"]["hardware"]

    stats = data["aggregations"]["nodes_agg"]["hardware"]["memory_stats"]
    assert "count" in stats


@pytest.mark.integration
async def test_bios_vendor_distribution(mcp_client):
    """Test BIOS vendor distribution."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {
                "nodes_agg": {
                    "nested": {"path": "nodes"},
                    "aggs": {
                        "hardware": {
                            "nested": {"path": "nodes.hardware"},
                            "aggs": {
                                "bios_vendors": {
                                    "terms": {
                                        "field": "nodes.hardware.bios_vendor",
                                        "size": 15,
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
    assert "nodes_agg" in data["aggregations"]
    assert "hardware" in data["aggregations"]["nodes_agg"]
    assert "bios_vendors" in data["aggregations"]["nodes_agg"]["hardware"]


@pytest.mark.integration
async def test_cpu_cores_statistics(mcp_client):
    """Test statistics on CPU total cores."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {
                "nodes_agg": {
                    "nested": {"path": "nodes"},
                    "aggs": {
                        "hardware": {
                            "nested": {"path": "nodes.hardware"},
                            "aggs": {
                                "cores_stats": {
                                    "stats": {"field": "nodes.hardware.cpu_total_cores"}
                                },
                                "cores_distribution": {
                                    "terms": {
                                        "field": "nodes.hardware.cpu_total_cores",
                                        "size": 20,
                                    }
                                },
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
    assert "nodes_agg" in data["aggregations"]
    assert "hardware" in data["aggregations"]["nodes_agg"]
    assert "cores_stats" in data["aggregations"]["nodes_agg"]["hardware"]
    assert "cores_distribution" in data["aggregations"]["nodes_agg"]["hardware"]


@pytest.mark.integration
async def test_kernel_version_distribution(mcp_client):
    """Test kernel version distribution."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-01-01')",
            "limit": 1,
            "aggs": {
                "nodes_agg": {
                    "nested": {"path": "nodes"},
                    "aggs": {
                        "kernel": {
                            "nested": {"path": "nodes.kernel"},
                            "aggs": {
                                "versions": {
                                    "terms": {
                                        "field": "nodes.kernel.version",
                                        "size": 30,
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
    assert "nodes_agg" in data["aggregations"]
    assert "kernel" in data["aggregations"]["nodes_agg"]
    assert "versions" in data["aggregations"]["nodes_agg"]["kernel"]


@pytest.mark.integration
async def test_hardware_with_job_status(mcp_client):
    """Test hardware aggregation with reverse nested to job status."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "nodes_agg": {
                    "nested": {"path": "nodes"},
                    "aggs": {
                        "hardware": {
                            "nested": {"path": "nodes.hardware"},
                            "aggs": {
                                "cpu_vendors": {
                                    "terms": {
                                        "field": "nodes.hardware.cpu_vendor",
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
    assert "nodes_agg" in data["aggregations"]
    assert "hardware" in data["aggregations"]["nodes_agg"]
    assert "cpu_vendors" in data["aggregations"]["nodes_agg"]["hardware"]

    buckets = data["aggregations"]["nodes_agg"]["hardware"]["cpu_vendors"]["buckets"]
    # Each CPU vendor bucket should have reverse nested to job status
    if len(buckets) > 0:
        for bucket in buckets:
            if "back_to_jobs" in bucket:
                assert "by_status" in bucket["back_to_jobs"]


@pytest.mark.integration
async def test_combined_hardware_metrics(mcp_client):
    """Test combined hardware metrics in a single aggregation."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "nodes_agg": {
                    "nested": {"path": "nodes"},
                    "aggs": {
                        "hardware": {
                            "nested": {"path": "nodes.hardware"},
                            "aggs": {
                                "cpu_vendors": {
                                    "terms": {
                                        "field": "nodes.hardware.cpu_vendor",
                                        "size": 5,
                                    }
                                },
                                "memory_stats": {
                                    "stats": {"field": "nodes.hardware.memory_total_gb"}
                                },
                                "cores_avg": {
                                    "avg": {"field": "nodes.hardware.cpu_total_cores"}
                                },
                            },
                        },
                        "kernel": {
                            "nested": {"path": "nodes.kernel"},
                            "aggs": {
                                "versions": {
                                    "terms": {
                                        "field": "nodes.kernel.version",
                                        "size": 10,
                                    }
                                }
                            },
                        },
                    },
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "nodes_agg" in data["aggregations"]

    nodes_agg = data["aggregations"]["nodes_agg"]
    # Hardware aggregations
    assert "hardware" in nodes_agg
    assert "cpu_vendors" in nodes_agg["hardware"]
    assert "memory_stats" in nodes_agg["hardware"]
    assert "cores_avg" in nodes_agg["hardware"]

    # Kernel aggregations
    assert "kernel" in nodes_agg
    assert "versions" in nodes_agg["kernel"]
