#!/usr/bin/env python3
"""
Examples of ElasticSearch aggregations for DCI jobs analysis.

These examples show how aggregations could be used once implemented
in the DCI API, dciclient, and MCP server.
"""

# Example 1: Simple counting by status
aggregations_by_status = {"by_status": {"terms": {"field": "status", "size": 10}}}

# Expected result:
# {
#   "by_status": {
#     "buckets": [
#       {"key": "success", "doc_count": 150},
#       {"key": "failure", "doc_count": 30},
#       {"key": "error", "doc_count": 10},
#       {"key": "running", "doc_count": 5}
#     ]
#   }
# }


# Example 2: Test results statistics (PTP example)
ptp_test_aggregations = {
    "test_results": {
        "nested": {"path": "tests.testsuites.testcases"},
        "aggs": {
            "ptp_tests": {
                "filter": {
                    "wildcard": {"tests.testsuites.testcases.name": "*PTP*LOCKED*"}
                },
                "aggs": {
                    "by_action": {
                        "terms": {"field": "tests.testsuites.testcases.action"}
                    },
                    "execution_stats": {
                        "stats": {"field": "tests.testsuites.testcases.time"}
                    },
                },
            }
        },
    }
}

# Expected result:
# {
#   "test_results": {
#     "ptp_tests": {
#       "by_action": {
#         "buckets": [
#           {"key": "success", "doc_count": 186},
#           {"key": "failure", "doc_count": 13},
#           {"key": "error", "doc_count": 1}
#         ]
#       },
#       "execution_stats": {
#         "count": 200,
#         "min": 0.5,
#         "max": 600.0,
#         "avg": 64.9,
#         "sum": 12980.0
#       }
#     }
#   }
# }


# Example 3: Daily trend with success/failure breakdown
daily_trend_aggregations = {
    "by_date": {
        "date_histogram": {
            "field": "created_at",
            "calendar_interval": "day",
            "format": "yyyy-MM-dd",
        },
        "aggs": {
            "by_status": {"terms": {"field": "status"}},
            "avg_duration": {"avg": {"field": "duration"}},
        },
    }
}

# Expected result:
# {
#   "by_date": {
#     "buckets": [
#       {
#         "key_as_string": "2026-02-24",
#         "doc_count": 45,
#         "by_status": {
#           "buckets": [
#             {"key": "success", "doc_count": 40},
#             {"key": "failure", "doc_count": 5}
#           ]
#         },
#         "avg_duration": {"value": 3600.5}
#       },
#       ...
#     ]
#   }
# }


# Example 4: OCP version distribution with component tags
ocp_version_aggregations = {
    "components": {
        "nested": {"path": "components"},
        "aggs": {
            "ocp_components": {
                "filter": {"term": {"components.type": "ocp"}},
                "aggs": {
                    "by_version": {
                        "terms": {"field": "components.version", "size": 50},
                        "aggs": {"by_tag": {"terms": {"field": "components.tags"}}},
                    }
                },
            }
        },
    }
}

# Expected result:
# {
#   "components": {
#     "ocp_components": {
#       "by_version": {
#         "buckets": [
#           {
#             "key": "4.19.0-nightly",
#             "doc_count": 136,
#             "by_tag": {
#               "buckets": [
#                 {"key": "build:nightly", "doc_count": 136}
#               ]
#             }
#           },
#           {
#             "key": "4.20.0",
#             "doc_count": 64,
#             "by_tag": {
#               "buckets": [
#                 {"key": "build:ga", "doc_count": 64}
#               ]
#             }
#           }
#         ]
#       }
#     }
#   }
# }


# Example 5: Hardware analysis - Network cards by OCP version
network_hardware_aggregations = {
    "by_ocp_version": {
        "nested": {"path": "components"},
        "aggs": {
            "ocp_only": {
                "filter": {"term": {"components.type": "ocp"}},
                "aggs": {
                    "versions": {
                        "terms": {"field": "components.version", "size": 20},
                        "aggs": {
                            # Reverse nested to get back to job level
                            "jobs": {
                                "reverse_nested": {},
                                "aggs": {
                                    "network_interfaces": {
                                        "nested": {
                                            "path": "nodes.hardware.network_interfaces"
                                        },
                                        "aggs": {
                                            "by_model": {
                                                "terms": {
                                                    "field": "nodes.hardware.network_interfaces.model",
                                                    "size": 50,
                                                }
                                            },
                                            "by_driver": {
                                                "terms": {
                                                    "field": "nodes.hardware.network_interfaces.driver",
                                                    "size": 30,
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
        },
    }
}

# Expected result:
# {
#   "by_ocp_version": {
#     "ocp_only": {
#       "versions": {
#         "buckets": [
#           {
#             "key": "4.21.3",
#             "doc_count": 35,
#             "jobs": {
#               "network_interfaces": {
#                 "by_model": {
#                   "buckets": [
#                     {"key": "Intel XXV710 25GbE", "doc_count": 214},
#                     {"key": "Virtio network device", "doc_count": 228}
#                   ]
#                 },
#                 "by_driver": {
#                   "buckets": [
#                     {"key": "i40e", "doc_count": 298},
#                     {"key": "mlx5_core", "doc_count": 254}
#                   ]
#                 }
#               }
#             }
#           }
#         ]
#       }
#     }
#   }
# }


# Example 6: Failure correlation analysis
failure_correlation_aggregations = {
    "failures_only": {
        "filter": {"term": {"status": "failure"}},
        "aggs": {
            "by_remoteci": {"terms": {"field": "remoteci.name", "size": 20}},
            "by_ocp_version": {
                "nested": {"path": "components"},
                "aggs": {
                    "ocp_only": {
                        "filter": {"term": {"components.type": "ocp"}},
                        "aggs": {
                            "versions": {
                                "terms": {"field": "components.version", "size": 20}
                            }
                        },
                    }
                },
            },
            "common_test_failures": {
                "nested": {"path": "tests.testsuites.testcases"},
                "aggs": {
                    "failed_tests": {
                        "filter": {
                            "terms": {
                                "tests.testsuites.testcases.action": [
                                    "failure",
                                    "error",
                                ]
                            }
                        },
                        "aggs": {
                            "top_failing_tests": {
                                "terms": {
                                    "field": "tests.testsuites.testcases.name",
                                    "size": 50,
                                }
                            }
                        },
                    }
                },
            },
        },
    }
}


# Example 7: Time-based performance analysis
performance_over_time_aggregations = {
    "by_week": {
        "date_histogram": {"field": "created_at", "calendar_interval": "week"},
        "aggs": {
            "duration_stats": {"stats": {"field": "duration"}},
            "duration_percentiles": {
                "percentiles": {"field": "duration", "percents": [50, 90, 95, 99]}
            },
            "success_rate": {
                "filters": {
                    "filters": {
                        "success": {"term": {"status": "success"}},
                        "failure": {"terms": {"status": ["failure", "error"]}},
                    }
                }
            },
        },
    }
}


# Example 8: Combined query - Full PTP analysis on OCP-4.19
ptp_ocp419_full_analysis = {
    "ocp_419_jobs": {
        "nested": {"path": "components"},
        "aggs": {
            "ocp_419_filter": {
                "filter": {
                    "bool": {
                        "must": [
                            {"term": {"components.type": "ocp"}},
                            {"prefix": {"components.version": "4.19"}},
                        ]
                    }
                },
                "aggs": {
                    "back_to_jobs": {
                        "reverse_nested": {},
                        "aggs": {
                            "ptp_test_results": {
                                "nested": {"path": "tests.testsuites.testcases"},
                                "aggs": {
                                    "ptp_locked_test": {
                                        "filter": {
                                            "wildcard": {
                                                "tests.testsuites.testcases.name": "*PTP*LOCKED*"
                                            }
                                        },
                                        "aggs": {
                                            "by_action": {
                                                "terms": {
                                                    "field": "tests.testsuites.testcases.action"
                                                }
                                            },
                                            "by_nightly_version": {
                                                "reverse_nested": {},
                                                "aggs": {
                                                    "components_again": {
                                                        "nested": {
                                                            "path": "components"
                                                        },
                                                        "aggs": {
                                                            "versions": {
                                                                "terms": {
                                                                    "field": "components.version",
                                                                    "size": 30,
                                                                }
                                                            }
                                                        },
                                                    }
                                                },
                                            },
                                            "daily_trend": {
                                                "reverse_nested": {},
                                                "aggs": {
                                                    "by_date": {
                                                        "date_histogram": {
                                                            "field": "created_at",
                                                            "calendar_interval": "day",
                                                        },
                                                        "aggs": {
                                                            "back_to_tests": {
                                                                "nested": {
                                                                    "path": "tests.testsuites.testcases"
                                                                },
                                                                "aggs": {
                                                                    "ptp_by_action": {
                                                                        "filter": {
                                                                            "wildcard": {
                                                                                "tests.testsuites.testcases.name": "*PTP*LOCKED*"
                                                                            }
                                                                        },
                                                                        "aggs": {
                                                                            "actions": {
                                                                                "terms": {
                                                                                    "field": "tests.testsuites.testcases.action"
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
                                            "time_stats": {
                                                "stats": {
                                                    "field": "tests.testsuites.testcases.time"
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
        },
    }
}


# Usage examples (once implemented):

"""
from dciclient.v1.api import job

# Simple aggregation
result = job.aggregate(
    context,
    query="(status='failure')",
    aggs=aggregations_by_status
)
print(result.json()["aggregations"])

# Complex PTP analysis
result = job.aggregate(
    context,
    query="(topic.name='OCP-4.19')",
    aggs=ptp_ocp419_full_analysis
)
ptp_stats = result.json()["aggregations"]

# Via MCP tool (once implemented)
result = await aggregate_dci_jobs(
    query="(topic.name='OCP-4.19')",
    aggregations=ptp_ocp419_full_analysis
)
"""


if __name__ == "__main__":
    print("ElasticSearch Aggregation Examples for DCI Jobs")
    print("=" * 60)
    print("\nThese examples show how to use ES aggregations for efficient")
    print("data analysis once implemented in the DCI stack.")
    print("\nBenefits:")
    print("  - 10,000x less data transfer")
    print("  - Server-side computation (distributed)")
    print("  - Sub-second response times")
    print("  - Complex multi-dimensional analysis")
