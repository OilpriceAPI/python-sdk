"""
Live integration smoke for the fuel-surcharge endpoints (#101).

These hit the REAL OilPriceAPI and require a key in the ``OILPRICEAPI_TEST_KEY``
environment variable. They are marked ``live`` and excluded from the default
unit gate (``--ignore=tests/integration``), and skipped when the key is absent.

Read-only. The carrier and service level used for the per-carrier calls are
taken from the list responses rather than hard-coded, so coverage changes on the
API side do not turn this into a false failure. The API does not feature-gate
these routes, so a 403 here is a real failure.
"""

import os
import time
from datetime import date, datetime

import pytest

from oilpriceapi import (
    FuelSurchargeHistoryPage,
    FuelSurchargeRate,
    OilPriceAPI,
    ParcelFuelSurchargeCarrier,
)

TEST_KEY = os.environ.get("OILPRICEAPI_TEST_KEY")

pytestmark = [
    pytest.mark.live,
    pytest.mark.integration,
    pytest.mark.skipif(
        not TEST_KEY,
        reason="OILPRICEAPI_TEST_KEY not set; skipping live fuel-surcharge tests",
    ),
]

# Respect the 1 req/sec rate limit.
RATE_LIMIT_SLEEP = 1.1


@pytest.fixture(scope="module")
def client():
    c = OilPriceAPI(api_key=TEST_KEY)
    yield c
    c.close()


def _assert_rate(rate: FuelSurchargeRate, mode: str) -> None:
    assert isinstance(rate, FuelSurchargeRate)
    assert rate.mode == mode
    assert isinstance(rate.surcharge_percent, float)
    assert type(rate.effective_date) is date
    assert isinstance(rate.retrieved_at, datetime) and rate.retrieved_at.tzinfo is not None
    assert rate.source.startswith("http")


def test_ltl_list_latest_and_history_live(client):
    rates = client.fuel_surcharge.list()
    assert rates, "expected at least one LTL carrier with data"
    for rate in rates:
        _assert_rate(rate, "ltl")
    carrier = rates[0].carrier
    time.sleep(RATE_LIMIT_SLEEP)

    latest = client.fuel_surcharge.latest(carrier)
    _assert_rate(latest, "ltl")
    assert latest.carrier == carrier
    assert latest.effective_date == rates[0].effective_date
    time.sleep(RATE_LIMIT_SLEEP)

    page = client.fuel_surcharge.history(carrier, per_page=2)
    assert isinstance(page, FuelSurchargeHistoryPage)
    assert page.meta.page == 1
    assert page.meta.per_page == 2
    assert page.meta.total_count >= len(page.history)
    assert 1 <= len(page.history) <= 2
    dates = [row.effective_date for row in page.history]
    assert dates == sorted(dates, reverse=True)
    time.sleep(RATE_LIMIT_SLEEP)


def test_parcel_list_and_latest_rate_live(client):
    carriers = client.fuel_surcharge.parcel_list()
    assert carriers, "expected at least one parcel carrier with data"
    for carrier in carriers:
        assert isinstance(carrier, ParcelFuelSurchargeCarrier)
        for rate in carrier.service_levels:
            _assert_rate(rate, "parcel")
            assert rate.service_level
    first = carriers[0]
    level = first.service_levels[0].service_level
    assert level is not None
    time.sleep(RATE_LIMIT_SLEEP)

    rate = client.fuel_surcharge.parcel_latest_rate(first.carrier, level)
    _assert_rate(rate, "parcel")
    assert rate.service_level == level
    assert rate.surcharge_percent == first.service_levels[0].surcharge_percent
    time.sleep(RATE_LIMIT_SLEEP)
