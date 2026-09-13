"""
Async WebSocket streaming client for OilPriceAPI.

Implements the Rails ActionCable JSON subprotocol against the ``/cable``
endpoint and exposes an ergonomic async-iterator API:

    >>> async with client.stream.prices(commodities=["BRENT_CRUDE_USD"]) as stream:
    ...     async for update in stream:
    ...         print(update.type, update.raw)

ActionCable handshake (as implemented by the OilPriceAPI server):

1. Client connects to ``wss://api.oilpriceapi.com/cable`` (auth via ``?token=``
   query param or ``Authorization: Token <key>`` header).
2. Server sends ``{"type": "welcome"}``.
3. Client sends a ``subscribe`` command whose ``identifier`` is a JSON string
   ``{"channel": "EnergyPricesChannel", "api_key": "<key>"}``.
4. Server replies ``{"type": "confirm_subscription", "identifier": ...}``.
5. Broadcasts arrive as ``{"identifier": ..., "message": {...}}``.
6. Server periodically sends ``{"type": "ping"}`` keepalives (ignored).

The whole of steps 1-4 is bounded by ``setup_timeout`` (default:
``open_timeout``), and every socket allocated along the way is closed on any
failure or cancellation.

Requires the optional ``[stream]`` extra (``pip install oilpriceapi[stream]``).
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import sys
from types import TracebackType
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, List, Optional, Tuple, Type

from .models import StreamUpdate

if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    from ..async_client import AsyncOilPriceAPI

logger = logging.getLogger(__name__)

# ActionCable channel name as defined server-side (EnergyPricesChannel).
CHANNEL_NAME = "EnergyPricesChannel"


class StreamingNotInstalledError(ImportError):
    """Raised when the optional ``websockets`` dependency is missing."""


class StreamAuthError(ConnectionError):
    """A permanent streaming setup failure -- retrying will not fix it.

    Raised when the server refuses the connection outright (an ActionCable
    ``disconnect`` frame) or rejects the subscription (``reject_subscription``):
    a bad API key, a missing streaming entitlement, or an unknown channel.
    Subclasses :class:`ConnectionError` so existing ``except ConnectionError``
    handlers keep working, while the reconnect loop can tell it apart from a
    transient network failure and stop immediately instead of burning the
    reconnect budget on a refusal that will not change.
    """


# Teardown is bounded too: a socket that refuses to close must not wedge the
# caller inside ``close()`` or inside the cleanup path of a failed setup.
TEARDOWN_TIMEOUT = 5.0


def _import_websockets() -> Any:
    """Import the ``websockets`` library, raising a friendly error if absent."""
    try:
        import websockets  # noqa: PLC0415

        return websockets
    except ImportError as exc:  # pragma: no cover - exercised via monkeypatch
        raise StreamingNotInstalledError(
            "WebSocket streaming requires the 'websockets' package. "
            "Install it with: pip install 'oilpriceapi[stream]'"
        ) from exc


def _transient_errors() -> Tuple[Type[BaseException], ...]:
    """Error types a reconnect should retry (as opposed to give up on).

    ``OSError`` covers refused/reset connections and the ``ConnectionError``
    the bounded setup raises on timeout; :class:`StreamAuthError` is a subclass
    of it and is therefore matched *before* this tuple by the reconnect loop.
    """
    websockets = _import_websockets()
    return (OSError, asyncio.TimeoutError, websockets.exceptions.WebSocketException)


class PriceStream:
    """An async-iterable handle over a single ActionCable subscription.

    Connects lazily on ``__aenter__`` (or first iteration), performs the
    ActionCable handshake, and yields :class:`StreamUpdate` objects. On
    transient disconnects it reconnects with exponential backoff + jitter,
    transparently re-subscribing, up to ``max_reconnect_attempts``.

    **Timeouts.** ``open_timeout`` is handed to the transport and bounds the
    WebSocket upgrade only. ``setup_timeout`` bounds the *whole* setup
    lifecycle -- upgrade, ``welcome`` and ``confirm_subscription`` -- and
    defaults to ``open_timeout``, so by default the configured timeout does
    cover protocol setup and there is no unbounded wait anywhere in
    :meth:`connect`. Pass ``setup_timeout`` explicitly when a slow server needs
    longer for the handshake than for the upgrade.

    **Cleanup.** Every socket this stream allocates is closed on any failure or
    cancellation, including a handshake that times out and a ``__aenter__``
    that raises (where ``__aexit__`` never runs). Once :meth:`close` has been
    called the stream is retired: it will not reconnect and :meth:`connect`
    raises.
    """

    def __init__(
        self,
        *,
        cable_url: str,
        api_key: str,
        channel: str = CHANNEL_NAME,
        params: Optional[Dict[str, Any]] = None,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 10,
        reconnect_base_delay: float = 1.0,
        reconnect_max_delay: float = 30.0,
        ping_interval: Optional[float] = None,
        open_timeout: float = 10.0,
        setup_timeout: Optional[float] = None,
    ) -> None:
        self._cable_url = cable_url
        self._api_key = api_key
        self._channel = channel
        self._params = params or {}
        self._auto_reconnect = auto_reconnect
        self._max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_base_delay = reconnect_base_delay
        self._reconnect_max_delay = reconnect_max_delay
        self._ping_interval = ping_interval
        self._open_timeout = open_timeout
        # Default: the caller's open_timeout also bounds the handshake.
        self._setup_timeout = open_timeout if setup_timeout is None else setup_timeout

        self._ws: Any = None
        self._closed = False
        self._subscribed = False

    # -- identifier --------------------------------------------------------

    @property
    def identifier(self) -> str:
        """The ActionCable subscription identifier (a JSON string)."""
        ident: Dict[str, Any] = {"channel": self._channel, "api_key": self._api_key}
        ident.update(self._params)
        # Sort keys for a stable identifier (ActionCable matches on exact string).
        return json.dumps(ident, sort_keys=True)

    @property
    def setup_timeout(self) -> float:
        """Deadline, in seconds, for connect + welcome + confirm_subscription."""
        return self._setup_timeout

    # -- connection lifecycle ---------------------------------------------

    async def connect(self) -> None:
        """Open the WebSocket and complete the ActionCable handshake.

        The entire lifecycle is bounded by :attr:`setup_timeout`; on timeout,
        failure or cancellation the socket allocated by this call is closed
        before the error propagates, so no upgraded socket is ever orphaned.
        """
        if self._closed:
            raise ConnectionError(
                "Stream is closed; open a new stream to reconnect."
            )

        # The socket lives in a box the *caller* of wait_for can reach, so the
        # cleanup below runs outside the (possibly cancelled) setup coroutine.
        box: Dict[str, Any] = {}
        try:
            ws = await asyncio.wait_for(self._setup(box), timeout=self._setup_timeout)
        except asyncio.TimeoutError as exc:
            await self._close_socket(box.get("ws"))
            raise ConnectionError(
                f"ActionCable setup timed out after {self._setup_timeout:g}s "
                "(connect, welcome, confirm_subscription). Raise setup_timeout "
                "if the server needs longer, or check the /cable endpoint."
            ) from exc
        except BaseException:
            # Includes cancellation and a rejected subscription: close first.
            await self._close_socket(box.get("ws"))
            raise

        if self._closed:
            # close() landed while the handshake was in flight.
            await self._close_socket(ws)
            raise ConnectionError("Stream is closed; open a new stream to reconnect.")

        self._ws = ws
        self._subscribed = True

    async def _setup(self, box: Dict[str, Any]) -> Any:
        """Allocate a socket and run the handshake on it. Bounded by connect()."""
        ws = await self._open_socket()
        box["ws"] = ws
        await self._await_welcome(ws)
        await self._subscribe(ws)
        return ws

    async def _open_socket(self) -> Any:
        """Open the raw WebSocket (the transport upgrade only)."""
        websockets = _import_websockets()
        # Auth via query param is the most portable across proxies; the server
        # also accepts the Authorization header (connection.rb find_verified_user).
        sep = "&" if "?" in self._cable_url else "?"
        url = f"{self._cable_url}{sep}token={self._api_key}"
        # Identify the SDK on the handshake exactly as the HTTP client does.
        # The upgrade request is an ordinary HTTP request, so without these
        # headers a streaming client is indistinguishable from a hand-rolled
        # WebSocket and drops out of SDK attribution entirely. The Go SDK
        # (stream.go) already sets the User-Agent here.
        from ..version import SDK_NAME, SDK_VERSION

        python_version = (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
        headers = {
            "Authorization": f"Token {self._api_key}",
            "User-Agent": f"{SDK_NAME}/{SDK_VERSION} python/{python_version}",
            "X-SDK-Name": SDK_NAME,
            "X-SDK-Version": SDK_VERSION,
        }

        return await websockets.connect(
            url,
            additional_headers=headers,
            ping_interval=self._ping_interval,
            open_timeout=self._open_timeout,
        )

    async def _await_welcome(self, ws: Any) -> None:
        """Wait for the ActionCable ``welcome`` frame before subscribing."""
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            msg_type = data.get("type")
            if msg_type == "welcome":
                return
            if msg_type == "disconnect":
                raise StreamAuthError(
                    f"Server refused connection: {data.get('reason', 'unknown')}"
                )
            # Ignore stray pings while waiting for welcome.

    async def _subscribe(self, ws: Any) -> None:
        """Send the subscribe command and await ``confirm_subscription``."""
        await ws.send(
            json.dumps({"command": "subscribe", "identifier": self.identifier})
        )
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            msg_type = data.get("type")
            if msg_type == "confirm_subscription":
                return
            if msg_type == "reject_subscription":
                raise StreamAuthError(
                    "Subscription rejected; confirm the API key and streaming entitlement at "
                    "https://www.oilpriceapi.com/pricing."
                )
            # Ignore pings / pre-confirmation noise.

    async def _close_socket(self, ws: Any) -> None:
        """Close one socket. Best-effort and bounded; never raises."""
        if ws is None:
            return
        try:
            await asyncio.wait_for(ws.close(), timeout=TEARDOWN_TIMEOUT)
        except Exception:  # noqa: BLE001 - best-effort teardown
            logger.debug("Failed to close websocket cleanly", exc_info=True)

    async def close(self) -> None:
        """Unsubscribe, close the socket, and retire the stream.

        Idempotent. After this returns the stream will not reconnect, holds no
        socket, and :meth:`connect` raises.
        """
        self._closed = True
        ws, self._ws = self._ws, None
        subscribed, self._subscribed = self._subscribed, False
        if ws is None:
            return
        try:
            if subscribed:
                await asyncio.wait_for(
                    ws.send(
                        json.dumps(
                            {"command": "unsubscribe", "identifier": self.identifier}
                        )
                    ),
                    timeout=TEARDOWN_TIMEOUT,
                )
        except Exception:  # noqa: BLE001 - best-effort teardown
            logger.debug("Failed to send unsubscribe on close", exc_info=True)
        finally:
            await self._close_socket(ws)

    # -- async context manager --------------------------------------------

    async def __aenter__(self) -> "PriceStream":
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self.close()

    # -- iteration ---------------------------------------------------------

    def __aiter__(self) -> AsyncIterator[StreamUpdate]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[StreamUpdate]:
        websockets = _import_websockets()
        connection_closed = websockets.exceptions.ConnectionClosed
        connection_closed_ok = websockets.exceptions.ConnectionClosedOK

        if self._ws is None and not self._closed:
            await self.connect()

        attempts = 0
        while not self._closed:
            ws = self._ws
            if ws is None:
                break
            try:
                raw = await ws.recv()
            except connection_closed_ok:
                # Clean server-side close — end iteration, do not reconnect.
                break
            except connection_closed:
                if not self._auto_reconnect or self._closed:
                    break
                # Consume the configured budget here rather than letting a
                # failed reconnect escape on the first attempt.
                attempts = await self._reconnect_with_budget(attempts)
                if self._closed or self._ws is None:
                    break
                continue

            attempts = 0  # reset the budget after any successful receive
            data = json.loads(raw)
            update = self._dispatch(data)
            if update is not None:
                yield update

        # Iteration finished for good (clean close, close() by the caller, or
        # auto_reconnect disabled): release the socket rather than leaving it
        # to garbage collection.
        await self.close()

    def _dispatch(self, data: Dict[str, Any]) -> Optional[StreamUpdate]:
        """Translate a raw ActionCable frame into a StreamUpdate (or None)."""
        msg_type = data.get("type")
        # Protocol control frames carry a top-level "type"; ignore them.
        if msg_type in ("ping", "welcome", "confirm_subscription", "reject_subscription"):
            return None
        if msg_type == "disconnect":
            logger.warning("ActionCable disconnect frame: %s", data.get("reason"))
            return None

        message = data.get("message")
        if not isinstance(message, dict):
            return None
        return StreamUpdate.from_message(message)

    # -- reconnect ---------------------------------------------------------

    async def _backoff(self, attempt: int) -> None:
        delay = min(
            self._reconnect_base_delay * (2 ** (attempt - 1)),
            self._reconnect_max_delay,
        )
        delay += random.uniform(0, delay * 0.25)  # noqa: S311 - jitter, not crypto
        logger.info("Reconnecting stream in %.2fs (attempt %d)", delay, attempt)
        await asyncio.sleep(delay)

    async def _reconnect_with_budget(self, attempts: int) -> int:
        """Reconnect, spending the bounded consecutive-failure budget.

        A transient failure (refused connection, a setup that timed out, a drop
        mid-handshake) costs one attempt and is retried after backoff. A
        permanent failure (:class:`StreamAuthError` -- bad key, no entitlement,
        rejected subscription) stops at once with that error, because no number
        of retries changes the answer. Raises ``ConnectionError`` once
        ``max_reconnect_attempts`` consecutive attempts have been spent.

        Returns the number of consecutive attempts consumed so far, so the
        caller can reset it on the next successful receive.
        """
        last_exc: Optional[BaseException] = None
        while not self._closed:
            attempts += 1
            if attempts > self._max_reconnect_attempts:
                raise ConnectionError(
                    f"Stream lost after {self._max_reconnect_attempts} reconnect attempts"
                ) from last_exc
            await self._backoff(attempts)
            if self._closed:
                break
            try:
                await self._reconnect()
            except StreamAuthError:
                raise
            except _transient_errors() as exc:
                last_exc = exc
                logger.warning(
                    "Reconnect attempt %d/%d failed: %s",
                    attempts,
                    self._max_reconnect_attempts,
                    exc,
                )
                continue
            return attempts
        return attempts

    async def _reconnect(self) -> None:
        """Drop the current socket (closing it) and run a fresh setup."""
        old, self._ws = self._ws, None
        self._subscribed = False
        await self._close_socket(old)
        await self.connect()


class AsyncStreamNamespace:
    """``client.stream`` namespace exposing streaming factory methods."""

    def __init__(self, client: "AsyncOilPriceAPI") -> None:
        self._client = client

    def _cable_url(self) -> str:
        base = self._client.base_url
        # https -> wss, http -> ws; append /cable mount point.
        if base.startswith("https://"):
            ws_base = "wss://" + base[len("https://") :]
        elif base.startswith("http://"):
            ws_base = "ws://" + base[len("http://") :]
        else:
            ws_base = base
        return ws_base.rstrip("/") + "/cable"

    def prices(
        self,
        commodities: Optional[List[str]] = None,
        *,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 10,
        reconnect_base_delay: float = 1.0,
        reconnect_max_delay: float = 30.0,
        open_timeout: float = 10.0,
        setup_timeout: Optional[float] = None,
    ) -> PriceStream:
        """Open a price-update stream over ``EnergyPricesChannel``.

        Args:
            commodities: Optional list of commodity codes to tag the
                subscription with (sent as a ``commodities`` identifier
                param). The server currently broadcasts the full price block;
                filter client-side via ``update.price_update`` if desired.
            auto_reconnect: Reconnect with backoff on transient drops.
            max_reconnect_attempts: Give up after this many failures.
            reconnect_base_delay: Initial backoff delay (seconds).
            reconnect_max_delay: Maximum backoff delay (seconds).
            open_timeout: WebSocket upgrade timeout (seconds). Also the
                default deadline for the whole ActionCable handshake.
            setup_timeout: Deadline (seconds) for the complete setup
                lifecycle -- upgrade, ``welcome`` and
                ``confirm_subscription``. Defaults to ``open_timeout``; there
                is no unbounded wait either way.

        Returns:
            A :class:`PriceStream` async context manager / iterator.

        Example:
            >>> async with client.stream.prices(["BRENT_CRUDE_USD"]) as stream:
            ...     async for update in stream:
            ...         if update.type == "price_update":
            ...             print(update.price_update.prices)
        """
        params: Dict[str, Any] = {}
        if commodities:
            params["commodities"] = list(commodities)

        api_key = self._client.api_key
        if not api_key:
            raise ValueError("An API key is required to open a stream.")

        return PriceStream(
            cable_url=self._cable_url(),
            api_key=api_key,
            params=params,
            auto_reconnect=auto_reconnect,
            max_reconnect_attempts=max_reconnect_attempts,
            reconnect_base_delay=reconnect_base_delay,
            reconnect_max_delay=reconnect_max_delay,
            open_timeout=open_timeout,
            setup_timeout=setup_timeout,
        )
