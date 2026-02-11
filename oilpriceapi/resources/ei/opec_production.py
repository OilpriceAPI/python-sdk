"""
EI OPEC Production Resource

Energy Intelligence OPEC production data operations.
"""

from typing import List, Dict, Any, Optional


class EIOpecProductionResource:
    """Resource for Energy Intelligence OPEC production data."""

    def __init__(self, client):
        """Initialize EI OPEC production resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self, **params) -> List[Dict[str, Any]]:
        """Get all OPEC production data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of OPEC production records

        Example:
            >>> production = client.ei.opec_production.list()
            >>> for record in production:
            ...     print(f"{record['country']}: {record['production']} bpd")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/opec_productions",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def get(self, id: str) -> Dict[str, Any]:
        """Get a specific OPEC production record by ID.

        Args:
            id: OPEC production record ID

        Returns:
            OPEC production record details

        Example:
            >>> record = client.ei.opec_production.get("123")
            >>> print(f"Production: {record['production']} bpd")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/opec_productions/{id}"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def latest(self) -> Dict[str, Any]:
        """Get latest OPEC production data.

        Returns:
            Latest OPEC production summary

        Example:
            >>> latest = client.ei.opec_production.latest()
            >>> print(f"Total OPEC production: {latest['total']} bpd")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/opec_productions/latest"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def total(self) -> Dict[str, Any]:
        """Get total OPEC production.

        Returns:
            Total OPEC production data

        Example:
            >>> total = client.ei.opec_production.total()
            >>> print(f"OPEC total: {total['production']} bpd")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/opec_productions/total"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def by_country(self, **params) -> List[Dict[str, Any]]:
        """Get OPEC production by country.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of country production records

        Example:
            >>> countries = client.ei.opec_production.by_country()
            >>> for country in countries:
            ...     print(f"{country['name']}: {country['production']} bpd")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/opec_productions/by_country",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def historical(self, **params) -> List[Dict[str, Any]]:
        """Get historical OPEC production data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of historical production records

        Example:
            >>> history = client.ei.opec_production.historical()
            >>> for record in history:
            ...     print(f"{record['date']}: {record['production']} bpd")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/opec_productions/historical",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def top_producers(self, **params) -> List[Dict[str, Any]]:
        """Get top OPEC producers.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of top producer records

        Example:
            >>> top = client.ei.opec_production.top_producers()
            >>> for producer in top:
            ...     print(f"{producer['country']}: {producer['production']} bpd")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/opec_productions/top_producers",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response
