"""
Unit tests for historical data resource.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, date
from oilpriceapi import OilPriceAPI
from oilpriceapi.models import HistoricalPrice, HistoricalResponse, PaginationMeta


class TestHistoricalResource:
    """Test HistoricalResource class."""

    @patch('httpx.Client.request')
    def test_get_historical_data(self, mock_request, api_key, mock_historical_response):
        """Test getting historical data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_historical_response
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        history = client.historical.get(
            commodity="BRENT_CRUDE_USD",
            start_date="2024-01-01",
            end_date="2024-01-03",
        )

        assert isinstance(history, HistoricalResponse)
        assert len(history.data) == 3
        assert all(isinstance(p, HistoricalPrice) for p in history.data)
        assert history.data[0].value == 75.50
        assert history.data[1].value == 76.25
        assert history.data[2].value == 74.80

    @patch('httpx.Client.request')
    def test_get_historical_with_pagination(self, mock_request, api_key):
        """Test historical data with pagination."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
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
                    }
                ]
            },
            "meta": {
                "page": 2,
                "per_page": 1,
                "total": 100,
                "total_pages": 100,
                "has_next": True,
                "has_prev": True,
            }
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        history = client.historical.get(
            commodity="BRENT_CRUDE_USD",
            page=2,
            per_page=1,
        )

        assert history.meta is not None
        assert history.meta.page == 2
        assert history.meta.total == 100
        assert history.meta.has_next is True
        assert history.meta.has_prev is True

    @patch('httpx.Client.request')
    def test_get_historical_date_formatting(self, mock_request, api_key, mock_historical_response):
        """Test date parameter formatting."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_historical_response
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)

        # Test with date objects
        start = date(2024, 1, 1)
        end = date(2024, 1, 3)
        history = client.historical.get(
            commodity="BRENT_CRUDE_USD",
            start_date=start,
            end_date=end,
        )

        # Check params were formatted correctly
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["params"]["start_date"] == "2024-01-01"
        assert call_kwargs["params"]["end_date"] == "2024-01-03"

    @patch('httpx.Client.request')
    def test_get_historical_with_datetime(self, mock_request, api_key, mock_historical_response):
        """Test with datetime objects."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_historical_response
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)

        # Test with datetime objects
        start = datetime(2024, 1, 1, 10, 0, 0)
        end = datetime(2024, 1, 3, 10, 0, 0)
        history = client.historical.get(
            commodity="BRENT_CRUDE_USD",
            start_date=start,
            end_date=end,
        )

        # Should convert to date format
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["params"]["start_date"] == "2024-01-01"

    @patch('httpx.Client.request')
    def test_get_historical_with_interval(self, mock_request, api_key, mock_historical_response):
        """Test with different intervals."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_historical_response
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)

        for interval in ["daily", "weekly", "monthly", "hourly"]:
            history = client.historical.get(
                commodity="BRENT_CRUDE_USD",
                interval=interval,
            )

            call_kwargs = mock_request.call_args.kwargs
            assert call_kwargs["params"]["interval"] == interval

    @patch('httpx.Client.request')
    def test_get_all_historical(self, mock_request, api_key):
        """Test get_all with automatic pagination."""
        # Mock two pages of data
        page1_response = Mock()
        page1_response.status_code = 200
        page1_response.json.return_value = {
            "status": "success",
            "data": {
                "prices": [
                    {
                        "code": "BRENT_CRUDE_USD",
                        "price": 75.0 + (i * 0.01),
                        "currency": "USD",
                        "created_at": "2024-01-15T10:00:00Z",  # Use fixed valid date
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
        }

        page2_response = Mock()
        page2_response.status_code = 200
        page2_response.json.return_value = {
            "status": "success",
            "data": {
                "prices": [
                    {
                        "code": "BRENT_CRUDE_USD",
                        "price": 75.0 + (i * 0.01),
                        "currency": "USD",
                        "created_at": "2024-02-15T10:00:00Z",  # Use fixed valid date
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
        }

        mock_request.side_effect = [page1_response, page2_response]

        client = OilPriceAPI(api_key=api_key)
        all_prices = client.historical.get_all(
            commodity="BRENT_CRUDE_USD",
            start_date="2024-01-01",
        )

        assert len(all_prices) == 1500
        assert mock_request.call_count == 2

    @patch('httpx.Client.request')
    def test_iter_pages(self, mock_request, api_key):
        """Test page iterator."""
        # Create mock responses for 3 pages
        responses = []
        for page in range(1, 4):
            response = Mock()
            response.status_code = 200
            response.json.return_value = {
                "status": "success",
                "data": {
                    "prices": [
                        {
                            "code": "BRENT_CRUDE_USD",
                            "price": 75.0,
                            "currency": "USD",
                            "created_at": "2024-01-01T10:00:00Z",
                            "type": "spot_price",
                            "unit": "barrel",
                        }
                    ] * 100  # 100 items per page
                },
                "meta": {
                    "page": page,
                    "per_page": 100,
                    "total": 300,
                    "total_pages": 3,
                    "has_next": page < 3,
                    "has_prev": page > 1,
                }
            }
            responses.append(response)

        mock_request.side_effect = responses

        client = OilPriceAPI(api_key=api_key)

        page_count = 0
        total_items = 0
        for page_data in client.historical.iter_pages(
            commodity="BRENT_CRUDE_USD",
            per_page=100,
        ):
            page_count += 1
            total_items += len(page_data)
            assert len(page_data) == 100

        assert page_count == 3
        assert total_items == 300

    @patch('httpx.Client.request')
    def test_to_dataframe(self, mock_request, api_key, mock_historical_response):
        """Test converting historical data to DataFrame."""
        pytest.importorskip("pandas")  # Skip if pandas not installed

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_historical_response
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        df = client.historical.to_dataframe(
            commodity="BRENT_CRUDE_USD",
            start="2024-01-01",
            end="2024-01-03",
        )

        assert df is not None
        assert len(df) == 3
        assert "value" in df.columns
        assert "commodity" in df.columns
        # Index should be date
        assert df.index.name == "date"

    @patch('httpx.Client.request')
    def test_to_dataframe_without_pandas(self, mock_request, api_key, monkeypatch):
        """Test to_dataframe raises error when pandas not available."""
        import sys
        monkeypatch.setitem(sys.modules, 'pandas', None)

        client = OilPriceAPI(api_key=api_key)

        with pytest.raises(ImportError) as exc_info:
            client.historical.to_dataframe(
                commodity="BRENT_CRUDE_USD",
                start="2024-01-01",
            )

        assert "pandas is required" in str(exc_info.value)


class TestHistoricalResourceResponseHandling:
    """Test response format handling."""

    @patch('httpx.Client.request')
    def test_handles_nested_data_format(self, mock_request, api_key):
        """Test handling nested data.prices format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
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
                    }
                ]
            }
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        history = client.historical.get(commodity="BRENT_CRUDE_USD")

        assert len(history.data) == 1
        assert history.data[0].value == 75.50

    @patch('httpx.Client.request')
    def test_handles_flat_data_format(self, mock_request, api_key):
        """Test handling flat data array format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "code": "BRENT_CRUDE_USD",
                    "price": 75.50,
                    "currency": "USD",
                    "created_at": "2024-01-01T10:00:00Z",
                    "type": "spot_price",
                    "unit": "barrel",
                }
            ]
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        history = client.historical.get(commodity="BRENT_CRUDE_USD")

        assert len(history.data) == 1

    @patch('httpx.Client.request')
    def test_handles_empty_response(self, mock_request, api_key):
        """Test handling empty data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "prices": []
            }
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        history = client.historical.get(commodity="BRENT_CRUDE_USD")

        assert len(history.data) == 0
        assert history.success is True


class TestHistoricalResourceEndpointSelection:
    """Test endpoint selection based on date range."""

    @patch('httpx.Client.request')
    def test_selects_past_day_endpoint_for_1_day_range(self, mock_request, api_key):
        """Test that 1 day range uses /v1/prices/past_day endpoint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"prices": []}
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        client.historical.get(
            commodity="WTI_USD",
            start_date="2024-12-15",
            end_date="2024-12-16",
        )

        # Verify correct endpoint was called
        call_args = mock_request.call_args
        assert "/v1/prices/past_day" in call_args.kwargs["url"]

    @patch('httpx.Client.request')
    def test_selects_past_week_endpoint_for_7_day_range(self, mock_request, api_key):
        """Test that 7 day range uses /v1/prices/past_week endpoint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"prices": []}
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        client.historical.get(
            commodity="WTI_USD",
            start_date="2024-12-09",
            end_date="2024-12-16",
        )

        # Verify correct endpoint was called
        call_args = mock_request.call_args
        assert "/v1/prices/past_week" in call_args.kwargs["url"]

    @patch('httpx.Client.request')
    def test_selects_past_month_endpoint_for_30_day_range(self, mock_request, api_key):
        """Test that 30 day range uses /v1/prices/past_month endpoint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"prices": []}
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        client.historical.get(
            commodity="WTI_USD",
            start_date="2024-11-16",
            end_date="2024-12-16",
        )

        # Verify correct endpoint was called
        call_args = mock_request.call_args
        assert "/v1/prices/past_month" in call_args.kwargs["url"]

    @patch('httpx.Client.request')
    def test_selects_past_year_endpoint_for_365_day_range(self, mock_request, api_key):
        """Test that 365 day range uses /v1/prices/past_year endpoint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"prices": []}
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        client.historical.get(
            commodity="WTI_USD",
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        # Verify correct endpoint was called
        call_args = mock_request.call_args
        assert "/v1/prices/past_year" in call_args.kwargs["url"]

    @patch('httpx.Client.request')
    def test_defaults_to_past_year_when_no_dates_provided(self, mock_request, api_key):
        """Test that no date range defaults to past_year endpoint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"prices": []}
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        client.historical.get(commodity="WTI_USD")

        # Verify past_year endpoint was used as default
        call_args = mock_request.call_args
        assert "/v1/prices/past_year" in call_args.kwargs["url"]


class TestHistoricalResourceTimeouts:
    """Test dynamic timeout handling for historical queries."""

    @patch('httpx.Client.request')
    def test_uses_30s_timeout_for_1_week_query(self, mock_request, api_key):
        """Test that 1 week query uses 30s timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"prices": []}
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        client.historical.get(
            commodity="WTI_USD",
            start_date="2024-12-09",
            end_date="2024-12-16",
        )

        # Verify timeout was set to 30s
        call_args = mock_request.call_args
        assert call_args.kwargs["timeout"] == 30

    @patch('httpx.Client.request')
    def test_uses_60s_timeout_for_1_month_query(self, mock_request, api_key):
        """Test that 1 month query uses 60s timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"prices": []}
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        client.historical.get(
            commodity="WTI_USD",
            start_date="2024-11-16",
            end_date="2024-12-16",
        )

        # Verify timeout was set to 60s
        call_args = mock_request.call_args
        assert call_args.kwargs["timeout"] == 60

    @patch('httpx.Client.request')
    def test_uses_120s_timeout_for_1_year_query(self, mock_request, api_key):
        """Test that 1 year query uses 120s timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"prices": []}
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        client.historical.get(
            commodity="WTI_USD",
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        # Verify timeout was set to 120s
        call_args = mock_request.call_args
        assert call_args.kwargs["timeout"] == 120

    @patch('httpx.Client.request')
    def test_allows_custom_timeout_override(self, mock_request, api_key):
        """Test that custom timeout can be provided."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"prices": []}
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key=api_key)
        client.historical.get(
            commodity="WTI_USD",
            start_date="2024-01-01",
            end_date="2024-12-31",
            timeout=180  # Custom 3 minute timeout
        )

        # Verify custom timeout was used
        call_args = mock_request.call_args
        assert call_args.kwargs["timeout"] == 180