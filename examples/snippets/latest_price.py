#!/usr/bin/env python3
import json
import math
import os
from typing import Any, Dict

from oilpriceapi import OilPriceAPI


def run() -> Dict[str, Any]:
    with OilPriceAPI(
        api_key=os.environ["OILPRICEAPI_KEY"],
        base_url=os.environ.get("OILPRICEAPI_BASE_URL"),
        max_retries=1,
    ) as client:
        payload = client.request(
            "GET",
            "/v1/prices/latest",
            params={"by_code": "BRENT_CRUDE_USD"},
            timeout=30,
        )

    record = payload.get("data")
    if not isinstance(record, dict):
        raise RuntimeError("EMPTY_RESPONSE: no price record returned")

    price = record.get("price")
    if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price):
        raise RuntimeError("MALFORMED_RESPONSE: price is not a finite number")

    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    source = record.get("source") or metadata.get("source")
    timestamp_field = next(
        (
            field
            for field in ("as_of", "source_timestamp", "created_at", "updated_at")
            if isinstance(record.get(field), str) and record[field].strip()
        ),
        None,
    )
    required_text = {
        "commodity": record.get("code"),
        "currency": record.get("currency"),
        "unit": record.get("unit"),
        "source": source,
    }
    if timestamp_field is None or any(
        not isinstance(value, str) or not value.strip() for value in required_text.values()
    ):
        raise RuntimeError("MALFORMED_RESPONSE: source context is incomplete")

    freshness = record.get("data_status")
    if freshness is not None and not isinstance(freshness, str):
        raise RuntimeError("MALFORMED_RESPONSE: freshness is not text")

    return {
        **required_text,
        "api_timestamp": record[timestamp_field],
        "timestamp_field": timestamp_field,
        "value_type": type(price).__name__,
        "freshness": freshness,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
