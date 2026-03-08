#!/usr/bin/env python3
"""
Test script to reproduce Idan's bug report.

Bug: SDK returns wrong commodity and wrong date range
Reporter: idan@comity.ai
Date: December 17, 2025
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from oilpriceapi import OilPriceAPI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    api_key = os.getenv('OILPRICEAPI_KEY')
    if not api_key:
        print("❌ ERROR: OILPRICEAPI_KEY not found in environment")
        print("Create a .env file with: OILPRICEAPI_KEY=your_key_here")
        sys.exit(1)

    client = OilPriceAPI(api_key=api_key)

    print("=" * 70)
    print("IDAN BUG REPRODUCTION TEST")
    print("=" * 70)

    print("\n📋 Test 1: Invalid Commodity Code")
    print("-" * 70)
    print("Query: commodity='INVALID_NONSENSE_XYZ'")
    print("       start_date='2024-01-01'")
    print("       end_date='2024-01-10'")
    print()

    try:
        response = client.historical.get(
            commodity="INVALID_NONSENSE_XYZ",
            start_date="2024-01-01",
            end_date="2024-01-10",
            interval="daily"
        )

        print(f"✓ Request succeeded (got {len(response.data)} records)")

        if len(response.data) == 0:
            print("✅ CORRECT: No data returned for invalid commodity")
        else:
            print(f"❌ BUG CONFIRMED: Returned {len(response.data)} records despite invalid commodity!")

            first_price = response.data[0]
            print(f"\nFirst record:")
            print(f"  Commodity: {first_price.commodity}")
            print(f"  Date: {first_price.date}")
            print(f"  Value: ${first_price.value:.2f}")

            if first_price.commodity == "BRENT_CRUDE_USD":
                print("\n❌ BUG: Default commodity BRENT_CRUDE_USD returned instead of error!")

            if first_price.date.year == 2025:
                print(f"❌ BUG: Returned {first_price.date.year} data when 2024 was requested!")

    except Exception as e:
        print(f"✅ CORRECT: Request failed with error (as expected): {e}")

    print("\n" + "=" * 70)
    print("📋 Test 2: Valid Commodity, Specific Date Range")
    print("-" * 70)
    print("Query: commodity='WTI_USD'")
    print("       start_date='2024-01-01'")
    print("       end_date='2024-01-10'")
    print()

    try:
        response2 = client.historical.get(
            commodity="WTI_USD",
            start_date="2024-01-01",
            end_date="2024-01-10",
            interval="daily"
        )

        print(f"✓ Request succeeded (got {len(response2.data)} records)")

        if len(response2.data) == 0:
            print("⚠️  WARNING: No data returned (might be expected if no historical data exists)")
        else:
            first_price = response2.data[0]
            last_price = response2.data[-1]

            print(f"\nDate range check:")
            print(f"  Requested: 2024-01-01 to 2024-01-10")
            print(f"  First record: {first_price.date}")
            print(f"  Last record: {last_price.date}")

            # Check if all dates are in correct range
            start_date = datetime(2024, 1, 1).date()
            end_date = datetime(2024, 1, 10).date()

            out_of_range = []
            for p in response2.data:
                p_date = p.date.date() if hasattr(p.date, 'date') else p.date
                if not (start_date <= p_date <= end_date):
                    out_of_range.append(p)

            if not out_of_range:
                print("\n✅ CORRECT: All dates within requested range")
            else:
                print(f"\n❌ BUG: {len(out_of_range)} records outside requested range!")
                print("\nOut of range examples:")
                for p in out_of_range[:5]:
                    print(f"  - {p.date} (value: ${p.value:.2f})")

            # Check commodity
            wrong_commodity = [p for p in response2.data if p.commodity != "WTI_USD"]
            if not wrong_commodity:
                print("✅ CORRECT: All records are WTI_USD")
            else:
                print(f"❌ BUG: Found {len(wrong_commodity)} records with wrong commodity!")
                commodities = set(p.commodity for p in wrong_commodity)
                print(f"  Wrong commodities: {', '.join(commodities)}")

    except Exception as e:
        print(f"❌ ERROR: Request failed unexpectedly: {e}")

    print("\n" + "=" * 70)
    print("📋 Test 3: Idan's Exact Query")
    print("-" * 70)
    print("Query: commodity='oijfoijofwijewef' (nonsense string)")
    print("       start_date='2024-01-01'")
    print("       end_date='2024-01-10'")
    print()

    try:
        response3 = client.historical.get(
            commodity="oijfoijofwijewef",
            start_date="2024-01-01",
            end_date="2024-01-10"
        )

        if len(response3.data) == 0:
            print("✅ CORRECT: No data returned for nonsense commodity")
        else:
            print(f"❌ BUG CONFIRMED: Returned {len(response3.data)} records!")
            print("\nThis is the exact bug Idan reported:")
            print("  - Invalid commodity code should return error or empty result")
            print("  - Instead, returned data (probably BRENT_CRUDE_USD with wrong dates)")

            if len(response3.data) > 0:
                first = response3.data[0]
                print(f"\n  Returned commodity: {first.commodity}")
                print(f"  Returned date: {first.date}")
                print(f"  Returned value: ${first.value:.2f}")

    except Exception as e:
        print(f"✅ CORRECT: Request failed with error: {type(e).__name__}: {e}")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

    client.close()


if __name__ == "__main__":
    main()
