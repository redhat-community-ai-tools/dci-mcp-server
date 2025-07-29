"""DCI product service for managing products."""

from typing import Any

from dciclient.v1.api import product

from .dci_base_service import DCIBaseService


class DCIProductService(DCIBaseService):
    """Service class for DCI product operations."""

    def get_product(self, product_id: str) -> Any:
        """
        Get a specific product by ID.

        Args:
            product_id: The ID of the product to retrieve

        Returns:
            Product data as dictionary, or None if not found
        """
        try:
            context = self._get_dci_context()
            result = product.get(context, product_id)
            if hasattr(result, "json"):
                return result.json()
            return result
        except Exception as e:
            print(f"Error getting product {product_id}: {e}")
            return None

    def list_products(
        self,
        limit: int | None = None,
        offset: int | None = None,
        where: str | None = None,
        sort: str | None = None,
    ) -> list:
        """
        List products with optional filtering and pagination.

        Args:
            limit: Maximum number of products to return
            offset: Number of products to skip
            where: Filter criteria (e.g., "name:RHEL")
            sort: Sort criteria (e.g., "-created_at")

        Returns:
            List of product dictionaries
        """
        try:
            context = self._get_dci_context()
            # Provide default values for required parameters
            if limit is None:
                limit = 50
            if offset is None:
                offset = 0

            result = product.list(
                context, limit=limit, offset=offset, where=where, sort=sort
            )
            if hasattr(result, "json"):
                data = result.json()
                return data.get("products", []) if isinstance(data, dict) else []
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error listing products: {e}")
            return []

    def list_product_teams(self, product_id: str) -> Any:
        """
        Get teams associated with a specific product.

        Args:
            product_id: The ID of the product

        Returns:
            List of team dictionaries
        """
        try:
            context = self._get_dci_context()
            result = product.list_teams(context, product_id)
            if hasattr(result, "json"):
                data = result.json()
                return data.get("teams", []) if isinstance(data, dict) else []
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error getting teams for product {product_id}: {e}")
            return []
