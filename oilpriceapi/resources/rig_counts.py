"""
Rig Counts Resource

Oil and gas drilling rig count operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from typing import Union


class RigCountsResource:
    """Resource for drilling rig count data."""

    def __init__(self, client):
        """Initialize rig counts resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def latest(self) -> Dict[str, Any]:
        """Get latest rig count data.

        Returns:
            Latest rig count with oil, gas, and total counts

        Example:
            >>> rig_counts = client.rig_counts.latest()
            >>> print(f"Oil Rigs: {rig_counts['oil']}")
            >>> print(f"Gas Rigs: {rig_counts['gas']}")
            >>> print(f"Total: {rig_counts['total']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/rig-counts/latest"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def current(self) -> Dict[str, Any]:
        """Get current rig count data.

        Alias for latest() for backward compatibility.

        Returns:
            Current rig count data

        Example:
            >>> rig_counts = client.rig_counts.current()
            >>> print(f"Total Rigs: {rig_counts['total']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/rig-counts/current"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def historical(
        self,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None
    ) -> List[Dict[str, Any]]:
        """Get historical rig count data.

        Args:
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            List of historical rig count records

        Example:
            >>> history = client.rig_counts.historical(
            ...     start_date="2024-01-01",
            ...     end_date="2024-12-31"
            ... )
            >>> for record in history:
            ...     print(f"{record['date']}: {record['total']} rigs")
        """
        params = {}
        if start_date:
            params["start_date"] = self._format_date(start_date)
        if end_date:
            params["end_date"] = self._format_date(end_date)

        response = self.client.request(
            method="GET",
            path="/v1/rig-counts/historical",
            params=params
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def trends(self, period: str = "monthly") -> Dict[str, Any]:
        """Get rig count trends.

        Args:
            period: Trend period ("daily", "weekly", "monthly", "yearly")

        Returns:
            Trend analysis with growth rates and patterns

        Example:
            >>> trends = client.rig_counts.trends(period="monthly")
            >>> print(f"Monthly Change: {trends['change']} rigs")
            >>> print(f"Growth Rate: {trends['growth_rate']}%")
        """
        response = self.client.request(
            method="GET",
            path="/v1/rig-counts/trends",
            params={"period": period}
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def summary(self) -> Dict[str, Any]:
        """Get rig count summary statistics.

        Returns:
            Summary with current counts, changes, and breakdowns

        Example:
            >>> summary = client.rig_counts.summary()
            >>> print(f"Total: {summary['total']}")
            >>> print(f"Week Change: {summary['week_change']}")
            >>> print(f"Month Change: {summary['month_change']}")
            >>> print(f"Year Change: {summary['year_change']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/rig-counts/summary"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def _format_date(self, date_input: Union[str, date, datetime]) -> str:
        """Format date for API."""
        if isinstance(date_input, str):
            return date_input
        elif isinstance(date_input, datetime):
            return date_input.date().isoformat()
        elif isinstance(date_input, date):
            return date_input.isoformat()
        else:
            raise ValueError(f"Invalid date type: {type(date_input)}")
