"""
Bunker Fuels Resource

Marine bunker fuel price operations.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from ..resource_validators import format_date
from ._route_args import (
    bunker_grade_prefix,
    bunker_port_code,
    bunker_spread_params,
    filter_bunker_history,
)


class BunkerFuelsResource:
    """Resource for marine bunker fuel prices."""

    def __init__(self, client):
        """Initialize bunker fuels resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def all(self) -> List[Dict[str, Any]]:
        """Get the available bunker fuel price records.

        Returns:
            List of bunker fuel price records returned by the API

        Example:
            >>> bunker_prices = client.bunker_fuels.all()
            >>> for price in bunker_prices:
            ...     print(f"{price['port']}: ${price['price']}/{price['unit']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/bunker-fuels"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def port(self, code: str) -> Dict[str, Any]:
        """Get bunker fuel prices for a specific port.

        Args:
            code: Port code (e.g., "SINGAPORE", "ROTTERDAM", "HOUSTON")

        Returns:
            Port bunker fuel prices with VLSFO, MGO, IFO380

        Example:
            >>> singapore = client.bunker_fuels.port("SINGAPORE")
            >>> print(f"VLSFO: ${singapore['vlsfo']['price']}")
            >>> print(f"MGO: ${singapore['mgo']['price']}")
            >>> print(f"IFO380: ${singapore['ifo380']['price']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/bunker-fuels/ports/{code}"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def compare(self, ports: List[str]) -> Dict[str, Any]:
        """Compare bunker fuel prices across multiple ports.

        Args:
            ports: List of port codes to compare

        Returns:
            Comparison data with prices and differentials

        Example:
            >>> comparison = client.bunker_fuels.compare([
            ...     "SINGAPORE",
            ...     "ROTTERDAM",
            ...     "HOUSTON"
            ... ])
            >>> for port, data in comparison.items():
            ...     print(f"{port}: ${data['vlsfo']['price']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/bunker-fuels/compare",
            params={"ports": ",".join(ports)}
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def spreads(self, from_port: str, to_port: str, grade: Optional[str] = None) -> Dict[str, Any]:
        """Get the price spread between two bunker ports.

        Calls ``GET /v1/bunker-fuels/spreads/ports``.

        Args:
            from_port: Port code (e.g. ``"SIN"`` or LOCODE ``"SGSIN"``)
            to_port: Port code (e.g. ``"RTM"``)
            grade: Optional fuel grade filter (e.g. ``"VLSFO"``)

        Returns:
            ``{"from_port", "to_port", "fuel_grade", "spreads", "metadata"}``

        Example:
            >>> result = client.bunker_fuels.spreads("SIN", "RTM", grade="VLSFO")
            >>> print(result["spreads"])
        """
        response = self.client.request(
            method="GET",
            path="/v1/bunker-fuels/spreads/ports",
            params=bunker_spread_params(from_port, to_port, grade)
        )

        if "data" in response:
            return response["data"]
        return response

    def historical(
        self,
        port: str,
        fuel_type: Optional[str] = None,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        interval: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get historical bunker fuel prices for one port.

        Calls ``GET /v1/bunker-fuels/historical/{port}``.

        Args:
            port: Port code (e.g. ``"SIN"`` or LOCODE ``"SGSIN"``). Required.
            fuel_type: Optional grade (``"vlsfo"``, ``"mgo"``, ``"hfo380"``).
                The API returns every grade for the port; this filters
                ``historical_data`` to records whose code starts with the
                grade.
            start_date: Start date (API ``from``; defaults to 30 days ago)
            end_date: End date (API ``to``; defaults to now)
            interval: Optional aggregation interval (e.g. ``"daily"``)

        Returns:
            ``{"port", "historical_data": [...], "period", "metadata"}``.
            Each record has ``timestamp``, ``code``, ``average_value`` and
            ``interval_type``.

        Example:
            >>> result = client.bunker_fuels.historical("SIN", fuel_type="vlsfo")
            >>> for r in result["historical_data"]:
            ...     print(r["timestamp"], r["average_value"])
        """
        prefix = bunker_grade_prefix(fuel_type)
        params: Dict[str, Any] = {}
        if start_date is not None:
            params["from"] = self._format_date(start_date)
        if end_date is not None:
            params["to"] = self._format_date(end_date)
        if interval is not None:
            params["interval"] = interval

        response = self.client.request(
            method="GET",
            path=f"/v1/bunker-fuels/historical/{bunker_port_code(port)}",
            params=params
        )

        data = response["data"] if "data" in response else response
        return filter_bunker_history(data, prefix)

    def export(self, format: str = "json") -> Any:
        """Export bunker fuel data.

        Args:
            format: Export format ("json", "csv", "xlsx")

        Returns:
            Exported data in requested format

        Example:
            >>> # JSON export
            >>> data = client.bunker_fuels.export(format="json")
            >>>
            >>> # CSV export
            >>> csv_data = client.bunker_fuels.export(format="csv")
        """
        response = self.client.request(
            method="GET",
            path="/v1/bunker-fuels/export",
            params={"format": format}
        )

        # For non-JSON formats, return raw response
        if format != "json":
            return response

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def _format_date(self, date_input: Union[str, date, datetime]) -> str:
        """Format date for API."""
        return format_date(date_input)
