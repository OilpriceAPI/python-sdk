# Python SDK synthetic monitoring

The `Scheduled SDK Synthetic` workflow runs once an hour and validates the two
smallest customer-critical paths through the installed SDK:

1. a latest `BRENT_CRUDE_USD` price with a finite numeric value, currency, unit,
   and source timestamp;
2. a five-record daily history request with finite numeric values.

A keyless demo-contract test runs first. The keyed check fails loudly when the
monitor credential is missing; it never silently skips.

## Receipts and alerts

Each run writes `sdk-health.json`, publishes it in the GitHub Actions job
summary, and retains it as an artifact for 30 days. Receipts contain the SDK
version, check names, durations, and structural assertions. They exclude the API
key, response values, request URLs, response bodies, and exception messages.

GitHub Actions run history is the dashboard. A failed scheduled workflow is the
alert and uses the repository notification settings; the workflow deliberately
does not create recurring GitHub issues.

## Response runbook

1. Open the failed `Scheduled SDK Synthetic` run and read its JSON receipt.
2. If `configuration` failed, restore or rotate `OILPRICEAPI_TEST_KEY`, then run
   the workflow manually.
3. If only the keyless demo check failed, verify public API availability and
   response-envelope drift.
4. If `latest_price` or `bounded_history` failed, compare with the latest
   `Live API Tests` run and reproduce with a non-customer test credential.
5. Treat repeated time-budget failures as a latency regression. Treat missing
   fields, empty history, or non-finite values as a contract regression.
6. Record any product incident in the owning API repository. Keep SDK parsing,
   retry, or compatibility fixes in this repository.

The schedule is hourly rather than every five minutes. Two authenticated checks
per hour provide continuous SDK-contract coverage without spending thousands of
CI minutes or consuming unnecessary API quota. Push and pull-request live tests
provide additional coverage between scheduled runs.
