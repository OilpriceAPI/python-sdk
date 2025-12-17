"""
Contract tests for OilPriceAPI.

These tests validate that the API behaves as the SDK expects.
If the API changes in a breaking way, these tests will fail and
alert us to update the SDK.

Contract tests are different from integration tests:
- Integration tests: Verify SDK functionality works
- Contract tests: Verify API contract hasn't changed

Run with: pytest tests/contract/ -v
"""

import pytest
import os
from datetime import datetime, timedelta
from oilpriceapi import OilPriceAPI


@pytest.mark.contract
class TestPricesEndpointContract:
    """Validate /v1/prices/latest endpoint contract."""

    def test_latest_price_response_format(self, live_client):
        """Verify latest price response has expected format."""
        price = live_client.prices.get("WTI_USD")

        # Contract: Response must have these fields
        assert hasattr(price, 'commodity'), "Missing 'commodity' field"
        assert hasattr(price, 'value'), "Missing 'value' field"
        assert hasattr(price, 'currency'), "Missing 'currency' field"
        assert hasattr(price, 'timestamp'), "Missing 'timestamp' field"

        # Contract: Fields must have correct types
        assert isinstance(price.commodity, str), "commodity must be string"
        assert isinstance(price.value, (int, float)), "value must be number"
        assert isinstance(price.currency, str), "currency must be string"
        assert isinstance(price.timestamp, datetime), "timestamp must be datetime"

    def test_latest_price_commodity_code_format(self, live_client):
        """Verify commodity codes follow expected format."""
        price = live_client.prices.get("WTI_USD")

        # Contract: Commodity codes are uppercase with underscores
        assert price.commodity.isupper(), "Commodity code must be uppercase"
        assert price.commodity.endswith("_USD"), "Commodity code must end with currency"
        assert "_" in price.commodity, "Commodity code must contain underscore"

    def test_latest_price_value_is_positive(self, live_client):
        """Verify price values are positive numbers."""
        commodities = ["WTI_USD", "BRENT_CRUDE_USD", "NATURAL_GAS_USD"]

        for commodity_code in commodities:
            price = live_client.prices.get(commodity_code)

            # Contract: Prices must be positive
            assert price.value > 0, f"{commodity_code} price must be positive"
            assert price.value < 1000000, f"{commodity_code} price seems unrealistic"

    def test_latest_price_timestamp_is_recent(self, live_client):
        """Verify timestamps are recent (not stale data)."""
        price = live_client.prices.get("WTI_USD")

        # Contract: Timestamps should be within last 7 days
        age = datetime.now(price.timestamp.tzinfo) - price.timestamp
        assert age.days < 7, f"Price timestamp is {age.days} days old (stale data?)"

    def test_invalid_commodity_returns_404(self, live_client):
        """Verify invalid commodity codes return 404."""
        from oilpriceapi.exceptions import DataNotFoundError

        # Contract: Invalid commodity should raise DataNotFoundError
        with pytest.raises(DataNotFoundError) as exc_info:
            live_client.prices.get("INVALID_COMMODITY_XYZ")

        assert "not found" in str(exc_info.value).lower()


@pytest.mark.contract
class TestHistoricalEndpointContract:
    """Validate /v1/prices endpoint contract."""

    def test_historical_response_format(self, live_client):
        """Verify historical response has expected format."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="daily"
        )

        # Contract: Response must be iterable
        assert hasattr(history, 'data'), "Missing 'data' field"
        assert hasattr(history.data, '__iter__'), "data must be iterable"
        assert len(history.data) > 0, "data must not be empty"

        # Contract: Each price must have expected fields
        for price in history.data:
            assert hasattr(price, 'date'), "Missing 'date' field"
            assert hasattr(price, 'value'), "Missing 'value' field"
            assert hasattr(price, 'commodity'), "Missing 'commodity' field"

    def test_historical_dates_are_chronological(self, live_client):
        """Verify historical data is returned in chronological order."""
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date="2024-01-01",
            end_date="2024-01-31",
            interval="daily"
        )

        dates = [p.date for p in history.data]

        # Contract: Dates should be sorted (descending - newest first)
        assert dates == sorted(dates, reverse=True), \
            "Historical data must be sorted by date (descending)"

    def test_historical_interval_is_respected(self, live_client):
        """Verify interval parameter is respected."""
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date="2024-01-01",
            end_date="2024-01-31",
            interval="daily"
        )

        # Contract: Daily interval should return approximately one record per day
        # (accounting for weekends/holidays)
        assert len(history.data) >= 20, "Daily interval should return ~20-31 records for a month"
        assert len(history.data) <= 31, "Daily interval should not return more than 31 records"

    def test_historical_date_range_is_respected(self, live_client):
        """Verify date range boundaries are respected."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="daily"
        )

        # Contract: All dates must be within requested range
        for price in history.data:
            assert price.date >= start_date, \
                f"Date {price.date} is before start_date {start_date}"
            assert price.date <= end_date, \
                f"Date {price.date} is after end_date {end_date}"

    def test_historical_pagination_metadata(self, live_client):
        """Verify pagination metadata is present."""
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date="2024-01-01",
            end_date="2024-01-31",
            interval="daily",
            per_page=10
        )

        # Contract: Response should have pagination metadata
        assert hasattr(history, 'meta'), "Missing 'meta' field"
        assert hasattr(history.meta, 'page'), "Missing 'meta.page' field"
        assert hasattr(history.meta, 'total'), "Missing 'meta.total' field"
        assert hasattr(history.meta, 'per_page'), "Missing 'meta.per_page' field"

        # Contract: Metadata values should be reasonable
        assert history.meta.page >= 1, "page must be >= 1"
        assert history.meta.per_page == 10, "per_page should match requested value"
        assert history.meta.total > 0, "total must be positive"


@pytest.mark.contract
class TestEndpointAvailability:
    """Verify expected endpoints exist and return correct status codes."""

    def test_past_day_endpoint_exists(self, live_client):
        """Verify /v1/prices/past_day endpoint exists."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        # Should use past_day endpoint
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="hourly"
        )

        # Contract: Endpoint should return data
        assert history is not None
        assert len(history.data) > 0

    def test_past_week_endpoint_exists(self, live_client):
        """Verify /v1/prices/past_week endpoint exists."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        # Should use past_week endpoint
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="daily"
        )

        # Contract: Endpoint should return data
        assert history is not None
        assert len(history.data) > 0

    def test_past_month_endpoint_exists(self, live_client):
        """Verify /v1/prices/past_month endpoint exists."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        # Should use past_month endpoint
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="daily"
        )

        # Contract: Endpoint should return data
        assert history is not None
        assert len(history.data) > 0

    def test_past_year_endpoint_exists(self, live_client):
        """Verify /v1/prices/past_year endpoint exists."""
        # Should use past_year endpoint
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date="2024-01-01",
            end_date="2024-12-31",
            interval="daily"
        )

        # Contract: Endpoint should return data
        assert history is not None
        assert len(history.data) > 0


@pytest.mark.contract
class TestErrorResponseContract:
    """Validate error response formats."""

    def test_404_error_format(self, live_client):
        """Verify 404 errors have expected format."""
        from oilpriceapi.exceptions import DataNotFoundError

        with pytest.raises(DataNotFoundError) as exc_info:
            live_client.prices.get("NONEXISTENT_COMMODITY")

        # Contract: Error should have message
        assert str(exc_info.value), "Error should have message"

    def test_rate_limit_header_format(self, live_client):
        """Verify rate limit headers are present (if applicable)."""
        # Make a request
        price = live_client.prices.get("WTI_USD")

        # Contract: If rate limiting is implemented, headers should be present
        # (This is informational, not a strict requirement)
        # Note: Would need to inspect response headers via client._client.last_response


@pytest.mark.contract
class TestDataTypeContract:
    """Validate data types match SDK expectations."""

    def test_price_values_are_decimal_compatible(self, live_client):
        """Verify price values can be used with Decimal."""
        from decimal import Decimal

        price = live_client.prices.get("WTI_USD")

        # Contract: Prices should be convertible to Decimal for precise calculations
        decimal_price = Decimal(str(price.value))
        assert decimal_price > 0, "Decimal price must be positive"

    def test_timestamps_are_timezone_aware(self, live_client):
        """Verify timestamps include timezone information."""
        price = live_client.prices.get("WTI_USD")

        # Contract: Timestamps should be timezone-aware
        assert price.timestamp.tzinfo is not None, \
            "Timestamps must be timezone-aware"

    def test_historical_dates_are_timezone_aware(self, live_client):
        """Verify historical dates include timezone information."""
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date="2024-01-01",
            end_date="2024-01-31",
            interval="daily"
        )

        for price in history.data:
            # Contract: All dates should be timezone-aware
            assert price.date.tzinfo is not None, \
                f"Date {price.date} must be timezone-aware"


@pytest.mark.contract
class TestBackwardCompatibility:
    """Verify backward compatibility with previous SDK versions."""

    def test_historical_without_interval_still_works(self, live_client):
        """Verify historical queries work without explicit interval."""
        # SDK v1.0 didn't require interval parameter
        # Contract: This should still work for backward compatibility
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date="2024-01-01",
            end_date="2024-01-31"
            # No interval specified
        )

        assert history is not None
        assert len(history.data) > 0

    def test_commodity_codes_stable_across_versions(self, live_client):
        """Verify commodity codes haven't changed."""
        # Contract: Core commodity codes should remain stable
        core_commodities = ["WTI_USD", "BRENT_CRUDE_USD", "NATURAL_GAS_USD"]

        for commodity_code in core_commodities:
            price = live_client.prices.get(commodity_code)
            assert price.commodity == commodity_code, \
                f"Commodity code should match request: {price.commodity} != {commodity_code}"
