# DataFrames and pagination

The pandas helpers preserve the source context returned by the API and fetch
complete result sets without requiring a manual page loop.

Install the optional dependency:

```bash
python -m pip install "oilpriceapi[pandas]"
```

## Historical data

```python
from oilpriceapi import OilPriceAPI

client = OilPriceAPI()
df = client.historical.to_dataframe(
    commodity="BRENT_CRUDE_USD",
    start="2026-01-01",
    end="2026-06-30",
    interval="daily",
    per_page=500,
)
```

The historical DataFrame contract is:

- Every page is fetched automatically until the API reports completion.
- `per_page` is an integer from 1 to 1000 and defaults to 500.
- `per_page` controls each request; it does not limit the total rows returned.
- `currency` and `unit` are taken from each API record. A missing currency
  remains null and is never converted to USD.
- An exact record repeated on a later, overlapping page is emitted once.
  Distinct records, including records sharing a timestamp, remain intact.
- An empty page terminates pagination even if stale metadata says another page
  exists.
- The result is sorted by its `date` index. Empty results retain the columns
  `commodity`, `value`, `currency`, `unit`, and `type_name`.

The convenience resource uses the same pagination behavior:

```python
df = client.prices.to_dataframe(
    commodity="EU_CARBON_EUR",
    start="2026-01-01",
    end="2026-06-30",
    per_page=250,
)
```

For model objects instead of pandas, use `client.historical.get_all(...)`.
It accepts the same `per_page` range and automatically fetches every page.

## Current prices

Calling `client.prices.to_dataframe()` with no commodity returns the current
price records available to the account and follows the API's pagination headers:

```python
df = client.prices.to_dataframe(per_page=250)
```

Each row keeps the API-provided currency and unit. Exact records repeated on a
later page are returned once.

## Manual page control

Use `client.historical.get(...)` when a single page is intentional:

```python
page = client.historical.get(
    commodity="BRENT_CRUDE_USD",
    page=2,
    per_page=100,
)
```

Use `client.historical.iter_pages(...)` to process complete results one page
at a time without retaining the entire response in memory.
