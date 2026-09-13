"""
Shared helpers for the agent-subscriptions + market-brief features (#3245).

Keeps the sync and async resources behaving identically: friendly interval
parsing, attribution header construction, and response unwrapping.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from .exceptions import SubscriptionIntervalError, ValidationError

if TYPE_CHECKING:
    from .models import Subscription

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


def _refuse(message: str, field: Optional[str], value: Any) -> ValidationError:
    """A local input refusal. No request was sent, so there is no HTTP status."""
    return ValidationError(message=message, field=field, value=value, status_code=None)


def _interval_refusal(message: str, interval: Any) -> SubscriptionIntervalError:
    # Dual-base (ValidationError + ValueError): this path raised ValueError
    # before #100, and callers may catch that.
    return SubscriptionIntervalError(
        message=message, field="interval", value=interval, status_code=None
    )


def normalize_interval(interval: Union[str, int]) -> int:
    """Convert a friendly interval into ``interval_seconds``.

    Accepts an int (returned as-is), a named alias ("5m", "1h", "daily"), or a
    ``<number><unit>`` string where unit is one of s/m/h/d (e.g. "30s", "2h").

    Raises:
        SubscriptionIntervalError: If the interval cannot be parsed or is
            non-positive. It is both a ``ValidationError`` (``field="interval"``,
            ``status_code=None``) and, for compatibility, a ``ValueError``.
    """
    if isinstance(interval, bool):  # bool is an int subclass; reject explicitly
        raise _interval_refusal(f"Invalid interval: {interval!r}", interval)
    if isinstance(interval, int):
        if interval <= 0:
            raise _interval_refusal(f"interval_seconds must be positive, got {interval}", interval)
        return interval

    if not isinstance(interval, str):
        raise _interval_refusal(f"Invalid interval type: {type(interval).__name__}", interval)

    key = interval.strip().lower()
    if key in _INTERVAL_ALIASES:
        return _INTERVAL_ALIASES[key]

    # Plain integer string e.g. "300".
    if key.isdigit():
        seconds = int(key)
        if seconds <= 0:
            raise _interval_refusal(f"interval_seconds must be positive, got {seconds}", interval)
        return seconds

    # <number><unit> form e.g. "45s", "2h".
    if len(key) >= 2 and key[-1] in _UNIT_SECONDS and key[:-1].isdigit():
        seconds = int(key[:-1]) * _UNIT_SECONDS[key[-1]]
        if seconds <= 0:
            raise _interval_refusal(f"interval_seconds must be positive, got {seconds}", interval)
        return seconds

    raise _interval_refusal(
        f"Unrecognized interval {interval!r}. Use seconds (int), a named alias "
        f"('5m', '1h', 'daily'), or '<n><unit>' where unit is s/m/h/d.",
        interval,
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


# Watch.status is a string enum on the server: { active, paused }.
VALID_STATUSES = ("active", "paused")

# Watch ids are UUIDs. Anything outside this alphabet would change the URL the
# request goes to (a "/" reaches another route, "?" or "#" rewrites the query),
# so it is refused before a request is built.
_SUBSCRIPTION_ID = re.compile(r"[A-Za-z0-9_-]+")


def validate_subscription_id(subscription_id: Any) -> str:
    """Return ``subscription_id`` if it can be placed in a URL path segment.

    Raises:
        ValidationError: ``field="subscription_id"``, ``status_code=None``, if
            the id is not a non-empty string of letters, digits, ``-`` or
            ``_``. Nothing is sent to the API.
    """
    if not isinstance(subscription_id, str) or not _SUBSCRIPTION_ID.fullmatch(subscription_id):
        raise _refuse(
            f"Invalid subscription id {subscription_id!r}: expected the id returned "
            f"by subscriptions.list() or subscriptions.create().",
            "subscription_id",
            subscription_id,
        )
    return subscription_id


def build_update_body(
    name: Optional[str] = None,
    codes: Optional[List[str]] = None,
    interval: Optional[Union[str, int]] = None,
    deliver_webhook: Optional[bool] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the PATCH /v1/subscriptions/:id body from the fields given.

    Only arguments that are not ``None`` are sent, so an update never resets a
    field the caller did not mention.

    Raises:
        ValidationError: ``status_code=None``, with ``field`` naming the invalid
            argument (``None`` when no field is given at all). Nothing is sent.
    """
    body: Dict[str, Any] = {}
    if name is not None:
        if not isinstance(name, str):
            raise _refuse(f"name must be a string, got {type(name).__name__}", "name", name)
        body["name"] = name
    if codes is not None:
        if isinstance(codes, (str, bytes)) or not isinstance(codes, (list, tuple)):
            raise _refuse(
                "codes must be a list of commodity codes, e.g. ['BRENT_CRUDE_USD']", "codes", codes
            )
        if not codes:
            raise _refuse("codes must contain at least one commodity code", "codes", codes)
        if not all(isinstance(code, str) and code.strip() for code in codes):
            raise _refuse("every code must be a non-empty string", "codes", codes)
        body["codes"] = list(codes)
    if interval is not None:
        try:
            body["interval_seconds"] = normalize_interval(interval)
        except SubscriptionIntervalError as error:
            # update() is new in #100: no caller relies on ValueError here, so
            # it gets the plain ValidationError every new refusal uses.
            raise _refuse(error.message, "interval", interval) from None
    if deliver_webhook is not None:
        if not isinstance(deliver_webhook, bool):
            raise _refuse(
                f"deliver_webhook must be True or False, got {deliver_webhook!r}",
                "deliver_webhook",
                deliver_webhook,
            )
        body["deliver_webhook"] = deliver_webhook
    if status is not None:
        if status not in VALID_STATUSES:
            raise _refuse(
                f"status must be one of {', '.join(VALID_STATUSES)}, got {status!r}",
                "status",
                status,
            )
        body["status"] = status
    if not body:
        raise _refuse(
            "update() needs at least one of: name, codes, interval, deliver_webhook, status",
            None,
            None,
        )
    return body


def unwrap_subscription(response: Any, *, subject: str) -> "Subscription":
    """Return the typed ``data.subscription`` record from a success body.

    Every single-subscription endpoint (show, create, update, pause, resume)
    answers ``{"status": "success", "data": {"subscription": {...}}}``.

    Raises:
        OilPriceAPIError: ``code="MALFORMED_RESPONSE"`` when the record is
            missing, is not an object, or lacks a required field. A malformed
            success is reported, never turned into a partial or invented record.
    """
    from pydantic import ValidationError as PydanticValidationError

    from .exceptions import OilPriceAPIError
    from .models import Subscription

    data = response.get("data") if isinstance(response, dict) else None
    record = data.get("subscription") if isinstance(data, dict) else None
    if not isinstance(record, dict):
        raise OilPriceAPIError(
            f"Malformed {subject} response: expected data.subscription to be an object",
            code="MALFORMED_RESPONSE",
            raw_body=response,
        )
    try:
        return Subscription(**record)
    except PydanticValidationError as error:
        raise OilPriceAPIError(
            f"Malformed {subject} response: {error.error_count()} invalid or missing "
            f"subscription field(s): "
            + ", ".join(".".join(str(part) for part in item["loc"]) for item in error.errors()),
            code="MALFORMED_RESPONSE",
            raw_body=response,
        ) from error


def unwrap_data(response: Any) -> Dict[str, Any]:
    """Return the ``data`` object from a ``{status, data}`` envelope."""
    if isinstance(response, dict) and "data" in response:
        data = response["data"]
        return data if isinstance(data, dict) else {}
    return response if isinstance(response, dict) else {}
