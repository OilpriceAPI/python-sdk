"""
Tests for SDK telemetry headers (issue #4).

The API tracks SDK adoption via request headers. Every SDK request must
identify itself with:

    X-SDK-Language: python
    X-SDK-Version: <version>
    X-Client-Type: sdk

Issue #4 reported that ``X-SDK-Language`` and ``X-Client-Type`` were never
reaching the API (0/166 requests), making it impossible to distinguish SDK
traffic from manual ``python-requests``/``python-httpx`` calls. These tests
encode the acceptance criteria for both the sync and async clients, asserting
the headers are both configured on the client and actually transmitted on the
wire.
"""

import asyncio

import httpx

from oilpriceapi import OilPriceAPI
from oilpriceapi.async_client import AsyncOilPriceAPI
from oilpriceapi.version import SDK_VERSION


class TestSyncTelemetryHeaders:
    """Sync client must advertise SDK telemetry headers."""

    def test_headers_include_sdk_language(self):
        client = OilPriceAPI(api_key="test_key")
        assert client.headers["X-SDK-Language"] == "python"

    def test_headers_include_client_type(self):
        client = OilPriceAPI(api_key="test_key")
        assert client.headers["X-Client-Type"] == "sdk"

    def test_headers_include_sdk_version(self):
        client = OilPriceAPI(api_key="test_key")
        assert client.headers["X-SDK-Version"] == SDK_VERSION

    def test_telemetry_headers_sent_on_request(self):
        """Headers must actually be transmitted, not just stored locally."""
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return httpx.Response(
                200,
                json={"data": {"price": 80.0, "commodity": "BRENT_CRUDE_USD"}},
            )

        client = OilPriceAPI(api_key="test_key")
        client._client = httpx.Client(
            base_url=client.base_url,
            headers=client.headers,
            transport=httpx.MockTransport(handler),
        )
        client.request("GET", "/v1/prices/latest")

        assert captured.get("x-sdk-language") == "python"
        assert captured.get("x-client-type") == "sdk"
        assert captured.get("x-sdk-version") == SDK_VERSION


class TestAsyncTelemetryHeaders:
    """Async client must advertise SDK telemetry headers."""

    def test_headers_include_sdk_language(self):
        client = AsyncOilPriceAPI(api_key="test_key")
        assert client.headers["X-SDK-Language"] == "python"

    def test_headers_include_client_type(self):
        client = AsyncOilPriceAPI(api_key="test_key")
        assert client.headers["X-Client-Type"] == "sdk"

    def test_headers_include_sdk_version(self):
        client = AsyncOilPriceAPI(api_key="test_key")
        assert client.headers["X-SDK-Version"] == SDK_VERSION

    def test_telemetry_headers_sent_on_request(self):
        """Async requests must transmit telemetry headers on the wire."""
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return httpx.Response(
                200,
                json={"data": {"price": 80.0, "commodity": "BRENT_CRUDE_USD"}},
            )

        async def run():
            client = AsyncOilPriceAPI(api_key="test_key")
            client._client = httpx.AsyncClient(
                base_url=client.base_url,
                headers=client.headers,
                transport=httpx.MockTransport(handler),
            )
            await client.request("GET", "/v1/prices/latest")
            await client._client.aclose()

        asyncio.run(run())

        assert captured.get("x-sdk-language") == "python"
        assert captured.get("x-client-type") == "sdk"
        assert captured.get("x-sdk-version") == SDK_VERSION
