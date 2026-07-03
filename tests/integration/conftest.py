"""
Shared configuration for integration tests.
"""

import os
import time
import pytest
from pathlib import Path
from oilpriceapi import OilPriceAPI
from oilpriceapi.exceptions import RateLimitError

try:
    from dotenv import dotenv_values
except ImportError:
    # python-dotenv is optional. The live demo contract tests need no .env /
    # API key, so don't make the whole integration suite uncollectable when it
    # isn't installed.
    def dotenv_values(_path):  # type: ignore[misc]
        return {}

# Load .env file from project root
project_root = Path(__file__).parent.parent.parent
env_path = project_root / '.env'

# Read .env file
env_vars = dotenv_values(env_path)

# Get API credentials
# Prefer .env for local dev, fall back to the environment for CI
# (weekly-health.yml sets OILPRICEAPI_KEY from the OILPRICEAPI_TEST_KEY secret).
API_KEY = env_vars.get('OILPRICEAPI_KEY') or os.environ.get('OILPRICEAPI_KEY')
BASE_URL = env_vars.get('OILPRICEAPI_BASE_URL') or os.environ.get('OILPRICEAPI_BASE_URL', 'https://api.oilpriceapi.com')

# CI shares a single 1-request/second API key across repositories, so live
# tests can collide and get HTTP 429 (RateLimitError) through no fault of the
# code under test. To keep green code green we:
#   1. Space live calls at least MIN_CALL_SPACING_SECONDS apart, and
#   2. Treat any 429 as a pytest.skip rather than a failure.
MIN_CALL_SPACING_SECONDS = 1.1
_last_live_call_at = 0.0


def _throttle_live_calls():
    """Enforce >=1.1s spacing between live API calls (1 req/sec shared key)."""
    global _last_live_call_at
    now = time.monotonic()
    elapsed = now - _last_live_call_at
    if elapsed < MIN_CALL_SPACING_SECONDS:
        time.sleep(MIN_CALL_SPACING_SECONDS - elapsed)
    _last_live_call_at = time.monotonic()


@pytest.fixture(scope="session")
def api_key():
    """Provide API key for tests."""
    if not API_KEY:
        pytest.skip("OILPRICEAPI_KEY not found in .env file or environment")
    return API_KEY


@pytest.fixture(scope="session")
def base_url():
    """Provide base URL for tests."""
    return BASE_URL


@pytest.fixture
def live_client(api_key, base_url):
    """Create a client for live API testing."""
    client = OilPriceAPI(api_key=api_key, base_url=base_url)
    yield client
    client.close()


@pytest.fixture
def live_call():
    """Run a live API call with rate-limit resilience.

    Spaces calls out (>=1.1s) and converts HTTP 429 (RateLimitError) into a
    pytest.skip so the shared 1-req/sec CI key can't red-flag green code.
    Any non-429 error is re-raised unchanged so real failures still surface.

    Usage:
        price = live_call(client.prices.get, "BRENT_CRUDE_USD")
    """
    def _call(func, *args, **kwargs):
        _throttle_live_calls()
        try:
            return func(*args, **kwargs)
        except RateLimitError:
            pytest.skip(
                "rate-limited (shared CI key) - skipping live assertion"
            )

    return _call