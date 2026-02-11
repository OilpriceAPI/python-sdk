"""
EI Rig Counts Resource

Energy Intelligence rig count data operations.
"""

from typing import List, Dict, Any, Optional


class EIRigCountsResource:
    """Resource for Energy Intelligence rig count data."""

    def __init__(self, client):
        """Initialize EI rig counts resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self, **params) -> List[Dict[str, Any]]:
        """Get all rig count data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of rig count records

        Example:
            >>> rigs = client.ei.rig_counts.list()
            >>> for rig in rigs:
            ...     print(f"{rig['basin']}: {rig['count']} rigs")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/rig_counts",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def get(self, id: str) -> Dict[str, Any]:
        """Get a specific rig count record by ID.

        Args:
            id: Rig count record ID

        Returns:
            Rig count record details

        Example:
            >>> rig = client.ei.rig_counts.get("123")
            >>> print(f"Rig count: {rig['count']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/rig_counts/{id}"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def latest(self) -> Dict[str, Any]:
        """Get latest rig count data.

        Returns:
            Latest rig count summary

        Example:
            >>> latest = client.ei.rig_counts.latest()
            >>> print(f"Total rigs: {latest['total']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/rig_counts/latest"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def by_basin(self, **params) -> List[Dict[str, Any]]:
        """Get rig counts by basin.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of basin rig counts

        Example:
            >>> basins = client.ei.rig_counts.by_basin()
            >>> for basin in basins:
            ...     print(f"{basin['name']}: {basin['rig_count']} rigs")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/rig_counts/by_basin",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def by_state(self, **params) -> List[Dict[str, Any]]:
        """Get rig counts by state.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of state rig counts

        Example:
            >>> states = client.ei.rig_counts.by_state()
            >>> for state in states:
            ...     print(f"{state['name']}: {state['rig_count']} rigs")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/rig_counts/by_state",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def historical(self, **params) -> List[Dict[str, Any]]:
        """Get historical rig count data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of historical rig count records

        Example:
            >>> history = client.ei.rig_counts.historical()
            >>> for record in history:
            ...     print(f"{record['date']}: {record['count']} rigs")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/rig_counts/historical",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response
