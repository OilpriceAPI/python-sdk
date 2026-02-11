"""
EI Drilling Productivity Resource

Energy Intelligence drilling productivity data operations.
"""

from typing import List, Dict, Any, Optional


class EIDrillingProductivityResource:
    """Resource for Energy Intelligence drilling productivity data."""

    def __init__(self, client):
        """Initialize EI drilling productivity resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self, **params) -> List[Dict[str, Any]]:
        """Get all drilling productivity data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of drilling productivity records

        Example:
            >>> productivity = client.ei.drilling_productivity.list()
            >>> for record in productivity:
            ...     print(f"{record['basin']}: {record['productivity']} bpd/rig")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/drilling_productivities",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def get(self, id: str) -> Dict[str, Any]:
        """Get a specific drilling productivity record by ID.

        Args:
            id: Drilling productivity record ID

        Returns:
            Drilling productivity record details

        Example:
            >>> record = client.ei.drilling_productivity.get("123")
            >>> print(f"Productivity: {record['productivity']} bpd/rig")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/drilling_productivities/{id}"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def latest(self) -> Dict[str, Any]:
        """Get latest drilling productivity data.

        Returns:
            Latest drilling productivity summary

        Example:
            >>> latest = client.ei.drilling_productivity.latest()
            >>> print(f"Average productivity: {latest['average']} bpd/rig")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/drilling_productivities/latest"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def summary(self) -> Dict[str, Any]:
        """Get drilling productivity summary.

        Returns:
            Summary statistics for drilling productivity

        Example:
            >>> summary = client.ei.drilling_productivity.summary()
            >>> print(f"Total production: {summary['total_production']} bpd")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/drilling_productivities/summary"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def duc_wells(self, **params) -> List[Dict[str, Any]]:
        """Get DUC (Drilled but Uncompleted) wells data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of DUC well records

        Example:
            >>> ducs = client.ei.drilling_productivity.duc_wells()
            >>> for duc in ducs:
            ...     print(f"{duc['basin']}: {duc['count']} DUCs")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/drilling_productivities/duc_wells",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def by_basin(self, **params) -> List[Dict[str, Any]]:
        """Get drilling productivity by basin.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of basin productivity records

        Example:
            >>> basins = client.ei.drilling_productivity.by_basin()
            >>> for basin in basins:
            ...     print(f"{basin['name']}: {basin['productivity']} bpd/rig")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/drilling_productivities/by_basin",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def historical(self, **params) -> List[Dict[str, Any]]:
        """Get historical drilling productivity data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of historical productivity records

        Example:
            >>> history = client.ei.drilling_productivity.historical()
            >>> for record in history:
            ...     print(f"{record['date']}: {record['productivity']} bpd/rig")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/drilling_productivities/historical",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def trends(self, **params) -> List[Dict[str, Any]]:
        """Get drilling productivity trends.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of trend data points

        Example:
            >>> trends = client.ei.drilling_productivity.trends()
            >>> for point in trends:
            ...     print(f"{point['date']}: {point['trend']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/drilling_productivities/trends",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response
