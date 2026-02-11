"""
EI FracFocus Resource

Energy Intelligence FracFocus data operations.
"""

from typing import List, Dict, Any, Optional


class EIFracFocusResource:
    """Resource for Energy Intelligence FracFocus data."""

    def __init__(self, client):
        """Initialize EI FracFocus resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self, **params) -> List[Dict[str, Any]]:
        """Get all FracFocus data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of FracFocus records

        Example:
            >>> frac_data = client.ei.frac_focus.list()
            >>> for record in frac_data:
            ...     print(f"{record['operator']}: {record['well_name']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/frac-focus",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def get(self, id: str) -> Dict[str, Any]:
        """Get a specific FracFocus record by ID.

        Args:
            id: FracFocus record ID

        Returns:
            FracFocus record details

        Example:
            >>> record = client.ei.frac_focus.get("123")
            >>> print(f"Operator: {record['operator']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/frac-focus/{id}"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def latest(self) -> Dict[str, Any]:
        """Get latest FracFocus data.

        Returns:
            Latest FracFocus summary

        Example:
            >>> latest = client.ei.frac_focus.latest()
            >>> print(f"Recent jobs: {latest['count']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/frac-focus/latest"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def summary(self) -> Dict[str, Any]:
        """Get FracFocus summary.

        Returns:
            Summary statistics for FracFocus data

        Example:
            >>> summary = client.ei.frac_focus.summary()
            >>> print(f"Total jobs: {summary['total']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/frac-focus/summary"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def by_state(self, **params) -> List[Dict[str, Any]]:
        """Get FracFocus data by state.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of state FracFocus records

        Example:
            >>> states = client.ei.frac_focus.by_state()
            >>> for state in states:
            ...     print(f"{state['name']}: {state['job_count']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/frac-focus/by-state",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def by_operator(self, **params) -> List[Dict[str, Any]]:
        """Get FracFocus data by operator.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of operator FracFocus records

        Example:
            >>> operators = client.ei.frac_focus.by_operator()
            >>> for operator in operators:
            ...     print(f"{operator['name']}: {operator['job_count']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/frac-focus/by-operator",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def by_chemical(self, **params) -> List[Dict[str, Any]]:
        """Get FracFocus data by chemical.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of chemical usage records

        Example:
            >>> chemicals = client.ei.frac_focus.by_chemical()
            >>> for chemical in chemicals:
            ...     print(f"{chemical['name']}: {chemical['usage_count']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/frac-focus/by-chemical",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def search(self, query: str, **params) -> List[Dict[str, Any]]:
        """Search FracFocus data.

        Args:
            query: Search query string
            **params: Optional query parameters for filtering

        Returns:
            List of matching FracFocus records

        Example:
            >>> results = client.ei.frac_focus.search("Exxon")
            >>> for result in results:
            ...     print(f"{result['operator']}: {result['well_name']}")
        """
        params["query"] = query
        response = self.client.request(
            method="GET",
            path="/v1/ei/frac-focus/search",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def chemicals(self, id: str) -> List[Dict[str, Any]]:
        """Get chemicals for a specific FracFocus record.

        Args:
            id: FracFocus record ID

        Returns:
            List of chemicals used in the frac job

        Example:
            >>> chemicals = client.ei.frac_focus.chemicals("123")
            >>> for chemical in chemicals:
            ...     print(f"{chemical['name']}: {chemical['concentration']}%")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/frac-focus/{id}/chemicals"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def for_well(self, api_number: str) -> List[Dict[str, Any]]:
        """Get FracFocus data for a specific well.

        Args:
            api_number: Well API number

        Returns:
            List of FracFocus records for the well

        Example:
            >>> well_data = client.ei.frac_focus.for_well("42-123-45678")
            >>> for record in well_data:
            ...     print(f"{record['job_date']}: {record['operator']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/frac-focus/for-well/{api_number}"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response
