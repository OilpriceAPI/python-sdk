"""
EI Drilling Productivity Resource

Energy Intelligence drilling productivity data operations.
"""

from typing import Any, Dict, List

from ._envelopes import ei_data, unwrap_ei_collection


class EIDrillingProductivityResource:
    """Resource for Energy Intelligence drilling productivity data."""

    def __init__(self, client):
        """Initialize EI drilling productivity resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self, **params) -> List[Dict[str, Any]]:
        """Get all drilling productivity data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of report summaries with ``id``, ``report_month``,
            ``summary`` and ``status``.

        Example:
            >>> reports = client.ei.drilling_productivity.list()
            >>> for report in reports:
            ...     print(f"{report['report_month']}: {report['status']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/drilling_productivities",
            params=params
        )

        return ei_data(response)

    def get(self, id: str) -> Dict[str, Any]:
        """Get a specific drilling productivity record by ID.

        Args:
            id: Drilling productivity record ID

        Returns:
            Report object with ``id``, ``report_month``, ``source``,
            ``last_updated``, ``total_duc`` and ``basins``.

        Example:
            >>> report = client.ei.drilling_productivity.get("123")
            >>> print(f"Total DUC: {report['total_duc']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/drilling_productivities/{id}"
        )

        return ei_data(response)

    def latest(self) -> Dict[str, Any]:
        """Get latest drilling productivity data.

        Returns:
            Report object with ``id``, ``report_month``, ``source``,
            ``last_updated``, ``total_duc`` and ``basins``.

        Example:
            >>> latest = client.ei.drilling_productivity.latest()
            >>> print(f"Total DUC: {latest['total_duc']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/drilling_productivities/latest"
        )

        return ei_data(response)

    def summary(self) -> Dict[str, Any]:
        """Get drilling productivity summary.

        Returns:
            Summary object with ``report_month``, ``total_duc_wells``,
            ``average_oil_productivity``, ``average_gas_productivity``,
            ``basins`` and ``headline``.

        Example:
            >>> summary = client.ei.drilling_productivity.summary()
            >>> print(f"Total DUC wells: {summary['total_duc_wells']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/drilling_productivities/summary"
        )

        return ei_data(response)

    def duc_wells(self, **params) -> List[Dict[str, Any]]:
        """Get DUC (Drilled but Uncompleted) wells data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``by_basin`` list from ``data``. Each record has
            ``basin``, ``basin_name``, ``duc_count``, ``region`` and
            ``type``.

        Example:
            >>> ducs = client.ei.drilling_productivity.duc_wells()
            >>> for duc in ducs:
            ...     print(f"{duc['basin_name']}: {duc['duc_count']} DUCs")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/drilling_productivities/duc_wells",
            params=params
        )

        return unwrap_ei_collection(
            response,
            collection="by_basin",
            subject="drilling-productivity DUC wells",
        )

    def by_basin(self, **params) -> List[Dict[str, Any]]:
        """Get drilling productivity by basin.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``months`` list from ``data`` — one entry per report month,
            each with ``report_month`` and a ``basins`` list of per-basin
            records. (``data['basins']`` is the echoed filter, not the
            collection.)

        Example:
            >>> months = client.ei.drilling_productivity.by_basin()
            >>> for month in months:
            ...     print(f"{month['report_month']}: {len(month['basins'])} basins")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/drilling_productivities/by_basin",
            params=params
        )

        return unwrap_ei_collection(
            response,
            collection="months",
            subject="drilling-productivity by-basin",
        )

    def historical(self, **params) -> List[Dict[str, Any]]:
        """Get historical drilling productivity data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``records`` list from ``data``. Each record has
            ``report_month``, ``duc_count``, ``new_well_oil_per_rig`` and
            ``new_well_gas_per_rig``.

        Example:
            >>> history = client.ei.drilling_productivity.historical(basin="permian")
            >>> for record in history:
            ...     print(f"{record['report_month']}: {record['duc_count']} DUCs")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/drilling_productivities/historical",
            params=params
        )

        return unwrap_ei_collection(
            response,
            collection="records",
            subject="drilling-productivity historical",
        )

    def trends(self, **params) -> List[Dict[str, Any]]:
        """Get drilling productivity trends.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``trends`` list from ``data``. Each record has ``basin``,
            ``current_duc``, ``previous_duc``, ``duc_change``,
            ``duc_trend``, ``productivity_oil`` and ``productivity_gas``.

        Example:
            >>> trends = client.ei.drilling_productivity.trends()
            >>> for point in trends:
            ...     print(f"{point['basin']}: {point['duc_trend']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/drilling_productivities/trends",
            params=params
        )

        return unwrap_ei_collection(
            response,
            collection="trends",
            subject="drilling-productivity trends",
        )
