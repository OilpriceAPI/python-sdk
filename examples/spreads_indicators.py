"""
Server-calculated spreads and market indicators (#99).

Requires OILPRICEAPI_KEY for an account on a paid plan (Developer and above);
other plans receive PermissionDeniedError with code PREMIUM_REQUIRED.

Run:  python examples/spreads_indicators.py
"""

import os

from oilpriceapi import OilPriceAPI
from oilpriceapi.exceptions import DataNotFoundError, PermissionDeniedError


def main() -> None:
    with OilPriceAPI(api_key=os.environ["OILPRICEAPI_KEY"]) as client:
        try:
            crack = client.spreads.crack(spread_type="3-2-1")
        except PermissionDeniedError as error:
            print(f"Calculated metrics are not enabled for this plan: {error.code}")
            return

        # Units and timestamps come from the response; staleness is only
        # flagged when the server flags it (None means "not flagged").
        print(f"3-2-1 crack: {crack.value} {crack.unit} as of {crack.timestamp.isoformat()}")
        if crack.data_stale:
            print(f"  stale: {crack.stale_warning}")

        history = client.spreads.crack_historical(start_date="2026-08-01")
        print(
            f"History requested {history.period.start}..{history.period.end}, "
            f"returned {history.coverage.observations} days "
            f"({history.coverage.from_}..{history.coverage.to})"
        )

        for pair in client.spreads.basis_all():
            print(f"{pair.spread_name}: {pair.value} {pair.unit} ({pair.signal})")

        parity = client.indicators.fuel_switching()
        print(f"Gas at {parity.oil_parity.ratio_pct}% of oil parity: {parity.oil_parity.signal}")

        try:
            context = client.indicators.price_context("BRENT_CRUDE_USD", related_spreads=True)
        except DataNotFoundError as error:
            print(f"No price context: {error}")
        else:
            print(f"Brent 1y percentile: {context.context.percentile_1y}")
            for spread in context.related_spreads or []:
                print(f"  related {spread.name}: {spread.value}")

        cot = client.indicators.cftc_positioning(commodity="WTI")
        print(
            f"WTI managed-money net {cot.positioning.speculative.net} "
            f"(report {cot.report_date}, signal {cot.signal})"
        )


if __name__ == "__main__":
    main()
