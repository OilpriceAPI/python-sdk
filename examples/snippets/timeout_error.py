#!/usr/bin/env python3
import json
from typing import Dict, Union

from _shared import base_url

from oilpriceapi import OilPriceAPI, TimeoutError


def run() -> Dict[str, Union[bool, str]]:
    try:
        with OilPriceAPI(base_url=base_url(), max_retries=1, timeout=0.05) as client:
            client.prices.get("BRENT_CRUDE_USD")
    except TimeoutError:
        return {"handled": True, "error_type": "TimeoutError"}

    raise RuntimeError("Expected the request to time out")


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
