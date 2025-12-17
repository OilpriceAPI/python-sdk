# SDK Telemetry Documentation

**Status**: Implemented but not yet integrated (Issue #24)
**Privacy**: Completely opt-in, no user data collected

---

## Overview

SDK telemetry helps detect issues like the v1.4.1 timeout bug across the user base before they become widespread.

**Problem**: The v1.4.1 bug affected Idan, but we don't know if it affected other users too.

**Solution**: Opt-in telemetry to detect error patterns and performance issues proactively.

---

## Privacy & Security

### What We Collect (When Enabled)

✅ **SDK Metadata**:
- SDK version (e.g., "1.4.2")
- Python version (e.g., "3.11.5")
- Platform (e.g., "Linux", "Darwin")

✅ **Operation Metrics**:
- Operation type (e.g., "historical.get", "prices.get")
- Success/failure status
- Duration (aggregated, no individual requests)
- Error types (e.g., "TimeoutError", not error messages)

✅ **Performance Data**:
- Query type (e.g., "1_week", "1_year")
- Endpoint used (e.g., "/v1/prices/past_week")
- Interval (e.g., "daily", "hourly")

### What We DON'T Collect

❌ **Never Collected**:
- API keys
- Commodity codes or names
- Date ranges or specific dates
- Query parameters (except interval)
- Response data or prices
- IP addresses
- User identifiable information
- Any sensitive business data

### Session ID

- Anonymous session ID generated per SDK instance
- Used only to group events from same session
- Cannot be tied back to user or organization
- Regenerated each time SDK is initialized

---

## Usage

### Enable Telemetry

```python
from oilpriceapi import OilPriceAPI

# Opt-in to telemetry
client = OilPriceAPI(
    api_key="your_key",
    enable_telemetry=True  # Default: False
)

# Use SDK normally
price = client.prices.get("BRENT_CRUDE_USD")
history = client.historical.get(
    commodity="WTI_USD",
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

### Environment Variable

```bash
# Enable telemetry via environment variable
export OILPRICEAPI_TELEMETRY=true

# SDK will respect environment variable
python your_script.py
```

### Disable Telemetry (Default)

```python
# Telemetry disabled by default (opt-in only)
client = OilPriceAPI(api_key="your_key")

# Or explicitly disable
client = OilPriceAPI(
    api_key="your_key",
    enable_telemetry=False
)
```

### Debug Mode

```python
# See what's being sent (for transparency)
client = OilPriceAPI(
    api_key="your_key",
    enable_telemetry=True,
    telemetry_debug=True  # Print telemetry events
)
```

Output:
```
[Telemetry] Enabled (session: a7f3c8e9)
[Telemetry] historical.get: 1250ms success=True
[Telemetry] Flushed 1 events (status: 200)
```

---

## How It Helps

### Detecting Issues Like v1.4.1

**Scenario**: New SDK version ships with timeout bug

**Without Telemetry**:
1. Bug ships to PyPI
2. Users start upgrading
3. Some users hit timeouts
4. Hope someone reports it
5. Days/weeks before we notice

**With Telemetry**:
1. Bug ships to PyPI
2. Users start upgrading (telemetry enabled)
3. **Telemetry shows spike in TimeoutErrors**
4. Alert fires: "SDK v1.4.2 has 50% failure rate on historical.get"
5. **Issue detected within hours, not days**
6. Proactive outreach to affected users

### Example Alert Scenarios

#### 1. Performance Regression
```
Alert: Historical query durations increased 3x
SDK Version: v1.4.3
Operation: historical.get (1_year queries)
Before: 75s average
After: 225s average
Action: Investigate endpoint selection logic
```

#### 2. Error Rate Spike
```
Alert: TimeoutError rate >10%
SDK Version: v1.4.2
Operation: historical.get
Error: TimeoutError (30s timeout)
Action: Check if v1.4.1 bug reintroduced
```

#### 3. Version Adoption Issues
```
Alert: v1.4.3 adoption <5% after 7 days
Possible causes:
- Installation issues
- Breaking changes users encountering
- Better to investigate early
```

---

## Data Flow

```
┌─────────────┐
│  Your SDK   │
│  Instance   │
└──────┬──────┘
       │
       │ 1. Operation completed
       │    (historical.get, 1.2s, success=True)
       │
       v
┌─────────────┐
│  Telemetry  │
│   Buffer    │  2. Buffer events (max 10 or 5min)
└──────┬──────┘
       │
       │ 3. Flush batch every 5 minutes
       │
       v
┌─────────────────────┐
│  Telemetry Service  │  4. Aggregate metrics
│  (api.oilprice.com) │
└──────┬──────────────┘
       │
       │ 5. Alert on anomalies
       │
       v
┌─────────────┐
│  Dashboard  │
│  & Alerts   │
└─────────────┘
```

---

## Integration (For Maintainers)

### Step 1: Add to Client

```python
# In oilpriceapi/client.py

from .telemetry import configure_telemetry, get_telemetry

class OilPriceAPI:
    def __init__(
        self,
        api_key: Optional[str] = None,
        enable_telemetry: bool = False,
        telemetry_debug: bool = False,
        **kwargs
    ):
        # ... existing code ...

        # Configure telemetry
        telemetry_enabled = enable_telemetry or os.environ.get("OILPRICEAPI_TELEMETRY") == "true"
        configure_telemetry(
            enabled=telemetry_enabled,
            debug=telemetry_debug
        )

        self._telemetry = get_telemetry()
```

### Step 2: Track Operations

```python
# In oilpriceapi/client.py

def request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
    """Make HTTP request with telemetry tracking."""
    start_time = time.time()
    success = False
    error_type = None

    try:
        response = self._client.request(method, path, **kwargs)
        success = True
        return response.json()

    except TimeoutError as e:
        error_type = "TimeoutError"
        raise

    except Exception as e:
        error_type = type(e).__name__
        raise

    finally:
        # Track telemetry (if enabled)
        duration = time.time() - start_time
        if self._telemetry:
            operation = self._get_operation_name(method, path)
            self._telemetry.track_request(
                operation=operation,
                duration=duration,
                success=success,
                error_type=error_type
            )
```

### Step 3: Add Metadata

```python
# In oilpriceapi/resources/historical.py

def get(self, commodity: str, start_date: str, end_date: str, **kwargs):
    """Get historical prices with telemetry metadata."""
    # ... existing code ...

    # Add telemetry metadata
    if client._telemetry:
        days = (end_date_obj - start_date_obj).days
        query_type = "1_week" if days <= 7 else "1_month" if days <= 30 else "1_year"
        endpoint_used = self._get_optimal_endpoint(start_date, end_date)

        # Will be attached to telemetry event
        kwargs["_telemetry_metadata"] = {
            "query_type": query_type,
            "interval": interval,
            "endpoint_used": endpoint_used
        }

    # ... make request ...
```

---

## Testing Telemetry

### Unit Tests

```python
# tests/unit/test_telemetry.py

def test_telemetry_disabled_by_default():
    """Telemetry should be opt-in."""
    client = OilPriceAPI(api_key="test_key")
    assert client._telemetry is None or not client._telemetry.enabled


def test_telemetry_can_be_enabled():
    """Telemetry can be explicitly enabled."""
    client = OilPriceAPI(
        api_key="test_key",
        enable_telemetry=True
    )
    assert client._telemetry.enabled


def test_telemetry_tracks_operations(mocker):
    """Telemetry tracks SDK operations."""
    telemetry = Telemetry(enabled=True, debug=True)

    # Mock telemetry endpoint
    mock_post = mocker.patch("httpx.post")

    telemetry.track_request(
        operation="historical.get",
        duration=1.5,
        success=True,
        metadata={"query_type": "1_year"}
    )

    telemetry._flush()

    # Verify telemetry was sent
    assert mock_post.called
    payload = mock_post.call_args[1]["json"]
    assert payload["events"][0]["operation"] == "historical.get"
    assert payload["events"][0]["success"] is True
```

### Integration Tests

```python
# tests/integration/test_telemetry_integration.py

def test_telemetry_real_operation():
    """Test telemetry with real API call."""
    client = OilPriceAPI(
        api_key=os.getenv("OILPRICEAPI_KEY"),
        enable_telemetry=True,
        telemetry_debug=True
    )

    # This will generate telemetry event
    history = client.historical.get(
        commodity="WTI_USD",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )

    # Verify telemetry recorded the operation
    # (In real implementation, would check telemetry buffer)
    assert history is not None
```

---

## Backend Requirements

### Telemetry Endpoint

The SDK sends telemetry to: `https://api.oilpriceapi.com/v1/telemetry`

**Request Format**:
```json
{
  "sdk": "oilpriceapi-python",
  "version": "1.4.2",
  "events": [
    {
      "type": "request",
      "session_id": "a7f3c8e9...",
      "sdk_version": "1.4.2",
      "python_version": "3.11.5",
      "platform": "Linux",
      "operation": "historical.get",
      "duration_ms": 1250,
      "success": true,
      "error_type": null,
      "timestamp": "2025-12-17T10:30:00Z",
      "metadata": {
        "query_type": "1_year",
        "interval": "daily",
        "endpoint_used": "/v1/prices/past_year"
      }
    }
  ]
}
```

**Response**: `200 OK` (or `202 Accepted`)

### Processing Pipeline

1. **Ingest**: Receive telemetry events
2. **Store**: Save to time-series database (InfluxDB/TimescaleDB)
3. **Aggregate**: Compute metrics by SDK version, operation, etc.
4. **Alert**: Fire alerts on anomalies
5. **Dashboard**: Visualize in Grafana

### Alert Rules

```yaml
# Would have caught v1.4.1 bug
- alert: HighTimeoutRate
  expr: |
    rate(telemetry_errors{error_type="TimeoutError"}[5m]) > 0.1
  labels:
    severity: critical
  annotations:
    summary: "SDK timeout rate >10%"

- alert: PerformanceRegression
  expr: |
    avg(telemetry_duration_ms{operation="historical.get"}[1h]) >
    avg(telemetry_duration_ms{operation="historical.get"}[1h] offset 24h) * 2
  labels:
    severity: warning
  annotations:
    summary: "2x performance regression detected"
```

---

## FAQ

### Why is telemetry opt-in?

Privacy and trust. We only collect data with explicit user consent.

### Can I see exactly what's sent?

Yes! Use `telemetry_debug=True` to print all events before sending.

### Does telemetry slow down the SDK?

No. Telemetry events are:
- Buffered (batch sends)
- Sent asynchronously (background thread)
- Short timeout (5s, won't block)
- Silent failures (won't affect your code)

### What if telemetry endpoint is down?

Silently fails. Your SDK operations continue normally.

### How do I disable telemetry after enabling?

```python
# Option 1: Don't pass enable_telemetry=True
client = OilPriceAPI(api_key="your_key")

# Option 2: Explicitly disable
client = OilPriceAPI(api_key="your_key", enable_telemetry=False)

# Option 3: Unset environment variable
unset OILPRICEAPI_TELEMETRY
```

### Where is telemetry data stored?

- Sent to OilPriceAPI infrastructure
- Stored in time-series database
- Retained for 90 days
- Used only for SDK health monitoring
- Not sold or shared with third parties

### Can I use custom telemetry endpoint?

Yes (for testing or self-hosting):

```python
from oilpriceapi import OilPriceAPI
from oilpriceapi.telemetry import configure_telemetry

configure_telemetry(
    enabled=True,
    endpoint="https://your-telemetry-server.com/events"
)

client = OilPriceAPI(api_key="your_key")
```

---

## Benefits

### For Users

✅ **Faster Bug Fixes**: Issues detected and fixed before you encounter them
✅ **Better Releases**: Telemetry validates new versions work well
✅ **Proactive Support**: We can reach out if we detect issues
✅ **Improved Performance**: Performance regressions caught quickly

### For Maintainers

✅ **Early Warning**: Detect issues within hours, not weeks
✅ **Usage Patterns**: Understand which features matter most
✅ **Version Adoption**: Know when to deprecate old versions
✅ **Performance Trends**: Optimize based on real-world usage

### For Community

✅ **Better SDK**: Data-driven improvements
✅ **Higher Quality**: Fewer bugs reach production
✅ **Transparency**: Open source telemetry code
✅ **Privacy Respected**: Opt-in only, no user data

---

## Related Issues

- [#24](https://github.com/OilpriceAPI/python-sdk/issues/24) - Add opt-in SDK telemetry (this document)
- [#20](https://github.com/OilpriceAPI/python-sdk/issues/20) - Integration tests
- [#23](https://github.com/OilpriceAPI/python-sdk/issues/23) - Monitoring & alerting

---

## Roadmap

### Phase 1: Implementation ✅ (Current)
- ✅ Telemetry module created
- ✅ Documentation written
- ⏳ Integration into client
- ⏳ Unit tests
- ⏳ Privacy review

### Phase 2: Backend
- ⏳ Telemetry endpoint implementation
- ⏳ Time-series database setup
- ⏳ Alert rules configuration
- ⏳ Grafana dashboards

### Phase 3: Launch
- ⏳ Announcement in release notes
- ⏳ Blog post explaining benefits
- ⏳ Opt-in campaign
- ⏳ Monitor adoption rate

---

## Contact

Questions about telemetry?
- GitHub Issue: https://github.com/OilpriceAPI/python-sdk/issues/24
- Email: privacy@oilpriceapi.com
- Documentation: https://docs.oilpriceapi.com/sdk/python/telemetry
