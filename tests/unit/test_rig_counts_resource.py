"""
Unit tests for RigCountsResource
"""

import pytest
from unittest.mock import Mock, patch
from oilpriceapi import OilPriceAPI


class TestRigCountsResource:
    """Test suite for RigCountsResource"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return OilPriceAPI(api_key="test_key")

    def test_latest(self, client):
        """Test getting latest rig counts"""
        mock_counts = {
            "oil_rigs": 450,
            "gas_rigs": 120,
            "total": 570,
            "week_ending": "2025-12-12"
        }

        with patch.object(client, 'request', return_value={"data": mock_counts}):
            counts = client.rig_counts.latest()

            assert counts["total"] == 570

    def test_current(self, client):
        """Test getting current rig counts"""
        mock_current = {
            "oil_rigs": 450,
            "gas_rigs": 120,
            "total": 570
        }

        with patch.object(client, 'request', return_value={"data": mock_current}):
            current = client.rig_counts.current()

            assert current["total"] == 570

    def test_trends(self, client):
        """Test getting rig count trends"""
        mock_trends = {
            "weekly_change": 5,
            "monthly_change": 15,
            "yearly_change": 50
        }

        with patch.object(client, 'request', return_value={"data": mock_trends}):
            trends = client.rig_counts.trends(period="monthly")

            assert trends["monthly_change"] == 15

    def test_summary(self, client):
        """Test getting rig count summary"""
        mock_summary = {
            "total_rigs": 570,
            "by_type": {"oil": 450, "gas": 120},
            "by_region": {"Permian": 200}
        }

        with patch.object(client, 'request', return_value={"data": mock_summary}):
            summary = client.rig_counts.summary()

            assert summary["total_rigs"] == 570
