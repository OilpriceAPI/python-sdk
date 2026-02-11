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

> **📝 Documentation Status**: This README reflects v1.5.0 features. All code examples shown are tested and working. Advanced features like technical indicators and CLI tools are planned for future releases - see our [GitHub Issues](https://github.com/OilpriceAPI/python-sdk/issues) for roadmap.

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

### Price Alerts (New in v1.5.0)

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
  "current_price": 86.5,
  "condition_operator": "greater_than",
  "condition_value": 85.0,
  "triggered_at": "2025-12-15T10:30:00Z"
}
```

### Commodities Catalog (New in v1.5.0)

```python
# Get all available commodities
commodities = client.commodities.list()
for commodity in commodities:
    print(f"{commodity['code']}: {commodity['name']}")

# Get details for specific commodity
brent = client.commodities.get("BRENT_CRUDE_USD")
print(f"Category: {brent['category']}")
print(f"Unit: {brent['unit']}")

# Get commodities grouped by category
categories = client.commodities.categories()
crude_oils = categories.get('Crude Oil', [])
```

### Futures Contracts (New in v1.5.0)

```python
# Get latest front month WTI futures
price = client.futures.latest("CL.1")
print(f"WTI Front Month: ${price['price']:.2f}")

# Get OHLC data
ohlc = client.futures.ohlc("CL.1")
print(f"Open: ${ohlc['open']:.2f}, High: ${ohlc['high']:.2f}")

# Get futures curve
curve = client.futures.curve("CL")
for point in curve:
    print(f"{point['month']}: ${point['price']:.2f}")

# Spread analysis between contracts
spread = client.futures.spreads("CL.1", "CL.2")
print(f"Calendar Spread: ${spread['current_spread']:.2f}")
```

### Oil Storage & Inventory (New in v1.5.0)

```python
# Get Cushing, OK inventory
cushing = client.storage.cushing()
print(f"Cushing Inventory: {cushing['value']} barrels")
print(f"Weekly Change: {cushing['change']} barrels")

# Strategic Petroleum Reserve
spr = client.storage.spr()
print(f"SPR Inventory: {spr['value']} barrels")

# Regional storage (PADD regions)
regional = client.storage.regional(region="PADD3")
print(f"Gulf Coast: {regional['value']} barrels")

# Historical storage data
history = client.storage.history("cushing", start_date="2024-01-01")
```

### Rig Counts (New in v1.5.0)

```python
# Get latest rig counts
rig_counts = client.rig_counts.latest()
print(f"Oil Rigs: {rig_counts['oil']}")
print(f"Gas Rigs: {rig_counts['gas']}")
print(f"Total: {rig_counts['total']}")

# Get rig count summary with changes
summary = client.rig_counts.summary()
print(f"Week Change: {summary['week_change']}")
print(f"Year Change: {summary['year_change']}")

# Historical rig counts
history = client.rig_counts.historical(start_date="2024-01-01")
```

### Bunker Fuels (New in v1.5.0)

```python
# Get bunker prices for Singapore
singapore = client.bunker_fuels.port("SINGAPORE")
print(f"VLSFO: ${singapore['vlsfo']['price']}")
print(f"MGO: ${singapore['mgo']['price']}")

# Compare prices across ports
comparison = client.bunker_fuels.compare(["SINGAPORE", "ROTTERDAM", "HOUSTON"])
for port, data in comparison.items():
    print(f"{port}: ${data['vlsfo']['price']}")

# Spread analysis
spreads = client.bunker_fuels.spreads()
print(f"VLSFO-MGO Spread: ${spreads['vlsfo_mgo']:.2f}")
```

### Price Analytics (New in v1.5.0)

```python
# Get 30-day performance
perf = client.analytics.performance("BRENT_CRUDE_USD", days=30)
print(f"30-day Return: {perf['return_pct']}%")
print(f"Volatility: {perf['volatility']}")

# Statistical analysis
stats = client.analytics.statistics("WTI_USD", days=90)
print(f"Mean: ${stats['mean']:.2f}, Std Dev: ${stats['std_dev']:.2f}")

# Correlation between commodities
corr = client.analytics.correlation("BRENT_CRUDE_USD", "WTI_USD", days=90)
print(f"Correlation: {corr['correlation']:.3f}")

# Trend analysis
trend = client.analytics.trend("NATURAL_GAS_USD", days=30)
print(f"Direction: {trend['direction']}, Strength: {trend['strength']}")

# Price forecast
forecast = client.analytics.forecast("BRENT_CRUDE_USD")
print(f"7-day Forecast: ${forecast['7_day']['price']:.2f}")
```

### Drilling Intelligence (New in v1.5.0)

```python
# Get latest drilling data
latest = client.drilling.latest()
print(f"Total rigs: {latest['total_rigs']}")
print(f"Frac spreads: {latest['frac_spreads']}")

# DUC (Drilled but Uncompleted) wells
ducs = client.drilling.duc_wells()
for duc in ducs:
    print(f"{duc['basin']}: {duc['count']} DUCs")

# Basin-specific data
permian = client.drilling.basin("permian")
print(f"Permian rigs: {permian['rig_count']}")

# Completion trends
completions = client.drilling.completions()
```

### Webhooks (New in v1.5.0)

```python
# Create webhook for price updates
webhook = client.webhooks.create(
    url="https://myapp.com/webhook",
    events=["price.updated", "alert.triggered"],
    description="Price alerts webhook",
    enabled=True
)
print(f"Webhook created: {webhook['id']}")

# List all webhooks
webhooks = client.webhooks.list()
for wh in webhooks:
    print(f"{wh['url']}: {wh['events']}")

# Test webhook endpoint
result = client.webhooks.test(webhook['id'])
print(f"Test status: {result['status']}")

# View webhook event history
events = client.webhooks.events(webhook['id'])
for event in events:
    print(f"{event['created_at']}: {event['type']} - {event['status']}")

# Delete webhook
client.webhooks.delete(webhook['id'])
```

### EIA Forecasts (New in v1.5.0)

```python
# Get monthly EIA forecasts
forecasts = client.forecasts.monthly()
for forecast in forecasts:
    print(f"{forecast['period']}: ${forecast['price']:.2f}")

# Get specific commodity forecast
wti_forecast = client.forecasts.get("2025-03", commodity="WTI_USD")
print(f"March 2025 WTI: ${wti_forecast['price']:.2f}")
print(f"Range: ${wti_forecast['low']:.2f} - ${wti_forecast['high']:.2f}")

# Check forecast accuracy
accuracy = client.forecasts.accuracy()
print(f"30-day Accuracy: {accuracy['30_day']['accuracy']}%")
```

### Data Quality Monitoring (New in v1.5.0)

```python
# Get overall data quality summary
summary = client.data_quality.summary()
print(f"Overall Quality Score: {summary['score']}")
print(f"Total Issues: {summary['total_issues']}")

# Get quality report for specific commodity
report = client.data_quality.report("BRENT_CRUDE_USD")
print(f"Quality Score: {report['quality_score']}%")
print(f"Completeness: {report['completeness']}%")
print(f"Last Update: {report['last_update']}")

# Get all quality reports
reports = client.data_quality.reports()
for report in reports:
    print(f"{report['commodity']}: {report['quality_score']}%")
```

### Energy Intelligence (New in v1.5.0)

```python
# Access EI sub-resources for government energy data
# EI rig counts
ei_rigs = client.ei.rig_counts.latest()
print(f"Total rigs: {ei_rigs['total']}")

# EI oil inventories (EIA weekly data)
inventories = client.ei.oil_inventories.latest()
print(f"Crude stocks: {inventories['crude']} barrels")

# OPEC production data
opec = client.ei.opec_production.latest()
for country, data in opec.items():
    print(f"{country}: {data['production']} bbl/day")

# Drilling productivity
productivity = client.ei.drilling_productivity.latest()
print(f"Permian: {productivity['permian']['boe_per_rig']} BOE/rig")

# Well timeline data
timeline = client.ei.well_timeline("42-123-45678")
for event in timeline['events']:
    print(f"{event['date']}: {event['type']}")
```

### Data Sources (New in v1.5.0)

```python
# List all configured data sources
sources = client.data_sources.list()
for source in sources:
    print(f"{source['name']}: {source['type']} - {source['status']}")

# Check health of a data source
health = client.data_sources.health("123")
print(f"Status: {health['status']}")
print(f"Last successful fetch: {health['last_success']}")

# View data source logs
logs = client.data_sources.logs("123", limit=100)
for log in logs:
    print(f"{log['timestamp']}: {log['level']} - {log['message']}")

# Test connection
result = client.data_sources.test("123")
print(f"Test status: {result['status']}")
```

## 📊 Features

- ✅ **Simple API** - Intuitive methods for all endpoints
- ✅ **Type Safe** - Full type hints for IDE autocomplete
- ✅ **Pandas Integration** - First-class DataFrame support
- ✅ **Price Alerts** - Automated monitoring with webhook notifications 🔔
- ✅ **Diesel Prices** - State averages + station-level pricing ⛽
- ✅ **Futures Contracts** - OHLC, curves, spreads, and continuous data
- ✅ **Storage & Inventory** - Cushing, SPR, and regional PADD data
- ✅ **Rig Counts** - Baker Hughes rig counts with historical trends
- ✅ **Bunker Fuels** - Marine fuel prices across major ports
- ✅ **Price Analytics** - Performance, correlations, trends, and forecasts
- ✅ **Drilling Intelligence** - DUC wells, permits, completions, and basin data
- ✅ **Webhooks** - Manage event subscriptions and notifications
- ✅ **EIA Forecasts** - Official monthly price forecasts with accuracy tracking
- ✅ **Energy Intelligence** - EIA data, OPEC production, drilling productivity
- ✅ **Data Quality** - Real-time quality monitoring and reporting
- ✅ **Data Sources** - Connector management with health checks and logging
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

[View all 107+ commodities](https://docs.oilpriceapi.com/commodities)

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
