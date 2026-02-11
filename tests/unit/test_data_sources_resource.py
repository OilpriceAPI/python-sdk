"""
Unit tests for DataSourcesResource
"""

import pytest
from unittest.mock import Mock, patch
from oilpriceapi import OilPriceAPI


class TestDataSourcesResource:
    """Test suite for DataSourcesResource"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return OilPriceAPI(api_key="test_key")

    def test_list_sources(self, client):
        """Test listing all data sources"""
        mock_sources = [
            {"id": "eia", "name": "U.S. Energy Information Administration"},
            {"id": "ice", "name": "Intercontinental Exchange"}
        ]

        with patch.object(client, 'request', return_value={"data": mock_sources}):
            sources = client.data_sources.list()

            assert len(sources) == 2
            assert sources[0]["id"] == "eia"

    def test_get_source(self, client):
        """Test getting a specific data source"""
        mock_source = {
            "id": "eia",
            "name": "U.S. Energy Information Administration",
            "description": "Official energy statistics",
            "update_frequency": "daily"
        }

        with patch.object(client, 'request', return_value={"data": mock_source}):
            source = client.data_sources.get("eia")

            assert source["id"] == "eia"

    def test_delete_source(self, client):
        """Test deleting a data source"""
        with patch.object(client, 'request', return_value={}):
            client.data_sources.delete("custom_source_1")

    def test_test_source(self, client):
        """Test testing a data source"""
        test_result = {
            "status": "success",
            "response_time_ms": 120
        }

        with patch.object(client, 'request', return_value={"data": test_result}):
            result = client.data_sources.test("eia")

            assert result["status"] == "success"

    def test_logs(self, client):
        """Test getting data source logs"""
        mock_logs = [
            {
                "timestamp": "2025-12-15T10:00:00Z",
                "status": "success",
                "records_fetched": 100
            }
        ]

        with patch.object(client, 'request', return_value={"data": mock_logs}):
            logs = client.data_sources.logs("eia")

            assert len(logs) == 1

    def test_health(self, client):
        """Test getting data source health"""
        mock_health = {
            "status": "healthy",
            "uptime_percent": 99.9,
            "last_check": "2025-12-15T10:00:00Z"
        }

        with patch.object(client, 'request', return_value={"data": mock_health}):
            health = client.data_sources.health("eia")

            assert health["status"] == "healthy"

    def test_rotate_credentials(self, client):
        """Test rotating data source credentials"""
        mock_result = {"status": "updated"}

        with patch.object(client, 'request', return_value={"data": mock_result}):
            result = client.data_sources.rotate_credentials(
                "custom_source_1",
                {"api_key": "new_key"}
            )

            assert result["status"] == "updated"
