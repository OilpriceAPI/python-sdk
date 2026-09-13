"""
EI Forecasts Resource

Energy Intelligence forecast data operations.
"""

from typing import Any, Dict, List

from ._envelopes import ei_data, unwrap_ei_collection


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

        return ei_data(response)

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

        return ei_data(response)

    def latest(self) -> Dict[str, Any]:
        """Get latest forecast data.

        Returns:
            Report object with ``id``, ``report_date``, ``source``,
            ``last_updated``, ``summary`` and ``forecasts`` (keyed by
            ``prices``, ``production`` and ``supply_demand``).

        Example:
            >>> latest = client.ei.forecasts.latest()
            >>> print(latest['forecasts'].keys())
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/forecasts/latest"
        )

        return ei_data(response)

    def summary(self) -> Dict[str, Any]:
        """Get forecast summary.

        Returns:
            Summary object with ``report_month``, ``forecasts`` and
            ``headline``.

        Example:
            >>> summary = client.ei.forecasts.summary()
            >>> print(summary['headline'])
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/forecasts/summary"
        )

        return ei_data(response)

    def prices(self, **params) -> Dict[str, Any]:
        """Get price forecasts.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            Object with ``report_month`` and ``commodities`` — a mapping
            keyed by commodity (``brent``, ``wti``, ``natural_gas``), each
            holding that commodity's forecast series. This endpoint returns
            a mapping, not a list.

        Example:
            >>> prices = client.ei.forecasts.prices()
            >>> for commodity, series in prices['commodities'].items():
            ...     print(f"{commodity}: {len(series)} periods")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/forecasts/prices",
            params=params
        )

        return ei_data(response)

    def production(self, **params) -> Dict[str, Any]:
        """Get production forecasts.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            Object with ``report_month`` and ``series`` — a mapping keyed by
            series code, each holding that series' forecast. This endpoint
            returns a mapping, not a list.

        Example:
            >>> production = client.ei.forecasts.production()
            >>> for code, series in production['series'].items():
            ...     print(f"{code}: {len(series)} periods")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/forecasts/production",
            params=params
        )

        return ei_data(response)

    def historical(self, **params) -> List[Dict[str, Any]]:
        """Get historical forecast data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``actuals`` list from ``data``. Each record has
            ``report_month``, ``period`` and ``value``.

        Example:
            >>> history = client.ei.forecasts.historical(series_code="BREPUUS")
            >>> for record in history:
            ...     print(f"{record['period']}: {record['value']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/forecasts/historical",
            params=params
        )

        return unwrap_ei_collection(
            response, collection="actuals", subject="forecast historical"
        )

    def compare(self, **params) -> Dict[str, Any]:
        """Compare forecast vs actual data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            Object with ``series_code``, ``month1``, ``month2`` and
            ``comparison``.

        Example:
            >>> comparison = client.ei.forecasts.compare(series_code="BREPUUS")
            >>> print(comparison['comparison'])
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/forecasts/compare",
            params=params
        )

        return ei_data(response)
