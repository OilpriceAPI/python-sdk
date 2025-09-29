"""
Shared test fixtures and configuration for pytest.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock
import httpx


@pytest.fixture
def api_key():
    """Test API key."""
    return "test_api_key_12345"


@pytest.fixture
def base_url():
    """Test base URL."""
    return "https://api.oilpriceapi.com"


@pytest.fixture
def mock_price_response():
    """Mock successful price response."""
    return {
        "status": "success",
        "data": {
            "code": "BRENT_CRUDE_USD",
            "price": 75.50,
            "currency": "USD",
            "created_at": "2024-01-15T10:00:00Z",
            "type": "spot_price",
        }
    }


@pytest.fixture
def mock_historical_response():
    """Mock successful historical response."""
    return {
        "status": "success",
        "data": {
            "prices": [
                {
                    "code": "BRENT_CRUDE_USD",
                    "price": 75.50,
                    "currency": "USD",
                    "created_at": "2024-01-01T10:00:00Z",
                    "type": "spot_price",
                    "unit": "barrel",
                },
                {
                    "code": "BRENT_CRUDE_USD",
                    "price": 76.25,
                    "currency": "USD",
                    "created_at": "2024-01-02T10:00:00Z",
                    "type": "spot_price",
                    "unit": "barrel",
                },
                {
                    "code": "BRENT_CRUDE_USD",
                    "price": 74.80,
                    "currency": "USD",
                    "created_at": "2024-01-03T10:00:00Z",
                    "type": "spot_price",
                    "unit": "barrel",
                },
            ]
        }
    }


@pytest.fixture
def mock_http_response():
    """Create a mock HTTP response."""
    def _make_response(status_code=200, json_data=None, headers=None):
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = status_code
        mock_response.json.return_value = json_data or {}
        mock_response.headers = headers or {}
        mock_response.text = str(json_data)
        return mock_response
    return _make_response


@pytest.fixture
def mock_401_response(mock_http_response):
    """Mock 401 authentication error response."""
    return mock_http_response(
        status_code=401,
        json_data={"error": "Invalid API key or authentication failed"}
    )


@pytest.fixture
def mock_404_response(mock_http_response):
    """Mock 404 not found response."""
    return mock_http_response(
        status_code=404,
        json_data={"error": "Resource not found", "commodity": "INVALID_CODE"}
    )


@pytest.fixture
def mock_429_response(mock_http_response):
    """Mock 429 rate limit response."""
    return mock_http_response(
        status_code=429,
        json_data={"error": "Rate limit exceeded"},
        headers={
            "X-RateLimit-Limit": "1000",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1705320000",
        }
    )


@pytest.fixture
def mock_500_response(mock_http_response):
    """Mock 500 server error response."""
    return mock_http_response(
        status_code=500,
        json_data={"error": "Internal server error"}
    )


@pytest.fixture
def sample_price_data():
    """Sample price data for testing."""
    return {
        "commodity": "BRENT_CRUDE_USD",
        "value": 75.50,
        "currency": "USD",
        "unit": "barrel",
        "timestamp": datetime(2024, 1, 15, 10, 0, 0),
        "change": 1.25,
        "change_percent": 1.68,
        "previous_close": 74.25,
        "open": 74.50,
        "high": 76.00,
        "low": 74.00,
    }


@pytest.fixture
def sample_historical_price_data():
    """Sample historical price data."""
    return {
        "created_at": "2024-01-01T10:00:00Z",
        "commodity_name": "BRENT_CRUDE_USD",
        "price": 75.50,
        "unit_of_measure": "barrel",
        "type_name": "spot_price",
    }


@pytest.fixture(autouse=True)
def reset_environment(monkeypatch):
    """Reset environment variables before each test."""
    monkeypatch.delenv("OILPRICEAPI_KEY", raising=False)
    monkeypatch.delenv("OILPRICEAPI_BASE_URL", raising=False)