"""
EI Oil Inventories Resource

Energy Intelligence oil inventory data operations.
"""

from typing import List, Dict, Any, Optional


class EIOilInventoriesResource:
    """Resource for Energy Intelligence oil inventory data."""

    def __init__(self, client):
        """Initialize EI oil inventories resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self, **params) -> List[Dict[str, Any]]:
        """Get all oil inventory data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of oil inventory records

        Example:
            >>> inventories = client.ei.oil_inventories.list()
            >>> for inv in inventories:
            ...     print(f"{inv['region']}: {inv['volume']} barrels")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/oil_inventories",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def get(self, id: str) -> Dict[str, Any]:
        """Get a specific oil inventory record by ID.

        Args:
            id: Oil inventory record ID

        Returns:
            Oil inventory record details

        Example:
            >>> inv = client.ei.oil_inventories.get("123")
            >>> print(f"Volume: {inv['volume']} barrels")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/oil_inventories/{id}"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def latest(self) -> Dict[str, Any]:
        """Get latest oil inventory data.

        Returns:
            Latest oil inventory summary

        Example:
            >>> latest = client.ei.oil_inventories.latest()
            >>> print(f"Total inventory: {latest['total']} barrels")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/oil_inventories/latest"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def summary(self) -> Dict[str, Any]:
        """Get oil inventory summary.

        Returns:
            Summary statistics for oil inventories

        Example:
            >>> summary = client.ei.oil_inventories.summary()
            >>> print(f"Crude: {summary['crude']} barrels")
            >>> print(f"Products: {summary['products']} barrels")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/oil_inventories/summary"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def by_product(self, **params) -> List[Dict[str, Any]]:
        """Get oil inventories by product type.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of product inventories

        Example:
            >>> products = client.ei.oil_inventories.by_product()
            >>> for product in products:
            ...     print(f"{product['type']}: {product['volume']} barrels")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/oil_inventories/by_product",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def historical(self, **params) -> List[Dict[str, Any]]:
        """Get historical oil inventory data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of historical inventory records

        Example:
            >>> history = client.ei.oil_inventories.historical()
            >>> for record in history:
            ...     print(f"{record['date']}: {record['volume']} barrels")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/oil_inventories/historical",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def cushing(self) -> Dict[str, Any]:
        """Get Cushing, OK oil inventory data.

        Returns:
            Cushing inventory data

        Example:
            >>> cushing = client.ei.oil_inventories.cushing()
            >>> print(f"Cushing inventory: {cushing['volume']} barrels")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/oil_inventories/cushing"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response
