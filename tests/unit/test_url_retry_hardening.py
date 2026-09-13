"""The remaining #123 findings: typed errors, a real 60s cap, honest status.

Three separate promises the code does not keep:

1. ``resolve_api_url``'s docstring says it raises ``ValidationError``. It leaks
   a raw stdlib ``ValueError`` for a base URL with an out-of-range port or a
   non-ASCII netloc whose NFKC normalisation introduces one of ``/?#@:``.
   ``_origin`` runs on ``base_url`` on EVERY request, so this is on the hot path.
2. ``calculate_wait_time``'s docstring says "capped at 60 seconds". With jitter
   it returns up to 78s, and only the 429/``Retry-After`` path was bounded by
   #115 -- the 5xx and transport-error paths call it raw.
3. ``ValidationError`` hard-codes ``status_code=422``, so a purely local guard
   refusal -- no request ever sent -- reports an HTTP status and
   ``is_client_error is True``. Anything aggregating by status records a 422
   for a request that never reached the network.
"""

from unittest.mock import Mock, patch

import pytest

from oilpriceapi._url import resolve_api_url
from oilpriceapi.exceptions import OilPriceAPIError, ValidationError
from oilpriceapi.retry import RetryStrategy

BASE = "https://api.oilpriceapi.com"

# Not a credential: a fixture string, every request here is mocked.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])

# urlsplit raises ValueError on both of these.
UNPARSEABLE_BASES = [
    "https://api.oilpriceapi.com:99999",
    "https://℀evil.example",
]


# --- 1. no raw ValueError escapes the documented contract -------------------

@pytest.mark.parametrize("base", UNPARSEABLE_BASES)
def test_resolve_api_url_raises_typed_error_not_valueerror(base):
    with pytest.raises(OilPriceAPIError):
        resolve_api_url(base, "/v1/prices")


@pytest.mark.parametrize("base", UNPARSEABLE_BASES)
def test_resolve_api_url_never_leaks_bare_valueerror(base):
    """A bare ValueError is exactly what the docstring says cannot happen."""
    try:
        resolve_api_url(base, "/v1/prices")
    except OilPriceAPIError:
        pass
    except ValueError as exc:  # pragma: no cover - this is the bug
        pytest.fail(f"leaked a raw ValueError: {exc}")


@pytest.mark.parametrize("path", ["/v1/prices:99999", "/v1/℀prices"])
def test_unusual_paths_against_a_sane_base_still_resolve(path):
    """The fix must not start refusing ordinary paths."""
    assert resolve_api_url(BASE, path).startswith(BASE)


# --- 2. the documented 60s cap is a real cap --------------------------------

def test_calculate_wait_time_never_exceeds_the_documented_cap():
    s = RetryStrategy(max_retries=20)
    # 2**10 = 1024 -> base 60 -> +30% jitter = up to 78s today.
    worst = max(s.calculate_wait_time(10) for _ in range(2000))
    assert worst <= RetryStrategy.MAX_WAIT_SECONDS, worst


@pytest.mark.parametrize("attempt", range(0, 14))
def test_calculate_wait_time_is_bounded_at_every_attempt(attempt):
    s = RetryStrategy(max_retries=20)
    for _ in range(100):
        w = s.calculate_wait_time(attempt)
        assert 0.0 <= w <= RetryStrategy.MAX_WAIT_SECONDS, (attempt, w)


def test_calculate_wait_time_keeps_jitter_below_the_cap():
    """Bounding must not collapse jitter into a constant and re-create the
    thundering herd the jitter exists to prevent."""
    s = RetryStrategy(max_retries=20)
    small = {round(s.calculate_wait_time(1), 6) for _ in range(200)}
    assert len(small) > 1, "jitter disappeared at an unsaturated attempt"


def test_calculate_wait_time_without_jitter_is_unchanged():
    s = RetryStrategy(max_retries=20, jitter=False)
    assert s.calculate_wait_time(0) == 1
    assert s.calculate_wait_time(2) == 4
    assert s.calculate_wait_time(10) == RetryStrategy.MAX_WAIT_SECONDS


def test_docstring_cap_matches_the_constant():
    doc = RetryStrategy.calculate_wait_time.__doc__ or ""
    assert str(int(RetryStrategy.MAX_WAIT_SECONDS)) in doc


# --- 3. a local refusal carries no HTTP status ------------------------------

def test_local_guard_refusal_has_no_http_status():
    """No request was sent, so there is no status code to report."""
    with pytest.raises(ValidationError) as exc:
        resolve_api_url(BASE, "//evil.example/v1/prices")
    assert exc.value.status_code is None


def test_local_guard_refusal_is_not_a_client_http_error():
    with pytest.raises(ValidationError) as exc:
        resolve_api_url(BASE, "//evil.example/v1/prices")
    assert exc.value.is_client_error is False


def test_server_sent_validation_error_keeps_422():
    """A real 422 from the API must still report 422."""
    err = ValidationError("bad field", field="code", status_code=422)
    assert err.status_code == 422
    assert err.is_client_error is True


def test_validation_error_default_is_still_422_for_existing_callers():
    """Back-compat: callers that construct it bare still get the HTTP default."""
    assert ValidationError("bad").status_code == 422


# --- 4. sync and async must not diverge -------------------------------------

def _server_error():
    """A 503 the retry strategy will keep retrying."""
    response = Mock()
    response.status_code = 503
    response.headers = {}
    response.json.return_value = {"error": "unavailable"}
    response.text = "unavailable"
    return response


@patch("httpx.Client.request")
def test_sync_client_never_sleeps_past_the_cap_on_5xx(mock_request, monkeypatch):
    """The 5xx path, which #115 left unbounded, on the real transport."""
    from oilpriceapi import OilPriceAPI

    mock_request.return_value = _server_error()
    sleeps = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))

    c = OilPriceAPI(api_key=FIXTURE_KEY, base_url=BASE, max_retries=14)
    with pytest.raises(Exception):
        c.request("GET", "/v1/prices/latest")

    assert sleeps, "no retry happened; the test proves nothing"
    assert max(sleeps) <= RetryStrategy.MAX_WAIT_SECONDS, max(sleeps)


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request")
async def test_async_client_never_sleeps_past_the_cap_on_5xx(mock_request, monkeypatch):
    """Parity: identical assertion against the async client's 5xx path."""
    import asyncio

    from oilpriceapi import AsyncOilPriceAPI

    mock_request.return_value = _server_error()
    sleeps = []

    async def fake_sleep(s):
        sleeps.append(s)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    c = AsyncOilPriceAPI(api_key=FIXTURE_KEY, base_url=BASE, max_retries=14)
    with pytest.raises(Exception):
        await c.request("GET", "/v1/prices/latest")

    assert sleeps, "no retry happened; the test proves nothing"
    assert max(sleeps) <= RetryStrategy.MAX_WAIT_SECONDS, max(sleeps)


def test_both_clients_have_the_same_number_of_wait_call_sites_per_method():
    """Structural pin: neither client may grow an unbounded wait the other
    lacks. Both route every wait through the one bounded calculate_wait_time."""
    import inspect

    from oilpriceapi import async_client, client

    sync_src = inspect.getsource(client)
    async_src = inspect.getsource(async_client)
    # Every wait in both clients comes from the shared, now-bounded strategy.
    assert "calculate_wait_time" in sync_src
    assert "calculate_wait_time" in async_src
    for src, name in ((sync_src, "client"), (async_src, "async_client")):
        assert "2 **" not in src, f"{name} computes its own backoff"
        assert "random.uniform" not in src, f"{name} adds its own jitter"
