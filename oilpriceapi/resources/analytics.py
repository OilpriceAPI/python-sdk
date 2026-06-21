"""
Analytics Resource

Price analytics and statistical analysis operations.

Wire-parameter note
--------------------
The v1 analytics controller (``app/controllers/v1/analytics_controller.rb``)
expects ``code`` / ``code1`` / ``code2`` and ``period`` query parameters — NOT
``commodity`` / ``commodity1`` / ``commodity2`` / ``days``. The public method
signatures keep the friendlier ``commodity`` / ``days`` names for backwards
compatibility, but this resource maps them to the names the API actually reads.
A mismatch here is the same bug class fixed in the Node SDK (it was sending
``commodity1`` / ``commodity2`` which the controller silently ignored).
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from ..client import OilPriceAPI


class AnalyticsResource:
    """Resource for price analytics and statistics."""

    def __init__(self, client: "OilPriceAPI") -> None:
        """Initialize analytics resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def performance(
        self,
        commodity: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get API usage performance analytics for the authenticated user.

        Args:
            commodity: Accepted for backwards compatibility; the controller does
                not filter performance by commodity.
            days: Number of days for the performance window. Mapped to the
                controller's ``range`` parameter (``7d`` / ``30d`` / ``90d``).

        Returns:
            Performance metrics for the user's API usage.

        Example:
            >>> perf = client.analytics.performance(days=30)
        """
        # Controller reads params[:range] ("7d"/"30d"/"90d"), not commodity/days.
        range_value = "7d" if days <= 7 else ("90d" if days >= 90 else "30d")
        params: Dict[str, Any] = {"range": range_value}

        response = self.client.request(
            method="GET",
            path="/v1/analytics/performance",
            params=params,
        )

        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response

    def statistics(self, commodity: str, days: int = 30) -> Dict[str, Any]:
        """Get statistical analysis for a commodity.

        Args:
            commodity: Commodity code (sent to the API as ``code``)
            days: Number of days for statistical analysis (sent as ``period``)

        Returns:
            Statistical metrics (mean, median, std dev, min, max, etc.)

        Example:
            >>> stats = client.analytics.statistics("WTI_USD", days=90)
        """
        response = self.client.request(
            method="GET",
            path="/v1/analytics/statistics",
            params={
                "code": commodity,
                "period": days,
            },
        )

        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response

    def correlation(
        self,
        commodity1: str,
        commodity2: str,
        days: int = 90,
    ) -> Dict[str, Any]:
        """Get correlation analysis between two commodities.

        Args:
            commodity1: First commodity code (sent to the API as ``code1``)
            commodity2: Second commodity code (sent to the API as ``code2``)
            days: Number of days for correlation calculation (sent as ``period``)

        Returns:
            Correlation metrics and analysis

        Example:
            >>> corr = client.analytics.correlation(
            ...     "BRENT_CRUDE_USD",
            ...     "WTI_USD",
            ...     days=90,
            ... )
        """
        # The controller requires code1/code2/period (NOT commodity1/commodity2/days).
        response = self.client.request(
            method="GET",
            path="/v1/analytics/correlation",
            params={
                "code1": commodity1,
                "code2": commodity2,
                "period": days,
            },
        )

        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response

    def trend(self, commodity: str, days: int = 30) -> Dict[str, Any]:
        """Get trend analysis for a commodity.

        Args:
            commodity: Commodity code (sent to the API as ``code``)
            days: Number of days for trend analysis (sent as ``period``)

        Returns:
            Trend metrics with direction, strength, and momentum

        Example:
            >>> trend = client.analytics.trend("NATURAL_GAS_USD", days=30)
        """
        response = self.client.request(
            method="GET",
            path="/v1/analytics/trend",
            params={
                "code": commodity,
                "period": days,
            },
        )

        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response

    def spread(self, spread: str, days: int = 30) -> Dict[str, Any]:
        """Get spread analysis for a named commodity spread.

        The spread endpoint operates on a *named* spread (e.g. ``"wti_brent"``),
        not an arbitrary pair of commodity codes. Call without ``spread`` set via
        :meth:`available_spreads` to discover valid names.

        Args:
            spread: Spread name, e.g. ``"wti_brent"`` (sent to the API as ``spread``)
            days: Number of days of history to analyze (sent as ``period``)

        Returns:
            Spread analysis with current spread and historical statistics

        Example:
            >>> spread = client.analytics.spread("wti_brent")
        """
        response = self.client.request(
            method="GET",
            path="/v1/analytics/spread",
            params={
                "spread": spread,
                "period": days,
            },
        )

        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response

    def available_spreads(self) -> Dict[str, Any]:
        """List the named spreads supported by the spread endpoint.

        Returns:
            Catalog of available spread names (the controller returns this when
            no ``spread`` parameter is supplied).

        Example:
            >>> spreads = client.analytics.available_spreads()
        """
        response = self.client.request(
            method="GET",
            path="/v1/analytics/spread",
            params={},
        )

        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response

    def forecast(self, commodity: str, method: str = "ema", days: int = 90) -> Dict[str, Any]:
        """Get price forecast for a commodity.

        Args:
            commodity: Commodity code (sent to the API as ``code``)
            method: Forecast method (sent as ``method``), e.g. ``"ema"``
            days: Number of days of history to base the forecast on (sent as ``period``)

        Returns:
            Forecast with predicted prices and confidence intervals

        Example:
            >>> forecast = client.analytics.forecast("BRENT_CRUDE_USD")
        """
        response = self.client.request(
            method="GET",
            path="/v1/analytics/forecast",
            params={
                "code": commodity,
                "method": method,
                "period": days,
            },
        )

        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response
