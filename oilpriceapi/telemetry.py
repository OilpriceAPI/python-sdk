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

import platform
import sys
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class Telemetry:
    """
    Opt-in telemetry collector for SDK health monitoring.

    Helps detect issues like v1.4.1 timeout bug across user base.

    Delivery is always performed on a background daemon thread; no SDK call
    path ever blocks on the telemetry endpoint.
    """

    #: Buffered events that trigger an early (still background) delivery.
    FLUSH_THRESHOLD = 10
    #: Hard cap on the buffer so an unreachable collector cannot leak memory.
    MAX_BUFFERED_EVENTS = 1000

    def __init__(
        self,
        enabled: bool = False,
        endpoint: str = "https://telemetry.oilpriceapi.com/v1/events",
        flush_interval: int = 300,  # 5 minutes
        debug: bool = False,
        close_timeout: float = 2.0,
    ):
        """
        Initialize telemetry.

        Args:
            enabled: Enable telemetry (default: False - opt-in)
            endpoint: Telemetry endpoint URL
            flush_interval: Seconds between metric flushes
            debug: Print telemetry events (for testing)
            close_timeout: Seconds close() waits for the flush thread to stop
        """
        self.enabled = enabled and HTTPX_AVAILABLE
        self.endpoint = endpoint
        self.flush_interval = flush_interval
        self.debug = debug
        self.close_timeout = close_timeout

        # Event buffer. Bounded: telemetry must never grow without limit when
        # the collector is unreachable.
        self._events: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._last_flush = time.time()

        # Lifecycle. Delivery happens only on the background thread, which is
        # woken either by the flush interval or by a full buffer.
        self._flush_thread: Optional[threading.Thread] = None
        self._wake = threading.Event()
        self._stopping = False

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
            # Read from the version module directly. Importing `__version__` from
            # the top-level package trips no_implicit_reexport under strict mypy.
            from oilpriceapi.version import __version__
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
            overflow = len(self._events) - self.MAX_BUFFERED_EVENTS
            if overflow > 0:
                # Drop the oldest events rather than grow without bound.
                del self._events[:overflow]
            buffered = len(self._events)

        if self.debug:
            print(f"[Telemetry] {operation}: {duration*1000:.0f}ms success={success}")

        # Ask the background thread to deliver. Never send on the caller's
        # thread: callers include AsyncOilPriceAPI, running on the event loop.
        if buffered >= self.FLUSH_THRESHOLD:
            self._wake.set()

    def _flush(self):
        """
        Deliver buffered events to the telemetry endpoint.

        Only ever called from the background flush thread. It is deliberately
        not gated on ``self.enabled`` so the final flush during close() can
        still drain the buffer after the collector has been disabled.
        """
        if not HTTPX_AVAILABLE:
            return

        with self._lock:
            if not self._events:
                return

            events = self._events.copy()
            self._events.clear()
            self._last_flush = time.time()

        try:
            # Runs on the background flush thread, never on a caller's thread.
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
        """Background thread that owns every telemetry delivery."""
        while True:
            # Wakes early when the buffer fills or when close() is called.
            self._wake.wait(self.flush_interval)
            self._wake.clear()
            self._flush()
            if self._stopping:
                return

    def close(self):
        """
        Stop background delivery and drain what is buffered.

        Idempotent: calling it twice (or on a disabled collector) is a no-op,
        and it never raises. After close() the collector accepts no further
        events and leaves no thread running.
        """
        self._stopping = True
        was_enabled = self.enabled
        self.enabled = False

        thread = self._flush_thread
        self._flush_thread = None
        self._wake.set()

        if not was_enabled or thread is None:
            with self._lock:
                self._events.clear()
            return

        if thread.is_alive() and thread is not threading.current_thread():
            # Bounded: a stuck collector must not hang the caller's shutdown.
            thread.join(timeout=self.close_timeout)


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

    kwargs: Dict[str, Any] = {"enabled": enabled, "debug": debug}
    if endpoint:
        kwargs["endpoint"] = endpoint

    previous = _global_telemetry
    _global_telemetry = Telemetry(**kwargs)

    # Replacing the global config must not leave the previous flush thread
    # running.
    if previous is not None:
        previous.close()


def get_telemetry() -> Optional[Telemetry]:
    """Get global telemetry instance."""
    return _global_telemetry


def track_request(*args, **kwargs):
    """Track request using global telemetry."""
    if _global_telemetry:
        _global_telemetry.track_request(*args, **kwargs)
