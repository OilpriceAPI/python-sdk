"""A response that omits ``code`` must not come back wearing the requested code (#127).

The durable, language-agnostic defence against the wrong-commodity bug class
(#112, mcp-server#90) is one consumer-side assertion::

    price = client.prices.get(requested)
    assert price.commodity == requested

Stamping the *requested* code onto a row that did not carry one makes that
assertion pass by construction, on exactly the responses where it needed to
fail. These tests pin the opposite: when the API omits ``code``, the guard
FAILS, in both clients, on every price-read path that shares the mapper.

``PricesResource._to_price`` (``get_all``, ``prices.py``) already treats an
absent code as empty; that is the behaviour being brought into line here.
"""

import asyncio
import inspect

import httpx
import pytest

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI
from oilpriceapi.async_client import AsyncPricesResource
from oilpriceapi.resources.prices import PricesResource

# Not a credential: a fixture string used only against a mock transport.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])

REQUESTED = "LNG_NW_EUROPE_EUR"

# An answered request whose row carries NO `code`. The SDK cannot know which
# instrument this described.
ROW_WITHOUT_CODE = {
    "price": 61.42,
    "currency": "USD",
    "unit": "barrel",
    "created_at": "2026-09-13T12:00:00Z",
}

ROW_WITH_CODE = dict(ROW_WITHOUT_CODE, code="BRENT_CRUDE_USD")


def _flat_handler(payload):
    """Single-code shape: ``{"status": ..., "data": {...}}``."""

    def handler(request):
        return httpx.Response(200, json={"status": "success", "data": payload})

    return handler


def _sync_client(handler):
    client = OilPriceAPI(api_key=FIXTURE_KEY)
    client._client = httpx.Client(
        base_url=client.base_url,
        headers=client.headers,
        transport=httpx.MockTransport(handler),
    )
    return client


def _async_client(handler):
    client = AsyncOilPriceAPI(api_key=FIXTURE_KEY)
    client._client = httpx.AsyncClient(
        base_url=client.base_url,
        headers=client.headers,
        transport=httpx.MockTransport(handler),
    )
    return client


# --------------------------------------------------------------------------
# The point of the issue: the consumer guard must FAIL, not be manufactured.
# --------------------------------------------------------------------------


def test_consumer_guard_fails_when_api_omits_code_sync():
    """`price.commodity == requested` must be False when the API sent no code."""
    client = _sync_client(_flat_handler(ROW_WITHOUT_CODE))

    price = client.prices.get(REQUESTED)

    assert price.commodity != REQUESTED, (
        "the SDK manufactured a confirmation: a row with no `code` came back as "
        f"{price.commodity!r}, so a caller's `commodity == requested` check passes "
        "on a row whose instrument is unknown"
    )
    assert price.commodity == ""
    assert price.value == 61.42


def test_consumer_guard_fails_when_api_omits_code_async():
    async def scenario():
        client = _async_client(_flat_handler(ROW_WITHOUT_CODE))
        try:
            return await client.prices.get(REQUESTED)
        finally:
            await client.close()

    price = asyncio.run(scenario())

    assert (
        price.commodity != REQUESTED
    ), "async client manufactured a confirmation for a row with no `code`"
    assert price.commodity == ""
    assert price.value == 61.42


def test_consumer_guard_fails_on_single_code_batch_path_sync():
    """get_multiple() with one code reaches the same mapper via _fetch_batch."""
    client = _sync_client(_flat_handler(ROW_WITHOUT_CODE))

    prices = client.prices.get_multiple([REQUESTED])

    assert [p.commodity for p in prices] == [""]
    assert all(p.commodity != REQUESTED for p in prices)


def test_consumer_guard_fails_on_single_code_batch_path_async():
    async def scenario():
        client = _async_client(_flat_handler(ROW_WITHOUT_CODE))
        try:
            return await client.prices.get_multiple([REQUESTED])
        finally:
            await client.close()

    prices = asyncio.run(scenario())

    assert [p.commodity for p in prices] == [""]
    assert all(p.commodity != REQUESTED for p in prices)


# --------------------------------------------------------------------------
# A code the API DID send is still honoured — including when it disagrees
# with the request, which is the #112 signal the guard exists to surface.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("row", [ROW_WITH_CODE])
def test_supplied_code_still_wins_sync(row):
    client = _sync_client(_flat_handler(row))

    price = client.prices.get(REQUESTED)

    assert price.commodity == "BRENT_CRUDE_USD"
    assert price.commodity != REQUESTED


@pytest.mark.parametrize("row", [ROW_WITH_CODE])
def test_supplied_code_still_wins_async(row):
    async def scenario():
        client = _async_client(_flat_handler(row))
        try:
            return await client.prices.get(REQUESTED)
        finally:
            await client.close()

    price = asyncio.run(scenario())

    assert price.commodity == "BRENT_CRUDE_USD"
    assert price.commodity != REQUESTED


# --------------------------------------------------------------------------
# Sync/async parity — the two clients must not drift again.
# --------------------------------------------------------------------------


def test_sync_and_async_mappers_agree_on_missing_code():
    sync_price = PricesResource._to_price(dict(ROW_WITHOUT_CODE))
    async_price = AsyncPricesResource._to_price(dict(ROW_WITHOUT_CODE))

    assert sync_price.commodity == async_price.commodity == ""


def test_sync_and_async_mappers_share_a_signature():
    """No `fallback_code` hook on one side and not the other."""
    assert inspect.signature(PricesResource._to_price) == inspect.signature(
        AsyncPricesResource._to_price
    )
    assert "fallback_code" not in inspect.signature(PricesResource._to_price).parameters


def test_all_price_read_paths_agree_with_get_all():
    """get_all (prices.py:207) already maps an absent code to ""; so must the rest."""
    sync_client = _sync_client(_flat_handler(ROW_WITHOUT_CODE))

    async def scenario():
        client = _async_client(_flat_handler(ROW_WITHOUT_CODE))
        try:
            return [
                (await client.prices.get(REQUESTED)).commodity,
                (await client.prices.get_multiple([REQUESTED]))[0].commodity,
            ]
        finally:
            await client.close()

    observed = [
        sync_client.prices.get(REQUESTED).commodity,
        sync_client.prices.get_multiple([REQUESTED])[0].commodity,
        *asyncio.run(scenario()),
    ]

    assert observed == ["", "", "", ""], observed
