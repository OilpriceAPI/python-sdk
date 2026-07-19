#!/usr/bin/env python3
import json
import os
from typing import Dict, Union

from oilpriceapi import OilPriceAPI


def run() -> Dict[str, Union[str, int]]:
    with OilPriceAPI(
        api_key=os.environ["OILPRICEAPI_KEY"],
        base_url=os.environ.get("OILPRICEAPI_BASE_URL"),
        max_retries=1,
    ) as client:
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
