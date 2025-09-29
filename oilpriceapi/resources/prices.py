"""
Prices Resource

Current price operations.
"""

from typing import List, Optional, Union
from datetime import datetime

from ..models import Price, PriceResponse, MultiplePricesResponse


class PricesResource:
    """Resource for current price operations."""
    
    def __init__(self, client):
        self.client = client
    
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
            method="GET",
            path="/v1/prices/latest",
            params={"by_code": commodity}
        )
        
        # Parse response
        if "data" in response:
            price_data = response["data"]
        else:
            price_data = response

        # Map API response to Price model
        # Note: API should provide 'unit' field. If missing, we default to 'barrel'
        # for backwards compatibility, but this may be incorrect for non-oil commodities
        # (e.g., natural gas measured in MMBtu, electricity in MWh)
        mapped_data = {
            "commodity": price_data.get("code", commodity),
            "value": price_data.get("price"),
            "currency": price_data.get("currency", "USD"),
            "unit": price_data.get("unit", "barrel"),
            "timestamp": price_data.get("created_at"),
        }

        return Price(**mapped_data)
    
    def get_multiple(
        self,
        commodities: List[str],
        raise_on_error: bool = False,
        return_failures: bool = False
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

        for commodity in commodities:
            try:
                price = self.get(commodity)
                prices.append(price)
            except OilPriceAPIError as e:
                if raise_on_error:
                    raise
                failures.append((commodity, str(e)))
                continue

        if return_failures:
            return prices, failures
        return prices
    
    def get_all(self) -> List[Price]:
        """Get current prices for all available commodities.
        
        Returns:
            List of Price objects for all commodities
            
        Example:
            >>> all_prices = client.prices.get_all()
            >>> oil_prices = [p for p in all_prices if 'CRUDE' in p.commodity]
        """
        response = self.client.request(
            method="GET",
            path="/v1/prices/all"
        )
        
        # Parse response
        if "data" in response:
            prices_data = response["data"]
        else:
            prices_data = response
        
        return [Price(**price_data) for price_data in prices_data]
    
    def to_dataframe(
        self,
        commodity: Optional[str] = None,
        commodities: Optional[List[str]] = None,
        start: Optional[Union[str, datetime]] = None,
        end: Optional[Union[str, datetime]] = None,
        interval: str = "daily"
    ):
        """Get price data as a pandas DataFrame.
        
        Note: Requires pandas to be installed.
        
        Args:
            commodity: Single commodity code
            commodities: Multiple commodity codes
            start: Start date for historical data
            end: End date for historical data
            interval: Data interval (minute, hourly, daily, weekly, monthly)
            
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
                    interval=interval
                )
            elif commodities:
                dfs = []
                for comm in commodities:
                    df_comm = hist.to_dataframe(
                        commodity=comm,
                        start=start,
                        end=end,
                        interval=interval
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
            prices = self.get_multiple(commodities)
            df = pd.DataFrame([p.model_dump() for p in prices])
        else:
            prices = self.get_all()
            df = pd.DataFrame([p.model_dump() for p in prices])
        
        # Set timestamp as index
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.set_index("timestamp", inplace=True)
        
        return df
