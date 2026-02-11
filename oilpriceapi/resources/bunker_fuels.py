"""
Bunker Fuels Resource

Marine bunker fuel price operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from typing import Union


class BunkerFuelsResource:
    """Resource for marine bunker fuel prices."""

    def __init__(self, client):
        """Initialize bunker fuels resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def all(self) -> List[Dict[str, Any]]:
        """Get all bunker fuel prices.

        Returns:
            List of bunker fuel prices across all ports

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

    def spreads(self) -> Dict[str, Any]:
        """Get bunker fuel spreads analysis.

        Returns:
            Spread analysis between fuel types and ports

        Example:
            >>> spreads = client.bunker_fuels.spreads()
            >>> print(f"VLSFO-MGO Spread: ${spreads['vlsfo_mgo']:.2f}")
            >>> print(f"VLSFO-IFO380 Spread: ${spreads['vlsfo_ifo380']:.2f}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/bunker-fuels/spreads"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def historical(
        self,
        port: str,
        fuel_type: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None
    ) -> List[Dict[str, Any]]:
        """Get historical bunker fuel prices.

        Args:
            port: Port code
            fuel_type: Fuel type (e.g., "vlsfo", "mgo", "ifo380")
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            List of historical price records

        Example:
            >>> history = client.bunker_fuels.historical(
            ...     port="SINGAPORE",
            ...     fuel_type="vlsfo",
            ...     start_date="2024-01-01",
            ...     end_date="2024-12-31"
            ... )
            >>> for record in history:
            ...     print(f"{record['date']}: ${record['price']:.2f}")
        """
        params = {
            "port": port,
            "fuel_type": fuel_type
        }
        if start_date:
            params["start_date"] = self._format_date(start_date)
        if end_date:
            params["end_date"] = self._format_date(end_date)

        response = self.client.request(
            method="GET",
            path="/v1/bunker-fuels/historical",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

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
        if isinstance(date_input, str):
            return date_input
        elif isinstance(date_input, datetime):
            return date_input.date().isoformat()
        elif isinstance(date_input, date):
            return date_input.isoformat()
        else:
            raise ValueError(f"Invalid date type: {type(date_input)}")
