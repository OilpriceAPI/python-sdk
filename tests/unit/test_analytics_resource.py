"""
Unit tests for AnalyticsResource
"""

import pytest
from unittest.mock import Mock, patch
from oilpriceapi import OilPriceAPI


class TestAnalyticsResource:
    """Test suite for AnalyticsResource"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return OilPriceAPI(api_key="test_key")

    def test_performance(self, client):
        """Test getting price performance analysis"""
        mock_perf = {
            "return_pct": 5.2,
            "volatility": 12.5,
            "trend": "bullish"
        }

        with patch.object(client, 'request', return_value={"data": mock_perf}):
            perf = client.analytics.performance("BRENT_CRUDE_USD", days=30)

            assert perf["return_pct"] == 5.2

    def test_statistics(self, client):
        """Test getting statistical analysis"""
        mock_stats = {
            "mean": 75.50,
            "std_dev": 3.25,
            "min": 70.00,
            "max": 82.00
        }

        with patch.object(client, 'request', return_value={"data": mock_stats}):
            stats = client.analytics.statistics("WTI_USD", days=90)

            assert stats["mean"] == 75.50

    def test_correlation(self, client):
        """Test getting correlation analysis"""
        mock_corr = {
            "correlation": 0.95,
            "p_value": 0.0001
        }

        with patch.object(client, 'request', return_value={"data": mock_corr}):
            corr = client.analytics.correlation("BRENT_CRUDE_USD", "WTI_USD", days=90)

            assert corr["correlation"] == 0.95

    def test_trend(self, client):
        """Test getting trend analysis"""
        mock_trend = {
            "direction": "up",
            "strength": "strong",
            "momentum": 0.8
        }

        with patch.object(client, 'request', return_value={"data": mock_trend}):
            trend = client.analytics.trend("NATURAL_GAS_USD", days=30)

            assert trend["direction"] == "up"

    def test_spread(self, client):
        """Test getting spread analysis"""
        mock_spread = {
            "current": 2.50,
            "average": 2.20,
            "percentile": 75
        }

        with patch.object(client, 'request', return_value={"data": mock_spread}):
            spread = client.analytics.spread("BRENT_CRUDE_USD", "WTI_USD")

            assert spread["current"] == 2.50

    def test_forecast(self, client):
        """Test getting price forecast"""
        mock_forecast = {
            "7_day": {"price": 76.00},
            "30_day": {"price": 77.50},
            "confidence": 0.85
        }

        with patch.object(client, 'request', return_value={"data": mock_forecast}):
            forecast = client.analytics.forecast("BRENT_CRUDE_USD")

            assert forecast["7_day"]["price"] == 76.00
