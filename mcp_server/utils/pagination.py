"""Pagination utilities for DCI API calls."""

from collections.abc import Callable
from typing import Any


def fetch_all_pages(
    list_function: Callable, *args, page_size: int = 50, max_pages: int = 100, **kwargs
) -> list[dict[str, Any]]:
    """
    Fetch all pages of results from a paginated API call.

    Args:
        list_function: The service method to call (e.g., service.list_teams)
        *args: Positional arguments to pass to the list function
        page_size: Number of items per page (default: 50)
        max_pages: Maximum number of pages to fetch (default: 100)
        **kwargs: Keyword arguments to pass to the list function

    Returns:
        List of all items from all pages
    """
    all_results = []
    offset = 0
    page_count = 0

    while page_count < max_pages:
        # Call the list function with current offset
        page_results = list_function(*args, limit=page_size, offset=offset, **kwargs)

        # Handle Response objects by extracting JSON data
        if hasattr(page_results, "json"):
            page_data = page_results.json()
            if isinstance(page_data, list):
                page_items = page_data
            elif isinstance(page_data, dict):
                # Try common keys for data arrays in DCI API
                for key in [
                    "teams",
                    "jobs",
                    "files",
                    "pipelines",
                    "products",
                    "topics",
                    "components",
                    "data",
                ]:
                    if key in page_data:
                        page_items = page_data[key]
                        break
                else:
                    page_items = []
            else:
                page_items = []
        else:
            # Assume it's already a list
            page_items = page_results if isinstance(page_results, list) else []

        # If no results returned, we've reached the end
        if not page_items:
            break

        # Add results from this page
        all_results.extend(page_items)

        # If we got fewer results than requested, we've reached the end
        if len(page_items) < page_size:
            break

        # Move to next page
        offset += page_size
        page_count += 1

    return all_results


def fetch_all_with_progress(
    list_function: Callable, *args, page_size: int = 50, max_pages: int = 100, **kwargs
) -> dict[str, Any]:
    """
    Fetch all pages with progress information.

    Args:
        list_function: The service method to call
        *args: Positional arguments to pass to the list function
        page_size: Number of items per page (default: 50)
        max_pages: Maximum number of pages to fetch (default: 100)
        **kwargs: Keyword arguments to pass to the list function

    Returns:
        Dictionary with results and pagination info
    """
    all_results = []
    offset = 0
    page_count = 0

    while page_count < max_pages:
        # Call the list function with current offset
        page_results = list_function(*args, limit=page_size, offset=offset, **kwargs)

        # Handle Response objects by extracting JSON data
        if hasattr(page_results, "json"):
            page_data = page_results.json()
            if isinstance(page_data, list):
                page_items = page_data
            elif isinstance(page_data, dict):
                # Try common keys for data arrays in DCI API
                for key in [
                    "teams",
                    "jobs",
                    "files",
                    "pipelines",
                    "products",
                    "topics",
                    "components",
                    "data",
                ]:
                    if key in page_data:
                        page_items = page_data[key]
                        break
                else:
                    page_items = []
            else:
                page_items = []
        else:
            # Assume it's already a list
            page_items = page_results if isinstance(page_results, list) else []

        # If no results returned, we've reached the end
        if not page_items:
            break

        # Add results from this page
        all_results.extend(page_items)
        page_count += 1

        # If we got fewer results than requested, we've reached the end
        if len(page_items) < page_size:
            break

        # Move to next page
        offset += page_size

    return {
        "results": all_results,
        "total_count": len(all_results),
        "pages_fetched": page_count,
        "page_size": page_size,
        "reached_end": len(page_items) < page_size if page_items else True,
    }
