"""HTTP client utilities for making requests to external APIs."""

from typing import Any

import httpx

from ..config import get_dci_api_key


async def make_request(
    url: str, method: str = "GET", data: dict[str, Any] | None = None
) -> Any:
    """
    Make an HTTP request with optional authentication.

    Args:
        url: The URL to make the request to
        method: HTTP method (GET, POST, etc.)
        data: Optional data for the request body or query parameters

    Returns:
        JSON response as dictionary, or None/error dict if request fails
    """
    # DCI_API_KEY is optional - if not provided, requests will be made without
    # authentication
    api_key = get_dci_api_key()
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            if method.upper() == "GET":
                response = await client.request(
                    method, url, headers=headers, params=data
                )
            else:
                response = await client.request(method, url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        # Return error information instead of crashing
        return {"error": f"Request failed: {str(e)}", "url": url}
