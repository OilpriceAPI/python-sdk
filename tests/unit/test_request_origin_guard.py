"""Raw paths must never move the request off the authenticated API origin (#102).

Every assertion here is made on what reaches the transport, not on an internal
flag: an off-origin path must produce ZERO outbound requests, so the customer's
API key is never attached to a host that is not OilPriceAPI.
"""

import asyncio

import httpx
import pytest

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI
from oilpriceapi.exceptions import OilPriceAPIError

# Not a credential: a fixture string used only against a mock transport.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])

FOREIGN_HOST = "fixture.invalid"

# Raw paths a caller could build from untrusted input. Each one either moves the
# origin outright or is normalized into an origin change by some parser in the
# chain (scheme-relative, userinfo authority, backslash, absolute URL).
OFF_ORIGIN_PATHS = [
    "//fixture.invalid/v1/prices/latest",
    "///fixture.invalid/v1/prices/latest",
    "//user@fixture.invalid/v1/prices/latest",
    "//fixture.invalid:8443/v1/prices/latest",
    "/\\fixture.invalid/v1/prices/latest",
    "\\\\fixture.invalid/v1/prices/latest",
    "https://fixture.invalid/v1/prices/latest",
    "http://fixture.invalid/v1/prices/latest",
    "/v1/prices\nHost: fixture.invalid",
]

ON_ORIGIN_PATHS = [
    "/v1/prices/latest",
    "v1/prices/latest",
    "/v1/prices/past_week",
    "/v1/commodities/BRENT%20CRUDE/summary",
    "/v1/subscriptions/9f3c1a2b-0000-4000-8000-000000000000",
]


class _Recorder:
    """Mock transport that records every request that actually goes out."""

    def __init__(self):
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        return httpx.Response(200, json={"status": "success", "data": {}})

    @property
    def hosts(self):
        return [r.url.host for r in self.requests]

    @property
    def authenticated_foreign_requests(self):
        return [
            r
            for r in self.requests
            if r.url.host != "api.oilpriceapi.com"
            and (r.headers.get("authorization") or r.headers.get("Authorization"))
        ]


def _sync_client(recorder, **kwargs):
    client = OilPriceAPI(api_key=FIXTURE_KEY, **kwargs)
    client._client = httpx.Client(
        base_url=client.base_url,
        headers=client.headers,
        transport=httpx.MockTransport(recorder),
    )
    return client


def _async_client(recorder, **kwargs):
    client = AsyncOilPriceAPI(api_key=FIXTURE_KEY, **kwargs)
    client._client = httpx.AsyncClient(
        base_url=client.base_url,
        headers=client.headers,
        transport=httpx.MockTransport(recorder),
    )
    return client


@pytest.mark.parametrize("path", OFF_ORIGIN_PATHS)
def test_sync_request_sends_nothing_for_off_origin_path(path):
    recorder = _Recorder()
    client = _sync_client(recorder)

    with pytest.raises(OilPriceAPIError):
        client.request("GET", path)

    assert recorder.requests == [], (
        f"path {path!r} reached the wire at {recorder.hosts}"
    )


@pytest.mark.parametrize("path", OFF_ORIGIN_PATHS)
def test_sync_request_with_headers_sends_nothing_for_off_origin_path(path):
    recorder = _Recorder()
    client = _sync_client(recorder)

    with pytest.raises(OilPriceAPIError):
        client.request_with_headers("GET", path)

    assert recorder.requests == []


@pytest.mark.parametrize("path", OFF_ORIGIN_PATHS)
def test_async_request_sends_nothing_for_off_origin_path(path):
    recorder = _Recorder()

    async def scenario():
        client = _async_client(recorder)
        with pytest.raises(OilPriceAPIError):
            await client.request("GET", path)
        await client._client.aclose()

    asyncio.run(scenario())
    assert recorder.requests == []


def test_api_key_never_reaches_a_foreign_host():
    """The property that actually matters: the key stays on our origin."""
    recorder = _Recorder()
    client = _sync_client(recorder)

    for path in OFF_ORIGIN_PATHS:
        try:
            client.request("GET", path)
        except OilPriceAPIError:
            pass

    assert recorder.authenticated_foreign_requests == []
    assert FOREIGN_HOST not in recorder.hosts


@pytest.mark.parametrize("path", ON_ORIGIN_PATHS)
def test_valid_paths_still_reach_the_api_origin(path):
    recorder = _Recorder()
    client = _sync_client(recorder)

    client.request("GET", path, params={"by_code": "BRENT_CRUDE_USD"})

    assert len(recorder.requests) == 1
    sent = recorder.requests[0]
    assert sent.url.host == "api.oilpriceapi.com"
    assert sent.url.scheme == "https"
    assert sent.url.params.get("by_code") == "BRENT_CRUDE_USD"
    assert sent.headers["Authorization"].endswith(FIXTURE_KEY)


def test_explicit_custom_base_url_is_preserved():
    """Proxies and test servers stay supported — the guard pins to the CONFIGURED origin."""
    recorder = _Recorder()
    client = _sync_client(recorder, base_url="https://proxy.internal.example:8443/api")

    client.request("GET", "/v1/prices/latest")

    assert len(recorder.requests) == 1
    sent = recorder.requests[0]
    assert sent.url.host == "proxy.internal.example"
    assert sent.url.port == 8443


def test_off_origin_path_is_still_rejected_under_a_custom_base_url():
    recorder = _Recorder()
    client = _sync_client(recorder, base_url="https://proxy.internal.example:8443/api")

    with pytest.raises(OilPriceAPIError):
        client.request("GET", "//fixture.invalid/v1/prices/latest")

    assert recorder.requests == []


def test_non_string_path_is_rejected_before_any_request():
    recorder = _Recorder()
    client = _sync_client(recorder)

    with pytest.raises(OilPriceAPIError):
        client.request("GET", None)

    assert recorder.requests == []


def test_rejection_message_does_not_leak_the_api_key():
    recorder = _Recorder()
    client = _sync_client(recorder)

    with pytest.raises(OilPriceAPIError) as excinfo:
        client.request("GET", "//fixture.invalid/v1/prices/latest")

    assert FIXTURE_KEY not in str(excinfo.value)
