"""
Unit tests for StorageResource
"""

import pytest
from unittest.mock import Mock, patch
from oilpriceapi import OilPriceAPI


class TestStorageResource:
    """Test suite for StorageResource"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return OilPriceAPI(api_key="test_key")

    def test_all(self, client):
        """Test getting all storage levels"""
        mock_storage = {
            "crude_oil": 150000000,
            "gasoline": 50000000,
            "distillate": 30000000
        }

        with patch.object(client, 'request', return_value={"data": mock_storage}):
            storage = client.storage.all()

            assert storage["crude_oil"] == 150000000

    def test_cushing(self, client):
        """Test getting Cushing storage levels"""
        mock_cushing = {"crude_oil": 50000000}

        with patch.object(client, 'request', return_value={"data": mock_cushing}):
            cushing = client.storage.cushing()

            assert cushing["crude_oil"] == 50000000

    def test_spr(self, client):
        """Test getting Strategic Petroleum Reserve levels"""
        mock_spr = {"crude_oil": 500000000}

        with patch.object(client, 'request', return_value={"data": mock_spr}):
            spr = client.storage.spr()

            assert spr["crude_oil"] == 500000000

    def test_regional(self, client):
        """Test getting regional storage levels"""
        mock_regional = {
            "region": "PADD3",
            "crude_oil": 200000000
        }

        with patch.object(client, 'request', return_value={"data": mock_regional}):
            regional = client.storage.regional(region="PADD3")

            assert regional["region"] == "PADD3"

    def test_regional_all(self, client):
        """Test getting all regional storage levels"""
        mock_all = {
            "PADD1": {"crude_oil": 150000000},
            "PADD2": {"crude_oil": 100000000}
        }

        with patch.object(client, 'request', return_value={"data": mock_all}):
            regional = client.storage.regional()

            assert "PADD1" in regional
