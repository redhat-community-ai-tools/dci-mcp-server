"""Base DCI service for common authentication and context management."""

import os
from typing import Any

from dciclient.v1.api.context import build_dci_context, build_signature_context


class DCIBaseService:
    """Base service class for DCI API interactions."""

    @staticmethod
    def decoded(response: Any) -> Any:
        """The response body, or raise naming the status and quoting the body.

        A gateway or proxy error arrives as HTML: the bare "Expecting value"
        of a JSON decode says nothing about which failure it was.
        """
        try:
            return response.json()
        except ValueError as exc:
            body = " ".join(response.text.split())[:200]
            raise ValueError(
                f"HTTP {response.status_code}, body is not JSON: {body}"
            ) from exc

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
