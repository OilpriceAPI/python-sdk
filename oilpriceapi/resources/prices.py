"""
Prices Resource

Current price operations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast

from .._pagination import validate_page_size
from ..models import Price


class PricesResource:
    """Resource for current price operations."""

    #: The API accepts at most this many commodity codes in one request, and
    #: that request counts ONCE against quota. Verified against production
    #: 2026-08-23: 20 codes -> 200, 21 -> 400 "Too many commodity codes
    #: requested (max: 20, requested: 21)". Raising this without a
    #: corresponding API change turns every call into a 400.
    MAX_CODES_PER_REQUEST = 20

    def __init__(self, client):
        self.client = client

    @staticmethod
    def _to_price(price_data: Dict[str, Any], fallback_code: Optional[str] = None) -> Price:
        """Map one API price row onto the Price model.

        Shared by get() and the batched path so the two cannot drift.

        Values are passed to a pydantic model, which does the coercion and
        raises on anything genuinely wrong. The casts here are for mypy: the
        JSON payload is Dict[str, Any], and the previous Price(**mapped_data)
        form simply hid that from the type checker.
        """
        return Price(
            commodity=cast(str, price_data.get("code", fallback_code)),
            value=cast(float, price_data.get("price")),
            currency=price_data.get("currency"),
            # Retain the established oil-only fallback for legacy minimal
            # responses; any unit actually supplied by the API wins.
            unit=cast(str, price_data.get("unit", "barrel")),
            timestamp=cast(datetime, price_data.get("created_at")),
        )

    def _fetch_batch(self, codes: List[str]) -> List[Price]:
        """One request for up to MAX_CODES_PER_REQUEST codes.

        A single code returns a flat ``data`` object; two or more return
        ``data.prices[]``. Both shapes are handled here so callers do not
        have to care how many codes they asked for.
        """
        response = self.client.request(
            method="GET",
            path="/v1/prices/latest",
            params={"by_code": ",".join(codes)},
        )
        data = response.get("data", response) if isinstance(response, dict) else response

        if isinstance(data, dict) and "prices" in data:
            rows = data["prices"]
        else:
            rows = [data]

        return [self._to_price(row, codes[0] if len(codes) == 1 else None) for row in rows]

    def get(self, commodity: str) -> Price:
        """Get current price for a single commodity.

        Args:
            commodity: Commodity code (e.g., "BRENT_CRUDE_USD")

        Returns:
            Price object with current data

        Example:
            >>> price = client.prices.get("BRENT_CRUDE_USD")
            >>> print(f"Brent: ${price.value:.2f}")
        """
        response = self.client.request(
            method="GET", path="/v1/prices/latest", params={"by_code": commodity}
        )

        price_data = response["data"] if "data" in response else response
        return self._to_price(price_data, commodity)

    def get_multiple(
        self, commodities: List[str], raise_on_error: bool = False, return_failures: bool = False
    ) -> Union[List[Price], tuple[List[Price], List[tuple[str, str]]]]:
        """Get prices for multiple commodities.

        Args:
            commodities: List of commodity codes
            raise_on_error: If True, raise exception on first failure. If False, skip failed commodities.
            return_failures: If True, return tuple of (prices, failures). Failures is list of (commodity, error_message).

        Returns:
            List of Price objects, or tuple of (prices, failures) if return_failures=True

        Raises:
            OilPriceAPIError: If raise_on_error=True and any commodity fails

        Example:
            >>> prices = client.prices.get_multiple([
            ...     "BRENT_CRUDE_USD",
            ...     "WTI_USD",
            ...     "NATURAL_GAS_USD"
            ... ])
            >>> for price in prices:
            ...     print(f"{price.commodity}: ${price.value:.2f}")

            >>> # With failure tracking
            >>> prices, failures = client.prices.get_multiple(
            ...     ["BRENT_CRUDE_USD", "INVALID_CODE"],
            ...     return_failures=True
            ... )
            >>> if failures:
            ...     print(f"Failed to fetch: {failures}")
        """
        from ..exceptions import OilPriceAPIError

        prices = []
        failures = []

        for start in range(0, len(commodities), self.MAX_CODES_PER_REQUEST):
            chunk = commodities[start : start + self.MAX_CODES_PER_REQUEST]
            try:
                prices.extend(self._fetch_batch(chunk))
            except OilPriceAPIError:
                if raise_on_error:
                    raise
                # The API rejects the WHOLE request when any code in it is
                # unknown, so a chunk failure does not say which code was at
                # fault. Retry just this chunk per code to preserve the
                # per-code failure contract. A one-code chunk has nothing to
                # narrow down, so it is recorded directly rather than refetched.
                if len(chunk) == 1:
                    try:
                        prices.append(self.get(chunk[0]))
                    except OilPriceAPIError as exc:
                        failures.append((chunk[0], str(exc)))
                    continue
                for commodity in chunk:
                    try:
                        prices.append(self.get(commodity))
                    except OilPriceAPIError as exc:
                        failures.append((commodity, str(exc)))

        if return_failures:
            return prices, failures
        return prices

    def get_all(self, per_page: int = 100) -> List[Price]:
        """Get current price records available to the account.

        Auto-paginates using X-Has-Next response headers until the API reports
        no additional records.

        Args:
            per_page: Number of records per page (default 100, matches API default)

        Returns:
            List of Price objects returned for the current account

        Example:
            >>> all_prices = client.prices.get_all()
            >>> oil_prices = [p for p in all_prices if 'CRUDE' in p.commodity]
        """
        validated_per_page = validate_page_size(per_page)
        all_prices: List[Price] = []
        seen_previous_pages: Set[Tuple[object, ...]] = set()
        page = 1

        while True:
            body, headers = self.client.request_with_headers(
                method="GET",
                path="/v1/prices/all",
                params={"page": page, "per_page": validated_per_page},
            )

            # Parse response — /v1/prices/all returns nested:
            # {"status":"success","data":{"status":"success","data":{"prices":{CODE: {...}, ...}}}}
            # Extract the prices dict regardless of nesting depth
            prices_data = body
            if isinstance(prices_data, dict) and "data" in prices_data:
                prices_data = prices_data["data"]
            if isinstance(prices_data, dict) and "data" in prices_data:
                prices_data = prices_data["data"]
            if isinstance(prices_data, dict) and "prices" in prices_data:
                prices_data = prices_data["prices"]

            # prices_data is now either a dict {CODE: {...}} or a list [{...}]
            items = (
                prices_data.values()
                if isinstance(prices_data, dict)
                else (prices_data if isinstance(prices_data, list) else [])
            )

            current_page_keys: Set[Tuple[object, ...]] = set()
            for price_data in items:
                if isinstance(price_data, dict):
                    mapped = {
                        "commodity": price_data.get("code", ""),
                        "value": price_data.get("price"),
                        "currency": price_data.get("currency"),
                        "unit": price_data.get("unit"),
                        "timestamp": price_data.get("updated_at") or price_data.get("created_at"),
                    }
                    price = Price(**mapped)
                    key = (
                        price.timestamp,
                        price.commodity,
                        price.value,
                        price.currency,
                        price.unit,
                    )
                    if key not in seen_previous_pages:
                        all_prices.append(price)
                    current_page_keys.add(key)
            seen_previous_pages.update(current_page_keys)

            # Check pagination header
            has_next = str(headers.get("X-Has-Next", "false")).lower() == "true"
            if not has_next or not prices_data:
                break

            page += 1

        return all_prices

    def to_dataframe(
        self,
        commodity: Optional[str] = None,
        commodities: Optional[List[str]] = None,
        start: Optional[Union[str, datetime]] = None,
        end: Optional[Union[str, datetime]] = None,
        interval: str = "daily",
        per_page: int = 100,
    ):
        """Get price data as a pandas DataFrame.

        Note: Requires pandas to be installed.

        Args:
            commodity: Single commodity code
            commodities: Multiple commodity codes
            start: Start date for historical data
            end: End date for historical data
            interval: Data interval (minute, hourly, daily, weekly, monthly)
            per_page: Records per request, from 1 to 1000. Auto-pagination
                      fetches every page for all-current and historical queries.

        Returns:
            pandas DataFrame with price data

        Example:
            >>> df = client.prices.to_dataframe(
            ...     commodity="BRENT_CRUDE_USD",
            ...     start="2024-01-01",
            ...     interval="daily"
            ... )
            >>> df.plot(y="value", title="Brent Crude Oil Prices")
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for DataFrame support. "
                "Install with: pip install oilpriceapi[pandas]"
            )

        # If historical data requested, use historical endpoint
        if start or end:
            from .historical import HistoricalResource

            hist = HistoricalResource(self.client)

            if commodity:
                df = hist.to_dataframe(
                    commodity=commodity,
                    start=start,
                    end=end,
                    interval=interval,
                    per_page=per_page,
                )
            elif commodities:
                dfs = []
                for comm in commodities:
                    df_comm = hist.to_dataframe(
                        commodity=comm,
                        start=start,
                        end=end,
                        interval=interval,
                        per_page=per_page,
                    )
                    df_comm["commodity"] = comm
                    dfs.append(df_comm)
                df = pd.concat(dfs, ignore_index=True)
            else:
                raise ValueError("Either commodity or commodities must be specified")

            return df

        # Current prices only
        if commodity:
            price = self.get(commodity)
            df = pd.DataFrame([price.model_dump()])
        elif commodities:
            # return_failures defaults to False, so this returns a plain List[Price].
            prices = self.get_multiple(commodities)
            assert isinstance(prices, list)
            df = pd.DataFrame([p.model_dump() for p in prices])
        else:
            prices = self.get_all(per_page=per_page)
            df = pd.DataFrame([p.model_dump() for p in prices])

        # Set timestamp as index
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.set_index("timestamp", inplace=True)

        return df
