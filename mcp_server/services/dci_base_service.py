"""Base DCI service for common authentication and context management."""

from typing import Any

from dciclient.v1.api.context import build_dci_context

from ..config import get_dci_api_key, get_dci_user_id, get_dci_user_secret


class DCIBaseService:
    """Base service class for DCI API interactions."""

    def __init__(self) -> None:
        """Initialize the DCI base service with authentication."""
        self.api_key = get_dci_api_key()
        self.user_id = get_dci_user_id()
        self.user_secret = get_dci_user_secret()

        if not self.api_key and not (self.user_id and self.user_secret):
            raise ValueError(
                "DCI authentication not configured. Set either DCI_API_KEY or "
                "DCI_USER_ID+DCI_USER_SECRET"
            )

    def _get_dci_context(self) -> Any:
        """Get DCI context for API calls."""

        if self.api_key:
            return build_dci_context(api_key=self.api_key)
        else:
            return build_dci_context(
                user_id=self.user_id,
                user_secret=self.user_secret,
            )
