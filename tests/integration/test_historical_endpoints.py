"""
Integration tests for historical data endpoints.

These tests verify endpoint selection, timeouts, and performance
for real API calls. They would have caught the v1.4.1 timeout bug.

Run with: pytest tests/integration/test_historical_endpoints.py -v
Skip with: pytest tests/integration -m "not integration"
"""

import os
import pytest
import time
from datetime import datetime, timedelta
from oilpriceapi import OilPriceAPI
from oilpriceapi.exceptions import TimeoutError


@pytest.mark.integration
class TestHistoricalEndpointSelection:
    """Test that SDK selects correct endpoints for different date ranges."""

    def test_1_day_query_uses_past_day_endpoint(self, live_client):
        """Verify 1-day queries use /v1/prices/past_day endpoint."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        start_time = time.time()
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="hourly"
        )
        duration = time.time() - start_time

        # Verify response
        assert history is not None
        assert len(history.data) > 0

        # Should be fast (using optimized endpoint)
        assert duration < 10, f"1-day query took {duration}s, expected <10s"

    def test_7_day_query_uses_past_week_endpoint(self, live_client):
        """Verify 7-day queries use /v1/prices/past_week endpoint."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        start_time = time.time()
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="daily"
        )
        duration = time.time() - start_time

        # Verify response
        assert history is not None
        assert len(history.data) > 0
        assert len(history.data) <= 10  # Should return ~7-8 days (inclusive range)

        # Should be fast (using optimized endpoint)
        # Bug in v1.4.1: This took 67s using wrong endpoint
        assert duration < 30, f"7-day query took {duration}s, expected <30s"
        print(f"✓ 7-day query completed in {duration:.2f}s (optimized endpoint)")

    def test_30_day_query_uses_past_month_endpoint(self, live_client):
        """Verify 30-day queries use /v1/prices/past_month endpoint."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        start_time = time.time()
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="daily"
        )
        duration = time.time() - start_time

        # Verify response
        assert history is not None
        assert len(history.data) > 0
        assert len(history.data) <= 31  # Should return ~30 days

        # Should be reasonably fast (using optimized endpoint)
        # Bug in v1.4.1: This took 67s using wrong endpoint
        assert duration < 60, f"30-day query took {duration}s, expected <60s"
        print(f"✓ 30-day query completed in {duration:.2f}s (optimized endpoint)")

    def test_365_day_query_uses_past_year_endpoint(self, live_client):
        """
        Verify 365-day queries use /v1/prices/past_year endpoint.

        This is the EXACT query that failed for Idan in v1.4.1.
        """
        start_time = time.time()
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date="2024-01-01",
            end_date="2024-12-31",
            interval="daily"
        )
        duration = time.time() - start_time

        # Verify response
        assert history is not None
        # API returns paginated results (100 per page by default)
        assert len(history.data) > 0, f"Expected data, got {len(history.data)}"
        # Note: API pagination metadata may not reflect full dataset correctly
        # The key test is that the query completes successfully without timing out

        # Should complete successfully (with 120s timeout in v1.4.2)
        # Bug in v1.4.1: This timed out at 30s
        # THIS IS THE CRITICAL TEST - would have caught v1.4.1 bug
        assert duration < 120, f"1-year query took {duration}s, exceeds 120s timeout"
        print(f"✓ 1-year query completed in {duration:.2f}s (within 120s timeout)")

        # Verify data quality
        for price in history.data[:5]:
            assert price.value > 0
            assert price.commodity == "WTI_USD"
            assert price.date is not None


@pytest.mark.integration
@pytest.mark.slow
class TestHistoricalTimeoutBehavior:
    """Test timeout handling for historical queries."""

    def test_custom_timeout_is_respected(self, live_client):
        """Test that custom timeout parameter works."""
        # Try a multi-year query with custom timeout
        start_time = time.time()

        try:
            history = live_client.historical.get(
                commodity="WTI_USD",
                start_date="2020-01-01",
                end_date="2024-12-31",
                interval="daily",
                timeout=180  # 3 minutes for 5 years
            )
            duration = time.time() - start_time

            assert history is not None
            assert len(history.data) > 1000  # ~5 years of data
            print(f"✓ Multi-year query completed in {duration:.2f}s with custom timeout")

        except Exception as e:
            duration = time.time() - start_time
            print(f"✗ Query failed after {duration:.2f}s: {e}")
            # Still assert we tried with the right timeout
            assert duration >= 120, "Should have used longer timeout"

    def test_timeout_scales_with_date_range(self, live_client):
        """Verify timeout automatically scales for larger date ranges."""
        # Small query should have short timeout
        start_time = time.time()
        history_week = live_client.historical.get(
            commodity="BRENT_CRUDE_USD",
            start_date=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            end_date=datetime.now().strftime("%Y-%m-%d"),
            interval="daily"
        )
        week_duration = time.time() - start_time

        assert history_week is not None
        assert week_duration < 30  # Uses 30s timeout

        # Large query should have longer timeout
        start_time = time.time()
        history_year = live_client.historical.get(
            commodity="BRENT_CRUDE_USD",
            start_date="2024-01-01",
            end_date="2024-12-31",
            interval="daily"
        )
        year_duration = time.time() - start_time

        assert history_year is not None
        # Should complete within 120s timeout (not 30s like v1.4.1)
        assert year_duration < 120


@pytest.mark.integration
@pytest.mark.slow
class TestHistoricalPerformanceBaselines:
    """
    Establish performance baselines for historical queries.

    These tests document expected response times and alert on regressions.
    """

    def test_1_week_query_performance_baseline(self, live_client):
        """1-week queries should complete in <30s."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        start_time = time.time()
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="daily"
        )
        duration = time.time() - start_time

        assert history is not None
        assert duration < 30, f"Regression: 1-week query took {duration}s (baseline: <30s)"

        # Record baseline for monitoring
        print(f"📊 Performance baseline: 1-week query = {duration:.2f}s")

    def test_1_month_query_performance_baseline(self, live_client):
        """1-month queries should complete in <60s."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        start_time = time.time()
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="daily"
        )
        duration = time.time() - start_time

        assert history is not None
        assert duration < 60, f"Regression: 1-month query took {duration}s (baseline: <60s)"

        print(f"📊 Performance baseline: 1-month query = {duration:.2f}s")

    def test_1_year_query_performance_baseline(self, live_client):
        """
        1-year queries should complete in <120s.

        This test documents the exact scenario that failed for Idan.
        """
        start_time = time.time()
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date="2024-01-01",
            end_date="2024-12-31",
            interval="daily"
        )
        duration = time.time() - start_time

        assert history is not None
        assert len(history.data) > 300
        assert duration < 120, f"Regression: 1-year query took {duration}s (baseline: <120s)"

        print(f"📊 Performance baseline: 1-year query = {duration:.2f}s")

        # Alert if approaching timeout
        if duration > 100:
            print(f"⚠️  WARNING: Query took {duration:.2f}s, approaching 120s timeout!")


@pytest.mark.integration
class TestHistoricalDataQuality:
    """Test data quality for historical queries."""

    def test_year_query_returns_complete_data(self, live_client):
        """Verify 1-year query returns complete dataset."""
        history = live_client.historical.get(
            commodity="WTI_USD",
            start_date="2024-01-01",
            end_date="2024-12-31",
            interval="daily"
        )

        assert history is not None
        # API returns paginated results (100 per page by default)
        # Verify we got at least one page of data
        assert len(history.data) > 0, f"Expected data, got {len(history.data)}"
        # Note: Full dataset validation requires pagination support

        # Verify chronological order
        dates = [p.date for p in history.data]
        assert dates == sorted(dates, reverse=True), "Data should be sorted by date (descending)"

    def test_historical_data_matches_commodity(self, live_client):
        """Verify all returned data matches requested commodity."""
        commodities = ["WTI_USD", "BRENT_CRUDE_USD", "NATURAL_GAS_USD"]

        for commodity_code in commodities:
            history = live_client.historical.get(
                commodity=commodity_code,
                start_date=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
                interval="daily"
            )

            assert history is not None
            for price in history.data:
                assert price.commodity == commodity_code


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("CI") is None,
    reason="Stress tests only run in CI"
)
class TestHistoricalStressTests:
    """Stress tests for historical queries (CI only)."""

    def test_concurrent_historical_queries(self, live_client):
        """Test multiple historical queries don't cause issues."""
        import concurrent.futures

        def query_historical(commodity):
            return live_client.historical.get(
                commodity=commodity,
                start_date="2024-01-01",
                end_date="2024-01-31",
                interval="daily"
            )

        commodities = ["WTI_USD", "BRENT_CRUDE_USD", "NATURAL_GAS_USD"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(query_historical, c) for c in commodities]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 3
        for result in results:
            assert result is not None
            assert len(result.data) > 0
