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

        # Set environment variables expected by dciclient
        import os

        if self.user_id and self.user_secret:
            os.environ["DCI_LOGIN"] = self.user_id
            os.environ["DCI_PASSWORD"] = self.user_secret
        if not os.environ.get("DCI_CS_URL"):
            os.environ["DCI_CS_URL"] = "https://api.distributed-ci.io"

    def _get_dci_context(self) -> Any:
        """Get DCI context for API calls."""

        if self.api_key:
            return build_dci_context(api_key=self.api_key)
        else:
            return build_dci_context(
                dci_login=self.user_id,
                dci_password=self.user_secret,
            )
