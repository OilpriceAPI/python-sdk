# Synthetic Monitoring Deployment Guide

Complete guide to deploying SDK synthetic monitoring that would have caught the v1.4.1 bug.

---

## Quick Start

```bash
# 1. Set API key
export OILPRICEAPI_KEY=your_key_here

# 2. Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# 3. Access dashboards
open http://localhost:3000  # Grafana (admin/admin)
open http://localhost:9090  # Prometheus
open http://localhost:8000/metrics  # Metrics endpoint
```

That's it! Monitoring is now running.

---

## What Gets Monitored

### SDK Health Checks (Every 15 Minutes)

1. **1-day historical query**
   - Expected: <10s
   - Alert if: >10s

2. **1-week historical query** ⭐
   - Expected: <30s
   - Alert if: >30s
   - **Would have caught v1.4.1 bug** (took 67s)

3. **1-month historical query**
   - Expected: <60s
   - Alert if: >60s

4. **1-year historical query** ⭐
   - Expected: <120s
   - Alert if: >120s or timeout
   - **Would have caught v1.4.1 bug** (timed out at 30s)

### Metrics Collected

- `sdk_historical_query_duration_seconds` - Query latency
- `sdk_historical_query_success_total` - Success count
- `sdk_historical_query_failure_total` - Failure count
- `sdk_endpoint_selection_correct` - Correct endpoint used
- `sdk_historical_records_returned` - Record count
- `sdk_monitor_last_test_timestamp` - Last test run time

---

## Architecture

```
┌─────────────────┐
│  SDK Monitor    │  Runs tests every 15min
│  (Docker)       │  Exposes Prometheus metrics
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Prometheus     │  Scrapes metrics every 60s
│  (Docker)       │  Stores time-series data
└────────┬────────┘
         │
         ├──────> Grafana (Dashboards)
         │
         └──────> Alertmanager (PagerDuty/Slack)
```

---

## Configuration

### Environment Variables

Create `.env` file:

```bash
# Required
OILPRICEAPI_KEY=your_api_key_here

# Optional
GRAFANA_PASSWORD=secure_password
TEST_INTERVAL=900  # 15 minutes (default)
METRICS_PORT=8000  # Metrics port (default)
```

### Prometheus Configuration

`monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 60s
  evaluation_interval: 60s

scrape_configs:
  - job_name: 'sdk_monitor'
    static_configs:
      - targets: ['sdk-monitor:8000']

  - job_name: 'pypi_stats'
    scrape_interval: 3600s
    static_configs:
      - targets: ['pypi-exporter:9101']

rule_files:
  - 'alert_rules.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### Alert Rules

`monitoring/alert_rules.yml`:

```yaml
groups:
  - name: sdk_health
    interval: 60s
    rules:
      # Would have caught v1.4.1 bug
      - alert: HistoricalQuery1WeekSlow
        expr: sdk_historical_query_duration_seconds{query_type="1_week"} > 30
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "1-week queries >30s (v1.4.1 bug pattern)"
          description: "Duration: {{ $value }}s (expected <30s)"

      - alert: HistoricalQuery1YearTimeout
        expr: sdk_historical_query_duration_seconds{query_type="1_year"} > 120
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "1-year queries timing out"
          description: "Duration: {{ $value }}s (v1.4.1 bug pattern)"

      - alert: SDKMonitorDown
        expr: up{job="sdk_monitor"} == 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "SDK monitor is down"
```

### Alertmanager Configuration

`monitoring/alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'default'
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
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
      - to: 'team@oilpriceapi.com'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
        description: '{{ .CommonAnnotations.summary }}'

  - name: 'slack'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#sdk-alerts'
        text: '{{ .CommonAnnotations.description }}'
```

---

## Deployment

### Production Deployment

```bash
# 1. Clone repository
git clone https://github.com/OilpriceAPI/python-sdk
cd python-sdk

# 2. Create .env file
cat > .env << EOF
OILPRICEAPI_KEY=your_production_key
GRAFANA_PASSWORD=secure_password
EOF

# 3. Create monitoring directory
mkdir -p monitoring/grafana/{provisioning,dashboards}

# 4. Copy configuration files
cp monitoring/prometheus.yml.example monitoring/prometheus.yml
cp monitoring/alert_rules.yml.example monitoring/alert_rules.yml
cp monitoring/alertmanager.yml.example monitoring/alertmanager.yml

# 5. Configure alerts (edit files above)
vim monitoring/alertmanager.yml  # Add PagerDuty/Slack keys

# 6. Start monitoring
docker-compose -f docker-compose.monitoring.yml up -d

# 7. Verify all services running
docker-compose -f docker-compose.monitoring.yml ps
```

### Verify Deployment

```bash
# Check monitor is running
curl http://localhost:8000/metrics | grep sdk_

# Check Prometheus scraping
curl http://localhost:9090/api/v1/query?query=up

# Check Grafana
open http://localhost:3000  # Login: admin/admin (or your password)
```

---

## Grafana Dashboards

### Import SDK Health Dashboard

1. Go to http://localhost:3000
2. Login (admin/admin or your password)
3. Click "+" → "Import"
4. Upload `monitoring/grafana/dashboards/sdk-health.json`

### Dashboard Panels

**Row 1: Query Performance**
- 1-Week Query Duration (should be <30s)
- 1-Month Query Duration (should be <60s)
- 1-Year Query Duration (should be <120s)
- Query Success Rate (should be >99%)

**Row 2: Error Tracking**
- Error Rate by Type
- Timeout Errors (should be 0)
- Failed Queries Over Time

**Row 3: Endpoint Selection**
- Endpoint Correctness (should be 1.0)
- Records Returned by Query Type
- Last Test Timestamp

---

## Troubleshooting

### Monitor Container Won't Start

```bash
# Check logs
docker-compose -f docker-compose.monitoring.yml logs sdk-monitor

# Common issues:
# 1. No API key set
export OILPRICEAPI_KEY=your_key

# 2. Port already in use
# Change port in docker-compose.monitoring.yml

# 3. Package installation failed
docker-compose -f docker-compose.monitoring.yml build --no-cache sdk-monitor
```

### No Metrics in Prometheus

```bash
# Check monitor is exposing metrics
curl http://localhost:8000/metrics

# Check Prometheus can reach monitor
docker-compose -f docker-compose.monitoring.yml exec prometheus \
  wget -O- http://sdk-monitor:8000/metrics

# Check Prometheus targets
open http://localhost:9090/targets
```

### Alerts Not Firing

```bash
# Check alert rules are loaded
open http://localhost:9090/alerts

# Check Alertmanager config
docker-compose -f docker-compose.monitoring.yml exec alertmanager \
  amtool check-config /etc/alertmanager/alertmanager.yml

# Test alert routing
docker-compose -f docker-compose.monitoring.yml exec alertmanager \
  amtool alert add test severity=critical
```

---

## Maintenance

### Daily

- Check Grafana dashboard for anomalies
- Verify latest test timestamp is recent
- Review any fired alerts

### Weekly

- Review query duration trends
- Check for performance regressions
- Update alert thresholds if needed

### Monthly

- Review and cleanup old metrics (auto-retention: 90 days)
- Update SDK monitor to latest version
- Review alert fatigue (too many false positives?)

---

## Cost Estimates

### Self-Hosted (Docker Compose)

**Requirements:**
- VM: 2 CPU, 4GB RAM, 20GB disk
- Providers: DigitalOcean, AWS, GCP

**Costs:**
- DigitalOcean Droplet ($24/month)
- AWS t3.medium (~$30/month)
- GCP e2-medium (~$25/month)

**Total: ~$25/month**

### Managed Services

**Grafana Cloud:**
- Free tier: 10k series, 14-day retention
- Pro: $8/month for 100k series

**Datadog:**
- ~$15/host/month
- Includes everything

**New Relic:**
- ~$25/month
- Includes synthetics

---

## Scaling

### For Multiple Commodities

Edit `scripts/synthetic_monitor.py`:

```python
# Test multiple commodities
COMMODITIES = ["WTI_USD", "BRENT_CRUDE_USD", "NATURAL_GAS_USD"]

for commodity in COMMODITIES:
    test_1_week_query(client, commodity)
    test_1_year_query(client, commodity)
```

### For Multiple Intervals

```python
# Test different intervals
INTERVALS = ["hourly", "daily", "weekly"]

for interval in INTERVALS:
    test_query_with_interval(client, interval)
```

### For Different Regions

Run multiple monitors in different regions:

```yaml
# docker-compose.monitoring.yml
services:
  sdk-monitor-us:
    build: .
    environment:
      - OILPRICEAPI_KEY=${US_API_KEY}
      - REGION=us-east-1

  sdk-monitor-eu:
    build: .
    environment:
      - OILPRICEAPI_KEY=${EU_API_KEY}
      - REGION=eu-west-1
```

---

## Success Metrics

### Monitoring is Working If:

✅ All services show "up" in Prometheus targets
✅ Latest test timestamp is within last 20 minutes
✅ Query durations within expected ranges
✅ Zero timeout errors
✅ Endpoint selection correctness = 1.0

### Would Have Detected v1.4.1 If:

✅ 1-week query duration alert fires (>30s)
✅ 1-year query timeout alert fires
✅ Endpoint selection correctness drops to 0
✅ PagerDuty/Slack notification sent
✅ Team investigates within 1 hour

**Result: Bug caught in <1 hour instead of 8 hours**

---

## Related

- [Monitoring Guide](../.github/MONITORING_GUIDE.md) - Architecture details
- [Synthetic Monitor Script](../scripts/synthetic_monitor.py) - Monitor source code
- [GitHub Issue #28](https://github.com/OilpriceAPI/python-sdk/issues/28)

---

## Quick Commands

```bash
# Start monitoring
docker-compose -f docker-compose.monitoring.yml up -d

# Stop monitoring
docker-compose -f docker-compose.monitoring.yml down

# View logs
docker-compose -f docker-compose.monitoring.yml logs -f sdk-monitor

# Restart monitor
docker-compose -f docker-compose.monitoring.yml restart sdk-monitor

# Check metrics
curl http://localhost:8000/metrics | grep sdk_

# Test alert
docker-compose -f docker-compose.monitoring.yml exec alertmanager \
  amtool alert add test severity=critical summary="Test alert"
```
