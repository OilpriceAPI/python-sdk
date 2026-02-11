"""
Unit tests for DrillingIntelligenceResource
"""

import pytest
from unittest.mock import Mock, patch
from oilpriceapi import OilPriceAPI


class TestDrillingIntelligenceResource:
    """Test suite for DrillingIntelligenceResource"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return OilPriceAPI(api_key="test_key")

    def test_list(self, client):
        """Test listing drilling activity"""
        mock_list = [
            {"id": "drill_1", "operator": "ExxonMobil"}
        ]

        with patch.object(client, 'request', return_value={"data": mock_list}):
            result = client.drilling.list()

            assert len(result) == 1

    def test_latest(self, client):
        """Test getting latest drilling data"""
        mock_latest = {
            "total_active": 500,
            "oil_directed": 400,
            "gas_directed": 100
        }

        with patch.object(client, 'request', return_value={"data": mock_latest}):
            latest = client.drilling.latest()

            assert latest["total_active"] == 500

    def test_summary(self, client):
        """Test getting drilling summary"""
        mock_summary = {
            "total_wells": 1000,
            "active_wells": 500
        }

        with patch.object(client, 'request', return_value={"data": mock_summary}):
            summary = client.drilling.summary()

            assert summary["total_wells"] == 1000

    def test_trends(self, client):
        """Test getting drilling trends"""
        mock_trends = [
            {"period": "2025-01", "wells": 50}
        ]

        with patch.object(client, 'request', return_value={"data": mock_trends}):
            trends = client.drilling.trends()

            assert len(trends) == 1

    def test_frac_spreads(self, client):
        """Test getting frac spread data"""
        mock_spreads = [
            {"region": "Permian", "spreads": 100}
        ]

        with patch.object(client, 'request', return_value={"data": mock_spreads}):
            spreads = client.drilling.frac_spreads()

            assert len(spreads) == 1

    def test_well_permits(self, client):
        """Test getting well permits"""
        mock_permits = [
            {"id": "perm_1", "operator": "ExxonMobil"}
        ]

        with patch.object(client, 'request', return_value={"data": mock_permits}):
            permits = client.drilling.well_permits()

            assert len(permits) == 1

    def test_duc_wells(self, client):
        """Test getting DUC well counts"""
        mock_ducs = [
            {"region": "Permian", "count": 2000}
        ]

        with patch.object(client, 'request', return_value={"data": mock_ducs}):
            ducs = client.drilling.duc_wells()

            assert len(ducs) == 1

    def test_completions(self, client):
        """Test getting well completions"""
        mock_completions = [
            {"id": "comp_1", "well_name": "Well #1"}
        ]

        with patch.object(client, 'request', return_value={"data": mock_completions}):
            completions = client.drilling.completions()

            assert len(completions) == 1

    def test_wells_drilled(self, client):
        """Test getting wells drilled"""
        mock_drilled = [
            {"period": "2025-01", "count": 100}
        ]

        with patch.object(client, 'request', return_value={"data": mock_drilled}):
            drilled = client.drilling.wells_drilled()

            assert len(drilled) == 1
