"""
Unit tests for the async WebSocket streaming client.

The ``websockets`` transport is fully mocked — these tests never touch the
network. They cover: the ActionCable handshake (welcome -> subscribe ->
confirm_subscription), message dispatch (price_update / rig_count_update /
ping / control-frame filtering), typed-model parsing, reconnect-with-backoff,
and clean teardown (unsubscribe + close).
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

import pytest

from oilpriceapi import AsyncOilPriceAPI
from oilpriceapi.streaming.client import PriceStream
from oilpriceapi.streaming.models import StreamUpdate


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------

class FakeWebSocket:
    """A scripted fake of a ``websockets`` connection.

    ``incoming`` is a list of frames the server "sends". String/dict frames
    are delivered via ``recv``; an item of the sentinel ``CLOSE`` raises a
    ConnectionClosed to simulate a drop; ``STOP`` ends the stream cleanly.
    """

    CLOSE = object()

    def __init__(self, incoming: List[Any]) -> None:
        self._incoming = list(incoming)
        self.sent: List[Dict[str, Any]] = []
        self.closed = False

    async def recv(self) -> str:
        if not self._incoming:
            # No more frames — emulate a graceful server close (no reconnect).
            import websockets

            raise websockets.exceptions.ConnectionClosedOK(None, None)
        item = self._incoming.pop(0)
        if item is self.CLOSE:
            # Abrupt drop — should trigger auto-reconnect.
            import websockets

            raise websockets.exceptions.ConnectionClosed(None, None)
        if isinstance(item, dict):
            return json.dumps(item)
        return item

    async def send(self, message: str) -> None:
        self.sent.append(json.loads(message))

    async def close(self) -> None:
        self.closed = True


class FakeConnector:
    """Stands in for ``websockets.connect`` — hands out queued sockets."""

    def __init__(self, sockets: List[FakeWebSocket]) -> None:
        self._sockets = list(sockets)
        self.connect_calls: List[Dict[str, Any]] = []

    async def __call__(self, url: str, **kwargs: Any) -> FakeWebSocket:
        self.connect_calls.append({"url": url, **kwargs})
        return self._sockets.pop(0)


def _patch_connect(monkeypatch: pytest.MonkeyPatch, connector: FakeConnector) -> None:
    import websockets

    monkeypatch.setattr(websockets, "connect", connector)


def _welcome() -> Dict[str, Any]:
    return {"type": "welcome"}


def _confirm(ident: str) -> Dict[str, Any]:
    return {"type": "confirm_subscription", "identifier": ident}


def _broadcast(message: Dict[str, Any], ident: str = "x") -> Dict[str, Any]:
    return {"identifier": ident, "message": message}


PRICE_UPDATE_MSG = {
    "type": "price_update",
    "timestamp": "2026-06-21T10:00:00Z",
    "base_currency": "USD",
    "base_unit": "MMBtu",
    "prices": {
        "oil": {
            "brent": {
                "normalized_price": 12.3,
                "original_price": 75.5,
                "original_unit": "barrel_oil",
                "original_currency": "USD",
                "timestamp": "2026-06-21T10:00:00Z",
            },
            "wti": None,
        },
        "natural_gas": {"uk": None, "us": None, "eu": None},
    },
}

RIG_UPDATE_MSG = {
    "type": "rig_count_update",
    "timestamp": "2026-06-21T10:05:00Z",
    "rig_count": {
        "code": "US_RIG_COUNT",
        "region": "United States",
        "count": 480,
        "source": "Baker Hughes",
        "updated_at": "2026-06-20T16:00:00Z",
    },
}


# --------------------------------------------------------------------------
# Model tests
# --------------------------------------------------------------------------

def test_stream_update_from_price_message():
    update = StreamUpdate.from_message(PRICE_UPDATE_MSG)
    assert update.type == "price_update"
    assert update.price_update is not None
    assert update.rig_count_update is None
    assert update.price_update.prices.oil.brent.original_price == 75.5
    assert update.raw == PRICE_UPDATE_MSG


def test_stream_update_from_rig_message():
    update = StreamUpdate.from_message(RIG_UPDATE_MSG)
    assert update.type == "rig_count_update"
    assert update.rig_count_update is not None
    assert update.rig_count_update.rig_count.code == "US_RIG_COUNT"
    assert update.rig_count_update.rig_count.count == 480


def test_stream_update_welcome_parses_as_price_update():
    msg = {"type": "welcome", "error": "Initial data temporarily unavailable"}
    update = StreamUpdate.from_message(msg)
    assert update.type == "welcome"
    assert update.price_update is not None
    assert update.price_update.error == "Initial data temporarily unavailable"


# --------------------------------------------------------------------------
# Handshake tests
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handshake_sends_subscribe(monkeypatch, api_key):
    ident_holder: Dict[str, str] = {}

    ws = FakeWebSocket([])
    # Build incoming after we know the identifier? Simpler: drive manually.
    stream = PriceStream(
        cable_url="wss://api.oilpriceapi.com/cable",
        api_key=api_key,
        params={"commodities": ["BRENT_CRUDE_USD"]},
    )
    ident = stream.identifier
    ws._incoming = [_welcome(), _confirm(ident)]  # type: ignore[attr-defined]
    connector = FakeConnector([ws])
    _patch_connect(monkeypatch, connector)

    await stream.connect()
    try:
        # Subscribe command was sent with the correct ActionCable identifier.
        assert ws.sent[0]["command"] == "subscribe"
        sub_ident = json.loads(ws.sent[0]["identifier"])
        assert sub_ident["channel"] == "EnergyPricesChannel"
        assert sub_ident["api_key"] == api_key
        assert sub_ident["commodities"] == ["BRENT_CRUDE_USD"]
        # Token passed via query param for portable auth.
        assert "token=" in connector.connect_calls[0]["url"]
        assert (
            connector.connect_calls[0]["additional_headers"]["Authorization"]
            == f"Token {api_key}"
        )
        assert stream._subscribed is True
        ident_holder["ident"] = ident
    finally:
        await stream.close()


@pytest.mark.asyncio
async def test_rejected_subscription_raises(monkeypatch, api_key):
    stream = PriceStream(cable_url="wss://h/cable", api_key=api_key)
    ws = FakeWebSocket([_welcome(), {"type": "reject_subscription"}])
    _patch_connect(monkeypatch, FakeConnector([ws]))

    with pytest.raises(ConnectionError, match="Subscription rejected"):
        await stream.connect()


# --------------------------------------------------------------------------
# Dispatch / iteration tests
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_iteration_dispatches_messages(monkeypatch, api_key):
    stream = PriceStream(cable_url="wss://h/cable", api_key=api_key)
    ident = stream.identifier
    ws = FakeWebSocket(
        [
            _welcome(),
            _confirm(ident),
            {"type": "ping", "message": 1234},  # ignored
            _broadcast(PRICE_UPDATE_MSG, ident),
            _broadcast(RIG_UPDATE_MSG, ident),
        ]
    )
    _patch_connect(monkeypatch, FakeConnector([ws]))

    updates: List[StreamUpdate] = []
    async with stream as s:
        async for update in s:
            updates.append(update)

    types = [u.type for u in updates]
    assert types == ["price_update", "rig_count_update"]
    assert updates[0].price_update.base_unit == "MMBtu"
    assert updates[1].rig_count_update.rig_count.region == "United States"


@pytest.mark.asyncio
async def test_control_frames_are_filtered(monkeypatch, api_key):
    stream = PriceStream(cable_url="wss://h/cable", api_key=api_key)
    ident = stream.identifier
    ws = FakeWebSocket(
        [
            _welcome(),
            _confirm(ident),
            {"type": "ping"},
            {"type": "confirm_subscription", "identifier": ident},
            _broadcast(PRICE_UPDATE_MSG, ident),
        ]
    )
    _patch_connect(monkeypatch, FakeConnector([ws]))

    updates = [u async for u in stream]
    assert len(updates) == 1
    assert updates[0].type == "price_update"
    await stream.close()


# --------------------------------------------------------------------------
# Reconnect tests
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reconnect_on_drop(monkeypatch, api_key):
    stream = PriceStream(
        cable_url="wss://h/cable",
        api_key=api_key,
        reconnect_base_delay=0.0,
        reconnect_max_delay=0.0,
    )
    ident = stream.identifier

    ws1 = FakeWebSocket([_welcome(), _confirm(ident), _broadcast(PRICE_UPDATE_MSG, ident), FakeWebSocket.CLOSE])
    ws2 = FakeWebSocket([_welcome(), _confirm(ident), _broadcast(RIG_UPDATE_MSG, ident)])
    connector = FakeConnector([ws1, ws2])
    _patch_connect(monkeypatch, connector)

    # Avoid real sleeping during backoff.
    async def _no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    updates = [u async for u in stream]
    assert [u.type for u in updates] == ["price_update", "rig_count_update"]
    # Reconnected => connect called twice, re-subscribed on the new socket.
    assert len(connector.connect_calls) == 2
    assert ws2.sent[0]["command"] == "subscribe"


@pytest.mark.asyncio
async def test_reconnect_gives_up_after_max_attempts(monkeypatch, api_key):
    stream = PriceStream(
        cable_url="wss://h/cable",
        api_key=api_key,
        max_reconnect_attempts=1,
        reconnect_base_delay=0.0,
    )
    ident = stream.identifier
    # Each socket drops immediately after handshake; second drop exceeds max=1.
    ws1 = FakeWebSocket([_welcome(), _confirm(ident), FakeWebSocket.CLOSE])
    ws2 = FakeWebSocket([_welcome(), _confirm(ident), FakeWebSocket.CLOSE])
    _patch_connect(monkeypatch, FakeConnector([ws1, ws2]))

    async def _no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    with pytest.raises(ConnectionError, match="reconnect attempts"):
        async for _ in stream:
            pass


@pytest.mark.asyncio
async def test_auto_reconnect_disabled_ends_cleanly(monkeypatch, api_key):
    stream = PriceStream(
        cable_url="wss://h/cable", api_key=api_key, auto_reconnect=False
    )
    ident = stream.identifier
    ws = FakeWebSocket([_welcome(), _confirm(ident), _broadcast(PRICE_UPDATE_MSG, ident), FakeWebSocket.CLOSE])
    _patch_connect(monkeypatch, FakeConnector([ws]))

    updates = [u async for u in stream]
    assert [u.type for u in updates] == ["price_update"]


# --------------------------------------------------------------------------
# Teardown tests
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_close_sends_unsubscribe(monkeypatch, api_key):
    stream = PriceStream(cable_url="wss://h/cable", api_key=api_key)
    ident = stream.identifier
    ws = FakeWebSocket([_welcome(), _confirm(ident)])
    _patch_connect(monkeypatch, FakeConnector([ws]))

    await stream.connect()
    await stream.close()

    assert ws.closed is True
    assert ws.sent[-1]["command"] == "unsubscribe"
    assert stream._ws is None


# --------------------------------------------------------------------------
# Namespace wiring tests
# --------------------------------------------------------------------------

def test_client_exposes_stream_namespace(api_key):
    client = AsyncOilPriceAPI(api_key=api_key)
    assert hasattr(client, "stream")
    stream = client.stream.prices(commodities=["WTI_USD"])
    assert isinstance(stream, PriceStream)
    ident = json.loads(stream.identifier)
    assert ident["channel"] == "EnergyPricesChannel"
    assert ident["commodities"] == ["WTI_USD"]


def test_cable_url_derivation(api_key):
    client = AsyncOilPriceAPI(api_key=api_key, base_url="https://api.oilpriceapi.com")
    assert client.stream._cable_url() == "wss://api.oilpriceapi.com/cable"

    client2 = AsyncOilPriceAPI(api_key=api_key, base_url="http://localhost:5000")
    assert client2.stream._cable_url() == "ws://localhost:5000/cable"
