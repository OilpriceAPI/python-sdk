#!/usr/bin/env python3
"""
Python SDK Audit Test Script

Tests all documented SDK features against production API to verify
README examples work correctly and SDK behavior matches documentation.

Usage:
    python tests/sdk_audit_test.py
    python tests/sdk_audit_test.py --verbose
"""

import os
import sys
from typing import List, Dict, Any
from dataclasses import dataclass
import traceback

# Add parent directory to path to import SDK
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from oilpriceapi import OilPriceAPI, AsyncOilPriceAPI
from oilpriceapi.exceptions import (
    OilPriceAPIError,
    AuthenticationError,
    RateLimitError,
    DataNotFoundError,
    ServerError,
)
from oilpriceapi.models import DieselPrice, DieselStation, PriceAlert


@dataclass
class TestResult:
    """Test result container"""
    name: str
    passed: bool
    error: str = None
    details: str = None


class PythonSDKAuditor:
    """Comprehensive Python SDK audit runner"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OILPRICEAPI_KEY') or '94cc54816ff442c372de223e8c33bee7f10a099ed96733d0dd2eeba449f8fb78'
        self.results: List[TestResult] = []
        self.client = None

    def run_all_tests(self):
        """Run all SDK audit tests"""
        print("🧪 Python SDK Audit Test Suite")
        print("=" * 60)
        print(f"API Key: {self.api_key[:20]}...")
        print("=" * 60)
        print("")

        # Test groups
        self.test_basic_initialization()
        self.test_prices_api()
        self.test_diesel_api()
        self.test_alerts_api()
        self.test_error_handling()
        self.test_async_support()

        # Print summary
        self.print_summary()

    def test_basic_initialization(self):
        """Test SDK initialization methods"""
        print("\n📋 Test Group: Basic Initialization")
        print("-" * 60)

        # Test 1: Environment variable initialization
        try:
            client = OilPriceAPI()
            self.client = client
            self.results.append(TestResult(
                name="Initialize with environment variable",
                passed=True,
                details="Client initialized successfully"
            ))
            print("  ✅ PASS: Initialize with environment variable")
        except Exception as e:
            self.results.append(TestResult(
                name="Initialize with environment variable",
                passed=False,
                error=str(e)
            ))
            print(f"  ❌ FAIL: Initialize with environment variable - {e}")

        # Test 2: Direct API key initialization
        try:
            client = OilPriceAPI(api_key=self.api_key)
            self.results.append(TestResult(
                name="Initialize with direct API key",
                passed=True,
                details="Client initialized with API key"
            ))
            print("  ✅ PASS: Initialize with direct API key")
        except Exception as e:
            self.results.append(TestResult(
                name="Initialize with direct API key",
                passed=False,
                error=str(e)
            ))
            print(f"  ❌ FAIL: Initialize with direct API key - {e}")

        # Test 3: Configuration options
        try:
            client = OilPriceAPI(
                api_key=self.api_key,
                timeout=30,
                max_retries=3
            )
            self.results.append(TestResult(
                name="Initialize with configuration",
                passed=True,
                details="Client initialized with config options"
            ))
            print("  ✅ PASS: Initialize with configuration")
        except Exception as e:
            self.results.append(TestResult(
                name="Initialize with configuration",
                passed=False,
                error=str(e)
            ))
            print(f"  ❌ FAIL: Initialize with configuration - {e}")

    def test_prices_api(self):
        """Test prices API methods"""
        print("\n📋 Test Group: Prices API")
        print("-" * 60)

        if not self.client:
            self.client = OilPriceAPI(api_key=self.api_key)

        # Test 1: Get single price
        try:
            price = self.client.prices.get("BRENT_CRUDE_USD")
            assert hasattr(price, 'value'), "Price object missing 'value' attribute"
            assert isinstance(price.value, (int, float)), "Price value is not numeric"
            self.results.append(TestResult(
                name="Get single price (prices.get)",
                passed=True,
                details=f"Brent price: ${price.value:.2f}"
            ))
            print(f"  ✅ PASS: Get single price - Brent: ${price.value:.2f}")
        except Exception as e:
            self.results.append(TestResult(
                name="Get single price (prices.get)",
                passed=False,
                error=str(e)
            ))
            print(f"  ❌ FAIL: Get single price - {e}")

        # Test 2: Get multiple prices
        try:
            prices = self.client.prices.get_multiple([
                "BRENT_CRUDE_USD",
                "WTI_USD",
                "NATURAL_GAS_USD"
            ])
            assert len(prices) > 0, "No prices returned"
            assert all(hasattr(p, 'value') for p in prices), "Price objects missing 'value'"
            self.results.append(TestResult(
                name="Get multiple prices (prices.get_multiple)",
                passed=True,
                details=f"Retrieved {len(prices)} prices"
            ))
            print(f"  ✅ PASS: Get multiple prices - {len(prices)} commodities")
        except Exception as e:
            self.results.append(TestResult(
                name="Get multiple prices (prices.get_multiple)",
                passed=False,
                error=str(e)
            ))
            print(f"  ❌ FAIL: Get multiple prices - {e}")

        # Test 3: Historical data as DataFrame
        try:
            df = self.client.prices.to_dataframe(
                commodity="BRENT_CRUDE_USD",
                start="2024-12-01",
                end="2024-12-15"
            )
            assert df is not None, "DataFrame is None"
            assert len(df) > 0, "DataFrame is empty"
            self.results.append(TestResult(
                name="Get historical data as DataFrame",
                passed=True,
                details=f"DataFrame with {len(df)} rows"
            ))
            print(f"  ✅ PASS: Historical DataFrame - {len(df)} rows")
        except Exception as e:
            self.results.append(TestResult(
                name="Get historical data as DataFrame",
                passed=False,
                error=str(e)
            ))
            print(f"  ❌ FAIL: Historical DataFrame - {e}")

    def test_diesel_api(self):
        """Test diesel API methods (new in v1.3.0)"""
        print("\n📋 Test Group: Diesel API")
        print("-" * 60)

        if not self.client:
            self.client = OilPriceAPI(api_key=self.api_key)

        # Test 1: Get state diesel price
        try:
            ca_price = self.client.diesel.get_price("CA")
            assert hasattr(ca_price, 'price'), "Missing 'price' attribute"
            assert hasattr(ca_price, 'source'), "Missing 'source' attribute"
            self.results.append(TestResult(
                name="Get state diesel price",
                passed=True,
                details=f"CA diesel: ${ca_price.price:.2f}"
            ))
            print(f"  ✅ PASS: State diesel price - CA: ${ca_price.price:.2f}")
        except Exception as e:
            self.results.append(TestResult(
                name="Get state diesel price",
                passed=False,
                error=str(e)
            ))
            print(f"  ❌ FAIL: State diesel price - {e}")

        # Test 2: Get diesel stations (may require paid tier)
        try:
            result = self.client.diesel.get_stations(
                lat=37.7749,   # San Francisco
                lng=-122.4194,
                radius=8047    # 5 miles
            )
            self.results.append(TestResult(
                name="Get diesel stations (paid tier)",
                passed=True,
                details=f"Found {len(result.stations) if hasattr(result, 'stations') else 0} stations"
            ))
            print(f"  ✅ PASS: Get diesel stations")
        except Exception as e:
            # This may fail on free tier, which is expected
            if "upgrade" in str(e).lower() or "tier" in str(e).lower():
                self.results.append(TestResult(
                    name="Get diesel stations (paid tier)",
                    passed=True,  # Expected failure on free tier
                    details="Expected failure on free tier"
                ))
                print(f"  ⏭️  SKIP: Get diesel stations - Requires paid tier (expected)")
            else:
                self.results.append(TestResult(
                    name="Get diesel stations (paid tier)",
                    passed=False,
                    error=str(e)
                ))
                print(f"  ❌ FAIL: Get diesel stations - {e}")

        # Test 3: Diesel prices as DataFrame
        try:
            df = self.client.diesel.to_dataframe(states=["CA", "TX"])
            assert df is not None, "DataFrame is None"
            self.results.append(TestResult(
                name="Diesel prices as DataFrame",
                passed=True,
                details=f"DataFrame with {len(df)} rows"
            ))
            print(f"  ✅ PASS: Diesel DataFrame - {len(df)} rows")
        except Exception as e:
            self.results.append(TestResult(
                name="Diesel prices as DataFrame",
                passed=False,
                error=str(e)
            ))
            print(f"  ❌ FAIL: Diesel DataFrame - {e}")

    def test_alerts_api(self):
        """Test alerts API methods (new in v1.4.0)"""
        print("\n📋 Test Group: Alerts API")
        print("-" * 60)

        if not self.client:
            self.client = OilPriceAPI(api_key=self.api_key)

        alert_id = None

        # Test 1: Create alert
        try:
            alert = self.client.alerts.create(
                name="SDK Test Alert",
                commodity_code="BRENT_CRUDE_USD",
                condition_operator="greater_than",
                condition_value=85.00,
                enabled=False  # Disabled so it doesn't trigger
            )
            assert hasattr(alert, 'id'), "Alert missing 'id' attribute"
            alert_id = alert.id
            self.results.append(TestResult(
                name="Create price alert",
                passed=True,
                details=f"Alert ID: {alert.id}"
            ))
            print(f"  ✅ PASS: Create alert - ID: {alert.id[:8]}...")
        except Exception as e:
            self.results.append(TestResult(
                name="Create price alert",
                passed=False,
                error=str(e)
            ))
            print(f"  ❌ FAIL: Create alert - {e}")

        # Test 2: List alerts
        try:
            alerts = self.client.alerts.list()
            assert isinstance(alerts, list), "Alerts list is not a list"
            self.results.append(TestResult(
                name="List alerts",
                passed=True,
                details=f"Found {len(alerts)} alerts"
            ))
            print(f"  ✅ PASS: List alerts - {len(alerts)} total")
        except Exception as e:
            self.results.append(TestResult(
                name="List alerts",
                passed=False,
                error=str(e)
            ))
            print(f"  ❌ FAIL: List alerts - {e}")

        # Test 3: Update alert (if created)
        if alert_id:
            try:
                updated = self.client.alerts.update(
                    alert_id,
                    condition_value=90.00
                )
                self.results.append(TestResult(
                    name="Update alert",
                    passed=True,
                    details="Alert updated successfully"
                ))
                print(f"  ✅ PASS: Update alert")
            except Exception as e:
                self.results.append(TestResult(
                    name="Update alert",
                    passed=False,
                    error=str(e)
                ))
                print(f"  ❌ FAIL: Update alert - {e}")

        # Test 4: Delete alert (cleanup)
        if alert_id:
            try:
                self.client.alerts.delete(alert_id)
                self.results.append(TestResult(
                    name="Delete alert",
                    passed=True,
                    details="Alert deleted successfully"
                ))
                print(f"  ✅ PASS: Delete alert")
            except Exception as e:
                self.results.append(TestResult(
                    name="Delete alert",
                    passed=False,
                    error=str(e)
                ))
                print(f"  ❌ FAIL: Delete alert - {e}")

    def test_error_handling(self):
        """Test error handling"""
        print("\n📋 Test Group: Error Handling")
        print("-" * 60)

        if not self.client:
            self.client = OilPriceAPI(api_key=self.api_key)

        # Test 1: Invalid commodity code
        try:
            price = self.client.prices.get("INVALID_CODE_XYZ")
            # Should raise DataNotFoundError
            self.results.append(TestResult(
                name="Invalid commodity error handling",
                passed=False,
                error="Expected DataNotFoundError but got success"
            ))
            print(f"  ❌ FAIL: Invalid commodity - Should have raised error")
        except DataNotFoundError as e:
            self.results.append(TestResult(
                name="Invalid commodity error handling",
                passed=True,
                details="DataNotFoundError raised correctly"
            ))
            print(f"  ✅ PASS: Invalid commodity raises DataNotFoundError")
        except Exception as e:
            self.results.append(TestResult(
                name="Invalid commodity error handling",
                passed=False,
                error=f"Wrong exception type: {type(e).__name__}"
            ))
            print(f"  ❌ FAIL: Invalid commodity - Wrong error type: {type(e).__name__}")

    def test_async_support(self):
        """Test async support"""
        print("\n📋 Test Group: Async Support")
        print("-" * 60)

        # Test 1: Async client initialization
        try:
            import asyncio

            async def test_async():
                async with AsyncOilPriceAPI(api_key=self.api_key) as client:
                    price = await client.prices.get("BRENT_CRUDE_USD")
                    return price

            price = asyncio.run(test_async())
            assert hasattr(price, 'value'), "Price missing 'value' attribute"
            self.results.append(TestResult(
                name="Async client support",
                passed=True,
                details=f"Async price: ${price.value:.2f}"
            ))
            print(f"  ✅ PASS: Async client - Price: ${price.value:.2f}")
        except Exception as e:
            self.results.append(TestResult(
                name="Async client support",
                passed=False,
                error=str(e)
            ))
            print(f"  ❌ FAIL: Async client - {e}")

    def print_summary(self):
        """Print test summary"""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {len(self.results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print("")

        if failed > 0:
            print("⚠️  FAILED TESTS:")
            print("")
            for result in self.results:
                if not result.passed:
                    print(f"  • {result.name}")
                    if result.error:
                        print(f"    Error: {result.error}")
            print("")
            print("👉 Next step: Create GitHub issues for failures")
        else:
            print("✅ ALL TESTS PASSED")
            print("Python SDK matches documentation!")

        print("=" * 60)

        # Return exit code
        return 0 if failed == 0 else 1


def main():
    """Main entry point"""
    auditor = PythonSDKAuditor()
    exit_code = auditor.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
