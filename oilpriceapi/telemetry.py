"""
Optional telemetry for OilPriceAPI SDK.

This module provides opt-in telemetry to help detect issues like
the v1.4.1 timeout bug before they affect all users.

Privacy:
- Completely opt-in (disabled by default)
- No user data or API keys collected
- Only aggregated metrics
- Open source and auditable

Usage:
    from oilpriceapi import OilPriceAPI

    # Enable telemetry
    client = OilPriceAPI(
        api_key="your_key",
        enable_telemetry=True  # Opt-in
    )

What we collect (when enabled):
- SDK version
- Python version
- Operation types (prices.get, historical.get, etc.)
- Success/failure rates
- Response times (aggregated)
- Error types (not error messages)

What we DON'T collect:
- API keys
- Commodity codes
- Date ranges
- Query parameters
- Response data
- Any user identifiable information
"""

import os
import sys
import time
import platform
import threading
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class Telemetry:
    """
    Opt-in telemetry collector for SDK health monitoring.

    Helps detect issues like v1.4.1 timeout bug across user base.
    """

    def __init__(
        self,
        enabled: bool = False,
        endpoint: str = "https://telemetry.oilpriceapi.com/v1/events",
        flush_interval: int = 300,  # 5 minutes
        debug: bool = False
    ):
        """
        Initialize telemetry.

        Args:
            enabled: Enable telemetry (default: False - opt-in)
            endpoint: Telemetry endpoint URL
            flush_interval: Seconds between metric flushes
            debug: Print telemetry events (for testing)
        """
        self.enabled = enabled and HTTPX_AVAILABLE
        self.endpoint = endpoint
        self.flush_interval = flush_interval
        self.debug = debug

        # Event buffer
        self._events = []
        self._lock = threading.Lock()
        self._last_flush = time.time()

        # Session info (collected once)
        self._session_id = self._generate_session_id()
        self._sdk_version = self._get_sdk_version()
        self._python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        self._platform = platform.system()

        if self.enabled:
            # Start background flush thread
            self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
            self._flush_thread.start()

            if self.debug:
                print(f"[Telemetry] Enabled (session: {self._session_id[:8]})")

    def _generate_session_id(self) -> str:
        """Generate anonymous session ID."""
        import hashlib
        import uuid

        # Use random UUID, not tied to user
        return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()

    def _get_sdk_version(self) -> str:
        """Get SDK version."""
        try:
            from oilpriceapi import __version__
            return __version__
        except ImportError:
            return "unknown"

    def track_request(
        self,
        operation: str,
        duration: float,
        success: bool,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Track SDK operation.

        Args:
            operation: Operation name (e.g., "prices.get", "historical.get")
            duration: Operation duration in seconds
            success: Whether operation succeeded
            error_type: Error type if failed (e.g., "TimeoutError")
            metadata: Additional non-sensitive metadata
        """
        if not self.enabled:
            return

        event = {
            "type": "request",
            "session_id": self._session_id,
            "sdk_version": self._sdk_version,
            "python_version": self._python_version,
            "platform": self._platform,
            "operation": operation,
            "duration_ms": int(duration * 1000),
            "success": success,
            "error_type": error_type,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add safe metadata (no sensitive data)
        if metadata:
            safe_metadata = {
                k: v for k, v in metadata.items()
                if k in ["query_type", "interval", "endpoint_used"]
            }
            event["metadata"] = safe_metadata

        with self._lock:
            self._events.append(event)

        if self.debug:
            print(f"[Telemetry] {operation}: {duration*1000:.0f}ms success={success}")

        # Flush if buffer is large or time elapsed
        if len(self._events) >= 10 or (time.time() - self._last_flush) > self.flush_interval:
            self._flush()

    def _flush(self):
        """Flush events to telemetry endpoint."""
        if not self.enabled or not HTTPX_AVAILABLE:
            return

        with self._lock:
            if not self._events:
                return

            events = self._events.copy()
            self._events.clear()
            self._last_flush = time.time()

        try:
            # Send telemetry in background (non-blocking)
            payload = {
                "events": events,
                "sdk": "oilpriceapi-python",
                "version": self._sdk_version,
            }

            # Use short timeout to not block SDK operations
            response = httpx.post(
                self.endpoint,
                json=payload,
                timeout=5.0,
                headers={"Content-Type": "application/json"}
            )

            if self.debug:
                print(f"[Telemetry] Flushed {len(events)} events (status: {response.status_code})")

        except Exception as e:
            if self.debug:
                print(f"[Telemetry] Flush failed: {e}")
            # Silently fail - don't affect SDK operations

    def _flush_loop(self):
        """Background thread to flush telemetry periodically."""
        while self.enabled:
            time.sleep(self.flush_interval)
            self._flush()

    def close(self):
        """Flush remaining events and close telemetry."""
        if self.enabled:
            self._flush()


# Global telemetry instance (disabled by default)
_global_telemetry: Optional[Telemetry] = None


def configure_telemetry(
    enabled: bool = False,
    endpoint: Optional[str] = None,
    debug: bool = False
):
    """
    Configure global telemetry.

    Args:
        enabled: Enable telemetry (opt-in)
        endpoint: Custom telemetry endpoint
        debug: Print telemetry events
    """
    global _global_telemetry

    kwargs = {"enabled": enabled, "debug": debug}
    if endpoint:
        kwargs["endpoint"] = endpoint

    _global_telemetry = Telemetry(**kwargs)


def get_telemetry() -> Optional[Telemetry]:
    """Get global telemetry instance."""
    return _global_telemetry


def track_request(*args, **kwargs):
    """Track request using global telemetry."""
    if _global_telemetry:
        _global_telemetry.track_request(*args, **kwargs)
