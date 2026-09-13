"""A scheme-less ``base_url`` must be refused at construction (#123).

``resolve_api_url`` pins every request to the configured origin by comparing
``_origin(url) != _origin(base_url)``.  ``_origin`` derives (scheme, host, port)
from ``urlsplit``.  For a ``base_url`` with no scheme -- ``"api.oilpriceapi.com"``
-- ``urlsplit`` finds no authority, so the origin is ``("", "", 0)``; the
resolved URL is relative, so its origin is ``("", "", 0)`` too.  The comparison
is then a tautology: it compares nothing against nothing and passes everything.

That silently removes one of the two layers protecting the customer's API key.
The remaining layer -- the literal ``//`` ban -- still holds today, so this is a
defence-in-depth regression rather than a live leak, and the end state is a
confusing ``UnsupportedProtocol`` from httpx rather than a credential going
anywhere.  The fix is to require an absolute http/https base at construction so
the origin comparison always has two real origins to compare.
"""

import pytest

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI
from oilpriceapi.exceptions import ConfigurationError
from oilpriceapi.retry import validated_base_url

# Every one of these leaves ``_origin`` with nothing to compare, or names a
# transport this SDK cannot speak.
SCHEMELESS = [
    "api.oilpriceapi.com",
    "api.oilpriceapi.com/v1",
    "//api.oilpriceapi.com",
    "localhost:8000",
    "ftp://api.oilpriceapi.com",
    "file:///etc/passwd",
    "https://",
]

ABSOLUTE = [
    "https://api.oilpriceapi.com",
    "http://localhost:8000",
    "https://staging.oilpriceapi.com/v1",
    "http://127.0.0.1:3000",
]


@pytest.mark.parametrize("base", SCHEMELESS)
def test_validated_base_url_refuses_non_absolute(base):
    with pytest.raises(ConfigurationError) as exc:
        validated_base_url(base)
    assert "base_url" in str(exc.value)


@pytest.mark.parametrize("base", ABSOLUTE)
def test_validated_base_url_accepts_absolute_http(base):
    assert validated_base_url(base) == base.rstrip("/")


@pytest.mark.parametrize("base", SCHEMELESS)
def test_sync_client_refuses_non_absolute_base_url(base):
    with pytest.raises(ConfigurationError):
        OilPriceAPI(api_key="test-key", base_url=base)


@pytest.mark.parametrize("base", SCHEMELESS)
def test_async_client_refuses_non_absolute_base_url(base):
    """Parity: the async client must refuse exactly what the sync one refuses."""
    with pytest.raises(ConfigurationError):
        AsyncOilPriceAPI(api_key="test-key", base_url=base)


def test_origin_guard_is_never_a_tautology():
    """No accepted base_url may leave the origin comparison comparing nothing."""
    from oilpriceapi._url import _origin

    for base in ABSOLUTE:
        scheme, host, port = _origin(validated_base_url(base))
        assert scheme in ("http", "https"), base
        assert host, base
        assert port, base


def test_sync_and_async_share_one_base_url_validator():
    """Pin parity structurally: both clients call the same validator."""
    import inspect

    from oilpriceapi import async_client as a
    from oilpriceapi import client as s

    assert "validated_base_url" in inspect.getsource(s.OilPriceAPI.__init__)
    assert "validated_base_url" in inspect.getsource(a.AsyncOilPriceAPI.__init__)
