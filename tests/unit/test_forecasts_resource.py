"""
Unit tests for ForecastsResource
"""

import pytest
from unittest.mock import Mock, patch
from oilpriceapi import OilPriceAPI


class TestForecastsResource:
    """Test suite for ForecastsResource"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return OilPriceAPI(api_key="test_key")

    def test_monthly(self, client):
        """Test getting monthly forecast"""
        mock_forecast = {
            "period": "2025-01",
            "forecasts": [
                {"commodity": "BRENT_CRUDE_USD", "price": 76.00}
            ]
        }

        with patch.object(client, 'request', return_value={"data": mock_forecast}):
            forecast = client.forecasts.monthly("BRENT_CRUDE_USD")

            assert forecast["period"] == "2025-01"

    def test_accuracy(self, client):
        """Test getting forecast accuracy"""
        mock_accuracy = {
            "avg_error_pct": 5.2,
            "mae": 3.50,
            "rmse": 4.25
        }

        with patch.object(client, 'request', return_value={"data": mock_accuracy}):
            accuracy = client.forecasts.accuracy()

            assert accuracy["avg_error_pct"] == 5.2

    def test_archive(self, client):
        """Test getting forecast archive"""
        mock_archive = [
            {"period": "2024-12", "forecast": 75.00, "actual": 74.50}
        ]

        with patch.object(client, 'request', return_value={"data": mock_archive}):
            archive = client.forecasts.archive(year=2024)

            assert len(archive) == 1

    def test_get(self, client):
        """Test getting specific period forecast"""
        mock_forecast = {
            "period": "2025-01",
            "commodity": "BRENT_CRUDE_USD",
            "price": 76.00
        }

        with patch.object(client, 'request', return_value={"data": mock_forecast}):
            forecast = client.forecasts.get("2025-01", "BRENT_CRUDE_USD")

            assert forecast["period"] == "2025-01"
