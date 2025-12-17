# SDK Performance Guide

Complete guide to OilPriceAPI Python SDK performance characteristics and optimization best practices.

---

## Performance Baselines

Based on production measurements and integration tests.

### Current Price Queries

| Operation | Average Time | P95 | P99 |
|-----------|--------------|-----|-----|
| `prices.get()` (single) | 150ms | 300ms | 500ms |
| `prices.get_multiple()` (3 commodities) | 200ms | 400ms | 600ms |
| `prices.get_multiple()` (10 commodities) | 250ms | 500ms | 800ms |

**Expected Performance:**
- Single price: <500ms
- Multiple prices: <1s for up to 10 commodities

### Historical Data Queries

| Query Type | Date Range | Records | Avg Time | Max Time | Endpoint Used |
|------------|------------|---------|----------|----------|---------------|
| 1 Day | 1 day | ~24 | 1-2s | 10s | `/past_day` |
| 1 Week | 7 days | ~7-8 | 5-10s | 30s | `/past_week` |
| 1 Month | 30 days | ~30 | 15-25s | 60s | `/past_month` |
| 1 Year | 365 days | ~365 | 60-85s | 120s | `/past_year` |

**Expected Performance:**
- 1 week queries: <30s
- 1 month queries: <60s
- 1 year queries: <120s

**v1.4.1 Bug**: All queries used `/past_year` endpoint, causing 1-week queries to take 67s instead of <10s.

**v1.4.2 Fix**: Intelligent endpoint selection reduces query times by 7x for short ranges.

### Pagination Performance

| Per Page | Total Records | API Calls | Avg Time |
|----------|---------------|-----------|----------|
| 100 | 365 | 4 calls | 75s |
| 500 | 365 | 1 call | 70s |
| 1000 | 365 | 1 call | 68s |

**Recommendation**: Use `per_page=1000` for large datasets to minimize API calls.

---

## Optimization Techniques

### 1. Use Appropriate Date Ranges

**Bad** (slow):
```python
# Fetches 365 days when only need 7
client.historical.get(
    commodity="WTI_USD",
    start_date="2024-01-01",  # Way too far back
    end_date="2024-01-07"     # Only need 7 days
)
# Takes: ~70s (uses /past_year endpoint)
```

**Good** (fast):
```python
# Fetches exactly what you need
from datetime import datetime, timedelta

end_date = datetime.now()
start_date = end_date - timedelta(days=7)

client.historical.get(
    commodity="WTI_USD",
    start_date=start_date.strftime("%Y-%m-%d"),
    end_date=end_date.strftime("%Y-%m-%d")
)
# Takes: ~8s (uses /past_week endpoint)
```

### 2. Batch Multiple Commodities

**Bad** (multiple API calls):
```python
# Makes 3 separate API calls
wti = client.prices.get("WTI_USD")          # 150ms
brent = client.prices.get("BRENT_CRUDE_USD") # 150ms
natgas = client.prices.get("NATURAL_GAS_USD") # 150ms
# Total: ~450ms + network overhead
```

**Good** (single API call):
```python
# Makes 1 API call
prices = client.prices.get_multiple([
    "WTI_USD",
    "BRENT_CRUDE_USD",
    "NATURAL_GAS_USD"
])
# Total: ~200ms
```

### 3. Increase Pagination Limit

**Bad** (many small requests):
```python
# Default per_page=100 means 4 API calls for 365 records
history = client.historical.get(
    commodity="WTI_USD",
    start_date="2024-01-01",
    end_date="2024-12-31",
    per_page=100  # Too small
)
# Takes: ~75s (4 API calls)
```

**Good** (one large request):
```python
# per_page=1000 means 1 API call for 365 records
history = client.historical.get(
    commodity="WTI_USD",
    start_date="2024-01-01",
    end_date="2024-12-31",
    per_page=1000  # Optimal
)
# Takes: ~68s (1 API call)
```

### 4. Use Async Client for Parallel Queries

**Bad** (sequential):
```python
# Queries run one after another
client = OilPriceAPI()
wti_history = client.historical.get("WTI_USD", ...)    # 70s
brent_history = client.historical.get("BRENT_CRUDE_USD", ...)  # 70s
# Total: ~140s
```

**Good** (parallel):
```python
import asyncio
from oilpriceapi import AsyncOilPriceAPI

async def get_all_history():
    async with AsyncOilPriceAPI() as client:
        wti_task = client.historical.get("WTI_USD", ...)
        brent_task = client.historical.get("BRENT_CRUDE_USD", ...)

        wti, brent = await asyncio.gather(wti_task, brent_task)
        return wti, brent

# Total: ~70s (parallel execution)
```

### 5. Reuse Client Instance

**Bad** (creates new client each time):
```python
def get_price(commodity):
    client = OilPriceAPI()  # New connection each time
    price = client.prices.get(commodity)
    client.close()
    return price

# Each call has connection overhead
for commodity in commodities:
    price = get_price(commodity)  # Slow
```

**Good** (reuse connection):
```python
def get_prices(commodities):
    with OilPriceAPI() as client:  # Single connection
        return [client.prices.get(c) for c in commodities]

prices = get_prices(commodities)  # Fast
```

### 6. Specify Timeout for Long Queries

**Bad** (may timeout):
```python
# Uses default 30s timeout
# 1-year query takes 70s -> Timeout!
client.historical.get(
    commodity="WTI_USD",
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

**Good** (appropriate timeout):
```python
# SDK v1.4.2+ automatically sets timeout based on date range
# 1-year query uses 120s timeout
client.historical.get(
    commodity="WTI_USD",
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# Or manually specify for multi-year queries
client.historical.get(
    commodity="WTI_USD",
    start_date="2020-01-01",
    end_date="2024-12-31",
    timeout=180  # 3 minutes for 5 years
)
```

---

## Performance Pitfalls

### Pitfall 1: Polling for Latest Prices

**Anti-Pattern:**
```python
import time

while True:
    price = client.prices.get("WTI_USD")
    print(f"WTI: ${price.value}")
    time.sleep(1)  # Poll every second
```

**Problems:**
- Wastes API quota
- Unnecessary load on API
- Price only updates ~every 5 minutes

**Solution:**
```python
# Poll at reasonable interval
import time

while True:
    price = client.prices.get("WTI_USD")
    print(f"WTI: ${price.value}")
    time.sleep(300)  # Poll every 5 minutes
```

**Better Solution (for real-time):**
```python
# Use WebSocket for real-time updates (if available)
# Or increase polling interval to match update frequency
```

### Pitfall 2: Fetching All Historical Data

**Anti-Pattern:**
```python
# Fetches ALL data since beginning of time
history = client.historical.get(
    commodity="WTI_USD",
    start_date="1990-01-01",  # 35 years!
    end_date="2025-01-01"
)
# Takes: 5+ minutes, may timeout
```

**Solution:**
```python
# Fetch data in chunks
from datetime import datetime, timedelta

def get_historical_range(client, commodity, years=1):
    """Get historical data in 1-year chunks."""
    all_data = []
    end_date = datetime.now()

    for year in range(years):
        start_date = end_date - timedelta(days=365)

        chunk = client.historical.get(
            commodity=commodity,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )

        all_data.extend(chunk.data)
        end_date = start_date

    return all_data

# Get 5 years in 5 chunks of 1 year each
data = get_historical_range(client, "WTI_USD", years=5)
```

### Pitfall 3: Not Using Context Manager

**Anti-Pattern:**
```python
client = OilPriceAPI()
price = client.prices.get("WTI_USD")
# Forget to close - connection leak
```

**Solution:**
```python
# Auto-closes connection
with OilPriceAPI() as client:
    price = client.prices.get("WTI_USD")
```

### Pitfall 4: Ignoring Retry Logic

**Anti-Pattern:**
```python
# Disable retries for "performance"
client = OilPriceAPI(max_retries=0)

# One network blip = permanent failure
price = client.prices.get("WTI_USD")  # Fails on transient error
```

**Solution:**
```python
# Use default retry logic (max_retries=3)
client = OilPriceAPI()  # Retries on 429, 500, 502, 503, 504

# Retries protect against transient failures
price = client.prices.get("WTI_USD")  # Resilient
```

---

## Caching Strategies

### Client-Side Caching

**Basic In-Memory Cache:**
```python
from datetime import datetime, timedelta
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_price(commodity, cache_key):
    """Cache prices for 5 minutes."""
    client = OilPriceAPI()
    return client.prices.get(commodity)

# Cache key changes every 5 minutes
def get_current_price(commodity):
    cache_key = int(datetime.now().timestamp() / 300)
    return get_cached_price(commodity, cache_key)

# First call: API request (150ms)
price1 = get_current_price("WTI_USD")

# Second call within 5 min: cached (<1ms)
price2 = get_current_price("WTI_USD")
```

**Redis Cache (for multi-process):**
```python
import redis
import json
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379)

def get_cached_price(client, commodity):
    """Cache price in Redis for 5 minutes."""
    cache_key = f"oilprice:{commodity}"

    # Check cache
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Fetch from API
    price = client.prices.get(commodity)

    # Cache for 5 minutes
    redis_client.setex(
        cache_key,
        timedelta(minutes=5),
        json.dumps(price.dict())
    )

    return price
```

### When to Cache

✅ **Good candidates for caching:**
- Latest prices (updates every 5 minutes)
- Historical data (never changes)
- Commodity metadata
- Static reference data

❌ **Don't cache:**
- Real-time price updates (if using WebSocket)
- User-specific data
- Data that changes frequently

---

## Monitoring Performance

### Track Response Times

```python
import time
from oilpriceapi import OilPriceAPI

def timed_query(operation, *args, **kwargs):
    """Execute operation and measure time."""
    start = time.time()

    try:
        result = operation(*args, **kwargs)
        duration = time.time() - start
        print(f"✓ {operation.__name__}: {duration:.2f}s")
        return result

    except Exception as e:
        duration = time.time() - start
        print(f"✗ {operation.__name__}: {duration:.2f}s - {e}")
        raise

# Usage
client = OilPriceAPI()

price = timed_query(client.prices.get, "WTI_USD")
# Output: ✓ get: 0.15s

history = timed_query(
    client.historical.get,
    commodity="WTI_USD",
    start_date="2024-01-01",
    end_date="2024-12-31"
)
# Output: ✓ get: 72.30s
```

### Set Performance Budgets

```python
class PerformanceBudget:
    """Assert operations complete within budget."""

    BUDGETS = {
        "prices.get": 0.5,           # 500ms
        "prices.get_multiple": 1.0,  # 1 second
        "historical.1_week": 30,     # 30 seconds
        "historical.1_month": 60,    # 60 seconds
        "historical.1_year": 120,    # 120 seconds
    }

    @staticmethod
    def check(operation, duration):
        budget = PerformanceBudget.BUDGETS.get(operation)
        if budget and duration > budget:
            print(f"⚠️  PERFORMANCE: {operation} took {duration:.2f}s (budget: {budget}s)")
            return False
        return True

# Usage
start = time.time()
price = client.prices.get("WTI_USD")
duration = time.time() - start

PerformanceBudget.check("prices.get", duration)
```

---

## Troubleshooting Slow Queries

### Diagnostic Checklist

1. **Check SDK Version**
   ```python
   import oilpriceapi
   print(oilpriceapi.__version__)
   # Should be >= 1.4.2 for optimal performance
   ```

2. **Check Date Range**
   ```python
   # Are you fetching more data than needed?
   days = (end_date - start_date).days
   print(f"Fetching {days} days of data")
   ```

3. **Check Network Latency**
   ```bash
   # Test API connectivity
   curl -w "%{time_total}\n" https://api.oilpriceapi.com/v1/health
   ```

4. **Check Pagination**
   ```python
   # Are you making too many small requests?
   print(f"Per page: {per_page}, Total pages: {total_records / per_page}")
   ```

5. **Enable Debug Logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)

   # Will show all HTTP requests and timing
   client = OilPriceAPI()
   ```

### Common Issues & Fixes

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Timeout on 1-year query | SDK v1.4.1 bug | Upgrade to v1.4.2+ |
| Slow historical queries | Using wrong endpoint | Upgrade to v1.4.2+ |
| Many small requests | Low pagination limit | Increase `per_page` to 1000 |
| Connection errors | Not reusing client | Use context manager |
| High memory usage | Loading too much data | Fetch in chunks |

---

## Performance Testing

### Benchmark Script

```python
"""
Benchmark SDK performance.

Usage: python benchmark.py
"""

import time
from datetime import datetime, timedelta
from oilpriceapi import OilPriceAPI

def benchmark():
    client = OilPriceAPI()

    tests = [
        ("Current price", lambda: client.prices.get("WTI_USD")),
        ("Multiple prices (3)", lambda: client.prices.get_multiple([
            "WTI_USD", "BRENT_CRUDE_USD", "NATURAL_GAS_USD"
        ])),
        ("1 week history", lambda: client.historical.get(
            "WTI_USD",
            (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d")
        )),
        ("1 month history", lambda: client.historical.get(
            "WTI_USD",
            (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d")
        )),
        ("1 year history", lambda: client.historical.get(
            "WTI_USD",
            "2024-01-01",
            "2024-12-31"
        )),
    ]

    print("="*60)
    print("OilPriceAPI SDK Performance Benchmark")
    print("="*60)
    print()

    for name, operation in tests:
        start = time.time()
        try:
            result = operation()
            duration = time.time() - start
            print(f"✓ {name:30s} {duration:8.2f}s")
        except Exception as e:
            duration = time.time() - start
            print(f"✗ {name:30s} {duration:8.2f}s - {e}")

    print()

if __name__ == "__main__":
    benchmark()
```

---

## Summary

### Quick Performance Checklist

- [ ] Using SDK v1.4.2+ (has endpoint optimization)
- [ ] Fetching minimal date range needed
- [ ] Using `per_page=1000` for large datasets
- [ ] Batching multiple commodity queries
- [ ] Reusing client instances
- [ ] Using context managers
- [ ] Caching where appropriate
- [ ] Setting appropriate timeouts
- [ ] Monitoring performance
- [ ] Running performance tests

### Expected Performance

- Current prices: <500ms
- Multiple prices (10): <1s
- 1 week history: <30s
- 1 month history: <60s
- 1 year history: <120s

### When to Optimize

Optimize when:
- Queries consistently exceed budgets
- User experience is affected
- API quota is being wasted
- Costs are higher than expected

Don't optimize prematurely - profile first!

---

## Related

- [Integration Tests](../tests/integration/README.md) - Performance baselines
- [Monitoring Guide](../.github/MONITORING_GUIDE.md) - Track performance
- [GitHub Issue #26](https://github.com/OilpriceAPI/python-sdk/issues/26)
