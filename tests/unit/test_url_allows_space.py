"""The origin guard must reject control characters, not SPACE (#119).

`_FORBIDDEN_CHARS` used `range(0x21)`, which is 0x00-0x20 INCLUSIVE, so
U+0020 SPACE was forbidden. The comment above it names CR/LF request splitting
and NUL as the threat -- all below 0x20. The range over-reached by exactly one
character, and any caller building a query string inline in the path got a hard
failure where the request previously worked: httpx percent-encodes a space, so
nothing the guard exists to stop is enabled by allowing it.

The SDK does this to itself in `resources/demo.py`
(`path = f"{path}?codes={','.join(codes)}"`).
"""

import pytest

from oilpriceapi._url import resolve_api_url
from oilpriceapi.exceptions import ValidationError

BASE = "https://api.oilpriceapi.com"


@pytest.mark.parametrize(
    "path,expected",
    [
        (
            "/v1/prices?name=Brent Crude",
            "https://api.oilpriceapi.com/v1/prices?name=Brent Crude",
        ),
        (
            "/v1/demo/prices?codes=BRENT_CRUDE_USD,WTI USD",
            "https://api.oilpriceapi.com/v1/demo/prices?codes=BRENT_CRUDE_USD,WTI USD",
        ),
        (
            "/v1/commodities/Brent Crude/summary",
            "https://api.oilpriceapi.com/v1/commodities/Brent Crude/summary",
        ),
    ],
)
def test_space_is_allowed_and_stays_on_origin(path, expected):
    assert resolve_api_url(BASE, path) == expected


@pytest.mark.parametrize(
    "char",
    [
        "\x00",  # NUL
        "\t",  # 0x09
        "\n",  # CR/LF request splitting
        "\r",
        "\x1f",  # last control char below SPACE
        "\x7f",  # DEL
    ],
)
def test_control_characters_are_still_refused(char):
    with pytest.raises(ValidationError):
        resolve_api_url(BASE, f"/v1/prices{char}Host: fixture.invalid")


def test_crlf_header_injection_is_still_refused():
    with pytest.raises(ValidationError):
        resolve_api_url(BASE, "/v1/prices\r\nX-Injected: 1")


def test_backslash_is_still_refused():
    with pytest.raises(ValidationError):
        resolve_api_url(BASE, "/\\fixture.invalid/v1/prices")


def test_a_space_cannot_introduce_an_authority():
    """Belt and braces: space plus an off-origin form is still refused."""
    for path in ("// fixture.invalid/v1/prices", "https://fixture.invalid/v1 prices"):
        with pytest.raises(ValidationError):
            resolve_api_url(BASE, path)


def test_the_sdks_own_demo_path_shape_resolves():
    """demo.py builds this exact shape; a code with a space must not raise."""
    codes = ["BRENT_CRUDE_USD", "Brent Crude"]
    path = f"/v1/demo/prices?codes={','.join(codes)}"

    assert resolve_api_url(BASE, path).startswith(BASE)
