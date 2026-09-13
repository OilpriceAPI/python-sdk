"""
Lifecycle and non-blocking guarantees for the opt-in telemetry transport (#105).

The telemetry collector is an advertised public option (``enable_telemetry`` on
both clients, plus ``configure_telemetry``), so it is fixed rather than removed.
These tests pin the four defects called out in the issue:

1. delivery must never happen synchronously on the caller's thread / event loop
2. ``close()`` must stop background activity and be idempotent
3. replacing the global config must not leak the previous thread
4. a telemetry failure must never alter or fail a request result

No test here is ever allowed to make a real network call: every test replaces
``oilpriceapi.telemetry.httpx.post`` with a local sink.
"""

import asyncio
import inspect
import threading
import time
from unittest.mock import Mock

import httpx
import pytest
import respx

from oilpriceapi import OilPriceAPI
from oilpriceapi.async_client import AsyncOilPriceAPI
from oilpriceapi.telemetry import Telemetry, configure_telemetry, get_telemetry

API_KEY = "test_api_key_12345"


@pytest.fixture(autouse=True)
def no_real_telemetry_network(monkeypatch):
    """Fail loudly if telemetry ever reaches the real httpx.post."""

    def _boom(*args, **kwargs):  # pragma: no cover - only runs on regression
        raise AssertionError("telemetry attempted a real network call")

    monkeypatch.setattr("oilpriceapi.telemetry.httpx.post", _boom)
    yield


@pytest.fixture
def sink(monkeypatch):
    """Replace the telemetry transport with a local, instrumented sink."""

    calls = []

    def _post(url, **kwargs):
        calls.append({"url": url, "json": kwargs.get("json")})
        time.sleep(_post.delay)
        return Mock(status_code=200)

    _post.delay = 0.0
    _post.calls = calls
    monkeypatch.setattr("oilpriceapi.telemetry.httpx.post", _post)
    return _post


def _track_n(telemetry, n):
    for i in range(n):
        telemetry.track_request(operation=f"GET /v1/op{i}", duration=0.01, success=True)


# ---------------------------------------------------------------------------
# 1. Disabled mode: no thread, no network
# ---------------------------------------------------------------------------


def test_disabled_telemetry_starts_no_thread_and_makes_no_network_call(sink):
    before = threading.active_count()
    telemetry = Telemetry(enabled=False)
    try:
        _track_n(telemetry, 25)
        assert threading.active_count() == before
        assert getattr(telemetry, "_flush_thread", None) is None
        assert sink.calls == []
    finally:
        telemetry.close()


def test_client_defaults_start_no_telemetry_thread(sink):
    before = threading.active_count()
    with OilPriceAPI(api_key=API_KEY) as client:
        assert client._telemetry.enabled is False
        assert threading.active_count() == before
    assert sink.calls == []


# ---------------------------------------------------------------------------
# 2. Enabled mode: ten tracked calls cannot block the caller
# ---------------------------------------------------------------------------


def test_ten_tracked_events_do_not_block_the_calling_thread(sink):
    sink.delay = 3.0
    telemetry = Telemetry(enabled=True, endpoint="http://localhost:1/telemetry")
    try:
        start = time.monotonic()
        _track_n(telemetry, 10)
        elapsed = time.monotonic() - start
        assert elapsed < 0.5, (
            f"track_request blocked the caller for {elapsed:.2f}s; "
            "delivery must not run on the caller's thread"
        )
    finally:
        telemetry.enabled = False
        telemetry.close()


@respx.mock
def test_sync_client_requests_are_not_blocked_by_telemetry_delivery(sink):
    sink.delay = 3.0
    respx.get("https://api.oilpriceapi.com/v1/prices/latest").mock(
        return_value=httpx.Response(200, json={"status": "success", "data": {}})
    )
    client = OilPriceAPI(api_key=API_KEY, enable_telemetry=True)
    try:
        start = time.monotonic()
        for _ in range(10):
            client.request("GET", "/v1/prices/latest")
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, f"ten client calls took {elapsed:.2f}s with a slow telemetry sink"
    finally:
        client._telemetry.enabled = False
        client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_client_event_loop_is_not_blocked_by_telemetry(sink):
    sink.delay = 3.0
    respx.get("https://api.oilpriceapi.com/v1/prices/latest").mock(
        return_value=httpx.Response(200, json={"status": "success", "data": {}})
    )
    client = AsyncOilPriceAPI(api_key=API_KEY, enable_telemetry=True)

    ticks = 0

    async def heartbeat():
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

    beat = asyncio.create_task(heartbeat())
    try:
        start = time.monotonic()
        for _ in range(10):
            await client.request("GET", "/v1/prices/latest")
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, f"ten async calls took {elapsed:.2f}s with a slow telemetry sink"
        ticks_after = ticks
        await asyncio.sleep(0.05)
        assert ticks > ticks_after, "event loop stalled while telemetry was delivering"
    finally:
        beat.cancel()
        client._telemetry.enabled = False
        await client.close()


# ---------------------------------------------------------------------------
# 3. close() stops background activity and is idempotent
# ---------------------------------------------------------------------------


def test_close_stops_the_background_thread_and_is_idempotent(sink):
    telemetry = Telemetry(enabled=True, endpoint="http://localhost:1/telemetry")
    thread = telemetry._flush_thread
    assert thread is not None and thread.is_alive()

    telemetry.close()

    assert telemetry.enabled is False
    thread.join(timeout=2.0)
    assert not thread.is_alive(), "close() left the telemetry flush thread running"

    # Idempotent: a second close is a no-op and never raises.
    telemetry.close()
    telemetry.close()

    # And no further events are buffered or delivered after close.
    calls_before = len(sink.calls)
    _track_n(telemetry, 25)
    assert telemetry._events == []
    assert len(sink.calls) == calls_before


def test_client_close_stops_telemetry_thread(sink):
    client = OilPriceAPI(api_key=API_KEY, enable_telemetry=True)
    thread = client._telemetry._flush_thread
    assert thread is not None and thread.is_alive()
    client.close()
    thread.join(timeout=2.0)
    assert not thread.is_alive()
    client.close()  # idempotent at the client level too


@pytest.mark.asyncio
async def test_async_client_close_stops_telemetry_thread(sink):
    client = AsyncOilPriceAPI(api_key=API_KEY, enable_telemetry=True)
    thread = client._telemetry._flush_thread
    assert thread is not None and thread.is_alive()
    await client.close()
    thread.join(timeout=2.0)
    assert not thread.is_alive()


# ---------------------------------------------------------------------------
# 4. Replacing the global config leaves no prior thread alive
# ---------------------------------------------------------------------------


def test_configure_telemetry_stops_the_previous_instance(sink):
    import oilpriceapi.telemetry as telemetry_module

    previous_global = telemetry_module._global_telemetry
    try:
        configure_telemetry(enabled=True, endpoint="http://localhost:1/telemetry")
        first = get_telemetry()
        assert first is not None
        first_thread = first._flush_thread
        assert first_thread is not None and first_thread.is_alive()

        configure_telemetry(enabled=True, endpoint="http://localhost:1/telemetry")
        second = get_telemetry()
        assert second is not first

        first_thread.join(timeout=2.0)
        assert not first_thread.is_alive(), "configure_telemetry leaked the previous flush thread"
        assert first.enabled is False

        second_thread = second._flush_thread
        configure_telemetry(enabled=False)
        if second_thread is not None:
            second_thread.join(timeout=2.0)
            assert not second_thread.is_alive()
    finally:
        current = telemetry_module._global_telemetry
        if current is not None:
            current.close()
        telemetry_module._global_telemetry = previous_global


# ---------------------------------------------------------------------------
# 5. A telemetry failure cannot alter or fail a request result
# ---------------------------------------------------------------------------


class _ExplodingTelemetry:
    enabled = True

    def track_request(self, *args, **kwargs):
        raise RuntimeError("telemetry backend exploded")

    def close(self):
        raise RuntimeError("telemetry close exploded")


@respx.mock
def test_sync_request_result_survives_a_telemetry_failure(sink):
    payload = {"status": "success", "data": {"code": "BRENT_CRUDE_USD", "price": 75.5}}
    respx.get("https://api.oilpriceapi.com/v1/prices/latest").mock(
        return_value=httpx.Response(200, json=payload)
    )
    client = OilPriceAPI(api_key=API_KEY)
    client._telemetry = _ExplodingTelemetry()
    result = client.request("GET", "/v1/prices/latest")
    assert result == payload


@pytest.mark.asyncio
@respx.mock
async def test_async_request_result_survives_a_telemetry_failure(sink):
    payload = {"status": "success", "data": {"code": "BRENT_CRUDE_USD", "price": 75.5}}
    respx.get("https://api.oilpriceapi.com/v1/prices/latest").mock(
        return_value=httpx.Response(200, json=payload)
    )
    client = AsyncOilPriceAPI(api_key=API_KEY)
    client._telemetry = _ExplodingTelemetry()
    try:
        result = await client.request("GET", "/v1/prices/latest")
        assert result == payload
    finally:
        client._telemetry = Telemetry(enabled=False)
        await client.close()


# ---------------------------------------------------------------------------
# 6. Sync and async clients must handle telemetry identically
# ---------------------------------------------------------------------------


def test_sync_and_async_clients_share_identical_telemetry_handling():
    sync_src = inspect.getsource(OilPriceAPI._track_telemetry)
    async_src = inspect.getsource(AsyncOilPriceAPI._track_telemetry)
    assert sync_src == async_src, "sync and async telemetry guards have diverged"

    for cls in (OilPriceAPI, AsyncOilPriceAPI):
        close_src = inspect.getsource(cls.close)
        assert "self._telemetry.close()" in close_src
        request_src = inspect.getsource(cls.request)
        assert "self._telemetry.track_request(" not in request_src, (
            f"{cls.__name__}.request calls track_request directly instead of the guarded helper"
        )
        assert "self._track_telemetry(" in request_src
