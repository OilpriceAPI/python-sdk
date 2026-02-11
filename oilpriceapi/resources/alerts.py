"""
Price Alerts Resource

Manage price alert configurations for automated notifications.
"""

from typing import Optional, List, Dict, Any
from ..exceptions import ValidationError, OilPriceAPIError
from ..models import PriceAlert, WebhookTestResponse


# Valid alert operators
VALID_OPERATORS = [
    'greater_than',
    'less_than',
    'equals',
    'greater_than_or_equal',
    'less_than_or_equal'
]


class AlertsResource:
    """
    Price Alerts Resource

    Manage automated price alert configurations with webhook notifications.

    **Features:**
    - Create alerts with customizable conditions
    - Monitor commodity prices automatically
    - Webhook notifications when conditions are met
    - Cooldown periods to prevent spam
    - 100 alerts per user soft limit

    **Example:**
    ```python
    from oilpriceapi import OilPriceAPI

    client = OilPriceAPI()

    # Create a price alert
    alert = client.alerts.create(
        name='Brent High Price Alert',
        commodity_code='BRENT_CRUDE_USD',
        condition_operator='greater_than',
        condition_value=85.00,
        webhook_url='https://your-app.com/webhooks/price-alert',
        enabled=True,
        cooldown_minutes=60
    )

    print(f"Alert created: {alert.name} (ID: {alert.id})")

    # List all alerts
    alerts = client.alerts.list()
    print(f"You have {len(alerts)} active alerts")

    # Update an alert
    updated = client.alerts.update(
        alert.id,
        condition_value=90.00,
        enabled=False
    )

    # Delete an alert
    client.alerts.delete(alert.id)
    ```
    """

    def __init__(self, client):
        """
        Initialize the alerts resource.

        Args:
            client: The OilPriceAPI client instance
        """
        self.client = client

    def list(self) -> List[PriceAlert]:
        """
        List all price alerts for the authenticated user.

        Returns all configured price alerts, including disabled ones.
        Alerts are sorted by creation date (newest first).

        Returns:
            List[PriceAlert]: Array of all price alerts

        Raises:
            OilPriceAPIError: If API request fails
            AuthenticationError: If API key is invalid
            RateLimitError: If rate limit exceeded

        Example:
            >>> alerts = client.alerts.list()
            >>> for alert in alerts:
            ...     print(f"{alert.name}: {alert.commodity_code} {alert.condition_operator} {alert.condition_value}")
            ...     print(f"  Status: {'Active' if alert.enabled else 'Disabled'}")
            ...     print(f"  Triggers: {alert.trigger_count}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/alerts"
        )

        # API returns array directly, but handle both formats for compatibility
        if isinstance(response, list):
            alerts_data = response
        elif "alerts" in response:
            alerts_data = response["alerts"]
        elif "data" in response:
            alerts_data = response["data"]
        else:
            alerts_data = []

        return [PriceAlert(**alert_data) for alert_data in alerts_data]

    def get(self, alert_id: str) -> PriceAlert:
        """
        Get a specific price alert by ID.

        Args:
            alert_id: The alert ID to retrieve

        Returns:
            PriceAlert: The price alert details

        Raises:
            ValidationError: If alert_id is invalid
            DataNotFoundError: If alert ID not found
            OilPriceAPIError: If API request fails

        Example:
            >>> alert = client.alerts.get('550e8400-e29b-41d4-a716-446655440000')
            >>> print(f"Alert: {alert.name}")
            >>> print(f"Condition: {alert.commodity_code} {alert.condition_operator} {alert.condition_value}")
            >>> print(f"Last triggered: {alert.last_triggered_at or 'Never'}")
        """
        if not alert_id or not isinstance(alert_id, str):
            raise ValidationError(
                message="Alert ID must be a non-empty string",
                field="alert_id",
                value=alert_id
            )

        response = self.client.request(
            method="GET",
            path=f"/v1/alerts/{alert_id}"
        )

        # API returns object directly, but handle both formats for compatibility
        if isinstance(response, dict) and "id" in response:
            # Direct object response (actual API behavior)
            alert_data = response
        elif "alert" in response:
            # Wrapped response
            alert_data = response["alert"]
        elif "data" in response:
            # Alternative wrapped format
            alert_data = response["data"]
        else:
            alert_data = response

        return PriceAlert(**alert_data)

    def create(
        self,
        name: str,
        commodity_code: str,
        condition_operator: str,
        condition_value: float,
        webhook_url: Optional[str] = None,
        enabled: bool = True,
        cooldown_minutes: int = 60,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PriceAlert:
        """
        Create a new price alert.

        Creates a price alert that monitors a commodity and triggers when
        the price meets the specified condition. Optionally sends webhook
        notifications when triggered.

        **Validation:**
        - name: 1-100 characters
        - commodity_code: Must be a valid commodity code
        - condition_value: Must be > 0 and <= 1,000,000
        - cooldown_minutes: Must be 0-1440 (24 hours)
        - webhook_url: Must be valid HTTPS URL if provided

        **Soft Limit:** 100 alerts per user

        Args:
            name: Alert name (1-100 characters)
            commodity_code: Commodity to monitor (e.g., "BRENT_CRUDE_USD")
            condition_operator: Comparison operator (greater_than, less_than, equals,
                               greater_than_or_equal, less_than_or_equal)
            condition_value: Price threshold (must be > 0 and <= 1,000,000)
            webhook_url: Optional HTTPS webhook URL for notifications
            enabled: Whether to enable the alert immediately (default: True)
            cooldown_minutes: Minutes between triggers (0-1440, default: 60)
            metadata: Optional custom metadata dictionary

        Returns:
            PriceAlert: The created price alert

        Raises:
            ValidationError: If parameters are invalid
            OilPriceAPIError: If API request fails

        Example:
            >>> # Alert when Brent crude exceeds $85
            >>> alert = client.alerts.create(
            ...     name='Brent $85 Alert',
            ...     commodity_code='BRENT_CRUDE_USD',
            ...     condition_operator='greater_than',
            ...     condition_value=85.00,
            ...     webhook_url='https://myapp.com/webhook',
            ...     enabled=True,
            ...     cooldown_minutes=120  # 2 hours between triggers
            ... )
        """
        # Validate required fields
        if not name or not isinstance(name, str):
            raise ValidationError(
                message="Alert name is required and must be a string",
                field="name",
                value=name
            )
        if len(name) < 1 or len(name) > 100:
            raise ValidationError(
                message="Alert name must be 1-100 characters",
                field="name",
                value=name
            )

        if not commodity_code or not isinstance(commodity_code, str):
            raise ValidationError(
                message="Commodity code is required and must be a string",
                field="commodity_code",
                value=commodity_code
            )

        if not condition_operator:
            raise ValidationError(
                message="Condition operator is required",
                field="condition_operator",
                value=condition_operator
            )
        if condition_operator not in VALID_OPERATORS:
            raise ValidationError(
                message=f"Invalid operator. Must be one of: {', '.join(VALID_OPERATORS)}",
                field="condition_operator",
                value=condition_operator
            )

        if not isinstance(condition_value, (int, float)):
            raise ValidationError(
                message="Condition value must be a number",
                field="condition_value",
                value=condition_value
            )
        if condition_value <= 0 or condition_value > 1_000_000:
            raise ValidationError(
                message="Condition value must be greater than 0 and less than or equal to 1,000,000",
                field="condition_value",
                value=condition_value
            )

        # Validate optional fields
        if webhook_url is not None:
            if not isinstance(webhook_url, str):
                raise ValidationError(
                    message="Webhook URL must be a string",
                    field="webhook_url",
                    value=webhook_url
                )
            if webhook_url and not webhook_url.startswith('https://'):
                raise ValidationError(
                    message="Webhook URL must use HTTPS protocol",
                    field="webhook_url",
                    value=webhook_url
                )

        if not isinstance(cooldown_minutes, int):
            raise ValidationError(
                message="Cooldown minutes must be an integer",
                field="cooldown_minutes",
                value=cooldown_minutes
            )
        if cooldown_minutes < 0 or cooldown_minutes > 1440:
            raise ValidationError(
                message="Cooldown minutes must be between 0 and 1440 (24 hours)",
                field="cooldown_minutes",
                value=cooldown_minutes
            )

        response = self.client.request(
            method="POST",
            path="/v1/alerts",
            json_data={
                "price_alert": {
                    "name": name,
                    "commodity_code": commodity_code,
                    "condition_operator": condition_operator,
                    "condition_value": condition_value,
                    "webhook_url": webhook_url,
                    "enabled": enabled,
                    "cooldown_minutes": cooldown_minutes,
                    "metadata": metadata
                }
            }
        )

        # API returns object directly, but handle both formats for compatibility
        if isinstance(response, dict) and "id" in response:
            # Direct object response (actual API behavior)
            alert_data = response
        elif "alert" in response:
            # Wrapped response
            alert_data = response["alert"]
        elif "data" in response:
            # Alternative wrapped format
            alert_data = response["data"]
        else:
            alert_data = response

        return PriceAlert(**alert_data)

    def update(
        self,
        alert_id: str,
        name: Optional[str] = None,
        commodity_code: Optional[str] = None,
        condition_operator: Optional[str] = None,
        condition_value: Optional[float] = None,
        webhook_url: Optional[str] = None,
        enabled: Optional[bool] = None,
        cooldown_minutes: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PriceAlert:
        """
        Update an existing price alert.

        Updates one or more fields of an existing alert. Only provided
        fields will be updated; others remain unchanged.

        Args:
            alert_id: The alert ID to update
            name: Alert name (1-100 characters)
            commodity_code: Commodity code to monitor
            condition_operator: Comparison operator
            condition_value: Price threshold
            webhook_url: Webhook URL (or None to remove)
            enabled: Whether the alert is active
            cooldown_minutes: Minutes between triggers (0-1440)
            metadata: Custom metadata dictionary

        Returns:
            PriceAlert: The updated price alert

        Raises:
            ValidationError: If parameters are invalid
            DataNotFoundError: If alert ID not found
            OilPriceAPIError: If API request fails

        Example:
            >>> # Disable an alert
            >>> client.alerts.update(alert_id, enabled=False)
            >>>
            >>> # Change threshold and cooldown
            >>> client.alerts.update(
            ...     alert_id,
            ...     condition_value=90.00,
            ...     cooldown_minutes=180
            ... )
            >>>
            >>> # Update webhook URL
            >>> client.alerts.update(
            ...     alert_id,
            ...     webhook_url='https://newapp.com/webhook'
            ... )
        """
        if not alert_id or not isinstance(alert_id, str):
            raise ValidationError(
                message="Alert ID must be a non-empty string",
                field="alert_id",
                value=alert_id
            )

        # Build update payload with only provided fields
        update_data = {}

        # Validate fields if provided
        if name is not None:
            if not isinstance(name, str) or len(name) < 1 or len(name) > 100:
                raise ValidationError(
                    message="Alert name must be 1-100 characters",
                    field="name",
                    value=name
                )
            update_data["name"] = name

        if commodity_code is not None:
            update_data["commodity_code"] = commodity_code

        if condition_operator is not None:
            if condition_operator not in VALID_OPERATORS:
                raise ValidationError(
                    message=f"Invalid operator. Must be one of: {', '.join(VALID_OPERATORS)}",
                    field="condition_operator",
                    value=condition_operator
                )
            update_data["condition_operator"] = condition_operator

        if condition_value is not None:
            if not isinstance(condition_value, (int, float)):
                raise ValidationError(
                    message="Condition value must be a number",
                    field="condition_value",
                    value=condition_value
                )
            if condition_value <= 0 or condition_value > 1_000_000:
                raise ValidationError(
                    message="Condition value must be greater than 0 and less than or equal to 1,000,000",
                    field="condition_value",
                    value=condition_value
                )
            update_data["condition_value"] = condition_value

        if webhook_url is not None:
            if webhook_url and (not isinstance(webhook_url, str) or not webhook_url.startswith('https://')):
                raise ValidationError(
                    message="Webhook URL must be a valid HTTPS URL",
                    field="webhook_url",
                    value=webhook_url
                )
            update_data["webhook_url"] = webhook_url

        if enabled is not None:
            update_data["enabled"] = enabled

        if cooldown_minutes is not None:
            if not isinstance(cooldown_minutes, int) or cooldown_minutes < 0 or cooldown_minutes > 1440:
                raise ValidationError(
                    message="Cooldown minutes must be between 0 and 1440 (24 hours)",
                    field="cooldown_minutes",
                    value=cooldown_minutes
                )
            update_data["cooldown_minutes"] = cooldown_minutes

        if metadata is not None:
            update_data["metadata"] = metadata

        response = self.client.request(
            method="PATCH",
            path=f"/v1/alerts/{alert_id}",
            json_data={
                "price_alert": update_data
            }
        )

        # API returns object directly, but handle both formats for compatibility
        if isinstance(response, dict) and "id" in response:
            # Direct object response (actual API behavior)
            alert_data = response
        elif "alert" in response:
            # Wrapped response
            alert_data = response["alert"]
        elif "data" in response:
            # Alternative wrapped format
            alert_data = response["data"]
        else:
            alert_data = response

        return PriceAlert(**alert_data)

    def delete(self, alert_id: str) -> None:
        """
        Delete a price alert.

        Permanently deletes a price alert. This action cannot be undone.

        Args:
            alert_id: The alert ID to delete

        Raises:
            ValidationError: If alert_id is invalid
            DataNotFoundError: If alert ID not found
            OilPriceAPIError: If API request fails

        Example:
            >>> client.alerts.delete(alert_id)
            >>> print('Alert deleted successfully')
        """
        if not alert_id or not isinstance(alert_id, str):
            raise ValidationError(
                message="Alert ID must be a non-empty string",
                field="alert_id",
                value=alert_id
            )

        self.client.request(
            method="DELETE",
            path=f"/v1/alerts/{alert_id}"
        )

    def test(self, alert_id: str) -> Dict[str, Any]:
        """
        Test an alert by simulating a trigger.

        Sends a test notification through the alert's webhook to verify
        it is configured correctly. Does not count toward trigger limits.

        Args:
            alert_id: The alert ID to test

        Returns:
            Dict[str, Any]: Test results including webhook response

        Raises:
            ValidationError: If alert_id is invalid
            DataNotFoundError: If alert ID not found
            OilPriceAPIError: If API request fails

        Example:
            >>> result = client.alerts.test(alert_id)
            >>> print(f"Test status: {result['status']}")
            >>> print(f"Response: {result['webhook_response']}")
        """
        if not alert_id or not isinstance(alert_id, str):
            raise ValidationError(
                message="Alert ID must be a non-empty string",
                field="alert_id",
                value=alert_id
            )

        response = self.client.request(
            method="POST",
            path=f"/v1/alerts/{alert_id}/test"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def triggers(self, **params) -> List[Dict[str, Any]]:
        """
        Get alert trigger history.

        Returns a list of all alert triggers across all alerts.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List[Dict[str, Any]]: List of alert trigger records

        Raises:
            OilPriceAPIError: If API request fails

        Example:
            >>> triggers = client.alerts.triggers()
            >>> for trigger in triggers:
            ...     print(f"{trigger['alert_name']}: {trigger['triggered_at']}")
            ...     print(f"  Price: ${trigger['price']} (threshold: ${trigger['threshold']})")
        """
        response = self.client.request(
            method="GET",
            path="/v1/alerts/triggers",
            params=params
        )

        # Parse response
        if isinstance(response, list):
            return response
        elif "triggers" in response:
            return response["triggers"]
        elif "data" in response:
            return response["data"]
        return []

    def analytics_history(self, **params) -> Dict[str, Any]:
        """
        Get alert analytics history.

        Returns analytics and statistics about alert performance,
        trigger frequency, and accuracy over time.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            Dict[str, Any]: Analytics data with metrics and trends

        Raises:
            OilPriceAPIError: If API request fails

        Example:
            >>> analytics = client.alerts.analytics_history()
            >>> print(f"Total triggers: {analytics['total_triggers']}")
            >>> print(f"Average response time: {analytics['avg_response_time']}ms")
            >>> print(f"Success rate: {analytics['success_rate']}%")
        """
        response = self.client.request(
            method="GET",
            path="/v1/alerts/analytics_history",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def to_dataframe(self) -> 'pandas.DataFrame':
        """
        Convert all price alerts to a pandas DataFrame.

        Returns a DataFrame with all configured alerts, suitable for
        analysis and visualization.

        Returns:
            pandas.DataFrame: DataFrame with alerts data

        Raises:
            ImportError: If pandas is not installed

        Example:
            >>> df = client.alerts.to_dataframe()
            >>> print(df[['name', 'commodity_code', 'enabled', 'trigger_count']])
            >>>
            >>> # Filter active alerts
            >>> active = df[df['enabled'] == True]
            >>> print(f"Active alerts: {len(active)}")
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for DataFrame operations. "
                "Install it with: pip install pandas"
            )

        alerts = self.list()

        if not alerts:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=[
                'id', 'name', 'commodity_code', 'condition_operator',
                'condition_value', 'webhook_url', 'enabled', 'cooldown_minutes',
                'trigger_count', 'last_triggered_at', 'created_at', 'updated_at'
            ])

        # Convert to list of dicts
        data = [alert.model_dump() for alert in alerts]

        df = pd.DataFrame(data)

        # Set id as index
        if 'id' in df.columns:
            df = df.set_index('id')

        return df
