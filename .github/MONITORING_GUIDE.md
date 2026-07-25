# Python SDK monitoring

Current SDK monitoring has two layers:

1. `Live API Tests` exercises keyless and keyed integration paths on pushes and
   pull requests.
2. `Scheduled SDK Synthetic` runs hourly, checks the latest-price and bounded
   history customer paths, and retains a privacy-safe JSON receipt for 30 days.

The operational design and response runbook live in
[`docs/SYNTHETIC_MONITORING.md`](../docs/SYNTHETIC_MONITORING.md).

API-service availability, infrastructure metrics, and incident alerting belong
to the API service rather than this SDK repository.
