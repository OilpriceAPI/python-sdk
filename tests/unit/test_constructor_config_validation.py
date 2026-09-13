"""The constructor must honour what the caller actually asked for (#120, #121).

#115 replaced two of the three `or` defaults and left the third -- on the line
directly above its own fix, in both clients:

    self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")   # unchanged
    self.timeout  = timeout or self.DEFAULT_TIMEOUT                   # unchanged
    self.max_retries = (... if max_retries is None else ...)          # fixed
    self.retry_on = (... if retry_on is None else ...)                # fixed

`timeout=0` is meaningful to httpx (fail immediately rather than wait) and is
what `float(os.getenv("OPA_TIMEOUT", "0"))` produces. Silently getting a
30-second timeout instead, and then a hang nobody can attribute back to the
constructor, is the same defect #115 set out to remove.

#121 is the other direction: #115's new validation started REJECTING
`max_retries=0` and `max_retries=3.0` at construction, values that worked in
1.13.0, with no version bump and no changelog. The validation is right -- 0
silently becoming 3 was the bug -- but taking a process down at startup is not
the way to deliver it inside a patch series.
"""

import warnings

import pytest

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI
from oilpriceapi.exceptions import ConfigurationError

# Not a credential: a fixture string, no request is made in this module.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])

CLIENTS = [pytest.param(OilPriceAPI, id="sync"), pytest.param(AsyncOilPriceAPI, id="async")]


# ---------------------------------------------------------------------------
# (a) timeout


@pytest.mark.parametrize("client_class", CLIENTS)
def test_explicit_zero_timeout_is_honoured(client_class):
    assert client_class(api_key=FIXTURE_KEY, timeout=0).timeout == 0


@pytest.mark.parametrize("client_class", CLIENTS)
def test_explicit_small_timeout_is_honoured(client_class):
    assert client_class(api_key=FIXTURE_KEY, timeout=0.001).timeout == 0.001


@pytest.mark.parametrize("client_class", CLIENTS)
def test_omitted_timeout_still_defaults(client_class):
    assert client_class(api_key=FIXTURE_KEY).timeout == 30
    assert client_class(api_key=FIXTURE_KEY, timeout=None).timeout == 30


@pytest.mark.parametrize("client_class", CLIENTS)
@pytest.mark.parametrize("bad", [-1, -0.5])
def test_negative_timeout_fails_loudly(client_class, bad):
    """It used to be passed straight down to httpx unvalidated."""
    with pytest.raises(ConfigurationError):
        client_class(api_key=FIXTURE_KEY, timeout=bad)


@pytest.mark.parametrize("client_class", CLIENTS)
@pytest.mark.parametrize("bad", ["30", None.__class__, object()])
def test_non_numeric_timeout_fails_loudly(client_class, bad):
    with pytest.raises(ConfigurationError):
        client_class(api_key=FIXTURE_KEY, timeout=bad)


def test_sync_and_async_agree_on_timeout():
    for value in (0, 0.5, 30, None):
        assert (
            OilPriceAPI(api_key=FIXTURE_KEY, timeout=value).timeout
            == AsyncOilPriceAPI(api_key=FIXTURE_KEY, timeout=value).timeout
        )


# ---------------------------------------------------------------------------
# (b) base_url


@pytest.mark.parametrize("client_class", CLIENTS)
def test_empty_base_url_is_not_silently_production(client_class):
    """Pointing at production when the caller asked for "" is the worst answer."""
    with pytest.raises(ConfigurationError):
        client_class(api_key=FIXTURE_KEY, base_url="")


@pytest.mark.parametrize("client_class", CLIENTS)
def test_explicit_base_url_is_preserved(client_class):
    client = client_class(api_key=FIXTURE_KEY, base_url="https://staging.fixture.invalid/")
    assert client.base_url == "https://staging.fixture.invalid"


@pytest.mark.parametrize("client_class", CLIENTS)
def test_omitted_base_url_still_defaults(client_class):
    assert client_class(api_key=FIXTURE_KEY).base_url == "https://api.oilpriceapi.com"
    assert client_class(api_key=FIXTURE_KEY, base_url=None).base_url == "https://api.oilpriceapi.com"


# ---------------------------------------------------------------------------
# (c) max_retries: keep the meaning, drop the startup crash


@pytest.mark.parametrize("client_class", CLIENTS)
def test_zero_max_retries_no_longer_crashes_at_construction(client_class):
    """1.13.0 accepted it. A patch upgrade must not take the process down."""
    with pytest.warns(DeprecationWarning, match="total ATTEMPTS"):
        client = client_class(api_key=FIXTURE_KEY, max_retries=0)

    assert client.max_retries == 1, "0 means 'do not retry', which is one attempt"


@pytest.mark.parametrize("client_class", CLIENTS)
def test_integral_float_max_retries_is_coerced(client_class):
    """What a JSON/YAML config round-trip produces for an integer."""
    with pytest.warns(DeprecationWarning):
        client = client_class(api_key=FIXTURE_KEY, max_retries=3.0)

    assert client.max_retries == 3


@pytest.mark.parametrize("client_class", CLIENTS)
def test_zero_max_retries_really_sends_one_attempt(client_class):
    """The warning must not be cosmetic: 0 must not quietly go back to 3."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        client = client_class(api_key=FIXTURE_KEY, max_retries=0)

    assert client._retry_strategy.max_retries == 1
    assert client._retry_strategy.should_retry(0, 503, method="GET") is False


@pytest.mark.parametrize("client_class", CLIENTS)
@pytest.mark.parametrize("bad", [-1, -5])
def test_negative_max_retries_still_fails_loudly(client_class, bad):
    with pytest.raises(ConfigurationError):
        client_class(api_key=FIXTURE_KEY, max_retries=bad)


@pytest.mark.parametrize("client_class", CLIENTS)
@pytest.mark.parametrize("bad", ["3", 2.5, True])
def test_non_integral_max_retries_still_fails_loudly(client_class, bad):
    """A bool is a typo hazard and 2.5 attempts is not a thing."""
    with pytest.raises(ConfigurationError):
        client_class(api_key=FIXTURE_KEY, max_retries=bad)


@pytest.mark.parametrize("client_class", CLIENTS)
def test_valid_max_retries_warns_about_nothing(client_class):
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert client_class(api_key=FIXTURE_KEY, max_retries=5).max_retries == 5


# ---------------------------------------------------------------------------
# (d) the breaking change is announced


def test_version_was_bumped_past_the_release_that_broke_it():
    from oilpriceapi.version import __version__

    assert __version__ != "1.13.0", (
        "max_retries=0 and timeout=0 behave differently from 1.13.0; that needs "
        "a version the caller can pin against"
    )


def test_changelog_documents_the_change():
    import pathlib

    import oilpriceapi

    changelog = pathlib.Path(oilpriceapi.__file__).resolve().parent.parent / "CHANGELOG.md"
    text = changelog.read_text()

    assert "max_retries" in text
    assert "timeout" in text
