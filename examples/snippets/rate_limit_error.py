#!/usr/bin/env python3
import json
from typing import Dict, Union

from _shared import base_url

from oilpriceapi import OilPriceAPI, RateLimitError


def run() -> Dict[str, Union[bool, int]]:
    try:
        with OilPriceAPI(base_url=base_url(), max_retries=1) as client:
            client.prices.get("BRENT_CRUDE_USD")
    except RateLimitError as error:
        return {"handled": True, "status_code": error.status_code or 429}

    raise RuntimeError("Expected the API to enforce its request limit")


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
