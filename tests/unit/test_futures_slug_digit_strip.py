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

import pytest

from oilpriceapi.exceptions import OilPriceAPIError
from oilpriceapi.resources._futures_slug import (
    CONTRACT_CODE_TO_SLUG,
    normalize_futures_slug,
)

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

def test_sync_futures_never_requests_a_generic_curve_for_a_dated_code():
    """End to end: a dated code must not reach the wire as the generic slug."""
    import httpx
    import respx

    from oilpriceapi import OilPriceAPI

    with respx.mock(base_url="https://api.oilpriceapi.com", assert_all_called=False) as mock:
        route = mock.get(path__startswith="/v1/futures").mock(
            return_value=httpx.Response(200, json={"data": {}})
        )
        c = OilPriceAPI(api_key="k", base_url="https://api.oilpriceapi.com")
        with pytest.raises(OilPriceAPIError):
            c.futures.curve("WTI2026")
        assert not route.called, (
            "a dated contract reached the network as a different instrument: "
            f"{[str(call.request.url) for call in route.calls]}"
        )


@pytest.mark.asyncio
async def test_async_futures_never_requests_a_generic_curve_for_a_dated_code():
    """Parity: the async client must refuse exactly what the sync one refuses."""
    import httpx
    import respx

    from oilpriceapi import AsyncOilPriceAPI

    with respx.mock(base_url="https://api.oilpriceapi.com", assert_all_called=False) as mock:
        route = mock.get(path__startswith="/v1/futures").mock(
            return_value=httpx.Response(200, json={"data": {}})
        )
        c = AsyncOilPriceAPI(api_key="k", base_url="https://api.oilpriceapi.com")
        with pytest.raises(OilPriceAPIError):
            await c.futures.curve("WTI2026")
        assert not route.called, (
            "a dated contract reached the network as a different instrument: "
            f"{[str(call.request.url) for call in route.calls]}"
        )


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
