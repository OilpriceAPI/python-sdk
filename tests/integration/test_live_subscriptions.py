"""
Live integration tests for market-brief + subscriptions (#3245).

These hit the REAL OilPriceAPI and require a key in the ``OILPRICEAPI_TEST_KEY``
environment variable. They are marked ``live`` and excluded from the default
unit gate (``--ignore=tests/integration``). They are skipped automatically when
the key is absent (e.g. on forks / CI without the secret).

Read-only by default: we fetch a market brief and list subscriptions. No
subscriptions are created or deleted, so nothing is written to production.

The API rate limit is 1 request/second, so calls are spaced with small sleeps.
"""

import os
import time

import pytest

from oilpriceapi import MarketBrief, OilPriceAPI

TEST_KEY = os.environ.get("OILPRICEAPI_TEST_KEY")

pytestmark = [
    pytest.mark.live,
    pytest.mark.integration,
    pytest.mark.skipif(
        not TEST_KEY,
        reason="OILPRICEAPI_TEST_KEY not set; skipping live subscription tests",
    ),
]

RATE_LIMIT_SLEEP = 1.1


@pytest.fixture
def client():
    c = OilPriceAPI(api_key=TEST_KEY)
    yield c
    c.close()


def test_market_brief_live(client):
    """market_brief returns a brief with a price for a known commodity."""
    brief = client.market_brief(["BRENT_CRUDE_USD"])
    assert isinstance(brief, MarketBrief)
    assert brief.commodities, "expected at least one commodity in the brief"
    commodity = brief.commodities[0]
    assert commodity.code
    assert commodity.price is not None and commodity.price > 0
    time.sleep(RATE_LIMIT_SLEEP)


def test_subscriptions_list_live(client):
    """subscriptions.list() returns a list (possibly empty) without error."""
    subs = client.subscriptions.list()
    assert isinstance(subs, list)
