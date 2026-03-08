#!/bin/bash

# Create GitHub Issues for SDK QA Improvements (Eisenhower Matrix Prioritized)
# Based on QA Assessment from Historical Timeout Issue

set -e

REPO="OilpriceAPI/python-sdk"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Creating QA Improvement Issues for ${REPO}${NC}"
echo -e "${BLUE}Eisenhower Matrix Prioritization${NC}"
echo ""

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
    echo "Install with: sudo apt install gh"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Error: Not authenticated with GitHub CLI${NC}"
    echo "Run: gh auth login"
    exit 1
fi

echo -e "${GREEN}✓ GitHub CLI authenticated${NC}"
echo ""

# Function to create issue
create_issue() {
    local title="$1"
    local body="$2"
    local labels="$3"
    local milestone="$4"

    echo -e "${YELLOW}Creating issue: ${title}${NC}"

    gh issue create \
        --repo "$REPO" \
        --title "$title" \
        --body "$body" \
        --label "$labels" \
        ${milestone:+--milestone "$milestone"} || {
        echo -e "${RED}Failed to create issue: ${title}${NC}"
        return 1
    }

    echo -e "${GREEN}✓ Created${NC}"
    echo ""
}

# =============================================================================
# QUADRANT 1: URGENT & IMPORTANT (Do First) 🔴
# Issues that prevent bugs like the historical timeout from reaching production
# =============================================================================

echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
echo -e "${RED}QUADRANT 1: URGENT & IMPORTANT (Do First)${NC}"
echo -e "${RED}Critical QA gaps that must be fixed before next release${NC}"
echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Issue 1: Integration Tests
create_issue \
"[Q1-P0] Add integration tests against real production API" \
"## Problem

We shipped SDK v1.4.1 with 100% timeout rate on historical queries. Unit tests passed because they used mocked responses.

**Root Cause**: No integration tests calling real API endpoints

## Impact

- **Severity**: P0 - 100% failure rate for core feature
- **Detection**: Customer report (not CI/CD)
- **Time to fix**: 2 hours emergency fix
- **Could have been**: Hundreds of users affected

## Solution

Add integration test suite that calls real production API:

\`\`\`python
# tests/integration/test_real_api_historical.py

@pytest.mark.integration
def test_1_year_query_against_production():
    \"\"\"Test real 1-year historical query.\"\"\"
    client = OilPriceAPI(api_key=os.getenv('TEST_API_KEY'))

    start_time = time.time()
    historical = client.historical.get(
        commodity='WTI_USD',
        start_date='2024-01-01',
        end_date='2024-12-31',
        interval='daily'
    )
    duration = time.time() - start_time

    # Would have caught the timeout bug
    assert duration < 120, f\"Query took {duration}s, exceeds timeout\"
    assert len(historical.data) > 300
\`\`\`

## Test Cases to Add

1. **Endpoint existence tests**
   - Verify all 4 historical endpoints exist (past_day, past_week, past_month, past_year)
   - Verify they return expected data format

2. **Query completion tests**
   - 1 day query completes successfully
   - 1 week query completes successfully
   - 1 month query completes successfully
   - 1 year query completes successfully

3. **Timeout behavior tests**
   - Queries complete within calculated timeout
   - TimeoutError raised if query exceeds timeout

4. **Data validation tests**
   - Correct number of records returned
   - Data format matches expectations
   - Pagination works correctly

## Implementation

\`\`\`bash
# New directory structure
tests/
  integration/
    __init__.py
    conftest.py          # Shared fixtures
    test_historical.py   # Historical endpoint tests
    test_prices.py       # Current price tests
    test_alerts.py       # Alert endpoint tests
\`\`\`

## CI Integration

\`\`\`yaml
# .github/workflows/test.yml
jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run integration tests
        env:
          TEST_API_KEY: \${{ secrets.TEST_API_KEY }}
        run: |
          pytest tests/integration/ --integration -v
\`\`\`

## Acceptance Criteria

- [ ] Integration test suite created in \`tests/integration/\`
- [ ] Tests cover all historical endpoints
- [ ] Tests validate timeout behavior
- [ ] Tests run in CI before every release
- [ ] Test API key configured in GitHub Secrets
- [ ] Tests pass consistently

## Estimated Effort

**Time**: 2-3 hours
**Complexity**: Low (straightforward API calls)
**Blocker**: Need test API key with Production Boost access

## Success Metrics

- Integration tests catch issues that unit tests miss
- Zero P0 bugs ship to production due to SDK issues
- Confidence in releases increases

## Related Issues

- Historical timeout bug (idan@comity.ai)
- QA Assessment: sdks/python/QA_ASSESSMENT_HISTORICAL_TIMEOUT_ISSUE.md

## Notes

This would have caught the historical timeout bug in CI before it reached customers. **Must be completed before next SDK release.**" \
"priority: critical,quadrant: q1,type: testing,technical-debt" \
""

# Issue 2: Performance Tests
create_issue \
"[Q1-P0] Add performance baseline tests for historical queries" \
"## Problem

We don't know how long queries SHOULD take. The historical timeout bug happened because:
- 1 year query takes 67-85 seconds
- SDK timeout was 30 seconds
- No tests validated this mismatch

## Impact

- Can't detect performance regressions
- Can't validate timeout configurations are appropriate
- No baseline for \"what's normal\"

## Solution

Add performance test suite with baseline expectations:

\`\`\`python
# tests/performance/test_historical_benchmarks.py

@pytest.mark.performance
@pytest.mark.parametrize('days,max_duration', [
    (1, 5),      # 1 day query should be <5s
    (7, 15),     # 1 week query should be <15s
    (30, 30),    # 1 month query should be <30s
    (365, 90),   # 1 year query should be <90s
])
def test_query_performance_baseline(prod_client, days, max_duration):
    \"\"\"Verify queries complete within expected time.\"\"\"
    start_date = (datetime.now() - timedelta(days=days)).date()
    end_date = datetime.now().date()

    start_time = time.time()
    response = prod_client.historical.get(
        commodity='WTI_USD',
        start_date=start_date,
        end_date=end_date,
        interval='daily'
    )
    duration = time.time() - start_time

    # FAIL if performance degrades
    assert duration < max_duration, \\
        f\"{days}-day query took {duration:.2f}s, expected <{max_duration}s\"
    assert len(response.data) > 0
\`\`\`

## Test Cases

1. **Response time baselines**
   - 1 day: <5s
   - 1 week: <15s
   - 1 month: <30s
   - 1 year: <90s

2. **Timeout appropriateness**
   - Verify calculated timeout > expected response time
   - Verify timeout has reasonable margin (1.5x response time)

3. **Performance regression detection**
   - Compare with previous run
   - Alert if >20% slower

## Implementation

\`\`\`bash
# Store baseline results
tests/performance/
  baselines/
    historical_response_times.json  # Baseline data
  test_historical_benchmarks.py     # Benchmark tests
  conftest.py                        # Performance fixtures
\`\`\`

## CI Integration

\`\`\`yaml
# Run performance tests weekly (not every commit - too slow)
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:      # Manual trigger

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - name: Run performance tests
        run: pytest tests/performance/ --performance -v

      - name: Compare with baseline
        run: python scripts/compare_performance.py

      - name: Create issue if regression
        if: failure()
        run: gh issue create --title \"Performance Regression Detected\"
\`\`\`

## Acceptance Criteria

- [ ] Performance test suite created
- [ ] Baselines established for all query types
- [ ] Tests fail if performance degrades >20%
- [ ] Tests run weekly in CI
- [ ] Results stored for trend analysis
- [ ] Automated alerts on regression

## Estimated Effort

**Time**: 3-4 hours
**Complexity**: Medium (need baseline data collection)

## Success Metrics

- Detect performance regressions before customers notice
- Validate timeout configurations are appropriate
- Track performance trends over time

## Related

- Issue #1 (Integration tests)
- Historical timeout bug" \
"priority: critical,quadrant: q1,type: testing,technical-debt"

# Issue 3: Pre-Release Validation
create_issue \
"[Q1-P0] Create pre-release validation checklist and automation" \
"## Problem

Current release process:
1. Run unit tests ✅
2. Publish to PyPI ✅
3. Hope nothing breaks ❌

**Result**: Bugs reach production

## Solution

Automated pre-release validation that MUST pass before PyPI publish:

\`\`\`bash
#!/bin/bash
# scripts/pre_release_validation.sh

set -e

echo \"Pre-Release Validation for SDK v\${VERSION}\"
echo \"========================================\"

# 1. Unit tests
echo \"Running unit tests...\"
pytest tests/unit/ -v || exit 1

# 2. Integration tests
echo \"Running integration tests against production API...\"
pytest tests/integration/ --integration -v || exit 1

# 3. Performance tests
echo \"Running performance benchmarks...\"
pytest tests/performance/ --performance -v || exit 1

# 4. Endpoint validation
echo \"Validating all endpoints exist...\"
python scripts/validate_endpoints.py || exit 1

# 5. Build test
echo \"Building package...\"
python -m build || exit 1

# 6. Install and smoke test
echo \"Installing built package...\"
pip install dist/*.whl
python -c \"import oilpriceapi; print(oilpriceapi.__version__)\" || exit 1

echo \"\"
echo \"✅ All validation checks passed\"
echo \"Ready to publish to PyPI\"
\`\`\`

## Pre-Release Checklist

### Code Quality
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All performance tests pass
- [ ] Code coverage >80%
- [ ] No linting errors
- [ ] No type errors (mypy)

### Integration Validation
- [ ] Test against production API
- [ ] All endpoints return expected responses
- [ ] Response times within expected ranges:
  - [ ] 1 day query: <5s
  - [ ] 1 week query: <15s
  - [ ] 1 month query: <30s
  - [ ] 1 year query: <90s
- [ ] Timeout handling works correctly
- [ ] Error handling works correctly

### Documentation
- [ ] CHANGELOG.md updated
- [ ] Version bumped in all locations
- [ ] README.md updated if needed
- [ ] Migration guide if breaking changes
- [ ] Examples tested and working

### Package Build
- [ ] Package builds successfully
- [ ] Wheel installs cleanly
- [ ] Import works after install
- [ ] Version matches expected

### Post-Release Monitoring (24h)
- [ ] PyPI package available
- [ ] Installation works: \`pip install oilpriceapi\`
- [ ] Monitor error rates
- [ ] Check download stats
- [ ] Monitor support tickets

## Automation

\`\`\`yaml
# .github/workflows/pre-release.yml

name: Pre-Release Validation

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to release'
        required: true

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run pre-release validation
        env:
          TEST_API_KEY: \${{ secrets.TEST_API_KEY }}
        run: |
          chmod +x scripts/pre_release_validation.sh
          ./scripts/pre_release_validation.sh

      - name: Create release checklist issue
        if: success()
        run: |
          gh issue create \\
            --title \"Release v\${{ github.event.inputs.version }} - Complete Checklist\" \\
            --body-file .github/release_checklist_template.md \\
            --label \"release\"
\`\`\`

## Acceptance Criteria

- [ ] Pre-release script created and tested
- [ ] Script runs all validation checks
- [ ] Script fails fast on any check failure
- [ ] GitHub workflow created
- [ ] Release checklist template created
- [ ] Documentation updated with release process

## Estimated Effort

**Time**: 2 hours
**Complexity**: Low

## Success Metrics

- Zero releases with P0 bugs
- All releases pass validation before publish
- Release process takes <30 minutes total

## Usage

\`\`\`bash
# Before publishing to PyPI
./scripts/pre_release_validation.sh

# If all checks pass
twine upload dist/*
\`\`\`" \
"priority: critical,quadrant: q1,type: process,automation"

# Issue 4: Monitoring and Alerting
create_issue \
"[Q1-P0] Add monitoring and alerting for SDK health metrics" \
"## Problem

We found out about the historical timeout bug from a customer email. We should have known from monitoring.

**What we don't track**:
- ❌ Timeout rate
- ❌ Response times by endpoint
- ❌ Error rates by SDK version
- ❌ Customer retry patterns

## Impact

- Issues go undetected until customers report
- No early warning system
- Can't measure impact of changes
- Can't track SDK adoption

## Solution

Add comprehensive monitoring and alerting:

### Backend Metrics (Production API)

\`\`\`python
# Track in production API (oilpriceapi-api)

from prometheus_client import Histogram, Counter

# Response time histogram
historical_response_time = Histogram(
    'historical_endpoint_response_seconds',
    'Historical endpoint response time',
    ['endpoint', 'commodity', 'interval'],
    buckets=[1, 5, 10, 30, 60, 90, 120, 180]
)

# Timeout counter
historical_timeout_total = Counter(
    'historical_endpoint_timeout_total',
    'Historical endpoint timeout count',
    ['endpoint', 'sdk_version']
)

# Error counter
sdk_error_total = Counter(
    'sdk_error_total',
    'SDK errors by type',
    ['sdk_version', 'error_type', 'endpoint']
)
\`\`\`

### Alerts

\`\`\`yaml
# prometheus/alerts/sdk_health.yml

groups:
  - name: sdk_health
    interval: 1m
    rules:
      - alert: HistoricalEndpointSlow
        expr: |
          histogram_quantile(0.95,
            rate(historical_endpoint_response_seconds_bucket[5m])
          ) > 60
        for: 5m
        labels:
          severity: warning
          component: sdk
        annotations:
          summary: \"Historical endpoint P95 latency >60s\"
          description: \"95th percentile response time is {{ \$value }}s\"

      - alert: HighTimeoutRate
        expr: |
          rate(historical_endpoint_timeout_total[5m]) /
          rate(historical_endpoint_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
          component: sdk
        annotations:
          summary: \"Historical endpoint timeout rate >5%\"
          description: \"{{ \$value | humanizePercentage }} of requests timing out\"

      - alert: SDKVersionErrorSpike
        expr: |
          rate(sdk_error_total{sdk_version=\"1.4.2\"}[5m]) > 0.10
        for: 5m
        labels:
          severity: critical
          component: sdk
        annotations:
          summary: \"SDK v1.4.2 error rate >10%\"
          description: \"High error rate detected: {{ \$value | humanizePercentage }}\"

      - alert: CustomerRetryPattern
        expr: |
          sum by (user_id, endpoint) (
            rate(api_requests_total[5m])
          ) > 0.5
        for: 2m
        labels:
          severity: warning
          component: sdk
        annotations:
          summary: \"User retrying same query repeatedly\"
          description: \"User {{ \$labels.user_id }} retrying {{ \$labels.endpoint }}\"
\`\`\`

### Dashboard

\`\`\`json
// grafana/dashboards/sdk_health.json

{
  \"title\": \"SDK Health Dashboard\",
  \"panels\": [
    {
      \"title\": \"Historical Endpoint Response Time (P50, P95, P99)\",
      \"targets\": [
        {\"expr\": \"histogram_quantile(0.50, rate(historical_endpoint_response_seconds_bucket[5m]))\"},
        {\"expr\": \"histogram_quantile(0.95, rate(historical_endpoint_response_seconds_bucket[5m]))\"},
        {\"expr\": \"histogram_quantile(0.99, rate(historical_endpoint_response_seconds_bucket[5m]))\"}
      ]
    },
    {
      \"title\": \"Timeout Rate by Endpoint\",
      \"targets\": [
        {\"expr\": \"rate(historical_endpoint_timeout_total[5m]) / rate(historical_endpoint_requests_total[5m])\"}
      ]
    },
    {
      \"title\": \"Error Rate by SDK Version\",
      \"targets\": [
        {\"expr\": \"rate(sdk_error_total[5m]) by (sdk_version)\"}
      ]
    }
  ]
}
\`\`\`

## Implementation Plan

### Phase 1: Backend Instrumentation (oilpriceapi-api)

1. Add Prometheus metrics to historical endpoints
2. Track response times, timeouts, errors
3. Include SDK version in request tracking

### Phase 2: Alerting

1. Deploy Prometheus alert rules
2. Configure Slack notifications
3. Set up on-call rotation for critical alerts

### Phase 3: Dashboards

1. Create Grafana dashboard
2. Add to team's monitoring rotation
3. Review weekly in team meetings

## Acceptance Criteria

- [ ] Prometheus metrics added to production API
- [ ] Alert rules deployed and tested
- [ ] Grafana dashboard created
- [ ] Slack notifications configured
- [ ] Runbook created for responding to alerts
- [ ] Team trained on dashboard usage

## Estimated Effort

**Time**: 4-6 hours
- Backend instrumentation: 2h
- Alert rules: 1h
- Dashboard: 1h
- Testing: 1h
- Documentation: 1h

## Success Metrics

- Detect issues within 5 minutes of occurrence
- Zero customer-reported bugs that weren't detected by monitoring
- Response time to incidents <15 minutes

## Test Plan

\`\`\`bash
# Simulate timeout scenario
curl -X POST http://localhost:9090/api/v1/alerts/test \\
  -d 'alert=HighTimeoutRate'

# Verify alert fires
# Verify Slack notification received
# Verify runbook is followed
\`\`\`

## Related

- Historical timeout bug (would have been detected in 5min)
- Issue #1 (Integration tests)
- Issue #2 (Performance tests)" \
"priority: critical,quadrant: q1,type: monitoring,ops"

# =============================================================================
# QUADRANT 2: NOT URGENT BUT IMPORTANT (Schedule) 🟡
# Important for long-term quality but don't block releases
# =============================================================================

echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}QUADRANT 2: NOT URGENT BUT IMPORTANT (Schedule)${NC}"
echo -e "${YELLOW}Important for long-term quality, schedule for next sprint${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Issue 5: SDK Telemetry
create_issue \
"[Q2-P1] Add opt-in SDK telemetry for proactive issue detection" \
"## Problem

We only learn about SDK issues when customers report them. We're reactive instead of proactive.

## Solution

Add opt-in telemetry to detect issues before customers report them:

\`\`\`python
# oilpriceapi/telemetry.py

class Telemetry:
    \"\"\"Opt-in telemetry for SDK health monitoring.\"\"\"

    def __init__(self, enabled=False):
        self.enabled = enabled or os.getenv('OILPRICEAPI_TELEMETRY') == 'true'

    def log_timeout_event(self, endpoint, timeout, duration):
        \"\"\"Log timeout events.\"\"\"
        if not self.enabled:
            return

        self._send({
            'event': 'timeout',
            'endpoint': endpoint,
            'timeout': timeout,
            'duration': duration,
            'sdk_version': __version__,
            'timestamp': datetime.utcnow().isoformat()
        })

    def log_error(self, error_type, endpoint, message):
        \"\"\"Log error events.\"\"\"
        if not self.enabled:
            return

        self._send({
            'event': 'error',
            'error_type': error_type,
            'endpoint': endpoint,
            'message': message,
            'sdk_version': __version__
        })
\`\`\`

## Usage

\`\`\`python
# Enable telemetry (opt-in)
client = OilPriceAPI(api_key='...', enable_telemetry=True)

# Or via environment variable
export OILPRICEAPI_TELEMETRY=true
\`\`\`

## Data Collected (Privacy-Preserving)

**YES** (collected):
- SDK version
- Endpoint called
- Error types
- Timeout events
- Response times (buckets)
- Python version

**NO** (NOT collected):
- API keys
- Request parameters
- Response data
- User identifying information
- IP addresses

## Benefits

1. **Early detection**: See issues before customers report
2. **Version adoption**: Track which versions are in use
3. **Error patterns**: Identify common failure modes
4. **Performance trends**: Track response times across users

## Implementation

\`\`\`python
# In client.py
class OilPriceAPI:
    def __init__(self, ..., enable_telemetry=False):
        self.telemetry = Telemetry(enabled=enable_telemetry)

    def request(self, method, path, ...):
        start = time.time()
        try:
            response = self._client.request(...)
            duration = time.time() - start

            if duration > timeout:
                self.telemetry.log_timeout_event(path, timeout, duration)

            return response
        except Exception as e:
            self.telemetry.log_error(type(e).__name__, path, str(e))
            raise
\`\`\`

## Acceptance Criteria

- [ ] Telemetry module created
- [ ] Opt-in by default (explicit enable required)
- [ ] Privacy policy documented
- [ ] Data retention policy defined
- [ ] Dashboard created for telemetry data
- [ ] Documentation updated with telemetry info

## Estimated Effort

**Time**: 6-8 hours

## Success Metrics

- Detect issues within 1 hour of first occurrence
- 20%+ of users opt into telemetry
- Identify patterns before customer reports" \
"priority: high,quadrant: q2,type: feature,monitoring"

# Issue 6: Contract Testing
create_issue \
"[Q2-P1] Add contract tests to validate API assumptions" \
"## Problem

SDK makes assumptions about API:
- Endpoints exist
- Response format matches expectations
- Field names are correct

**Risk**: Backend changes can break SDK

## Solution

Add contract tests that validate SDK assumptions against API:

\`\`\`python
# tests/contract/test_api_contracts.py

class TestHistoricalEndpointContract:
    \"\"\"Validate historical endpoint contract.\"\"\"

    def test_past_year_endpoint_exists(self):
        response = requests.get(f'{API_URL}/v1/prices/past_year')
        assert response.status_code != 404

    def test_response_schema_matches_sdk(self):
        response = requests.get(
            f'{API_URL}/v1/prices/past_year',
            params={'commodity': 'WTI_USD'},
            headers={'Authorization': f'Token {TEST_KEY}'}
        )

        data = response.json()

        # Validate structure
        assert 'data' in data
        assert 'prices' in data['data']

        # Validate price schema
        price = data['data']['prices'][0]
        assert 'code' in price
        assert 'price' in price
        assert 'created_at' in price
        assert 'type' in price
        assert 'unit' in price

    def test_pagination_schema(self):
        response = requests.get(
            f'{API_URL}/v1/prices/past_year',
            params={'commodity': 'WTI_USD', 'page': 1, 'per_page': 10}
        )

        data = response.json()

        # Validate pagination metadata
        assert 'meta' in data
        assert 'page' in data['meta']
        assert 'per_page' in data['meta']
        assert 'total' in data['meta']
        assert 'has_next' in data['meta']
\`\`\`

## Run on Backend Deploys

\`\`\`yaml
# In oilpriceapi-api repo: .github/workflows/deploy.yml

jobs:
  deploy:
    steps:
      - name: Deploy to production
        run: ...

      - name: Run SDK contract tests
        run: |
          # Clone SDK repo
          git clone https://github.com/OilpriceAPI/python-sdk.git
          cd python-sdk

          # Run contract tests against deployed API
          pytest tests/contract/ --api-url=https://api.oilpriceapi.com

      - name: Create issue if contract broken
        if: failure()
        run: |
          gh issue create \\
            --title \"SDK Contract Broken by Backend Deploy\" \\
            --label \"bug,priority: critical\"
\`\`\`

## Acceptance Criteria

- [ ] Contract test suite created
- [ ] Tests validate all SDK assumptions
- [ ] Tests run on backend deploys
- [ ] Failures create GitHub issues automatically
- [ ] Documentation for maintaining contracts

## Estimated Effort

**Time**: 4 hours" \
"priority: high,quadrant: q2,type: testing"

# Issue 7: Documentation Improvements
create_issue \
"[Q2-P2] Document SDK performance characteristics and best practices" \
"## Problem

Users don't know:
- How long queries should take
- When to use custom timeouts
- What's \"normal\" performance

## Solution

Add comprehensive performance documentation:

\`\`\`markdown
# Performance Guide

## Expected Response Times

### Historical Queries

| Date Range | Expected Time | Recommended Timeout |
|------------|---------------|---------------------|
| 1 day      | 1-2 seconds   | 30 seconds          |
| 1 week     | 5-10 seconds  | 30 seconds          |
| 1 month    | 15-25 seconds | 60 seconds          |
| 1 year     | 60-90 seconds | 120 seconds         |

### Custom Timeouts

For queries longer than 1 year:

\`\`\`python
# 5 years of data - use 3 minute timeout
historical = client.historical.get(
    commodity='WTI_USD',
    start_date='2020-01-01',
    end_date='2024-12-31',
    timeout=180
)
\`\`\`

## Best Practices

### 1. Use Appropriate Date Ranges

✅ **Good**: Request only data you need
\`\`\`python
# Get last week
historical = client.historical.get(
    commodity='WTI_USD',
    start_date=(datetime.now() - timedelta(days=7)).date(),
    end_date=datetime.now().date()
)
\`\`\`

❌ **Bad**: Request full year when you only need a week
\`\`\`python
# DON'T DO THIS - 10x slower than necessary
historical = client.historical.get(
    commodity='WTI_USD',
    start_date='2024-01-01',
    end_date='2024-12-31'
)
# Then filter: [p for p in historical.data if ...]
\`\`\`

### 2. Use Pagination for Large Datasets

\`\`\`python
# Memory-efficient iteration
for page in client.historical.iter_pages(
    commodity='WTI_USD',
    start_date='2024-01-01',
    per_page=1000
):
    process_batch(page)  # Process 1000 records at a time
\`\`\`

### 3. Choose Appropriate Intervals

\`\`\`python
# Daily interval for year (365 records)
historical = client.historical.get(..., interval='daily')  # Fast

# Raw interval for year (1M+ records)
historical = client.historical.get(..., interval='raw')    # Very slow!
\`\`\`

## Troubleshooting

### Timeout Errors

If you're getting timeout errors:

1. Check your date range - is it larger than expected?
2. Increase timeout for large queries
3. Use pagination instead of getting all data at once
4. Consider using a coarser interval (daily instead of raw)
\`\`\`

## Acceptance Criteria

- [ ] Performance guide added to docs
- [ ] Best practices documented
- [ ] Troubleshooting guide added
- [ ] Examples updated with performance notes
- [ ] README links to performance guide

## Estimated Effort

**Time**: 3 hours" \
"priority: medium,quadrant: q2,type: documentation"

# Issue 8: Canary Releases
create_issue \
"[Q2-P2] Implement canary release process for safer rollouts" \
"## Problem

When we publish to PyPI, all users get the new version immediately. If there's a bug, everyone is affected.

## Solution

Implement canary releases:

1. **Pre-release versions** (test with subset of users)
   \`\`\`bash
   # Publish pre-release to PyPI
   python -m build
   twine upload dist/oilpriceapi-1.4.3rc1*
   \`\`\`

2. **Staged rollout** (gradually increase adoption)
   - Day 1: Release as pre-release (1.4.3rc1)
   - Day 2: Monitor error rates
   - Day 3: Promote to full release (1.4.3) if clean

3. **Rollback capability**
   \`\`\`python
   # If issues detected
   pip install oilpriceapi==1.4.2  # Rollback
   \`\`\`

## Process

\`\`\`bash
# 1. Create release candidate
VERSION=1.4.3rc1 ./scripts/release.sh

# 2. Monitor for 24-48h
- Check error rates
- Monitor support tickets
- Watch telemetry

# 3. Promote or rollback
if no_issues:
    VERSION=1.4.3 ./scripts/release.sh  # Full release
else:
    yank_from_pypi(1.4.3rc1)            # Rollback
\`\`\`

## Acceptance Criteria

- [ ] Pre-release process documented
- [ ] Monitoring during canary period
- [ ] Promotion criteria defined
- [ ] Rollback procedure tested

## Estimated Effort

**Time**: 2 hours" \
"priority: medium,quadrant: q2,type: process"

# Issue 9: Synthetic Monitoring
create_issue \
"[Q2-P2] Add synthetic monitoring with continuous SDK health checks" \
"## Problem

We only test SDK when:
- Someone runs tests manually
- CI runs on commits
- Customers use it in production

**Gap**: No continuous validation that SDK works in production

## Solution

Add synthetic monitoring that runs realistic SDK queries continuously:

\`\`\`python
# monitoring/synthetic/sdk_health_check.py

import schedule
import time
from oilpriceapi import OilPriceAPI

def health_check():
    \"\"\"Run realistic SDK queries.\"\"\"
    client = OilPriceAPI(api_key=MONITOR_KEY)

    checks = [
        ('current_price', lambda: client.prices.get('WTI_USD')),
        ('1_week_historical', lambda: client.historical.get(
            'WTI_USD',
            (datetime.now() - timedelta(days=7)).date(),
            datetime.now().date()
        )),
        ('1_month_historical', lambda: client.historical.get(
            'WTI_USD',
            (datetime.now() - timedelta(days=30)).date(),
            datetime.now().date()
        )),
    ]

    for name, check in checks:
        try:
            start = time.time()
            result = check()
            duration = time.time() - start

            send_metric(f'synthetic.{name}.success', 1)
            send_metric(f'synthetic.{name}.duration', duration)
        except Exception as e:
            send_metric(f'synthetic.{name}.failure', 1)
            send_alert(f'Synthetic check failed: {name}: {e}')

# Run every 5 minutes
schedule.every(5).minutes.do(health_check)
\`\`\`

## Deploy

\`\`\`yaml
# Deploy as cron job or lambda
apiVersion: batch/v1
kind: CronJob
metadata:
  name: sdk-synthetic-monitoring
spec:
  schedule: \"*/5 * * * *\"  # Every 5 minutes
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: health-check
            image: oilpriceapi/sdk-monitor:latest
            env:
            - name: MONITOR_API_KEY
              valueFrom:
                secretKeyRef:
                  name: monitoring-secrets
                  key: api-key
\`\`\`

## Alerts

\`\`\`
ALERT: Synthetic check failure rate >10% over 15min
ALERT: Synthetic check duration >2x baseline
ALERT: Synthetic check not running (missing data)
\`\`\`

## Acceptance Criteria

- [ ] Synthetic monitoring script created
- [ ] Deployed and running every 5 minutes
- [ ] Alerts configured
- [ ] Dashboard shows synthetic check results
- [ ] Runbook for responding to failures

## Estimated Effort

**Time**: 4 hours" \
"priority: medium,quadrant: q2,type: monitoring"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ All QA improvement issues created successfully${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Summary:${NC}"
echo -e "  ${RED}Quadrant 1 (Urgent & Important):${NC} 4 issues - DO FIRST"
echo -e "  ${YELLOW}Quadrant 2 (Important, Not Urgent):${NC} 5 issues - SCHEDULE"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. Review issues in GitHub: https://github.com/${REPO}/issues"
echo -e "  2. Start with Q1 issues (critical, must complete before next release)"
echo -e "  3. Schedule Q2 issues for next sprint"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: Complete Q1 issues before publishing SDK v1.4.3${NC}"
echo ""
