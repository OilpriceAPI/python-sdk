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

Requires the optional ``[stream]`` extra (``pip install oilpriceapi[stream]``).
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from types import TracebackType
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, List, Optional, Type

from .models import StreamUpdate

if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    from ..async_client import AsyncOilPriceAPI

logger = logging.getLogger(__name__)

# ActionCable channel name as defined server-side (EnergyPricesChannel).
CHANNEL_NAME = "EnergyPricesChannel"


class StreamingNotInstalledError(ImportError):
    """Raised when the optional ``websockets`` dependency is missing."""


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


class PriceStream:
    """An async-iterable handle over a single ActionCable subscription.

    Connects lazily on ``__aenter__`` (or first iteration), performs the
    ActionCable handshake, and yields :class:`StreamUpdate` objects. On
    transient disconnects it reconnects with exponential backoff + jitter,
    transparently re-subscribing, up to ``max_reconnect_attempts``.
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

    # -- connection lifecycle ---------------------------------------------

    async def connect(self) -> None:
        """Open the WebSocket and complete the ActionCable handshake."""
        websockets = _import_websockets()
        # Auth via query param is the most portable across proxies; the server
        # also accepts the Authorization header (connection.rb find_verified_user).
        sep = "&" if "?" in self._cable_url else "?"
        url = f"{self._cable_url}{sep}token={self._api_key}"
        headers = {"Authorization": f"Token {self._api_key}"}

        self._ws = await websockets.connect(
            url,
            additional_headers=headers,
            ping_interval=self._ping_interval,
            open_timeout=self._open_timeout,
        )
        await self._await_welcome()
        await self._subscribe()

    async def _await_welcome(self) -> None:
        """Wait for the ActionCable ``welcome`` frame before subscribing."""
        while True:
            raw = await self._ws.recv()
            data = json.loads(raw)
            msg_type = data.get("type")
            if msg_type == "welcome":
                return
            if msg_type == "disconnect":
                raise ConnectionError(
                    f"Server refused connection: {data.get('reason', 'unknown')}"
                )
            # Ignore stray pings while waiting for welcome.

    async def _subscribe(self) -> None:
        """Send the subscribe command and await ``confirm_subscription``."""
        await self._ws.send(
            json.dumps({"command": "subscribe", "identifier": self.identifier})
        )
        while True:
            raw = await self._ws.recv()
            data = json.loads(raw)
            msg_type = data.get("type")
            if msg_type == "confirm_subscription":
                self._subscribed = True
                return
            if msg_type == "reject_subscription":
                raise ConnectionError(
                    "Subscription rejected — check your plan tier and API key "
                    "(WebSocket streaming requires Reservoir Mastery)."
                )
            # Ignore pings / pre-confirmation noise.

    async def close(self) -> None:
        """Unsubscribe and close the underlying WebSocket."""
        self._closed = True
        if self._ws is not None:
            try:
                if self._subscribed:
                    await self._ws.send(
                        json.dumps({"command": "unsubscribe", "identifier": self.identifier})
                    )
            except Exception:  # noqa: BLE001 - best-effort teardown
                logger.debug("Failed to send unsubscribe on close", exc_info=True)
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001 - best-effort teardown
                logger.debug("Failed to close websocket cleanly", exc_info=True)
            finally:
                self._ws = None
                self._subscribed = False

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
            try:
                raw = await self._ws.recv()
            except connection_closed_ok:
                # Clean server-side close — end iteration, do not reconnect.
                break
            except connection_closed:
                if not self._auto_reconnect or self._closed:
                    break
                attempts += 1
                if attempts > self._max_reconnect_attempts:
                    raise ConnectionError(
                        f"Stream lost after {self._max_reconnect_attempts} reconnect attempts"
                    )
                await self._backoff(attempts)
                await self._reconnect()
                continue

            attempts = 0  # reset backoff after any successful receive
            data = json.loads(raw)
            update = self._dispatch(data)
            if update is not None:
                yield update

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

    async def _reconnect(self) -> None:
        self._subscribed = False
        self._ws = None
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
    ) -> PriceStream:
        """Open a real-time price stream over ``EnergyPricesChannel``.

        Args:
            commodities: Optional list of commodity codes to tag the
                subscription with (sent as a ``commodities`` identifier
                param). The server currently broadcasts the full price block;
                filter client-side via ``update.price_update`` if desired.
            auto_reconnect: Reconnect with backoff on transient drops.
            max_reconnect_attempts: Give up after this many failures.
            reconnect_base_delay: Initial backoff delay (seconds).
            reconnect_max_delay: Maximum backoff delay (seconds).
            open_timeout: Connection open timeout (seconds).

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
        )
