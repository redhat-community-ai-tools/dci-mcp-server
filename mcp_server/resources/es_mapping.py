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

"""MCP resources for ElasticSearch mapping."""

import json
from pathlib import Path

from fastmcp import FastMCP


def register_es_mapping_resource(mcp: FastMCP) -> None:
    """Register ElasticSearch mapping as an MCP resource."""

    @mcp.resource("dci://elasticsearch/mapping")
    async def get_es_mapping() -> str:
        """
        Get the ElasticSearch mapping for DCI jobs index.

        This mapping describes the structure of job documents in Elasticsearch,
        including field types and nested relationships. Use this to construct
        correct aggregation queries.

        The mapping is in ElasticSearch 7.16 format.
        """
        # Get the path to the ES mapping file
        mapping_path = (
            Path(__file__).parent.parent.parent / "ES_mapping" / "mapping.json"
        )

        if not mapping_path.exists():
            return json.dumps({"error": "ES mapping file not found"}, indent=2)

        try:
            with open(mapping_path) as f:
                mapping_data = json.load(f)
            return json.dumps(mapping_data, indent=2)
        except Exception as e:
            return json.dumps(
                {"error": f"Failed to load ES mapping: {str(e)}"}, indent=2
            )
