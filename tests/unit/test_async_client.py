"""
Unit tests for async client.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime

from oilpriceapi import AsyncOilPriceAPI
from oilpriceapi.models import Price, HistoricalPrice, HistoricalResponse
from oilpriceapi.exceptions import (
    ConfigurationError,
    AuthenticationError,
    RateLimitError,
    DataNotFoundError,
)


class TestAsyncClientInitialization:
    """Test AsyncOilPriceAPI initialization."""

    def test_init_with_api_key(self, api_key):
        """Test async client initialization with API key."""
        client = AsyncOilPriceAPI(api_key=api_key)
        assert client.api_key == api_key
        assert client.base_url == "https://api.oilpriceapi.com"
        assert client.timeout == 30
        assert client.max_retries == 3

    def test_init_from_environment(self, monkeypatch, api_key):
        """Test initialization from environment variable."""
        monkeypatch.setenv("OILPRICEAPI_KEY", api_key)
        client = AsyncOilPriceAPI()
        assert client.api_key == api_key

    def test_init_without_api_key(self, monkeypatch):
        """Test initialization fails without API key."""
        monkeypatch.delenv("OILPRICEAPI_KEY", raising=False)
        with pytest.raises(ConfigurationError):
            AsyncOilPriceAPI()

    def test_custom_configuration(self, api_key):
        """Test custom configuration."""
        client = AsyncOilPriceAPI(
            api_key=api_key,
            base_url="https://custom.api.com",
            timeout=60,
            max_retries=5,
        )
        assert client.base_url == "https://custom.api.com"
        assert client.timeout == 60
        assert client.max_retries == 5

    @pytest.mark.asyncio
    async def test_context_manager(self, api_key):
        """Test async context manager."""
        async with AsyncOilPriceAPI(api_key=api_key) as client:
            assert client.api_key == api_key
            assert client._client is not None


class TestAsyncPricesResource:
    """Test async prices resource."""

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.request')
    async def test_get_price(self, mock_request, api_key, mock_price_response):
        """Test getting a single price async."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value=mock_price_response)
        mock_request.return_value = mock_response

        async with AsyncOilPriceAPI(api_key=api_key) as client:
            price = await client.prices.get("BRENT_CRUDE_USD")

            assert isinstance(price, Price)
            assert price.commodity == "BRENT_CRUDE_USD"
            assert price.value == 75.50

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.request')
    async def test_get_multiple_prices_concurrently(self, mock_request, api_key):
        """Test getting multiple prices concurrently."""
        # Mock different responses for each commodity
        async def make_response(code, price_value):
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value={
                "status": "success",
                "data": {
                    "code": code,
                    "price": price_value,
                    "currency": "USD",
                    "created_at": "2024-01-15T10:00:00Z",
                    "type": "spot_price",
                }
            })
            return mock_response

        # Return different responses for each call
        mock_request.side_effect = [
            await make_response("BRENT_CRUDE_USD", 75.50),
            await make_response("WTI_USD", 70.25),
            await make_response("NATURAL_GAS_USD", 3.25),
        ]

        async with AsyncOilPriceAPI(api_key=api_key) as client:
            # Get prices concurrently
            prices = await asyncio.gather(
                client.prices.get("BRENT_CRUDE_USD"),
                client.prices.get("WTI_USD"),
                client.prices.get("NATURAL_GAS_USD"),
            )

            assert len(prices) == 3
            assert prices[0].value == 75.50
            assert prices[1].value == 70.25
            assert prices[2].value == 3.25


class TestAsyncHistoricalResource:
    """Test async historical resource."""

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.request')
    async def test_get_historical_data(self, mock_request, api_key, mock_historical_response):
        """Test getting historical data async."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value=mock_historical_response)
        mock_request.return_value = mock_response

        async with AsyncOilPriceAPI(api_key=api_key) as client:
            history = await client.historical.get(
                commodity="BRENT_CRUDE_USD",
                start_date="2024-01-01",
                end_date="2024-01-03",
            )

            assert isinstance(history, HistoricalResponse)
            assert len(history.data) == 3
            assert all(isinstance(p, HistoricalPrice) for p in history.data)

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.request')
    async def test_get_all_historical(self, mock_request, api_key):
        """Test get_all with automatic pagination."""
        # Mock two pages
        page1_response = AsyncMock()
        page1_response.status_code = 200
        page1_response.json = AsyncMock(return_value={
            "status": "success",
            "data": {
                "prices": [
                    {
                        "code": "BRENT_CRUDE_USD",
                        "price": 75.0 + (i * 0.01),
                        "currency": "USD",
                        "created_at": "2024-01-15T10:00:00Z",
                        "type": "spot_price",
                        "unit": "barrel",
                    }
                    for i in range(1000)
                ]
            },
            "meta": {
                "page": 1,
                "per_page": 1000,
                "total": 1500,
                "total_pages": 2,
                "has_next": True,
                "has_prev": False,
            }
        })

        page2_response = AsyncMock()
        page2_response.status_code = 200
        page2_response.json = AsyncMock(return_value={
            "status": "success",
            "data": {
                "prices": [
                    {
                        "code": "BRENT_CRUDE_USD",
                        "price": 75.0 + (i * 0.01),
                        "currency": "USD",
                        "created_at": "2024-02-15T10:00:00Z",
                        "type": "spot_price",
                        "unit": "barrel",
                    }
                    for i in range(500)
                ]
            },
            "meta": {
                "page": 2,
                "per_page": 1000,
                "total": 1500,
                "total_pages": 2,
                "has_next": False,
                "has_prev": True,
            }
        })

        mock_request.side_effect = [page1_response, page2_response]

        async with AsyncOilPriceAPI(api_key=api_key) as client:
            all_prices = await client.historical.get_all(
                commodity="BRENT_CRUDE_USD",
                start_date="2024-01-01",
            )

            assert len(all_prices) == 1500
            assert mock_request.call_count == 2


class TestAsyncErrorHandling:
    """Test async error handling."""

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.request')
    async def test_authentication_error(self, mock_request, api_key):
        """Test authentication error handling."""
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.json = AsyncMock(return_value={"error": "Invalid API key"})
        mock_request.return_value = mock_response

        async with AsyncOilPriceAPI(api_key=api_key) as client:
            with pytest.raises(AuthenticationError):
                await client.prices.get("BRENT_CRUDE_USD")

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.request')
    async def test_rate_limit_error(self, mock_request, api_key):
        """Test rate limit error handling."""
        mock_response = AsyncMock()
        mock_response.status_code = 429
        mock_response.headers = {
            "X-RateLimit-Limit": "1000",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1705320000",
        }
        mock_response.json = AsyncMock(return_value={"error": "Rate limit exceeded"})
        mock_request.return_value = mock_response

        async with AsyncOilPriceAPI(api_key=api_key) as client:
            with pytest.raises(RateLimitError) as exc_info:
                await client.prices.get("BRENT_CRUDE_USD")

            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.request')
    async def test_data_not_found_error(self, mock_request, api_key):
        """Test data not found error."""
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.json = AsyncMock(return_value={
            "error": "Commodity not found",
            "commodity": "INVALID_CODE",
        })
        mock_request.return_value = mock_response

        async with AsyncOilPriceAPI(api_key=api_key) as client:
            with pytest.raises(DataNotFoundError):
                await client.prices.get("INVALID_CODE")

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.request')
    async def test_retry_on_server_error(self, mock_request, api_key):
        """Test retry logic on server errors."""
        # First two calls fail, third succeeds
        fail_response1 = AsyncMock()
        fail_response1.status_code = 500
        fail_response1.json = AsyncMock(return_value={"error": "Server error"})

        fail_response2 = AsyncMock()
        fail_response2.status_code = 502
        fail_response2.json = AsyncMock(return_value={"error": "Bad gateway"})

        success_response = AsyncMock()
        success_response.status_code = 200
        success_response.json = AsyncMock(return_value={
            "status": "success",
            "data": {
                "code": "BRENT_CRUDE_USD",
                "price": 75.50,
                "currency": "USD",
                "created_at": "2024-01-15T10:00:00Z",
                "type": "spot_price",
            }
        })

        mock_request.side_effect = [fail_response1, fail_response2, success_response]

        async with AsyncOilPriceAPI(api_key=api_key, max_retries=3) as client:
            # Patch sleep to avoid waiting in tests
            with patch('asyncio.sleep', new_callable=AsyncMock):
                price = await client.prices.get("BRENT_CRUDE_USD")

            assert price.value == 75.50
            assert mock_request.call_count == 3


class TestAsyncConcurrency:
    """Test async concurrent operations."""

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.request')
    async def test_concurrent_historical_requests(self, mock_request, api_key, mock_historical_response):
        """Test multiple concurrent historical data requests."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value=mock_historical_response)
        mock_request.return_value = mock_response

        async with AsyncOilPriceAPI(api_key=api_key) as client:
            # Fetch data for multiple commodities concurrently
            results = await asyncio.gather(
                client.historical.get("BRENT_CRUDE_USD", start_date="2024-01-01"),
                client.historical.get("WTI_USD", start_date="2024-01-01"),
                client.historical.get("NATURAL_GAS_USD", start_date="2024-01-01"),
            )

            assert len(results) == 3
            assert all(isinstance(r, HistoricalResponse) for r in results)
            assert mock_request.call_count == 3

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.request')
    async def test_mixed_operations_concurrent(self, mock_request, api_key, mock_price_response, mock_historical_response):
        """Test mixing current price and historical requests."""
        # Alternate responses for different request types
        async def make_response(is_historical):
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            if is_historical:
                mock_resp.json = AsyncMock(return_value=mock_historical_response)
            else:
                mock_resp.json = AsyncMock(return_value=mock_price_response)
            return mock_resp

        mock_request.side_effect = [
            await make_response(False),  # Current price
            await make_response(True),   # Historical
            await make_response(False),  # Current price
        ]

        async with AsyncOilPriceAPI(api_key=api_key) as client:
            current1, history, current2 = await asyncio.gather(
                client.prices.get("BRENT_CRUDE_USD"),
                client.historical.get("WTI_USD", start_date="2024-01-01"),
                client.prices.get("NATURAL_GAS_USD"),
            )

            assert isinstance(current1, Price)
            assert isinstance(history, HistoricalResponse)
            assert isinstance(current2, Price)