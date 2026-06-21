"""
Shared helpers for the agent-subscriptions + market-brief features (#3245).

Keeps the sync and async resources behaving identically: friendly interval
parsing, attribution header construction, and response unwrapping.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

# Default attribution source stamped on subscriptions created via this SDK.
DEFAULT_SOURCE = "sdk-python"

# Friendly interval aliases → seconds. Anything else falls through to the
# numeric parser below (e.g. "30s", "15m", "2h", "1d", or a raw int).
_INTERVAL_ALIASES: Dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "10m": 600,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "hourly": 3600,
    "6h": 21600,
    "12h": 43200,
    "1d": 86400,
    "daily": 86400,
}

_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def normalize_interval(interval: Union[str, int]) -> int:
    """Convert a friendly interval into ``interval_seconds``.

    Accepts an int (returned as-is), a named alias ("5m", "1h", "daily"), or a
    ``<number><unit>`` string where unit is one of s/m/h/d (e.g. "30s", "2h").

    Raises:
        ValueError: If the interval cannot be parsed or is non-positive.
    """
    if isinstance(interval, bool):  # bool is an int subclass; reject explicitly
        raise ValueError(f"Invalid interval: {interval!r}")
    if isinstance(interval, int):
        if interval <= 0:
            raise ValueError(f"interval_seconds must be positive, got {interval}")
        return interval

    if not isinstance(interval, str):
        raise ValueError(f"Invalid interval type: {type(interval).__name__}")

    key = interval.strip().lower()
    if key in _INTERVAL_ALIASES:
        return _INTERVAL_ALIASES[key]

    # Plain integer string e.g. "300".
    if key.isdigit():
        seconds = int(key)
        if seconds <= 0:
            raise ValueError(f"interval_seconds must be positive, got {seconds}")
        return seconds

    # <number><unit> form e.g. "45s", "2h".
    if len(key) >= 2 and key[-1] in _UNIT_SECONDS and key[:-1].isdigit():
        seconds = int(key[:-1]) * _UNIT_SECONDS[key[-1]]
        if seconds <= 0:
            raise ValueError(f"interval_seconds must be positive, got {seconds}")
        return seconds

    raise ValueError(
        f"Unrecognized interval {interval!r}. Use seconds (int), a named alias "
        f"('5m', '1h', 'daily'), or '<n><unit>' where unit is s/m/h/d."
    )


def build_attribution_headers(
    source: Optional[str] = None,
    tool: Optional[str] = None,
) -> Dict[str, str]:
    """Build the X-OPA-Source / X-OPA-Tool attribution headers.

    Defaults ``source`` to ``sdk-python``; omits the tool header when unset.
    """
    headers: Dict[str, str] = {"X-OPA-Source": source or DEFAULT_SOURCE}
    if tool:
        headers["X-OPA-Tool"] = tool
    return headers


def build_create_body(
    codes: List[str],
    interval: Union[str, int],
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the POST /v1/subscriptions request body from friendly args."""
    body: Dict[str, Any] = {
        "codes": list(codes),
        "interval_seconds": normalize_interval(interval),
    }
    if name is not None:
        body["name"] = name
    return body


def unwrap_data(response: Any) -> Dict[str, Any]:
    """Return the ``data`` object from a ``{status, data}`` envelope."""
    if isinstance(response, dict) and "data" in response:
        data = response["data"]
        return data if isinstance(data, dict) else {}
    return response if isinstance(response, dict) else {}
