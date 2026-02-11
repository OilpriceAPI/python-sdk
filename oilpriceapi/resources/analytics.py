"""
Analytics Resource

Price analytics and statistical analysis operations.
"""

from typing import Dict, Any, Optional


class AnalyticsResource:
    """Resource for price analytics and statistics."""

    def __init__(self, client):
        """Initialize analytics resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def performance(
        self,
        commodity: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get price performance analysis.

        Args:
            commodity: Commodity code (if None, returns all commodities)
            days: Number of days for performance calculation

        Returns:
            Performance metrics with returns, volatility, and trends

        Example:
            >>> perf = client.analytics.performance("BRENT_CRUDE_USD", days=30)
            >>> print(f"30-day Return: {perf['return_pct']}%")
            >>> print(f"Volatility: {perf['volatility']}")
            >>> print(f"Trend: {perf['trend']}")
        """
        params = {"days": days}
        if commodity:
            params["commodity"] = commodity

        response = self.client.request(
            method="GET",
            path="/v1/analytics/performance",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def statistics(self, commodity: str, days: int = 30) -> Dict[str, Any]:
        """Get statistical analysis for a commodity.

        Args:
            commodity: Commodity code
            days: Number of days for statistical analysis

        Returns:
            Statistical metrics (mean, median, std dev, min, max, etc.)

        Example:
            >>> stats = client.analytics.statistics("WTI_USD", days=90)
            >>> print(f"Mean: ${stats['mean']:.2f}")
            >>> print(f"Std Dev: ${stats['std_dev']:.2f}")
            >>> print(f"Min: ${stats['min']:.2f}")
            >>> print(f"Max: ${stats['max']:.2f}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/analytics/statistics",
            params={
                "commodity": commodity,
                "days": days
            }
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def correlation(
        self,
        commodity1: str,
        commodity2: str,
        days: int = 90
    ) -> Dict[str, Any]:
        """Get correlation analysis between two commodities.

        Args:
            commodity1: First commodity code
            commodity2: Second commodity code
            days: Number of days for correlation calculation

        Returns:
            Correlation metrics and analysis

        Example:
            >>> corr = client.analytics.correlation(
            ...     "BRENT_CRUDE_USD",
            ...     "WTI_USD",
            ...     days=90
            ... )
            >>> print(f"Correlation: {corr['correlation']:.3f}")
            >>> print(f"P-value: {corr['p_value']:.4f}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/analytics/correlation",
            params={
                "commodity1": commodity1,
                "commodity2": commodity2,
                "days": days
            }
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def trend(self, commodity: str, days: int = 30) -> Dict[str, Any]:
        """Get trend analysis for a commodity.

        Args:
            commodity: Commodity code
            days: Number of days for trend analysis

        Returns:
            Trend metrics with direction, strength, and momentum

        Example:
            >>> trend = client.analytics.trend("NATURAL_GAS_USD", days=30)
            >>> print(f"Direction: {trend['direction']}")
            >>> print(f"Strength: {trend['strength']}")
            >>> print(f"Momentum: {trend['momentum']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/analytics/trend",
            params={
                "commodity": commodity,
                "days": days
            }
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def spread(self, commodity1: str, commodity2: str) -> Dict[str, Any]:
        """Get spread analysis between two commodities.

        Args:
            commodity1: First commodity code
            commodity2: Second commodity code

        Returns:
            Spread analysis with current spread and historical statistics

        Example:
            >>> spread = client.analytics.spread("BRENT_CRUDE_USD", "WTI_USD")
            >>> print(f"Current Spread: ${spread['current']:.2f}")
            >>> print(f"Average Spread: ${spread['average']:.2f}")
            >>> print(f"Spread Percentile: {spread['percentile']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/analytics/spread",
            params={
                "commodity1": commodity1,
                "commodity2": commodity2
            }
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def forecast(self, commodity: str) -> Dict[str, Any]:
        """Get price forecast for a commodity.

        Args:
            commodity: Commodity code

        Returns:
            Forecast with predicted prices and confidence intervals

        Example:
            >>> forecast = client.analytics.forecast("BRENT_CRUDE_USD")
            >>> print(f"7-day Forecast: ${forecast['7_day']['price']:.2f}")
            >>> print(f"30-day Forecast: ${forecast['30_day']['price']:.2f}")
            >>> print(f"Confidence: {forecast['confidence']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/analytics/forecast",
            params={"commodity": commodity}
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response
