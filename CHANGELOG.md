# Changelog

All notable changes to the OilPriceAPI Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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