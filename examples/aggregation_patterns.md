# ElasticSearch Aggregation Patterns for DCI Jobs

This guide helps AI assistants (Claude) construct correct ElasticSearch 7.16 aggregations based on user requests.

## When to Use Aggregations

Use the `aggs` parameter with `search_dci_jobs` when users ask for:
- **Counts**: "How many jobs failed?", "Count jobs by status"
- **Statistics**: "Average duration", "Min/max/sum of duration"
- **Trends**: "Daily job trend", "Weekly failure rate"
- **Distributions**: "Jobs by OCP version", "Jobs by team"
- **Aggregated analysis**: Any question requiring statistics rather than individual documents

**Note:** `limit` is auto-set to `1` when using aggregations to save bandwidth (returns only 1 job document + aggregation results). The DCI server requires `limit >= 1` to return aggregations.

## Basic Aggregation Structure

All aggregations follow this pattern:
```json
{
  "aggs": {
    "<aggregation_name>": {
      "<aggregation_type>": {
        "field": "<field_name>",
        ... other options ...
      }
    }
  }
}
```

## Simple Field Aggregations

### Terms Aggregation (Group By / Count By)

**Pattern:**
```json
{"aggs": {"<name>": {"terms": {"field": "<field>", "size": <N>}}}}
```

**Examples:**

**"How many jobs by status?"**
```json
{"aggs": {"by_status": {"terms": {"field": "status", "size": 10}}}}
```

**"Count jobs by team"**
```json
{"aggs": {"by_team": {"terms": {"field": "team_id", "size": 50}}}}
```

**"Jobs by remoteci"**
```json
{"aggs": {"by_remoteci": {"terms": {"field": "remoteci_id", "size": 100}}}}
```

### Date Histogram (Time-based Trends)

**Pattern:**
```json
{"aggs": {"<name>": {"date_histogram": {"field": "created_at", "calendar_interval": "<interval>"}}}}
```

Intervals: `"hour"`, `"day"`, `"week"`, `"month"`, `"quarter"`, `"year"`

**Examples:**

**"Daily job count"**
```json
{"aggs": {"daily": {"date_histogram": {"field": "created_at", "calendar_interval": "day"}}}}
```

**"Weekly trend"**
```json
{"aggs": {"weekly": {"date_histogram": {"field": "created_at", "calendar_interval": "week"}}}}
```

**"Hourly jobs today"**
```json
{"aggs": {"hourly": {"date_histogram": {"field": "created_at", "calendar_interval": "hour"}}}}
```

### Stats Aggregations (Numerical Analysis)

**Pattern:**
```json
{"aggs": {"<name>": {"<stats_type>": {"field": "<numeric_field>"}}}}
```

Stats types: `avg`, `min`, `max`, `sum`, `stats` (all), `value_count`

**Examples:**

**"Average job duration"**
```json
{"aggs": {"avg_duration": {"avg": {"field": "duration"}}}}
```

**"Duration statistics (min/max/avg/sum)"**
```json
{"aggs": {"duration_stats": {"stats": {"field": "duration"}}}}
```

**"Total job count"**
```json
{"aggs": {"total_jobs": {"value_count": {"field": "id"}}}}
```

## Nested Field Aggregations

Nested fields require special syntax with `nested` aggregation type.

### Pattern for Single-Level Nested

```json
{
  "aggs": {
    "<outer_name>": {
      "nested": {"path": "<nested_path>"},
      "aggs": {
        "<inner_name>": {
          "<aggregation_type>": {"field": "<nested_path>.<field>"}
        }
      }
    }
  }
}
```

### Components (Single Nested)

**"OCP version distribution"**
```json
{
  "aggs": {
    "components_agg": {
      "nested": {"path": "components"},
      "aggs": {
        "ocp_only": {
          "filter": {"term": {"components.type": "ocp"}},
          "aggs": {
            "versions": {"terms": {"field": "components.version", "size": 50}}
          }
        }
      }
    }
  }
}
```

**"All component types"**
```json
{
  "aggs": {
    "component_types": {
      "nested": {"path": "components"},
      "aggs": {
        "types": {"terms": {"field": "components.type", "size": 20}}
      }
    }
  }
}
```

**"Component tags distribution"**
```json
{
  "aggs": {
    "component_tags": {
      "nested": {"path": "components"},
      "aggs": {
        "tags": {"terms": {"field": "components.tags", "size": 50}}
      }
    }
  }
}
```

### Team, RemoteCI, Pipeline, Topic (Single Nested)

**"Jobs by team name"**
```json
{
  "aggs": {
    "teams": {
      "nested": {"path": "team"},
      "aggs": {
        "by_name": {"terms": {"field": "team.name", "size": 50}}
      }
    }
  }
}
```

**"Jobs by remoteci name"**
```json
{
  "aggs": {
    "remotecis": {
      "nested": {"path": "remoteci"},
      "aggs": {
        "by_name": {"terms": {"field": "remoteci.name", "size": 100}}
      }
    }
  }
}
```

**"Jobs by pipeline"**
```json
{
  "aggs": {
    "pipelines": {
      "nested": {"path": "pipeline"},
      "aggs": {
        "by_name": {"terms": {"field": "pipeline.name", "size": 50}}
      }
    }
  }
}
```

**"Jobs by topic"**
```json
{
  "aggs": {
    "topics": {
      "nested": {"path": "topic"},
      "aggs": {
        "by_name": {"terms": {"field": "topic.name", "size": 50}}
      }
    }
  }
}
```

### Test Results (Triple Nested!)

Tests have a 3-level structure: `tests` → `testsuites` → `testcases`

**Pattern:**
```json
{
  "aggs": {
    "tests_agg": {
      "nested": {"path": "tests"},
      "aggs": {
        "testsuites_agg": {
          "nested": {"path": "tests.testsuites"},
          "aggs": {
            "testcases_agg": {
              "nested": {"path": "tests.testsuites.testcases"},
              "aggs": {
                "<final_agg>": {...}
              }
            }
          }
        }
      }
    }
  }
}
```

**Examples:**

**"Test results by action (success/failure/error)"**
```json
{
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
                "by_action": {"terms": {"field": "tests.testsuites.testcases.action", "size": 10}}
              }
            }
          }
        }
      }
    }
  }
}
```

**"Average test execution time"**
```json
{
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
                "avg_time": {"avg": {"field": "tests.testsuites.testcases.time"}}
              }
            }
          }
        }
      }
    }
  }
}
```

**"Top failing tests"**
```json
{
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
                  "filter": {"term": {"tests.testsuites.testcases.action": "failure"}},
                  "aggs": {
                    "top_tests": {"terms": {"field": "tests.testsuites.testcases.name", "size": 20}}
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

## Sub-Aggregations (Multi-Dimensional Analysis)

You can nest aggregations to get multi-dimensional breakdowns.

**"Daily jobs with status breakdown"**
```json
{
  "aggs": {
    "daily": {
      "date_histogram": {"field": "created_at", "calendar_interval": "day"},
      "aggs": {
        "by_status": {"terms": {"field": "status"}},
        "avg_duration": {"avg": {"field": "duration"}}
      }
    }
  }
}
```

**"Status breakdown with average duration per status"**
```json
{
  "aggs": {
    "by_status": {
      "terms": {"field": "status"},
      "aggs": {
        "avg_duration": {"avg": {"field": "duration"}},
        "total_count": {"value_count": {"field": "id"}}
      }
    }
  }
}
```

**"OCP versions with daily trend for each version"**
```json
{
  "aggs": {
    "components_agg": {
      "nested": {"path": "components"},
      "aggs": {
        "ocp_only": {
          "filter": {"term": {"components.type": "ocp"}},
          "aggs": {
            "versions": {
              "terms": {"field": "components.version", "size": 50},
              "aggs": {
                "back_to_jobs": {
                  "reverse_nested": {},
                  "aggs": {
                    "daily": {"date_histogram": {"field": "created_at", "calendar_interval": "day"}}
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

## Reverse Nested

When inside a nested aggregation and you need to access the parent document level, use `reverse_nested`.

**Example: OCP versions with job status for each version**
```json
{
  "aggs": {
    "components_agg": {
      "nested": {"path": "components"},
      "aggs": {
        "ocp_versions": {
          "filter": {"term": {"components.type": "ocp"}},
          "aggs": {
            "versions": {
              "terms": {"field": "components.version", "size": 20},
              "aggs": {
                "back_to_jobs": {
                  "reverse_nested": {},
                  "aggs": {
                    "by_status": {"terms": {"field": "status"}}
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

## Common User Request Patterns

### Natural Language → Aggregation Mapping

| User Request | Aggregation Type | Example |
|--------------|------------------|---------|
| "How many X?" | terms count | `{"aggs": {"count_x": {"terms": {"field": "x"}}}}` |
| "Average/mean X" | avg | `{"aggs": {"avg_x": {"avg": {"field": "x"}}}}` |
| "Min/max X" | min/max or stats | `{"aggs": {"stats_x": {"stats": {"field": "x"}}}}` |
| "Daily/weekly trend" | date_histogram | `{"aggs": {"trend": {"date_histogram": {"field": "created_at", "calendar_interval": "day"}}}}` |
| "Distribution of X" | terms | `{"aggs": {"dist": {"terms": {"field": "x", "size": 50}}}}` |
| "Jobs by status" | terms on status | See examples above |
| "Failure rate" | terms with bucket_script or filters | Filter failures vs total |
| "Top N X" | terms with size | `{"terms": {"field": "x", "size": N}}` |

## Field Reference (From ES Mapping)

### Simple Fields (Direct Aggregation)
- `status` (keyword): job status
- `tags` (keyword array): job tags
- `team_id`, `remoteci_id`, `pipeline_id`, `topic_id`, `product_id` (keyword): IDs
- `created_at`, `updated_at` (date): timestamps
- `duration` (long): job duration in seconds
- `state`, `name` (keyword)

### Nested Fields (Require Nested Aggregation)
- `components`: type, name, version, tags, canonical_project_name, state, team_id, topic_id
- `tests.testsuites.testcases`: name, action, classname, time, type, message
- `team`: id, name, state, external, has_pre_release_access
- `remoteci`: id, name, state, public
- `pipeline`: id, name, state
- `topic`: id, name, component_types, export_control, product_id
- `files`: id, name, mime, size, state
- `keys_values`: key, value
- `nodes.hardware`: (nested within nested) - system info, CPU, memory, BIOS, devices
- `nodes.kernel`: (nested within nested) - version, params

## Tips for Building Aggregations

1. **Start simple**: Begin with a basic terms or date_histogram aggregation
2. **Add filters**: Use filter aggregations to narrow down before grouping
3. **Use reverse_nested**: When you need to go back to parent documents from nested context
4. **Set appropriate size**: For terms aggregations, set `size` large enough (default is 10)
5. **Combine aggregations**: Use sub-aggregations for multi-dimensional analysis
6. **Test incrementally**: Build complex aggregations step by step

## Error Patterns to Avoid

❌ **Forgetting nested wrapper for nested fields**
```json
// WRONG - won't work for components.version
{"aggs": {"versions": {"terms": {"field": "components.version"}}}}
```

✅ **Correct - with nested aggregation**
```json
{"aggs": {"components_agg": {"nested": {"path": "components"}, "aggs": {"versions": {"terms": {"field": "components.version"}}}}}}
```

❌ **Using wrong field path in nested aggregation**
```json
// WRONG - missing the full path
{"nested": {"path": "tests"}, "aggs": {"by_action": {"terms": {"field": "action"}}}}
```

✅ **Correct - full path from root**
```json
{"nested": {"path": "tests.testsuites.testcases"}, "aggs": {"by_action": {"terms": {"field": "tests.testsuites.testcases.action"}}}}
```

❌ **Forgetting size parameter for large datasets**
```json
// WRONG - only returns 10 items (default)
{"aggs": {"versions": {"terms": {"field": "components.version"}}}}
```

✅ **Correct - explicit size**
```json
{"aggs": {"versions": {"terms": {"field": "components.version", "size": 100}}}}
```
