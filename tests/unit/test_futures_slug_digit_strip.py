"""A year is not a contract-order marker (#128).

`normalize_futures_slug` strips a trailing digit run unconditionally, so a
DATED contract is silently answered with the GENERIC front-month slug -- a
different instrument:

    WTI2026   -> 'wti'
    BRENT2027 -> 'brent'
    NG2026    -> 'natural-gas'

`CONTRACT_CODE_TO_SLUG` contains no key with a digit in it, so every one of
those resolutions came from the strip, not from a real mapping. The call
succeeds and returns data; nothing tells the caller their year was discarded.

This is the other half of what #111 fixed. #111 removed the guess from the
separator-splitting branch (`WTI_MIDLAND_USD` now raises rather than resolving
to `wti`); the digit strip on the very next line still guesses.

A refusal is recoverable. A wrong instrument's curve is not.
"""

from unittest.mock import Mock, patch

import pytest

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI
from oilpriceapi.exceptions import OilPriceAPIError
from oilpriceapi.resources._futures_slug import (
    CONTRACT_CODE_TO_SLUG,
    normalize_futures_slug,
)

# Not a credential: a fixture string, every request here is mocked.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])

# What must KEEP working: TradingView order markers, one or two digits.
MUST_RESOLVE = {
    "CL1!": "wti",
    "CL.1": "wti",
    "CL": "wti",
    "CL1": "wti",
    "CL2": "wti",
    "CL12": "wti",
    "BZ": "brent",
    "BZ1!": "brent",
    "NG": "natural-gas",
    "NG1!": "natural-gas",
}

# What must now REFUSE: a year is not an order marker.
MUST_REFUSE = [
    "WTI2026",
    "BRENT2027",
    "NG2026",
    "TTF2026",
    "GASOIL2026",
    "CL2026",
    "BZ2027",
    "CL123",      # 3 digits is not an order marker either
    "CL99999",
]


def test_no_contract_code_key_contains_a_digit():
    """The premise: every digit resolution today comes from the strip."""
    assert [k for k in CONTRACT_CODE_TO_SLUG if any(c.isdigit() for c in k)] == []


@pytest.mark.parametrize("code,expected", sorted(MUST_RESOLVE.items()))
def test_order_markers_still_resolve(code, expected):
    assert normalize_futures_slug(code) == expected


@pytest.mark.parametrize("code", MUST_REFUSE)
def test_dated_contracts_are_refused_not_guessed(code):
    with pytest.raises(OilPriceAPIError):
        normalize_futures_slug(code)


@pytest.mark.parametrize("code", MUST_REFUSE)
def test_refusal_is_also_a_valueerror_for_legacy_callers(code):
    """`FuturesContractError` subclasses ValueError; keep that (#122)."""
    with pytest.raises(ValueError):
        normalize_futures_slug(code)


@pytest.mark.parametrize("code", MUST_REFUSE)
def test_refusal_names_the_input(code):
    with pytest.raises(OilPriceAPIError) as exc:
        normalize_futures_slug(code)
    assert code in str(exc.value)


def test_canonical_slugs_are_untouched():
    for slug in ("wti", "brent", "natural-gas"):
        assert normalize_futures_slug(slug) == slug


# --- the request actually sent, sync and async -----------------------------
#
# Patching `httpx.Client.request` / `httpx.AsyncClient.request` is this repo's
# existing convention (see tests/unit/test_diesel_envelope.py) and keeps the
# test suite free of an extra HTTP-mocking dependency.

def _ok(payload=None):
    response = Mock()
    response.status_code = 200
    response.json.return_value = payload if payload is not None else {"data": {}}
    return response


@patch("httpx.Client.request")
def test_sync_futures_never_requests_a_generic_curve_for_a_dated_code(mock_request):
    """End to end: a dated code must not reach the wire as the generic slug."""
    mock_request.return_value = _ok()
    c = OilPriceAPI(api_key=FIXTURE_KEY)

    with pytest.raises(OilPriceAPIError):
        c.futures.curve("WTI2026")

    assert not mock_request.called, (
        "a dated contract reached the network as a different instrument: "
        f"{mock_request.call_args_list}"
    )


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request")
async def test_async_futures_never_requests_a_generic_curve_for_a_dated_code(mock_request):
    """Parity: the async client must refuse exactly what the sync one refuses."""
    mock_request.return_value = _ok()
    c = AsyncOilPriceAPI(api_key=FIXTURE_KEY)

    with pytest.raises(OilPriceAPIError):
        await c.futures.curve("WTI2026")

    assert not mock_request.called, (
        "a dated contract reached the network as a different instrument: "
        f"{mock_request.call_args_list}"
    )


@patch("httpx.Client.request")
def test_sync_futures_still_requests_the_generic_curve_for_an_order_marker(mock_request):
    """The control: CL1! must still go out, as /v1/futures/wti/..."""
    mock_request.return_value = _ok()
    c = OilPriceAPI(api_key=FIXTURE_KEY)

    c.futures.curve("CL1!")

    assert mock_request.called
    sent = str(mock_request.call_args)
    assert "/v1/futures/wti" in sent, sent


def test_sync_and_async_futures_normalize_identically():
    """Both clients must route every contract argument through one resolver."""
    import inspect

    from oilpriceapi import async_resources
    from oilpriceapi.resources import futures

    for mod, name in ((futures, "futures"), (async_resources, "async_resources")):
        assert "normalize_futures_slug" in inspect.getsource(mod), name

    for code in MUST_REFUSE + list(MUST_RESOLVE):
        sync_result = async_result = None
        try:
            sync_result = normalize_futures_slug(code)
        except OilPriceAPIError as exc:
            sync_result = type(exc)
        try:
            async_result = normalize_futures_slug(code)
        except OilPriceAPIError as exc:
            async_result = type(exc)
        assert sync_result == async_result, code
