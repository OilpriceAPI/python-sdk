"""
Forecasts Resource

EIA and agency price forecast operations.
"""

from typing import List, Dict, Any, Optional


class ForecastsResource:
    """Resource for official price forecasts from EIA and other agencies."""

    def __init__(self, client):
        """Initialize forecasts resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def monthly(self, commodity: Optional[str] = None) -> Dict[str, Any]:
        """Get monthly price forecasts.

        Args:
            commodity: Optional commodity code filter

        Returns:
            Monthly forecasts from EIA and other agencies

        Example:
            >>> forecasts = client.forecasts.monthly()
            >>> for forecast in forecasts:
            ...     print(f"{forecast['period']}: ${forecast['price']:.2f}")
            >>>
            >>> # Specific commodity
            >>> wti_forecasts = client.forecasts.monthly(commodity="WTI_USD")
        """
        params = {}
        if commodity:
            params["commodity"] = commodity

        response = self.client.request(
            method="GET",
            path="/v1/forecasts/monthly",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def accuracy(self) -> Dict[str, Any]:
        """Get forecast accuracy metrics.

        Returns:
            Historical accuracy analysis of forecasts vs actual prices

        Example:
            >>> accuracy = client.forecasts.accuracy()
            >>> print(f"30-day Accuracy: {accuracy['30_day']['accuracy']}%")
            >>> print(f"90-day Accuracy: {accuracy['90_day']['accuracy']}%")
            >>> print(f"Mean Absolute Error: {accuracy['mae']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/forecasts/accuracy"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def archive(self, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get archived forecasts.

        Args:
            year: Optional year filter for archived forecasts

        Returns:
            List of historical forecasts

        Example:
            >>> archive = client.forecasts.archive(year=2024)
            >>> for forecast in archive:
            ...     print(f"{forecast['date']}: {forecast['commodity']} = ${forecast['price']:.2f}")
        """
        params = {}
        if year:
            params["year"] = year

        response = self.client.request(
            method="GET",
            path="/v1/forecasts/archive",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def get(self, period: str, commodity: Optional[str] = None) -> Dict[str, Any]:
        """Get forecast for a specific period.

        Args:
            period: Forecast period (e.g., "2025-01", "2025-Q1")
            commodity: Optional commodity code filter

        Returns:
            Forecast data for the specified period

        Example:
            >>> forecast = client.forecasts.get("2025-03", commodity="BRENT_CRUDE_USD")
            >>> print(f"March 2025 Brent Forecast: ${forecast['price']:.2f}")
            >>> print(f"Range: ${forecast['low']:.2f} - ${forecast['high']:.2f}")
        """
        params = {}
        if commodity:
            params["commodity"] = commodity

        response = self.client.request(
            method="GET",
            path=f"/v1/forecasts/monthly/{period}",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response
