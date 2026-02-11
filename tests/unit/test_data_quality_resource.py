"""
Unit tests for DataQualityResource
"""

import pytest
from unittest.mock import Mock, patch
from oilpriceapi import OilPriceAPI


class TestDataQualityResource:
    """Test suite for DataQualityResource"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return OilPriceAPI(api_key="test_key")

    def test_summary(self, client):
        """Test getting data quality summary"""
        mock_summary = {
            "overall_quality": "high",
            "score": 95.5,
            "last_updated": "2025-12-15T10:00:00Z"
        }

        with patch.object(client, 'request', return_value={"data": mock_summary}):
            summary = client.data_quality.summary()

            assert summary["score"] == 95.5

    def test_reports(self, client):
        """Test getting all data quality reports"""
        mock_reports = [
            {"code": "BRENT_CRUDE_USD", "quality_score": 98},
            {"code": "WTI_USD", "quality_score": 97}
        ]

        with patch.object(client, 'request', return_value={"data": mock_reports}):
            reports = client.data_quality.reports()

            assert len(reports) == 2

    def test_report(self, client):
        """Test getting data quality report for a commodity"""
        mock_report = {
            "code": "BRENT_CRUDE_USD",
            "quality_score": 98,
            "last_updated": "2025-12-15T09:00:00Z"
        }

        with patch.object(client, 'request', return_value={"data": mock_report}):
            report = client.data_quality.report("BRENT_CRUDE_USD")

            assert report["quality_score"] == 98
