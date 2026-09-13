"""A write whose outcome is unknown must SAY so, on every ambiguous path (#116).

#115 stopped replaying non-idempotent writes and promised the caller two
things: the write is sent once, AND the resulting error carries
``.ambiguous_write = True`` plus a note telling them to check whether it
landed. Only the first half was wired to the 5xx branch.

A 502/503 from a gateway that already committed at the origin is the most
common ambiguous outcome in production -- more common than the client-side
socket timeout that was the only marked case. A caller implementing the
documented contract skipped reconciliation for exactly the case the fix
existed for.

Every assertion here is made on the exception the public method raises and on
what reached the transport, never on an internal flag.
"""

import asyncio
from unittest.mock import patch

import httpx
import pytest

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI
from oilpriceapi.exceptions import OilPriceAPIError

# Not a credential: a fixture string, every request here hits a mock transport.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])


class _Counter:
    def __init__(self, outcome):
        self.methods = []
        self._outcome = outcome

    def __call__(self, request):
        self.methods.append(request.method)
        return self._outcome(request)


def _status(code, headers=None):
    def handler(request):
        return httpx.Response(code, headers=headers or {}, json={"error": "nope"})

    return handler


def _sync_client(counter, **kwargs):
    client = OilPriceAPI(api_key=FIXTURE_KEY, **kwargs)
    client._client = httpx.Client(
        base_url=client.base_url,
        headers=client.headers,
        transport=httpx.MockTransport(counter),
    )
    return client


def _async_client(counter, **kwargs):
    client = AsyncOilPriceAPI(api_key=FIXTURE_KEY, **kwargs)
    client._client = httpx.AsyncClient(
        base_url=client.base_url,
        headers=client.headers,
        transport=httpx.MockTransport(counter),
    )
    return client


def _assert_ambiguous(error, method):
    assert getattr(error, "ambiguous_write", False) is True, (
        "the caller was not told the write outcome is unknown"
    )
    assert "NOT retried" in str(error)
    assert method.upper() in str(error)


# ---------------------------------------------------------------------------
# (a) A 5xx on a non-idempotent write is ambiguous and must be marked


@pytest.mark.parametrize("code", [500, 502, 503, 504])
def test_sync_post_5xx_is_marked_ambiguous(code):
    counter = _Counter(_status(code))
    client = _sync_client(counter)

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError) as excinfo:
            client.request("POST", "/v1/subscriptions", json_data={"plan": "x"})

    assert counter.methods == ["POST"], "the write must still be sent exactly once"
    _assert_ambiguous(excinfo.value, "POST")


def test_sync_patch_5xx_is_marked_ambiguous():
    counter = _Counter(_status(503))
    client = _sync_client(counter)

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError) as excinfo:
            client.request("PATCH", "/v1/alerts/1", json_data={"threshold": 1})

    assert counter.methods == ["PATCH"]
    _assert_ambiguous(excinfo.value, "PATCH")


def test_sync_request_with_headers_post_5xx_is_marked_ambiguous():
    counter = _Counter(_status(503))
    client = _sync_client(counter)

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError) as excinfo:
            client.request_with_headers("POST", "/v1/subscriptions", json_data={"plan": "x"})

    assert counter.methods == ["POST"]
    _assert_ambiguous(excinfo.value, "POST")


def test_async_post_5xx_is_marked_ambiguous():
    counter = _Counter(_status(503))

    async def scenario():
        client = _async_client(counter)
        with pytest.raises(OilPriceAPIError) as excinfo:
            await client.request("POST", "/v1/subscriptions", json_data={"plan": "x"})
        await client._client.aclose()
        return excinfo.value

    async def fake_sleep(seconds):
        return None

    with patch("asyncio.sleep", fake_sleep):
        error = asyncio.run(scenario())

    assert counter.methods == ["POST"]
    _assert_ambiguous(error, "POST")


def test_sync_and_async_produce_the_same_signal():
    """The two clients must not diverge on this contract."""
    sync_counter = _Counter(_status(503))
    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError) as sync_info:
            _sync_client(sync_counter).request("POST", "/v1/subscriptions", json_data={})

    async_counter = _Counter(_status(503))

    async def scenario():
        client = _async_client(async_counter)
        with pytest.raises(OilPriceAPIError) as info:
            await client.request("POST", "/v1/subscriptions", json_data={})
        await client._client.aclose()
        return info.value

    async def fake_sleep(seconds):
        return None

    with patch("asyncio.sleep", fake_sleep):
        async_error = asyncio.run(scenario())

    assert type(sync_info.value) is type(async_error)
    assert str(sync_info.value) == str(async_error)
    assert sync_info.value.ambiguous_write == async_error.ambiguous_write is True


# ---------------------------------------------------------------------------
# (b) Everything that is NOT ambiguous must stay unmarked


def test_sync_post_4xx_is_not_ambiguous():
    """A 400 refused the write outright; nothing landed, nothing to reconcile."""
    counter = _Counter(_status(400))
    client = _sync_client(counter)

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError) as excinfo:
            client.request("POST", "/v1/subscriptions", json_data={"plan": "x"})

    assert getattr(excinfo.value, "ambiguous_write", False) is False
    assert "NOT retried" not in str(excinfo.value)


def test_sync_post_429_is_not_ambiguous():
    """429 is an outright refusal, so the write definitively did not happen."""
    counter = _Counter(_status(429))
    client = _sync_client(counter)

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError) as excinfo:
            client.request("POST", "/v1/subscriptions", json_data={"plan": "x"})

    assert counter.methods == ["POST", "POST", "POST"], "429 is safe to replay"
    assert getattr(excinfo.value, "ambiguous_write", False) is False


def test_sync_get_5xx_is_not_ambiguous():
    counter = _Counter(_status(503))
    client = _sync_client(counter)

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError) as excinfo:
            client.request("GET", "/v1/prices/latest")

    assert counter.methods == ["GET", "GET", "GET"]
    assert getattr(excinfo.value, "ambiguous_write", False) is False


def test_sync_post_5xx_with_idempotent_true_is_retried_and_not_ambiguous():
    counter = _Counter(_status(503))
    client = _sync_client(counter)

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError) as excinfo:
            client.request(
                "POST", "/v1/diesel-prices/stations", json_data={}, idempotent=True
            )

    assert counter.methods == ["POST", "POST", "POST"]
    assert getattr(excinfo.value, "ambiguous_write", False) is False
