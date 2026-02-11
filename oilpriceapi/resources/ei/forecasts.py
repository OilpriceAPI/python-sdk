"""
EI Forecasts Resource

Energy Intelligence forecast data operations.
"""

from typing import List, Dict, Any, Optional


class EIForecastsResource:
    """Resource for Energy Intelligence forecast data."""

    def __init__(self, client):
        """Initialize EI forecasts resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self, **params) -> List[Dict[str, Any]]:
        """Get all forecast data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of forecast records

        Example:
            >>> forecasts = client.ei.forecasts.list()
            >>> for forecast in forecasts:
            ...     print(f"{forecast['commodity']}: ${forecast['predicted_price']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/forecasts",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def get(self, id: str) -> Dict[str, Any]:
        """Get a specific forecast record by ID.

        Args:
            id: Forecast record ID

        Returns:
            Forecast record details

        Example:
            >>> forecast = client.ei.forecasts.get("123")
            >>> print(f"Predicted price: ${forecast['predicted_price']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/forecasts/{id}"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def latest(self) -> Dict[str, Any]:
        """Get latest forecast data.

        Returns:
            Latest forecast summary

        Example:
            >>> latest = client.ei.forecasts.latest()
            >>> print(f"Next month forecast: ${latest['forecast_price']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/forecasts/latest"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def summary(self) -> Dict[str, Any]:
        """Get forecast summary.

        Returns:
            Summary statistics for forecasts

        Example:
            >>> summary = client.ei.forecasts.summary()
            >>> print(f"Average forecast: ${summary['average']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/forecasts/summary"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def prices(self, **params) -> List[Dict[str, Any]]:
        """Get price forecasts.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of price forecast records

        Example:
            >>> prices = client.ei.forecasts.prices()
            >>> for price in prices:
            ...     print(f"{price['date']}: ${price['forecast']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/forecasts/prices",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def production(self, **params) -> List[Dict[str, Any]]:
        """Get production forecasts.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of production forecast records

        Example:
            >>> production = client.ei.forecasts.production()
            >>> for record in production:
            ...     print(f"{record['date']}: {record['forecast']} bpd")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/forecasts/production",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def historical(self, **params) -> List[Dict[str, Any]]:
        """Get historical forecast data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of historical forecast records

        Example:
            >>> history = client.ei.forecasts.historical()
            >>> for record in history:
            ...     print(f"{record['date']}: ${record['forecast']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/forecasts/historical",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def compare(self, **params) -> Dict[str, Any]:
        """Compare forecast vs actual data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            Comparison data with accuracy metrics

        Example:
            >>> comparison = client.ei.forecasts.compare()
            >>> print(f"Accuracy: {comparison['accuracy']}%")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/forecasts/compare",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response
