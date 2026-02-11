"""
Data Sources Resource

Data source connector management operations.
"""

from typing import List, Dict, Any, Optional


class DataSourcesResource:
    """Resource for data source connector management."""

    def __init__(self, client):
        """Initialize data sources resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self, **params) -> List[Dict[str, Any]]:
        """Get all data sources.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of data source records

        Example:
            >>> sources = client.data_sources.list()
            >>> for source in sources:
            ...     print(f"{source['name']}: {source['type']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/data-sources",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def get(self, source_id: str) -> Dict[str, Any]:
        """Get a specific data source by ID.

        Args:
            source_id: Data source ID

        Returns:
            Data source details

        Example:
            >>> source = client.data_sources.get("123")
            >>> print(f"Name: {source['name']}")
            >>> print(f"Type: {source['type']}")
            >>> print(f"Status: {source['status']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/data-sources/{source_id}"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def create(
        self,
        name: str,
        source_type: str,
        credentials: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a new data source.

        Args:
            name: Data source name
            source_type: Type of data source (e.g., "platts", "argus", "opis")
            credentials: Credentials for the data source
            config: Optional configuration settings
            enabled: Whether the data source is active (default: True)
            **kwargs: Additional data source configuration

        Returns:
            Created data source details

        Example:
            >>> source = client.data_sources.create(
            ...     name="Platts API",
            ...     source_type="platts",
            ...     credentials={
            ...         "api_key": "your-api-key",
            ...         "api_secret": "your-secret"
            ...     },
            ...     config={
            ...         "fetch_interval": 300
            ...     },
            ...     enabled=True
            ... )
            >>> print(f"Data source created: {source['id']}")
        """
        json_data = {
            "name": name,
            "source_type": source_type,
            "credentials": credentials,
            "enabled": enabled,
        }

        if config:
            json_data["config"] = config

        # Add any additional kwargs
        json_data.update(kwargs)

        response = self.client.request(
            method="POST",
            path="/v1/data-sources",
            json_data=json_data
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def update(
        self,
        source_id: str,
        name: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Update an existing data source.

        Args:
            source_id: Data source ID to update
            name: Data source name
            credentials: Credentials for the data source
            config: Configuration settings
            enabled: Whether the data source is active
            **kwargs: Additional data source configuration

        Returns:
            Updated data source details

        Example:
            >>> source = client.data_sources.update(
            ...     source_id="123",
            ...     config={"fetch_interval": 600},
            ...     enabled=False
            ... )
            >>> print(f"Data source updated: {source['id']}")
        """
        json_data = {}

        if name is not None:
            json_data["name"] = name
        if credentials is not None:
            json_data["credentials"] = credentials
        if config is not None:
            json_data["config"] = config
        if enabled is not None:
            json_data["enabled"] = enabled

        # Add any additional kwargs
        json_data.update(kwargs)

        response = self.client.request(
            method="PATCH",
            path=f"/v1/data-sources/{source_id}",
            json_data=json_data
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def delete(self, source_id: str) -> None:
        """Delete a data source.

        Args:
            source_id: Data source ID to delete

        Example:
            >>> client.data_sources.delete("123")
            >>> print("Data source deleted")
        """
        self.client.request(
            method="DELETE",
            path=f"/v1/data-sources/{source_id}"
        )

    def test(self, source_id: str) -> Dict[str, Any]:
        """Test a data source connection.

        Args:
            source_id: Data source ID to test

        Returns:
            Test result details

        Example:
            >>> result = client.data_sources.test("123")
            >>> print(f"Test status: {result['status']}")
            >>> print(f"Message: {result['message']}")
        """
        response = self.client.request(
            method="POST",
            path=f"/v1/data-sources/{source_id}/test"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def logs(self, source_id: str, **params) -> List[Dict[str, Any]]:
        """Get data source logs.

        Args:
            source_id: Data source ID
            **params: Optional query parameters for filtering

        Returns:
            List of log entries

        Example:
            >>> logs = client.data_sources.logs("123", limit=100)
            >>> for log in logs:
            ...     print(f"{log['timestamp']}: {log['level']} - {log['message']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/data-sources/{source_id}/logs",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def health(self, source_id: str) -> Dict[str, Any]:
        """Get data source health status.

        Args:
            source_id: Data source ID

        Returns:
            Health status details

        Example:
            >>> health = client.data_sources.health("123")
            >>> print(f"Status: {health['status']}")
            >>> print(f"Last successful fetch: {health['last_success']}")
            >>> print(f"Error count: {health['error_count']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/data-sources/{source_id}/health"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def rotate_credentials(self, source_id: str, new_credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Rotate data source credentials.

        Args:
            source_id: Data source ID
            new_credentials: New credentials to set

        Returns:
            Updated data source details

        Example:
            >>> source = client.data_sources.rotate_credentials(
            ...     source_id="123",
            ...     new_credentials={
            ...         "api_key": "new-api-key",
            ...         "api_secret": "new-secret"
            ...     }
            ... )
            >>> print(f"Credentials rotated for: {source['name']}")
        """
        response = self.client.request(
            method="POST",
            path=f"/v1/data-sources/{source_id}/rotate_credentials",
            json_data={"credentials": new_credentials}
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response
