#!/bin/bash

# Script to create GitHub issues for Python SDK development
# Run from the repository root

REPO="oilpriceapi-api"  # Update with your actual repo

echo "Creating GitHub Issues for Python SDK Development..."

# Epic Issue
gh issue create \
  --title "🐍 Epic: Python SDK Development" \
  --body "## Overview
Build a comprehensive Python SDK for OilPriceAPI to improve developer experience and increase adoption.

## Goal
Create a best-in-class Python SDK that makes OilPriceAPI the easiest commodity price API to integrate.

## Timeline
6 weeks from start to PyPI publication

## Success Metrics
- 1000+ installs in first month
- <15 minute integration time
- 95%+ test coverage
- <5% support tickets

## Phases
1. **Week 1**: Foundation & Core Client
2. **Week 2**: Historical Data & Robustness
3. **Week 3**: Data Science Integration
4. **Week 4**: Advanced Features
5. **Week 5**: Polish & Developer Experience
6. **Week 6**: Launch Preparation

## Related Issues
This epic will be broken down into individual feature issues." \
  --label "epic,enhancement,python-sdk" \
  --repo $REPO

# Foundation Issues
gh issue create \
  --title "🏗️ Setup: Initialize Python SDK project structure" \
  --body "## Description
Create the initial project structure for the Python SDK.

## Tasks
- [ ] Create directory structure under sdks/python/
- [ ] Set up pyproject.toml with modern Python packaging
- [ ] Configure .gitignore for Python
- [ ] Create initial README.md
- [ ] Set up pre-commit hooks

## Acceptance Criteria
- Project structure matches PRD
- Can run \`pip install -e .\` successfully
- Pre-commit hooks working

## Files to Create
\`\`\`
sdks/python/
├── oilpriceapi/
│   ├── __init__.py
│   └── client.py
├── tests/
│   └── __init__.py
├── pyproject.toml
├── README.md
└── .gitignore
\`\`\`" \
  --label "setup,python-sdk,week-1" \
  --repo $REPO

gh issue create \
  --title "🔧 CI/CD: Configure GitHub Actions for Python SDK" \
  --body "## Description
Set up continuous integration and deployment pipelines.

## Tasks
- [ ] Create test workflow (pytest, coverage)
- [ ] Add linting workflow (black, flake8, mypy)
- [ ] Set up PyPI publish workflow
- [ ] Configure dependabot
- [ ] Add badge to README

## Acceptance Criteria
- Tests run on every PR
- Coverage reported to PR
- Auto-publish to PyPI on release tag
- Linting enforced

## Workflow Files
- .github/workflows/python-test.yml
- .github/workflows/python-lint.yml
- .github/workflows/python-publish.yml" \
  --label "devops,python-sdk,week-1" \
  --repo $REPO

gh issue create \
  --title "💻 Core: Implement base client class" \
  --body "## Description
Create the main OilPriceAPIClient class with configuration.

## Tasks
- [ ] Create client.py with base class
- [ ] Add configuration management
- [ ] Implement authentication
- [ ] Add HTTP client wrapper (httpx)
- [ ] Support environment variables
- [ ] Add logging

## Example Usage
\`\`\`python
from oilpriceapi import OilPriceAPI

# From environment
client = OilPriceAPI()

# Direct key
client = OilPriceAPI(api_key='key')

# With config
client = OilPriceAPI(
    api_key='key',
    timeout=30,
    max_retries=3
)
\`\`\`

## Acceptance Criteria
- Client initializes properly
- API key from env var works
- Configuration is validated
- Type hints complete" \
  --label "feature,python-sdk,week-1" \
  --repo $REPO

# Core Feature Issues
gh issue create \
  --title "💰 Feature: Implement current prices endpoint" \
  --body "## Description
Add support for getting current commodity prices.

## Tasks
- [ ] Create resources/prices.py
- [ ] Implement get() method
- [ ] Add get_multiple() method
- [ ] Create Price model with Pydantic
- [ ] Add comprehensive tests
- [ ] Add type hints

## API Design
\`\`\`python
# Single price
price = client.prices.get('BRENT_CRUDE_USD')
print(f'Brent: \${price.value}')

# Multiple prices
prices = client.prices.get_multiple([
    'BRENT_CRUDE_USD',
    'WTI_USD',
    'NATURAL_GAS_USD'
])
\`\`\`

## Acceptance Criteria
- Returns typed Price objects
- Handles errors gracefully
- IDE autocomplete works
- 100% test coverage" \
  --label "feature,python-sdk,week-1" \
  --repo $REPO

gh issue create \
  --title "📈 Feature: Add historical data retrieval" \
  --body "## Description
Implement historical price data access with intervals.

## Tasks
- [ ] Create resources/historical.py
- [ ] Add date range support
- [ ] Implement interval selection
- [ ] Handle pagination transparently
- [ ] Add iterator support
- [ ] Create examples

## API Design
\`\`\`python
# Get historical data
history = client.historical.get(
    commodity='BRENT_CRUDE_USD',
    start_date='2024-01-01',
    end_date='2024-12-31',
    interval='daily'
)

# Iterate through pages
for page in client.historical.iter_pages('WTI_USD'):
    process_batch(page)
\`\`\`

## Acceptance Criteria
- Handles any date range
- Pagination is transparent
- Memory efficient
- Supports all intervals" \
  --label "feature,python-sdk,week-2" \
  --repo $REPO

# Data Science Issues
gh issue create \
  --title "🐼 Feature: Pandas DataFrame integration" \
  --body "## Description
First-class pandas support for all data endpoints.

## Tasks
- [ ] Create integrations/pandas_ext.py
- [ ] Add to_dataframe() method
- [ ] Optimize dtypes
- [ ] Handle datetime index
- [ ] Support multi-commodity DataFrames
- [ ] Create jupyter notebook example

## API Design
\`\`\`python
# Direct to DataFrame
df = client.prices.to_dataframe(
    commodity='BRENT_CRUDE_USD',
    start='2024-01-01',
    interval='daily'
)

# Multi-commodity
df = client.prices.to_dataframe(
    commodities=['BRENT_CRUDE_USD', 'WTI_USD'],
    start='2024-01-01'
)

# With proper types
assert df.index.dtype == 'datetime64[ns]'
assert df['price'].dtype == 'float64'
\`\`\`

## Acceptance Criteria
- Returns properly typed DataFrame
- Datetime index by default
- Works without pandas (graceful degradation)
- Handles timezones correctly" \
  --label "feature,python-sdk,data-science,week-3" \
  --repo $REPO

gh issue create \
  --title "📊 Feature: Add technical indicators" \
  --body "## Description
Built-in technical analysis indicators for price data.

## Tasks
- [ ] Create analysis/indicators.py
- [ ] Implement SMA (20, 50, 200)
- [ ] Add EMA calculation
- [ ] Implement RSI
- [ ] Add Bollinger Bands
- [ ] Create spread calculator
- [ ] Add MACD

## API Design
\`\`\`python
# Add indicators to DataFrame
df = client.analysis.with_indicators(
    df,
    indicators=['sma_20', 'sma_50', 'rsi', 'bollinger']
)

# Calculate spread
spread = client.analysis.spread(
    'BRENT_CRUDE_USD',
    'WTI_USD',
    start='2024-01-01'
)
\`\`\`

## Acceptance Criteria
- Calculations match reference implementations
- Handles edge cases (insufficient data)
- Well documented
- Includes examples" \
  --label "feature,python-sdk,data-science,week-3" \
  --repo $REPO

# Advanced Features
gh issue create \
  --title "⚡ Feature: Async client implementation" \
  --body "## Description
Full async/await support for high-performance applications.

## Tasks
- [ ] Create async_client.py
- [ ] Implement all endpoints as async
- [ ] Add connection pooling
- [ ] Support context manager
- [ ] Add concurrency examples
- [ ] Benchmark performance

## API Design
\`\`\`python
import asyncio
from oilpriceapi import AsyncClient

async def get_all_prices():
    async with AsyncClient() as client:
        prices = await asyncio.gather(
            client.prices.get('BRENT_CRUDE_USD'),
            client.prices.get('WTI_USD'),
            client.prices.get('NATURAL_GAS_USD'),
        )
        return prices

prices = asyncio.run(get_all_prices())
\`\`\`

## Acceptance Criteria
- All endpoints available as async
- Proper connection cleanup
- 10x performance for bulk operations
- No memory leaks" \
  --label "feature,python-sdk,performance,week-4" \
  --repo $REPO

gh issue create \
  --title "💾 Feature: Implement caching layer" \
  --body "## Description
Smart caching to reduce API calls and improve performance.

## Tasks
- [ ] Create utils/cache.py
- [ ] Implement memory cache
- [ ] Add Redis cache support
- [ ] Configure TTL per endpoint
- [ ] Add cache invalidation
- [ ] Add cache metrics

## API Design
\`\`\`python
# Memory cache
client = OilPriceAPI(
    cache='memory',
    cache_ttl=300  # 5 minutes
)

# Redis cache
client = OilPriceAPI(
    cache='redis',
    redis_url='redis://localhost:6379',
    cache_ttl=300
)

# Check cache stats
stats = client.cache_stats()
print(f'Hit rate: {stats.hit_rate:.2%}')
\`\`\`

## Acceptance Criteria
- Reduces duplicate API calls
- Configurable TTL
- Thread-safe
- Metrics available" \
  --label "feature,python-sdk,performance,week-4" \
  --repo $REPO

# Developer Experience
gh issue create \
  --title "🛠️ Feature: Create CLI tool" \
  --body "## Description
Command-line interface for quick price checks and exports.

## Tasks
- [ ] Create cli/commands.py
- [ ] Implement 'get' command
- [ ] Add 'export' command
- [ ] Create 'watch' mode
- [ ] Add Rich formatting
- [ ] Support JSON output

## Commands
\`\`\`bash
# Get current price
$ oilprice get BRENT_CRUDE_USD
Brent Crude (USD): \$71.45 ↑ 1.2%

# Export data
$ oilprice export WTI_USD --start 2024-01-01 --format csv -o wti.csv
✓ Exported 250 records

# Watch prices
$ oilprice watch BRENT_CRUDE_USD --interval 60

# JSON output
$ oilprice get WTI_USD --json | jq .
\`\`\`

## Acceptance Criteria
- Intuitive commands
- Beautiful output
- Fast response
- Helpful error messages" \
  --label "feature,python-sdk,cli,week-5" \
  --repo $REPO

gh issue create \
  --title "🧪 Testing: Create mock client and fixtures" \
  --body "## Description
Testing utilities for SDK users.

## Tasks
- [ ] Create testing/mock.py
- [ ] Implement MockClient
- [ ] Add price fixtures
- [ ] Create scenario fixtures (volatile, stable, crash)
- [ ] Add assertion helpers
- [ ] Document testing patterns

## API Design
\`\`\`python
from oilpriceapi.testing import MockClient

def test_my_strategy():
    client = MockClient()
    client.set_price('BRENT_CRUDE_USD', 75.50)

    result = my_trading_strategy(client)
    assert result.action == 'BUY'

# Load scenario
client.load_scenario('volatile_market')
\`\`\`

## Acceptance Criteria
- Easy to mock
- Realistic data
- Good examples
- Clear documentation" \
  --label "testing,python-sdk,week-5" \
  --repo $REPO

gh issue create \
  --title "📚 Docs: Create comprehensive documentation" \
  --body "## Description
Complete documentation and examples.

## Tasks
- [ ] Write getting started guide
- [ ] Create API reference (autodoc)
- [ ] Add 5+ example notebooks
- [ ] Create troubleshooting guide
- [ ] Add migration guide from raw API
- [ ] Create video tutorial

## Documentation Structure
\`\`\`
docs/
├── getting-started.md
├── api-reference.md
├── examples.md
├── troubleshooting.md
└── migration.md

examples/
├── quickstart.ipynb
├── data_analysis.ipynb
├── trading_signals.ipynb
├── async_example.py
└── cli_examples.md
\`\`\`

## Acceptance Criteria
- Covers all features
- Examples run without errors
- Clear and concise
- Good SEO" \
  --label "documentation,python-sdk,week-5" \
  --repo $REPO

# Launch Issues
gh issue create \
  --title "🚀 Launch: Publish to PyPI" \
  --body "## Description
Release version 1.0.0 to PyPI.

## Tasks
- [ ] Final security review
- [ ] Performance profiling
- [ ] Update CHANGELOG
- [ ] Create release notes
- [ ] Tag version 1.0.0
- [ ] Publish to TestPyPI first
- [ ] Publish to PyPI
- [ ] Verify installation

## Release Checklist
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Examples working
- [ ] No security issues
- [ ] Version bumped
- [ ] CHANGELOG updated

## Acceptance Criteria
- \`pip install oilpriceapi\` works
- All examples run
- Documentation linked
- Announcement ready" \
  --label "release,python-sdk,week-6" \
  --repo $REPO

gh issue create \
  --title "📣 Launch: Create announcement content" \
  --body "## Description
Marketing and documentation for launch.

## Tasks
- [ ] Write blog post
- [ ] Create demo video
- [ ] Update main documentation
- [ ] Prepare social media posts
- [ ] Email beta users
- [ ] Submit to Python Weekly
- [ ] Post on relevant subreddits

## Content Checklist
- [ ] Blog post (1500 words)
- [ ] Demo video (3-5 min)
- [ ] Twitter thread
- [ ] LinkedIn post
- [ ] Reddit posts (r/Python, r/algotrading)
- [ ] Hacker News submission

## Acceptance Criteria
- Blog post published
- Video uploaded
- 100+ views day one
- 10+ GitHub stars" \
  --label "marketing,python-sdk,week-6" \
  --repo $REPO

echo "✅ All GitHub issues created successfully!"
echo "View them at: https://github.com/$REPO/issues?q=label:python-sdk"