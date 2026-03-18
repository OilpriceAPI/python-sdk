"""
Unit tests for prices resource.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from oilpriceapi import OilPriceAPI
from oilpriceapi.models import Price
from oilpriceapi.exceptions import DataNotFoundError


class TestPricesResource:
    """Test PricesResource class."""

    @patch('httpx.Client.request')
    def test_get_single_price(self, mock_request, api_key, mock_price_response):
        """Test getting a single commodity price."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_price_response
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        price = client.prices.get("BRENT_CRUDE_USD")

        assert isinstance(price, Price)
        assert price.commodity == "BRENT_CRUDE_USD"
        assert price.value == 75.50
        assert price.currency == "USD"

        # Verify request was made correctly
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["method"] == "GET"
        assert "by_code" in call_kwargs["params"]
        assert call_kwargs["params"]["by_code"] == "BRENT_CRUDE_USD"

    @patch('httpx.Client.request')
    def test_get_multiple_prices(self, mock_request, api_key, mock_price_response):
        """Test getting multiple commodity prices."""
        # Mock responses for each commodity
        responses = [
            Mock(
                status_code=200,
                json=lambda: {
                    "status": "success",
                    "data": {
                        "code": "BRENT_CRUDE_USD",
                        "price": 75.50,
                        "currency": "USD",
                        "created_at": "2024-01-15T10:00:00Z",
                        "type": "spot_price",
                    }
                }
            ),
            Mock(
                status_code=200,
                json=lambda: {
                    "status": "success",
                    "data": {
                        "code": "WTI_USD",
                        "price": 70.25,
                        "currency": "USD",
                        "created_at": "2024-01-15T10:00:00Z",
                        "type": "spot_price",
                    }
                }
            ),
        ]
        mock_request.side_effect = responses

        client = OilPriceAPI(api_key=api_key)
        prices = client.prices.get_multiple(["BRENT_CRUDE_USD", "WTI_USD"])

        assert len(prices) == 2
        assert prices[0].commodity == "BRENT_CRUDE_USD"
        assert prices[0].value == 75.50
        assert prices[1].commodity == "WTI_USD"
        assert prices[1].value == 70.25
        assert mock_request.call_count == 2

    @patch('httpx.Client.request')
    def test_get_multiple_prices_with_failures(self, mock_request, api_key):
        """Test get_multiple skips failed commodities."""
        # First succeeds, second fails, third succeeds
        responses = [
            Mock(
                status_code=200,
                json=lambda: {
                    "status": "success",
                    "data": {
                        "code": "BRENT_CRUDE_USD",
                        "price": 75.50,
                        "currency": "USD",
                        "created_at": "2024-01-15T10:00:00Z",
                        "type": "spot_price",
                    }
                }
            ),
            Mock(status_code=404, json=lambda: {"error": "Not found"}),
            Mock(
                status_code=200,
                json=lambda: {
                    "status": "success",
                    "data": {
                        "code": "NATURAL_GAS_USD",
                        "price": 3.25,
                        "currency": "USD",
                        "created_at": "2024-01-15T10:00:00Z",
                        "type": "spot_price",
                    }
                }
            ),
        ]
        mock_request.side_effect = responses

        client = OilPriceAPI(api_key=api_key)
        prices = client.prices.get_multiple([
            "BRENT_CRUDE_USD",
            "INVALID_CODE",
            "NATURAL_GAS_USD"
        ])

        # Should only return 2 prices (skips the failed one)
        assert len(prices) == 2
        assert prices[0].commodity == "BRENT_CRUDE_USD"
        assert prices[1].commodity == "NATURAL_GAS_USD"

    @patch('httpx.Client.request')
    def test_get_price_with_alternate_response_format(self, mock_request, api_key):
        """Test handling response without nested data key."""
        mock_response = Mock()
        mock_response.status_code = 200
        # Response without nested data
        mock_response.json.return_value = {
            "code": "BRENT_CRUDE_USD",
            "price": 75.50,
            "currency": "USD",
            "created_at": "2024-01-15T10:00:00Z",
            "type": "spot_price",
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        price = client.prices.get("BRENT_CRUDE_USD")

        assert price.commodity == "BRENT_CRUDE_USD"
        assert price.value == 75.50

    @patch('httpx.Client.request')
    def test_to_dataframe_current_single(self, mock_request, api_key, mock_price_response):
        """Test converting single current price to DataFrame."""
        pytest.importorskip("pandas")  # Skip if pandas not installed

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_price_response
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        df = client.prices.to_dataframe(commodity="BRENT_CRUDE_USD")

        assert df is not None
        assert len(df) == 1
        assert "commodity" in df.columns
        assert "value" in df.columns
        assert df["commodity"].iloc[0] == "BRENT_CRUDE_USD"

    @patch('httpx.Client.request')
    def test_to_dataframe_without_pandas(self, mock_request, api_key, monkeypatch):
        """Test to_dataframe raises error when pandas not available."""
        # Hide pandas
        import sys
        monkeypatch.setitem(sys.modules, 'pandas', None)

        client = OilPriceAPI(api_key=api_key)

        with pytest.raises(ImportError) as exc_info:
            client.prices.to_dataframe(commodity="BRENT_CRUDE_USD")

        assert "pandas is required" in str(exc_info.value)


class TestGetAllPagination:
    """Test get_all auto-pagination via X-Has-Next header."""

    @patch('httpx.Client.request')
    def test_get_all_single_page(self, mock_request, api_key):
        """Test get_all with a single page (X-Has-Next: false)."""
        import httpx
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                {
                    "code": "BRENT_CRUDE_USD",
                    "price": 75.50,
                    "currency": "USD",
                    "unit": "barrel",
                    "created_at": "2024-01-15T10:00:00Z",
                },
                {
                    "code": "EU_CARBON_EUR",
                    "price": 65.00,
                    "currency": "EUR",
                    "unit": "tonne",
                    "created_at": "2024-01-15T10:00:00Z",
                },
            ],
        }
        mock_response.headers = {"X-Has-Next": "false"}
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        prices = client.prices.get_all()

        assert len(prices) == 2
        assert mock_request.call_count == 1

    @patch('httpx.Client.request')
    def test_get_all_multi_page(self, mock_request, api_key):
        """Test get_all fetches all pages when X-Has-Next is true."""
        import httpx

        def make_response(data, has_next):
            r = Mock(spec=httpx.Response)
            r.status_code = 200
            r.json.return_value = {"status": "success", "data": data}
            r.headers = {"X-Has-Next": "true" if has_next else "false"}
            return r

        page1_data = [
            {
                "code": "BRENT_CRUDE_USD",
                "price": 75.50,
                "currency": "USD",
                "unit": "barrel",
                "created_at": "2024-01-15T10:00:00Z",
            }
        ]
        page2_data = [
            {
                "code": "WTI_USD",
                "price": 70.25,
                "currency": "USD",
                "unit": "barrel",
                "created_at": "2024-01-15T10:00:00Z",
            }
        ]

        mock_request.side_effect = [
            make_response(page1_data, has_next=True),
            make_response(page2_data, has_next=False),
        ]

        client = OilPriceAPI(api_key=api_key)
        prices = client.prices.get_all(per_page=1)

        assert len(prices) == 2
        assert mock_request.call_count == 2
        assert prices[0].commodity == "BRENT_CRUDE_USD"
        assert prices[1].commodity == "WTI_USD"

    @patch('httpx.Client.request')
    def test_get_all_preserves_currency(self, mock_request, api_key):
        """Bug 1: get_all must preserve each record's currency field."""
        import httpx
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                {
                    "code": "EU_CARBON_EUR",
                    "price": 65.00,
                    "currency": "EUR",
                    "unit": "tonne",
                    "created_at": "2024-01-15T10:00:00Z",
                },
                {
                    "code": "NATURAL_GAS_GBP",
                    "price": 90.00,
                    "currency": "GBP",
                    "unit": "therm",
                    "created_at": "2024-01-15T10:00:00Z",
                },
                {
                    "code": "BRENT_CRUDE_USD",
                    "price": 75.50,
                    "currency": "USD",
                    "unit": "barrel",
                    "created_at": "2024-01-15T10:00:00Z",
                },
            ],
        }
        mock_response.headers = {"X-Has-Next": "false"}
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        prices = client.prices.get_all()

        by_code = {p.commodity: p for p in prices}
        assert by_code["EU_CARBON_EUR"].currency == "EUR"
        assert by_code["NATURAL_GAS_GBP"].currency == "GBP"
        assert by_code["BRENT_CRUDE_USD"].currency == "USD"

    @patch('httpx.Client.request')
    def test_to_dataframe_currency_column(self, mock_request, api_key):
        """Bug 1: to_dataframe() currency column must reflect each commodity's currency."""
        pytest.importorskip("pandas")
        import httpx
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                {
                    "code": "EU_CARBON_EUR",
                    "price": 65.00,
                    "currency": "EUR",
                    "unit": "tonne",
                    "created_at": "2024-01-15T10:00:00Z",
                },
                {
                    "code": "BRENT_CRUDE_USD",
                    "price": 75.50,
                    "currency": "USD",
                    "unit": "barrel",
                    "created_at": "2024-01-15T10:00:00Z",
                },
            ],
        }
        mock_response.headers = {"X-Has-Next": "false"}
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        df = client.prices.to_dataframe()

        assert "currency" in df.columns
        currencies = dict(zip(df["commodity"], df["currency"]))
        assert currencies["EU_CARBON_EUR"] == "EUR"
        assert currencies["BRENT_CRUDE_USD"] == "USD"

    @patch('httpx.Client.request')
    def test_to_dataframe_per_page_parameter(self, mock_request, api_key):
        """Bug 2: to_dataframe() per_page parameter is forwarded to get_all."""
        pytest.importorskip("pandas")
        import httpx
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                {
                    "code": "BRENT_CRUDE_USD",
                    "price": 75.50,
                    "currency": "USD",
                    "unit": "barrel",
                    "created_at": "2024-01-15T10:00:00Z",
                }
            ],
        }
        mock_response.headers = {"X-Has-Next": "false"}
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        df = client.prices.to_dataframe(per_page=50)

        # Verify per_page was included in the request params
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["params"]["per_page"] == 50


class TestPricesResourceErrorHandling:
    """Test error handling in prices resource."""

    @patch('httpx.Client.request')
    def test_get_price_not_found(self, mock_request, api_key, mock_404_response):
        """Test handling commodity not found."""
        mock_request.return_value = mock_404_response

        client = OilPriceAPI(api_key=api_key)

        with pytest.raises(DataNotFoundError) as exc_info:
            client.prices.get("INVALID_CODE")

        error = exc_info.value
        assert error.status_code == 404
        assert "not found" in str(error).lower()

    @patch('httpx.Client.request')
    def test_get_price_handles_missing_fields(self, mock_request, api_key):
        """Test handling response with missing optional fields."""
        mock_response = Mock()
        mock_response.status_code = 200
        # Minimal response
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "code": "TEST",
                "price": 100.0,
                "created_at": "2024-01-15T10:00:00Z",
            }
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        price = client.prices.get("TEST")

        assert price.commodity == "TEST"
        assert price.value == 100.0
        # Should have defaults for missing fields
        assert price.currency == "USD"
        assert price.unit == "barrel"