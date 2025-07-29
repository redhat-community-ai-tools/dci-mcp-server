"""DCI team service for managing teams."""

from typing import Any

from dciclient.v1.api import team

from .dci_base_service import DCIBaseService


class DCITeamService(DCIBaseService):
    """Service class for DCI team operations."""

    def get_team(self, team_id: str) -> dict[str, Any] | None:
        """
        Get a specific team by ID.

        Args:
            team_id: The ID of the team to retrieve

        Returns:
            Team data as dictionary, or None if not found
        """
        try:
            context = self._get_dci_context()
            result = team.get(context, team_id)
            return result
        except Exception as e:
            print(f"Error getting team {team_id}: {e}")
            return None

    def list_teams(
        self,
        limit: int | None = None,
        offset: int | None = None,
        where: str | None = None,
        sort: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List teams with optional filtering and pagination.

        Args:
            limit: Maximum number of teams to return
            offset: Number of teams to skip
            where: Filter criteria (e.g., "name:like:qa")
            sort: Sort criteria (e.g., "created_at:desc")

        Returns:
            List of team dictionaries
        """
        try:
            context = self._get_dci_context()
            # Provide default values for required parameters
            if limit is None:
                limit = 50
            if offset is None:
                offset = 0

            result = team.list(
                context, limit=limit, offset=offset, where=where, sort=sort
            )
            return result
        except Exception as e:
            print(f"Error listing teams: {e}")
            return []
