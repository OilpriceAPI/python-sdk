#!/usr/bin/env python3
import json
from typing import Dict, Union

from _shared import base_url

from oilpriceapi import OilPriceAPI


def run() -> Dict[str, Union[str, None]]:
    with OilPriceAPI(base_url=base_url(), max_retries=1) as client:
        price = client.prices.get("BRENT_CRUDE_USD")

    return {
        "commodity": price.commodity,
        "currency": price.currency,
        "value_type": type(price.value).__name__,
        "timestamp_type": type(price.timestamp).__name__,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
