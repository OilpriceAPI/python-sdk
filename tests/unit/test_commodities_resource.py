"""
Unit tests for CommoditiesResource
"""

import pytest
from unittest.mock import Mock, patch
from oilpriceapi import OilPriceAPI


class TestCommoditiesResource:
    """Test suite for CommoditiesResource"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return OilPriceAPI(api_key="test_key")

    @pytest.fixture
    def mock_commodity(self):
        """Create a mock commodity"""
        return {
            "code": "BRENT_CRUDE_USD",
            "name": "Brent Crude Oil",
            "category": "Crude Oil",
            "unit": "barrel",
            "currency": "USD",
            "description": "North Sea Brent crude oil benchmark",
            "source": "ICE",
            "active": True
        }

    def test_list_commodities(self, client, mock_commodity):
        """Test listing all commodities"""
        mock_commodities = [
            mock_commodity,
            {
                "code": "WTI_USD",
                "name": "WTI Crude Oil",
                "category": "Crude Oil",
                "unit": "barrel",
                "currency": "USD"
            }
        ]

        with patch.object(client, 'request', return_value={"data": mock_commodities}):
            commodities = client.commodities.list()

            assert len(commodities) == 2
            assert commodities[0]["code"] == "BRENT_CRUDE_USD"
            assert commodities[1]["code"] == "WTI_USD"

    def test_list_commodities_direct_response(self, client, mock_commodity):
        """Test listing commodities with direct array response"""
        mock_commodities = [mock_commodity]

        with patch.object(client, 'request', return_value=mock_commodities):
            commodities = client.commodities.list()

            assert len(commodities) == 1
            assert commodities[0]["code"] == "BRENT_CRUDE_USD"

    def test_get_commodity(self, client, mock_commodity):
        """Test getting a specific commodity"""
        with patch.object(client, 'request', return_value={"data": mock_commodity}):
            commodity = client.commodities.get("BRENT_CRUDE_USD")

            assert commodity["code"] == "BRENT_CRUDE_USD"
            assert commodity["name"] == "Brent Crude Oil"
            assert commodity["category"] == "Crude Oil"

    def test_get_commodity_direct_response(self, client, mock_commodity):
        """Test getting commodity with direct object response"""
        with patch.object(client, 'request', return_value=mock_commodity):
            commodity = client.commodities.get("BRENT_CRUDE_USD")

            assert commodity["code"] == "BRENT_CRUDE_USD"

    def test_categories(self, client, mock_commodity):
        """Test getting commodities grouped by category"""
        mock_categories = {
            "Crude Oil": [
                mock_commodity,
                {"code": "WTI_USD", "name": "WTI Crude Oil"}
            ],
            "Natural Gas": [
                {"code": "NATURAL_GAS_USD", "name": "Natural Gas"}
            ]
        }

        with patch.object(client, 'request', return_value={"data": mock_categories}):
            categories = client.commodities.categories()

            assert "Crude Oil" in categories
            assert "Natural Gas" in categories
            assert len(categories["Crude Oil"]) == 2
            assert len(categories["Natural Gas"]) == 1

    def test_categories_direct_response(self, client):
        """Test getting categories with direct object response"""
        mock_categories = {
            "Crude Oil": [{"code": "BRENT_CRUDE_USD"}]
        }

        with patch.object(client, 'request', return_value=mock_categories):
            categories = client.commodities.categories()

            assert "Crude Oil" in categories
