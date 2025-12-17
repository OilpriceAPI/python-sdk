# SDK Monitoring & Alerting Guide

This guide explains how to monitor OilPriceAPI Python SDK health and catch issues like the v1.4.1 timeout bug before they affect users.

## Overview

**Problem**: The v1.4.1 historical timeout bug wasn't detected until a customer reported it.

**Solution**: Proactive monitoring of SDK health metrics to detect issues before customer impact.

## Monitoring Architecture

```
┌─────────────────┐
│  SDK Usage      │
│  (PyPI Stats)   │
└────────┬────────┘
         │
         v
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Synthetic      │────>│  Prometheus  │────>│  Grafana    │
│  Monitoring     │     │  (Metrics)   │     │  (Dashboards)│
└─────────────────┘     └──────┬───────┘     └─────────────┘
                               │
                               v
                        ┌──────────────┐
                        │  Alertmanager│
                        │  (PagerDuty) │
                        └──────────────┘
```

## Metrics to Monitor

### 1. SDK Health Metrics

#### Download Statistics (PyPI)
- **Metric**: `sdk_downloads_total`
- **Source**: PyPI JSON API
- **Alert**: Downloads drop >50% week-over-week
- **Why**: Indicates major issue causing users to stop upgrading

#### Version Adoption Rate
- **Metric**: `sdk_version_distribution`
- **Source**: PyPI stats / telemetry (if enabled)
- **Alert**: Latest version adoption <10% after 7 days
- **Why**: Users not upgrading = possible issue with new version

### 2. Synthetic Monitoring

#### Historical Query Tests (The Critical Test)
- **Metric**: `sdk_historical_query_duration_seconds`
- **Test**: Run 1-week, 1-month, 1-year queries every 15 minutes
- **Alert**:
  - 1-week query >30s
  - 1-month query >60s
  - 1-year query >120s or timeout
- **Why**: Would have caught the v1.4.1 timeout bug

#### Endpoint Selection Verification
- **Metric**: `sdk_endpoint_selection_correct`
- **Test**: Verify SDK selects correct endpoint for date range
- **Alert**: Wrong endpoint selected
- **Why**: Would have caught v1.4.1 hardcoded endpoint bug

### 3. Error Tracking

#### SDK Exceptions
- **Tool**: Sentry / Application Insights
- **Track**: Timeout errors, authentication failures, connection errors
- **Alert**: Error rate >1% of requests
- **Why**: Early warning of SDK or API issues

### 4. API Response Times

#### Backend Performance
- **Metric**: `api_response_duration_seconds`
- **Track**: P50, P95, P99 response times by endpoint
- **Alert**: P95 >30s for past_week endpoint
- **Why**: Backend slowness affects SDK performance

## Implementation

### 1. Synthetic Monitoring Script

Create `/scripts/synthetic_monitor.py`:

```python
"""
Synthetic monitoring for OilPriceAPI SDK.

Runs continuous health checks and reports metrics to Prometheus.
"""

import time
from datetime import datetime, timedelta
from prometheus_client import start_http_server, Gauge, Counter, Histogram
from oilpriceapi import OilPriceAPI

# Metrics
QUERY_DURATION = Histogram(
    'sdk_historical_query_duration_seconds',
    'Historical query duration',
    ['query_type', 'commodity']
)

QUERY_SUCCESS = Counter(
    'sdk_historical_query_success_total',
    'Successful historical queries',
    ['query_type']
)

QUERY_FAILURE = Counter(
    'sdk_historical_query_failure_total',
    'Failed historical queries',
    ['query_type', 'error_type']
)

ENDPOINT_CORRECTNESS = Gauge(
    'sdk_endpoint_selection_correct',
    'Whether SDK selected correct endpoint',
    ['query_type']
)

def test_1_week_query(client):
    """Test 1-week historical query."""
    start_time = time.time()
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        history = client.historical.get(
            commodity="WTI_USD",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="daily"
        )

        duration = time.time() - start_time
        QUERY_DURATION.labels(query_type='1_week', commodity='WTI_USD').observe(duration)
        QUERY_SUCCESS.labels(query_type='1_week').inc()

        # Alert if too slow (would catch v1.4.1 bug)
        if duration < 30:
            ENDPOINT_CORRECTNESS.labels(query_type='1_week').set(1)
            return True
        else:
            ENDPOINT_CORRECTNESS.labels(query_type='1_week').set(0)
            print(f"WARNING: 1-week query took {duration}s (expected <30s)")
            return False

    except Exception as e:
        QUERY_FAILURE.labels(query_type='1_week', error_type=type(e).__name__).inc()
        ENDPOINT_CORRECTNESS.labels(query_type='1_week').set(0)
        print(f"ERROR: 1-week query failed: {e}")
        return False


def test_1_year_query(client):
    """Test 1-year historical query."""
    start_time = time.time()
    try:
        history = client.historical.get(
            commodity="WTI_USD",
            start_date="2024-01-01",
            end_date="2024-12-31",
            interval="daily"
        )

        duration = time.time() - start_time
        QUERY_DURATION.labels(query_type='1_year', commodity='WTI_USD').observe(duration)
        QUERY_SUCCESS.labels(query_type='1_year').inc()

        # Alert if timeout (would catch v1.4.1 bug)
        if duration < 120:
            ENDPOINT_CORRECTNESS.labels(query_type='1_year').set(1)
            return True
        else:
            ENDPOINT_CORRECTNESS.labels(query_type='1_year').set(0)
            print(f"WARNING: 1-year query took {duration}s (expected <120s)")
            return False

    except Exception as e:
        QUERY_FAILURE.labels(query_type='1_year', error_type=type(e).__name__).inc()
        ENDPOINT_CORRECTNESS.labels(query_type='1_year').set(0)
        print(f"ERROR: 1-year query failed: {e}")
        return False


def run_synthetic_tests(client):
    """Run all synthetic tests."""
    print(f"[{datetime.now()}] Running synthetic tests...")

    test_1_week_query(client)
    test_1_year_query(client)

    print(f"[{datetime.now()}] Tests complete")


def main():
    """Main monitoring loop."""
    import os

    api_key = os.getenv('OILPRICEAPI_KEY')
    if not api_key:
        print("ERROR: OILPRICEAPI_KEY environment variable not set")
        return

    # Start Prometheus metrics server
    port = int(os.getenv('METRICS_PORT', '8000'))
    start_http_server(port)
    print(f"Metrics server started on port {port}")

    # Create SDK client
    client = OilPriceAPI(api_key=api_key)

    # Run tests every 15 minutes
    interval = int(os.getenv('TEST_INTERVAL', '900'))  # 15 minutes

    while True:
        try:
            run_synthetic_tests(client)
        except Exception as e:
            print(f"ERROR in monitoring loop: {e}")

        time.sleep(interval)


if __name__ == '__main__':
    main()
```

### 2. Docker Container for Monitoring

`Dockerfile.monitor`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install SDK and dependencies
RUN pip install oilpriceapi prometheus_client

# Copy monitoring script
COPY scripts/synthetic_monitor.py .

# Expose Prometheus metrics port
EXPOSE 8000

# Run monitoring
CMD ["python", "synthetic_monitor.py"]
```

Run with:
```bash
docker build -f Dockerfile.monitor -t oilpriceapi-monitor .
docker run -e OILPRICEAPI_KEY=$OILPRICEAPI_KEY -p 8000:8000 oilpriceapi-monitor
```

### 3. Prometheus Configuration

`prometheus.yml`:

```yaml
global:
  scrape_interval: 60s
  evaluation_interval: 60s

scrape_configs:
  - job_name: 'oilpriceapi_sdk_monitor'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: /metrics

  - job_name: 'pypi_stats'
    scrape_interval: 3600s  # Every hour
    static_configs:
      - targets: ['pypi-exporter:9101']

rule_files:
  - 'alert_rules.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### 4. Alert Rules

`alert_rules.yml`:

```yaml
groups:
  - name: sdk_health
    interval: 60s
    rules:
      # CRITICAL: Would have caught v1.4.1 bug
      - alert: HistoricalQuery1WeekSlow
        expr: sdk_historical_query_duration_seconds{query_type="1_week"} > 30
        for: 5m
        labels:
          severity: critical
          component: sdk
        annotations:
          summary: "SDK 1-week queries are slow"
          description: "1-week historical queries taking >30s (v1.4.1 bug)"
          runbook: "Check endpoint selection logic in historical.py"

      - alert: HistoricalQuery1YearTimeout
        expr: sdk_historical_query_duration_seconds{query_type="1_year"} > 120
        for: 5m
        labels:
          severity: critical
          component: sdk
        annotations:
          summary: "SDK 1-year queries timing out"
          description: "1-year queries taking >120s or timing out (v1.4.1 bug)"
          runbook: "Check timeout configuration and endpoint selection"

      - alert: HistoricalQueryFailures
        expr: rate(sdk_historical_query_failure_total[5m]) > 0.1
        for: 10m
        labels:
          severity: warning
          component: sdk
        annotations:
          summary: "High SDK query failure rate"
          description: "More than 10% of queries failing"

      - alert: EndpointSelectionWrong
        expr: sdk_endpoint_selection_correct{query_type="1_week"} == 0
        for: 5m
        labels:
          severity: critical
          component: sdk
        annotations:
          summary: "SDK selecting wrong endpoint"
          description: "SDK not using optimized endpoint for date range (v1.4.1 bug)"
          runbook: "Check _get_optimal_endpoint() in historical.py"

  - name: sdk_adoption
    interval: 3600s
    rules:
      - alert: LowVersionAdoption
        expr: |
          (sdk_version_downloads{version=~".*latest.*"} /
           sum(sdk_version_downloads)) < 0.10
        for: 7d
        labels:
          severity: warning
          component: releases
        annotations:
          summary: "Low adoption of latest SDK version"
          description: "Less than 10% of downloads are latest version after 7 days"

      - alert: DownloadsDrop
        expr: |
          (sdk_downloads_total offset 7d) - sdk_downloads_total >
          (sdk_downloads_total offset 7d) * 0.5
        for: 1d
        labels:
          severity: warning
          component: releases
        annotations:
          summary: "SDK downloads dropped significantly"
          description: "Downloads down >50% week-over-week"
```

### 5. Grafana Dashboard

Import this JSON dashboard for monitoring SDK health:

**Key Panels:**
1. Historical Query Duration (1-week, 1-month, 1-year)
2. Query Success Rate
3. Endpoint Selection Correctness
4. PyPI Download Trends
5. Version Distribution

See `grafana_dashboard.json` in this directory.

### 6. PagerDuty Integration

Configure Alertmanager to page on critical alerts:

`alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'default'
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'default'
    email_configs:
      - to: 'sdk-team@oilpriceapi.com'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '<your_pagerduty_key>'
        description: '{{ .CommonAnnotations.summary }}'

  - name: 'slack'
    slack_configs:
      - api_url: '<your_slack_webhook>'
        channel: '#sdk-alerts'
        text: '{{ .CommonAnnotations.description }}'
```

## Deployment

### Quick Start (Docker Compose)

```yaml
version: '3'
services:
  sdk-monitor:
    build:
      context: .
      dockerfile: Dockerfile.monitor
    environment:
      - OILPRICEAPI_KEY=${OILPRICEAPI_KEY}
      - METRICS_PORT=8000
      - TEST_INTERVAL=900
    ports:
      - "8000:8000"
    restart: unless-stopped

  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - ./alert_rules.yml:/etc/prometheus/alert_rules.yml
    ports:
      - "9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=secret
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

  alertmanager:
    image: prom/alertmanager
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
    ports:
      - "9093:9093"
    restart: unless-stopped

volumes:
  grafana_data:
```

Run with:
```bash
docker-compose up -d
```

Access:
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Metrics: http://localhost:8000/metrics

## Testing the Monitoring

### 1. Verify metrics are being collected:
```bash
curl http://localhost:8000/metrics | grep sdk_historical
```

### 2. Trigger test alert (simulate v1.4.1 bug):
```bash
# Temporarily break endpoint selection to trigger alert
# This would simulate the v1.4.1 bug
```

### 3. Check alert fired in Prometheus:
- Go to http://localhost:9090/alerts
- Should see "HistoricalQuery1WeekSlow" or "EndpointSelectionWrong"

### 4. Verify PagerDuty received alert:
- Check PagerDuty incidents
- Should receive page for critical alerts

## Cost Considerations

### Free Tier Options:
- **Prometheus**: Self-hosted (free)
- **Grafana**: Self-hosted (free) or Cloud free tier
- **Synthetic Monitoring**: ~$5-10/month for small VM
- **Total**: ~$10/month for complete monitoring

### Paid Options:
- **Datadog**: ~$15/host/month (includes everything)
- **New Relic**: ~$25/month (includes synthetics)
- **Grafana Cloud**: Free tier, then $8/month

## Maintenance

### Weekly:
- Review synthetic test results
- Check for new alert patterns
- Update baseline thresholds if needed

### Monthly:
- Review PyPI download trends
- Analyze version adoption rates
- Update dashboard based on new insights

### Per Release:
- Add synthetic tests for new features
- Update alert thresholds if performance improves
- Document new metrics in runbooks

## What This Would Have Prevented

### v1.4.1 Historical Timeout Bug

**Detection:** Within 15 minutes of release via synthetic monitoring

**Alerts Triggered:**
1. `HistoricalQuery1WeekSlow` - 7-day query took 67s (expected <30s)
2. `HistoricalQuery1YearTimeout` - 1-year query timed out at 30s
3. `EndpointSelectionWrong` - SDK using wrong endpoint

**Response:**
1. PagerDuty pages on-call engineer
2. Check synthetic test logs
3. Identify endpoint selection bug
4. Rollback v1.4.1, release v1.4.2 fix
5. Customer never affected

## Related Issues

- [#20](https://github.com/OilpriceAPI/python-sdk/issues/20) - Integration tests
- [#21](https://github.com/OilpriceAPI/python-sdk/issues/21) - Performance baselines
- [#22](https://github.com/OilpriceAPI/python-sdk/issues/22) - Pre-release validation
- [#23](https://github.com/OilpriceAPI/python-sdk/issues/23) - Monitoring & alerting (this document)

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
- [PyPI Stats API](https://pypistats.org/api/)
- [Best Practices for SDK Monitoring](https://example.com)
