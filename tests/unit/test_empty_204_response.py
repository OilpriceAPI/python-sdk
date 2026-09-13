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
  - typed errors for 401/403 are untouched, and a 204 is not retried.

Transport mocking follows this repo's existing convention -- patching
`httpx.Client.request` / `httpx.AsyncClient.request`, as
tests/unit/test_diesel_envelope.py does -- so no extra HTTP-mocking dependency
is needed.
"""

import json
from unittest.mock import Mock, patch

import pytest

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI
from oilpriceapi.exceptions import AuthenticationError, OilPriceAPIError

# Not a credential: a fixture string, every request here is mocked.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])

WEBHOOK = "/v1/webhooks/fixture-id"


def _no_content(status=204, body=b""):
    """A real no-content response: json() raises, content is empty."""
    response = Mock()
    response.status_code = status
    response.headers = {}
    response.content = body
    response.text = body.decode()
    response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
    return response


def _malformed(status=200, body=b"{not json"):
    """A real parse failure: json() raises but the body is NOT empty."""
    response = Mock()
    response.status_code = status
    response.headers = {}
    response.content = body
    response.text = body.decode()
    response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
    return response


def _error(status, payload):
    response = Mock()
    response.status_code = status
    response.headers = {}
    response.content = json.dumps(payload).encode()
    response.text = json.dumps(payload)
    response.json.return_value = payload
    return response


def _sync():
    return OilPriceAPI(api_key=FIXTURE_KEY, max_retries=1)


def _async():
    return AsyncOilPriceAPI(api_key=FIXTURE_KEY, max_retries=1)


# --- 204 with no body is success -------------------------------------------

@patch("httpx.Client.request")
def test_sync_delete_accepts_204_no_content(mock_request):
    mock_request.return_value = _no_content()
    assert _sync().webhooks.delete("fixture-id") is None


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request")
async def test_async_delete_accepts_204_no_content(mock_request):
    mock_request.return_value = _no_content()
    assert await _async().webhooks.delete("fixture-id") is None


@patch("httpx.Client.request")
def test_sync_request_returns_empty_dict_for_204(mock_request):
    mock_request.return_value = _no_content()
    assert _sync().request("DELETE", WEBHOOK) == {}


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request")
async def test_async_request_returns_empty_dict_for_204(mock_request):
    mock_request.return_value = _no_content()
    assert await _async().request("DELETE", WEBHOOK) == {}


@patch("httpx.Client.request")
def test_request_with_headers_accepts_204(mock_request):
    """The third decode site, which #103 names alongside the other two."""
    response = _no_content()
    response.headers = {"X-Request-Id": "abc"}
    mock_request.return_value = response

    body, headers = _sync().request_with_headers("DELETE", WEBHOOK)

    assert body == {}
    assert headers["X-Request-Id"] == "abc"


@pytest.mark.parametrize("status", [200, 202, 204])
@patch("httpx.Client.request")
def test_any_2xx_with_an_empty_body_is_success(mock_request, status):
    """A 200 or 202 with a genuinely empty body is the same situation."""
    mock_request.return_value = _no_content(status=status)
    assert _sync().request("DELETE", WEBHOOK) == {}


@patch("httpx.Client.request")
def test_whitespace_only_body_is_treated_as_empty(mock_request):
    mock_request.return_value = _no_content(status=200, body=b"\n  \n")
    assert _sync().request("DELETE", WEBHOOK) == {}


# --- what must STILL fail ---------------------------------------------------

@patch("httpx.Client.request")
def test_malformed_nonempty_200_is_still_an_error(mock_request):
    """A real parse failure must not be laundered into an empty success."""
    mock_request.return_value = _malformed()
    with pytest.raises(json.JSONDecodeError):
        _sync().request("GET", "/v1/prices/latest")


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request")
async def test_async_malformed_nonempty_200_is_still_an_error(mock_request):
    mock_request.return_value = _malformed()
    with pytest.raises(json.JSONDecodeError):
        await _async().request("GET", "/v1/prices/latest")


@patch("httpx.Client.request")
def test_204_is_not_retried(mock_request):
    """A success must not burn the retry budget."""
    mock_request.return_value = _no_content()
    _sync().request("DELETE", WEBHOOK)
    assert mock_request.call_count == 1


@patch("httpx.Client.request")
def test_401_still_raises_authentication_error(mock_request):
    mock_request.return_value = _error(401, {"error": "bad key"})
    with pytest.raises(AuthenticationError):
        _sync().request("DELETE", WEBHOOK)


@patch("httpx.Client.request")
def test_403_still_raises_a_typed_error(mock_request):
    mock_request.return_value = _error(403, {"error": "forbidden"})
    with pytest.raises(OilPriceAPIError):
        _sync().request("DELETE", WEBHOOK)


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request")
async def test_async_401_still_raises_authentication_error(mock_request):
    mock_request.return_value = _error(401, {"error": "bad key"})
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
