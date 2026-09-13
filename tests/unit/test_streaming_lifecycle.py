"""
Lifecycle tests for the async WebSocket streaming client (issue #108).

These cover the two defects the coverage review found in
``oilpriceapi/streaming/client.py``:

1. ``open_timeout`` bounded only the WebSocket upgrade. The ActionCable
   handshake that follows it -- waiting for ``welcome`` and then for
   ``confirm_subscription`` -- had no deadline at all, so a socket that
   upgrades and then goes quiet hangs the caller forever. Cancelling out of
   that hang left the upgraded socket open.
2. A reconnect that fails inside the ``ConnectionClosed`` handler escaped the
   iterator on the first attempt instead of consuming the configured
   ``max_reconnect_attempts`` budget.

Every await in this module carries its own deadline so a regression fails fast
instead of blocking CI. The ``websockets`` transport is fully mocked; nothing
here touches the network.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

import pytest

from oilpriceapi.streaming.client import PriceStream

# Hard ceiling for any await in this file. A correct implementation finishes
# these in milliseconds; a regression trips the deadline instead of hanging.
DEADLINE = 2.0


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------

class ScriptedSocket:
    """A fake ``websockets`` connection driven by a scripted frame list.

    Frame items:
      * ``dict`` / ``str``   -- delivered by ``recv``
      * ``HANG``             -- ``recv`` never completes
      * ``DROP``             -- ``recv`` raises ``ConnectionClosed``
    An exhausted script raises ``ConnectionClosedOK`` (graceful server close).
    """

    HANG = object()
    DROP = object()

    def __init__(self, frames: Optional[List[Any]] = None) -> None:
        self.frames: List[Any] = list(frames or [])
        self.sent: List[Dict[str, Any]] = []
        self.closed = False
        self.recv_started = asyncio.Event()

    async def recv(self) -> str:
        self.recv_started.set()
        import websockets

        if not self.frames:
            raise websockets.exceptions.ConnectionClosedOK(None, None)
        item = self.frames.pop(0)
        if item is self.HANG:
            # Upgraded, connected, and silent forever.
            await asyncio.sleep(3600)
            raise AssertionError("unreachable")  # pragma: no cover
        if item is self.DROP:
            raise websockets.exceptions.ConnectionClosed(None, None)
        if isinstance(item, dict):
            return json.dumps(item)
        return item

    async def send(self, message: str) -> None:
        self.sent.append(json.loads(message))

    async def close(self) -> None:
        self.closed = True


class RecordingConnector:
    """Stands in for ``websockets.connect``; records every socket handed out.

    ``results`` entries are either a ``ScriptedSocket`` to return or an
    exception instance to raise (a transport-level connect failure).
    """

    def __init__(self, results: List[Any], default: Any = None) -> None:
        self._results = list(results)
        self._default = default
        self.calls: List[Dict[str, Any]] = []
        self.allocated: List[ScriptedSocket] = []

    async def __call__(self, url: str, **kwargs: Any) -> ScriptedSocket:
        self.calls.append({"url": url, **kwargs})
        if self._results:
            result = self._results.pop(0)
        elif self._default is not None:
            result = self._default() if callable(self._default) else self._default
        else:
            raise AssertionError("connector called more times than scripted")
        if isinstance(result, BaseException):
            raise result
        self.allocated.append(result)
        return result


def _patch_connect(monkeypatch: pytest.MonkeyPatch, connector: RecordingConnector) -> None:
    import websockets

    monkeypatch.setattr(websockets, "connect", connector)


def _welcome() -> Dict[str, Any]:
    return {"type": "welcome"}


def _confirm() -> Dict[str, Any]:
    return {"type": "confirm_subscription"}


def assert_no_socket_leaked(connector: RecordingConnector) -> None:
    """Every socket the connector handed out must have been closed."""
    leaked = [i for i, ws in enumerate(connector.allocated) if not ws.closed]
    assert not leaked, (
        f"{len(leaked)} of {len(connector.allocated)} allocated socket(s) left "
        f"open (indices {leaked})"
    )


def assert_no_pending_tasks() -> None:
    pending = [
        t
        for t in asyncio.all_tasks()
        if t is not asyncio.current_task() and not t.done()
    ]
    assert not pending, f"{len(pending)} task(s) left pending: {pending}"


# --------------------------------------------------------------------------
# 1. Bounded setup lifecycle
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upgraded_socket_with_no_welcome_is_bounded(monkeypatch, api_key):
    """A socket that upgrades and never sends ``welcome`` must not hang."""
    ws = ScriptedSocket([ScriptedSocket.HANG])
    connector = RecordingConnector([ws])
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(cable_url="ws://h/cable", api_key=api_key, open_timeout=0.05)

    with pytest.raises(ConnectionError, match="timed out"):
        await asyncio.wait_for(stream.connect(), timeout=DEADLINE)

    assert_no_socket_leaked(connector)
    assert stream._ws is None
    assert_no_pending_tasks()


@pytest.mark.asyncio
async def test_welcome_without_confirmation_is_bounded(monkeypatch, api_key):
    """``welcome`` then silence must not hang waiting for the confirmation."""
    ws = ScriptedSocket([_welcome(), ScriptedSocket.HANG])
    connector = RecordingConnector([ws])
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(cable_url="ws://h/cable", api_key=api_key, open_timeout=0.05)

    with pytest.raises(ConnectionError, match="timed out"):
        await asyncio.wait_for(stream.connect(), timeout=DEADLINE)

    # The subscribe command did go out; the server simply never confirmed it.
    assert ws.sent and ws.sent[0]["command"] == "subscribe"
    assert_no_socket_leaked(connector)
    assert stream._ws is None
    assert_no_pending_tasks()


@pytest.mark.asyncio
async def test_setup_timeout_overrides_open_timeout(monkeypatch, api_key):
    """``setup_timeout`` bounds the whole handshake independently of open_timeout."""
    ws = ScriptedSocket([ScriptedSocket.HANG])
    connector = RecordingConnector([ws])
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(
        cable_url="ws://h/cable",
        api_key=api_key,
        open_timeout=300.0,
        setup_timeout=0.05,
    )

    with pytest.raises(ConnectionError, match="timed out"):
        await asyncio.wait_for(stream.connect(), timeout=DEADLINE)

    # open_timeout is still handed to the transport for the upgrade itself.
    assert connector.calls[0]["open_timeout"] == 300.0
    assert_no_socket_leaked(connector)


@pytest.mark.asyncio
async def test_rejected_subscription_closes_the_socket(monkeypatch, api_key):
    ws = ScriptedSocket([_welcome(), {"type": "reject_subscription"}])
    connector = RecordingConnector([ws])
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(cable_url="ws://h/cable", api_key=api_key)

    with pytest.raises(ConnectionError, match="Subscription rejected"):
        await asyncio.wait_for(stream.connect(), timeout=DEADLINE)

    assert_no_socket_leaked(connector)
    assert stream._ws is None


@pytest.mark.asyncio
async def test_server_disconnect_during_handshake_closes_the_socket(monkeypatch, api_key):
    ws = ScriptedSocket([{"type": "disconnect", "reason": "unauthorized"}])
    connector = RecordingConnector([ws])
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(cable_url="ws://h/cable", api_key=api_key)

    with pytest.raises(ConnectionError, match="unauthorized"):
        await asyncio.wait_for(stream.connect(), timeout=DEADLINE)

    assert_no_socket_leaked(connector)
    assert stream._ws is None


@pytest.mark.asyncio
async def test_failed_aenter_closes_the_socket(monkeypatch, api_key):
    """``__aexit__`` never runs when ``__aenter__`` raises -- setup must clean up."""
    ws = ScriptedSocket([_welcome(), {"type": "reject_subscription"}])
    connector = RecordingConnector([ws])
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(cable_url="ws://h/cable", api_key=api_key)

    async def _enter() -> None:
        async with stream:  # pragma: no cover - body never reached
            raise AssertionError("unreachable")

    with pytest.raises(ConnectionError, match="Subscription rejected"):
        await asyncio.wait_for(_enter(), timeout=DEADLINE)

    assert_no_socket_leaked(connector)
    assert stream._ws is None


@pytest.mark.asyncio
async def test_cancellation_mid_setup_closes_the_socket(monkeypatch, api_key):
    """A caller who cancels during the handshake leaves no socket behind."""
    ws = ScriptedSocket([ScriptedSocket.HANG])
    connector = RecordingConnector([ws])
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(cable_url="ws://h/cable", api_key=api_key, setup_timeout=60.0)

    task = asyncio.create_task(stream.connect())
    await asyncio.wait_for(ws.recv_started.wait(), timeout=DEADLINE)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=DEADLINE)

    assert_no_socket_leaked(connector)
    assert stream._ws is None
    assert_no_pending_tasks()


# --------------------------------------------------------------------------
# 2. Reconnect budget
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transient_reconnect_failure_consumes_the_budget(monkeypatch, api_key):
    """An OSError on reconnect consumes one attempt, not the whole iterator."""
    first = ScriptedSocket([_welcome(), _confirm(), ScriptedSocket.DROP])
    connector = RecordingConnector(
        [first], default=lambda: OSError("connection refused")
    )
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(
        cable_url="ws://h/cable",
        api_key=api_key,
        max_reconnect_attempts=10,
        reconnect_base_delay=0.0,
        reconnect_max_delay=0.0,
    )

    async def _drain() -> None:
        async for _ in stream:
            pass

    with pytest.raises(ConnectionError, match="10 reconnect attempts"):
        await asyncio.wait_for(_drain(), timeout=DEADLINE)

    # 1 initial connect + 10 reconnect attempts, the full configured budget.
    assert len(connector.calls) == 11
    assert_no_socket_leaked(connector)


@pytest.mark.asyncio
async def test_reconnect_succeeds_within_the_budget(monkeypatch, api_key):
    """Two transient failures then a success: iteration continues."""
    first = ScriptedSocket([_welcome(), _confirm(), ScriptedSocket.DROP])
    third = ScriptedSocket([_welcome(), _confirm()])
    connector = RecordingConnector(
        [first, OSError("refused"), OSError("refused"), third]
    )
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(
        cable_url="ws://h/cable",
        api_key=api_key,
        max_reconnect_attempts=5,
        reconnect_base_delay=0.0,
        reconnect_max_delay=0.0,
    )

    async def _drain() -> List[Any]:
        return [u async for u in stream]

    updates = await asyncio.wait_for(_drain(), timeout=DEADLINE)

    assert updates == []  # third socket closes gracefully with no broadcasts
    assert len(connector.calls) == 4
    assert_no_socket_leaked(connector)


@pytest.mark.asyncio
async def test_permanent_rejection_on_reconnect_stops_immediately(monkeypatch, api_key):
    """An auth/entitlement rejection is permanent: stop, do not burn the budget."""
    first = ScriptedSocket([_welcome(), _confirm(), ScriptedSocket.DROP])
    second = ScriptedSocket([_welcome(), {"type": "reject_subscription"}])
    connector = RecordingConnector([first, second])
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(
        cable_url="ws://h/cable",
        api_key=api_key,
        max_reconnect_attempts=10,
        reconnect_base_delay=0.0,
        reconnect_max_delay=0.0,
    )

    async def _drain() -> None:
        async for _ in stream:
            pass

    with pytest.raises(ConnectionError, match="Subscription rejected"):
        await asyncio.wait_for(_drain(), timeout=DEADLINE)

    # One initial connect, exactly one reconnect, then a hard stop.
    assert len(connector.calls) == 2
    assert_no_socket_leaked(connector)


@pytest.mark.asyncio
async def test_permanent_failure_is_a_distinguishable_error_type(monkeypatch, api_key):
    """Callers can tell a permanent refusal from a transient network error."""
    from oilpriceapi.streaming.client import StreamAuthError

    assert issubclass(StreamAuthError, ConnectionError)

    ws = ScriptedSocket([_welcome(), {"type": "reject_subscription"}])
    connector = RecordingConnector([ws])
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(cable_url="ws://h/cable", api_key=api_key)
    with pytest.raises(StreamAuthError) as excinfo:
        await asyncio.wait_for(stream.connect(), timeout=DEADLINE)

    assert "pricing" in str(excinfo.value)
    assert_no_socket_leaked(connector)


@pytest.mark.asyncio
async def test_reconnect_closes_the_previous_socket(monkeypatch, api_key):
    first = ScriptedSocket([_welcome(), _confirm(), ScriptedSocket.DROP])
    second = ScriptedSocket([_welcome(), _confirm()])
    connector = RecordingConnector([first, second])
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(
        cable_url="ws://h/cable",
        api_key=api_key,
        reconnect_base_delay=0.0,
        reconnect_max_delay=0.0,
    )

    async def _drain() -> List[Any]:
        return [u async for u in stream]

    await asyncio.wait_for(_drain(), timeout=DEADLINE)

    assert first.closed is True, "the dropped socket was never closed"
    assert_no_socket_leaked(connector)


# --------------------------------------------------------------------------
# 3. Close / cancel stop the lifecycle
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_close_prevents_any_further_connect(monkeypatch, api_key):
    ws = ScriptedSocket([_welcome(), _confirm()])
    connector = RecordingConnector([ws])
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(cable_url="ws://h/cable", api_key=api_key)
    await asyncio.wait_for(stream.connect(), timeout=DEADLINE)
    await asyncio.wait_for(stream.close(), timeout=DEADLINE)

    assert ws.closed is True
    assert stream._ws is None

    # A closed stream must not silently open a new socket.
    with pytest.raises(ConnectionError, match="closed"):
        await asyncio.wait_for(stream.connect(), timeout=DEADLINE)

    # Iterating a closed stream yields nothing and reconnects nothing.
    async def _drain() -> List[Any]:
        return [u async for u in stream]

    assert await asyncio.wait_for(_drain(), timeout=DEADLINE) == []
    assert len(connector.calls) == 1
    assert_no_pending_tasks()


@pytest.mark.asyncio
async def test_close_is_idempotent(monkeypatch, api_key):
    ws = ScriptedSocket([_welcome(), _confirm()])
    connector = RecordingConnector([ws])
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(cable_url="ws://h/cable", api_key=api_key)
    await asyncio.wait_for(stream.connect(), timeout=DEADLINE)
    await asyncio.wait_for(stream.close(), timeout=DEADLINE)
    await asyncio.wait_for(stream.close(), timeout=DEADLINE)

    unsubscribes = [m for m in ws.sent if m.get("command") == "unsubscribe"]
    assert len(unsubscribes) == 1
    assert_no_socket_leaked(connector)


@pytest.mark.asyncio
async def test_close_during_backoff_stops_reconnecting(monkeypatch, api_key):
    """Closing while the iterator waits to reconnect must not open a new socket."""
    first = ScriptedSocket([_welcome(), _confirm(), ScriptedSocket.DROP])
    connector = RecordingConnector([first])
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(
        cable_url="ws://h/cable",
        api_key=api_key,
        max_reconnect_attempts=10,
        reconnect_base_delay=0.2,
        reconnect_max_delay=0.2,
    )

    async def _drain() -> List[Any]:
        return [u async for u in stream]

    task = asyncio.create_task(_drain())
    await asyncio.sleep(0.05)  # let it drop and enter backoff
    await asyncio.wait_for(stream.close(), timeout=DEADLINE)

    assert await asyncio.wait_for(task, timeout=DEADLINE) == []
    assert len(connector.calls) == 1, "reconnected after close()"
    assert_no_socket_leaked(connector)
    assert_no_pending_tasks()


@pytest.mark.asyncio
async def test_cancelling_an_active_stream_leaves_nothing_pending(monkeypatch, api_key):
    first = ScriptedSocket([_welcome(), _confirm(), ScriptedSocket.HANG])
    connector = RecordingConnector([first])
    _patch_connect(monkeypatch, connector)

    stream = PriceStream(cable_url="ws://h/cable", api_key=api_key)

    async def _consume() -> None:
        async with stream as s:
            async for _ in s:
                pass

    task = asyncio.create_task(_consume())
    await asyncio.wait_for(first.recv_started.wait(), timeout=DEADLINE)
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=DEADLINE)

    assert_no_socket_leaked(connector)
    assert len(connector.calls) == 1
    assert_no_pending_tasks()


# --------------------------------------------------------------------------
# 4. Sync/async parity
# --------------------------------------------------------------------------

def test_streaming_is_async_only(api_key):
    """Streaming has no sync counterpart; pin that so parity cannot drift silently.

    If a sync stream is ever added, this test fails and forces the same bounded
    setup + cleanup + reconnect-budget lifecycle to be applied to it.
    """
    from oilpriceapi import OilPriceAPI

    client = OilPriceAPI(api_key=api_key)
    assert not hasattr(client, "stream")
