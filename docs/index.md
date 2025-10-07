# OilPriceAPI Python SDK Documentation

Welcome to the official Python SDK for [OilPriceAPI](https://oilpriceapi.com) - the most affordable way to access professional-grade oil and commodity price data.

## 🚀 Getting Started

### Installation

Install the SDK using pip:

```bash
pip install oilpriceapi
```

### Get Your API Key

1. **[Sign up for free](https://oilpriceapi.com/auth/signup)** at OilPriceAPI
2. Get your API key from the dashboard
3. Start making requests immediately

### Quick Example

```python
from oilpriceapi import OilPriceAPI

# Initialize with your API key
client = OilPriceAPI(api_key="your_api_key")

# Get latest Brent Crude price
price = client.prices.get("BRENT_CRUDE_USD")
print(f"Brent Crude: ${price.value:.2f}")
```

## 📚 Core Features

### Real-Time Price Data

Get the latest commodity prices updated every 5 minutes:

```python
# Single commodity
brent = client.prices.get("BRENT_CRUDE_USD")

# Multiple commodities
prices = client.prices.get_multiple([
    "BRENT_CRUDE_USD",
    "WTI_USD",
    "NATURAL_GAS_USD"
])
```

**[View all available commodities →](https://docs.oilpriceapi.com/commodities)**

### Historical Data

Access years of historical price data for backtesting and analysis:

```python
# Get historical data
df = client.prices.to_dataframe(
    commodity="BRENT_CRUDE_USD",
    start="2024-01-01",
    end="2024-12-31",
    interval="daily"
)

# Analyze trends
print(df.describe())
```

**[Learn about historical endpoints →](https://docs.oilpriceapi.com/api-reference/historical)**

### Technical Analysis

Built-in technical indicators for trading strategies:

```python
# Add moving averages, RSI, MACD
df = client.analysis.with_indicators(
    df,
    indicators=["sma_20", "sma_50", "rsi", "bollinger_bands"]
)

# Calculate spread between commodities
spread = client.analysis.spread("BRENT_CRUDE_USD", "WTI_USD")
```

### Async Support

High-performance async operations for concurrent requests:

```python
import asyncio
from oilpriceapi import AsyncOilPriceAPI

async def get_all_prices():
    async with AsyncOilPriceAPI() as client:
        prices = await asyncio.gather(
            client.prices.get("BRENT_CRUDE_USD"),
            client.prices.get("WTI_USD"),
            client.prices.get("NATURAL_GAS_USD")
        )
        return prices

prices = asyncio.run(get_all_prices())
```

## 🎯 Use Cases

### Energy Trading
Build algorithmic trading strategies with real-time price feeds and historical data for backtesting.

**[Explore trading examples →](https://oilpriceapi.com/use-cases/trading)**

### Financial Analysis
Integrate commodity prices into financial models and risk management systems.

**[View financial use cases →](https://oilpriceapi.com/use-cases/finance)**

### Research & Analytics
Analyze long-term price trends, correlations, and market dynamics for academic or commercial research.

**[See research applications →](https://oilpriceapi.com/use-cases/research)**

### Web & Mobile Apps
Embed live commodity price widgets and charts in your applications.

**[Explore integration guides →](https://docs.oilpriceapi.com/integrations)**

## 📊 Available Commodities

### Crude Oil
- **Brent Crude** (`BRENT_CRUDE_USD`) - International benchmark
- **WTI** (`WTI_USD`) - US benchmark
- **Dubai Crude** (`DUBAI_CRUDE_USD`) - Middle East benchmark

### Natural Gas
- **Natural Gas** (`NATURAL_GAS_USD`) - Henry Hub spot price
- **LNG** (`LNG_USD`) - Liquefied natural gas

### Refined Products
- **Diesel** (`DIESEL_USD`)
- **Gasoline** (`GASOLINE_USD`)
- **Heating Oil** (`HEATING_OIL_USD`)
- **Jet Fuel** (`JET_FUEL_USD`)

**[View complete commodity list →](https://docs.oilpriceapi.com/commodities)**

## 🔧 Advanced Configuration

### Authentication

```python
# Environment variable (recommended)
export OILPRICEAPI_KEY="your_api_key"
client = OilPriceAPI()

# Direct configuration
client = OilPriceAPI(
    api_key="your_api_key",
    timeout=30,
    max_retries=3
)
```

### Caching

```python
# In-memory caching
client = OilPriceAPI(
    cache="memory",
    cache_ttl=300  # 5 minutes
)

# Redis caching
client = OilPriceAPI(
    cache="redis",
    cache_url="redis://localhost:6379"
)
```

### Error Handling

```python
from oilpriceapi.exceptions import (
    OilPriceAPIError,
    RateLimitError,
    DataNotFoundError
)

try:
    price = client.prices.get("BRENT_CRUDE_USD")
except RateLimitError as e:
    print(f"Rate limited. Resets in {e.seconds_until_reset}s")
except DataNotFoundError:
    print("Commodity not found")
except OilPriceAPIError as e:
    print(f"API error: {e}")
```

## 💰 Pricing & Plans

Choose the plan that fits your needs:

### Free Tier
- 1,000 API requests/month
- Real-time data
- No credit card required

**[Start free →](https://oilpriceapi.com/auth/signup)**

### Paid Plans
- **Exploration**: $15/month - 10,000 requests
- **Production Boost**: $45/month - 50,000 requests
- **Reservoir Mastery**: $129/month - 250,000 requests

**All plans include:**
- ✅ Real-time price updates every 5 minutes
- ✅ Historical data access
- ✅ 99.9% uptime SLA
- ✅ Email support
- ✅ No hidden fees

**[View detailed pricing →](https://oilpriceapi.com/pricing)**

## 🛠️ Development

### Testing Your Integration

```python
from oilpriceapi.testing import MockClient

def test_trading_strategy():
    # Create mock client
    client = MockClient()
    client.set_price("BRENT_CRUDE_USD", 75.50)

    # Test your code
    result = my_strategy(client)
    assert result.action == "BUY"
```

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=oilpriceapi --cov-report=html
```

## 📖 Additional Resources

### Documentation
- **[API Reference](https://docs.oilpriceapi.com/api-reference)** - Complete REST API documentation
- **[SDK Reference](https://docs.oilpriceapi.com/sdk/python)** - Python SDK API reference
- **[Quickstart Guide](https://docs.oilpriceapi.com/quickstart)** - Get started in 5 minutes
- **[Code Examples](https://docs.oilpriceapi.com/examples)** - Real-world code samples

### Support
- **[FAQ](https://oilpriceapi.com/faq)** - Frequently asked questions
- **[Status Page](https://status.oilpriceapi.com)** - API status and uptime
- **[GitHub Issues](https://github.com/oilpriceapi/python-sdk/issues)** - Bug reports and feature requests
- **[Email Support](mailto:support@oilpriceapi.com)** - Get help from our team

### Learning
- **[Blog](https://oilpriceapi.com/blog)** - Industry insights and tutorials
- **[Use Cases](https://oilpriceapi.com/use-cases)** - Learn how others use the API
- **[Changelog](https://github.com/oilpriceapi/python-sdk/blob/main/CHANGELOG.md)** - SDK version history

## 🤝 Contributing

We welcome contributions! Check out our [Contributing Guide](https://github.com/OilpriceAPI/python-sdk/blob/main/CONTRIBUTING.md) to get started.

## 📝 License

MIT License - see [LICENSE](https://github.com/OilpriceAPI/python-sdk/blob/main/LICENSE) file for details.

---

**Ready to get started?** [Sign up for your free API key →](https://oilpriceapi.com/auth/signup)

**Questions?** [Contact our support team →](mailto:support@oilpriceapi.com)

**Want to learn more?** [Visit OilPriceAPI.com →](https://oilpriceapi.com)
