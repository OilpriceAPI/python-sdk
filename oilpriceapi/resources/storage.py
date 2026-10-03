"""
Storage Resource

Oil inventory and storage data operations.
"""

from datetime import date, datetime
from typing import Any, Dict, Optional, Union

from ..resource_validators import format_date
from ._route_args import storage_history_code, storage_history_period


class StorageResource:
    """Resource for oil storage and inventory data."""

    def __init__(self, client):
        """Initialize storage resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def all(self) -> Dict[str, Any]:
        """Get all current storage data.

        Returns:
            Dictionary with all storage data including Cushing, SPR, and regional

        Example:
            >>> storage = client.storage.all()
            >>> print(f"Cushing: {storage['cushing']['value']} barrels")
            >>> print(f"SPR: {storage['spr']['value']} barrels")
        """
        response = self.client.request(
            method="GET",
            path="/v1/storage"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def cushing(self) -> Dict[str, Any]:
        """Get Cushing, OK storage data.

        Returns:
            Cushing inventory data

        Example:
            >>> cushing = client.storage.cushing()
            >>> print(f"Cushing Inventory: {cushing['value']} barrels")
            >>> print(f"Change: {cushing['change']} barrels")
        """
        response = self.client.request(
            method="GET",
            path="/v1/storage/cushing"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def spr(self) -> Dict[str, Any]:
        """Get Strategic Petroleum Reserve data.

        Returns:
            SPR inventory data

        Example:
            >>> spr = client.storage.spr()
            >>> print(f"SPR Inventory: {spr['value']} barrels")
            >>> print(f"Updated: {spr['updated_at']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/storage/spr"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def regional(self, region: Optional[str] = None) -> Dict[str, Any]:
        """Get regional storage data.

        Args:
            region: Optional region filter (e.g., "PADD1", "PADD2", "PADD3")

        Returns:
            Regional storage data

        Example:
            >>> regional = client.storage.regional()
            >>> for region, data in regional.items():
            ...     print(f"{region}: {data['value']} barrels")
            >>>
            >>> # Specific region
            >>> padd3 = client.storage.regional(region="PADD3")
        """
        params = {}
        if region:
            params["region"] = region

        response = self.client.request(
            method="GET",
            path="/v1/storage/regional",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def history(self, code: str, period: str = "90d") -> Dict[str, Any]:
        """Get historical storage data for a storage series.

        Calls ``GET /v1/storage/history/{code}``.

        Args:
            code: Storage series code: ``CUSHING_STORAGE``, ``US_SPR``,
                ``SINGAPORE_STORAGE_TOTAL`` or ``ARA_STORAGE_TOTAL``. The
                short forms ``"cushing"`` and ``"spr"`` are accepted.
            period: Lookback window: ``"7d"``, ``"30d"``, ``"90d"``
                (default), ``"1y"`` or ``"all"``.

        Returns:
            ``{"code", "period", "history": [...], "statistics": {...}}``.
            Each history record has ``value`` (million barrels),
            ``data_date``, ``week_change`` and ``capacity_utilization``.

        Example:
            >>> result = client.storage.history("cushing", period="30d")
            >>> for record in result["history"]:
            ...     print(f"{record['data_date']}: {record['value']}M bbl")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/storage/history/{storage_history_code(code)}",
            params={"period": storage_history_period(period)}
        )

        if "data" in response:
            return response["data"]
        return response

    def _format_date(self, date_input: Union[str, date, datetime]) -> str:
        """Format date for API."""
        return format_date(date_input)
