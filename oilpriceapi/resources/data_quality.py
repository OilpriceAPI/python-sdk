"""
Data Quality Resource

Data quality monitoring and reporting operations.
"""

from typing import List, Dict, Any


class DataQualityResource:
    """Resource for data quality monitoring."""

    def __init__(self, client):
        """Initialize data quality resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def summary(self) -> Dict[str, Any]:
        """Get data quality summary.

        Returns:
            Summary of data quality metrics across all commodities

        Example:
            >>> summary = client.data_quality.summary()
            >>> print(f"Overall Quality Score: {summary['score']}")
            >>> print(f"Commodities: {summary['total_commodities']}")
            >>> print(f"Issues: {summary['total_issues']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/data-quality/summary"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def reports(self) -> List[Dict[str, Any]]:
        """Get all data quality reports.

        Returns:
            List of data quality reports for all commodities

        Example:
            >>> reports = client.data_quality.reports()
            >>> for report in reports:
            ...     print(f"{report['commodity']}: {report['quality_score']}%")
            ...     if report['issues']:
            ...         print(f"  Issues: {', '.join(report['issues'])}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/data-quality/reports"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response

    def report(self, code: str) -> Dict[str, Any]:
        """Get data quality report for a specific commodity.

        Args:
            code: Commodity code

        Returns:
            Detailed data quality report

        Example:
            >>> report = client.data_quality.report("BRENT_CRUDE_USD")
            >>> print(f"Quality Score: {report['quality_score']}%")
            >>> print(f"Last Update: {report['last_update']}")
            >>> print(f"Update Frequency: {report['update_frequency']}")
            >>> print(f"Data Completeness: {report['completeness']}%")
            >>> print(f"Data Accuracy: {report['accuracy']}%")
            >>> if report['issues']:
            ...     print(f"Issues: {report['issues']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/data-quality/reports/{code}"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response
