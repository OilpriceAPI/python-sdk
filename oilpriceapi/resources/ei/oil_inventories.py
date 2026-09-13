"""
EI Oil Inventories Resource

Energy Intelligence oil inventory data operations.
"""

from typing import Any, Dict, List

from ._envelopes import ei_data, unwrap_ei_collection


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

        return ei_data(response)

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

        return ei_data(response)

    def latest(self) -> Dict[str, Any]:
        """Get latest oil inventory data.

        Returns:
            Report object with ``id``, ``report_date``, ``week_ending``,
            ``source``, ``last_updated``, ``summary`` and ``inventories``.

        Example:
            >>> latest = client.ei.oil_inventories.latest()
            >>> print(f"Week ending: {latest['week_ending']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/oil_inventories/latest"
        )

        return ei_data(response)

    def summary(self) -> Dict[str, Any]:
        """Get oil inventory summary.

        Returns:
            Object with ``week_ending``, ``inventories`` and ``headline``.

        Example:
            >>> summary = client.ei.oil_inventories.summary()
            >>> print(summary['headline'])
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/oil_inventories/summary"
        )

        return ei_data(response)

    def by_product(self, **params) -> List[Dict[str, Any]]:
        """Get oil inventories by product type.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``products`` list from ``data``. Each record has
            ``product_type``, ``location``, ``volume_mmbbl``,
            ``week_over_week``, ``direction`` and ``vs_five_year_avg``.

        Example:
            >>> products = client.ei.oil_inventories.by_product()
            >>> for product in products:
            ...     print(f"{product['product_type']}: {product['volume_mmbbl']} MMbbl")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/oil_inventories/by_product",
            params=params
        )

        return unwrap_ei_collection(
            response, collection="products", subject="oil-inventory by-product"
        )

    def historical(self, **params) -> List[Dict[str, Any]]:
        """Get historical oil inventory data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``records`` list from ``data``. Each record has
            ``week_ending``, ``volume_mmbbl`` and ``week_over_week``.

        Example:
            >>> history = client.ei.oil_inventories.historical()
            >>> for record in history:
            ...     print(f"{record['week_ending']}: {record['volume_mmbbl']} MMbbl")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/oil_inventories/historical",
            params=params
        )

        return unwrap_ei_collection(
            response, collection="records", subject="oil-inventory historical"
        )

    def cushing(self) -> Dict[str, Any]:
        """Get Cushing, OK oil inventory data.

        Returns:
            Object with ``location``, ``latest`` and ``history``.

        Example:
            >>> cushing = client.ei.oil_inventories.cushing()
            >>> print(f"Cushing: {cushing['latest']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/oil_inventories/cushing"
        )

        return ei_data(response)
