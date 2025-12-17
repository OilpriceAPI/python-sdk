# Contract Tests

Contract tests validate that the API behaves as the SDK expects. They catch breaking changes in the API before users encounter them.

## Purpose

**Difference from Integration Tests:**
- **Integration Tests**: Verify SDK functionality works end-to-end
- **Contract Tests**: Verify API contract hasn't changed in breaking ways

**Example**: If the API changes the response format, contract tests fail but integration tests might pass (if SDK auto-adapts).

## What We Test

### 1. Response Format
- Required fields are present
- Field types match expectations
- Data structures are correct

### 2. Endpoint Availability
- All expected endpoints exist
- Endpoints return expected data
- New endpoints documented

### 3. Data Quality
- Values are within expected ranges
- Timestamps are recent
- Dates are in correct order

### 4. Error Handling
- Error responses have expected format
- Error codes are correct
- Error messages are informative

### 5. Backward Compatibility
- Old SDK versions still work
- Deprecated features still function
- Migration path exists for changes

## Running Contract Tests

### Run all contract tests:
```bash
pytest tests/contract/ -v
```

### Run specific test class:
```bash
pytest tests/contract/test_api_contract.py::TestPricesEndpointContract -v
```

### Run only contract tests (not integration):
```bash
pytest -m contract -v
```

### Run before API changes:
```bash
# Establish baseline
pytest tests/contract/ -v > contract_baseline.txt

# After API change, compare
pytest tests/contract/ -v > contract_after.txt
diff contract_baseline.txt contract_after.txt
```

## When to Run

### Before SDK Release
Contract tests should pass to ensure SDK works with current API.

### After API Deployment
Run contract tests against new API version to catch breaking changes.

### During Development
Run when modifying SDK code that depends on API response format.

### In CI/CD
Run on every PR to catch regressions.

## What Breaks Mean

### Contract Test Fails
- **Cause**: API response format changed
- **Action**: Update SDK to handle new format
- **Impact**: Users on old SDK versions may break

### Contract Test Passes But Integration Fails
- **Cause**: SDK logic error
- **Action**: Fix SDK bug
- **Impact**: SDK update needed

### Both Pass
- **Status**: ✅ SDK and API are in sync

## Examples

### Example 1: Field Renamed

**API Change:**
```diff
{
  "data": {
-   "price": 75.50,
+   "value": 75.50,
    "commodity": "WTI_USD"
  }
}
```

**Contract Test Fails:**
```python
def test_price_field_exists(self, live_client):
    price = live_client.prices.get("WTI_USD")
    assert hasattr(price, 'value'), "Missing 'value' field"  # FAILS
```

**Action Required:**
1. Update SDK to use new field name
2. Add backward compatibility if possible
3. Release SDK update
4. Communicate breaking change to users

### Example 2: New Endpoint Added

**API Change:**
- New endpoint: `/v1/prices/past_day`

**Contract Test:**
```python
def test_past_day_endpoint_exists(self, live_client):
    """Verify new past_day endpoint works."""
    history = live_client.historical.get(
        commodity="WTI_USD",
        start_date=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        end_date=datetime.now().strftime("%Y-%m-%d")
    )
    assert history is not None  # Should work
```

**Action Required:**
1. Add SDK support for new endpoint
2. Update documentation
3. Release SDK update (non-breaking)

### Example 3: Response Time Increased

**API Change:**
- Historical queries now take 90s instead of 60s

**Contract Test Fails:**
```python
def test_query_completes_in_time(self, live_client):
    start = time.time()
    history = live_client.historical.get(...)
    duration = time.time() - start
    assert duration < 120, f"Query took {duration}s"  # PASSES (within timeout)
```

**Action Required:**
1. Investigate if timeout adjustment needed
2. Update performance baselines
3. Consider if SDK timeout should increase

## Best Practices

### 1. Test API Contract, Not Implementation
```python
# Good: Tests contract
assert hasattr(price, 'value'), "value field required by contract"

# Bad: Tests implementation detail
assert price.value == 75.50, "should be exactly 75.50"  # Too specific
```

### 2. Test Required Fields Only
```python
# Good: Tests required fields
assert hasattr(price, 'commodity')
assert hasattr(price, 'value')

# Bad: Tests optional fields as required
assert hasattr(price, 'source')  # Might be optional
```

### 3. Test Ranges, Not Exact Values
```python
# Good: Tests reasonable range
assert 0 < price.value < 1000000

# Bad: Tests exact value
assert price.value == 75.50  # Will fail constantly
```

### 4. Document Why Each Test Exists
```python
def test_timestamps_are_timezone_aware(self, live_client):
    """
    Verify timestamps include timezone info.

    Why: SDK v1.0 assumed UTC but didn't enforce it.
    Contract: All timestamps must be timezone-aware.
    Breaking: If API returns naive datetimes, SDK breaks.
    """
```

## Contract Test Checklist

When adding new SDK features, add contract tests for:

- [ ] New endpoints exist
- [ ] Response format is documented
- [ ] Required fields are present
- [ ] Data types match expectations
- [ ] Error cases return expected codes
- [ ] Backward compatibility maintained
- [ ] Performance within acceptable range

## CI/CD Integration

### GitHub Actions Example:

```yaml
name: Contract Tests

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  push:
    branches: [main]
  pull_request:

jobs:
  contract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run contract tests
        env:
          OILPRICEAPI_KEY: ${{ secrets.OILPRICEAPI_KEY }}
        run: pytest tests/contract/ -v --tb=short

      - name: Notify on failure
        if: failure() && github.event_name == 'schedule'
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
            -H 'Content-Type: application/json' \
            -d '{"text":"Contract tests failed! API may have changed."}'
```

## Troubleshooting

### All contract tests fail
- **Cause**: API is down or unreachable
- **Check**: API health endpoint
- **Action**: Wait for API to recover

### Some tests fail after API deployment
- **Cause**: Breaking API change
- **Check**: API changelog
- **Action**: Update SDK, release new version

### Tests flaky (sometimes pass, sometimes fail)
- **Cause**: API returns inconsistent data
- **Check**: Test on multiple commodities
- **Action**: Make tests more resilient or fix API

### Tests pass locally but fail in CI
- **Cause**: Different API keys or environments
- **Check**: CI environment variables
- **Action**: Use same test API key

## Related

- [Integration Tests](../integration/README.md)
- [GitHub Issue #25](https://github.com/OilpriceAPI/python-sdk/issues/25)
- [API Documentation](https://docs.oilpriceapi.com)
