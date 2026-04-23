# Optimisation des requêtes DCI avec ElasticSearch

## Problème actuel

Lors d'analyses statistiques, nous récupérons tous les documents complets puis les analysons en Python :
- ❌ Transfert de données massif (10-50 MB pour 200 jobs)
- ❌ Parsing et analyse CPU-intensive côté client
- ❌ Lent et inefficace

## Solutions d'optimisation

### 1. Filtrage de champs (Disponible maintenant)

Le paramètre `fields` permet de réduire la taille des réponses :

```python
# Au lieu de récupérer tout :
search_dci_jobs(
    query="(status='failure')",
    limit=200
)  # → 10 MB

# Récupérer seulement les champs nécessaires :
search_dci_jobs(
    query="(status='failure')",
    fields=["id", "status", "created_at", "components.version"],
    limit=200
)  # → 1 MB (10x plus petit)
```

**Avantages** :
- ✅ Déjà disponible
- ✅ Réduit le transfert réseau
- ✅ Parsing plus rapide

**Limites** :
- ❌ Nécessite toujours de récupérer tous les documents
- ❌ Analyse en Python encore nécessaire

### 2. Agrégations ElasticSearch (À implémenter)

Les agrégations ES calculent les statistiques côté serveur.

#### Exemple : Statistiques de tests PTP

**Requête actuelle (inefficace)** :
```python
# 1. Récupérer 200 jobs complets
result = search_dci_jobs(
    query="((tests.testsuites.testcases.name=~'.*PTP.*LOCKED.*'))",
    limit=200
)

# 2. Analyser en Python
for job in result['hits']:
    for test in job['tests']:
        for testsuite in test['testsuites']:
            for testcase in testsuite['testcases']:
                if 'PTP' in testcase['name']:
                    stats[testcase['action']] += 1
```

**Requête optimale avec agrégations** :
```json
{
  "query": "((tests.testsuites.testcases.name=~'.*PTP.*LOCKED.*'))",
  "size": 0,
  "aggs": {
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
            "by_ocp_version": {
              "terms": {"field": "components.version", "size": 50}
            },
            "avg_time": {
              "avg": {"field": "tests.testsuites.testcases.time"}
            },
            "by_date": {
              "date_histogram": {
                "field": "created_at",
                "calendar_interval": "day"
              },
              "aggs": {
                "by_action": {
                  "terms": {"field": "tests.testsuites.testcases.action"}
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

**Résultat** :
```json
{
  "aggregations": {
    "test_results": {
      "ptp_tests": {
        "by_action": {
          "buckets": [
            {"key": "success", "doc_count": 186},
            {"key": "failure", "doc_count": 13},
            {"key": "error", "doc_count": 1}
          ]
        },
        "by_ocp_version": {
          "buckets": [
            {"key": "4.19.0-nightly", "doc_count": 136},
            {"key": "4.20.0", "doc_count": 64}
          ]
        },
        "avg_time": {"value": 64.9},
        "by_date": {
          "buckets": [
            {
              "key_as_string": "2026-02-10",
              "by_action": {
                "buckets": [
                  {"key": "success", "doc_count": 8},
                  {"key": "failure", "doc_count": 2}
                ]
              }
            }
          ]
        }
      }
    }
  }
}
```

**Avantages** :
- ✅ Transfert minimal (~1 KB vs 10 MB)
- ✅ Calcul distribué côté ES
- ✅ Résultats instantanés
- ✅ Support des groupements complexes

#### Exemple : Heatmap Intel Network Cards

**Actuel** :
```python
# Récupérer 83 jobs avec nodes.hardware → 5 MB
result = search_dci_jobs(
    query="(nodes.hardware.cpu_vendor='Intel')",
    limit=100
)
# Analyser en Python...
```

**Avec agrégations** :
```json
{
  "query": "(nodes.hardware.cpu_vendor='Intel')",
  "size": 0,
  "aggs": {
    "by_date": {
      "date_histogram": {
        "field": "created_at",
        "calendar_interval": "day"
      },
      "aggs": {
        "by_ocp_version": {
          "terms": {"field": "components.version", "size": 20},
          "aggs": {
            "network_cards": {
              "nested": {"path": "nodes.hardware.network_interfaces"},
              "aggs": {
                "by_model": {
                  "terms": {
                    "field": "nodes.hardware.network_interfaces.model",
                    "size": 50
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

## Implémentation recommandée

### Phase 1 : Support côté serveur (API DCI)

Modifier l'endpoint `/analytics/jobs` pour accepter `aggs` :

```python
# dci-control-server
@app.route("/analytics/jobs", methods=["POST"])
def analytics_jobs():
    query = request.json.get("query")
    aggs = request.json.get("aggs")  # Nouveau

    es_query = convert_dci_query_to_es(query)

    if aggs:
        es_query["aggs"] = aggs
        es_query["size"] = 0  # Pas de documents

    result = es_client.search(index="jobs", body=es_query)
    return jsonify(result)
```

### Phase 2 : Support client (dciclient)

```python
# dciclient/v1/api/job.py
def aggregate(context, query, aggs, **kwargs):
    """
    Execute aggregations on jobs.

    Args:
        query: DCI query string
        aggs: ElasticSearch aggregation DSL (dict)

    Returns:
        Aggregation results
    """
    uri = "%s/analytics/jobs" % context.dci_cs_api
    kwargs['query'] = query
    kwargs['aggs'] = aggs
    r = context.session.post(uri, json=kwargs)
    return r
```

### Phase 3 : Support MCP (dci-mcp-server)

```python
# mcp_server/services/dci_job_service.py
def aggregate_jobs(self, query: str, aggregations: dict) -> dict:
    """Execute aggregations on jobs."""
    try:
        context = self._get_dci_context()
        return job.aggregate(context, query=query, aggs=aggregations).json()
    except Exception as e:
        return {"error": str(e)}

# mcp_server/tools/job_tools.py
@mcp.tool()
async def aggregate_dci_jobs(
    query: str,
    aggregations: dict,
) -> str:
    """
    Execute ElasticSearch aggregations on DCI jobs for statistics.

    Instead of retrieving all documents and analyzing in Python,
    this tool computes statistics server-side using ES aggregations.

    Example aggregations:
    - Count by status: {"by_status": {"terms": {"field": "status"}}}
    - Average duration: {"avg_duration": {"avg": {"field": "duration"}}}
    - Daily histogram: {"by_date": {"date_histogram": {"field": "created_at", "calendar_interval": "day"}}}

    Returns:
        JSON with aggregation results under "aggregations" key
    """
    service = DCIJobService()
    result = service.aggregate_jobs(query=query, aggregations=aggregations)
    return json.dumps(result.get("aggregations", {}), indent=2)
```

## Cas d'usage

### Avant (inefficace)
```python
# Récupère 200 jobs × 50 KB = 10 MB
jobs = search_dci_jobs(
    query="(status='failure')",
    limit=200
)

# Compte en Python
stats = {"by_status": {}, "by_version": {}}
for job in jobs:
    stats["by_status"][job["status"]] += 1
    stats["by_version"][job["components"][0]["version"]] += 1
```

### Après (optimal)
```python
# Récupère juste les compteurs ~ 1 KB
stats = aggregate_dci_jobs(
    query="(status='failure')",
    aggregations={
        "by_status": {"terms": {"field": "status"}},
        "by_version": {"terms": {"field": "components.version"}}
    }
)
# Résultat déjà calculé !
```

## Gains attendus

| Métrique | Avant | Après | Gain |
|----------|-------|-------|------|
| **Transfert réseau** | 10 MB | 1 KB | **10,000x** |
| **Temps de réponse** | 5-10s | <1s | **10x** |
| **CPU client** | High | Minimal | **100x** |
| **Évolutivité** | Limitée | Excellente | ∞ |

## Prochaines étapes

1. ✅ Documenter le problème (ce fichier)
2. ⬜ Proposer l'implémentation à l'équipe DCI
3. ⬜ Implémenter côté serveur (dci-control-server)
4. ⬜ Ajouter à dciclient
5. ⬜ Ajouter au MCP server
6. ⬜ Migrer les analyses existantes
