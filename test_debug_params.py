#!/usr/bin/env python3
"""Debug script to see what parameters SDK sends to API."""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from oilpriceapi import OilPriceAPI
from dotenv import load_dotenv

load_dotenv()

# Monkey patch the request method to print parameters
original_request = OilPriceAPI.request

def debug_request(self, method, path, params=None, **kwargs):
    print(f"\n🔍 DEBUG: API Request")
    print(f"   Method: {method}")
    print(f"   Path: {path}")
    print(f"   Params: {params}")
    print(f"   Kwargs: {kwargs}")
    print()
    return original_request(self, method, path, params, **kwargs)

OilPriceAPI.request = debug_request

# Now make the request
client = OilPriceAPI(api_key=os.getenv('OILPRICEAPI_KEY'))

print("Making historical request with custom date range...")
response = client.historical.get(
    commodity="WTI_USD",
    start_date="2024-01-01",
    end_date="2024-01-10",
    interval="daily"
)

print(f"\n✓ Got {len(response.data)} records")
if len(response.data) > 0:
    print(f"  First: {response.data[0].date}")
    print(f"  Last: {response.data[-1].date}")

client.close()
