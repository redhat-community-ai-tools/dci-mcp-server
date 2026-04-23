#!/usr/bin/env python3
"""
Usage examples for ElasticSearch aggregations with search_dci_jobs tool.

These examples show how to use the aggs parameter to get statistics
instead of fetching all job documents.
"""

# Example 1: Count jobs by status
# User: "How many jobs failed last month?"
# Tool call:
search_dci_jobs_example_1 = {
    "query": "((created_at>='2026-03-01') and (created_at<'2026-04-01'))",
    "limit": 1,  # Minimal job documents, focus on aggregation stats
    "aggs": {"by_status": {"terms": {"field": "status", "size": 10}}},
}

# Expected response:
# {
#   "aggregations": {
#     "by_status": {
#       "buckets": [
#         {"key": "success", "doc_count": 150},
#         {"key": "failure", "doc_count": 30},
#         {"key": "error", "doc_count": 5}
#       ]
#     }
#   },
#   "hits": [],
#   "total": 185
# }


# Example 2: Daily job trend with status breakdown
# User: "Show me daily job trend for the last week"
search_dci_jobs_example_2 = {
    "query": "((created_at>='2026-04-13'))",
    "limit": 1,
    "aggs": {
        "daily": {
            "date_histogram": {"field": "created_at", "calendar_interval": "day"},
            "aggs": {
                "by_status": {"terms": {"field": "status"}},
                "avg_duration": {"avg": {"field": "duration"}},
            },
        }
    },
}

# Expected response:
# {
#   "aggregations": {
#     "daily": {
#       "buckets": [
#         {
#           "key_as_string": "2026-04-13",
#           "doc_count": 45,
#           "by_status": {
#             "buckets": [
#               {"key": "success", "doc_count": 40},
#               {"key": "failure", "doc_count": 5}
#             ]
#           },
#           "avg_duration": {"value": 3600.5}
#         },
#         ...
#       ]
#     }
#   }
# }


# Example 3: OCP version distribution (nested aggregation)
# User: "Which OCP versions are being tested most?"
search_dci_jobs_example_3 = {
    "query": "((tags in ['daily']))",
    "limit": 1,
    "aggs": {
        "components_agg": {
            "nested": {"path": "components"},
            "aggs": {
                "ocp_only": {
                    "filter": {"term": {"components.type": "ocp"}},
                    "aggs": {
                        "versions": {
                            "terms": {"field": "components.version", "size": 50}
                        }
                    },
                }
            },
        }
    },
}

# Expected response:
# {
#   "aggregations": {
#     "components_agg": {
#       "ocp_only": {
#         "versions": {
#           "buckets": [
#             {"key": "4.19.0-nightly", "doc_count": 136},
#             {"key": "4.20.0", "doc_count": 64},
#             {"key": "4.18.5", "doc_count": 45}
#           ]
#         }
#       }
#     }
#   }
# }


# Example 4: Test failure rate (triple-nested aggregation)
# User: "What's the test success/failure rate?"
search_dci_jobs_example_4 = {
    "query": "((tags in ['daily']) and (created_at>='2026-04-01'))",
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
                                },
                                "avg_time": {
                                    "avg": {"field": "tests.testsuites.testcases.time"}
                                },
                            },
                        }
                    },
                }
            },
        }
    },
}

# Expected response:
# {
#   "aggregations": {
#     "test_results": {
#       "testsuites": {
#         "testcases": {
#           "by_action": {
#             "buckets": [
#               {"key": "success", "doc_count": 18600},
#               {"key": "failure", "doc_count": 1300},
#               {"key": "skip", "doc_count": 450},
#               {"key": "error", "doc_count": 100}
#             ]
#           },
#           "avg_time": {"value": 12.5}
#         }
#       }
#     }
#   }
# }


# Example 5: Jobs by team with average duration
# User: "Which teams run the most jobs and how long do they take?"
search_dci_jobs_example_5 = {
    "query": "((created_at>='2026-03-01'))",
    "limit": 1,
    "aggs": {
        "by_team": {
            "terms": {"field": "team_id", "size": 20},
            "aggs": {
                "avg_duration": {"avg": {"field": "duration"}},
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
    },
}


# Example 6: Duration statistics
# User: "What's the average job duration and how long do the longest jobs take?"
search_dci_jobs_example_6 = {
    "query": "((status='success') and (created_at>='2026-04-01'))",
    "limit": 1,
    "aggs": {
        "duration_stats": {"stats": {"field": "duration"}},
        "duration_percentiles": {
            "percentiles": {"field": "duration", "percents": [50, 90, 95, 99]}
        },
    },
}

# Expected response:
# {
#   "aggregations": {
#     "duration_stats": {
#       "count": 150,
#       "min": 1200.0,
#       "max": 7200.0,
#       "avg": 3600.5,
#       "sum": 540075.0
#     },
#     "duration_percentiles": {
#       "values": {
#         "50.0": 3400.0,
#         "90.0": 5800.0,
#         "95.0": 6400.0,
#         "99.0": 7000.0
#       }
#     }
#   }
# }


# Example 7: Combining document retrieval with aggregations
# User: "Show me the latest failed job AND the failure count by reason"
search_dci_jobs_example_7 = {
    "query": "((status in ['failure', 'error']))",
    "limit": 1,  # Get the latest failed job
    "fields": ["id", "name", "status", "status_reason", "created_at"],
    "sort": "-created_at",
    "aggs": {"failure_reasons": {"terms": {"field": "status_reason", "size": 20}}},
}

# Response includes both hits (1 job) and aggregations (stats)


if __name__ == "__main__":
    print("ElasticSearch Aggregation Usage Examples")
    print("=" * 60)
    print("\nThese examples show how Claude can automatically construct")
    print("aggregations based on user questions.")
    print("\nKey principle: Use aggregations for statistics/counts/trends,")
    print("not for retrieving individual job documents.")
