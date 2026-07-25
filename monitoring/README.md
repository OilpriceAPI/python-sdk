# Synthetic monitoring

The supported monitor is the repository's hourly `Scheduled SDK Synthetic`
GitHub Actions workflow.

See [the current design, receipts, and response runbook](../docs/SYNTHETIC_MONITORING.md).

The old local Prometheus/Grafana compose example was removed because its
referenced configuration and dashboard files did not exist, it exposed a
long-running process that printed part of the API key, and it was never the
deployed monitoring path.
