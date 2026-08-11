# OilPriceAPI Python SDK Documentation

Welcome to the official Python SDK for [OilPriceAPI](https://oilpriceapi.com), providing source-timestamped oil and commodity data.

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

### Current Price Data

Get the latest available commodity prices with API-provided source timestamps:

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

**[View the current commodity catalog →](https://docs.oilpriceapi.com/commodities)**

### Historical Data

Access years of historical price data for backtesting and analysis:

```python
# Get historical data
df = client.prices.to_dataframe(
    commodity="BRENT_CRUDE_USD",
    start="2024-01-01",
    end="2024-12-31",
    interval="daily",
    per_page=500
)

# Analyze trends
print(df.describe())
```

The DataFrame helper fetches every page and preserves the `currency` and
`unit` returned for each record. `per_page` may be set from 1 to 1000 and
controls request size rather than total results. See
**[DataFrames and pagination →](DATAFRAMES.md)** for empty-result and page
boundary behavior.

**[Learn about historical endpoints →](https://docs.oilpriceapi.com/api-reference/historical)**

Date strings use strict `YYYY-MM-DD` syntax and are checked before a request.
See **[Dates and commodity codes →](CODE_GUIDANCE.md)** for validation and
recovery behavior.

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
Build algorithmic trading strategies with current and historical data while retaining source timestamps for backtesting.

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

## 📊 Find Commodity Codes

Search the current API catalog so an integration does not depend on a stale
code list:

```python
matches = client.commodities.search("brent crude", limit=5)
print([commodity["code"] for commodity in matches])
```

**[View dates and commodity-code guidance →](CODE_GUIDANCE.md)**

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
from oilpriceapi import (
    DataNotFoundError,
    OilPriceAPIError,
    RateLimitError,
)

try:
    price = client.prices.get("BRENT_CRUDE_USD")
except RateLimitError as error:
    print(f"Rate limited. Resets in {error.seconds_until_reset}s")
except DataNotFoundError:
    print("Commodity not found")
except OilPriceAPIError as error:
    if error.code == "invalid_code" and error.suggestions:
        print("Try one of:", ", ".join(error.suggestions))
    if error.request_id:
        print("Support request ID:", error.request_id)
    if error.remediation_url:
        print("Recovery:", error.remediation_url)
    print(f"API error: {error}")
```

Every non-2xx response uses this shared typed contract. `status_code`, `code`,
commodity suggestions, plan or feature requirements, retry metadata, sanitized
response headers, and raw diagnostics remain available without exposing the
configured API key.

## 💰 Access & Plans

Dataset access, allowances, and feature availability depend on the current
account entitlement. Review the [current pricing](https://oilpriceapi.com/pricing)
and the machine-readable [product facts](https://api.oilpriceapi.com/product-facts.json)
instead of relying on values bundled into an SDK release. API responses retain
the applicable source, observation timestamp, and limit metadata.

**[Create an API key →](https://oilpriceapi.com/auth/signup)**

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

**Ready to get started?** [Create an API key →](https://oilpriceapi.com/auth/signup)

**Questions?** [Contact our support team →](mailto:support@oilpriceapi.com)

**Want to learn more?** [Visit OilPriceAPI.com →](https://oilpriceapi.com)
