# Integration Tests

Integration tests that call the real OilPriceAPI production endpoints.

## Purpose

These tests would have caught the v1.4.1 historical timeout bug before it reached production. They verify:

1. **Endpoint Selection**: SDK chooses correct endpoints for different date ranges
2. **Timeout Behavior**: Queries complete within expected timeouts
3. **Performance Baselines**: Response times meet expectations
4. **Data Quality**: Returned data is correct and complete

## Setup

### 1. Create `.env` file in project root:

```bash
OILPRICEAPI_KEY=your_api_key_here
OILPRICEAPI_BASE_URL=https://api.oilpriceapi.com
```

You can get a free API key at: https://oilpriceapi.com/auth/signup

### 2. Install test dependencies:

```bash
pip install -e ".[dev]"
```

## Running Tests

### Run all integration tests:
```bash
pytest tests/integration/ -v
```

### Run specific test file:
```bash
# Test historical endpoints (the ones that caught the bug)
pytest tests/integration/test_historical_endpoints.py -v

# Test general API integration
pytest tests/integration/test_live_api.py -v
```

### Skip slow tests:
```bash
pytest tests/integration/ -m "not slow" -v
```

### Run only integration tests (not unit tests):
```bash
pytest -m integration -v
```

### Run performance baseline tests:
```bash
pytest tests/integration/test_historical_endpoints.py::TestHistoricalPerformanceBaselines -v
```

## Test Organization

### `test_historical_endpoints.py` (NEW)
Comprehensive tests for historical data queries that would have caught the v1.4.1 bug:

- **TestHistoricalEndpointSelection**: Verifies SDK selects optimal endpoints
  - 1-day queries use `/v1/prices/past_day`
  - 7-day queries use `/v1/prices/past_week`
  - 30-day queries use `/v1/prices/past_month`
  - 365-day queries use `/v1/prices/past_year`

- **TestHistoricalTimeoutBehavior**: Verifies timeout handling
  - Custom timeouts work correctly
  - Timeouts scale with date range size

- **TestHistoricalPerformanceBaselines**: Establishes performance expectations
  - 1-week queries: <30s
  - 1-month queries: <60s
  - 1-year queries: <120s (the bug that affected Idan)

- **TestHistoricalDataQuality**: Verifies data correctness
  - Complete datasets returned
  - Data matches requested commodity
  - Chronological ordering

### `test_live_api.py` (EXISTING)
General API integration tests:
- Current price queries
- Multi-commodity queries
- Error handling
- Context manager support

## What These Tests Caught

### v1.4.1 Bug: Historical Timeout Issue
**Customer Report**: idan@comity.ai - 100% timeout rate on historical queries

**Root Cause**: SDK hardcoded `/v1/prices/past_year` for all date ranges

**Would Have Been Caught By**:
- `test_7_day_query_uses_past_week_endpoint` - Would have failed (took 67s instead of <30s)
- `test_365_day_query_uses_past_year_endpoint` - Would have failed (timeout at 30s)
- `test_1_year_query_performance_baseline` - Would have failed (timeout)

**Fix**: SDK v1.4.2 with intelligent endpoint selection and dynamic timeouts

## CI/CD Integration

### GitHub Actions Example:

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run integration tests
        env:
          OILPRICEAPI_KEY: ${{ secrets.OILPRICEAPI_KEY }}
        run: pytest tests/integration/ -v -m "not slow"

      - name: Run performance baselines (weekly)
        if: github.event_name == 'schedule'
        env:
          OILPRICEAPI_KEY: ${{ secrets.OILPRICEAPI_KEY }}
        run: pytest tests/integration/ -v -m slow
```

## Best Practices

### 1. Run Before Every Release
```bash
# Pre-release validation
pytest tests/integration/ -v --tb=short
```

### 2. Monitor Performance
Watch for performance regressions:
```bash
pytest tests/integration/test_historical_endpoints.py::TestHistoricalPerformanceBaselines -v -s
```

The `-s` flag shows print statements with timing info.

### 3. Skip Expensive Tests Locally
```bash
# Fast feedback during development
pytest tests/integration/ -m "not slow" -v
```

### 4. Run Full Suite in CI
```bash
# Complete validation before merge
pytest tests/integration/ -v
```

## Expected Results

### Successful Run:
```
tests/integration/test_historical_endpoints.py::TestHistoricalEndpointSelection::test_1_day_query_uses_past_day_endpoint PASSED
tests/integration/test_historical_endpoints.py::TestHistoricalEndpointSelection::test_7_day_query_uses_past_week_endpoint PASSED
✓ 7-day query completed in 8.42s (optimized endpoint)
tests/integration/test_historical_endpoints.py::TestHistoricalEndpointSelection::test_30_day_query_uses_past_month_endpoint PASSED
✓ 30-day query completed in 18.73s (optimized endpoint)
tests/integration/test_historical_endpoints.py::TestHistoricalEndpointSelection::test_365_day_query_uses_past_year_endpoint PASSED
✓ 1-year query completed in 72.15s (within 120s timeout)
```

### Performance Regression Detected:
```
tests/integration/test_historical_endpoints.py::TestHistoricalPerformanceBaselines::test_1_week_query_performance_baseline FAILED
AssertionError: Regression: 1-week query took 65.2s (baseline: <30s)
```

## Troubleshooting

### Tests fail with "OILPRICEAPI_KEY not found"
- Ensure `.env` file exists in project root
- Check `.env` contains `OILPRICEAPI_KEY=your_key`

### Tests timeout
- Check internet connection
- Verify API is accessible: `curl https://api.oilpriceapi.com/health`
- Check API key is valid and has sufficient quota

### Performance tests fail
- API response times can vary based on load
- Run multiple times to confirm consistent regression
- Check if backend deployment or maintenance is in progress

## Adding New Integration Tests

When adding new SDK features, add corresponding integration tests:

1. Create test class in appropriate file
2. Mark with `@pytest.mark.integration`
3. Use `live_client` fixture from conftest.py
4. Add performance assertions (expected response time)
5. Document what bug it would have caught

Example:
```python
@pytest.mark.integration
class TestNewFeature:
    """Test new feature with real API."""

    def test_feature_works(self, live_client):
        """Test feature completes successfully."""
        start_time = time.time()

        result = live_client.new_feature.method()

        duration = time.time() - start_time
        assert result is not None
        assert duration < 10  # Performance expectation
```

## Related Issues

- [#20](https://github.com/OilpriceAPI/python-sdk/issues/20) - Add integration tests against real production API
- [#21](https://github.com/OilpriceAPI/python-sdk/issues/21) - Add performance baseline tests for historical queries

## Resources

- [GitHub Issue #20](https://github.com/OilpriceAPI/python-sdk/issues/20) - Integration tests requirement
- [QA Assessment](../../QA_ASSESSMENT_HISTORICAL_TIMEOUT_ISSUE.md) - What we learned from the timeout bug
- [Root Cause Analysis](../../IDAN_COMITY_HISTORICAL_TIMEOUT_ANALYSIS.md) - Details of the v1.4.1 bug
