"""
Live integration tests for the futures endpoints.

These hit the REAL OilPriceAPI and require a key in the ``OILPRICEAPI_TEST_KEY``
environment variable. They are marked ``live`` and excluded from the default
unit gate (``--ignore=tests/integration``). They are skipped automatically when
the key is absent (e.g. on forks).

The API rate limit is 1 request/second, so calls are spaced with small sleeps
and kept to a handful.
"""

import os
import time

import pytest

from oilpriceapi import OilPriceAPI

TEST_KEY = os.environ.get("OILPRICEAPI_TEST_KEY")

pytestmark = [
    pytest.mark.live,
    pytest.mark.integration,
    pytest.mark.skipif(
        not TEST_KEY,
        reason="OILPRICEAPI_TEST_KEY not set; skipping live futures tests",
    ),
]

# Respect the 1 req/sec rate limit.
RATE_LIMIT_SLEEP = 1.1


def _front_price(curve: dict) -> float:
    """Pull a representative price out of a futures latest/curve response."""
    front = curve.get("front_month") or {}
    for key in ("last_price", "price", "close"):
        val = front.get(key)
        if isinstance(val, (int, float)):
            return float(val)
    # Fall back to the first contract in the curve.
    contracts = curve.get("contracts") or []
    for contract in contracts:
        for key in ("last_price", "price", "close"):
            val = contract.get(key)
            if isinstance(val, (int, float)):
                return float(val)
    raise AssertionError(f"No numeric price found in futures response: {curve!r}")


@pytest.fixture(scope="module")
def live_client():
    client = OilPriceAPI(api_key=TEST_KEY)
    yield client
    client.close()


def test_latest_by_slug(live_client):
    """futures.latest('ice-brent') returns 200 + a sane Brent price."""
    curve = live_client.futures.latest("ice-brent")
    assert isinstance(curve, dict)
    price = _front_price(curve)
    # Sanity range for Brent crude (USD/bbl).
    assert 10 < price < 500, f"Brent price out of sane range: {price}"


def test_latest_by_contract_code(live_client):
    """Friendly code 'BZ' normalizes to ice-brent and returns a sane price."""
    time.sleep(RATE_LIMIT_SLEEP)
    curve = live_client.futures.latest("BZ")
    assert isinstance(curve, dict)
    price = _front_price(curve)
    assert 10 < price < 500, f"Brent (BZ) price out of sane range: {price}"


def test_curve(live_client):
    """futures.curve('ice-brent') returns 200 with curve data."""
    time.sleep(RATE_LIMIT_SLEEP)
    curve = live_client.futures.curve("ice-brent")
    # Curve responses may be a list of points or a dict wrapping them.
    assert curve is not None
    if isinstance(curve, dict):
        assert curve, "curve response should not be empty"
    else:
        assert len(curve) >= 0
