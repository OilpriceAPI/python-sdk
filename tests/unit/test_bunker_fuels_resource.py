"""
Unit tests for BunkerFuelsResource
"""

import pytest
from unittest.mock import Mock, patch
from oilpriceapi import OilPriceAPI


class TestBunkerFuelsResource:
    """Test suite for BunkerFuelsResource"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return OilPriceAPI(api_key="test_key")

    def test_all(self, client):
        """Test getting all bunker fuel prices"""
        mock_prices = [
            {"port": "Rotterdam", "IFO380": 450.00},
            {"port": "Singapore", "IFO380": 460.00}
        ]

        with patch.object(client, 'request', return_value={"data": mock_prices}):
            prices = client.bunker_fuels.all()

            assert len(prices) == 2

    def test_port(self, client):
        """Test getting bunker fuel prices for a port"""
        mock_port = {
            "code": "NLRTM",
            "name": "Rotterdam",
            "IFO380": 450.00,
            "VLSFO": 520.00
        }

        with patch.object(client, 'request', return_value={"data": mock_port}):
            port = client.bunker_fuels.port("NLRTM")

            assert port["IFO380"] == 450.00

    def test_compare(self, client):
        """Test comparing bunker fuel prices across ports"""
        mock_compare = {
            "ports": ["Rotterdam", "Singapore"],
            "prices": {
                "Rotterdam": {"IFO380": 450.00},
                "Singapore": {"IFO380": 460.00}
            }
        }

        with patch.object(client, 'request', return_value={"data": mock_compare}):
            compare = client.bunker_fuels.compare(["Rotterdam", "Singapore"])

            assert "Rotterdam" in compare["prices"]

    def test_spreads(self, client):
        """Test getting bunker fuel spreads"""
        mock_spreads = {
            "VLSFO_IFO380": 70.00,
            "MGO_VLSFO": 160.00
        }

        with patch.object(client, 'request', return_value={"data": mock_spreads}):
            spreads = client.bunker_fuels.spreads()

            assert spreads["VLSFO_IFO380"] == 70.00

    def test_export(self, client):
        """Test exporting bunker fuel data"""
        mock_export = [{"port": "Rotterdam"}]

        with patch.object(client, 'request', return_value=mock_export):
            export = client.bunker_fuels.export(format="json")

            assert isinstance(export, list)
