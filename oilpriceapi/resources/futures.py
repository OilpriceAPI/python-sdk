"""
Futures Resource

Futures contract price operations.

Endpoints are keyed by *slug* (e.g. ``"ice-brent"``), not by raw exchange
contract code. The latest-curve route is ``GET /v1/futures/{slug}`` and the
sub-resources are ``/{slug}/curve``, ``/historical``, ``/ohlc``, ``/intraday``
and ``/spread-history``. Each method accepts either a slug or a friendly
contract code (e.g. ``"BZ"``, ``"CL"``, ``"NG"``) and normalizes it via
:mod:`._futures_slug`.

Valid slugs: ``ice-brent``, ``ice-wti``, ``ice-gasoil``, ``natural-gas``,
``ttf-gas``, ``lng-jkm``, ``eua-carbon``, ``uk-carbon`` (+ continuous slugs
``continuous/brent`` and ``continuous/wti``).
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from ._futures_slug import normalize_futures_slug


class FuturesResource:
    """Resource for futures contract operations."""

    def __init__(self, client):
        """Initialize futures resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def latest(self, contract: str) -> Dict[str, Any]:
        """Get the latest futures curve for a contract family.

        Args:
            contract: Futures slug (e.g. ``"ice-brent"``, ``"ice-wti"``) or a
                friendly contract code (e.g. ``"BZ"``, ``"CL"``, ``"NG"``).

        Returns:
            Latest futures curve data (front month + forward contracts)

        Example:
            >>> curve = client.futures.latest("ice-brent")
            >>> # Friendly code form also works:
            >>> curve = client.futures.latest("BZ")
            >>> print(curve["front_month"]["last_price"])
        """
        slug = normalize_futures_slug(contract)
        response = self.client.request(
            method="GET",
            path=f"/v1/futures/{slug}"
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
            contract: Futures slug or friendly contract code (see ``latest``).
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            List of historical price records

        Example:
            >>> history = client.futures.historical(
            ...     contract="ice-wti",
            ...     start_date="2024-01-01",
            ...     end_date="2024-12-31"
            ... )
            >>> for record in history:
            ...     print(f"{record['date']}: ${record['price']:.2f}")
        """
        slug = normalize_futures_slug(contract)
        params = {}
        if start_date:
            params["start_date"] = self._format_date(start_date)
        if end_date:
            params["end_date"] = self._format_date(end_date)

        response = self.client.request(
            method="GET",
            path=f"/v1/futures/{slug}/historical",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def ohlc(self, contract: str, date: Optional[str] = None) -> Dict[str, Any]:
        """Get OHLC (Open, High, Low, Close) data for a contract.

        Args:
            contract: Futures slug or friendly contract code (see ``latest``).
            date: Specific date for OHLC data (defaults to latest)

        Returns:
            OHLC data with open, high, low, close, and volume

        Example:
            >>> ohlc = client.futures.ohlc("ice-wti")
            >>> print(f"Open: ${ohlc['open']:.2f}")
            >>> print(f"High: ${ohlc['high']:.2f}")
            >>> print(f"Low: ${ohlc['low']:.2f}")
            >>> print(f"Close: ${ohlc['close']:.2f}")
        """
        slug = normalize_futures_slug(contract)
        params = {}
        if date:
            params["date"] = date

        response = self.client.request(
            method="GET",
            path=f"/v1/futures/{slug}/ohlc",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def intraday(self, contract: str) -> List[Dict[str, Any]]:
        """Get intraday futures prices for a contract.

        Args:
            contract: Futures slug or friendly contract code (see ``latest``).

        Returns:
            List of intraday price records

        Example:
            >>> intraday = client.futures.intraday("ice-wti")
            >>> for record in intraday:
            ...     print(f"{record['time']}: ${record['price']:.2f}")
        """
        slug = normalize_futures_slug(contract)
        response = self.client.request(
            method="GET",
            path=f"/v1/futures/{slug}/intraday"
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
        """Get the futures curve (contango/backwardation) for a contract.

        Args:
            contract: Futures slug or friendly contract code (see ``latest``).

        Returns:
            List of futures curve data points

        Example:
            >>> curve = client.futures.curve("ice-wti")
            >>> for point in curve:
            ...     print(f"{point['month']}: ${point['price']:.2f}")
        """
        slug = normalize_futures_slug(contract)
        response = self.client.request(
            method="GET",
            path=f"/v1/futures/{slug}/curve"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def continuous(self, contract: str, months: int = 12) -> List[Dict[str, Any]]:
        """Get continuous (auto-rolled) front-month futures history.

        Continuous series are exposed at ``/v1/futures/continuous/{brent,wti}``.

        Args:
            contract: A continuous slug (``"continuous/brent"`` /
                ``"continuous/wti"``) or a friendly code that resolves to one
                of the continuous families (``"BZ"`` -> Brent, ``"CL"`` -> WTI).
            months: Number of months of history (default: 12)

        Returns:
            List of continuous contract prices

        Example:
            >>> history = client.futures.continuous("continuous/wti", months=24)
            >>> for record in history:
            ...     print(f"{record['date']}: ${record['price']:.2f}")
        """
        slug = self._continuous_slug(contract)
        response = self.client.request(
            method="GET",
            path=f"/v1/futures/{slug}/historical",
            params={"months": months}
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    @staticmethod
    def _continuous_slug(contract: str) -> str:
        """Resolve ``contract`` to a ``continuous/{brent,wti}`` slug."""
        slug = normalize_futures_slug(contract)
        if slug.startswith("continuous/"):
            return slug
        if slug in ("ice-brent",):
            return "continuous/brent"
        if slug in ("ice-wti",):
            return "continuous/wti"
        raise ValueError(
            f"Continuous futures are only available for Brent and WTI, "
            f"got {contract!r}. Use 'continuous/brent', 'continuous/wti', "
            f"'BZ' or 'CL'."
        )

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
