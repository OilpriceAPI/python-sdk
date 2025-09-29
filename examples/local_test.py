#!/usr/bin/env python3
"""
OilPriceAPI SDK - Local Testing Example

This script tests the SDK against your API instance.

Required environment variables:
- OILPRICEAPI_KEY: Your API key
- OILPRICEAPI_BASE_URL: API base URL (optional, defaults to production)
"""

import os
import asyncio
from oilpriceapi import OilPriceAPI, AsyncOilPriceAPI

# Load from environment
API_KEY = os.getenv("OILPRICEAPI_KEY")
BASE_URL = os.getenv("OILPRICEAPI_BASE_URL", "https://api.oilpriceapi.com")

if not API_KEY:
    raise ValueError("OILPRICEAPI_KEY environment variable is required")


def test_basic_operations():
    """Test basic SDK operations."""
    print("\n" + "=" * 60)
    print("🧪 Testing Basic Operations")
    print("=" * 60)
    
    # Initialize client with local settings
    client = OilPriceAPI(api_key=API_KEY, base_url=BASE_URL)
    
    # Test single price fetch
    print("\n1️⃣  Fetching single price (BRENT_CRUDE_USD)...")
    try:
        brent = client.prices.get("BRENT_CRUDE_USD")
        print(f"   ✅ Brent Crude: ${brent.value:.2f} {brent.currency}")
        print(f"   Last Updated: {brent.timestamp}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test multiple prices
    print("\n2️⃣  Fetching multiple commodity prices...")
    commodities = ["BRENT_CRUDE_USD", "GOLD_USD", "GASOLINE_RBOB_USD"]
    try:
        prices = client.prices.get_multiple(commodities)
        for price in prices:
            print(f"   ✅ {price.commodity}: ${price.value:.2f}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test historical data
    print("\n3️⃣  Fetching historical data...")
    try:
        history = client.historical.get(
            commodity="BRENT_CRUDE_USD",
            start_date="2024-01-01",
            end_date="2024-01-07",
            per_page=5
        )
        print(f"   ✅ Retrieved {len(history.data)} historical records")
        if history.data:
            for record in history.data[:3]:
                print(f"      {record.date}: ${record.value:.2f}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    client.close()


async def test_async_operations():
    """Test async SDK operations."""
    print("\n" + "=" * 60)
    print("⚡ Testing Async Operations")
    print("=" * 60)
    
    async with AsyncOilPriceAPI(api_key=API_KEY, base_url=BASE_URL) as client:
        print("\n1️⃣  Fetching prices concurrently...")
        
        commodities = ["BRENT_CRUDE_USD", "GOLD_USD", "COAL_USD"]
        
        try:
            # Fetch all prices in parallel
            tasks = [client.prices.get(code) for code in commodities]
            prices = await asyncio.gather(*tasks, return_exceptions=True)
            
            for commodity, result in zip(commodities, prices):
                if isinstance(result, Exception):
                    print(f"   ❌ {commodity}: {result}")
                else:
                    print(f"   ✅ {result.commodity}: ${result.value:.2f}")
        except Exception as e:
            print(f"   ❌ Error: {e}")


def test_error_handling():
    """Test error handling."""
    print("\n" + "=" * 60)
    print("⚠️  Testing Error Handling")
    print("=" * 60)
    
    client = OilPriceAPI(api_key=API_KEY, base_url=BASE_URL)
    
    # Test invalid commodity
    print("\n1️⃣  Testing invalid commodity code...")
    try:
        price = client.prices.get("INVALID_CODE_XYZ")
        print(f"   ❌ Should have raised an error")
    except Exception as e:
        print(f"   ✅ Error caught: {type(e).__name__}")
    
    # Test invalid API key
    print("\n2️⃣  Testing invalid API key...")
    bad_client = OilPriceAPI(api_key="invalid_key_123", base_url=BASE_URL)
    try:
        price = bad_client.prices.get("BRENT_CRUDE_USD")
        print(f"   ❌ Should have raised an error")
    except Exception as e:
        print(f"   ✅ Error caught: {type(e).__name__}")
    
    client.close()
    bad_client.close()


def test_commodity_variety():
    """Test various commodity types."""
    print("\n" + "=" * 60)
    print("🌐 Testing Various Commodity Types")
    print("=" * 60)
    
    client = OilPriceAPI(api_key=API_KEY, base_url=BASE_URL)
    
    # Different commodity categories
    test_commodities = {
        "Energy": ["BRENT_CRUDE_USD", "NATURAL_GAS_USD", "HEATING_OIL_USD"],
        "Precious Metals": ["GOLD_USD", "SILVER_USD"],
        "Currencies": ["EUR_USD", "GBP_USD"],
        "Marine Fuels": ["HFO_380_USD", "MGO_05S_USD"],
    }
    
    for category, codes in test_commodities.items():
        print(f"\n{category}:")
        for code in codes:
            try:
                price = client.prices.get(code)
                print(f"   ✅ {code}: ${price.value:.2f}")
            except Exception as e:
                print(f"   ❌ {code}: Not available")
    
    client.close()


def main():
    """Run all tests."""
    print("\n" + "#" * 60)
    print("#" + " " * 12 + "OilPriceAPI SDK - Local Testing" + " " * 14 + "#")
    print("#" * 60)
    print(f"\n🎯 Base URL: {BASE_URL}")
    print(f"🔑 API Key: {API_KEY[:10]}...{API_KEY[-10:]}")
    
    try:
        # Run synchronous tests
        test_basic_operations()
        test_error_handling()
        test_commodity_variety()
        
        # Run async tests
        asyncio.run(test_async_operations())
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
