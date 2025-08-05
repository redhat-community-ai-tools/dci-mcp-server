"""Base DCI service for common authentication and context management."""

import os
from typing import Any

from dciclient.v1.api.context import build_dci_context, build_signature_context


class DCIBaseService:
    """Base service class for DCI API interactions."""

    def _get_dci_context(self) -> Any:
        """Get DCI context for API calls."""

        if "DCI_CLIENT_ID" in os.environ and "DCI_API_SECRET" in os.environ:
            return build_signature_context(
                dci_client_id=os.environ.get("DCI_CLIENT_ID"),
                dci_api_secret=os.environ.get("DCI_API_SECRET"),
            )
        else:
            return build_dci_context(
                dci_login=os.environ.get("DCI_LOGIN"),
                dci_password=os.environ.get("DCI_PASSWORD"),
            )
