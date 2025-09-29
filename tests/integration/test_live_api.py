"""
Integration tests that hit the real API.

These tests require a valid API key and should be run sparingly.
Set OILPRICEAPI_KEY environment variable to run these tests.
"""

import pytest
import os
from datetime import datetime, timedelta
from oilpriceapi import OilPriceAPI
from oilpriceapi.exceptions import AuthenticationError, DataNotFoundError

# Note: .env loading and live_client fixture are provided by conftest.py


class TestLiveAPIIntegration:
    """Integration tests with live API."""

    def test_get_current_price(self, live_client):
        """Test getting current price from live API."""
        price = live_client.prices.get("BRENT_CRUDE_USD")

        assert price is not None
        assert price.commodity == "BRENT_CRUDE_USD"
        assert price.value > 0
        assert price.currency == "USD"
        assert isinstance(price.timestamp, datetime)

    def test_get_multiple_prices(self, live_client):
        """Test getting multiple prices."""
        commodities = ["BRENT_CRUDE_USD", "WTI_USD", "NATURAL_GAS_USD"]
        prices = live_client.prices.get_multiple(commodities)

        assert len(prices) >= 1  # At least some should succeed
        for price in prices:
            assert price.value > 0
            assert price.commodity in commodities

    def test_get_historical_data(self, live_client):
        """Test getting historical data."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        history = live_client.historical.get(
            commodity="BRENT_CRUDE_USD",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            per_page=100,
        )

        assert history is not None
        assert len(history.data) > 0
        for price in history.data:
            assert price.value > 0
            assert price.commodity == "BRENT_CRUDE_USD"

    def test_invalid_commodity(self, live_client):
        """Test handling of invalid commodity."""
        with pytest.raises(DataNotFoundError):
            live_client.prices.get("TOTALLY_INVALID_COMMODITY_XYZ")

    @pytest.mark.skip(reason="API currently doesn't validate API keys for read operations")
    def test_invalid_api_key(self):
        """Test authentication error with invalid key."""
        # Note: This test is skipped because the API doesn't currently
        # return 401 for invalid keys on read operations
        bad_client = OilPriceAPI(api_key="invalid_key_123")

        with pytest.raises(AuthenticationError):
            bad_client.prices.get("BRENT_CRUDE_USD")

    def test_context_manager(self, api_key):
        """Test client works as context manager."""
        with OilPriceAPI(api_key=api_key) as client:
            price = client.prices.get("BRENT_CRUDE_USD")
            assert price is not None


@pytest.mark.slow
class TestLiveAPIPerformance:
    """Performance tests (marked slow)."""

    def test_pagination_performance(self, live_client):
        """Test pagination doesn't cause issues."""
        # Get a reasonable amount of data
        history = live_client.historical.get(
            commodity="BRENT_CRUDE_USD",
            start_date="2024-01-01",
            end_date="2024-01-31",
            per_page=1000,
        )

        assert len(history.data) > 0

    @pytest.mark.skipif(
        not os.getenv("RUN_EXPENSIVE_TESTS"),
        reason="Expensive test - set RUN_EXPENSIVE_TESTS=1 to run"
    )
    def test_get_all_historical_large_dataset(self, live_client):
        """Test get_all with large dataset (expensive)."""
        # This could use many API calls
        all_data = live_client.historical.get_all(
            commodity="BRENT_CRUDE_USD",
            start_date="2024-01-01",
            end_date="2024-02-01",
        )

        assert len(all_data) > 0