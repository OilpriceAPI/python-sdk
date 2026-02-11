"""
Storage Resource

Oil inventory and storage data operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from typing import Union


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

    def history(
        self,
        code: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None
    ) -> List[Dict[str, Any]]:
        """Get historical storage data for a specific location.

        Args:
            code: Storage location code (e.g., "cushing", "spr", "padd1")
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            List of historical storage records

        Example:
            >>> history = client.storage.history(
            ...     code="cushing",
            ...     start_date="2024-01-01",
            ...     end_date="2024-12-31"
            ... )
            >>> for record in history:
            ...     print(f"{record['date']}: {record['value']} barrels")
        """
        params = {}
        if start_date:
            params["start_date"] = self._format_date(start_date)
        if end_date:
            params["end_date"] = self._format_date(end_date)

        response = self.client.request(
            method="GET",
            path=f"/v1/storage/{code}/history",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def _format_date(self, date_input: Union[str, date, datetime]) -> str:
        """Format date for API."""
        if isinstance(date_input, str):
            return date_input
        elif isinstance(date_input, datetime):
            return date_input.date().isoformat()
        elif isinstance(date_input, date):
            return date_input.isoformat()
        else:
            raise ValueError(f"Invalid date type: {type(date_input)}")
