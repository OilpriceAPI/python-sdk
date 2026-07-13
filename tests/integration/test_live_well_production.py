"""
Live integration smoke for the well-production endpoints (#50).

These hit the REAL OilPriceAPI and require a key in the ``OILPRICEAPI_TEST_KEY``
environment variable. They are marked ``live`` and excluded from the default
unit gate (``--ignore=tests/integration``). They are skipped automatically when
the key is absent (e.g. on forks).

The well-production endpoints are gated on the Drilling Intelligence feature
(HTTP 403 ``ENTERPRISE_REQUIRED`` otherwise). The CI test key is a free-tier
account, so BOTH outcomes are valid coverage here:

* 200 -> assert the summary envelope shape (national + top_states), or
* 403 -> assert the SDK surfaces the entitlement gate as OilPriceAPIError.

Either way the route must exist (a 404 is a real failure).
"""

import os
import time

import pytest

from oilpriceapi import OilPriceAPI
from oilpriceapi.exceptions import OilPriceAPIError

TEST_KEY = os.environ.get("OILPRICEAPI_TEST_KEY")

pytestmark = [
    pytest.mark.live,
    pytest.mark.integration,
    pytest.mark.skipif(
        not TEST_KEY,
        reason="OILPRICEAPI_TEST_KEY not set; skipping live well-production tests",
    ),
]

# Respect the 1 req/sec rate limit.
RATE_LIMIT_SLEEP = 1.1


@pytest.fixture(scope="module")
def live_client():
    client = OilPriceAPI(api_key=TEST_KEY)
    yield client
    client.close()


def test_summary_route_exists(live_client):
    """GET /v1/well-production returns the summary envelope or a 403 gate."""
    time.sleep(RATE_LIMIT_SLEEP)
    try:
        summary = live_client.well_production.summary()
    except OilPriceAPIError as exc:
        # Free-tier keys hit the Drilling Intelligence plan gate — that is
        # a valid outcome, but the route must exist (404 would surface as
        # DataNotFoundError with status 404).
        assert exc.status_code == 403, f"unexpected error: {exc}"
        return

    assert "national" in summary
    assert "top_states" in summary
    if summary["top_states"]:
        state = summary["top_states"][0]
        assert "state" in state
        assert "oil_bbl" in state


def test_states_route_exists(live_client):
    """GET /v1/well-production/states returns states or a 403 gate."""
    time.sleep(RATE_LIMIT_SLEEP)
    try:
        result = live_client.well_production.states()
    except OilPriceAPIError as exc:
        assert exc.status_code == 403, f"unexpected error: {exc}"
        return

    assert "states" in result
    assert result["count"] == len(result["states"])
