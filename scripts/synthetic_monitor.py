#!/usr/bin/env python3
"""Run a bounded, privacy-safe production smoke through the Python SDK.

The script is intentionally one-shot so a scheduler owns cadence, retries, and
alerting. It emits a machine-readable receipt and never prints credentials,
response bodies, request URLs, or exception messages.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from oilpriceapi import OilPriceAPI
from oilpriceapi.version import SDK_VERSION

Receipt = Dict[str, Any]
Check = Callable[[OilPriceAPI], Dict[str, Any]]


def _latest_price_check(client: OilPriceAPI) -> Dict[str, Any]:
    price = client.prices.get("BRENT_CRUDE_USD")
    if (
        isinstance(price.value, bool)
        or not isinstance(price.value, (int, float))
        or not math.isfinite(price.value)
    ):
        raise ValueError("latest price is not finite")
    if not isinstance(price.currency, str) or not price.currency:
        raise ValueError("latest price currency is missing")
    if not isinstance(price.unit, str) or not price.unit:
        raise ValueError("latest price unit is missing")
    if price.timestamp is None:
        raise ValueError("latest price timestamp is missing")
    return {
        "commodity": price.commodity,
        "currency_present": True,
        "numeric_value": True,
        "source_timestamp_present": True,
        "unit_present": True,
    }


def _historical_check(client: OilPriceAPI) -> Dict[str, Any]:
    history = client.historical.get(
        commodity="BRENT_CRUDE_USD",
        interval="daily",
        per_page=5,
    )
    if not history.data:
        raise ValueError("historical response is empty")
    if any(
        isinstance(record.value, bool)
        or not isinstance(record.value, (int, float))
        or not math.isfinite(record.value)
        for record in history.data
    ):
        raise ValueError("historical response contains a non-finite value")
    return {
        "commodity": history.data[0].commodity,
        "nonempty": True,
        "records_checked": len(history.data),
    }


def _run_check(
    name: str,
    check: Check,
    client: OilPriceAPI,
    *,
    monotonic: Callable[[], float],
    budget_seconds: float,
) -> Receipt:
    started = monotonic()
    try:
        details = check(client)
        duration = monotonic() - started
        if duration > budget_seconds:
            return {
                "name": name,
                "status": "fail",
                "duration_seconds": round(duration, 3),
                "error_type": "TimeBudgetExceeded",
            }
        return {
            "name": name,
            "status": "pass",
            "duration_seconds": round(duration, 3),
            "details": details,
        }
    except Exception as exc:  # noqa: BLE001 - capture SDK/network failures safely
        return {
            "name": name,
            "status": "fail",
            "duration_seconds": round(monotonic() - started, 3),
            "error_type": type(exc).__name__,
        }


def run_synthetic_checks(
    api_key: str,
    *,
    base_url: Optional[str] = None,
    client_factory: Callable[..., OilPriceAPI] = OilPriceAPI,
    monotonic: Callable[[], float] = time.monotonic,
) -> Receipt:
    """Run the latest-price and bounded-history checks once."""
    checked_at = datetime.now(timezone.utc).isoformat()
    try:
        with client_factory(
            api_key=api_key,
            base_url=base_url,
            timeout=20,
            max_retries=1,
        ) as client:
            checks = [
                _run_check(
                    "latest_price",
                    _latest_price_check,
                    client,
                    monotonic=monotonic,
                    budget_seconds=30,
                ),
                _run_check(
                    "bounded_history",
                    _historical_check,
                    client,
                    monotonic=monotonic,
                    budget_seconds=30,
                ),
            ]
    except Exception as exc:  # noqa: BLE001 - sanitize initialization failures
        checks = [
            {
                "name": "client_initialization",
                "status": "fail",
                "duration_seconds": 0.0,
                "error_type": type(exc).__name__,
            }
        ]

    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    return {
        "schema_version": 1,
        "status": status,
        "checked_at": checked_at,
        "sdk_version": SDK_VERSION,
        "checks": checks,
    }


def _write_receipt(receipt: Receipt, output: Optional[str]) -> None:
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if output:
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        help="Optional path for the JSON receipt; the receipt is always printed.",
    )
    args = parser.parse_args()

    api_key = os.environ.get("OILPRICEAPI_KEY")
    if not api_key:
        receipt: Receipt = {
            "schema_version": 1,
            "status": "fail",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "sdk_version": SDK_VERSION,
            "checks": [
                {
                    "name": "configuration",
                    "status": "fail",
                    "duration_seconds": 0.0,
                    "error_type": "MissingAPIKey",
                }
            ],
        }
    else:
        receipt = run_synthetic_checks(
            api_key,
            base_url=os.environ.get("OILPRICEAPI_BASE_URL"),
        )

    _write_receipt(receipt, args.output)
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
