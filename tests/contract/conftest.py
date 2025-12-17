"""
Shared configuration for contract tests.
"""

import os
import pytest
from pathlib import Path
from dotenv import dotenv_values
from oilpriceapi import OilPriceAPI

# Load .env file from project root
project_root = Path(__file__).parent.parent.parent
env_path = project_root / '.env'

# Read .env file
env_vars = dotenv_values(env_path)

# Get API credentials
API_KEY = env_vars.get('OILPRICEAPI_KEY')
BASE_URL = env_vars.get('OILPRICEAPI_BASE_URL', 'https://api.oilpriceapi.com')


@pytest.fixture(scope="session")
def api_key():
    """Provide API key for tests."""
    if not API_KEY:
        pytest.skip("OILPRICEAPI_KEY not found in .env file")
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
