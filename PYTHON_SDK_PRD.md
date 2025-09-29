# OilPriceAPI Python SDK - Product Requirements Document

## 📋 Executive Summary

Build a best-in-class Python SDK that makes OilPriceAPI the easiest commodity price API to integrate, with special focus on data science workflows, type safety, and developer experience.

## 🎯 Goals & Success Metrics

### Primary Goals
1. **Reduce integration time** from 4+ hours to <15 minutes
2. **Increase API adoption** by 50% within 6 months
3. **Become the preferred** oil price data source for Python developers

### Success Metrics
- **Week 1**: 100+ installs, 5+ GitHub stars
- **Month 1**: 1,000+ installs, 25+ stars, <5% support tickets
- **Month 6**: 10,000+ monthly installs, 200+ stars, 30% of API traffic via SDK

## 👥 Target Users

### Primary: Quantitative Analyst/Data Scientist
```python
# What they want:
import oilpriceapi as opa

# Instant pandas DataFrame
df = opa.get_prices("BRENT_CRUDE_USD", start="2024-01-01")

# Easy visualization
df.plot(y='price', title='Brent Crude 2024')

# Simple analysis
spreads = opa.calculate_spread("BRENT_CRUDE_USD", "WTI_USD")
```

### Secondary: Trading System Developer
```python
# Real-time async operations
async with opa.AsyncClient() as client:
    prices = await client.get_multiple_prices([
        "BRENT_CRUDE_USD",
        "WTI_USD",
        "NATURAL_GAS_USD"
    ])
```

### Tertiary: Hobbyist/Student
```python
# Dead simple for beginners
oil = opa.get_current_price("BRENT_CRUDE_USD")
print(f"Oil is ${oil}")  # "Oil is $71.45"
```

## 🏗️ Core Architecture

### Package Structure
```
sdks/python/
├── oilpriceapi/
│   ├── __init__.py           # Main exports, version
│   ├── client.py             # OilPriceAPIClient class
│   ├── async_client.py       # AsyncOilPriceAPIClient
│   ├── auth.py               # Authentication handling
│   ├── config.py             # Configuration management
│   ├── exceptions.py         # Custom exceptions
│   │
│   ├── models/               # Pydantic models
│   │   ├── __init__.py
│   │   ├── price.py          # Price, PriceResponse
│   │   ├── commodity.py      # Commodity enum
│   │   └── common.py         # Shared models
│   │
│   ├── resources/            # API endpoint groups
│   │   ├── __init__.py
│   │   ├── base.py           # BaseResource class
│   │   ├── prices.py         # Prices endpoints
│   │   ├── historical.py     # Historical data
│   │   ├── futures.py        # Futures endpoints
│   │   └── storage.py        # Storage data
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── retry.py          # Retry logic
│   │   ├── pagination.py     # Pagination helpers
│   │   ├── cache.py          # Caching layer
│   │   └── validators.py     # Input validation
│   │
│   └── integrations/
│       ├── __init__.py
│       ├── pandas_ext.py     # Pandas extensions
│       ├── numpy_ext.py      # NumPy helpers
│       └── jupyter.py        # Jupyter utilities
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── examples/
│   ├── quickstart.ipynb
│   ├── data_analysis.ipynb
│   ├── trading_signals.ipynb
│   └── async_example.py
│
├── docs/
│   ├── getting-started.md
│   ├── api-reference.md
│   └── examples.md
│
├── pyproject.toml            # Modern Python packaging
├── setup.py                  # Backwards compatibility
├── README.md
├── CHANGELOG.md
├── LICENSE
└── .github/
    └── workflows/
        ├── test.yml
        ├── publish.yml
        └── docs.yml
```

## 💻 Core Features

### 1. Simple Initialization
```python
# Environment variable (preferred)
client = OilPriceAPI()  # Uses OILPRICEAPI_KEY

# Direct key
client = OilPriceAPI(api_key="your_key")

# With configuration
client = OilPriceAPI(
    api_key="your_key",
    timeout=30,
    max_retries=3,
    cache_ttl=300
)
```

### 2. Type-Safe Models with Pydantic
```python
from oilpriceapi.models import Price, Commodity
from datetime import datetime
from decimal import Decimal

@dataclass
class Price:
    commodity: Commodity
    value: Decimal
    currency: str
    timestamp: datetime
    source: str

    @property
    def formatted(self) -> str:
        return f"${self.value:.2f}"
```

### 3. Intuitive Resource Structure
```python
# Current prices
price = client.prices.get("BRENT_CRUDE_USD")
multiple = client.prices.get_multiple(["BRENT_CRUDE_USD", "WTI_USD"])

# Historical data
history = client.historical.get_daily(
    commodity="BRENT_CRUDE_USD",
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# With pagination
for page in client.historical.iter_pages("BRENT_CRUDE_USD"):
    process_batch(page)
```

### 4. Pandas Integration (First-Class)
```python
# Direct to DataFrame
df = client.prices.to_dataframe(
    commodity="BRENT_CRUDE_USD",
    start="2024-01-01",
    interval="daily"
)

# With technical indicators
df = client.analysis.with_indicators(
    df,
    indicators=["sma_20", "sma_50", "rsi", "bollinger"]
)

# Spread calculation
spread_df = client.analysis.spread(
    "BRENT_CRUDE_USD",
    "WTI_USD",
    start="2024-01-01"
)
```

### 5. Async Support
```python
import asyncio
from oilpriceapi import AsyncClient

async def get_all_prices():
    async with AsyncClient() as client:
        prices = await asyncio.gather(
            client.prices.get("BRENT_CRUDE_USD"),
            client.prices.get("WTI_USD"),
            client.prices.get("NATURAL_GAS_USD"),
        )
        return prices
```

### 6. Smart Caching
```python
# Memory cache (default)
client = OilPriceAPI(cache="memory", cache_ttl=300)

# Redis cache
client = OilPriceAPI(
    cache="redis",
    redis_url="redis://localhost:6379",
    cache_ttl=300
)

# Disable cache
client = OilPriceAPI(cache=None)
```

### 7. Comprehensive Error Handling
```python
from oilpriceapi.exceptions import (
    OilPriceAPIError,
    AuthenticationError,
    RateLimitError,
    DataNotFoundError,
    ServerError
)

try:
    price = client.prices.get("INVALID")
except DataNotFoundError as e:
    print(f"Commodity not found: {e.commodity}")
    print(f"Valid commodities: {e.valid_commodities}")
except RateLimitError as e:
    print(f"Rate limited. Resets in {e.seconds_until_reset}s")
    # SDK automatically retries with exponential backoff
```

### 8. CLI Tool
```bash
# Install with CLI extras
pip install oilpriceapi[cli]

# Get current price
$ oilprice get BRENT_CRUDE_USD
Brent Crude (USD): $71.45 ↑ 1.2% (2024-11-29 10:30:00 UTC)

# Export data
$ oilprice export WTI_USD --start 2024-01-01 --format csv -o wti_2024.csv
✓ Exported 250 records to wti_2024.csv

# Watch prices
$ oilprice watch BRENT_CRUDE_USD --interval 60
```

### 9. Jupyter Notebook Enhancements
```python
# In Jupyter/Colab
from oilpriceapi.jupyter import enable_rich_display
enable_rich_display()

# Now prices display as nice tables
prices = client.prices.get_all()
prices  # Renders as formatted table with sparklines
```

### 10. Testing Support
```python
from oilpriceapi.testing import MockClient

def test_my_strategy():
    client = MockClient()
    client.set_price("BRENT_CRUDE_USD", 75.50)

    result = my_trading_strategy(client)
    assert result.action == "BUY"
```

## 📦 Dependencies

### Core (Required)
```toml
[dependencies]
httpx = ">=0.24.0"          # Modern HTTP client
pydantic = ">=2.0.0"        # Data validation
python-dateutil = ">=2.8.0" # Date parsing
typing-extensions = ">=4.5.0" # Backports for older Python
```

### Optional Extras
```toml
[project.optional-dependencies]
pandas = ["pandas>=1.5.0", "numpy>=1.20.0"]
async = ["aiohttp>=3.8.0"]
cache = ["redis>=4.5.0", "cachetools>=5.3.0"]
cli = ["click>=8.0.0", "rich>=13.0.0"]
dev = ["pytest>=7.0.0", "black>=23.0.0", "mypy>=1.0.0"]
```

## 🚀 Implementation Phases

### Phase 1: Foundation (Week 1)
- [x] Create directory structure
- [ ] Set up packaging (pyproject.toml)
- [ ] Implement basic client
- [ ] Authentication
- [ ] Current prices endpoint
- [ ] Basic error handling
- [ ] Unit tests

### Phase 2: Core Features (Week 2)
- [ ] Historical data endpoints
- [ ] Pagination
- [ ] Rate limit handling
- [ ] Retry logic
- [ ] Integration tests

### Phase 3: Data Science (Week 3)
- [ ] Pandas integration
- [ ] DataFrame conversion
- [ ] Technical indicators
- [ ] Data export functions
- [ ] Jupyter notebook support

### Phase 4: Advanced (Week 4)
- [ ] Async client
- [ ] Caching layer
- [ ] WebSocket support (premium)
- [ ] Performance optimization

### Phase 5: Developer Experience (Week 5)
- [ ] CLI tool
- [ ] Rich documentation
- [ ] Example notebooks
- [ ] Testing utilities
- [ ] Type stubs

### Phase 6: Launch (Week 6)
- [ ] PyPI publication
- [ ] Documentation site
- [ ] Launch blog post
- [ ] Community outreach

## 📊 Quality Requirements

### Code Quality
- 95%+ test coverage
- Type hints on all public APIs
- Passes `mypy --strict`
- Black formatted
- Comprehensive docstrings

### Performance
- <50ms overhead on API calls
- <10MB memory for basic usage
- Supports 1000+ concurrent requests

### Compatibility
- Python 3.8+ (covering 95% of users)
- Windows, macOS, Linux
- Jupyter/Colab compatible
- Works behind corporate proxies

## 🔒 Security

- API keys only in environment variables
- No secrets in logs
- HTTPS enforced
- Input validation
- Rate limit compliance

## 📈 Differentiation

### vs. Alpha Vantage SDK
- ✅ Better: Type hints, async support, caching
- ✅ Better: Oil/energy specific features
- ✅ Better: Pandas integration

### vs. Yahoo Finance
- ✅ Better: Reliable data source
- ✅ Better: Professional support
- ✅ Better: No rate limit surprises

### vs. IEX Cloud
- ✅ Better: Simpler API
- ✅ Better: Free tier friendly
- ✅ Better: Energy focused

## ❓ Open Questions

1. **Python 3.7 support?** - EOL but 8% usage
2. **Plotting library?** - Plotly vs Matplotlib
3. **Streaming data?** - WebSocket vs SSE
4. **SDK versioning?** - Match API or independent?
5. **Docstring style?** - Google vs NumPy

## 🎯 Definition of Done

- [ ] All tests passing (>95% coverage)
- [ ] Documentation complete
- [ ] Published to PyPI
- [ ] 3+ example notebooks
- [ ] Announcement blog post
- [ ] 10+ beta users confirmed working