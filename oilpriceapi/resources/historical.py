"""
Historical Data Resource

Historical price data operations.
"""

from typing import List, Optional, Union, Generator
from datetime import datetime, date

from ..models import HistoricalPrice, HistoricalResponse, PaginationMeta


class HistoricalResource:
    """Resource for historical price data."""
    
    def __init__(self, client):
        self.client = client
    
    def get(
        self,
        commodity: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        interval: str = "daily",
        page: int = 1,
        per_page: int = 100,
        type_name: str = "spot_price"
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
        """
        # Build parameters
        params = {
            "commodity": commodity,
            "interval": interval,
            "page": page,
            "per_page": min(per_page, 1000),  # Max 1000 per page
            "by_type": type_name,
        }
        
        # Add date parameters if provided
        if start_date:
            params["start_date"] = self._format_date(start_date)
        if end_date:
            params["end_date"] = self._format_date(end_date)
        
        # Make request
        response = self.client.request(
            method="GET",
            path="/v1/prices/past_year",  # This endpoint handles all historical data
            params=params
        )
        
        # Parse response - handle nested structure
        # API returns: {"status": "success", "data": {"prices": [...]}}
        if "data" in response and isinstance(response["data"], dict) and "prices" in response["data"]:
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
                    "unit_of_measure": price_data.get("unit", "barrel"),
                    "type_name": price_data.get("type", "spot_price"),
                }
                prices.append(HistoricalPrice(**mapped_data))
        
        # Parse pagination metadata
        meta = None
        if "meta" in response:
            meta_data = response["meta"]
            meta = PaginationMeta(
                page=meta_data.get("page", page),
                per_page=meta_data.get("per_page", per_page),
                total=meta_data.get("total", len(prices)),
                total_pages=meta_data.get("total_pages", 1),
                has_next=meta_data.get("has_next", False),
                has_prev=meta_data.get("has_prev", False),
            )
        else:
            # Create default metadata if not in response
            meta = PaginationMeta(
                page=page,
                per_page=per_page,
                total=len(prices),
                total_pages=1,
                has_next=len(prices) == per_page,
                has_prev=page > 1,
            )
        
        return HistoricalResponse(
            success=True,
            data=prices,
            meta=meta
        )
    
    def get_all(
        self,
        commodity: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        interval: str = "daily",
        type_name: str = "spot_price"
    ) -> List[HistoricalPrice]:
        """Get all historical data (handles pagination automatically).
        
        Args:
            commodity: Commodity code
            start_date: Start date for data range
            end_date: End date for data range
            interval: Data interval
            type_name: Price type
            
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
        all_prices = []
        page = 1
        
        while True:
            response = self.get(
                commodity=commodity,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                page=page,
                per_page=1000,  # Max per page
                type_name=type_name
            )
            
            all_prices.extend(response.data)
            
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
        type_name: str = "spot_price"
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
                type_name=type_name
            )
            
            if response.data:
                yield response.data
            
            if not response.meta or not response.meta.has_next:
                break
            
            page += 1
    
    def to_dataframe(
        self,
        commodity: str,
        start: Optional[Union[str, date, datetime]] = None,
        end: Optional[Union[str, date, datetime]] = None,
        interval: str = "daily",
        type_name: str = "spot_price"
    ):
        """Get historical data as a pandas DataFrame.
        
        Note: Requires pandas to be installed.
        
        Args:
            commodity: Commodity code
            start: Start date
            end: End date
            interval: Data interval
            type_name: Price type
            
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
            type_name=type_name
        )
        
        # Convert to DataFrame
        df = pd.DataFrame([p.model_dump() for p in prices])
        
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
        if isinstance(date_input, str):
            return date_input
        elif isinstance(date_input, datetime):
            return date_input.date().isoformat()
        elif isinstance(date_input, date):
            return date_input.isoformat()
        else:
            raise ValueError(f"Invalid date type: {type(date_input)}")
