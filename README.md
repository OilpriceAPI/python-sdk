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
    if error.status_code in (402, 403):
        print("Review dataset access for this account.")
    else:
        raise
```

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
making a universal latency promise.

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
