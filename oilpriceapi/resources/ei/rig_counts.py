"""
EI Rig Counts Resource

Energy Intelligence rig count data operations.

Envelope reference (verified live 2026-09-13): every route below returns
``{"data": ..., "meta": {...}}``. ``by_basin``, ``by_state`` and ``historical``
put their records under a named key inside ``data``.
"""

from typing import Any, Dict, List

from ._envelopes import ei_data, unwrap_ei_collection


class EIRigCountsResource:
    """Resource for Energy Intelligence rig count data."""

    def __init__(self, client):
        """Initialize EI rig counts resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self, **params) -> List[Dict[str, Any]]:
        """Get all rig count reports.

        Args:
            **params: Optional query parameters (``page``, ``per_page``)

        Returns:
            List of report summaries, each with ``id``, ``report_date``,
            ``summary`` and ``status``.

        Example:
            >>> reports = client.ei.rig_counts.list()
            >>> for report in reports:
            ...     print(f"{report['report_date']}: {report['status']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/rig_counts",
            params=params
        )

        return ei_data(response)

    def get(self, id: str) -> Dict[str, Any]:
        """Get a specific rig count report by ID.

        Args:
            id: Rig count report ID

        Returns:
            Report with ``report_date``, ``us_total``, ``basins``,
            ``top_states`` and ``drilling_type``.

        Example:
            >>> report = client.ei.rig_counts.get("123")
            >>> print(f"US total: {report['us_total']['total_rigs']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/rig_counts/{id}"
        )

        return ei_data(response)

    def latest(self) -> Dict[str, Any]:
        """Get the latest rig count report.

        Returns:
            Report object with ``id``, ``report_date``, ``source``,
            ``last_updated``, ``us_total``, ``basins`` (a mapping keyed by
            basin), ``top_states`` and ``drilling_type``.

        Example:
            >>> latest = client.ei.rig_counts.latest()
            >>> print(f"Total rigs: {latest['us_total']['total_rigs']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/rig_counts/latest"
        )

        return ei_data(response)

    def by_basin(self, **params) -> List[Dict[str, Any]]:
        """Get rig counts by basin.

        Args:
            **params: Optional ``basins`` (comma-separated) and ``date``

        Returns:
            The ``basins`` list from ``data``. Each record has ``region``,
            ``region_type``, ``count``, ``week_over_week`` and
            ``change_direction``. The report date itself is not part of this
            list; call :meth:`latest` when you need it.

        Example:
            >>> basins = client.ei.rig_counts.by_basin()
            >>> for basin in basins:
            ...     print(f"{basin['region']}: {basin['count']} rigs")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/rig_counts/by_basin",
            params=params
        )

        return unwrap_ei_collection(
            response, collection="basins", subject="rig-count by-basin"
        )

    def by_state(self, **params) -> List[Dict[str, Any]]:
        """Get rig counts by state.

        Args:
            **params: Optional ``states`` (comma-separated) and ``date``

        Returns:
            The ``states`` list from ``data``. Each record has ``region``,
            ``region_type``, ``count``, ``week_over_week`` and
            ``change_direction``.

        Example:
            >>> states = client.ei.rig_counts.by_state()
            >>> for state in states:
            ...     print(f"{state['region']}: {state['count']} rigs")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/rig_counts/by_state",
            params=params
        )

        return unwrap_ei_collection(
            response, collection="states", subject="rig-count by-state"
        )

    def historical(self, **params) -> List[Dict[str, Any]]:
        """Get historical rig counts for one region.

        Args:
            **params: Optional ``region`` (default ``us``), ``start_date``,
                ``end_date`` and ``limit``

        Returns:
            The ``records`` list from ``data``. Each record has ``date``,
            ``count`` and ``week_over_week``.

        Example:
            >>> history = client.ei.rig_counts.historical(region="us")
            >>> for record in history:
            ...     print(f"{record['date']}: {record['count']} rigs")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/rig_counts/historical",
            params=params
        )

        return unwrap_ei_collection(
            response, collection="records", subject="rig-count historical"
        )
