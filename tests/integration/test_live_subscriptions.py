"""
Live integration tests for market-brief + subscriptions (#3245).

These hit the REAL OilPriceAPI and require a key in the ``OILPRICEAPI_TEST_KEY``
environment variable. They are marked ``live`` and excluded from the default
unit gate (``--ignore=tests/integration``). They are skipped automatically when
the key is absent (e.g. on forks / CI without the secret).

The brief and list tests are read-only. ``test_subscription_lifecycle_live``
writes: it creates ONE watch of its own on the key's account, walks it through
get / update / pause / resume, and deletes it in a ``finally`` that runs even
when an assertion fails. It never reads, changes or deletes any other watch.
A subscription here is an agent "watch", not a billing subscription: nothing
in this lifecycle changes what the account is charged.

The API rate limit is 1 request/second, so calls are spaced with small sleeps.
"""

import os
import time
import uuid

import pytest

from oilpriceapi import MarketBrief, OilPriceAPI
from oilpriceapi.exceptions import DataNotFoundError

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


def test_subscription_lifecycle_live(client):
    """create -> get -> update -> pause -> resume -> delete, cleaned up always."""
    name = f"sdk-python-lifecycle-{uuid.uuid4().hex[:12]}"
    created = client.subscriptions.create(["BRENT_CRUDE_USD"], interval="daily", name=name)
    watch_id = created.id
    deleted = False
    try:
        assert created.name == name
        assert created.codes == ["BRENT_CRUDE_USD"]
        assert created.interval_seconds == 86400
        time.sleep(RATE_LIMIT_SLEEP)

        fetched = client.subscriptions.get(watch_id)
        assert fetched.id == watch_id
        assert fetched.created_at == created.created_at
        time.sleep(RATE_LIMIT_SLEEP)

        renamed = client.subscriptions.update(watch_id, name=f"{name}-renamed")
        assert renamed.id == watch_id
        assert renamed.name == f"{name}-renamed"
        time.sleep(RATE_LIMIT_SLEEP)

        paused = client.subscriptions.pause(watch_id)
        assert paused.status == "paused"
        time.sleep(RATE_LIMIT_SLEEP)

        resumed = client.subscriptions.resume(watch_id)
        assert resumed.status == "active"
        assert resumed.next_run_at is not None
        time.sleep(RATE_LIMIT_SLEEP)

        assert client.subscriptions.delete(watch_id) is True
        deleted = True
        time.sleep(RATE_LIMIT_SLEEP)

        with pytest.raises(DataNotFoundError):
            client.subscriptions.get(watch_id)
    finally:
        if not deleted:
            time.sleep(RATE_LIMIT_SLEEP)
            try:
                client.subscriptions.delete(watch_id)
            except DataNotFoundError:
                pass
