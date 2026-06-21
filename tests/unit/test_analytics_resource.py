"""
Unit tests for AnalyticsResource.

These assert both response parsing AND the exact wire parameters sent to the
API. The wire-param assertions guard against the param-mismatch bug class fixed
in the Node SDK: the v1 analytics controller reads ``code`` / ``code1`` /
``code2`` / ``period`` (not ``commodity`` / ``commodity1`` / ``commodity2`` /
``days``), so a wrong key is silently ignored server-side.
"""

from unittest.mock import patch

import pytest

from oilpriceapi import OilPriceAPI


class TestAnalyticsResource:
    """Test suite for AnalyticsResource"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return OilPriceAPI(api_key="test_key")

    def test_performance(self, client):
        """performance() maps days -> range and parses the data envelope."""
        mock_perf = {"return_pct": 5.2, "volatility": 12.5, "trend": "bullish"}

        with patch.object(client, "request", return_value={"data": mock_perf}) as req:
            perf = client.analytics.performance(days=30)

            assert perf["return_pct"] == 5.2
            _, kwargs = req.call_args
            assert kwargs["path"] == "/v1/analytics/performance"
            # Controller reads params[:range], not commodity/days.
            assert kwargs["params"] == {"range": "30d"}

    def test_statistics_sends_code_and_period(self, client):
        """statistics() sends code/period (not commodity/days)."""
        mock_stats = {"mean": 75.50, "std_dev": 3.25, "min": 70.00, "max": 82.00}

        with patch.object(client, "request", return_value={"data": mock_stats}) as req:
            stats = client.analytics.statistics("WTI_USD", days=90)

            assert stats["mean"] == 75.50
            _, kwargs = req.call_args
            assert kwargs["params"] == {"code": "WTI_USD", "period": 90}

    def test_correlation_sends_code1_code2_period(self, client):
        """correlation() sends code1/code2/period (the Node SDK bug class)."""
        mock_corr = {"correlation": 0.95, "p_value": 0.0001}

        with patch.object(client, "request", return_value={"data": mock_corr}) as req:
            corr = client.analytics.correlation("BRENT_CRUDE_USD", "WTI_USD", days=90)

            assert corr["correlation"] == 0.95
            _, kwargs = req.call_args
            params = kwargs["params"]
            assert params == {"code1": "BRENT_CRUDE_USD", "code2": "WTI_USD", "period": 90}
            # Regression guard: the old/Node bug used these keys.
            assert "commodity1" not in params
            assert "commodity2" not in params
            assert "days" not in params

    def test_trend_sends_code_and_period(self, client):
        """trend() sends code/period."""
        mock_trend = {"direction": "up", "strength": "strong", "momentum": 0.8}

        with patch.object(client, "request", return_value={"data": mock_trend}) as req:
            trend = client.analytics.trend("NATURAL_GAS_USD", days=30)

            assert trend["direction"] == "up"
            _, kwargs = req.call_args
            assert kwargs["params"] == {"code": "NATURAL_GAS_USD", "period": 30}

    def test_spread_sends_named_spread_and_period(self, client):
        """spread() operates on a named spread, sent as spread/period."""
        mock_spread = {"current": 2.50, "average": 2.20, "percentile": 75}

        with patch.object(client, "request", return_value={"data": mock_spread}) as req:
            spread = client.analytics.spread("wti_brent")

            assert spread["current"] == 2.50
            _, kwargs = req.call_args
            assert kwargs["params"] == {"spread": "wti_brent", "period": 30}

    def test_forecast_sends_code_method_period(self, client):
        """forecast() sends code/method/period."""
        mock_forecast = {
            "7_day": {"price": 76.00},
            "30_day": {"price": 77.50},
            "confidence": 0.85,
        }

        with patch.object(client, "request", return_value={"data": mock_forecast}) as req:
            forecast = client.analytics.forecast("BRENT_CRUDE_USD")

            assert forecast["7_day"]["price"] == 76.00
            _, kwargs = req.call_args
            assert kwargs["params"] == {
                "code": "BRENT_CRUDE_USD",
                "method": "ema",
                "period": 90,
            }
