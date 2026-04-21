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
Integration tests for real-world use cases and scenarios.
These tests simulate actual user workflows and analysis patterns.
"""

import json
from datetime import datetime, timedelta

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
async def test_uc1_weekly_failure_analysis(mcp_client):
    """
    Use Case 1: Weekly Failure Analysis.

    Goal: Analyze failures from the last 7 days to identify:
    - Total failure count
    - Affected pipelines
    - Failure trend (daily breakdown)
    - Average duration of failed jobs
    """
    # Calculate date range for last 7 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)

    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": f"((status in ['failure', 'error']) and (created_at>='{start_date}'))",
            "limit": 1,
            "aggs": {
                "aggs": {
                    "total_failures": {"value_count": {"field": "id"}},
                    "by_pipeline": {
                        "nested": {"path": "pipeline"},
                        "aggs": {
                            "names": {"terms": {"field": "pipeline.name", "size": 20}}
                        },
                    },
                    "daily_trend": {
                        "date_histogram": {
                            "field": "created_at",
                            "calendar_interval": "day",
                        },
                        "aggs": {"by_status": {"terms": {"field": "status"}}},
                    },
                    "duration_stats": {"stats": {"field": "duration"}},
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data

    # Verify all required aggregations are present
    assert "total_failures" in data["aggregations"]
    assert "by_pipeline" in data["aggregations"]
    assert "daily_trend" in data["aggregations"]
    assert "duration_stats" in data["aggregations"]

    # Verify structure
    total_failures = data["aggregations"]["total_failures"]["value"]
    assert total_failures >= 0

    # Pipelines affected
    pipeline_buckets = data["aggregations"]["by_pipeline"]["names"]["buckets"]
    assert isinstance(pipeline_buckets, list)

    # Daily trend
    daily_buckets = data["aggregations"]["daily_trend"]["buckets"]
    assert isinstance(daily_buckets, list)

    # Duration stats
    stats = data["aggregations"]["duration_stats"]
    assert "count" in stats


@pytest.mark.integration
async def test_uc2_component_adoption_tracking(mcp_client):
    """
    Use Case 2: Component Adoption Tracking.

    Goal: Track usage of a specific OCP version (e.g., 4.16) to understand:
    - How many jobs use it
    - Which teams are adopting it
    - Success rate for this version
    - Trend over time
    """
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-03-01')",
            "limit": 1,
            "aggs": {
                "aggs": {
                    "components_agg": {
                        "nested": {"path": "components"},
                        "aggs": {
                            "ocp_416": {
                                "filter": {
                                    "bool": {
                                        "must": [
                                            {"term": {"components.type": "ocp"}},
                                            {"prefix": {"components.version": "4.16"}},
                                        ]
                                    }
                                },
                                "aggs": {
                                    "versions": {
                                        "terms": {
                                            "field": "components.version",
                                            "size": 20,
                                        },
                                        "aggs": {
                                            "back_to_jobs": {
                                                "reverse_nested": {},
                                                "aggs": {
                                                    "by_status": {
                                                        "terms": {"field": "status"}
                                                    },
                                                    "by_team": {
                                                        "nested": {"path": "team"},
                                                        "aggs": {
                                                            "names": {
                                                                "terms": {
                                                                    "field": "team.name",
                                                                    "size": 20,
                                                                }
                                                            }
                                                        },
                                                    },
                                                    "weekly_trend": {
                                                        "date_histogram": {
                                                            "field": "created_at",
                                                            "calendar_interval": "week",
                                                        }
                                                    },
                                                },
                                            }
                                        },
                                    }
                                },
                            }
                        },
                    }
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "components_agg" in data["aggregations"]
    assert "ocp_416" in data["aggregations"]["components_agg"]

    ocp_416 = data["aggregations"]["components_agg"]["ocp_416"]
    assert "versions" in ocp_416
    assert "buckets" in ocp_416["versions"]

    # Check if any 4.16 versions were found
    version_buckets = ocp_416["versions"]["buckets"]
    if len(version_buckets) > 0:
        # Verify structure for each version
        for version_bucket in version_buckets:
            assert "back_to_jobs" in version_bucket
            back_to_jobs = version_bucket["back_to_jobs"]

            # Status breakdown
            assert "by_status" in back_to_jobs
            assert "buckets" in back_to_jobs["by_status"]

            # Team breakdown
            assert "by_team" in back_to_jobs
            assert "names" in back_to_jobs["by_team"]

            # Weekly trend
            assert "weekly_trend" in back_to_jobs
            assert "buckets" in back_to_jobs["weekly_trend"]


@pytest.mark.integration
async def test_uc3_performance_monitoring(mcp_client):
    """
    Use Case 3: Performance Monitoring.

    Goal: Monitor job performance to identify slow jobs:
    - Jobs with duration > 2 hours (7200 seconds)
    - Duration statistics by pipeline
    - Trend over time to see if performance is degrading
    """
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((status='success') and (created_at>='2026-04-01') and (duration>=7200))",
            "limit": 1,
            "aggs": {
                "aggs": {
                    "slow_jobs_count": {"value_count": {"field": "id"}},
                    "duration_stats": {"stats": {"field": "duration"}},
                    "by_pipeline": {
                        "nested": {"path": "pipeline"},
                        "aggs": {
                            "names": {
                                "terms": {"field": "pipeline.name", "size": 20},
                                "aggs": {
                                    "back_to_jobs": {
                                        "reverse_nested": {},
                                        "aggs": {
                                            "avg_duration": {
                                                "avg": {"field": "duration"}
                                            },
                                            "max_duration": {
                                                "max": {"field": "duration"}
                                            },
                                        },
                                    }
                                },
                            }
                        },
                    },
                    "weekly_trend": {
                        "date_histogram": {
                            "field": "created_at",
                            "calendar_interval": "week",
                        },
                        "aggs": {"avg_duration": {"avg": {"field": "duration"}}},
                    },
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "slow_jobs_count" in data["aggregations"]
    assert "duration_stats" in data["aggregations"]
    assert "by_pipeline" in data["aggregations"]
    assert "weekly_trend" in data["aggregations"]

    # Verify duration stats
    stats = data["aggregations"]["duration_stats"]
    if stats["count"] > 0:
        assert stats["min"] >= 7200  # All jobs should be >= 2 hours


@pytest.mark.integration
async def test_uc4_daily_jobs_health_dashboard(mcp_client):
    """
    Use Case 4: Daily Jobs Health Dashboard.

    Goal: Get a quick health overview of daily jobs:
    - Total count
    - Success rate
    - Distribution by pipeline
    - Recent trend (last 30 days)
    """
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((tags in ['daily']) and (created_at>='2026-03-20'))",
            "limit": 1,
            "aggs": {
                "aggs": {
                    "total_count": {"value_count": {"field": "id"}},
                    "by_status": {"terms": {"field": "status", "size": 10}},
                    "by_pipeline": {
                        "nested": {"path": "pipeline"},
                        "aggs": {
                            "names": {
                                "terms": {"field": "pipeline.name", "size": 30},
                                "aggs": {
                                    "back_to_jobs": {
                                        "reverse_nested": {},
                                        "aggs": {
                                            "by_status": {"terms": {"field": "status"}}
                                        },
                                    }
                                },
                            }
                        },
                    },
                    "daily_trend": {
                        "date_histogram": {
                            "field": "created_at",
                            "calendar_interval": "day",
                        },
                        "aggs": {
                            "by_status": {"terms": {"field": "status"}},
                            "avg_duration": {"avg": {"field": "duration"}},
                        },
                    },
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "total_count" in data["aggregations"]
    assert "by_status" in data["aggregations"]
    assert "by_pipeline" in data["aggregations"]
    assert "daily_trend" in data["aggregations"]

    # Verify we can calculate success rate
    status_buckets = data["aggregations"]["by_status"]["buckets"]
    total_jobs = sum(b["doc_count"] for b in status_buckets)
    assert total_jobs > 0


@pytest.mark.integration
async def test_uc5_infrastructure_utilization(mcp_client):
    """
    Use Case 5: Infrastructure Utilization.

    Goal: Analyze RemoteCI utilization:
    - Job count per RemoteCI
    - Success rate per RemoteCI
    - Average job duration per RemoteCI
    - Active vs idle RemoteCIs
    """
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "aggs": {
                    "by_remoteci": {
                        "nested": {"path": "remoteci"},
                        "aggs": {
                            "names": {
                                "terms": {"field": "remoteci.name", "size": 50},
                                "aggs": {
                                    "back_to_jobs": {
                                        "reverse_nested": {},
                                        "aggs": {
                                            "by_status": {"terms": {"field": "status"}},
                                            "avg_duration": {
                                                "avg": {"field": "duration"}
                                            },
                                            "total_duration": {
                                                "sum": {"field": "duration"}
                                            },
                                        },
                                    }
                                },
                            }
                        },
                    }
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "by_remoteci" in data["aggregations"]
    assert "names" in data["aggregations"]["by_remoteci"]
    assert "buckets" in data["aggregations"]["by_remoteci"]["names"]

    remoteci_buckets = data["aggregations"]["by_remoteci"]["names"]["buckets"]
    assert len(remoteci_buckets) > 0

    # Verify each RemoteCI has the required metrics
    for bucket in remoteci_buckets:
        assert "back_to_jobs" in bucket
        back = bucket["back_to_jobs"]
        assert "by_status" in back
        assert "avg_duration" in back
        assert "total_duration" in back


@pytest.mark.integration
async def test_uc6_component_combination_analysis(mcp_client):
    """
    Use Case 6: Component Combination Analysis.

    Goal: Analyze jobs that test specific component combinations:
    - Jobs with both OCP and specific storage solution
    - Success rate for this combination
    - Most common versions used together
    """
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "((components.type='ocp') and (created_at>='2026-04-01'))",
            "limit": 1,
            "aggs": {
                "aggs": {
                    "components_agg": {
                        "nested": {"path": "components"},
                        "aggs": {
                            "by_type": {
                                "terms": {"field": "components.type", "size": 20},
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
                    },
                    "by_status": {"terms": {"field": "status"}},
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "components_agg" in data["aggregations"]
    assert "by_status" in data["aggregations"]

    # Verify component type breakdown with versions
    comp_agg = data["aggregations"]["components_agg"]
    assert "by_type" in comp_agg
    assert "buckets" in comp_agg["by_type"]

    # Each component type should have version breakdown
    for bucket in comp_agg["by_type"]["buckets"]:
        assert "versions" in bucket
        assert "buckets" in bucket["versions"]
