"""
Commodities Resource

Commodity catalog and category operations.
"""

from typing import List, Dict, Any


class CommoditiesResource:
    """Resource for commodity catalog operations."""

    def __init__(self, client):
        """Initialize commodities resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self) -> List[Dict[str, Any]]:
        """Get list of all available commodities.

        Returns:
            List of commodity objects with code, name, and metadata

        Example:
            >>> commodities = client.commodities.list()
            >>> for commodity in commodities:
            ...     print(f"{commodity['code']}: {commodity['name']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/commodities"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def get(self, code: str) -> Dict[str, Any]:
        """Get details for a single commodity.

        Args:
            code: Commodity code (e.g., "BRENT_CRUDE_USD")

        Returns:
            Commodity object with detailed information

        Example:
            >>> commodity = client.commodities.get("BRENT_CRUDE_USD")
            >>> print(f"Name: {commodity['name']}")
            >>> print(f"Category: {commodity['category']}")
            >>> print(f"Unit: {commodity['unit']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/commodities/{code}"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def categories(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get commodities grouped by category.

        Returns:
            Dictionary mapping category names to lists of commodities

        Example:
            >>> categories = client.commodities.categories()
            >>> for category, commodities in categories.items():
            ...     print(f"{category}: {len(commodities)} commodities")
            >>>
            >>> # Access specific category
            >>> crude_oils = categories.get('Crude Oil', [])
        """
        response = self.client.request(
            method="GET",
            path="/v1/commodities/categories"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response
