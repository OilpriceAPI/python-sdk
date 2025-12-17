# Changelog

All notable changes to the OilPriceAPI Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.3] - 2025-12-17

### Fixed
- **CRITICAL: Historical Data Returns Wrong Commodity**: Fixed issue where all historical queries returned BRENT_CRUDE_USD regardless of requested commodity
  - Root cause: SDK was sending `commodity` parameter but API expects `by_code` parameter
  - Impact: ALL historical queries since v1.4.0 returned incorrect data
  - Solution: Changed parameter name from `commodity` to `by_code` in historical resource
  - Reported by: Idan (idan@comity.ai)

- **Date Range Parameters Ignored**: Fixed issue where start_date and end_date parameters were completely ignored
  - Root cause: API endpoints were hardcoded to return last week/month/year from current date
  - Impact: Requesting specific date ranges (e.g., Jan 2024) would return current period instead
  - Solution: API now respects start_date and end_date parameters across all historical endpoints
  - This fix was applied to the backend API simultaneously

### Added
- **Strict Commodity Validation**: API now validates commodity codes and returns clear error messages for invalid codes
  - Before: Silently accepted invalid codes like "oijfoijofwijewef" and returned BRENT data
  - After: Returns 400 Bad Request with list of valid codes
  - Error includes link to `/v1/prices/metrics` for full list of valid commodity codes

### Breaking Changes
None - This is a critical bug fix. Existing code will work correctly after update.

### Upgrade Priority
**CRITICAL** - All users of `client.historical.get()` should upgrade immediately. Previous versions return completely wrong data.

## [1.4.2] - 2025-12-16

### Fixed
- **Historical Queries Timeout Issue**: Fixed 100% timeout rate on historical data requests
  - Root cause: SDK was using hardcoded `/v1/prices/past_year` endpoint for all date ranges
  - Solution: Implemented intelligent endpoint selection based on date range
    - 1 day range → `/v1/prices/past_day` endpoint
    - 7 day range → `/v1/prices/past_week` endpoint
    - 30 day range → `/v1/prices/past_month` endpoint
    - 365 day range → `/v1/prices/past_year` endpoint
  - Performance improvement: 7x faster for 1 week queries, 3x faster for 1 month queries

### Added
- **Dynamic Timeout Management**: Automatic timeout adjustment based on query size
  - 1 week queries: 30 seconds (previously 30s, but now uses optimal endpoint)
  - 1 month queries: 60 seconds
  - 1 year queries: 120 seconds (up from 30s - fixes timeout issue)
  - Custom timeout override: `historical.get(..., timeout=180)` for very large queries
- **Per-Request Timeout Override**: Added `timeout` parameter to `client.request()` method
  - Allows fine-grained timeout control for specific requests
  - Historical resource automatically uses appropriate timeouts

### Performance
- 1 week historical queries: **67s → ~10s** (7x faster via `/past_week` endpoint)
- 1 month historical queries: **67s → ~20s** (3x faster via `/past_month` endpoint)
- 1 year historical queries: **Timeout (30s) → Success (67-85s with 120s timeout)**

### Testing
- Added 9 new tests for endpoint selection and timeout handling
- All 20 existing tests pass with new changes
- Test coverage for `historical.py`: 88.68% (up from ~54%)

### Documentation
- Updated `historical.get()` docstring with timeout parameter examples
- Added clear examples for custom timeout usage

### Breaking Changes
None - This is a backwards-compatible bug fix. Existing code will continue to work and will automatically benefit from performance improvements.

## [1.4.0] - 2025-12-15

### Added
- **Price Alerts**: New `client.alerts` resource for automated price monitoring
- **Alert CRUD Operations**: Complete create, read, update, delete operations
- **Webhook Notifications**: HTTPS webhook support for alert triggers
- **Alert Operators**: 5 comparison operators (greater_than, less_than, equals, greater_than_or_equal, less_than_or_equal)
- **Cooldown Periods**: Rate limiting for alert triggers (0-1440 minutes)
- **Webhook Testing**: Test webhook endpoints before creating alerts
- **DataFrame Support**: `alerts.to_dataframe()` - Convert alerts to pandas DataFrames
- New Pydantic models:
  - `PriceAlert` - Alert configuration and status
  - `WebhookTestResponse` - Webhook test results

### Features
- **Comprehensive Validation**: Input validation for all alert parameters
- **Type Safety**: Full Pydantic models with datetime handling
- **Error Handling**: Specific ValidationError exceptions with field details
- **Pandas Integration**: Built-in DataFrame conversion for analysis
- **Documentation**: Complete docstrings with examples

### Supported Endpoints
Now supports **12 endpoints** (up from 7):
- `GET /v1/prices/latest` - Get latest commodity prices
- `GET /v1/prices` - Get historical commodity prices
- `GET /v1/commodities` - Get all commodities metadata
- `GET /v1/commodities/categories` - Get commodity categories
- `GET /v1/commodities/{code}` - Get specific commodity details
- `GET /v1/diesel-prices` - Get state average diesel prices
- `POST /v1/diesel-prices/stations` - Get nearby diesel stations
- `GET /v1/alerts` - List all price alerts (NEW)
- `GET /v1/alerts/{id}` - Get specific alert (NEW)
- `POST /v1/alerts` - Create price alert (NEW)
- `PATCH /v1/alerts/{id}` - Update price alert (NEW)
- `DELETE /v1/alerts/{id}` - Delete price alert (NEW)

### Testing
- Added comprehensive test suite for alerts resource (22 test cases)
- Tests cover all CRUD operations, validation, webhook testing, and DataFrame operations
- 82% coverage of alerts functionality

### Breaking Changes
None - This is a backwards-compatible feature addition.

### Example Usage

```python
from oilpriceapi import OilPriceAPI

client = OilPriceAPI()

# Create a price alert
alert = client.alerts.create(
    name="Brent High Alert",
    commodity_code="BRENT_CRUDE_USD",
    condition_operator="greater_than",
    condition_value=85.00,
    webhook_url="https://your-server.com/webhook",
    cooldown_minutes=60
)

# List all alerts
alerts = client.alerts.list()
for alert in alerts:
    print(f"{alert.name}: {alert.trigger_count} triggers")

# Update alert
client.alerts.update(alert.id, condition_value=90.00)

# Test webhook
test_result = client.alerts.test_webhook("https://your-server.com/webhook")
print(f"Webhook OK: {test_result.success}")

# Get as DataFrame
df = client.alerts.to_dataframe()
```

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