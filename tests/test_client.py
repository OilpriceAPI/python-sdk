"""
Tests for OilPriceAPI client.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx
from datetime import datetime

from oilpriceapi import OilPriceAPI
from oilpriceapi.exceptions import (
    ConfigurationError,
    AuthenticationError,
    RateLimitError,
    DataNotFoundError,
    ServerError,
)
from oilpriceapi.models import Price


class TestOilPriceAPIClient:
    """Test OilPriceAPI client initialization and configuration."""
    
    def test_init_with_api_key(self):
        """Test client initialization with API key."""
        client = OilPriceAPI(api_key="test_key_123")
        assert client.api_key == "test_key_123"
        assert client.base_url == "https://api.oilpriceapi.com"
        assert client.timeout == 30
        assert client.max_retries == 3
    
    def test_init_from_environment(self, monkeypatch):
        """Test client initialization from environment variable."""
        monkeypatch.setenv("OILPRICEAPI_KEY", "env_key_456")
        client = OilPriceAPI()
        assert client.api_key == "env_key_456"
    
    def test_init_without_api_key(self, monkeypatch):
        """Test client initialization fails without API key."""
        monkeypatch.delenv("OILPRICEAPI_KEY", raising=False)
        with pytest.raises(ConfigurationError) as exc_info:
            OilPriceAPI()
        assert "API key required" in str(exc_info.value)
    
    def test_custom_configuration(self):
        """Test client with custom configuration."""
        client = OilPriceAPI(
            api_key="test_key",
            base_url="https://custom.api.com",
            timeout=60,
            max_retries=5,
        )
        assert client.base_url == "https://custom.api.com"
        assert client.timeout == 60
        assert client.max_retries == 5
    
    def test_headers_configuration(self):
        """Test headers are properly configured."""
        client = OilPriceAPI(api_key="test_key")
        assert client.headers["Authorization"] == "Token test_key"
        assert client.headers["Content-Type"] == "application/json"
        assert "User-Agent" in client.headers
    
    def test_context_manager(self):
        """Test client works as context manager."""
        with OilPriceAPI(api_key="test_key") as client:
            assert client.api_key == "test_key"
            assert client._client is not None


class TestPricesResource:
    """Test prices resource methods."""
    
    @patch('httpx.Client.request')
    def test_get_price(self, mock_request):
        """Test getting a single price."""
        # Mock response - API returns code, price, created_at fields
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "code": "BRENT_CRUDE_USD",
                "price": 75.50,
                "currency": "USD",
                "created_at": "2024-01-15T10:00:00Z",
                "type": "spot_price",
            }
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key="test_key")
        price = client.prices.get("BRENT_CRUDE_USD")

        assert isinstance(price, Price)
        assert price.commodity == "BRENT_CRUDE_USD"
        assert price.value == 75.50
        assert price.currency == "USD"

        # Check request was made correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args.kwargs["method"] == "GET"
    
    @patch('httpx.Client.request')
    def test_get_multiple_prices(self, mock_request):
        """Test getting multiple prices."""
        # Create separate responses for each commodity
        def create_response(code, price_value):
            response = Mock()
            response.status_code = 200
            response.json.return_value = {
                "status": "success",
                "data": {
                    "code": code,
                    "price": price_value,
                    "currency": "USD",
                    "created_at": "2024-01-15T10:00:00Z",
                    "type": "spot_price",
                }
            }
            return response

        # Set up side_effect to return different responses
        mock_request.side_effect = [
            create_response("BRENT_CRUDE_USD", 75.50),
            create_response("WTI_USD", 70.25),
        ]

        client = OilPriceAPI(api_key="test_key")
        prices = client.prices.get_multiple(["BRENT_CRUDE_USD", "WTI_USD"])

        assert len(prices) == 2
        assert prices[0].commodity == "BRENT_CRUDE_USD"
        assert prices[0].value == 75.50
        assert prices[1].commodity == "WTI_USD"
        assert prices[1].value == 70.25


class TestErrorHandling:
    """Test error handling."""
    
    @patch('httpx.Client.request')
    def test_authentication_error(self, mock_request):
        """Test authentication error handling."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid API key"}
        mock_request.return_value = mock_response
        
        client = OilPriceAPI(api_key="invalid_key")
        with pytest.raises(AuthenticationError) as exc_info:
            client.prices.get("BRENT_CRUDE_USD")
        assert "Invalid API key" in str(exc_info.value)
    
    @patch('httpx.Client.request')
    def test_rate_limit_error(self, mock_request):
        """Test rate limit error handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {
            "X-RateLimit-Limit": "1000",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1705320000",
        }
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        mock_request.return_value = mock_response
        
        client = OilPriceAPI(api_key="test_key")
        with pytest.raises(RateLimitError) as exc_info:
            client.prices.get("BRENT_CRUDE_USD")
        
        error = exc_info.value
        assert error.status_code == 429
        assert error.limit == "1000"
        assert error.remaining == "0"
    
    @patch('httpx.Client.request')
    def test_data_not_found_error(self, mock_request):
        """Test data not found error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "error": "Commodity not found",
            "commodity": "INVALID_CODE",
        }
        mock_request.return_value = mock_response
        
        client = OilPriceAPI(api_key="test_key")
        with pytest.raises(DataNotFoundError) as exc_info:
            client.prices.get("INVALID_CODE")
        
        error = exc_info.value
        assert error.status_code == 404
        assert "not found" in str(error).lower()
    
    @patch('httpx.Client.request')
    def test_server_error_with_retry(self, mock_request):
        """Test server error with retry logic."""
        # First two calls fail, third succeeds
        fail_response1 = Mock()
        fail_response1.status_code = 500
        fail_response1.json.return_value = {"error": "Server error"}

        fail_response2 = Mock()
        fail_response2.status_code = 502
        fail_response2.json.return_value = {"error": "Bad gateway"}

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "status": "success",
            "data": {
                "code": "BRENT_CRUDE_USD",
                "price": 75.50,
                "currency": "USD",
                "created_at": "2024-01-15T10:00:00Z",
                "type": "spot_price",
            }
        }

        mock_request.side_effect = [fail_response1, fail_response2, success_response]

        # Use fast retry for testing
        client = OilPriceAPI(api_key="test_key", max_retries=3)

        with patch('time.sleep'):  # Skip sleep in tests
            price = client.prices.get("BRENT_CRUDE_USD")

        assert price.value == 75.50
        assert mock_request.call_count == 3


class TestModels:
    """Test data models."""
    
    def test_price_model(self):
        """Test Price model."""
        price = Price(
            commodity="BRENT_CRUDE_USD",
            value=75.50,
            currency="USD",
            unit="barrel",
            timestamp="2024-01-15T10:00:00Z",
            change=1.25,
            change_percentage=1.68,
        )
        
        assert price.commodity == "BRENT_CRUDE_USD"
        assert price.value == 75.50
        assert price.is_up is True
        assert price.is_down is False
        assert "↑" in str(price)  # Up arrow
        assert "1.68%" in str(price)
    
    def test_price_model_with_negative_change(self):
        """Test Price model with negative change."""
        price = Price(
            commodity="WTI_USD",
            value=70.25,
            currency="USD",
            unit="barrel",
            timestamp="2024-01-15T10:00:00Z",
            change=-0.75,
            change_percentage=-1.06,
        )
        
        assert price.is_up is False
        assert price.is_down is True
        assert "↓" in str(price)  # Down arrow
    
    def test_timestamp_parsing(self):
        """Test timestamp parsing in various formats."""
        # ISO format with Z
        price1 = Price(
            commodity="TEST",
            value=100,
            currency="USD",
            unit="unit",
            timestamp="2024-01-15T10:00:00Z",
        )
        assert isinstance(price1.timestamp, datetime)
        
        # ISO format with timezone
        price2 = Price(
            commodity="TEST",
            value=100,
            currency="USD",
            unit="unit",
            timestamp="2024-01-15T10:00:00+00:00",
        )
        assert isinstance(price2.timestamp, datetime)
