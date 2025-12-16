# OilPriceAPI Python SDK

> **Real-time oil and commodity price data for Python** - Professional-grade API at 98% less cost than Bloomberg Terminal

[![PyPI version](https://badge.fury.io/py/oilpriceapi.svg)](https://badge.fury.io/py/oilpriceapi)
[![PyPI Downloads](https://img.shields.io/pypi/dm/oilpriceapi)](https://pypistats.org/packages/oilpriceapi)
[![Python](https://img.shields.io/pypi/pyversions/oilpriceapi.svg)](https://pypi.org/project/oilpriceapi/)
[![Tests](https://github.com/oilpriceapi/python-sdk/actions/workflows/test.yml/badge.svg)](https://github.com/oilpriceapi/python-sdk/actions/workflows/test.yml)
[![Coverage](https://codecov.io/gh/oilpriceapi/python-sdk/branch/main/graph/badge.svg)](https://codecov.io/gh/oilpriceapi/python-sdk)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**[Get Free API Key](https://oilpriceapi.com/auth/signup)** • **[Documentation](https://docs.oilpriceapi.com/sdk/python)** • **[Pricing](https://oilpriceapi.com/pricing)**

The official Python SDK for [OilPriceAPI](https://oilpriceapi.com) - Real-time and historical oil prices for Brent Crude, WTI, Natural Gas, and more.

> **📝 Documentation Status**: This README reflects v1.4.0 features. All code examples shown are tested and working. Advanced features like technical indicators and CLI tools are planned for future releases - see our [GitHub Issues](https://github.com/OilpriceAPI/python-sdk/issues) for roadmap.

**Quick start:**
```bash
pip install oilpriceapi
```

## 🚀 Quick Start

### Installation

```bash
pip install oilpriceapi
```

### Basic Usage

```python
from oilpriceapi import OilPriceAPI

# Initialize client (uses OILPRICEAPI_KEY env var by default)
client = OilPriceAPI()

# Get latest Brent Crude price
brent = client.prices.get("BRENT_CRUDE_USD")
print(f"Brent Crude: ${brent.value:.2f}")
# Output: Brent Crude: $71.45

# Get multiple prices
prices = client.prices.get_multiple(["BRENT_CRUDE_USD", "WTI_USD", "NATURAL_GAS_USD"])
for price in prices:
    print(f"{price.commodity}: ${price.value:.2f}")
```

### Historical Data with Pandas

```python
# Get historical data as DataFrame
df = client.prices.to_dataframe(
    commodity="BRENT_CRUDE_USD",
    start="2024-01-01",
    end="2024-12-31",
    interval="daily"
)

print(f"Retrieved {len(df)} data points")
print(df.head())
```

### Diesel Prices (New in v1.3.0)

```python
# Get state average diesel price (free tier)
ca_price = client.diesel.get_price("CA")
print(f"California diesel: ${ca_price.price:.2f}/gallon")
print(f"Source: {ca_price.source}")
print(f"Updated: {ca_price.updated_at}")

# Get nearby diesel stations (paid tiers)
result = client.diesel.get_stations(
    lat=37.7749,   # San Francisco
    lng=-122.4194,
    radius=8047    # 5 miles in meters
)

print(f"Regional average: ${result.regional_average.price:.2f}/gallon")
print(f"Found {len(result.stations)} stations")

# Find cheapest station
cheapest = min(result.stations, key=lambda s: s.diesel_price)
print(f"Cheapest: {cheapest.name} at {cheapest.formatted_price}")
print(f"Savings: ${abs(cheapest.price_delta):.2f}/gal vs average")

# Get diesel prices as DataFrame
df = client.diesel.to_dataframe(states=["CA", "TX", "NY", "FL"])
print(df[["state", "price", "updated_at"]])

# Station data as DataFrame
df_stations = client.diesel.to_dataframe(
    lat=34.0522,   # Los Angeles
    lng=-118.2437,
    radius=5000
)
print(df_stations[["name", "diesel_price", "price_vs_average"]])
```

### Price Alerts (New in v1.4.0)

```python
# Create a price alert with webhook notification
alert = client.alerts.create(
    name="Brent High Alert",
    commodity_code="BRENT_CRUDE_USD",
    condition_operator="greater_than",
    condition_value=85.00,
    webhook_url="https://your-server.com/webhook",  # Optional
    enabled=True,
    cooldown_minutes=60  # Min time between triggers
)

print(f"Alert created: {alert.id}")
print(f"Monitoring: {alert.commodity_code}")
print(f"Condition: {alert.condition_operator} ${alert.condition_value}")

# List all alerts
alerts = client.alerts.list()
for alert in alerts:
    print(f"{alert.name}: {alert.enabled} ({alert.trigger_count} triggers)")

# Update an alert
updated = client.alerts.update(
    alert.id,
    condition_value=90.00,
    enabled=False
)

# Test webhook endpoint
test_result = client.alerts.test_webhook("https://your-server.com/webhook")
if test_result.success:
    print(f"Webhook OK: {test_result.status_code} in {test_result.response_time_ms}ms")
else:
    print(f"Webhook failed: {test_result.error}")

# Delete an alert
client.alerts.delete(alert.id)

# Get alerts as DataFrame
df = client.alerts.to_dataframe()
print(df[["name", "commodity_code", "condition_value", "trigger_count"]])
```

**Supported operators:**
- `greater_than` - Price exceeds threshold
- `less_than` - Price falls below threshold
- `equals` - Price matches threshold
- `greater_than_or_equal` - Price meets or exceeds threshold
- `less_than_or_equal` - Price meets or falls below threshold

**Webhook Payload:**
```json
{
  "alert_id": "550e8400-e29b-41d4-a716-446655440000",
  "alert_name": "Brent High Alert",
  "commodity_code": "BRENT_CRUDE_USD",
  "current_price": 86.50,
  "condition_operator": "greater_than",
  "condition_value": 85.00,
  "triggered_at": "2025-12-15T10:30:00Z"
}
```

## 📊 Features

- ✅ **Simple API** - Intuitive methods for all endpoints
- ✅ **Type Safe** - Full type hints for IDE autocomplete
- ✅ **Pandas Integration** - First-class DataFrame support
- ✅ **Price Alerts** - Automated monitoring with webhook notifications 🔔
- ✅ **Diesel Prices** - State averages + station-level pricing ⛽
- ✅ **Async Support** - High-performance async client
- ✅ **Smart Caching** - Reduce API calls automatically
- ✅ **Rate Limit Handling** - Automatic retries with backoff
- ✅ **Error Handling** - Comprehensive exception classes

## 📚 Documentation

**[Complete SDK Documentation →](docs/index.md)** | **[Online Docs →](https://docs.oilpriceapi.com/sdk/python)**

### Authentication

```python
# Method 1: Environment variable (recommended)
export OILPRICEAPI_KEY="your_api_key"
client = OilPriceAPI()

# Method 2: Direct initialization
client = OilPriceAPI(api_key="your_api_key")

# Method 3: With configuration
client = OilPriceAPI(
    api_key="your_api_key",
    timeout=30,
    max_retries=3,
    cache="memory",
    cache_ttl=300
)
```

### Available Commodities

**Oil & Gas:**
- `BRENT_CRUDE_USD` - Brent Crude Oil
- `WTI_USD` - West Texas Intermediate
- `NATURAL_GAS_USD` - Natural Gas
- `DIESEL_USD` - Diesel
- `GASOLINE_USD` - Gasoline
- `HEATING_OIL_USD` - Heating Oil

**Coal (8 Endpoints):**
- `CAPP_COAL_USD` - Central Appalachian Coal (US Spot)
- `PRB_COAL_USD` - Powder River Basin Coal (US Spot)
- `ILLINOIS_COAL_USD` - Illinois Basin Coal (US Spot)
- `NEWCASTLE_COAL_USD` - Newcastle API6 (International Futures)
- `COKING_COAL_USD` - Metallurgical Coal (International Futures)
- `CME_COAL_USD` - CME Coal Futures
- `NYMEX_APPALACHIAN_USD` - NYMEX Central Appalachian (Historical 2004-2016)
- `NYMEX_WESTERN_RAIL_USD` - NYMEX Powder River Basin (Historical 2009-2017)

[View all 79 commodities](https://docs.oilpriceapi.com/commodities)

### Error Handling

```python
from oilpriceapi.exceptions import OilPriceAPIError, RateLimitError, DataNotFoundError

try:
    price = client.prices.get("INVALID_CODE")
except DataNotFoundError as e:
    print(f"Commodity not found: {e}")
except RateLimitError as e:
    print(f"Rate limited. Resets in {e.seconds_until_reset}s")
except OilPriceAPIError as e:
    print(f"API error: {e}")
```

## ⚡ Async Support

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
        return prices

# Run async function
prices = asyncio.run(get_prices())
```

## 🧪 Testing

The SDK uses standard Python testing frameworks. Example using pytest:

```python
import pytest
from oilpriceapi import OilPriceAPI

def test_get_price():
    client = OilPriceAPI(api_key="your_test_key")
    price = client.prices.get("BRENT_CRUDE_USD")

    assert price is not None
    assert price.value > 0
    assert price.commodity == "BRENT_CRUDE_USD"
```

## 📈 Examples

### Quick Examples

```python
# Example 1: Get multiple commodity prices
from oilpriceapi import OilPriceAPI

client = OilPriceAPI()
commodities = ["BRENT_CRUDE_USD", "WTI_USD", "NATURAL_GAS_USD"]
prices = client.prices.get_multiple(commodities)

for price in prices:
    print(f"{price.commodity}: ${price.value:.2f}")
```

```python
# Example 2: Historical data analysis with pandas
import pandas as pd
from oilpriceapi import OilPriceAPI

client = OilPriceAPI()
df = client.prices.to_dataframe(
    commodity="BRENT_CRUDE_USD",
    start="2024-01-01",
    end="2024-12-31"
)

# Calculate simple moving average
df['SMA_20'] = df['price'].rolling(window=20).mean()
print(df[['created_at', 'price', 'SMA_20']].tail())
```

```python
# Example 3: Price alerts with webhooks
from oilpriceapi import OilPriceAPI

client = OilPriceAPI()

# Create alert when oil exceeds $85
alert = client.alerts.create(
    name="High Oil Price Alert",
    commodity_code="BRENT_CRUDE_USD",
    condition_operator="greater_than",
    condition_value=85.00,
    webhook_url="https://your-app.com/webhook",
    enabled=True
)

print(f"Alert created: {alert.id}")
```

## 🔧 Development

```bash
# Clone repository
git clone https://github.com/oilpriceapi/python-sdk
cd python-sdk

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .

# Type checking
mypy oilpriceapi
```

## 📝 License

MIT License - see [LICENSE](https://github.com/OilpriceAPI/python-sdk/blob/main/LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please see our [Contributing Guide](https://github.com/OilpriceAPI/python-sdk/blob/main/CONTRIBUTING.md) for details.

## 💬 Support

- 📧 Email: support@oilpriceapi.com
- 🐛 Issues: [GitHub Issues](https://github.com/oilpriceapi/python-sdk/issues)
- 📖 Docs: [Documentation](https://docs.oilpriceapi.com/sdk/python)

## 🔗 Links

- [OilPriceAPI Website](https://oilpriceapi.com)
- [API Documentation](https://docs.oilpriceapi.com)
- [Pricing](https://oilpriceapi.com/pricing)
- [Status Page](https://status.oilpriceapi.com)

---

## 🌟 Why OilPriceAPI?

[OilPriceAPI](https://oilpriceapi.com) provides professional-grade commodity price data at **98% less cost than Bloomberg Terminal** ($24,000/year vs $45/month). Trusted by energy traders, financial analysts, and developers worldwide.

### Key Benefits
- ⚡ **Real-time data** updated every 5 minutes
- 📊 **Historical data** for trend analysis and backtesting
- 🔒 **99.9% uptime** with enterprise-grade reliability
- 🚀 **5-minute integration** with this Python SDK
- 💰 **Free tier** with 100 requests (lifetime) to get started

**[Start Free →](https://oilpriceapi.com/auth/signup)** | **[View Pricing →](https://oilpriceapi.com/pricing)** | **[Read Docs →](https://docs.oilpriceapi.com)**

---

Made with ❤️ by the OilPriceAPI Team