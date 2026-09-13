"""Automatic retry must never replay a non-idempotent write (#104).

A POST that the server committed before the response was lost is ambiguous, not
failed. Replaying it double-creates: two subscriptions, two webhooks, two of
whatever the caller was writing. These tests count what reaches the transport.

Also covers the constructor's `or` defaults, which silently turned
`max_retries=0` into 3 and `retry_on=[]` into the default status list, and the
bounding of a server `Retry-After`.
"""

import asyncio
from unittest.mock import patch

import httpx
import pytest

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI
from oilpriceapi.exceptions import ConfigurationError, OilPriceAPIError
from oilpriceapi.retry import RetryStrategy

# Not a credential: a fixture string, every request here hits a mock transport.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])


class _Counter:
    """Mock transport that counts attempts and replays a scripted outcome."""

    def __init__(self, outcome):
        self.methods = []
        self._outcome = outcome

    def __call__(self, request):
        self.methods.append(request.method)
        return self._outcome(request)


def _timeout(request):
    raise httpx.ReadTimeout("server committed, response lost", request=request)


def _connect_error(request):
    raise httpx.ConnectError("connection reset", request=request)


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


# ---------------------------------------------------------------------------
# (a) non-idempotent writes are sent once
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("outcome", [_timeout, _connect_error, _status(503), _status(500)])
@pytest.mark.parametrize("method", ["POST", "PATCH"])
def test_write_is_sent_exactly_once(method, outcome):
    counter = _Counter(outcome)
    client = _sync_client(counter)

    with patch("time.sleep") as slept:
        with pytest.raises(OilPriceAPIError):
            client.request(method, "/v1/subscriptions", json_data={"code": "BRENT_CRUDE_USD"})

    assert counter.methods == [method], f"write was replayed: {counter.methods}"
    assert slept.call_count == 0


@pytest.mark.parametrize("outcome", [_timeout, _status(503)])
def test_async_write_is_sent_exactly_once(outcome):
    counter = _Counter(outcome)

    async def scenario():
        client = _async_client(counter)
        with pytest.raises(OilPriceAPIError):
            await client.request("POST", "/v1/webhooks", json_data={"url": "https://x.example"})
        await client._client.aclose()

    with patch("asyncio.sleep") as slept:
        asyncio.run(scenario())

    assert counter.methods == ["POST"]
    assert slept.call_count == 0


def test_request_with_headers_does_not_replay_a_write():
    counter = _Counter(_timeout)
    client = _sync_client(counter)

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError):
            client.request_with_headers("POST", "/v1/webhooks", json_data={"url": "https://x"})

    assert counter.methods == ["POST"]


def test_ambiguous_write_error_says_it_was_not_retried():
    counter = _Counter(_timeout)
    client = _sync_client(counter)

    with pytest.raises(OilPriceAPIError) as excinfo:
        client.request("POST", "/v1/subscriptions", json_data={"code": "BRENT_CRUDE_USD"})

    message = str(excinfo.value).lower()
    assert "not retried" in message or "not replayed" in message
    assert getattr(excinfo.value, "ambiguous_write", False) is True


def test_caller_can_opt_into_replaying_a_write():
    """An explicit idempotent=True is the caller asserting the write is safe."""
    counter = _Counter(_timeout)
    client = _sync_client(counter)

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError):
            client.request("POST", "/v1/echo", json_data={}, idempotent=True)

    assert counter.methods == ["POST", "POST", "POST"]


# ---------------------------------------------------------------------------
# reads must keep recovering
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["GET", "HEAD", "PUT", "DELETE"])
def test_idempotent_methods_still_retry_transient_failures(method):
    counter = _Counter(_timeout)
    client = _sync_client(counter)

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError):
            client.request(method, "/v1/prices/latest")

    assert counter.methods == [method] * 3


def test_get_recovers_after_a_transient_failure():
    state = {"n": 0}

    def flaky(request):
        state["n"] += 1
        if state["n"] == 1:
            raise httpx.ReadTimeout("transient", request=request)
        return httpx.Response(200, json={"status": "success", "data": {"price": 1}})

    counter = _Counter(flaky)
    client = _sync_client(counter)

    with patch("time.sleep"):
        body = client.request("GET", "/v1/prices/latest")

    assert body["data"]["price"] == 1
    assert counter.methods == ["GET", "GET"]


def test_a_429_still_retries_a_write():
    """A 429 is a refusal: the write definitively did not happen, so replay is safe."""
    counter = _Counter(_status(429, {"Retry-After": "1"}))
    client = _sync_client(counter)

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError):
            client.request("POST", "/v1/subscriptions", json_data={})

    assert counter.methods == ["POST", "POST", "POST"]


# ---------------------------------------------------------------------------
# (b) explicit configuration must survive the constructor
# ---------------------------------------------------------------------------


def test_empty_retry_on_is_preserved():
    client = OilPriceAPI(api_key=FIXTURE_KEY, retry_on=[])
    assert client.retry_on == []
    assert client._retry_strategy.retry_on == []


def test_empty_retry_on_actually_stops_status_retries():
    counter = _Counter(_status(503))
    client = _sync_client(counter, retry_on=[])

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError):
            client.request("GET", "/v1/prices/latest")

    assert counter.methods == ["GET"]


def test_async_empty_retry_on_is_preserved():
    client = AsyncOilPriceAPI(api_key=FIXTURE_KEY, retry_on=[])
    assert client.retry_on == []


@pytest.mark.parametrize("bad", [-1, -5])
def test_invalid_max_retries_fails_loudly(bad):
    """max_retries counts ATTEMPTS. A negative count is not a thing; say so."""
    with pytest.raises(ConfigurationError) as excinfo:
        OilPriceAPI(api_key=FIXTURE_KEY, max_retries=bad)
    assert "attempt" in str(excinfo.value).lower()


@pytest.mark.parametrize("bad", ["3", 2.5, True])
def test_non_integer_max_retries_fails_loudly(bad):
    with pytest.raises(ConfigurationError):
        OilPriceAPI(api_key=FIXTURE_KEY, max_retries=bad)


def test_async_invalid_max_retries_fails_loudly():
    with pytest.raises(ConfigurationError):
        AsyncOilPriceAPI(api_key=FIXTURE_KEY, max_retries=-1)


# max_retries=0 was briefly a ConfigurationError at construction. It is now a
# DeprecationWarning resolving to one attempt: the validation was right, but a
# value that constructed fine in 1.13.0 must not take a process down at startup
# inside a patch series (#121). The full contract lives in
# tests/unit/test_constructor_config_validation.py; this pins the one thing
# THIS file exists to protect -- 0 does not silently go back to 3.
def test_zero_max_retries_does_not_go_back_to_three():
    counter = _Counter(_status(503))
    with pytest.warns(DeprecationWarning):
        client = _sync_client(counter, max_retries=0)

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError):
            client.request("GET", "/v1/prices/latest")

    assert counter.methods == ["GET"]


def test_max_retries_one_means_a_single_attempt():
    counter = _Counter(_status(503))
    client = _sync_client(counter, max_retries=1)

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError):
            client.request("GET", "/v1/prices/latest")

    assert counter.methods == ["GET"]


# ---------------------------------------------------------------------------
# (c) Retry-After must be bounded in both directions
# ---------------------------------------------------------------------------


def test_retry_after_is_capped():
    """The keyless demo returns retry-after: 31612 — 8.8 hours of blocked process."""
    counter = _Counter(_status(429, {"Retry-After": "31612"}))
    client = _sync_client(counter)
    waits = []

    with patch("time.sleep", side_effect=waits.append):
        with pytest.raises(OilPriceAPIError):
            client.request("GET", "/v1/prices/latest")

    assert waits, "expected at least one retry"
    assert max(waits) <= 60.0


@pytest.mark.parametrize("value", ["-30", "-1"])
def test_negative_retry_after_never_reaches_sleep(value):
    """time.sleep() raises ValueError on a negative argument."""
    counter = _Counter(_status(429, {"Retry-After": value}))
    client = _sync_client(counter)
    waits = []

    with patch("time.sleep", side_effect=waits.append):
        with pytest.raises(OilPriceAPIError):
            client.request("GET", "/v1/prices/latest")

    assert all(w >= 0 for w in waits), waits


def test_async_retry_after_is_bounded():
    counter = _Counter(_status(429, {"Retry-After": "31612"}))
    waits = []

    async def scenario():
        client = _async_client(counter)
        with pytest.raises(OilPriceAPIError):
            await client.request("GET", "/v1/prices/latest")
        await client._client.aclose()

    async def fake_sleep(seconds):
        waits.append(seconds)

    with patch("asyncio.sleep", side_effect=fake_sleep):
        asyncio.run(scenario())

    assert waits and max(waits) <= 60.0 and min(waits) >= 0


def test_request_with_headers_bounds_retry_after():
    counter = _Counter(_status(429, {"Retry-After": "31612"}))
    client = _sync_client(counter)
    waits = []

    with patch("time.sleep", side_effect=waits.append):
        with pytest.raises(OilPriceAPIError):
            client.request_with_headers("GET", "/v1/prices/latest")

    assert waits and max(waits) <= 60.0


# ---------------------------------------------------------------------------
# already-fixed behaviour that must not regress
# ---------------------------------------------------------------------------


def test_durable_quota_exhaustion_is_still_never_retried():
    headers = {
        "Retry-After": "600",
        "X-RateLimit-State": "exhausted",
        "X-RateLimit-Window": "monthly_counter",
    }
    counter = _Counter(_status(429, headers))
    client = _sync_client(counter)

    with patch("time.sleep") as slept:
        with pytest.raises(OilPriceAPIError):
            client.request("GET", "/v1/prices/latest")

    assert counter.methods == ["GET"]
    assert slept.call_count == 0


# ---------------------------------------------------------------------------
# RetryStrategy keeps its existing public contract
# ---------------------------------------------------------------------------


def test_retry_strategy_defaults_to_replay_safe_when_method_is_unknown():
    """The public helper is unchanged for callers that pass no method."""
    strategy = RetryStrategy(max_retries=3)
    assert strategy.should_retry_on_exception(0) is True
    assert strategy.should_retry(0, 500) is True


def test_retry_strategy_knows_which_methods_are_replay_safe():
    strategy = RetryStrategy(max_retries=3, retry_on=[429, 500, 502, 503, 504])
    assert strategy.should_retry_on_exception(0, method="GET") is True
    assert strategy.should_retry_on_exception(0, method="post") is False
    assert strategy.should_retry_on_exception(0, method="POST", idempotent=True) is True
    assert strategy.should_retry(0, 500, method="POST") is False
    assert strategy.should_retry(0, 429, method="POST") is True
