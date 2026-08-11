# OilPriceAPI Python SDK

Official Python client for source-timestamped OilPriceAPI energy data. It
provides typed synchronous and asynchronous clients, bounded retries, explicit
errors, optional pandas helpers, and executable example manifests.

[![PyPI version](https://img.shields.io/pypi/v/oilpriceapi)](https://pypi.org/project/oilpriceapi/)
[![Python](https://img.shields.io/pypi/pyversions/oilpriceapi.svg)](https://pypi.org/project/oilpriceapi/)
[![Tests](https://github.com/OilpriceAPI/python-sdk/actions/workflows/test.yml/badge.svg)](https://github.com/OilpriceAPI/python-sdk/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

Mutable offer, catalog, freshness, entitlement, and data-rights wording is
governed by the reviewed
[`product-facts.json`](https://api.oilpriceapi.com/product-facts.json) contract.
Latest available values include source timestamps; cadence, history depth, and
access vary by source, market hours, dataset, and account entitlement.

## Install

```bash
python -m pip install oilpriceapi
```

Optional extras are installed only when the application uses them:

```bash
python -m pip install "oilpriceapi[pandas]"
python -m pip install "oilpriceapi[stream]"
```

An installed helper does not imply that every dataset or workflow is enabled
for an account. Confirm access in the current API response and documentation.

## Authenticate

Create an API key in the [OilPriceAPI dashboard](https://www.oilpriceapi.com/auth/signup)
and provide it through the environment. Do not put a key in source code, a
notebook cell, a URL, logs, screenshots, or issue text.

```bash
export OILPRICEAPI_KEY="your-key-from-the-dashboard"
```

The API authentication header is `Authorization: Token YOUR_API_KEY`.

## First Request With Source Context

The canonical first request is
`GET /v1/prices/latest?by_code=BRENT_CRUDE_USD`. This example fails closed if
the response omits the context needed to interpret the value:

```python
import math
import os

from oilpriceapi import OilPriceAPI

with OilPriceAPI(api_key=os.environ["OILPRICEAPI_KEY"], max_retries=1) as client:
    payload = client.request(
        "GET",
        "/v1/prices/latest",
        params={"by_code": "BRENT_CRUDE_USD"},
        timeout=30,
    )

record = payload.get("data")
if not isinstance(record, dict):
    raise RuntimeError("EMPTY_RESPONSE: no price record returned")

price = record.get("price")
if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price):
    raise RuntimeError("MALFORMED_RESPONSE: price is not a finite number")

source = record.get("source")
metadata = record.get("metadata")
if not source and isinstance(metadata, dict):
    source = metadata.get("source")

timestamp_field = next(
    (
        field
        for field in ("as_of", "source_timestamp", "created_at", "updated_at")
        if isinstance(record.get(field), str) and record[field].strip()
    ),
    None,
)

required_text = {
    "code": record.get("code"),
    "currency": record.get("currency"),
    "unit": record.get("unit"),
    "source": source,
}
if timestamp_field is None or any(
    not isinstance(value, str) or not value.strip()
    for value in required_text.values()
):
    raise RuntimeError("MALFORMED_RESPONSE: source context is incomplete")

print(
    {
        **required_text,
        "price": float(price),
        "api_timestamp_field": timestamp_field,
        "api_timestamp": record[timestamp_field],
        "freshness": record.get("data_status") or record.get("freshness"),
    }
)
```

The reviewed standalone form is
[`examples/snippets/latest_price.py`](examples/snippets/latest_price.py). CI
executes it against production-shaped fixtures and publishes its code and
checksum in the release snippet manifest.

## Typed Client

For applications that only need the normalized core fields:

```python
import os

from oilpriceapi import OilPriceAPI

with OilPriceAPI(api_key=os.environ["OILPRICEAPI_KEY"]) as client:
    price = client.prices.get("BRENT_CRUDE_USD")

print(
    price.commodity,
    price.value,
    price.currency,
    price.unit,
    price.timestamp.isoformat(),
)
```

Use the raw first-request pattern when downstream logic requires the exact
source and timestamp-field semantics from the API response.

## Permit To Production

Well-level production coverage is narrower than permit coverage. Check the
live coverage response before following a permit into monthly production:

```python
import os

from oilpriceapi import OilPriceAPI
from oilpriceapi.exceptions import DataNotFoundError

with OilPriceAPI(api_key=os.environ["OILPRICEAPI_KEY"]) as client:
    summary = client.well_production.summary()
    coverage = summary.get("coverage")
    if not isinstance(coverage, dict):
        raise RuntimeError("MALFORMED_RESPONSE: well-production coverage is missing")

    covered_state_values = coverage.get("well_level_states_with_data")
    if not isinstance(covered_state_values, list):
        raise RuntimeError("MALFORMED_RESPONSE: well-level state coverage is missing")
    covered_states = set(covered_state_values)
    permits = client.ei.well_permits.search(states="TX", well_name="Eagle")

    for permit in permits:
        api_number = permit.get("api_number")
        if (
            permit.get("state_code") not in covered_states
            or not isinstance(api_number, str)
            or len(api_number) != 14
            or not api_number.isascii()
            or not api_number.isdigit()
        ):
            continue

        try:
            production = client.well_production.well(api_number)
        except DataNotFoundError:
            continue
        well = permit.get("well")
        well_name = well.get("name") if isinstance(well, dict) else None
        print(well_name, production.get("data", []))
```

An empty permit search or production history is a valid data state. Do not
infer broader well-level coverage from the presence of permit data or an SDK
helper; dataset and account availability come from the current API response.

## Complete pandas DataFrames

Install the optional pandas support, then request a historical DataFrame:

```python
df = client.historical.to_dataframe(
    commodity="BRENT_CRUDE_USD",
    start="2026-01-01",
    end="2026-06-30",
    per_page=500,
)
```

`to_dataframe()` fetches every page automatically. `per_page` controls the
request page size, not the total result size, and must be an integer from 1 to
1000. The DataFrame preserves each API row's `currency` and `unit`; a missing
currency remains missing rather than being labeled USD. Exact records repeated
by an overlapping page boundary are returned once, while distinct records are
retained. Empty results have a stable schema with a `date` index.

The same `per_page` behavior applies to date-range queries through
`client.prices.to_dataframe(...)`. See the
[DataFrames and pagination guide](docs/DATAFRAMES.md) for the complete
contract.

## Dates and Commodity Codes

Date strings must be real calendar dates in exact `YYYY-MM-DD` form. Malformed
values are rejected before an API request, while well-formed ranges are still
validated authoritatively by the server.

Search the current API catalog instead of maintaining a local code list:

```python
matches = client.commodities.search("brent crude", limit=5)
print([commodity["code"] for commodity in matches])
```

Invalid-code API responses expose sanitized recovery values through
`error.suggestions` and `error.invalid_codes`. See the
[dates and commodity-code guide](docs/CODE_GUIDANCE.md) for sync/async examples
and failure behavior.

## Recovery

The package exposes typed errors for the customer-recoverable boundaries:

```python
from oilpriceapi import (
    AuthenticationError,
    OilPriceAPIError,
    RateLimitError,
    TimeoutError,
)

try:
    price = client.prices.get("BRENT_CRUDE_USD")
except AuthenticationError:
    print("Replace the missing, expired, or revoked API key.")
except RateLimitError as error:
    print("Wait for the API-provided reset window.", error.seconds_until_reset)
except TimeoutError:
    print("Retry once, then check https://status.oilpriceapi.com.")
except OilPriceAPIError as error:
    # Safe support context: do not log your API key or request headers.
    if error.request_id:
        print("Support request ID:", error.request_id)
    if error.status_code in (402, 403):
        print(
            "Review dataset access for this account.",
            error.required_plan,
            error.required_feature,
            error.remediation_url,
        )
    else:
        raise
```

All non-2xx responses share the same `OilPriceAPIError` attributes, including
`status_code`, `code`, `request_id`, plan/feature recovery fields, retry
metadata, commodity `suggestions` and `invalid_codes`, sanitized response
`headers`, `raw_body`, and `raw_text`. Canonical nested, fail/data, and legacy
flat API error envelopes are normalized into that contract. Transport failures
use `NetworkError`; timeouts remain the more specific `TimeoutError`.

Executable recovery examples cover 401, 403, 429, and timeout responses under
[`examples/snippets/`](examples/snippets/). Empty or malformed successful
responses should stop analysis rather than inventing a price, unit, currency,
source, or timestamp.

## Capabilities

The client includes resources for latest and historical values plus additional
dataset and workflow families. Availability is determined by the live API and
account entitlement, not by the presence of a helper method in the package.

- Use [API documentation](https://docs.oilpriceapi.com) for current paths and parameters.
- Use the [commodity catalog](https://www.oilpriceapi.com/commodities) to inspect codes.
- Use [pricing](https://www.oilpriceapi.com/pricing) to review current account options.
- Use the [data usage policy](https://www.oilpriceapi.com/legal/data-usage) before redistributing data.

Standard plans provide API access, normalization, monitoring, and delivery;
they do not transfer ownership of underlying source data or unrestricted raw
data redistribution rights.

## Reproducible Examples

Website and documentation snippets are maintained in `examples/snippets/`.
Every release attaches a versioned manifest containing the package version,
minimum runtime, source commit, expected response shape, exact code, and SHA-256
for each example.

```bash
python scripts/generate_snippet_manifest.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output artifacts/snippets/oilpriceapi-python-snippets-v1.json
```

## Development

The [performance guide](docs/PERFORMANCE_GUIDE.md) documents timeout,
connection-pooling, batching, retry, and troubleshooting behavior without
making a universal latency promise. The
[release process](docs/RELEASE_PROCESS.md) documents the actual PyPI gate and
immutable-version recovery procedure.

```bash
python -m pip install -e '.[dev]'
python scripts/validate_storefront_claims.py
pytest tests/ --ignore=tests/integration --ignore=tests/contract -m 'not slow'
python -m build
```

Live tests require an explicitly supplied non-customer test credential. Unit
and snippet tests use local fixtures and do not print or persist credentials.

## Support

- [API documentation](https://docs.oilpriceapi.com)
- [Service status](https://status.oilpriceapi.com)
- [Product facts](https://api.oilpriceapi.com/product-facts.json)
- [GitHub issues](https://github.com/OilpriceAPI/python-sdk/issues)

Licensed under the [MIT License](LICENSE).
