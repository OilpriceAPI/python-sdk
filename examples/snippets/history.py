#!/usr/bin/env python3
import json
from typing import Dict, Union

from _shared import base_url

from oilpriceapi import OilPriceAPI


def run() -> Dict[str, Union[str, int]]:
    with OilPriceAPI(base_url=base_url(), max_retries=1) as client:
        history = client.historical.get(
            commodity="BRENT_CRUDE_USD",
            interval="daily",
            per_page=5,
        )

    first = history.data[0]
    return {
        "commodity": first.commodity,
        "count": len(history.data),
        "value_type": type(first.value).__name__,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
