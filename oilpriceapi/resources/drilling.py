"""
Drilling Intelligence Resource

Drilling and completion activity data operations.
"""

from typing import List, Dict, Any, Optional


class DrillingIntelligenceResource:
    """Resource for drilling intelligence data."""

    def __init__(self, client):
        """Initialize drilling intelligence resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self, **params) -> List[Dict[str, Any]]:
        """Get all drilling intelligence data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of drilling intelligence records

        Example:
            >>> data = client.drilling.list()
            >>> for record in data:
            ...     print(f"{record['basin']}: {record['rig_count']} rigs")
        """
        response = self.client.request(
            method="GET",
            path="/v1/drilling-intelligence",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def latest(self) -> Dict[str, Any]:
        """Get latest drilling intelligence data.

        Returns:
            Latest drilling intelligence summary

        Example:
            >>> latest = client.drilling.latest()
            >>> print(f"Total rigs: {latest['total_rigs']}")
            >>> print(f"Frac spreads: {latest['frac_spreads']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/drilling-intelligence/latest"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def summary(self) -> Dict[str, Any]:
        """Get drilling intelligence summary.

        Returns:
            Summary statistics for drilling activity

        Example:
            >>> summary = client.drilling.summary()
            >>> print(f"Active rigs: {summary['active_rigs']}")
            >>> print(f"Total wells: {summary['total_wells']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/drilling-intelligence/summary"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def trends(self, **params) -> List[Dict[str, Any]]:
        """Get drilling activity trends.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of trend data points

        Example:
            >>> trends = client.drilling.trends()
            >>> for point in trends:
            ...     print(f"{point['date']}: {point['rig_count']} rigs")
        """
        response = self.client.request(
            method="GET",
            path="/v1/drilling-intelligence/trends",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def frac_spreads(self, **params) -> List[Dict[str, Any]]:
        """Get frac spread data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of frac spread records

        Example:
            >>> spreads = client.drilling.frac_spreads()
            >>> for spread in spreads:
            ...     print(f"{spread['basin']}: {spread['count']} spreads")
        """
        response = self.client.request(
            method="GET",
            path="/v1/drilling-intelligence/frac-spreads",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def well_permits(self, **params) -> List[Dict[str, Any]]:
        """Get well permit data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of well permit records

        Example:
            >>> permits = client.drilling.well_permits()
            >>> for permit in permits:
            ...     print(f"{permit['operator']}: {permit['count']} permits")
        """
        response = self.client.request(
            method="GET",
            path="/v1/drilling-intelligence/well-permits",
            params=params
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
            >>> ducs = client.drilling.duc_wells()
            >>> for duc in ducs:
            ...     print(f"{duc['basin']}: {duc['count']} DUCs")
        """
        response = self.client.request(
            method="GET",
            path="/v1/drilling-intelligence/duc-wells",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def completions(self, **params) -> List[Dict[str, Any]]:
        """Get well completion data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of completion records

        Example:
            >>> completions = client.drilling.completions()
            >>> for completion in completions:
            ...     print(f"{completion['basin']}: {completion['count']} completions")
        """
        response = self.client.request(
            method="GET",
            path="/v1/drilling-intelligence/completions",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def wells_drilled(self, **params) -> List[Dict[str, Any]]:
        """Get wells drilled data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of wells drilled records

        Example:
            >>> wells = client.drilling.wells_drilled()
            >>> for well in wells:
            ...     print(f"{well['basin']}: {well['count']} wells")
        """
        response = self.client.request(
            method="GET",
            path="/v1/drilling-intelligence/wells-drilled",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def basin(self, name: str) -> Dict[str, Any]:
        """Get drilling data for a specific basin.

        Args:
            name: Basin name

        Returns:
            Basin-specific drilling data

        Example:
            >>> permian = client.drilling.basin("permian")
            >>> print(f"Permian rigs: {permian['rig_count']}")
            >>> print(f"DUCs: {permian['duc_count']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/drilling-intelligence/basin/{name}"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response
