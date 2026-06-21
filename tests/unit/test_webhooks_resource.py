"""
Unit tests for WebhooksResource
"""

from unittest.mock import patch

import pytest

from oilpriceapi import OilPriceAPI


class TestWebhooksResource:
    """Test suite for WebhooksResource"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return OilPriceAPI(api_key="test_key")

    @pytest.fixture
    def mock_webhook(self):
        """Create a mock webhook"""
        return {
            "id": "wh_123",
            "url": "https://example.com/webhook",
            "events": ["price.updated", "alert.triggered"],
            "enabled": True,
            "created_at": "2025-12-15T10:00:00Z"
        }

    def test_list_webhooks(self, client, mock_webhook):
        """Test listing all webhooks"""
        mock_webhooks = [mock_webhook]

        with patch.object(client, 'request', return_value={"data": mock_webhooks}):
            webhooks = client.webhooks.list()

            assert len(webhooks) == 1
            assert webhooks[0]["id"] == "wh_123"

    def test_get_webhook(self, client, mock_webhook):
        """Test getting a specific webhook"""
        with patch.object(client, 'request', return_value={"data": mock_webhook}):
            webhook = client.webhooks.get("wh_123")

            assert webhook["id"] == "wh_123"
            assert webhook["url"] == "https://example.com/webhook"

    def test_delete_webhook(self, client):
        """Test deleting a webhook"""
        with patch.object(client, 'request', return_value={}):
            client.webhooks.delete("wh_123")

    def test_test_webhook(self, client):
        """Test testing a webhook"""
        test_result = {
            "status": "success",
            "response_code": 200,
            "response_time_ms": 150
        }

        with patch.object(client, 'request', return_value={"data": test_result}):
            result = client.webhooks.test("wh_123")

            assert result["status"] == "success"
            assert result["response_code"] == 200

    def test_events(self, client):
        """Test getting webhook events"""
        mock_events = [
            {
                "id": "evt_1",
                "type": "price.updated",
                "timestamp": "2025-12-15T10:00:00Z"
            }
        ]

        with patch.object(client, 'request', return_value={"data": mock_events}):
            events = client.webhooks.events("wh_123")

            assert len(events) == 1
            assert events[0]["type"] == "price.updated"

    def test_create_maps_enabled_to_status(self, client):
        """create() sends `status` ("active"/"inactive"), not boolean `enabled`.

        The webhooks controller permits `status` and silently drops `enabled`.
        """
        with patch.object(client, "request", return_value={"data": {"id": "wh_1"}}) as req:
            client.webhooks.create(
                url="https://example.com/wh",
                events=["price.updated"],
                enabled=False,
            )
            _, kwargs = req.call_args
            body = kwargs["json_data"]
            assert body["status"] == "inactive"
            assert "enabled" not in body

    def test_update_maps_enabled_to_status(self, client):
        """update() maps enabled -> status."""
        with patch.object(client, "request", return_value={"data": {"id": "wh_1"}}) as req:
            client.webhooks.update("wh_1", enabled=True)
            _, kwargs = req.call_args
            body = kwargs["json_data"]
            assert body["status"] == "active"
            assert "enabled" not in body
