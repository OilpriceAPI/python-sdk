#!/usr/bin/env python3
"""
Live test of OilPriceAPI SDK

Required environment variables:
- OILPRICEAPI_KEY: Your API key
- OILPRICEAPI_BASE_URL: API base URL (default: https://api.oilpriceapi.com)
"""

import os
import asyncio
from oilpriceapi import OilPriceAPI, AsyncOilPriceAPI

# Load from environment variables
API_KEY = os.getenv("OILPRICEAPI_KEY")
BASE_URL = os.getenv("OILPRICEAPI_BASE_URL", "https://api.oilpriceapi.com")

if not API_KEY:
    raise ValueError("OILPRICEAPI_KEY environment variable is required")

def test_sync_client():
    """Test synchronous client."""
    print("\n=== Testing Synchronous Client ===")
    
    # Initialize client
    client = OilPriceAPI(api_key=API_KEY, base_url=BASE_URL)
    
    try:
        # Test getting single price
        print("\n1. Getting BRENT_CRUDE_USD price...")
        price = client.prices.get("BRENT_CRUDE_USD")
        print(f"   Brent Crude: ${price.value:.2f} {price.currency}")
        print(f"   Timestamp: {price.timestamp}")
        
        # Test getting multiple prices
        print("\n2. Getting multiple prices...")
        commodities = ["BRENT_CRUDE_USD", "WTI_USD", "NATURAL_GAS_USD"]
        prices = client.prices.get_multiple(commodities)
        for p in prices:
            print(f"   {p.commodity}: ${p.value:.2f}")
        
        # Test historical data
        print("\n3. Getting historical data...")
        history = client.historical.get(
            commodity="BRENT_CRUDE_USD",
            start_date="2024-01-01",
            end_date="2024-01-07",
            per_page=5
        )
        print(f"   Retrieved {len(history.data)} historical records")
        for h in history.data[:3]:
            print(f"   {h.date}: ${h.value:.2f}")
        
        print("\n✅ Synchronous client tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


async def test_async_client():
    """Test asynchronous client."""
    print("\n=== Testing Asynchronous Client ===")
    
    async with AsyncOilPriceAPI(api_key=API_KEY, base_url=BASE_URL) as client:
        try:
            # Test concurrent price fetching
            print("\n1. Getting prices concurrently...")
            prices = await asyncio.gather(
                client.prices.get("BRENT_CRUDE_USD"),
                client.prices.get("WTI_USD"),
                client.prices.get("NATURAL_GAS_USD"),
            )
            
            for price in prices:
                print(f"   {price.commodity}: ${price.value:.2f}")
            
            # Test historical data
            print("\n2. Getting historical data async...")
            history = await client.historical.get(
                commodity="WTI_USD",
                start_date="2024-01-01",
                end_date="2024-01-07",
                per_page=5
            )
            print(f"   Retrieved {len(history.data)} historical records")
            
            print("\n✅ Asynchronous client tests passed!")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


def test_error_handling():
    """Test error handling."""
    print("\n=== Testing Error Handling ===")
    
    client = OilPriceAPI(api_key=API_KEY, base_url=BASE_URL)
    
    # Test invalid commodity
    print("\n1. Testing invalid commodity...")
    try:
        price = client.prices.get("INVALID_COMMODITY")
        print("   ❌ Should have raised an error")
    except Exception as e:
        print(f"   ✅ Caught expected error: {type(e).__name__}: {e}")
    
    # Test invalid API key
    print("\n2. Testing invalid API key...")
    bad_client = OilPriceAPI(api_key="invalid_key", base_url=BASE_URL)
    try:
        price = bad_client.prices.get("BRENT_CRUDE_USD")
        print("   ❌ Should have raised an error")
    except Exception as e:
        print(f"   ✅ Caught expected error: {type(e).__name__}: {e}")
    
    client.close()
    bad_client.close()


def test_convenience_function():
    """Test convenience function."""
    print("\n=== Testing Convenience Function ===")
    
    import os
    os.environ["OILPRICEAPI_KEY"] = API_KEY
    
    from oilpriceapi import get_current_price
    
    try:
        price = get_current_price("BRENT_CRUDE_USD")
        print(f"   Brent Crude: ${price:.2f}")
        print("   ✅ Convenience function works!")
    except Exception as e:
        print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    print("🧪 OilPriceAPI Python SDK Live Test")
    print("=====================================")
    
    # Test sync client
    test_sync_client()
    
    # Test async client
    asyncio.run(test_async_client())
    
    # Test error handling
    test_error_handling()
    
    # Test convenience function
    test_convenience_function()
    
    print("\n✅ All tests completed!")
