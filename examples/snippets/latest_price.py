#!/usr/bin/env python3
import json
import os
from typing import Dict, Union

from oilpriceapi import OilPriceAPI


def run() -> Dict[str, Union[str, None]]:
    with OilPriceAPI(
        api_key=os.environ["OILPRICEAPI_KEY"],
        base_url=os.environ.get("OILPRICEAPI_BASE_URL"),
        max_retries=1,
    ) as client:
        price = client.prices.get("BRENT_CRUDE_USD")

    return {
        "commodity": price.commodity,
        "currency": price.currency,
        "value_type": type(price.value).__name__,
        "timestamp_type": type(price.timestamp).__name__,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
