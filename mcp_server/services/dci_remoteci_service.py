"""DCI remoteci service for managing remotecis."""

import sys
from typing import Any

from dciclient.v1.api import remoteci

from .dci_base_service import DCIBaseService


class DCIRemoteCIService(DCIBaseService):
    """Service class for DCI remoteci operations."""

    def get_remoteci(self, remoteci_id: str) -> Any:
        """
        Get a specific remoteci by ID.

        Args:
            remoteci_id: The ID of the remoteci to retrieve

        Returns:
            Remoteci data as dictionary, or None if not found
        """
        try:
            context = self._get_dci_context()
            result = remoteci.get(context, remoteci_id)
            if hasattr(result, "json"):
                return result.json()
            return result
        except Exception as e:
            print(f"Error getting remoteci {remoteci_id}: {e}")
            return None

    def query_remotecis(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        sort: str | None = None,
    ) -> list:
        """
        List remotecis using the advanced query syntax.

        Args:
            query: query criteria (e.g., "and(ilike(name,dallas),contains(tags,ga))")
            limit: Maximum number of remotecis to return (default: 50)
            offset: Number of remotecis to skip (default: 0)
            sort: Sort criteria (e.g., "-created_at")

        Returns:
            A dictionary with remotecis data or an empty dictionary on error
        """
        try:
            context = self._get_dci_context()
            return remoteci.list(
                context, query=query, limit=limit, offset=offset, sort=sort
            ).json()
        except Exception as e:
            print(f"Error listing remotecis: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            return {"error": str(e), "message": "Failed to list remotecis."}

    def list_remotecis(
        self,
        limit: int | None = None,
        offset: int | None = None,
        where: str | None = None,
        sort: str | None = None,
    ) -> list:
        """
        List remotecis with optional filtering and pagination.

        Args:
            limit: Maximum number of remotecis to return
            offset: Number of remotecis to skip
            where: Filter criteria (e.g., "name:dallas")
            sort: Sort criteria (e.g., "-created_at")

        Returns:
            List of remoteci dictionaries
        """
        try:
            context = self._get_dci_context()
            # Provide default values for required parameters
            if limit is None:
                limit = 50
            if offset is None:
                offset = 0

            result = remoteci.list(
                context, limit=limit, offset=offset, where=where, sort=sort
            )
            if hasattr(result, "json"):
                data = result.json()
                return data.get("remotecis", []) if isinstance(data, dict) else []
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error listing remotecis: {e}")
            return []
