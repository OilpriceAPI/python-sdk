# Python SDK Website & Documentation Audit

**Date:** 2025-11-26
**Status:** ⚠️ Needs Updates

---

## Summary

**Good news:** Python SDK has dedicated marketing pages and documentation.

**Bad news:** Website code examples are outdated and show incorrect SDK usage.

---

## What Exists

### 1. Website Marketing Pages

**Page 1: `/python-oil-api`**
- URL: https://www.oilpriceapi.com/python-oil-api
- File: `/home/kwaldman/code/website-clean/app/python-oil-api/page.tsx`
- Hero with code example
- Installation instructions
- Feature cards
- CTAs to signup, PyPI, docs

**Page 2: `/developers/python`**
- URL: https://www.oilpriceapi.com/developers/python
- File: `/home/kwaldman/code/website-clean/app/developers/python/page.tsx`
- Integration guide
- Code examples
- Best practices

### 2. Documentation Site

**Docs URL:** https://docs.oilpriceapi.com/sdk/python
- Found in: `/home/kwaldman/code/oilpriceapi-docs/`
- Build artifacts show Python SDK pages exist
- VuePress site

### 3. SDK README

**File:** `/home/kwaldman/code/sdks/python/README.md`
- ✅ Comprehensive
- ✅ Up-to-date
- ✅ Shows correct API usage
- ✅ Includes async examples

---

## Problems Found

### 🔴 Critical: Incorrect Code Examples on Website

**Problem:** Website shows code that DOESN'T match actual SDK

**Page:** `/python-oil-api/page.tsx` (lines 53-66)

**Current (WRONG) code:**
```python
from oilpriceapi import OilPriceAPI

client = OilPriceAPI(api_key="your_free_key")
prices = client.get_latest_prices()  # ❌ This method doesn't exist!

print(f"WTI: ${prices['WTI_USD']}/barrel")
print(f"Brent: ${prices['BRENT_USD']}/barrel")
```

**Correct code should be:**
```python
from oilpriceapi import OilPriceAPI

client = OilPriceAPI(api_key="your_free_key")
wti = client.prices.get("WTI_USD")
brent = client.prices.get("BRENT_CRUDE_USD")

print(f"WTI: ${wti.value}/barrel")
print(f"Brent: ${brent.value}/barrel")
```

**Impact:**
- Users copy/paste code from website → **code fails**
- Bad first impression
- Support burden (users ask why examples don't work)

---

### 🟡 Medium: Missing Async Examples

**Problem:** Neither website page mentions `AsyncOilPriceAPI`

**What's missing:**
```python
import asyncio
from oilpriceapi import AsyncOilPriceAPI

async def get_prices():
    async with AsyncOilPriceAPI() as client:
        prices = await asyncio.gather(
            client.prices.get("BRENT_CRUDE_USD"),
            client.prices.get("WTI_USD"),
            client.prices.get("NATURAL_GAS_USD")
        )
        for price in prices:
            print(f"{price.commodity}: ${price.value}")

asyncio.run(get_prices())
```

**Impact:**
- Users don't know async support exists
- Missing key selling point from Reddit post
- Async is major feature we're promoting on Reddit

---

### 🟡 Medium: Outdated Developer Guide

**Problem:** `/developers/python` page shows manual `requests` library code

**Page:** `/developers/python/page.tsx` (lines 23-99)

**Current code:**
```python
import requests

class OilPriceAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        # ... manual requests implementation
```

**Should be:**
- Using actual `oilpriceapi` package
- Not showing manual requests implementation
- That's what the SDK is for!

---

## Recommended Fixes

### Priority 1: Fix `/python-oil-api` Code Example

**File:** `/home/kwaldman/code/website-clean/app/python-oil-api/page.tsx`

**Change lines 53-66 from:**
```typescript
<code>{`pip install oilpriceapi

from oilpriceapi import OilPriceAPI

client = OilPriceAPI(api_key="your_free_key")
prices = client.get_latest_prices()

print(f"WTI: $\{prices['WTI_USD']\}/barrel")
print(f"Brent: $\{prices['BRENT_USD']\}/barrel")

# Output:
# WTI: $63.53/barrel
# Brent: $67.91/barrel`}</code>
```

**To:**
```typescript
<code>{`pip install oilpriceapi

from oilpriceapi import OilPriceAPI

client = OilPriceAPI(api_key="your_free_key")
wti = client.prices.get("WTI_USD")
brent = client.prices.get("BRENT_CRUDE_USD")

print(f"WTI: $\{wti.value\}/barrel")
print(f"Brent: $\{brent.value\}/barrel")

# Output:
# WTI: $71.23/barrel
# Brent: $74.89/barrel`}</code>
```

---

### Priority 2: Add Async Section to `/python-oil-api`

**Add after the basic example (around line 89):**

```tsx
{/* Async Example Section */}
<section className="py-20 bg-slate-900">
  <div className="container mx-auto px-4">
    <div className="max-w-4xl mx-auto">
      <h2 className="text-3xl font-bold mb-8 text-white">
        Async Support for High-Performance Apps
      </h2>

      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm text-gray-400">Concurrent Requests</span>
          <span className="text-xs bg-blue-600/20 text-blue-400 px-2 py-1 rounded">
            Python 3.7+
          </span>
        </div>
        <pre className="text-green-400 overflow-x-auto">
          <code>{`import asyncio
from oilpriceapi import AsyncOilPriceAPI

async def get_prices():
    async with AsyncOilPriceAPI() as client:
        # Fetch multiple commodities concurrently
        prices = await asyncio.gather(
            client.prices.get("BRENT_CRUDE_USD"),
            client.prices.get("WTI_USD"),
            client.prices.get("NATURAL_GAS_USD")
        )
        for price in prices:
            print(f"\{price.commodity\}: $\{price.value\}")

asyncio.run(get_prices())

# Output:
# BRENT_CRUDE_USD: $74.89
# WTI_USD: $71.23
# NATURAL_GAS_USD: $2.89`}</code>
        </pre>
      </div>

      <p className="text-gray-300 mt-6">
        Async support with connection pooling (max 100 concurrent, 20 keepalive).
        Perfect for data pipelines and trading systems.
      </p>
    </div>
  </div>
</section>
```

---

### Priority 3: Replace Manual Implementation on `/developers/python`

**File:** `/home/kwaldman/code/website-clean/app/developers/python/page.tsx`

**Replace the entire `pythonExample` const (lines 23-99) with:**

```typescript
const pythonExample = `# Install the SDK
pip install oilpriceapi

# Basic usage
from oilpriceapi import OilPriceAPI

# Initialize client (uses OILPRICEAPI_KEY env var by default)
client = OilPriceAPI()

# Get latest Brent Crude price
brent = client.prices.get("BRENT_CRUDE_USD")
print(f"Brent Crude: $\{brent.value:.2f\}")
# Output: Brent Crude: $74.89

# Get multiple prices
prices = client.prices.get_multiple([
    "BRENT_CRUDE_USD",
    "WTI_USD",
    "NATURAL_GAS_USD"
])
for price in prices:
    print(f"\{price.commodity\}: $\{price.value:.2f\}")

# Historical data
historical = client.prices.get_historical(
    "BRENT_CRUDE_USD",
    start_date="2024-01-01",
    end_date="2024-12-31"
)
print(f"Found \{len(historical)\} historical prices")

# Async support for concurrent requests
import asyncio
from oilpriceapi import AsyncOilPriceAPI

async def get_prices_async():
    async with AsyncOilPriceAPI() as client:
        prices = await asyncio.gather(
            client.prices.get("BRENT_CRUDE_USD"),
            client.prices.get("WTI_USD")
        )
        return prices

# Run async code
prices = asyncio.run(get_prices_async())`;
```

---

## Deployment Plan

### Step 1: Test Code Examples Locally

```bash
cd /home/kwaldman/code/sdks/python

# Test sync example
python3 << 'EOF'
from oilpriceapi import OilPriceAPI
client = OilPriceAPI(api_key="3839c085...")
wti = client.prices.get("WTI_USD")
brent = client.prices.get("BRENT_CRUDE_USD")
print(f"WTI: ${wti.value}/barrel")
print(f"Brent: ${brent.value}/barrel")
EOF

# Test async example
python3 << 'EOF'
import asyncio
from oilpriceapi import AsyncOilPriceAPI

async def test():
    async with AsyncOilPriceAPI(api_key="3839c085...") as client:
        prices = await asyncio.gather(
            client.prices.get("BRENT_CRUDE_USD"),
            client.prices.get("WTI_USD")
        )
        for price in prices:
            print(f"{price.commodity}: ${price.value}")

asyncio.run(test())
EOF
```

### Step 2: Update Website

```bash
cd /home/kwaldman/code/website-clean

# 1. Edit /app/python-oil-api/page.tsx (fix code example)
# 2. Edit /app/developers/python/page.tsx (replace manual code)
# 3. Test locally: npm run dev
# 4. Verify examples work
# 5. Deploy: doctl apps create-deployment 4cf05d8d-32ae-4cea-9e3b-2993b41bd11b
```

### Step 3: Update Documentation Site

```bash
cd /home/kwaldman/code/oilpriceapi-docs

# Find and update Python SDK docs
# Verify all examples match actual SDK API
# Deploy docs site
```

---

## Testing Checklist

Before deploying:

- [ ] Test sync example in Python REPL
- [ ] Test async example in Python REPL
- [ ] Verify commodity codes are correct (BRENT_CRUDE_USD, WTI_USD)
- [ ] Check all methods exist (`client.prices.get()`, `client.prices.get_multiple()`)
- [ ] Test locally with `npm run dev`
- [ ] Check for TypeScript errors
- [ ] Test on mobile (responsive design)
- [ ] Verify links to PyPI, docs, signup work

---

## Timeline

**Before Saturday Reddit Post:**
- ✅ P0: Fix `/python-oil-api` code example (15 min)
- ⏳ P1: Add async section (30 min)
- ⏳ P2: Update `/developers/python` (15 min)

**After Reddit Post:**
- ⏳ P3: Update documentation site
- ⏳ P4: Add more advanced examples

---

## Files to Edit

1. `/home/kwaldman/code/website-clean/app/python-oil-api/page.tsx`
   - Lines 53-66: Fix code example
   - After line 89: Add async section

2. `/home/kwaldman/code/website-clean/app/developers/python/page.tsx`
   - Lines 23-99: Replace `pythonExample` const

3. `/home/kwaldman/code/oilpriceapi-docs/docs/sdks/python.md` (if exists)
   - Verify examples match SDK

---

## Impact

**If we fix before Saturday:**
- ✅ Reddit users try SDK and it works
- ✅ Good first impression
- ✅ Lower support burden
- ✅ More GitHub stars/PyPI downloads

**If we don't fix:**
- ❌ Users copy code from website → fails
- ❌ Bad reviews on Reddit
- ❌ Support requests: "Your examples don't work"
- ❌ Lost credibility

---

**Recommendation:** Fix P0 (correct code example) BEFORE Saturday Reddit post (30 minutes of work, high impact).
