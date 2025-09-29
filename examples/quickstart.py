#!/usr/bin/env python3
"""
OilPriceAPI SDK - Quick Start Example

This script demonstrates basic usage of the OilPriceAPI Python SDK.
"""

import os
import asyncio
from datetime import datetime, timedelta
from oilpriceapi import OilPriceAPI, AsyncOilPriceAPI

# Set your API key as an environment variable or replace this string
# export OILPRICEAPI_KEY="your_api_key_here"
API_KEY = os.environ.get("OILPRICEAPI_KEY", "your_api_key_here")


def basic_usage():
    """Demonstrate basic price fetching."""
    print("\n" + "=" * 60)
    print("1. BASIC USAGE - Getting Current Prices")
    print("=" * 60)
    
    # Initialize the client
    client = OilPriceAPI(api_key=API_KEY)
    
    # Get a single commodity price
    print("\n📊 Fetching Brent Crude Oil price...")
    brent = client.prices.get("BRENT_CRUDE_USD")
    print(f"Brent Crude: ${brent.value:.2f} {brent.currency}")
    print(f"Last Updated: {brent.timestamp}")
    
    # Get multiple commodity prices
    print("\n📊 Fetching multiple commodity prices...")
    commodities = ["BRENT_CRUDE_USD", "WTI_USD", "NATURAL_GAS_USD", "GOLD_USD"]
    prices = client.prices.get_multiple(commodities)
    
    for price in prices:
        print(f"  {price.commodity}: ${price.value:.2f} {price.currency}")
    
    client.close()


def historical_data():
    """Demonstrate historical data retrieval."""
    print("\n" + "=" * 60)
    print("2. HISTORICAL DATA - Past Price Analysis")
    print("=" * 60)
    
    client = OilPriceAPI(api_key=API_KEY)
    
    # Get historical data for the past week
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    print(f"\n📈 Fetching Brent Crude prices from {start_date.date()} to {end_date.date()}...")
    
    history = client.historical.get(
        commodity="BRENT_CRUDE_USD",
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        interval="daily",
        per_page=100
    )
    
    print(f"Retrieved {len(history.data)} data points")
    
    # Calculate simple statistics
    if history.data:
        prices = [p.value for p in history.data]
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        
        print(f"\n📊 Statistics:")
        print(f"  Average: ${avg_price:.2f}")
        print(f"  Minimum: ${min_price:.2f}")
        print(f"  Maximum: ${max_price:.2f}")
        print(f"  Volatility: ${max_price - min_price:.2f}")
    
    client.close()


def error_handling():
    """Demonstrate proper error handling."""
    print("\n" + "=" * 60)
    print("3. ERROR HANDLING - Graceful Error Management")
    print("=" * 60)
    
    client = OilPriceAPI(api_key=API_KEY)
    
    # Try to fetch an invalid commodity
    print("\n⚠️  Attempting to fetch invalid commodity...")
    try:
        price = client.prices.get("INVALID_COMMODITY_CODE")
    except Exception as e:
        print(f"✅ Error handled gracefully: {type(e).__name__}: {e}")
    
    # Handle rate limiting (simulated)
    print("\n⚠️  Demonstrating rate limit handling...")
    print("The SDK automatically retries with exponential backoff")
    
    client.close()


async def async_example():
    """Demonstrate async client for high-performance operations."""
    print("\n" + "=" * 60)
    print("4. ASYNC CLIENT - High Performance Concurrent Requests")
    print("=" * 60)
    
    async with AsyncOilPriceAPI(api_key=API_KEY) as client:
        # Fetch multiple prices concurrently
        commodities = [
            "BRENT_CRUDE_USD",
            "WTI_USD",
            "NATURAL_GAS_USD",
            "HEATING_OIL_USD",
            "GASOLINE_RBOB_USD",
            "GOLD_USD",
        ]
        
        print(f"\n⚡ Fetching {len(commodities)} prices concurrently...")
        import time
        start_time = time.time()
        
        # Fetch all prices in parallel
        tasks = [client.prices.get(code) for code in commodities]
        prices = await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed = time.time() - start_time
        
        # Display results
        for commodity, result in zip(commodities, prices):
            if isinstance(result, Exception):
                print(f"  {commodity}: Error - {result}")
            else:
                print(f"  {result.commodity}: ${result.value:.2f}")
        
        print(f"\n✅ Fetched all prices in {elapsed:.2f} seconds")


def pandas_integration():
    """Demonstrate pandas DataFrame integration."""
    print("\n" + "=" * 60)
    print("5. PANDAS INTEGRATION - Data Analysis Ready")
    print("=" * 60)
    
    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        print("\n⚠️  Pandas not installed. Install with: pip install pandas")
        return
    
    client = OilPriceAPI(api_key=API_KEY)
    
    print("\n🐼 Converting price data to DataFrame...")
    
    # Get current prices as DataFrame
    df = client.prices.to_dataframe(
        commodities=["BRENT_CRUDE_USD", "WTI_USD", "NATURAL_GAS_USD"]
    )
    
    if not df.empty:
        print("\nDataFrame created:")
        print(df[['commodity', 'value', 'currency', 'timestamp']].to_string())
        
        # Calculate spread between Brent and WTI
        brent_price = df[df['commodity'] == 'BRENT_CRUDE_USD']['value'].iloc[0]
        wti_price = df[df['commodity'] == 'WTI_USD']['value'].iloc[0]
        spread = brent_price - wti_price
        
        print(f"\n📊 Brent-WTI Spread: ${spread:.2f}")
    
    client.close()


def main():
    """Run all examples."""
    print("\n" + "#" * 60)
    print("#" + " " * 58 + "#")
    print("#" + " " * 15 + "OilPriceAPI Python SDK Examples" + " " * 11 + "#")
    print("#" + " " * 58 + "#") 
    print("#" * 60)
    
    # Check for API key
    if API_KEY == "your_api_key_here":
        print("\n⚠️  Please set your API key:")
        print("    export OILPRICEAPI_KEY='your_actual_api_key'")
        print("    or edit this file and replace 'your_api_key_here'")
        return
    
    try:
        # Run examples
        basic_usage()
        historical_data()
        error_handling()
        
        # Run async example
        asyncio.run(async_example())
        
        # Pandas integration
        pandas_integration()
        
        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
