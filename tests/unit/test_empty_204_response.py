"""A successful 204 must not be reported to the caller as a failure (#103).

Both clients parse EVERY 2xx with `response.json()`. The Rails webhooks
controller answers `destroy` with `head :no_content` -- a 204 with an empty
body -- so `client.webhooks.delete(...)` raises JSONDecodeError. The deletion
SUCCEEDED and the caller was told it failed, which is the worst shape of error
for a mutation: the obvious recovery is to retry a delete that already worked.

Narrow by design:
  - an empty body on a 2xx is success, and `delete` keeps returning None;
  - a MALFORMED NON-EMPTY 200 stays an error -- it is a real parse failure and
    must not be laundered into an empty success;
  - typed errors for 401/403/429 are untouched.
"""

import httpx
import pytest
import respx

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI
from oilpriceapi.exceptions import (
    AuthenticationError,
    OilPriceAPIError,
)

BASE = "https://api.oilpriceapi.com"
WEBHOOK = "/v1/webhooks/fixture-id"


def _sync():
    return OilPriceAPI(api_key="k", base_url=BASE, max_retries=1)


def _async():
    return AsyncOilPriceAPI(api_key="k", base_url=BASE, max_retries=1)


# --- 204 with no body is success -------------------------------------------

@respx.mock
def test_sync_delete_accepts_204_no_content():
    respx.delete(f"{BASE}{WEBHOOK}").mock(return_value=httpx.Response(204))
    assert _sync().webhooks.delete("fixture-id") is None


@pytest.mark.asyncio
@respx.mock
async def test_async_delete_accepts_204_no_content():
    respx.delete(f"{BASE}{WEBHOOK}").mock(return_value=httpx.Response(204))
    assert await _async().webhooks.delete("fixture-id") is None


@respx.mock
def test_sync_request_returns_empty_dict_for_204():
    respx.delete(f"{BASE}{WEBHOOK}").mock(return_value=httpx.Response(204))
    assert _sync().request("DELETE", WEBHOOK) == {}


@pytest.mark.asyncio
@respx.mock
async def test_async_request_returns_empty_dict_for_204():
    respx.delete(f"{BASE}{WEBHOOK}").mock(return_value=httpx.Response(204))
    assert await _async().request("DELETE", WEBHOOK) == {}


@respx.mock
def test_request_with_headers_accepts_204():
    """The third decode site, which #103 names alongside the other two."""
    respx.delete(f"{BASE}{WEBHOOK}").mock(
        return_value=httpx.Response(204, headers={"X-Request-Id": "abc"})
    )
    body, headers = _sync().request_with_headers("DELETE", WEBHOOK)
    assert body == {}
    assert headers["X-Request-Id"] == "abc"


@pytest.mark.parametrize("status", [200, 202, 204])
@respx.mock
def test_any_2xx_with_an_empty_body_is_success(status):
    """A 200 or 202 with a genuinely empty body is the same situation."""
    respx.delete(f"{BASE}{WEBHOOK}").mock(
        return_value=httpx.Response(status, content=b"")
    )
    assert _sync().request("DELETE", WEBHOOK) == {}


@respx.mock
def test_whitespace_only_body_is_treated_as_empty():
    respx.delete(f"{BASE}{WEBHOOK}").mock(
        return_value=httpx.Response(200, content=b"\n  \n")
    )
    assert _sync().request("DELETE", WEBHOOK) == {}


# --- what must STILL fail ---------------------------------------------------

@respx.mock
def test_malformed_nonempty_200_is_still_an_error():
    """A real parse failure must not be laundered into an empty success."""
    respx.get(f"{BASE}/v1/prices/latest").mock(
        return_value=httpx.Response(200, content=b"{not json")
    )
    with pytest.raises(Exception) as exc:
        _sync().request("GET", "/v1/prices/latest")
    assert not isinstance(exc.value, type(None))


@pytest.mark.asyncio
@respx.mock
async def test_async_malformed_nonempty_200_is_still_an_error():
    respx.get(f"{BASE}/v1/prices/latest").mock(
        return_value=httpx.Response(200, content=b"{not json")
    )
    with pytest.raises(Exception):
        await _async().request("GET", "/v1/prices/latest")


@respx.mock
def test_204_is_not_retried():
    """A success must not burn the retry budget."""
    route = respx.delete(f"{BASE}{WEBHOOK}").mock(
        return_value=httpx.Response(204)
    )
    _sync().request("DELETE", WEBHOOK)
    assert route.call_count == 1


@respx.mock
def test_401_still_raises_authentication_error():
    respx.delete(f"{BASE}{WEBHOOK}").mock(
        return_value=httpx.Response(401, json={"error": "bad key"})
    )
    with pytest.raises(AuthenticationError):
        _sync().request("DELETE", WEBHOOK)


@respx.mock
def test_403_still_raises_a_typed_error():
    respx.delete(f"{BASE}{WEBHOOK}").mock(
        return_value=httpx.Response(403, json={"error": "forbidden"})
    )
    with pytest.raises(OilPriceAPIError):
        _sync().request("DELETE", WEBHOOK)


@pytest.mark.asyncio
@respx.mock
async def test_async_401_still_raises_authentication_error():
    respx.delete(f"{BASE}{WEBHOOK}").mock(
        return_value=httpx.Response(401, json={"error": "bad key"})
    )
    with pytest.raises(AuthenticationError):
        await _async().request("DELETE", WEBHOOK)


# --- sync/async parity ------------------------------------------------------

def test_all_three_decode_sites_share_one_helper():
    """client.request, client.request_with_headers and async_client.request
    must decode identically; three copies of the branch would drift."""
    import inspect

    from oilpriceapi import async_client, client

    sync_src = inspect.getsource(client)
    async_src = inspect.getsource(async_client)
    for src, name in ((sync_src, "client"), (async_src, "async_client")):
        assert "decode_json_body" in src, name
        # No bare `return response.json()` left behind.
        assert "return response.json()" not in src, name
    assert "return response.json(), response.headers" not in sync_src
