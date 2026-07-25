# Dates and commodity-code guidance

## Strict date syntax

SDK methods that accept dates validate each supplied value before sending a
request. Strings must be a real calendar date in exact `YYYY-MM-DD` form.
`datetime.date` and `datetime.datetime` values are also accepted and normalized
to that form.

```python
from datetime import date

client.historical.get(
    "BRENT_CRUDE_USD",
    start_date=date(2026, 1, 1),
    end_date="2026-01-31",
)
```

Malformed values such as `2026-01-010`, `2026-1-10`, impossible calendar
dates, empty strings, and datetime strings are rejected locally with
`ValueError`; no API request is made. A range whose individual dates are valid
but whose ordering or business meaning is invalid is still sent to the API so
the server remains the authority for range semantics.

## Search the current catalog

Use `commodities.search()` when a code is unknown. Each search fetches the
current API catalog and ranks matches across code, name, category, description,
currency, unit, and source. The SDK does not bundle a hand-maintained code list.

```python
matches = client.commodities.search("brent crude", limit=5)
for commodity in matches:
    print(commodity["code"], commodity.get("name"))
```

The async client provides the same behavior:

```python
matches = await client.commodities.search("natural gas")
```

No match or an empty catalog returns `[]`. Authentication, network, timeout,
and other API failures are not converted into an empty result; their existing
typed SDK exceptions propagate so callers can distinguish failure from “no
matches.”

## Recover from an invalid code

When the API includes commodity suggestions in an error response, the SDK
exposes bounded string values on `error.suggestions`. Invalid submitted codes
are available on `error.invalid_codes`.

```python
from oilpriceapi import OilPriceAPIError

try:
    client.prices.get("BRENNT")
except OilPriceAPIError as error:
    if error.code == "invalid_code" and error.suggestions:
        print("Try one of:", ", ".join(error.suggestions))
    else:
        raise
```

The response parser ignores unexpected non-string suggestion values, limits
the number and length of values retained, and applies the same credential
redaction used for other error diagnostics.
