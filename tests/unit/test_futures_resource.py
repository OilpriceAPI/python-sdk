"""
Unit tests for FuturesResource
"""

import pytest
from unittest.mock import Mock, patch
from datetime import date, datetime
from oilpriceapi import OilPriceAPI


class TestFuturesResource:
    """Test suite for FuturesResource"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return OilPriceAPI(api_key="test_key")

    def test_latest(self, client):
        """Test getting latest futures price"""
        mock_price = {"contract": "CL.1", "price": 75.50, "timestamp": "2025-12-15T10:00:00Z"}

        with patch.object(client, 'request', return_value={"data": mock_price}):
            price = client.futures.latest("CL.1")

            assert price["contract"] == "CL.1"
            assert price["price"] == 75.50

    def test_historical(self, client):
        """Test getting historical futures prices"""
        mock_history = [
            {"date": "2024-01-01", "price": 70.00},
            {"date": "2024-01-02", "price": 71.00}
        ]

        with patch.object(client, 'request', return_value={"data": mock_history}):
            history = client.futures.historical("CL.1", start_date="2024-01-01", end_date="2024-01-02")

            assert len(history) == 2
            assert history[0]["price"] == 70.00

    def test_historical_with_date_objects(self, client):
        """Test historical with date objects"""
        mock_history = [{"date": "2024-01-01", "price": 70.00}]

        with patch.object(client, 'request', return_value={"data": mock_history}) as mock_req:
            start = date(2024, 1, 1)
            end = datetime(2024, 1, 31, 23, 59, 59)

            history = client.futures.historical("CL.1", start_date=start, end_date=end)

            call_args = mock_req.call_args
            assert call_args[1]["params"]["start_date"] == "2024-01-01"
            assert call_args[1]["params"]["end_date"] == "2024-01-31"

    def test_ohlc(self, client):
        """Test getting OHLC data"""
        mock_ohlc = {
            "open": 75.00,
            "high": 76.00,
            "low": 74.50,
            "close": 75.50,
            "volume": 100000
        }

        with patch.object(client, 'request', return_value={"data": mock_ohlc}):
            ohlc = client.futures.ohlc("CL.1")

            assert ohlc["open"] == 75.00
            assert ohlc["close"] == 75.50

    def test_intraday(self, client):
        """Test getting intraday prices"""
        mock_intraday = [
            {"time": "09:00", "price": 75.00},
            {"time": "10:00", "price": 75.25}
        ]

        with patch.object(client, 'request', return_value={"data": mock_intraday}):
            intraday = client.futures.intraday("CL.1")

            assert len(intraday) == 2

    def test_spreads(self, client):
        """Test getting spread analysis"""
        mock_spread = {
            "contract1": "CL.1",
            "contract2": "CL.2",
            "current_spread": 0.50,
            "average_spread": 0.45
        }

        with patch.object(client, 'request', return_value={"data": mock_spread}):
            spread = client.futures.spreads("CL.1", "CL.2")

            assert spread["current_spread"] == 0.50

    def test_curve(self, client):
        """Test getting futures curve"""
        mock_curve = [
            {"month": "2024-01", "price": 75.00},
            {"month": "2024-02", "price": 74.50}
        ]

        with patch.object(client, 'request', return_value={"data": mock_curve}):
            curve = client.futures.curve("CL")

            assert len(curve) == 2

    def test_continuous(self, client):
        """Test getting continuous futures prices"""
        mock_continuous = [{"date": "2024-01-01", "price": 75.00}]

        with patch.object(client, 'request', return_value={"data": mock_continuous}):
            continuous = client.futures.continuous("CL", months=24)

            assert len(continuous) == 1

    def test_format_date_string(self, client):
        """Test date formatting with string"""
        result = client.futures._format_date("2024-01-01")
        assert result == "2024-01-01"

    def test_format_date_object(self, client):
        """Test date formatting with date object"""
        result = client.futures._format_date(date(2024, 1, 1))
        assert result == "2024-01-01"

    def test_format_date_datetime(self, client):
        """Test date formatting with datetime object"""
        result = client.futures._format_date(datetime(2024, 1, 1, 12, 0, 0))
        assert result == "2024-01-01"

    def test_format_date_invalid(self, client):
        """Test date formatting with invalid type"""
        with pytest.raises(ValueError) as exc:
            client.futures._format_date(12345)

        assert "Invalid date type" in str(exc.value)
