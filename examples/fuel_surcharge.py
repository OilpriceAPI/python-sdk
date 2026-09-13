"""Carrier fuel surcharges: LTL and parcel (#101).

Usage:
    OILPRICEAPI_KEY=... python examples/fuel_surcharge.py

Prints the latest LTL surcharge per carrier, one carrier's recent weekly
history, and the latest parcel surcharge per service level. Every row shows the
carrier's effective date and where the value was retrieved from.
"""

import os

from oilpriceapi import OilPriceAPI
from oilpriceapi.exceptions import DataNotFoundError


def main() -> None:
    with OilPriceAPI(api_key=os.environ["OILPRICEAPI_KEY"]) as client:
        print("LTL carriers")
        rates = client.fuel_surcharge.list()
        for rate in rates:
            print(
                f"  {rate.carrier:<22} {rate.surcharge_percent:>6.2f}%  "
                f"effective {rate.effective_date}  retrieved {rate.retrieved_at:%Y-%m-%d}"
            )

        if rates:
            carrier = rates[0].carrier
            page = client.fuel_surcharge.history(carrier, per_page=4)
            print(f"\n{carrier} history ({page.meta.total_count} weeks on record)")
            for row in page.history:
                diesel = "n/a" if row.doe_diesel_price is None else f"${row.doe_diesel_price:.3f}"
                print(f"  {row.effective_date}  {row.surcharge_percent:.2f}%  DOE diesel {diesel}")
            print(f"  source: {page.history[0].source}" if page.history else "  no rows")

        print("\nParcel carriers")
        for parcel in client.fuel_surcharge.parcel_list():
            for rate in parcel.service_levels:
                print(
                    f"  {parcel.carrier:<6} {rate.service_level:<26} "
                    f"{rate.surcharge_percent:>6.2f}%  effective {rate.effective_date}"
                )

        try:
            client.fuel_surcharge.latest("fedex-freight")
        except DataNotFoundError as error:
            print(f"\nNot covered: {error.message}")
            print(f"Covered carriers: {', '.join(error.suggestions)}")


if __name__ == "__main__":
    main()
