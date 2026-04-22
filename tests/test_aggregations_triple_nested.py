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
Integration tests for triple-nested field aggregations.
Tests cover: tests → testsuites → testcases (3-level nested structure).
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
async def test_test_results_by_action(mcp_client):
    """Test aggregation on test results by action (success/failure/error/skip)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "test_results": {
                    "nested": {"path": "tests"},
                    "aggs": {
                        "testsuites": {
                            "nested": {"path": "tests.testsuites"},
                            "aggs": {
                                "testcases": {
                                    "nested": {"path": "tests.testsuites.testcases"},
                                    "aggs": {
                                        "by_action": {
                                            "terms": {
                                                "field": "tests.testsuites.testcases.action",
                                                "size": 10,
                                            }
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
    assert "test_results" in data["aggregations"]
    assert "testsuites" in data["aggregations"]["test_results"]
    assert "testcases" in data["aggregations"]["test_results"]["testsuites"]
    assert (
        "by_action" in data["aggregations"]["test_results"]["testsuites"]["testcases"]
    )
    assert (
        "buckets"
        in data["aggregations"]["test_results"]["testsuites"]["testcases"]["by_action"]
    )

    buckets = data["aggregations"]["test_results"]["testsuites"]["testcases"][
        "by_action"
    ]["buckets"]
    # Should have buckets for test actions (success, failure, error, skip, etc.)
    if len(buckets) > 0:
        for bucket in buckets:
            assert "key" in bucket
            assert "doc_count" in bucket
            # Action should be a non-empty string
            assert isinstance(bucket["key"], str)
            assert len(bucket["key"]) > 0


@pytest.mark.integration
async def test_test_execution_time_stats(mcp_client):
    """Test statistics on test execution time."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "test_performance": {
                    "nested": {"path": "tests"},
                    "aggs": {
                        "testsuites": {
                            "nested": {"path": "tests.testsuites"},
                            "aggs": {
                                "testcases": {
                                    "nested": {"path": "tests.testsuites.testcases"},
                                    "aggs": {
                                        "time_stats": {
                                            "stats": {
                                                "field": "tests.testsuites.testcases.time"
                                            }
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
    assert "test_performance" in data["aggregations"]
    assert "testsuites" in data["aggregations"]["test_performance"]
    assert "testcases" in data["aggregations"]["test_performance"]["testsuites"]
    assert (
        "time_stats"
        in data["aggregations"]["test_performance"]["testsuites"]["testcases"]
    )

    stats = data["aggregations"]["test_performance"]["testsuites"]["testcases"][
        "time_stats"
    ]
    # Stats might be empty if no test data, but structure should be correct
    assert "count" in stats


@pytest.mark.integration
async def test_top_failing_tests(mcp_client):
    """Test aggregation to find top failing tests by name."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "failing_tests": {
                    "nested": {"path": "tests"},
                    "aggs": {
                        "testsuites": {
                            "nested": {"path": "tests.testsuites"},
                            "aggs": {
                                "testcases": {
                                    "nested": {"path": "tests.testsuites.testcases"},
                                    "aggs": {
                                        "failures_only": {
                                            "filter": {
                                                "term": {
                                                    "tests.testsuites.testcases.action": "failure"
                                                }
                                            },
                                            "aggs": {
                                                "top_tests": {
                                                    "terms": {
                                                        "field": "tests.testsuites.testcases.name",
                                                        "size": 20,
                                                    }
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
    assert "failing_tests" in data["aggregations"]

    # Navigate to the failures_only filter
    failing_tests = data["aggregations"]["failing_tests"]
    assert "testsuites" in failing_tests
    assert "testcases" in failing_tests["testsuites"]
    assert "failures_only" in failing_tests["testsuites"]["testcases"]

    failures_only = failing_tests["testsuites"]["testcases"]["failures_only"]
    assert "doc_count" in failures_only
    assert "top_tests" in failures_only


@pytest.mark.integration
async def test_test_suite_statistics(mcp_client):
    """Test aggregation on test suite level (errors, failures, success counts)."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "test_suites": {
                    "nested": {"path": "tests"},
                    "aggs": {
                        "suites": {
                            "nested": {"path": "tests.testsuites"},
                            "aggs": {
                                "total_errors": {
                                    "sum": {"field": "tests.testsuites.errors"}
                                },
                                "total_failures": {
                                    "sum": {"field": "tests.testsuites.failures"}
                                },
                                "total_success": {
                                    "sum": {"field": "tests.testsuites.success"}
                                },
                                "total_skipped": {
                                    "sum": {"field": "tests.testsuites.skipped"}
                                },
                                "avg_time": {"avg": {"field": "tests.testsuites.time"}},
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
    assert "test_suites" in data["aggregations"]
    assert "suites" in data["aggregations"]["test_suites"]

    suites = data["aggregations"]["test_suites"]["suites"]
    assert "total_errors" in suites
    assert "total_failures" in suites
    assert "total_success" in suites
    assert "total_skipped" in suites
    assert "avg_time" in suites


@pytest.mark.integration
async def test_test_results_with_job_status(mcp_client):
    """Test reverse nested: test results grouped by job status."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "test_results": {
                    "nested": {"path": "tests"},
                    "aggs": {
                        "testsuites": {
                            "nested": {"path": "tests.testsuites"},
                            "aggs": {
                                "testcases": {
                                    "nested": {"path": "tests.testsuites.testcases"},
                                    "aggs": {
                                        "by_action": {
                                            "terms": {
                                                "field": "tests.testsuites.testcases.action",
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
                }
            },
        },
    )
    assert not result.is_error

    data = parse_response(result)
    assert "aggregations" in data
    assert "test_results" in data["aggregations"]

    # Navigate to test actions
    test_results = data["aggregations"]["test_results"]
    assert "testsuites" in test_results
    assert "testcases" in test_results["testsuites"]
    assert "by_action" in test_results["testsuites"]["testcases"]

    buckets = test_results["testsuites"]["testcases"]["by_action"]["buckets"]
    # Each action bucket should have reverse nested to job status
    if len(buckets) > 0:
        for bucket in buckets:
            if "back_to_jobs" in bucket:
                assert "by_status" in bucket["back_to_jobs"]


@pytest.mark.integration
async def test_test_classname_distribution(mcp_client):
    """Test aggregation by test classname."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "test_classes": {
                    "nested": {"path": "tests"},
                    "aggs": {
                        "testsuites": {
                            "nested": {"path": "tests.testsuites"},
                            "aggs": {
                                "testcases": {
                                    "nested": {"path": "tests.testsuites.testcases"},
                                    "aggs": {
                                        "by_classname": {
                                            "terms": {
                                                "field": "tests.testsuites.testcases.classname",
                                                "size": 30,
                                            }
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
    assert "test_classes" in data["aggregations"]
    assert "testsuites" in data["aggregations"]["test_classes"]
    assert "testcases" in data["aggregations"]["test_classes"]["testsuites"]
    assert (
        "by_classname"
        in data["aggregations"]["test_classes"]["testsuites"]["testcases"]
    )


@pytest.mark.integration
async def test_test_type_distribution(mcp_client):
    """Test aggregation by test type."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "test_types": {
                    "nested": {"path": "tests"},
                    "aggs": {
                        "testsuites": {
                            "nested": {"path": "tests.testsuites"},
                            "aggs": {
                                "testcases": {
                                    "nested": {"path": "tests.testsuites.testcases"},
                                    "aggs": {
                                        "by_type": {
                                            "terms": {
                                                "field": "tests.testsuites.testcases.type",
                                                "size": 20,
                                            }
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
    assert "test_types" in data["aggregations"]


@pytest.mark.integration
async def test_testsuite_name_distribution(mcp_client):
    """Test aggregation by test suite name."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "suite_names": {
                    "nested": {"path": "tests"},
                    "aggs": {
                        "testsuites": {
                            "nested": {"path": "tests.testsuites"},
                            "aggs": {
                                "by_name": {
                                    "terms": {
                                        "field": "tests.testsuites.name",
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
    assert "suite_names" in data["aggregations"]
    assert "testsuites" in data["aggregations"]["suite_names"]
    assert "by_name" in data["aggregations"]["suite_names"]["testsuites"]


@pytest.mark.integration
async def test_combined_test_metrics(mcp_client):
    """Test combined test metrics: actions, time stats, and suite counts."""
    result = await mcp_client.call_tool(
        "search_dci_jobs",
        {
            "query": "(created_at>='2026-04-01')",
            "limit": 1,
            "aggs": {
                "test_metrics": {
                    "nested": {"path": "tests"},
                    "aggs": {
                        "testsuites": {
                            "nested": {"path": "tests.testsuites"},
                            "aggs": {
                                "suite_count": {
                                    "value_count": {"field": "tests.testsuites.name"}
                                },
                                "total_tests": {
                                    "sum": {"field": "tests.testsuites.tests"}
                                },
                                "testcases": {
                                    "nested": {"path": "tests.testsuites.testcases"},
                                    "aggs": {
                                        "by_action": {
                                            "terms": {
                                                "field": "tests.testsuites.testcases.action",
                                                "size": 10,
                                            }
                                        },
                                        "avg_time": {
                                            "avg": {
                                                "field": "tests.testsuites.testcases.time"
                                            }
                                        },
                                    },
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
    assert "test_metrics" in data["aggregations"]
    assert "testsuites" in data["aggregations"]["test_metrics"]

    suites = data["aggregations"]["test_metrics"]["testsuites"]
    assert "suite_count" in suites
    assert "total_tests" in suites
    assert "testcases" in suites
    assert "by_action" in suites["testcases"]
    assert "avg_time" in suites["testcases"]
