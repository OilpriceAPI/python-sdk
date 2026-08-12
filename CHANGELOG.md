# Changelog

All notable changes to the OilPriceAPI Python SDK will be documented in this file.

## [1.12.7] - 2026-08-12

### Fixed

- Removed a nonexistent request-limit bonus claim from sync and async
  usage-attribution header comments.
- Added red-first recursive authored and installed-wheel claim coverage so
  telemetry or application metadata cannot be presented as changing account
  entitlements.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.12.6] - 2026-08-11

### Changed

- Route Brent, WTI, gasoil, and EU carbon futures through the API's
  instrument-generic paths in sync and async clients. Existing venue-slug and
  contract-code inputs remain compatible and normalize to those same paths.

## [1.12.5] - 2026-08-11

### Added

- Document a coverage-gated permit-to-production workflow and package discovery
  keywords for well permits, drilling data, and well production.

### Fixed

- Accept live well-permit filters without a legacy free-form query and unwrap
  the production `{ well_permits, meta }` search response in sync and async
  clients while retaining positional-query compatibility.
- Require the PyPI publisher to verify the complete checksummed artifact set,
  share one package-version parser, scan both workflow filename extensions,
  and allow bounded public-index propagation before release completion.

## [1.12.4] - 2026-08-11

### Fixed

- Reject common fixed request and API-call rate spellings, including prefix,
  suffix, and hyphenated daily/hourly/minute forms, and direct examples to the
  reviewed live product facts.

## [1.12.3] - 2026-08-11

### Fixed

- Match hyphenated free-tier wording and universal catalog claims in every
  readable wheel surface, and replace the remaining packaged docstrings with
  current-account and runtime-response terminology.

## [1.12.2] - 2026-08-11

### Fixed

- Remove stale fixed plan-price, monthly allowance, cadence, uptime, and
  generic real-time claims from documentation and packaged docstrings.
- Recursively validate authored docs and package source, then scan the exact
  installed wheel and PyPI metadata during the release smoke test.

## [1.12.1] - 2026-08-11

### Fixed

- Read release metadata without importing the uninstalled source package, so
  the trusted publisher can validate the exact wheel from a build-only clean
  environment before PyPI upload.

## [1.12.0] - 2026-08-11

### Added

- Add sync and async `client.commodities.search(...)`, backed by the current
  API catalog rather than a bundled commodity-code list.
- Expose bounded, credential-redacted `suggestions` and `invalid_codes` from
  nested invalid-code error responses.

### Changed

- Date-bearing resources now reject malformed or impossible `YYYY-MM-DD`
  strings locally while leaving well-formed range semantics to the API.
- Historical DataFrame helpers now accept a `per_page` value from 1 to 1000
  and fetch all pages automatically. The `client.prices.to_dataframe(...)`
  convenience path forwards the same option for date-range queries.

### Fixed

- Stop retrying exhausted daily, monthly, and trial quota responses. Sync and
  async clients now make one request at a durable quota wall while preserving
  bounded retry behavior for recoverable hourly and ambiguous 429 responses.
- Replace the demo synthetic's fixed catalogue-size assertion with an
  integrity contract for the original core codes and every usable returned
  row. Request, transport, and operating-system failures now fail the monitor
  instead of being converted to skips.
- Preserve each API record's currency and unit in current and historical
  DataFrames instead of labeling a missing currency as USD.
- Remove exact duplicate records introduced by overlapping page boundaries,
  stop safely on empty pages with stale continuation metadata, and return a
  stable schema for empty historical DataFrames.

## [1.11.0] - 2026-07-19

### Changed

- Replaced the PyPI storefront with reviewed source-timestamped wording and
  removed unsupported fixed catalog, traffic, cadence, and entitlement claims.
- Made the canonical first-request snippet fail closed unless symbol, numeric
  value, currency, unit, source, and an exact API timestamp field are present.
- Added a storefront claim guard and corrected the history snippet's declared
  endpoint to match its executable request path.

### Added

- **Well Production Resource (beta)**: `client.well_production` (and async mirror) covering `/v1/well-production*` — `summary()`, `states()`, `state()`, `well()`, `top_producers()`, `cycle_time()`, `cycle_time_cohorts()`. Per-well data is beta and limited to states with collected regulatory data; endpoints are gated on the Drilling Intelligence feature (403 `ENTERPRISE_REQUIRED`). Closes #50.

### Security

- Removed a committed API-key fallback from `tests/sdk_audit_test.py`; the audit script now reads `OILPRICEAPI_KEY`/`OILPRICEAPI_TEST_KEY` from the environment only and skips cleanly when unset.

## [1.10.2] - 2026-07-10

### Changed

- Loosen `source` typing and align examples with the API's masked source labels: the response `source` now returns `market_reporting` for non-government series (government labels like `EIA`/`opec.org` are unchanged). Model `source` fields remain a free `str` (no venue enum); test fixtures no longer use venue names such as `ICE`. See oilpriceapi-api#4175.

## [1.10.1] - 2026-07-03

### Changed

- docs: registry storefront README — hero, "What can you get?" commodity table, and cross-SDK toolbox table so the PyPI page matches the other OilPriceAPI SDKs. No code changes.

## [1.10.0] - 2026-07-03

### Added

- **Analysis Resource (Technical Indicators)**: `client.analysis` with `with_indicators(df, indicators=[...])` DataFrame helper and direct methods `sma()`, `ema()`, `rsi()`, `macd()`, `bollinger_bands()`, `atr()`. Pure pandas/numpy implementation, no new dependencies. Closes #3.

## [1.5.0] - 2026-02-11

### Added

- **Commodities Resource**: `client.commodities.list()`, `get(code)`, `categories()` for commodity catalog discovery
- **Futures Resource**: `client.futures.latest()`, `historical()`, `ohlc()`, `intraday()`, `spreads()`, `curve()`, `continuous()` for futures contract data
- **Storage Resource**: `client.storage.all()`, `cushing()`, `spr()`, `regional()`, `history()` for oil inventory levels
- **Rig Counts Resource**: `client.rig_counts.latest()`, `current()`, `historical()`, `trends()`, `summary()` for Baker Hughes rig count data
- **Bunker Fuels Resource**: `client.bunker_fuels.all()`, `port()`, `compare()`, `spreads()`, `historical()`, `export()` for marine fuel prices
- **Analytics Resource**: `client.analytics.performance()`, `statistics()`, `correlation()`, `trend()`, `spread()`, `forecast()` for price analytics
- **Forecasts Resource**: `client.forecasts.monthly()`, `accuracy()`, `archive()`, `get()` for EIA monthly price forecasts
- **Data Quality Resource**: `client.data_quality.summary()`, `reports()`, `report()` for data quality monitoring
- **Drilling Intelligence Resource**: `client.drilling.latest()`, `summary()`, `trends()`, `frac_spreads()`, `well_permits()`, `duc_wells()`, `completions()`, `wells_drilled()`, `basin()` for drilling activity data
- **Energy Intelligence Resource**: `client.ei` with 7 sub-resources: `rig_counts`, `oil_inventories`, `opec_production`, `drilling_productivity`, `forecasts`, `well_permits`, `frac_focus` for comprehensive EIA data
- **Webhooks Resource**: `client.webhooks.create()`, `list()`, `get()`, `update()`, `delete()`, `test()`, `events()` for webhook management
- **Data Sources Resource**: `client.data_sources.list()`, `get()`, `create()`, `update()`, `delete()`, `test()`, `logs()`, `health()`, `rotate_credentials()` for data connector management
- **Enhanced Alerts**: Added `test()`, `triggers()`, `analytics_history()` methods to existing alerts resource
- **Data Connector Support**: `client.get_data_connector_prices()` for BYOS (Bring Your Own Subscription) prices
- **Telemetry Headers**: `app_url` and `app_name` parameters for API usage attribution

### Fixed

- **Diesel validation**: Empty string state codes now properly rejected with ValidationError

### Testing

- 84 new unit tests added (222 total, 0 failures)
- Test coverage improved from ~40% to 60%
- New test files for all 13 resource modules

### Breaking Changes

None - All new resources are additive. Existing code continues to work unchanged.

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
