"""Diesel `state` must come back the same from both clients, and uppercase.

Two defects, one line apart.

1. PARITY. `resources/diesel.py:116-118` fills a missing `state` from the
   envelope's `location.state_code`, falling back to what the caller asked for.
   `async_resources.py` has no such block at all, so the SAME response that the
   sync client parses makes the async client raise "state: Field required".
   The `regional_average` envelope carries `region` ("california"), not
   `state`, so this is the ordinary path, not an edge case.

2. CASING. The sync branch takes `location["state_code"]` verbatim while its
   own fallback uppercases. For one caller input the same field comes back
   'ca' on one branch and 'CA' on the other (#123, "Minor, while in the area").
"""

import asyncio

import httpx
import pytest
import respx

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI

BASE = "https://api.oilpriceapi.com"

COMMON = {
    "price": 3.91,
    "currency": "USD",
    "unit": "gallon",
    "granularity": "state",
    "source": "EIA",
    "updated_at": "2026-09-13T00:00:00Z",
}

# The envelope carries `region`, not `state`; the code lives in `location`,
# lowercase, as the API sends it.
WITH_LOCATION = {
    "regional_average": dict(COMMON, region="california"),
    "location": {"state_code": "ca", "region": "california"},
}

# No location block at all -- the fallback path.
WITHOUT_LOCATION = {"regional_average": dict(COMMON, region="california")}


def _sync_state(payload, asked="ca"):
    with respx.mock(base_url=BASE, assert_all_called=False) as m:
        m.get(path__startswith="/v1/diesel-prices").mock(
            return_value=httpx.Response(200, json=payload)
        )
        c = OilPriceAPI(api_key="k", base_url=BASE)
        return c.diesel.get_price(asked).state


def _async_state(payload, asked="ca"):
    async def go():
        with respx.mock(base_url=BASE, assert_all_called=False) as m:
            m.get(path__startswith="/v1/diesel-prices").mock(
                return_value=httpx.Response(200, json=payload)
            )
            c = AsyncOilPriceAPI(api_key="k", base_url=BASE)
            return (await c.diesel.get_price(asked)).state

    return asyncio.run(go())


# --- 1. parity --------------------------------------------------------------

@pytest.mark.parametrize(
    "payload", [WITH_LOCATION, WITHOUT_LOCATION], ids=["with_location", "no_location"]
)
def test_sync_and_async_agree_on_state(payload):
    assert _sync_state(payload) == _async_state(payload)


@pytest.mark.parametrize(
    "payload", [WITH_LOCATION, WITHOUT_LOCATION], ids=["with_location", "no_location"]
)
def test_async_does_not_raise_on_an_envelope_sync_parses(payload):
    """The async client must not reject a response the sync client accepts."""
    assert _async_state(payload)


# --- 2. casing --------------------------------------------------------------

def test_sync_state_is_uppercase_from_the_location_block():
    assert _sync_state(WITH_LOCATION) == "CA"


def test_sync_state_is_uppercase_from_the_fallback():
    assert _sync_state(WITHOUT_LOCATION) == "CA"


def test_async_state_is_uppercase_from_the_location_block():
    assert _async_state(WITH_LOCATION) == "CA"


def test_async_state_is_uppercase_from_the_fallback():
    assert _async_state(WITHOUT_LOCATION) == "CA"


def test_both_branches_of_each_client_agree():
    """The whole point: one caller input, one answer, whichever branch ran."""
    assert (
        _sync_state(WITH_LOCATION)
        == _sync_state(WITHOUT_LOCATION)
        == _async_state(WITH_LOCATION)
        == _async_state(WITHOUT_LOCATION)
        == "CA"
    )


def test_an_explicit_state_in_the_payload_still_wins():
    """Don't clobber a state the server actually sent."""
    payload = {"regional_average": dict(COMMON, state="TX")}
    assert _sync_state(payload, asked="ca") == "TX"
    assert _async_state(payload, asked="ca") == "TX"
