"""Server-side attribution contract for the Python SDK.

`MinimalAnalyticsService#detect_sdk_info` in oilpriceapi-api parses
sdk_language/sdk_version out of the User-Agent with exactly the regex
pinned below. A User-Agent that stops matching it still returns 200 --
the request succeeds and the SDK silently disappears from adoption
reporting. That is a failure no HTTP-level test would catch, so these
tests assert the *parsed* language and version rather than a substring.

Keep SERVER_SDK_REGEX in step with
app/services/minimal_analytics_service.rb (detect_sdk_info).
"""

import re

import pytest

from oilpriceapi import OilPriceAPI
from oilpriceapi.version import SDK_NAME, SDK_VERSION

SERVER_SDK_REGEX = re.compile(
    r"oilpriceapi-([a-z0-9-]+)/v?([\d]+\.[\d]+\.?[\d]*)", re.IGNORECASE
)


def _parse(user_agent):
    return SERVER_SDK_REGEX.search(user_agent or "")


def test_sdk_name_and_version_are_shaped_for_the_server_regex():
    match = _parse(f"{SDK_NAME}/{SDK_VERSION}")
    assert match is not None, f"{SDK_NAME}/{SDK_VERSION} does not parse server-side"
    assert match.group(1) == "python"
    assert match.group(2) == SDK_VERSION


def test_sync_client_user_agent_parses_to_python_and_the_real_version():
    client = OilPriceAPI(api_key="test_key")
    match = _parse(client.headers.get("User-Agent"))

    assert match is not None, "sync client User-Agent is not attributable server-side"
    assert match.group(1) == "python"
    assert match.group(2) == SDK_VERSION


def test_async_client_user_agent_parses_to_python_and_the_real_version():
    from oilpriceapi import AsyncOilPriceAPI

    client = AsyncOilPriceAPI(api_key="test_key")
    match = _parse(client.headers.get("User-Agent"))

    assert match is not None, "async client User-Agent is not attributable server-side"
    assert match.group(1) == "python"
    assert match.group(2) == SDK_VERSION


@pytest.mark.asyncio
async def test_streaming_handshake_sends_an_attributable_user_agent(monkeypatch):
    """The ActionCable upgrade is an ordinary HTTP request.

    Without a User-Agent a streaming client is indistinguishable from a
    hand-rolled WebSocket and drops out of SDK attribution entirely. The Go
    SDK already sets one on its handshake (stream.go).
    """
    from oilpriceapi.streaming import client as streaming_client

    captured = {}

    class _FakeWS:
        """Scripted ActionCable peer: welcome, then confirm_subscription."""

        def __init__(self):
            self._frames = iter(
                ['{"type": "welcome"}', '{"type": "confirm_subscription"}']
            )

        async def recv(self):
            return next(self._frames)

        async def send(self, _data):
            return None

        async def close(self):
            return None

    async def _fake_connect(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs.get("additional_headers") or {}
        return _FakeWS()

    class _FakeWebsockets:
        connect = staticmethod(_fake_connect)

    monkeypatch.setattr(
        streaming_client, "_import_websockets", lambda: _FakeWebsockets
    )

    stream = streaming_client.PriceStream(
        cable_url="wss://api.oilpriceapi.com/cable", api_key="test_key"
    )
    await stream.connect()

    headers = {k.lower(): v for k, v in captured["headers"].items()}
    match = _parse(headers.get("user-agent"))

    assert match is not None, (
        "WebSocket handshake sent no attributable User-Agent; "
        f"headers were {sorted(headers)}"
    )
    assert match.group(1) == "python"
    assert match.group(2) == SDK_VERSION
