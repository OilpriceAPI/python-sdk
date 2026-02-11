"""
EI Well Permits Resource

Energy Intelligence well permit data operations.
"""

from typing import List, Dict, Any, Optional


class EIWellPermitsResource:
    """Resource for Energy Intelligence well permit data."""

    def __init__(self, client):
        """Initialize EI well permits resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self, **params) -> List[Dict[str, Any]]:
        """Get all well permit data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of well permit records

        Example:
            >>> permits = client.ei.well_permits.list()
            >>> for permit in permits:
            ...     print(f"{permit['operator']}: {permit['state']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/well-permits",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def get(self, id: str) -> Dict[str, Any]:
        """Get a specific well permit record by ID.

        Args:
            id: Well permit record ID

        Returns:
            Well permit record details

        Example:
            >>> permit = client.ei.well_permits.get("123")
            >>> print(f"Operator: {permit['operator']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/well-permits/{id}"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def latest(self) -> Dict[str, Any]:
        """Get latest well permit data.

        Returns:
            Latest well permit summary

        Example:
            >>> latest = client.ei.well_permits.latest()
            >>> print(f"Recent permits: {latest['count']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/well-permits/latest"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def summary(self) -> Dict[str, Any]:
        """Get well permit summary.

        Returns:
            Summary statistics for well permits

        Example:
            >>> summary = client.ei.well_permits.summary()
            >>> print(f"Total permits: {summary['total']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/well-permits/summary"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def by_state(self, **params) -> List[Dict[str, Any]]:
        """Get well permits by state.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of state permit records

        Example:
            >>> states = client.ei.well_permits.by_state()
            >>> for state in states:
            ...     print(f"{state['name']}: {state['permit_count']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/well-permits/by-state",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def by_operator(self, **params) -> List[Dict[str, Any]]:
        """Get well permits by operator.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of operator permit records

        Example:
            >>> operators = client.ei.well_permits.by_operator()
            >>> for operator in operators:
            ...     print(f"{operator['name']}: {operator['permit_count']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/well-permits/by-operator",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def by_formation(self, **params) -> List[Dict[str, Any]]:
        """Get well permits by formation.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of formation permit records

        Example:
            >>> formations = client.ei.well_permits.by_formation()
            >>> for formation in formations:
            ...     print(f"{formation['name']}: {formation['permit_count']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/well-permits/by-formation",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def search(self, query: str, **params) -> List[Dict[str, Any]]:
        """Search well permits.

        Args:
            query: Search query string
            **params: Optional query parameters for filtering

        Returns:
            List of matching permit records

        Example:
            >>> results = client.ei.well_permits.search("Chevron")
            >>> for result in results:
            ...     print(f"{result['operator']}: {result['state']}")
        """
        params["query"] = query
        response = self.client.request(
            method="GET",
            path="/v1/ei/well-permits/search",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response
