"""
Unit tests for AlertsResource
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from oilpriceapi import OilPriceAPI, PriceAlert, WebhookTestResponse
from oilpriceapi.exceptions import ValidationError


class TestAlertsResource:
    """Test suite for AlertsResource"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return OilPriceAPI(api_key="test_key")

    @pytest.fixture
    def mock_alert(self):
        """Create a mock price alert"""
        return {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Brent High Alert",
            "commodity_code": "BRENT_CRUDE_USD",
            "condition_operator": "greater_than",
            "condition_value": 85.00,
            "webhook_url": "https://example.com/webhook",
            "enabled": True,
            "cooldown_minutes": 60,
            "metadata": None,
            "trigger_count": 0,
            "last_triggered_at": None,
            "created_at": "2025-12-15T10:00:00Z",
            "updated_at": "2025-12-15T10:00:00Z"
        }

    def test_list_alerts(self, client, mock_alert):
        """Test listing all alerts"""
        mock_alert_2 = {
            **mock_alert,
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "name": "WTI Low Alert",
            "commodity_code": "WTI_USD",
            "condition_operator": "less_than",
            "condition_value": 70.00
        }

        with patch.object(client, 'request', return_value={"alerts": [mock_alert, mock_alert_2]}):
            alerts = client.alerts.list()

            assert len(alerts) == 2
            assert isinstance(alerts[0], PriceAlert)
            assert alerts[0].name == "Brent High Alert"
            assert alerts[1].name == "WTI Low Alert"

    def test_list_alerts_empty(self, client):
        """Test listing alerts when none exist"""
        with patch.object(client, 'request', return_value={"alerts": []}):
            alerts = client.alerts.list()

            assert alerts == []

    def test_get_alert(self, client, mock_alert):
        """Test getting a specific alert"""
        with patch.object(client, 'request', return_value={"alert": mock_alert}):
            alert = client.alerts.get("550e8400-e29b-41d4-a716-446655440000")

            assert isinstance(alert, PriceAlert)
            assert alert.id == "550e8400-e29b-41d4-a716-446655440000"
            assert alert.name == "Brent High Alert"

    def test_get_alert_invalid_id(self, client):
        """Test getting alert with invalid ID"""
        with pytest.raises(ValidationError) as exc:
            client.alerts.get("")

        assert "alert_id" in str(exc.value)

        with pytest.raises(ValidationError):
            client.alerts.get(None)

    def test_create_alert_with_required_fields(self, client, mock_alert):
        """Test creating alert with required fields only"""
        with patch.object(client, 'request', return_value={"alert": mock_alert}):
            alert = client.alerts.create(
                name="Brent High Alert",
                commodity_code="BRENT_CRUDE_USD",
                condition_operator="greater_than",
                condition_value=85.00
            )

            assert isinstance(alert, PriceAlert)
            assert alert.name == "Brent High Alert"
            assert alert.commodity_code == "BRENT_CRUDE_USD"

    def test_create_alert_with_all_fields(self, client, mock_alert):
        """Test creating alert with all optional fields"""
        complete_alert = {
            **mock_alert,
            "webhook_url": "https://example.com/webhook",
            "enabled": False,
            "cooldown_minutes": 180,
            "metadata": {"tag": "important"}
        }

        with patch.object(client, 'request', return_value={"alert": complete_alert}):
            alert = client.alerts.create(
                name="Complete Alert",
                commodity_code="BRENT_CRUDE_USD",
                condition_operator="greater_than",
                condition_value=90.00,
                webhook_url="https://example.com/webhook",
                enabled=False,
                cooldown_minutes=180,
                metadata={"tag": "important"}
            )

            assert alert.webhook_url == "https://example.com/webhook"
            assert alert.enabled is False
            assert alert.cooldown_minutes == 180

    def test_create_alert_validate_name(self, client):
        """Test name validation"""
        # Empty name
        with pytest.raises(ValidationError) as exc:
            client.alerts.create(
                name="",
                commodity_code="BRENT_CRUDE_USD",
                condition_operator="greater_than",
                condition_value=85.00
            )
        assert "name" in str(exc.value)

        # Too long name
        with pytest.raises(ValidationError) as exc:
            client.alerts.create(
                name="a" * 101,
                commodity_code="BRENT_CRUDE_USD",
                condition_operator="greater_than",
                condition_value=85.00
            )
        assert "name" in str(exc.value)

    def test_create_alert_validate_commodity_code(self, client):
        """Test commodity code validation"""
        with pytest.raises(ValidationError) as exc:
            client.alerts.create(
                name="Valid Name",
                commodity_code="",
                condition_operator="greater_than",
                condition_value=85.00
            )
        assert "commodity_code" in str(exc.value)

    def test_create_alert_validate_operator(self, client):
        """Test operator validation"""
        # Invalid operator
        with pytest.raises(ValidationError) as exc:
            client.alerts.create(
                name="Valid Name",
                commodity_code="BRENT_CRUDE_USD",
                condition_operator="invalid_operator",
                condition_value=85.00
            )
        assert "condition_operator" in str(exc.value)

        # Missing operator
        with pytest.raises(ValidationError) as exc:
            client.alerts.create(
                name="Valid Name",
                commodity_code="BRENT_CRUDE_USD",
                condition_operator="",
                condition_value=85.00
            )
        assert "condition_operator" in str(exc.value)

    def test_create_alert_validate_value(self, client):
        """Test condition value validation"""
        # Zero value
        with pytest.raises(ValidationError) as exc:
            client.alerts.create(
                name="Valid Name",
                commodity_code="BRENT_CRUDE_USD",
                condition_operator="greater_than",
                condition_value=0
            )
        assert "condition_value" in str(exc.value)

        # Negative value
        with pytest.raises(ValidationError):
            client.alerts.create(
                name="Valid Name",
                commodity_code="BRENT_CRUDE_USD",
                condition_operator="greater_than",
                condition_value=-5
            )

        # Too large value
        with pytest.raises(ValidationError) as exc:
            client.alerts.create(
                name="Valid Name",
                commodity_code="BRENT_CRUDE_USD",
                condition_operator="greater_than",
                condition_value=1_000_001
            )
        assert "condition_value" in str(exc.value)

    def test_create_alert_validate_webhook_url(self, client):
        """Test webhook URL validation"""
        # Non-HTTPS URL
        with pytest.raises(ValidationError) as exc:
            client.alerts.create(
                name="Valid Name",
                commodity_code="BRENT_CRUDE_USD",
                condition_operator="greater_than",
                condition_value=85.00,
                webhook_url="http://insecure.com"
            )
        assert "webhook_url" in str(exc.value)

    def test_create_alert_validate_cooldown(self, client):
        """Test cooldown minutes validation"""
        # Negative cooldown
        with pytest.raises(ValidationError) as exc:
            client.alerts.create(
                name="Valid Name",
                commodity_code="BRENT_CRUDE_USD",
                condition_operator="greater_than",
                condition_value=85.00,
                cooldown_minutes=-1
            )
        assert "cooldown_minutes" in str(exc.value)

        # Too large cooldown
        with pytest.raises(ValidationError):
            client.alerts.create(
                name="Valid Name",
                commodity_code="BRENT_CRUDE_USD",
                condition_operator="greater_than",
                condition_value=85.00,
                cooldown_minutes=1441
            )

    def test_create_alert_all_valid_operators(self, client, mock_alert):
        """Test all valid operators are accepted"""
        operators = [
            'greater_than',
            'less_than',
            'equals',
            'greater_than_or_equal',
            'less_than_or_equal'
        ]

        for operator in operators:
            with patch.object(client, 'request', return_value={"alert": mock_alert}):
                alert = client.alerts.create(
                    name="Test Alert",
                    commodity_code="BRENT_CRUDE_USD",
                    condition_operator=operator,
                    condition_value=85.00
                )
                assert isinstance(alert, PriceAlert)

    def test_update_alert(self, client, mock_alert):
        """Test updating an alert"""
        updated_alert = {
            **mock_alert,
            "condition_value": 90.00,
            "enabled": False
        }

        with patch.object(client, 'request', return_value={"alert": updated_alert}):
            alert = client.alerts.update(
                "550e8400-e29b-41d4-a716-446655440000",
                condition_value=90.00,
                enabled=False
            )

            assert alert.condition_value == 90.00
            assert alert.enabled is False

    def test_update_alert_all_fields(self, client, mock_alert):
        """Test updating all fields"""
        updated_alert = {
            **mock_alert,
            "name": "Updated Alert",
            "commodity_code": "WTI_USD",
            "condition_operator": "less_than",
            "condition_value": 70.00,
            "webhook_url": "https://new-webhook.com",
            "enabled": True,
            "cooldown_minutes": 120,
            "metadata": {"updated": True}
        }

        with patch.object(client, 'request', return_value={"alert": updated_alert}):
            alert = client.alerts.update(
                "550e8400-e29b-41d4-a716-446655440000",
                name="Updated Alert",
                commodity_code="WTI_USD",
                condition_operator="less_than",
                condition_value=70.00,
                webhook_url="https://new-webhook.com",
                enabled=True,
                cooldown_minutes=120,
                metadata={"updated": True}
            )

            assert alert.name == "Updated Alert"
            assert alert.commodity_code == "WTI_USD"

    def test_update_alert_invalid_id(self, client):
        """Test updating with invalid ID"""
        with pytest.raises(ValidationError):
            client.alerts.update("", enabled=False)

    def test_update_alert_validation(self, client):
        """Test validation during update"""
        # Invalid name
        with pytest.raises(ValidationError):
            client.alerts.update("valid-id", name="a" * 101)

        # Invalid operator
        with pytest.raises(ValidationError):
            client.alerts.update("valid-id", condition_operator="invalid")

        # Invalid value
        with pytest.raises(ValidationError):
            client.alerts.update("valid-id", condition_value=0)

        # Invalid webhook URL
        with pytest.raises(ValidationError):
            client.alerts.update("valid-id", webhook_url="http://insecure.com")

        # Invalid cooldown
        with pytest.raises(ValidationError):
            client.alerts.update("valid-id", cooldown_minutes=-1)

    def test_delete_alert(self, client):
        """Test deleting an alert"""
        with patch.object(client, 'request', return_value={}):
            # Should not raise
            client.alerts.delete("550e8400-e29b-41d4-a716-446655440000")

    def test_delete_alert_invalid_id(self, client):
        """Test deleting with invalid ID"""
        with pytest.raises(ValidationError):
            client.alerts.delete("")

        with pytest.raises(ValidationError):
            client.alerts.delete(None)

    def test_test_webhook_success(self, client):
        """Test successful webhook test"""
        mock_response = {
            "success": True,
            "status_code": 200,
            "response_time_ms": 145.0,
            "response_body": '{"received":true}'
        }

        with patch.object(client, 'request', return_value=mock_response):
            result = client.alerts.test_webhook("https://example.com/webhook")

            assert isinstance(result, WebhookTestResponse)
            assert result.success is True
            assert result.status_code == 200
            assert result.response_time_ms == 145.0

    def test_test_webhook_failure(self, client):
        """Test failed webhook test"""
        mock_response = {
            "success": False,
            "status_code": 500,
            "response_time_ms": 5000.0,
            "error": "Internal Server Error"
        }

        with patch.object(client, 'request', return_value=mock_response):
            result = client.alerts.test_webhook("https://example.com/webhook")

            assert result.success is False
            assert result.error == "Internal Server Error"

    def test_test_webhook_validation(self, client):
        """Test webhook URL validation"""
        # Empty URL
        with pytest.raises(ValidationError):
            client.alerts.test_webhook("")

        # None URL
        with pytest.raises(ValidationError):
            client.alerts.test_webhook(None)

        # Non-HTTPS URL
        with pytest.raises(ValidationError):
            client.alerts.test_webhook("http://insecure.com")

    def test_to_dataframe(self, client, mock_alert):
        """Test converting alerts to DataFrame"""
        pytest.importorskip("pandas")  # Skip if pandas not installed

        mock_alerts = [
            mock_alert,
            {
                **mock_alert,
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "name": "WTI Low Alert"
            }
        ]

        with patch.object(client, 'request', return_value={"alerts": mock_alerts}):
            df = client.alerts.to_dataframe()

            assert len(df) == 2
            assert "name" in df.columns
            assert "commodity_code" in df.columns
            assert df.index.name == "id" or df.index[0] == "550e8400-e29b-41d4-a716-446655440000"

    def test_to_dataframe_empty(self, client):
        """Test converting empty alerts list to DataFrame"""
        pytest.importorskip("pandas")

        with patch.object(client, 'request', return_value={"alerts": []}):
            df = client.alerts.to_dataframe()

            assert len(df) == 0
            assert "name" in df.columns  # Should have expected columns
