"""
Historical Data Resource

Historical price data operations.
"""

from datetime import date, datetime
from typing import Generator, List, Optional, Set, Tuple, Union

from .._pagination import validate_page_size
from ..models import HistoricalPrice, HistoricalResponse, PaginationMeta
from ..resource_validators import format_date

DEFAULT_AUTO_PAGE_SIZE = 500
HISTORICAL_DATAFRAME_COLUMNS = [
    "date",
    "commodity",
    "value",
    "currency",
    "unit",
    "type_name",
]


def _price_key(price: HistoricalPrice) -> Tuple[object, ...]:
    """Identify an exact record so overlapping pages do not duplicate it."""
    return (
        price.date,
        price.commodity,
        price.value,
        price.currency,
        price.unit,
        price.type_name,
    )


class HistoricalResource:
    """Resource for historical price data."""

    def __init__(self, client):
        self.client = client

    def _parse_date(self, date_input: Union[str, date, datetime]) -> date:
        """Parse date input to date object."""
        return date.fromisoformat(format_date(date_input))

    def _get_optimal_endpoint(
        self,
        start_date: Optional[Union[str, date, datetime]],
        end_date: Optional[Union[str, date, datetime]],
    ) -> str:
        """Select optimal endpoint based on date range.

        Args:
            start_date: Start date for data range
            end_date: End date for data range

        Returns:
            Optimal API endpoint path
        """
        if not start_date or not end_date:
            return "/v1/prices/past_year"

        # Parse dates
        start = self._parse_date(start_date)
        end = self._parse_date(end_date)

        # Calculate days in range
        days = (end - start).days

        # Select endpoint based on range
        if days <= 1:
            return "/v1/prices/past_day"
        elif days <= 7:
            return "/v1/prices/past_week"
        elif days <= 30:
            return "/v1/prices/past_month"
        else:
            return "/v1/prices/past_year"

    def _calculate_timeout(
        self,
        start_date: Optional[Union[str, date, datetime]],
        end_date: Optional[Union[str, date, datetime]],
        custom_timeout: Optional[float],
    ) -> Optional[float]:
        """Calculate appropriate timeout based on date range.

        Args:
            start_date: Start date for data range
            end_date: End date for data range
            custom_timeout: User-provided timeout override

        Returns:
            Timeout in seconds, or None to use client default
        """
        # If user provided custom timeout, use it
        if custom_timeout is not None:
            return custom_timeout

        # If no dates provided, use default (will query 1 year)
        if not start_date or not end_date:
            return 120  # 2 minutes for year queries

        # Parse dates and calculate range
        start = self._parse_date(start_date)
        end = self._parse_date(end_date)
        days = (end - start).days

        # Return appropriate timeout based on expected data volume
        if days <= 7:
            return 30  # 30s for 1 week
        elif days <= 30:
            return 60  # 1 min for 1 month
        else:
            return 120  # 2 min for 1 year

    def get(
        self,
        commodity: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        interval: str = "daily",
        page: int = 1,
        per_page: int = 100,
        type_name: str = "spot_price",
        timeout: Optional[float] = None,
    ) -> HistoricalResponse:
        """Get historical price data.

        Args:
            commodity: Commodity code (e.g., "BRENT_CRUDE_USD")
            start_date: Start date for data range
            end_date: End date for data range
            interval: Data interval (minute, hourly, daily, weekly, monthly)
            page: Page number for pagination
            per_page: Items per page (max 1000)
            type_name: Price type (spot_price, futures, etc.)
            timeout: Request timeout in seconds. If None, automatically determined by date range.
                     - 1 week range: 30s
                     - 1 month range: 60s
                     - 1 year range: 120s

        Returns:
            HistoricalResponse with price data and pagination info

        Example:
            >>> history = client.historical.get(
            ...     commodity="BRENT_CRUDE_USD",
            ...     start_date="2024-01-01",
            ...     end_date="2024-12-31",
            ...     interval="daily"
            ... )
            >>> for price in history.data:
            ...     print(f"{price.date}: ${price.value:.2f}")

            >>> # Custom timeout for very large queries
            >>> history = client.historical.get(
            ...     commodity="WTI_USD",
            ...     start_date="2020-01-01",
            ...     end_date="2024-12-31",
            ...     timeout=180  # 3 minutes
            ... )
        """
        validated_per_page = validate_page_size(per_page)

        # Build parameters
        # CRITICAL: API expects 'by_code' not 'commodity' (Issue #XXX)
        params = {
            "by_code": commodity,  # Changed from 'commodity' to match API expectation
            "interval": interval,
            "page": page,
            "per_page": validated_per_page,
            "by_type": type_name,
        }

        # Add date parameters if provided
        normalized_start = (
            self._format_date(start_date) if start_date is not None else None
        )
        normalized_end = self._format_date(end_date) if end_date is not None else None
        if normalized_start is not None:
            params["start_date"] = normalized_start
        if normalized_end is not None:
            params["end_date"] = normalized_end

        # Select optimal endpoint based on date range
        endpoint = self._get_optimal_endpoint(normalized_start, normalized_end)

        # Calculate appropriate timeout
        request_timeout = self._calculate_timeout(normalized_start, normalized_end, timeout)

        # Make request with optimal endpoint and timeout — use request_with_headers
        # so we can read X-Has-Next for reliable pagination detection
        response, headers = self.client.request_with_headers(
            method="GET", path=endpoint, params=params, timeout=request_timeout
        )

        # Parse response - handle nested structure
        # API returns: {"status": "success", "data": {"prices": [...]}}
        if (
            "data" in response
            and isinstance(response["data"], dict)
            and "prices" in response["data"]
        ):
            prices_data = response["data"]["prices"]
        elif "data" in response and isinstance(response["data"], list):
            prices_data = response["data"]
        else:
            prices_data = response if isinstance(response, list) else []

        # Create HistoricalPrice objects
        prices = []
        for price_data in prices_data:
            if isinstance(price_data, dict):
                # Map API fields to model fields
                mapped_data = {
                    "created_at": price_data.get("created_at"),
                    "commodity_name": price_data.get("code", price_data.get("commodity_name")),
                    "price": price_data.get("price"),
                    "currency": price_data.get("currency"),
                    "unit_of_measure": price_data.get("unit"),
                    "type_name": price_data.get("type", "spot_price"),
                }
                prices.append(HistoricalPrice(**mapped_data))

        # Parse pagination metadata — prefer response headers over body
        # API uses X-Total-Pages (Kaminari-style) or X-Has-Next (custom)
        total_pages = int(headers.get("X-Total-Pages", 0))
        has_next_header = str(headers.get("X-Has-Next", "")).lower() == "true" or (
            total_pages > 0 and page < total_pages
        )

        meta = None
        if "meta" in response:
            meta_data = response["meta"]
            meta = PaginationMeta(
                page=meta_data.get("page", page),
                per_page=meta_data.get("per_page", validated_per_page),
                total=meta_data.get("total", len(prices)),
                total_pages=meta_data.get("total_pages", 1),
                has_next=meta_data.get("has_next", has_next_header),
                has_prev=meta_data.get("has_prev", False),
            )
        else:
            # Use X-Has-Next header for reliable pagination detection
            meta = PaginationMeta(
                page=page,
                per_page=validated_per_page,
                total=int(headers.get("X-Total", len(prices))),
                total_pages=int(headers.get("X-Total-Pages", 1)),
                has_next=has_next_header,
                has_prev=page > 1,
            )

        return HistoricalResponse(success=True, data=prices, meta=meta)

    def get_all(
        self,
        commodity: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        interval: str = "daily",
        type_name: str = "spot_price",
        per_page: int = DEFAULT_AUTO_PAGE_SIZE,
    ) -> List[HistoricalPrice]:
        """Get all historical data (handles pagination automatically).

        Args:
            commodity: Commodity code
            start_date: Start date for data range
            end_date: End date for data range
            interval: Data interval
            type_name: Price type
            per_page: Records per request, from 1 to 1000. Defaults to 500.

        Returns:
            List of all HistoricalPrice objects

        Example:
            >>> all_data = client.historical.get_all(
            ...     commodity="WTI_USD",
            ...     start_date="2024-01-01",
            ...     interval="daily"
            ... )
            >>> print(f"Total records: {len(all_data)}")
        """
        validated_per_page = validate_page_size(per_page)
        all_prices: List[HistoricalPrice] = []
        seen_previous_pages: Set[Tuple[object, ...]] = set()
        page = 1

        while True:
            response = self.get(
                commodity=commodity,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                page=page,
                per_page=validated_per_page,
                type_name=type_name,
            )

            if not response.data:
                break

            current_page_keys: Set[Tuple[object, ...]] = set()
            for price in response.data:
                key = _price_key(price)
                if key not in seen_previous_pages:
                    all_prices.append(price)
                current_page_keys.add(key)
            seen_previous_pages.update(current_page_keys)

            if not response.meta or not response.meta.has_next:
                break

            page += 1

        return all_prices

    def iter_pages(
        self,
        commodity: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        interval: str = "daily",
        per_page: int = 100,
        type_name: str = "spot_price",
    ) -> Generator[List[HistoricalPrice], None, None]:
        """Iterate through pages of historical data.

        Memory efficient iterator for large datasets.

        Args:
            commodity: Commodity code
            start_date: Start date for data range
            end_date: End date for data range
            interval: Data interval
            per_page: Items per page
            type_name: Price type

        Yields:
            List of HistoricalPrice objects for each page

        Example:
            >>> for page_data in client.historical.iter_pages("NATURAL_GAS_USD"):
            ...     process_batch(page_data)
            ...     print(f"Processed {len(page_data)} records")
        """
        page = 1

        while True:
            response = self.get(
                commodity=commodity,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                page=page,
                per_page=per_page,
                type_name=type_name,
            )

            if response.data:
                yield response.data
            else:
                break

            if not response.meta or not response.meta.has_next:
                break

            page += 1

    def to_dataframe(
        self,
        commodity: str,
        start: Optional[Union[str, date, datetime]] = None,
        end: Optional[Union[str, date, datetime]] = None,
        interval: str = "daily",
        type_name: str = "spot_price",
        per_page: int = DEFAULT_AUTO_PAGE_SIZE,
    ):
        """Get historical data as a pandas DataFrame.

        Note: Requires pandas to be installed.

        Args:
            commodity: Commodity code
            start: Start date
            end: End date
            interval: Data interval
            type_name: Price type
            per_page: Records per request, from 1 to 1000. All pages are
                fetched automatically; defaults to 500.

        Returns:
            pandas DataFrame with historical prices

        Example:
            >>> df = client.historical.to_dataframe(
            ...     commodity="BRENT_CRUDE_USD",
            ...     start="2024-01-01",
            ...     end="2024-12-31",
            ...     interval="daily"
            ... )
            >>> df.describe()
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for DataFrame support. "
                "Install with: pip install oilpriceapi[pandas]"
            )

        # Get all data
        prices = self.get_all(
            commodity=commodity,
            start_date=start,
            end_date=end,
            interval=interval,
            type_name=type_name,
            per_page=per_page,
        )

        # Convert to DataFrame
        df = pd.DataFrame(
            [p.model_dump() for p in prices],
            columns=HISTORICAL_DATAFRAME_COLUMNS,
        )

        # Set date as index
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            df.sort_index(inplace=True)

        # Ensure numeric types
        if "value" in df.columns:
            df["value"] = pd.to_numeric(df["value"], errors="coerce")

        return df

    def _format_date(self, date_input: Union[str, date, datetime]) -> str:
        """Format date for API."""
        return format_date(date_input)
