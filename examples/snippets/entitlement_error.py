#!/usr/bin/env python3
import json
import os
from typing import Dict, Union

from oilpriceapi import OilPriceAPI, OilPriceAPIError


def run() -> Dict[str, Union[bool, int]]:
    try:
        with OilPriceAPI(
            api_key=os.environ["OILPRICEAPI_KEY"],
            base_url=os.environ.get("OILPRICEAPI_BASE_URL"),
            max_retries=1,
        ) as client:
            client.prices.get("BRENT_CRUDE_USD")
    except OilPriceAPIError as error:
        if error.status_code != 403:
            raise
        return {"handled": True, "status_code": error.status_code}

    raise RuntimeError("Expected the API to reject the account entitlement")


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
