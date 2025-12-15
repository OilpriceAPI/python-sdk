# Changelog

All notable changes to the OilPriceAPI Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2025-12-15

### Added
- **Diesel Prices Support**: New `client.diesel` resource for diesel price data
- **State Average Diesel Prices**: `diesel.get_price(state)` - Get EIA state-level diesel averages (free tier)
- **Station-Level Diesel Pricing**: `diesel.get_stations(lat, lng, radius)` - Get nearby diesel stations with current prices from Google Maps (paid tiers)
- **Diesel DataFrame Support**: `diesel.to_dataframe()` - Convert diesel data to pandas DataFrames
- New Pydantic models:
  - `DieselPrice` - State average diesel price data
  - `DieselStation` - Individual diesel station with pricing
  - `DieselStationsResponse` - Response from stations endpoint
  - `DieselRegionalAverage` - Regional average for comparison
  - `DieselSearchArea` - Search area details
  - `DieselStationsMetadata` - Query metadata

### Features
- **Input Validation**: Comprehensive validation for coordinates, state codes, and radius
- **Error Handling**: Specific errors for tier restrictions (403) and rate limits (429)
- **Type Safety**: Full Pydantic models for all diesel operations
- **Pandas Integration**: Built-in DataFrame conversion for analysis
- **Documentation**: Complete docstrings with examples

### Supported Endpoints
Now supports **7 endpoints** (up from 5):
- `GET /v1/prices/latest` - Get latest commodity prices
- `GET /v1/prices` - Get historical commodity prices
- `GET /v1/commodities` - Get all commodities metadata
- `GET /v1/commodities/categories` - Get commodity categories
- `GET /v1/commodities/{code}` - Get specific commodity details
- `GET /v1/diesel-prices` - Get state average diesel prices (NEW)
- `POST /v1/diesel-prices/stations` - Get nearby diesel stations (NEW)

### Testing
- Added comprehensive test suite for diesel resource (18 test cases)
- Tests cover input validation, error handling, and DataFrame operations
- 100% coverage of diesel functionality

### Breaking Changes
None - This is a backwards-compatible feature addition.

### Example Usage

```python
from oilpriceapi import OilPriceAPI

client = OilPriceAPI()

# State average (free tier)
ca_price = client.diesel.get_price("CA")
print(f"California diesel: ${ca_price.price:.2f}/gallon")

# Nearby stations (paid tiers)
result = client.diesel.get_stations(lat=37.7749, lng=-122.4194)
cheapest = min(result.stations, key=lambda s: s.diesel_price)
print(f"Cheapest: {cheapest.name} at {cheapest.formatted_price}")

# DataFrame analysis
df = client.diesel.to_dataframe(states=["CA", "TX", "NY", "FL"])
print(df[["state", "price", "updated_at"]])
```

## [1.0.0] - 2025-09-29

### Added
- 🎉 Initial release of OilPriceAPI Python SDK
- ✅ Synchronous client (`OilPriceAPI`)
- ✅ Asynchronous client (`AsyncOilPriceAPI`)
- ✅ Type-safe models with Pydantic
- ✅ Current price operations (`client.prices.get()`)
- ✅ Historical data operations (`client.historical.get()`)
- ✅ Pandas DataFrame integration (`to_dataframe()`)
- ✅ Visualization module with Tufte-style charts
- ✅ Automatic retry logic with exponential backoff
- ✅ Rate limit handling
- ✅ Comprehensive error handling
- ✅ Context manager support (`with` statements)
- ✅ Environment variable configuration
- ✅ Full type hints for IDE autocomplete
- ✅ Documentation and examples

### Features
- **Current Prices**: Get latest commodity prices
- **Historical Data**: Fetch past prices with flexible date ranges
- **Multi-commodity**: Support for Brent, WTI, Natural Gas, and more
- **Pagination**: Automatic handling of large datasets
- **Data Export**: Convert to pandas DataFrames for analysis
- **Async Support**: High-performance async/await operations
- **Visualization**: Built-in charting with matplotlib
- **Type Safety**: Full Pydantic validation

### Security
- Environment variable-based API key management
- No hardcoded credentials
- HTTPS-only communication
- Safe error messages that don't leak secrets

### Documentation
- Comprehensive README with examples
- API reference documentation
- Security policy (SECURITY.md)
- Contributing guidelines (CONTRIBUTING.md)
- Example scripts and notebooks

### Supported Python Versions
- Python 3.8+
- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12

---

## [Unreleased]

### Planned
- CLI tool (`oilprice` command)
- WebSocket support for real-time prices
- Advanced caching with Redis
- Technical indicators (RSI, MACD, Bollinger Bands)
- More visualization styles
- Jupyter notebook widgets

---

## Release Notes

### How to Upgrade

```bash
# From PyPI
pip install --upgrade oilpriceapi

# From source
pip install -e ".[dev]"
```

### Breaking Changes
None - this is the initial release.

### Deprecations
None.

### Migration Guide
N/A for initial release.

---

## Links
- [PyPI Package](https://pypi.org/project/oilpriceapi/)
- [GitHub Repository](https://github.com/oilpriceapi/python-sdk)
- [Documentation](https://docs.oilpriceapi.com/sdk/python)
- [API Documentation](https://docs.oilpriceapi.com)
- [Website](https://oilpriceapi.com)