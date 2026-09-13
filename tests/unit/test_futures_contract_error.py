"""An unresolvable futures contract must raise inside the SDK's hierarchy (#122).

`normalize_futures_slug` raised a builtin `ValueError`, which is not an
`OilPriceAPIError`. That predates #111, but #111 turned 18 live catalog codes
from "resolved to a DIFFERENT instrument" into "raises" -- the right call -- so
user code shaped like

    try:
        curve = client.futures.curve(code)
    except OilPriceAPIError:
        fall_back()

went from a silently wrong answer to an uncaught crash. A refusal is only
recoverable if it is catchable through the documented base class.
"""

import pytest

from oilpriceapi import exceptions
from oilpriceapi.exceptions import OilPriceAPIError, ValidationError
from oilpriceapi.resources._futures_slug import normalize_futures_slug
from oilpriceapi.resources.futures import FuturesResource

# The catalog codes #111 moved from "wrong instrument" to "raises".
REWRITTEN_BY_111 = [
    "LNG_NW_EUROPE_EUR",
    "WTI_MIDLAND_USD",
    "BRENT_CRUDE_USD",
    "GASOIL_USD",
    "JKM_LNG_USD",
]


class _FakeClient:
    def request(self, **kwargs):  # pragma: no cover - never reached
        raise AssertionError("a refused contract must not reach the transport")


@pytest.mark.parametrize("code", REWRITTEN_BY_111)
def test_normalize_raises_inside_the_sdk_hierarchy(code):
    with pytest.raises(OilPriceAPIError):
        normalize_futures_slug(code)


@pytest.mark.parametrize("code", REWRITTEN_BY_111)
def test_it_is_a_validation_error_carrying_the_contract(code):
    with pytest.raises(exceptions.FuturesContractError) as excinfo:
        normalize_futures_slug(code)

    error = excinfo.value
    assert isinstance(error, ValidationError)
    assert error.field == "contract"
    assert error.value == code


@pytest.mark.parametrize("code", REWRITTEN_BY_111)
def test_value_error_callers_still_catch_it(code):
    """Backwards compatible: code written against the old `raise ValueError`."""
    with pytest.raises(ValueError):
        normalize_futures_slug(code)


def test_the_helpful_message_survives_str():
    """The message IS the remediation: it lists every valid slug and code."""
    with pytest.raises(exceptions.FuturesContractError) as excinfo:
        normalize_futures_slug("WTI_MIDLAND_USD")

    rendered = str(excinfo.value)
    assert "Unknown futures contract/slug 'WTI_MIDLAND_USD'" in rendered
    assert "Pass a slug (" in rendered
    assert "brent" in rendered
    assert "CL" in rendered


@pytest.mark.parametrize("method", ["latest", "curve", "intraday", "historical", "ohlc"])
def test_public_futures_methods_do_not_escape_the_base_class(method):
    resource = FuturesResource(_FakeClient())

    with pytest.raises(OilPriceAPIError):
        getattr(resource, method)("WTI_MIDLAND_USD")


@pytest.mark.parametrize("contract", ["brent", "wti", "CL", "BZ", "continuous/brent"])
def test_valid_contracts_are_untouched(contract):
    assert normalize_futures_slug(contract)
