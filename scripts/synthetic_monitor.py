"""
Synthetic monitoring for OilPriceAPI SDK.

Runs continuous health checks and reports metrics to Prometheus.
This would have caught the v1.4.1 historical timeout bug.

Usage:
    export OILPRICEAPI_KEY=your_key
    python scripts/synthetic_monitor.py

    # With custom settings
    export METRICS_PORT=8000
    export TEST_INTERVAL=900  # 15 minutes
    python scripts/synthetic_monitor.py
"""

import os
import sys
import time
from datetime import datetime, timedelta

try:
    from prometheus_client import start_http_server, Gauge, Counter, Histogram
    from oilpriceapi import OilPriceAPI
except ImportError:
    print("ERROR: Required dependencies not installed")
    print("Run: pip install oilpriceapi prometheus_client")
    sys.exit(1)


# Prometheus Metrics
QUERY_DURATION = Histogram(
    'sdk_historical_query_duration_seconds',
    'Historical query duration in seconds',
    ['query_type', 'commodity'],
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

QUERY_SUCCESS = Counter(
    'sdk_historical_query_success_total',
    'Total successful historical queries',
    ['query_type', 'commodity']
)

QUERY_FAILURE = Counter(
    'sdk_historical_query_failure_total',
    'Total failed historical queries',
    ['query_type', 'commodity', 'error_type']
)

ENDPOINT_CORRECTNESS = Gauge(
    'sdk_endpoint_selection_correct',
    'Whether SDK selected correct endpoint (1=correct, 0=wrong)',
    ['query_type']
)

RECORD_COUNT = Gauge(
    'sdk_historical_records_returned',
    'Number of records returned by historical query',
    ['query_type', 'commodity']
)

LAST_TEST_TIMESTAMP = Gauge(
    'sdk_monitor_last_test_timestamp',
    'Unix timestamp of last test run'
)


def test_1_day_query(client, commodity="WTI_USD"):
    """Test 1-day historical query."""
    query_type = "1_day"
    print(f"  Testing {query_type} query for {commodity}...")

    start_time = time.time()
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        history = client.historical.get(
            commodity=commodity,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="hourly"
        )

        duration = time.time() - start_time
        record_count = len(history.data)

        QUERY_DURATION.labels(query_type=query_type, commodity=commodity).observe(duration)
        QUERY_SUCCESS.labels(query_type=query_type, commodity=commodity).inc()
        RECORD_COUNT.labels(query_type=query_type, commodity=commodity).set(record_count)

        # Expected: <10s for 1-day query
        is_correct = duration < 10
        ENDPOINT_CORRECTNESS.labels(query_type=query_type).set(1 if is_correct else 0)

        status = "✓" if is_correct else "✗"
        print(f"    {status} Completed in {duration:.2f}s ({record_count} records)")

        if not is_correct:
            print(f"    WARNING: Expected <10s, got {duration:.2f}s")

        return is_correct

    except Exception as e:
        duration = time.time() - start_time
        error_type = type(e).__name__

        QUERY_FAILURE.labels(query_type=query_type, commodity=commodity, error_type=error_type).inc()
        ENDPOINT_CORRECTNESS.labels(query_type=query_type).set(0)

        print(f"    ✗ Failed after {duration:.2f}s: {error_type}: {str(e)[:100]}")
        return False


def test_1_week_query(client, commodity="WTI_USD"):
    """
    Test 1-week historical query.

    This test would have caught the v1.4.1 bug:
    - Bug: Took 67s (using wrong endpoint)
    - Expected: <30s (using /v1/prices/past_week)
    """
    query_type = "1_week"
    print(f"  Testing {query_type} query for {commodity}...")

    start_time = time.time()
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        history = client.historical.get(
            commodity=commodity,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="daily"
        )

        duration = time.time() - start_time
        record_count = len(history.data)

        QUERY_DURATION.labels(query_type=query_type, commodity=commodity).observe(duration)
        QUERY_SUCCESS.labels(query_type=query_type, commodity=commodity).inc()
        RECORD_COUNT.labels(query_type=query_type, commodity=commodity).set(record_count)

        # Expected: <30s for 1-week query (would catch v1.4.1 bug)
        is_correct = duration < 30
        ENDPOINT_CORRECTNESS.labels(query_type=query_type).set(1 if is_correct else 0)

        status = "✓" if is_correct else "✗"
        print(f"    {status} Completed in {duration:.2f}s ({record_count} records)")

        if not is_correct:
            print(f"    🚨 CRITICAL: Expected <30s, got {duration:.2f}s")
            print(f"    This matches the v1.4.1 bug pattern!")

        return is_correct

    except Exception as e:
        duration = time.time() - start_time
        error_type = type(e).__name__

        QUERY_FAILURE.labels(query_type=query_type, commodity=commodity, error_type=error_type).inc()
        ENDPOINT_CORRECTNESS.labels(query_type=query_type).set(0)

        print(f"    ✗ Failed after {duration:.2f}s: {error_type}: {str(e)[:100]}")
        return False


def test_1_month_query(client, commodity="WTI_USD"):
    """Test 1-month historical query."""
    query_type = "1_month"
    print(f"  Testing {query_type} query for {commodity}...")

    start_time = time.time()
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        history = client.historical.get(
            commodity=commodity,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="daily"
        )

        duration = time.time() - start_time
        record_count = len(history.data)

        QUERY_DURATION.labels(query_type=query_type, commodity=commodity).observe(duration)
        QUERY_SUCCESS.labels(query_type=query_type, commodity=commodity).inc()
        RECORD_COUNT.labels(query_type=query_type, commodity=commodity).set(record_count)

        # Expected: <60s for 1-month query
        is_correct = duration < 60
        ENDPOINT_CORRECTNESS.labels(query_type=query_type).set(1 if is_correct else 0)

        status = "✓" if is_correct else "✗"
        print(f"    {status} Completed in {duration:.2f}s ({record_count} records)")

        if not is_correct:
            print(f"    WARNING: Expected <60s, got {duration:.2f}s")

        return is_correct

    except Exception as e:
        duration = time.time() - start_time
        error_type = type(e).__name__

        QUERY_FAILURE.labels(query_type=query_type, commodity=commodity, error_type=error_type).inc()
        ENDPOINT_CORRECTNESS.labels(query_type=query_type).set(0)

        print(f"    ✗ Failed after {duration:.2f}s: {error_type}: {str(e)[:100]}")
        return False


def test_1_year_query(client, commodity="WTI_USD"):
    """
    Test 1-year historical query.

    This test would have caught the v1.4.1 bug:
    - Bug: Timed out at 30s
    - Expected: Complete in <120s
    """
    query_type = "1_year"
    print(f"  Testing {query_type} query for {commodity}...")

    start_time = time.time()
    try:
        # Use fixed date range for consistency
        history = client.historical.get(
            commodity=commodity,
            start_date="2024-01-01",
            end_date="2024-12-31",
            interval="daily"
        )

        duration = time.time() - start_time
        record_count = len(history.data)

        QUERY_DURATION.labels(query_type=query_type, commodity=commodity).observe(duration)
        QUERY_SUCCESS.labels(query_type=query_type, commodity=commodity).inc()
        RECORD_COUNT.labels(query_type=query_type, commodity=commodity).set(record_count)

        # Expected: <120s for 1-year query (would catch v1.4.1 timeout bug)
        is_correct = duration < 120
        ENDPOINT_CORRECTNESS.labels(query_type=query_type).set(1 if is_correct else 0)

        status = "✓" if is_correct else "✗"
        print(f"    {status} Completed in {duration:.2f}s ({record_count} records)")

        if not is_correct:
            print(f"    🚨 CRITICAL: Expected <120s, got {duration:.2f}s")
            print(f"    This matches the v1.4.1 timeout bug!")

        return is_correct

    except Exception as e:
        duration = time.time() - start_time
        error_type = type(e).__name__

        QUERY_FAILURE.labels(query_type=query_type, commodity=commodity, error_type=error_type).inc()
        ENDPOINT_CORRECTNESS.labels(query_type=query_type).set(0)

        print(f"    ✗ Failed after {duration:.2f}s: {error_type}: {str(e)[:100]}")

        if "timeout" in str(e).lower() or error_type == "TimeoutError":
            print(f"    🚨 CRITICAL: TIMEOUT DETECTED - THIS IS THE v1.4.1 BUG!")

        return False


def run_synthetic_tests(client):
    """Run all synthetic tests."""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running synthetic tests...")

    results = {
        "1_day": test_1_day_query(client),
        "1_week": test_1_week_query(client),
        "1_month": test_1_month_query(client),
        "1_year": test_1_year_query(client),
    }

    LAST_TEST_TIMESTAMP.set(time.time())

    # Summary
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\n  Summary: {passed}/{total} tests passed")

    if passed < total:
        print(f"  ⚠️  {total - passed} test(s) failed - check logs above")

    return passed == total


def main():
    """Main monitoring loop."""
    print("="*60)
    print("OilPriceAPI SDK Synthetic Monitor")
    print("="*60)
    print("")
    print("This monitor would have caught the v1.4.1 timeout bug.")
    print("")

    # Get configuration from environment
    api_key = os.getenv('OILPRICEAPI_KEY')
    if not api_key:
        print("ERROR: OILPRICEAPI_KEY environment variable not set")
        print("")
        print("Set it with:")
        print("  export OILPRICEAPI_KEY=your_key")
        return 1

    metrics_port = int(os.getenv('METRICS_PORT', '8000'))
    test_interval = int(os.getenv('TEST_INTERVAL', '900'))  # 15 minutes default

    print(f"Configuration:")
    print(f"  API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"  Metrics Port: {metrics_port}")
    print(f"  Test Interval: {test_interval}s ({test_interval/60:.0f} minutes)")
    print("")

    # Start Prometheus metrics server
    try:
        start_http_server(metrics_port)
        print(f"✓ Metrics server started on http://0.0.0.0:{metrics_port}/metrics")
    except OSError as e:
        print(f"ERROR: Failed to start metrics server on port {metrics_port}: {e}")
        print(f"Try a different port: METRICS_PORT=8001 python {sys.argv[0]}")
        return 1

    # Create SDK client
    try:
        client = OilPriceAPI(api_key=api_key)
        print(f"✓ SDK client initialized")
    except Exception as e:
        print(f"ERROR: Failed to initialize SDK client: {e}")
        return 1

    print("")
    print("Starting monitoring loop (Ctrl+C to stop)...")
    print("")

    # Run tests immediately on start
    try:
        run_synthetic_tests(client)
    except Exception as e:
        print(f"ERROR in initial test run: {e}")

    # Monitoring loop
    test_count = 1
    while True:
        try:
            time.sleep(test_interval)
            test_count += 1
            print(f"\n{'='*60}")
            print(f"Test run #{test_count}")
            print(f"{'='*60}")
            run_synthetic_tests(client)

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user (Ctrl+C)")
            break

        except Exception as e:
            print(f"\nERROR in monitoring loop: {e}")
            print("Continuing monitoring...")
            time.sleep(60)  # Wait a minute before retrying

    return 0


if __name__ == '__main__':
    sys.exit(main())
