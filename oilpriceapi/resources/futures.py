"""
Futures Resource

Futures contract price operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from typing import Union


class FuturesResource:
    """Resource for futures contract operations."""

    def __init__(self, client):
        """Initialize futures resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def latest(self, contract: str) -> Dict[str, Any]:
        """Get latest futures price for a contract.

        Args:
            contract: Futures contract code (e.g., "CL.1", "BZ.1")

        Returns:
            Latest futures price data

        Example:
            >>> price = client.futures.latest("CL.1")
            >>> print(f"WTI Front Month: ${price['price']:.2f}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/futures/{contract}"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def historical(
        self,
        contract: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None
    ) -> List[Dict[str, Any]]:
        """Get historical futures prices for a contract.

        Args:
            contract: Futures contract code
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            List of historical price records

        Example:
            >>> history = client.futures.historical(
            ...     contract="CL.1",
            ...     start_date="2024-01-01",
            ...     end_date="2024-12-31"
            ... )
            >>> for record in history:
            ...     print(f"{record['date']}: ${record['price']:.2f}")
        """
        params = {}
        if start_date:
            params["start_date"] = self._format_date(start_date)
        if end_date:
            params["end_date"] = self._format_date(end_date)

        response = self.client.request(
            method="GET",
            path=f"/v1/futures/{contract}/historical",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def ohlc(self, contract: str, date: Optional[str] = None) -> Dict[str, Any]:
        """Get OHLC (Open, High, Low, Close) data for a contract.

        Args:
            contract: Futures contract code
            date: Specific date for OHLC data (defaults to latest)

        Returns:
            OHLC data with open, high, low, close, and volume

        Example:
            >>> ohlc = client.futures.ohlc("CL.1")
            >>> print(f"Open: ${ohlc['open']:.2f}")
            >>> print(f"High: ${ohlc['high']:.2f}")
            >>> print(f"Low: ${ohlc['low']:.2f}")
            >>> print(f"Close: ${ohlc['close']:.2f}")
        """
        params = {}
        if date:
            params["date"] = date

        response = self.client.request(
            method="GET",
            path=f"/v1/futures/{contract}/ohlc",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def intraday(self, contract: str) -> List[Dict[str, Any]]:
        """Get intraday futures prices for a contract.

        Args:
            contract: Futures contract code

        Returns:
            List of intraday price records

        Example:
            >>> intraday = client.futures.intraday("CL.1")
            >>> for record in intraday:
            ...     print(f"{record['time']}: ${record['price']:.2f}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/futures/{contract}/intraday"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def spreads(self, contract1: str, contract2: str) -> Dict[str, Any]:
        """Get spread analysis between two futures contracts.

        Args:
            contract1: First futures contract code
            contract2: Second futures contract code

        Returns:
            Spread analysis with current spread and historical data

        Example:
            >>> spread = client.futures.spreads("CL.1", "CL.2")
            >>> print(f"Front Month - Second Month: ${spread['current_spread']:.2f}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/futures/spreads",
            params={
                "contract1": contract1,
                "contract2": contract2
            }
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def curve(self, contract: str) -> List[Dict[str, Any]]:
        """Get futures curve for a contract.

        Args:
            contract: Futures contract code

        Returns:
            List of futures curve data points

        Example:
            >>> curve = client.futures.curve("CL")
            >>> for point in curve:
            ...     print(f"{point['month']}: ${point['price']:.2f}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/futures/{contract}/curve"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def continuous(self, contract: str, months: int = 12) -> List[Dict[str, Any]]:
        """Get continuous futures price history.

        Args:
            contract: Futures contract code
            months: Number of months of history (default: 12)

        Returns:
            List of continuous contract prices

        Example:
            >>> continuous = client.futures.continuous("CL", months=24)
            >>> for record in continuous:
            ...     print(f"{record['date']}: ${record['price']:.2f}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/futures/{contract}/continuous",
            params={"months": months}
        )

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
