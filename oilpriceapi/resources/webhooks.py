"""
Webhooks Resource

Webhook endpoint management operations.
"""

from typing import List, Dict, Any, Optional


class WebhooksResource:
    """Resource for webhook management."""

    def __init__(self, client):
        """Initialize webhooks resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self, **params) -> List[Dict[str, Any]]:
        """Get all webhooks.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of webhook records

        Example:
            >>> webhooks = client.webhooks.list()
            >>> for webhook in webhooks:
            ...     print(f"{webhook['url']}: {webhook['events']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/webhooks",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def get(self, webhook_id: str) -> Dict[str, Any]:
        """Get a specific webhook by ID.

        Args:
            webhook_id: Webhook ID

        Returns:
            Webhook details

        Example:
            >>> webhook = client.webhooks.get("123")
            >>> print(f"URL: {webhook['url']}")
            >>> print(f"Events: {webhook['events']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/webhooks/{webhook_id}"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def create(
        self,
        url: str,
        events: List[str],
        description: Optional[str] = None,
        secret: Optional[str] = None,
        enabled: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a new webhook.

        Args:
            url: Webhook endpoint URL (must be HTTPS)
            events: List of event types to subscribe to
            description: Optional description
            secret: Optional webhook secret for signature verification
            enabled: Whether the webhook is active (default: True)
            **kwargs: Additional webhook configuration

        Returns:
            Created webhook details

        Example:
            >>> webhook = client.webhooks.create(
            ...     url="https://myapp.com/webhook",
            ...     events=["price.updated", "alert.triggered"],
            ...     description="Price alerts webhook",
            ...     enabled=True
            ... )
            >>> print(f"Webhook created: {webhook['id']}")
        """
        json_data = {
            "url": url,
            "events": events,
            "enabled": enabled,
        }

        if description:
            json_data["description"] = description
        if secret:
            json_data["secret"] = secret

        # Add any additional kwargs
        json_data.update(kwargs)

        response = self.client.request(
            method="POST",
            path="/v1/webhooks",
            json_data=json_data
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def update(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
        secret: Optional[str] = None,
        enabled: Optional[bool] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Update an existing webhook.

        Args:
            webhook_id: Webhook ID to update
            url: Webhook endpoint URL
            events: List of event types to subscribe to
            description: Description
            secret: Webhook secret for signature verification
            enabled: Whether the webhook is active
            **kwargs: Additional webhook configuration

        Returns:
            Updated webhook details

        Example:
            >>> webhook = client.webhooks.update(
            ...     webhook_id="123",
            ...     events=["price.updated"],
            ...     enabled=False
            ... )
            >>> print(f"Webhook updated: {webhook['id']}")
        """
        json_data = {}

        if url is not None:
            json_data["url"] = url
        if events is not None:
            json_data["events"] = events
        if description is not None:
            json_data["description"] = description
        if secret is not None:
            json_data["secret"] = secret
        if enabled is not None:
            json_data["enabled"] = enabled

        # Add any additional kwargs
        json_data.update(kwargs)

        response = self.client.request(
            method="PATCH",
            path=f"/v1/webhooks/{webhook_id}",
            json_data=json_data
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def delete(self, webhook_id: str) -> None:
        """Delete a webhook.

        Args:
            webhook_id: Webhook ID to delete

        Example:
            >>> client.webhooks.delete("123")
            >>> print("Webhook deleted")
        """
        self.client.request(
            method="DELETE",
            path=f"/v1/webhooks/{webhook_id}"
        )

    def test(self, webhook_id: str) -> Dict[str, Any]:
        """Test a webhook by sending a test event.

        Args:
            webhook_id: Webhook ID to test

        Returns:
            Test result details

        Example:
            >>> result = client.webhooks.test("123")
            >>> print(f"Test status: {result['status']}")
            >>> print(f"Response: {result['response']}")
        """
        response = self.client.request(
            method="POST",
            path=f"/v1/webhooks/{webhook_id}/test"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def events(self, webhook_id: str, **params) -> List[Dict[str, Any]]:
        """Get webhook event history.

        Args:
            webhook_id: Webhook ID
            **params: Optional query parameters for filtering

        Returns:
            List of webhook event records

        Example:
            >>> events = client.webhooks.events("123")
            >>> for event in events:
            ...     print(f"{event['created_at']}: {event['type']} - {event['status']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/webhooks/{webhook_id}/events",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response
